# app/api/routes_recipes.py
# 레시피 추천/검색 — 지용 담당

from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile

from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.schemas import (
    RecipeRecommendationOut,
    RecipeRecommendIn,
)
from app.services.reco import find_recipes_by_ingredients
from app.services.vision_openai import (
    extract_ingredients_from_files,
    VisionNotReady,
)


router = APIRouter(prefix="/photo", tags=["photo"])


# 텍스트(재료) 기반 추천 — 프론트 엔드포인트
@router.post("/recommend", response_model=List[RecipeRecommendationOut])
async def recommend_by_ingredients(
    payload: RecipeRecommendIn,
    anon_id: str = Depends(get_or_set_anon_id),  # 쿠키 유지
):
    # 입력 정리: 공백/빈값 제거
    ings = [s.strip() for s in (payload.ingredients or []) if isinstance(s, str) and s.strip()]
    if not ings:
        raise HTTPException(status_code=400, detail="ingredients required")

    db = get_db()
    docs = await find_recipes_by_ingredients(db, ings, limit=12)

    # 프론트 카드 스키마에 맞춰 변환
    return [
        RecipeRecommendationOut(
            id=str(d.get("_id", "") or d.get("id", "")),
            title=d.get("title", "") or "",
            description=(d.get("description") or ""),
            ingredients=d.get("ingredients", []) or [],
            steps=d.get("steps", []) or [],
            imageUrl=d.get("imageUrl"),
            tags=d.get("tags", []) or [],
        )
        for d in (docs or [])
    ]


# 사진 업로드 기반 추천 — 가변 파일 리스트 
@router.post("/recommend/upload", response_model=List[RecipeRecommendationOut])
async def recommend_from_images(
    files: List[UploadFile] = File(...),          # image_0~8 개별 필드 대신 한 번에
    anon_id: str = Depends(get_or_set_anon_id),
):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    # Vision 준비 미완이어도 앱은 살리고 503만 반환
    try:
        raw_ings = await extract_ingredients_from_files(files)
    except VisionNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 추출 재료 정리: 공백 제거 + 중복 제거 + 정렬(디버깅 편의)
    ings = sorted({s.strip() for s in (raw_ings or []) if isinstance(s, str) and s.strip()})
    if not ings:
        return []

    db = get_db()
    docs = await find_recipes_by_ingredients(db, ings, limit=12)

    return [
        RecipeRecommendationOut(
            id=str(d.get("_id", "") or d.get("id", "")),
            title=d.get("title", "") or "",
            description=(d.get("description") or ""),
            ingredients=d.get("ingredients", []) or [],
            steps=d.get("steps", []) or [],
            imageUrl=d.get("imageUrl"),
            tags=d.get("tags", []) or [],
        )
        for d in (docs or [])
    ]
