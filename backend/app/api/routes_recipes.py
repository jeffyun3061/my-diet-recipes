# app/api/routes_recipes.py
# 사진 업로드 → LLM으로 재료 추출 → DB 검색 → 프론트 카드 배열 반환

from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Request, Response, HTTPException, Depends

from app.db.init import get_db
from app.core.deps import get_or_set_anon_id
from app.db.models.schemas import RecipeRecommendationOut
from app.services.vision_openai import extract_ingredients_from_images

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _to_card(doc: Dict[str, Any]) -> RecipeRecommendationOut:
    title = doc.get("title") or ""
    desc = doc.get("summary") or doc.get("description") or ""
    image = (
        doc.get("image")
        or (doc.get("images") or [None])[0]
        if isinstance(doc.get("images", []), list)
        else doc.get("image")
    )
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


@router.post("/recommend", response_model=List[RecipeRecommendationOut])
async def recommend_from_images(
    req: Request,
    res: Response,
    anon_id: str = Depends(get_or_set_anon_id),  # 쿠키 보장
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
    files = [image_0, image_1, image_2, image_3, image_4, image_5, image_6, image_7, image_8]
    imgs: List[bytes] = []
    for f in files:
        if not f:
            continue
        if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=415, detail="지원하지 않는 이미지 형식입니다.")
        imgs.append(await f.read())
    if not imgs:
        raise HTTPException(status_code=400, detail="이미지가 필요합니다.")

    # LLM으로 재료 추출 (실패시 503으로 전달)
    try:
        detected = await extract_ingredients_from_images(imgs)
    except Exception as e:
        # VisionNotReady / 네트워크 / 포맷오류 등 모두 여기서 잡힘
        raise HTTPException(status_code=503, detail=str(e))
    tokens = [x["name"] for x in detected if x.get("name")]

    # DB 검색
    db = get_db()
    cond = {"ingredients.norm": {"$in": tokens}} if tokens else {}
    docs = await db["recipes"].find(cond).limit(24).to_list(length=24)

    # 간단 스코어링(매칭 개수 기준) — 추후 가중치/임베딩 혼합 확장 가능
    def score(d: Dict[str, Any]) -> int:
        norm = set(d.get("ingredients", {}).get("norm", [])) if isinstance(d.get("ingredients"), dict) else set()
        return sum(1 for t in tokens if t in norm)

    docs.sort(key=score, reverse=True)
    cards = [_to_card(d) for d in docs]

    # 추천 이력 저장(옵션)
    await db["recommendations"].insert_one({
        "anon_id": anon_id,
        "used": {"ingredients": detected},
        "result_ids": [c.id for c in cards],
        "created_at": __import__("datetime").datetime.utcnow(),
    })

    return [c.model_dump() for c in cards]


# (보조) Swagger/포스트맨에서 여러 장 올리기 쉬운 버전
@router.post("/recommend/files", response_model=List[RecipeRecommendationOut], tags=["recipes"])
async def recommend_from_files(
    files: List[UploadFile] = File(..., description="이미지 파일들 (여러 장 가능)"),
    anon_id: str = Depends(get_or_set_anon_id),
):
    # 파일 검증/읽기
    if not files:
        raise HTTPException(status_code=400, detail="이미지가 필요합니다.")

    imgs: List[bytes] = []
    for f in files:
        if not f or not getattr(f, "filename", ""):
            continue
        if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=415, detail="지원하지 않는 이미지 형식입니다.")
        imgs.append(await f.read())

    if not imgs:
        raise HTTPException(status_code=400, detail="이미지가 비었습니다.")

    # LLM → 재료 추출
    try:
        detected = await extract_ingredients_from_images(imgs)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    tokens = [x["name"] for x in detected if x.get("name")]

    # DB 검색
    db = get_db()
    cond = {"ingredients.norm": {"$in": tokens}} if tokens else {}
    docs = await db["recipes"].find(cond).limit(24).to_list(length=24)

    # 간단 스코어링
    def score(d: Dict[str, Any]) -> int:
        norm = set(d.get("ingredients", {}).get("norm", [])) if isinstance(d.get("ingredients"), dict) else set()
        return sum(1 for t in tokens if t in norm)

    docs.sort(key=score, reverse=True)
    cards = [_to_card(d) for d in docs]

    # 로그 남기기(옵션)
    await db["recommendations"].insert_one({
        "anon_id": anon_id,
        "used": {"ingredients": detected},
        "result_ids": [c.id for c in cards],
        "created_at": __import__("datetime").datetime.utcnow(),
    })

    return [c.model_dump() for c in cards]
