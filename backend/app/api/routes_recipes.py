# app/api/routes_recipes.py
# 사진 업로드 → LLM으로 재료 추출 → 재료 정규화 → DB 검색 → 카드 배열 반환

from __future__ import annotations
from typing import List, Dict, Any, Optional
import re
from fastapi import APIRouter, UploadFile, File, Request, Response, HTTPException, Depends

from app.db.init import get_db
from app.core.deps import get_or_set_anon_id
from app.db.models.schemas import RecipeRecommendationOut
from app.services.crawl10000.recommender import hybrid_recommend
from app.services.vision_openai import extract_ingredients_from_images, VisionNotReady
from app.services.crawl10000.etl import normalize_ingredients

# 카드 스키마 (표시용 3~4 태그/요약/단계 컷)
from app.models.schemas import RecipeCardStrict, to_strict_card

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

# 제목에 들어가면 컷할 키워드(요리 아님: 보관/언박싱/후기/세척 등)
EX_TITLE_RE = re.compile("(보관|보관법|저장|세척|언박싱|후기|구매가이드)")

# 재료 칩에도 쇼핑/가격 노이즈 제거 (프리뷰/모달 공통)
ING_NOISE_RE = re.compile(r"(원\b|구매|쿠폰|특가|스폰|광고|배송|장바구니|마켓|스마트스토어|리뷰)", re.I)

def _clean_ingredients(chips: list[str], max_len: Optional[int] = None) -> list[str]:
    
    # 재료 문자열에서 상표/라벨/쇼핑 단어/가격류 제거, 중복 제거.
    # max_len 지정 시 상한 적용(프리뷰는 6, 모달은 제한 없음).
    
    out, seen = [], set()
    for s in chips or []:
        t = re.sub(r"^\s*[\[\(].*?[\]\)]\s*", "", str(s).strip())  # [올팜] 같은 라벨 제거
        if not t or ING_NOISE_RE.search(t):
            continue
        t = re.sub(r"\s+", " ", t).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
        if max_len is not None and len(out) >= max_len:
            break
    return out

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
        id=str(doc.get("_id") or ""),
        title=title,
        description=desc,
        ingredients=ing_list,
        steps=steps,
        imageUrl=image,
        tags=[str(t) for t in tags] if tags else [],
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

# Vision → 재료 토큰화 → 추천
async def _detect_tokens_from_bytes(imgs: List[bytes]) -> List[str]:
    try:
        items = await extract_ingredients_from_images(imgs)
    except VisionNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"vision error: {e}")

    raw_names = [x.get("name", "") for x in items if isinstance(x, dict)]
    tokens = normalize_ingredients(raw_names)
    return tokens

# 업로드 추천: 카드 룰과 동일하게 후처리

async def _search_recipes(tokens: List[str]) -> List[RecipeRecommendationOut]:
    db = get_db()
    user_diet = ""  # TODO: "lowcarb" 등 내부 태그 문자열로 매핑해 넣으면 가점(+0.05)
    cards = await hybrid_recommend(db["recipes"], tokens, user_diet=user_diet, top_k=24)

    out: List[RecipeRecommendationOut] = []
    for c in cards:
        # description/summary 한 줄 요약(공백 정리 + 120자 컷)
        desc = (c.get("description") or c.get("summary") or "")
        desc = re.sub(r"\s+", " ", str(desc)).strip()[:120]

        # steps: 노이즈 제거 + 3줄 미리보기
        steps_preview = _compact3(c.get("steps") or [])

        # ingredients/tags: 공백 정리 + 개수 제한(ingredients는 6개까지)
        ingredients = _clean_ingredients([str(x) for x in (c.get("ingredients") or [])], max_len=6)
        tags = [
            s for s in (str(t).strip() for t in (c.get("tags") or [])) if s
        ][:6]

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

@router.post("/recommend", response_model=List[RecipeRecommendationOut])
async def recommend_from_images(
    req: Request,
    res: Response,
    anon_id: str = Depends(get_or_set_anon_id),   # 쿠키 보장
    image_0: UploadFile = File(...),
    image_1: UploadFile | None = File(None),
    image_2: UploadFile | None = File(None),
    image_3: UploadFile | None = File(None),
    image_4: UploadFile | None = File(None),
    image_5: UploadFile | None = File(None),
    image_6: UploadFile | None = File(None),
    image_7: UploadFile | None = File(None),
    image_8: UploadFile | None = File(None),
):
    files = [f for f in [image_0, image_1, image_2, image_3, image_4, image_5, image_6, image_7, image_8] if f]

    imgs: List[bytes] = []
    for f in files:
        if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=415, detail="지원하지 않는 이미지 형식입니다.")
        imgs.append(await f.read())

    if not imgs:
        raise HTTPException(status_code=400, detail="이미지가 필요합니다.")

    tokens = await _detect_tokens_from_bytes(imgs)
    cards = await _search_recipes(tokens)

    # 추천 이력 저장(옵션)
    db = get_db()
    await db["recommendations"].insert_one({
        "anon_id": anon_id,
        "used": {"tokens": tokens},
        "result_ids": [c.id for c in cards],
        "created_at": __import__("datetime").datetime.utcnow(),
    })

    return [c.model_dump() for c in cards]

@router.post("/recommend/files", response_model=List[RecipeRecommendationOut])
async def recommend_from_files(
    req: Request,
    res: Response,
    anon_id: str = Depends(get_or_set_anon_id),
    files: List[UploadFile] = File(..., description="이미지 파일들 (여러 장 가능)"),
):
    valid_files = [f for f in files if f and f.filename]
    imgs: List[bytes] = []
    for f in valid_files:
        if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=415, detail="지원하지 않는 이미지 형식입니다.")
        imgs.append(await f.read())

    if not imgs:
        raise HTTPException(status_code=400, detail="이미지가 필요합니다.")

    tokens = await _detect_tokens_from_bytes(imgs)
    cards = await _search_recipes(tokens)

    db = get_db()
    await db["recommendations"].insert_one({
        "anon_id": anon_id,
        "used": {"tokens": tokens},
        "result_ids": [c.id for c in cards],
        "created_at": __import__("datetime").datetime.utcnow(),
    })

    return [c.model_dump() for c in cards]

# Cards 전용 서브라우터

cards = APIRouter(prefix="/cards", tags=["recipes"])

def _strict_to_flat(c: RecipeCardStrict) -> RecipeRecommendationOut:
    v = c.variant  # 첫 변형
    # 1) 우선순위: steps > steps_compact
    raw_steps = (v.steps or []) if v and v.steps else (v.steps_compact or []) if v else []
    # 2) 가격/리뷰/쇼핑/잡문 제거 + 3줄(미리보기)
    steps_clean = _drop_noise_lines(raw_steps)[:3]

    # 요약 텍스트도 공백만 정리
    desc = (v.summary or c.subtitle or "") if v else (c.subtitle or "")
    desc = re.sub(r"\s+", " ", desc).strip()

    # 재료 칩도 노이즈 제거(프리뷰는 6개 상한)  ← ★ 여기서 한 번 더 방어
    ingredients = _clean_ingredients((v.key_ingredients or []) if v else [], max_len=6)

    return RecipeRecommendationOut(
        id=c.id,
        title=c.title,
        description=desc,
        ingredients=ingredients,
        steps=steps_clean,
        imageUrl=(c.imageUrl or None),
        tags=(c.tags or []),
    )

# 정적/특수 경로를 먼저 선언 (경로 충돌 방지: /flat, /full → /{id})
@cards.get("/flat", response_model=List[RecipeRecommendationOut])
async def list_cards_flat(limit: int = 30):
    db = get_db()
    # 요리 아님 컷 + 최소 1줄 스텝 보장
    query = {
        "is_recipe": True,
        "source.site": {"$in": ["만개의레시피", "unknown"]},
        "title": {"$not": EX_TITLE_RE},
        "$or": [
            {"variants.0.steps_compact.0": {"$exists": True}},
            {"variants.0.steps.0": {"$exists": True}},  # 백필/스키마 차이 대비
        ],
    }
    proj = {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}

    cur = db["recipe_cards"].find(query, proj).sort([("source.recipe_id", -1), ("id", 1)]).limit(limit)
    docs = await cur.to_list(length=limit)
    for d in docs:
        if isinstance(d.get("variants"), list):
            d["variants"] = d["variants"][:1]
    strict_cards = [to_strict_card(d) for d in docs]
    return [_strict_to_flat(c).model_dump() for c in strict_cards]

@cards.get("/{card_id}/flat", response_model=RecipeRecommendationOut)
async def get_card_flat(card_id: str):
    db = get_db()
    d = await db["recipe_cards"].find_one(
        {"id": card_id},
        {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
    )
    if not d:
        raise HTTPException(status_code=404, detail="recipe not found")
    if isinstance(d.get("variants"), list):
        d["variants"] = d["variants"][:1]
    return _strict_to_flat(to_strict_card(d)).model_dump()

# 상세 모달용 ‘풀 조리과정’ (고정 경로, 반드시 /{card_id} 위!)
@cards.get("/{card_id}/full")
async def get_card_full(card_id: str):
    # 상세 모달 전용:
    # - steps_full: 광고/가격/쇼핑 라인 제거된 '완전한' 조리과정 (길이 제한 없음)
    # - ingredients_full: 원문 재료 리스트(있으면) — 노이즈 제거(상한 없음)
    db = get_db()
    card = await db["recipe_cards"].find_one(
        {"id": card_id},
        {"_id": 0, "id": 1, "title": 1, "imageUrl": 1, "tags": 1, "source": 1}
    )
    if not card:
        raise HTTPException(status_code=404, detail="card not found")

    # 원본 recipe 찾기
    r = await _find_source_recipe(card, db)

    steps_full: list[str] = []
    ingredients_full: list[str] = []

    if r:
        # steps
        steps_full = _drop_noise_lines(_steps_from_any(r))

        # ingredients — 다양한 스키마에서 안전 추출
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

        ing = None
        for entry in [
            ("ingredients", ["list", "lines", "original"]),
            "ingredients", "재료", "재료목록"
        ]:
            if isinstance(entry, tuple):
                v = r.get(entry[0])
                if v:
                    ing = _list_from(v, entry[1])
                    if ing:
                        break
            else:
                v = r.get(entry)
                if v:
                    ing = _list_from(v, [])
                    if ing:
                        break
        # 모달은 상한 없이 깨끗하게
        ingredients_full = _clean_ingredients([s for s in (ing or []) if str(s).strip()], max_len=None)

    return {
        "id": card["id"],
        "title": card["title"],
        "imageUrl": card.get("imageUrl"),
        "tags": card.get("tags") or [],
        "ingredients_full": ingredients_full,
        "steps_full": steps_full,
        "source": card.get("source") or {},
    }

# 기본(스트릭트) 경로는 뒤에 선언
@cards.get("", response_model=List[RecipeCardStrict])
async def list_cards(limit: int = 30):
    db = get_db()
    query = {
        "is_recipe": True,
        "source.site": {"$in": ["만개의레시피", "unknown"]},
        "title": {"$not": EX_TITLE_RE},
        "$or": [
            {"variants.0.steps_compact.0": {"$exists": True}},
            {"variants.0.steps.0": {"$exists": True}},
        ],
    }
    proj = {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}

    cur = db["recipe_cards"].find(query, proj).sort([("source.recipe_id", -1), ("id", 1)]).limit(limit)
    docs = await cur.to_list(length=limit)
    for d in docs:
        if isinstance(d.get("variants"), list):
            d["variants"] = d["variants"][:1]
    return [to_strict_card(d) for d in docs]

@cards.get("/{card_id}", response_model=RecipeCardStrict)
async def get_card(card_id: str):
    db = get_db()
    d = await db["recipe_cards"].find_one(
        {"id": card_id},
        {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
    )
    if not d:
        raise HTTPException(status_code=404, detail="recipe not found")
    if isinstance(d.get("variants"), list):
        d["variants"] = d["variants"][:1]
    return to_strict_card(d)

# 메인 라우터에 서브라우터 등록 (경로 충돌 방지)
router.include_router(cards)
