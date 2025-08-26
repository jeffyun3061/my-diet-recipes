# app/api/routes_recipes.py
# 사진 업로드 → LLM으로 재료 추출 → 재료 정규화 → DB 검색 → 카드 배열 반환

from __future__ import annotations
from typing import List, Dict, Any
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


async def _detect_tokens_from_bytes(imgs: List[bytes]) -> List[str]:
    # Vision으로 재료 추출
    try:
        items = await extract_ingredients_from_images(imgs)
    except VisionNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # 기타 네트워크/모델 에러
        raise HTTPException(status_code=503, detail=f"vision error: {e}")

    # 이름만 추출 → 정규화
    raw_names = [x.get("name", "") for x in items if isinstance(x, dict)]
    tokens = normalize_ingredients(raw_names)
    return tokens


async def _search_recipes(tokens: List[str]) -> List[RecipeRecommendationOut]:
    # 기존 단순 find/sort 대신 하이브리드 추천으로 교체.
    # tokens: 비전/LLM에서 추출한 slug 리스트
    db = get_db()

    # (필요 시) 사용자 식단 라벨 가점 반영 가능
    # ex) prefs = await db["preferences"].find_one({"anon_id": ...})
    user_diet = ""  # TODO: "lowcarb" 등 내부 태그 문자열로 매핑해 넣으면 가점(+0.05)

    # 하이브리드 추천 호출 → 프론트 카드 스키마에 맞춘 dict 리스트 반환
    cards = await hybrid_recommend(db["recipes"], tokens, user_diet=user_diet, top_k=24)

    # Pydantic 모델로 변환하여 반환 (기존 response_model 유지)
    return [
        RecipeRecommendationOut(
            id=c.get("id", ""),
            title=c.get("title", ""),
            description=c.get("description", ""),
            ingredients=c.get("ingredients", []),
            steps=c.get("steps", []),
            imageUrl=c.get("imageUrl", ""),
            tags=c.get("tags", []),
        )
        for c in cards
    ]


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
    # Swagger에서 빈 문자열("")을 보내면 422가 떠서, 프론트는 반드시 "없는 필드는 아예 보내지 않기"
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
    # 진짜 파일만 필터
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


# Cards 전용 서브라우터 (충돌 방지 고정) 

cards = APIRouter(prefix="/cards", tags=["recipes"])

def _strict_to_flat(c: RecipeCardStrict) -> RecipeRecommendationOut:
    # RecipeCardStrict → 기존 프론트 카드 스키마로 평탄화
    v = c.variant  # 모델에서 첫 변형을 반환하는 프로퍼티
    return RecipeRecommendationOut(
        id=c.id,
        title=c.title,
        description=(v.summary or c.subtitle or ""),
        ingredients=(v.key_ingredients or []),
        steps=(v.steps or []),           # 이미 3줄 요약
        imageUrl=(c.imageUrl or None),
        tags=(c.tags or []),
    )

# 정적/특수 경로를 먼저 선언 

@cards.get("/flat", response_model=List[RecipeRecommendationOut])
async def list_cards_flat(limit: int = 30):
    db = get_db()
    cur = db["recipe_cards"].find(
        {"source.site": {"$in": ["만개의레시피", "unknown"]}},
        {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
    ).sort([("source.recipe_id", -1), ("id", 1)]).limit(limit)
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

# 기본(스트릭트) 경로는 뒤에 선언

@cards.get("", response_model=List[RecipeCardStrict])
async def list_cards(limit: int = 30):
    db = get_db()
    cur = db["recipe_cards"].find(
        {"source.site": {"$in": ["만개의레시피", "unknown"]}},
        {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "tags": 1, "imageUrl": 1, "variants": 1}
    ).sort([("source.recipe_id", -1), ("id", 1)]).limit(limit)
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
