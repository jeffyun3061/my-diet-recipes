# app/api/routes_recipes.py
# 사진 업로드 → LLM으로 재료 추출 → 재료 정규화 → DB 검색 → 카드 배열 반환

from __future__ import annotations
from typing import List, Dict, Any, Optional
import re
import logging
from fastapi import APIRouter, UploadFile, Request, HTTPException, Depends
from bson import ObjectId
from typing import Mapping, Any


from app.db.init import get_db
from app.core.deps import get_or_set_anon_id
from app.db.models.schemas import RecipeRecommendationOut
from app.services.crawl10000.recommender import hybrid_recommend
from app.services.vision_openai import extract_ingredients_from_images, VisionNotReady
from app.services.crawl10000.seed_ing import normalize_ingredients_ko

# 카드 스키마 (표시용 3~4 태그/요약/단계 컷)
from app.models.schemas import RecipeCardStrict, to_strict_card

log = logging.getLogger(__name__)

# 메인 라우터
router = APIRouter(prefix="/recipes", tags=["recipes"])

# ------------------------------
# 공통 노이즈 필터 & 헬퍼
# ------------------------------

# 가격/리뷰/쇼핑/광고 라인 제거 (steps/본문)
PRICE_RE  = re.compile(r"(?<!\d)(?:\d{1,3}(?:[,\.\s]\d{3})+|\d+)\s*(?:원|krw)\b", re.I)
RATING_RE = re.compile(r"(?:평점\s*)?\b[0-5](?:\.\d)?\s*\([\d,]+\)")
SHOP_RE   = re.compile(r"(구매|쿠폰|특가|배송|장바구니|마켓|스마트스토어|리뷰|광고|스폰|만개의레시피|요리사랑|815요리사랑)", re.I)
BULLET_RE = re.compile(r"^\s*(?:\d+\s*[.)]|[-•●▪])\s*")

def to_recipe_recommendation(doc: Mapping[str, Any]) -> dict:
    rid = str(doc.get("_id") or doc.get("id") or "")
    return {
        "id": rid,
        "title": doc.get("title", ""),
        "description": doc.get("summary", "") or doc.get("description", ""),
        "imageUrl": doc.get("imageUrl") or doc.get("image") or "",
        "tags": (
            doc.get("tags")
            or doc.get("chips")
            or doc.get("key_ingredients")
            or []
        ),
        "ingredients": (
            doc.get("ingredients_full")
            or doc.get("ingredients")
            or []
        ),
        "steps": (
            doc.get("steps_full")
            or doc.get("steps_compact")
            or doc.get("steps")
            or []
        ),
    }

def _drop_noise_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for s in (lines or []):
        s = str(s).strip()
        if not s:
            continue
        if PRICE_RE.search(s) or RATING_RE.search(s) or SHOP_RE.search(s):
            continue
        s = BULLET_RE.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    return out

def _compact3(lines: list[str]) -> list[str]:
    # 카드 미리보기용: 노이즈 제거 후 최대 3줄
    return _drop_noise_lines([str(x) for x in (lines or [])])[:3]

# 제목 컷 키워드(요리 아님: 보관/언박싱/후기/세척 등)
EX_TITLE_RE = re.compile("(보관|보관법|저장|세척|언박싱|후기|구매가이드)")

# 재료 칩 노이즈 제거
ING_NOISE_RE = re.compile(r"(원\b|구매|쿠폰|특가|스폰|광고|배송|장바구니|마켓|스마트스토어|리뷰)", re.I)

def _clean_ingredients(chips: list[str], max_len: Optional[int] = None) -> list[str]:
    out, seen = [], set()
    for s in chips or []:
        t = re.sub(r"^\s*[\[\(].*?[\]\)]\s*", "", str(s).strip())  # [라벨] 제거
        if not t or ING_NOISE_RE.search(t):
            continue
        t = re.sub(r"\s+", " ", t).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
        if max_len is not None and len(out) >= max_len:
            break
    return out

def _ensure_id_from__id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    recipe_cards 컬렉션의 _id(ObjectId)를 문자열로 변환해 'id' 필드에 주입.
    기존 문서에 id가 있더라도, 모달 상세 조회 일관성을 위해 _id 우선으로 덮어쓴다.
    """
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
    return doc

# ------------------------------
# 원본 → 카드 변환 헬퍼
# ------------------------------

def _to_card(doc: Dict[str, Any]) -> RecipeRecommendationOut:
    title = doc.get("title") or ""
    desc = doc.get("summary") or doc.get("description") or ""
    image = None
    if isinstance(doc.get("images"), list) and doc.get("images"):
        image = doc["images"][0]
    image = image or doc.get("image") or ""
    tags = doc.get("tags") or doc.get("categories") or []

    ing_list: List[str] = []
    if isinstance(doc.get("ingredients"), dict):
        for k in ["original", "lines", "list"]:
            v = doc["ingredients"].get(k)
            if isinstance(v, list):
                ing_list = [str(x) for x in v if x]
                if ing_list:
                    break
    elif isinstance(doc.get("ingredients"), list):
        ing_list = [str(x) for x in doc["ingredients"] if x]

    steps: List[str] = []
    for k in ["steps", "directions", "instructions"]:
        v = doc.get(k)
        if isinstance(v, list):
            steps = [str(x) for x in v if x]
            if steps:
                break

    return RecipeRecommendationOut(
        id=str(doc.get("_id") or doc.get("id") or ""),
        title=title,
        description=desc,
        ingredients=ing_list,
        steps=steps,
        imageUrl=image,
        tags=[str(t) for t in (tags or [])],
    )

# ‘원본 recipes’ 문서의 steps 안전 추출
STEP_CANDIDATES = ["steps", "directions", "instructions", "조리과정", "조리방법", "만드는법", "recipeSteps"]
def _steps_from_any(doc: Dict[str, Any]) -> List[str]:
    for k in STEP_CANDIDATES:
        v = doc.get(k)
        if not v:
            continue
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        if isinstance(v, dict):
            for kk in ("list", "lines", "original"):
                vv = v.get(kk)
                if isinstance(vv, list):
                    return [str(x) for x in vv if str(x).strip()]
                if isinstance(vv, str) and vv.strip():
                    parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", vv)
                    return [p.strip() for p in parts if p.strip()]
        if isinstance(v, str) and v.strip():
            parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", v)
            return [p.strip() for p in parts if p.strip()]
    return []

async def _find_source_recipe(card: Dict[str, Any], db) -> Optional[Dict[str, Any]]:
    """recipe_cards → recipes 역참조 (url/recipe_id/title 기준)"""
    src = card.get("source") or {}
    url = src.get("url") or src.get("href")
    rid = src.get("recipe_id")
    title = card.get("title") or ""
    r = None
    if url:
        r = await db["recipes"].find_one({"$or": [
            {"url": url}, {"link": url}, {"source.url": url}, {"source.href": url}
        ]})
    if not r and rid:
        r = await db["recipes"].find_one({"url": {"$regex": f"/{rid}$"}})
    if not r and title:
        r = await db["recipes"].find_one({"title": title})
    return r

# ------------------------------
# 업로드 수집 / Vision / 추천
# ------------------------------

async def _collect_uploads(request: Request) -> List[bytes]:
    """
    - image_0..image_8 필드 또는
    - files=[UploadFile,...] 배열
    모두 지원. 이미지 MIME만 통과.
    """
    imgs: List[bytes] = []
    try:
        form = await request.form()
    except Exception:
        form = None

    if form:
        for _, v in form.multi_items():
            if not v:
                continue
            ct = getattr(v, "content_type", None)
            if not ct:
                continue
            ct = ct.lower()
            if ct in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
                try:
                    data = await v.read()
                except Exception:
                    continue
                if data:
                    imgs.append(data)
    return imgs

async def _detect_tokens_from_bytes(imgs: List[bytes]) -> tuple[List[str], List[str]]:
    try:
        items = await extract_ingredients_from_images(imgs)
    except VisionNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"vision_error: {e}")

    raw_names = [x.get("name", "") for x in items if isinstance(x, dict)]
    raw_names = [n for n in raw_names if n]
    tokens = normalize_ingredients_ko(raw_names)
    return tokens, raw_names

async def _search_recipes(db, tokens: List[str]) -> List[RecipeRecommendationOut]:
    # NOTE: recommender.hybrid_recommend(db, ingredients, limit=30) 시그니처에 맞춤
    cards = await hybrid_recommend(db, tokens, limit=30)

    out: List[RecipeRecommendationOut] = []
    for c in cards:
        desc = (c.get("description") or c.get("summary") or "")
        desc = re.sub(r"\s+", " ", str(desc)).strip()[:120]
        steps_preview = _compact3(c.get("steps") or [])
        ingredients = _clean_ingredients([str(x) for x in (c.get("ingredients") or [])], max_len=6)
        tags = [s for s in (str(t).strip() for t in (c.get("tags") or [])) if s][:6]

        out.append(
            RecipeRecommendationOut(
                id=str(c.get("id", "")),
                title=str(c.get("title", "")),
                description=desc,
                ingredients=ingredients,
                steps=steps_preview,
                imageUrl=c.get("imageUrl") or "",
                tags=tags,
            )
        )
    return out

# ------------------------------
# 추천 코어 + 안전 직렬화
# ------------------------------

def _to_dict(x: Any) -> Any:
    # pydantic v2/v1 모두 지원
    try:
        return x.model_dump()    # v2
    except Exception:
        try:
            return x.dict()      # v1
        except Exception:
            return x

async def _recommend_from_imgs(img_bytes: list[bytes], db) -> list[RecipeRecommendationOut]:
    if not img_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 없습니다.")

    try:
        # Vision → 원재료명
        items = await extract_ingredients_from_images(img_bytes)
    except VisionNotReady as e:
        log.warning("VisionNotReady: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.exception("Vision error")
        raise HTTPException(status_code=500, detail=f"vision_error: {e}")

    raw = [x.get("name", "") for x in items if isinstance(x, dict) and x.get("name")]
    tokens = normalize_ingredients_ko(raw)
    log.info("recommend raw=%s -> tokens=%s (n_images=%d)", raw, tokens, len(img_bytes))

    if not tokens:
        raise HTTPException(
            status_code=422,
            detail={"msg": "이미지에서 핵심 재료를 찾지 못했습니다.", "debug": {"raw": raw, "images": len(img_bytes)}},
        )

    try:
        return await _search_recipes(db, tokens)
    except Exception as e:
        log.exception("hybrid_recommend failed")
        raise HTTPException(status_code=500, detail=f"recommend_error: {e}")

async def _read_uploadfiles(uploads: list[UploadFile]) -> list[bytes]:
    imgs: list[bytes] = []
    for up in uploads:
        if not up:
            continue
        if up.content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
            continue
        data = await up.read()
        if data:
            imgs.append(data)
    return imgs[:9]  # 최대 9장만 사용 (프리뷰/성능 보호)

# ------------------------------
# 엔드포인트: 추천
# ------------------------------

@router.post("/recommend", response_model=List[RecipeRecommendationOut])
async def recommend(
    request: Request,
    db=Depends(get_db),
    anon_id: str = Depends(get_or_set_anon_id),
):
    """
    프런트가 보내는 모든 형태의 업로드 요청을 수신하여 처리합니다.
    - image_0..image_8 필드
    - files / files[] 배열
    - 기타 form-data 속 UploadFile 항목들
    """
    img_bytes = await _collect_uploads(request)
    if not img_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 없습니다.")
    items = await _recommend_from_imgs(img_bytes, db)
    return [_to_dict(it) for it in items]

@router.post("/recommend/files")
async def recommend_files(
    request: Request,
    db=Depends(get_db),
    _: str = Depends(get_or_set_anon_id),
):
    """
    일부 클라이언트가 필드명을 고정하지 않고 멀티파트로만 보낼 때 대응:
    request.form()에서 UploadFile들을 긁어와 처리.
    """
    img_bytes = await _collect_uploads(request)
    if not img_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 없습니다.")
    items = await _recommend_from_imgs(img_bytes, db)
    return [_to_dict(it) for it in items]

@router.post("/recommend/tokens")     #재료 배열 확인용
async def recommend_from_tokens(
    body: dict, db = Depends(get_db)
):
    tokens = normalize_ingredients_ko(body.get("tokens") or [])
    cards = await hybrid_recommend(db, ingredients=tokens, limit=20)
    return [to_recipe_recommendation(c) for c in cards]

@router.get("/{rid}")
async def get_recipe_full(rid: str, db=Depends(get_db)):
    from bson import ObjectId
    q = {"_id": ObjectId(rid)} if ObjectId.is_valid(rid) else {"id": rid}
    doc = await db.recipe_cards.find_one(q)
    if not doc:
        raise HTTPException(404, "not found")
    return to_recipe_recommendation(doc)

# ------------------------------
# Cards 전용 서브라우터
# ------------------------------

cards = APIRouter(prefix="/cards", tags=["recipes"])

def _strict_to_flat(c: RecipeCardStrict) -> RecipeRecommendationOut:
    v = getattr(c, "variant", None)  # 첫 변형
    # 1) 우선순위: steps > steps_compact
    raw_steps = (v.steps or []) if v and getattr(v, "steps", None) else (getattr(v, "steps_compact", []) or [])
    # 2) 가격/리뷰/쇼핑/잡문 제거 + 3줄(미리보기)
    steps_clean = _drop_noise_lines(raw_steps)[:3]

    # 요약 텍스트도 공백만 정리
    desc = (getattr(v, "summary", "") or getattr(c, "subtitle", "")) if v else (getattr(c, "subtitle", "") or "")
    desc = re.sub(r"\s+", " ", desc).strip()

    # 재료 칩도 노이즈 제거(프리뷰는 6개 상한)
    key_ing = getattr(v, "key_ingredients", []) if v else []
    ingredients = _clean_ingredients(key_ing, max_len=6)

    return RecipeRecommendationOut(
        id=c.id,
        title=c.title,
        description=desc,
        ingredients=ingredients,
        steps=steps_clean,
        imageUrl=(getattr(c, "imageUrl", None) or None),
        tags=(getattr(c, "tags", []) or []),
    )

# 정적/특수 경로를 먼저 선언 (경로 충돌 방지: /flat, /full → /{id})
@cards.get("/flat", response_model=List[RecipeRecommendationOut])
async def list_cards_flat(limit: int = 30, db=Depends(get_db)):
    query = {
        "is_recipe": True,
        "source.site": {"$in": ["만개의레시피", "unknown"]},
        "title": {"$not": EX_TITLE_RE},
        "$or": [
            {"variants.0.steps_compact.0": {"$exists": True}},
            {"variants.0.steps.0": {"$exists": True}},  # 백필/스키마 차이 대비
        ],
    }
    proj = {
        "id": 1,
        "title": 1,
        "subtitle": 1,          # 프리뷰 폴백 소스
        "summary": 1,
        "description": 1,
        "imageUrl": 1,
        "tags": 1,
        "chips": 1,
        "ingredients": 1,
        "ingredients_full": 1,
        "ingredients_clean": 1,
        "steps": 1,
        "steps_full": 1,
        "variants": 1,          # v.summary / v.steps(_compact) / v.key_ingredients
    }

    cur = db["recipe_cards"].find(query, proj).sort([("source.recipe_id", -1), ("_id", 1)]).limit(limit)
    docs = await cur.to_list(length=limit)

    # 중요: _id → id 강제 세팅 + 첫 변형만 사용
    for d in docs:
        _ensure_id_from__id(d)
        if isinstance(d.get("variants"), list):
            d["variants"] = d["variants"][:1]

    strict_cards = [to_strict_card(d) for d in docs]
    return [_strict_to_flat(c).model_dump() for c in strict_cards]

@cards.get("/{card_id}/flat", response_model=RecipeRecommendationOut)
async def get_card_flat(card_id: str, db=Depends(get_db)):
    # ObjectId 시도 → 실패 시 문자열 id 필드로도 검색(하위호환)
    try:
        q = {"_id": ObjectId(card_id)}
    except Exception:
        q = {"id": card_id}

    d = await db["recipe_cards"].find_one(
        q,
        {"id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
    )
    if not d:
        raise HTTPException(status_code=404, detail="recipe not found")

    _ensure_id_from__id(d)
    if isinstance(d.get("variants"), list):
        d["variants"] = d["variants"][:1]
    return _strict_to_flat(to_strict_card(d)).model_dump()

# 상세 모달용 ‘풀 조리과정’ (카드 id + 레시피 id 둘 다 지원)
@cards.get("/{card_id}/full")
async def get_card_full(card_id: str, db=Depends(get_db)):
    """
    상세 모달 전용:
      A) card_id가 recipe_cards._id → 카드 기반으로 구성
      B) card_id가 recipes._id       → 원본 기반 구성 + 역매핑으로 카드 찾아 최종 폴백
    """
    db = get_db()

    def _list_from(d, keys: list[str] = []) -> list[str]:
        if isinstance(d, dict):
            for k in keys:
                v = d.get(k)
                if isinstance(v, list):
                    return [str(x) for x in v if x]
                if isinstance(v, str) and v.strip():
                    parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", v)
                    return [p.strip() for p in parts if p.strip()]
        if isinstance(d, list):
            return [str(x) for x in d if x]
        if isinstance(d, str) and d.strip():
            parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", d)
            return [p.strip() for p in parts if p.strip()]
        return []

    # ---------- A) recipe_cards._id 로 시도 ----------
    card = None
    try:
        card = await db["recipe_cards"].find_one(
            {"_id": ObjectId(card_id)},
            {
                "_id": 1, "id": 1, "title": 1, "imageUrl": 1, "tags": 1, "source": 1,
                "steps_full": 1, "ingredients_full": 1, "variants": 1
            }
        )
    except Exception:
        pass

    if card:
        steps_full: list[str] = []
        ingredients_full: list[str] = []

        # 원본 recipes 우선
        r = await _find_source_recipe(card, db)
        if r:
            steps_full = _drop_noise_lines(_steps_from_any(r))
            ing = None
            for entry in [
                ("ingredients", ["list", "lines", "original"]),
                "ingredients", "재료", "재료목록"
            ]:
                if isinstance(entry, tuple):
                    v = r.get(entry[0])
                    if v:
                        ing = _list_from(v, entry[1])
                        if ing: break
                else:
                    v = r.get(entry)
                    if v:
                        ing = _list_from(v, [])
                        if ing: break
            ingredients_full = _clean_ingredients([s for s in (ing or []) if str(s).strip()], max_len=None)

        # 카드 백필 폴백
        if not steps_full:
            steps_full = _drop_noise_lines([str(x) for x in (card.get("steps_full") or []) if str(x).strip()])
        if not ingredients_full:
            ingredients_full = _clean_ingredients([str(x) for x in (card.get("ingredients_full") or []) if str(x).strip()], max_len=None)

        # variants 최종 폴백
        if (not steps_full) or (not ingredients_full):
            v0 = (card.get("variants") or [None])[0] or {}
            if not steps_full:
                raw_steps = (v0.get("steps") or []) or (v0.get("steps_compact") or [])
                steps_full = _drop_noise_lines([str(x).strip() for x in raw_steps if str(x).strip()])
            if not ingredients_full:
                ingredients_full = _clean_ingredients([str(x).strip() for x in (v0.get("key_ingredients") or []) if str(x).strip()], max_len=None)

        # persist on-demand fill (A-branch)
        try:
            to_set: Dict[str, Any] = {}
            if steps_full and not (card.get("steps_full") or []):
                to_set["steps_full"] = steps_full
            if ingredients_full and not (card.get("ingredients_full") or []):
                to_set["ingredients_full"] = ingredients_full
            if to_set:
                await db["recipe_cards"].update_one({"_id": card["_id"]}, {"$set": to_set})
        except Exception:
            pass

        return {
            "id": str(card.get("_id") or card.get("id")),
            "title": card.get("title") or "",
            "imageUrl": card.get("imageUrl"),
            "tags": card.get("tags") or [],
            "ingredients_full": ingredients_full,
            "steps_full": steps_full,
            "source": card.get("source") or {},
        }

    # ---------- B) recipes._id 로 처리 + 역매핑 ----------
    try:
        r = await db["recipes"].find_one({"_id": ObjectId(card_id)})
    except Exception:
        r = None

    if r:
        title = str(r.get("title") or r.get("name") or "")
        image = None
        if isinstance(r.get("images"), list) and r["images"]:
            image = r["images"][0]
        image = image or r.get("image") or r.get("thumbnail") or None
        tags = r.get("tags") or r.get("categories") or []

        # 1) 원본에서 추출
        steps_full = _drop_noise_lines(_steps_from_any(r))

        ing = None
        for entry in [
            ("ingredients", ["list", "lines", "original"]),
            "ingredients", "재료", "재료목록"
        ]:
            if isinstance(entry, tuple):
                v = r.get(entry[0])
                if v:
                    ing = _list_from(v, entry[1])
                    if ing: break
            else:
                v = r.get(entry)
                if v:
                    ing = _list_from(v, [])
                    if ing: break
        ingredients_full = _clean_ingredients([s for s in (ing or []) if str(s).strip()], max_len=None)

        # 2) 역매핑: recipes → recipe_cards (url/title/recipe_id 근사 매칭)
        mc = None
        if (not steps_full) or (not ingredients_full):
            url = r.get("url") or r.get("link")
            rid_from_url = None
            if isinstance(url, str):
                m = re.search(r"/([^/]+)$", url.strip())
                if m:
                    rid_from_url = m.group(1)

            mc = await db["recipe_cards"].find_one(
                {"$or": [
                    {"source.url": url}, {"source.href": url},
                    {"source.recipe_id": rid_from_url} if rid_from_url else {"_id": None},
                    {"title": title} if title else {"_id": None},
                ]},
                {
                    "_id": 1, "title": 1, "imageUrl": 1, "tags": 1, "variants": 1,
                    "steps_full": 1, "ingredients_full": 1, "source": 1
                }
            )

            if mc:
                # 카드 백필 폴백
                if not steps_full:
                    steps_full = _drop_noise_lines([str(x) for x in (mc.get("steps_full") or []) if str(x).strip()])
                if not ingredients_full:
                    ingredients_full = _clean_ingredients([str(x) for x in (mc.get("ingredients_full") or []) if str(x).strip()], max_len=None)

                # variants 최종 폴백
                if (not steps_full) or (not ingredients_full):
                    v0 = (mc.get("variants") or [None])[0] or {}
                    if not steps_full:
                        raw_steps = (v0.get("steps") or []) or (v0.get("steps_compact") or [])
                        steps_full = _drop_noise_lines([str(x).strip() for x in raw_steps if str(x).strip()])
                    if not ingredients_full:
                        ingredients_full = _clean_ingredients([str(x).strip() for x in (v0.get("key_ingredients") or []) if str(x).strip()], max_len=None)

                # persist for mapped card (B-branch)
                try:
                    to_set: Dict[str, Any] = {}
                    if steps_full and not (mc.get("steps_full") or []):
                        to_set["steps_full"] = steps_full
                    if ingredients_full and not (mc.get("ingredients_full") or []):
                        to_set["ingredients_full"] = ingredients_full
                    if to_set:
                        await db["recipe_cards"].update_one({"_id": mc["_id"]}, {"$set": to_set})
                except Exception:
                    pass

                # 카드에서 태그/이미지 보강
                if not image:
                    image = mc.get("imageUrl") or image
                if not tags:
                    tags = mc.get("tags") or tags

        return {
            "id": str(r["_id"]),   # 프론트는 이 id로 호출했음
            "title": title,
            "imageUrl": image,
            "tags": [str(t) for t in (tags or [])],
            "ingredients_full": ingredients_full,
            "steps_full": steps_full,
            "source": r.get("source") or {},
        }

    # 전부 실패
    raise HTTPException(status_code=404, detail="card not found")

# 기본(스트릭트) 경로는 뒤에 선언
@cards.get("", response_model=List[RecipeCardStrict])
async def list_cards(limit: int = 30, db=Depends(get_db)):
    query = {
        "is_recipe": True,
        "source.site": {"$in": ["만개의레시피", "unknown"]},
        "title": {"$not": EX_TITLE_RE},
        "$or": [
            {"variants.0.steps_compact.0": {"$exists": True}},
            {"variants.0.steps.0": {"$exists": True}},
        ],
    }
    proj = {"id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}

    cur = db["recipe_cards"].find(query, proj).sort([("source.recipe_id", -1), ("_id", 1)]).limit(limit)
    docs = await cur.to_list(length=limit)

    for d in docs:
        _ensure_id_from__id(d)  # _id → id 주입
        if isinstance(d.get("variants"), list):
            d["variants"] = d["variants"][:1]
    return [to_strict_card(d) for d in docs]

@cards.get("/{card_id}", response_model=RecipeCardStrict)
async def get_card(card_id: str, db=Depends(get_db)):
    # _id 우선
    d = None
    try:
        d = await db["recipe_cards"].find_one(
            {"_id": ObjectId(card_id)},
            {"id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
        )
    except Exception:
        pass
    if not d:
        d = await db["recipe_cards"].find_one(
            {"id": card_id},
            {"id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
        )
    if not d:
        raise HTTPException(status_code=404, detail="recipe not found")

    _ensure_id_from__id(d)
    if isinstance(d.get("variants"), list):
        d["variants"] = d["variants"][:1]
    return to_strict_card(d)

# 메인 라우터에 서브라우터 등록 (경로 충돌 방지)
router.include_router(cards)
