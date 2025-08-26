# app/api/routes_photo.py
# 사진 분석/추천 — 지용 담당

from __future__ import annotations
from typing import List, Optional
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Response

from bson.objectid import ObjectId
from bson.errors import InvalidId 
from urllib.parse import quote
import logging # ObjectId 유효성 검사를 위해 import

from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.schemas import (
    RecipeRecommendationOut,
    RecipeRecommendIn,
    PhotoDoc,
)
from app.services.crawl10000.recommender import hybrid_recommend
from app.services.vision_openai import (
    extract_ingredients_from_files,
    VisionNotReady,
)
from app.services.crawl10000.etl import normalize_ingredients
from app.services.analyze import analyze_image_detailed


router = APIRouter(prefix="/photo", tags=["photo"])

@router.post("/upload")
async def upload_photo(file: UploadFile = File(...), anon_id: str = Depends(get_or_set_anon_id)):
    """
    사진을 업로드하여 DB에 저장하는 API
    """
    # 파일 타입 검증
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")
    
    # 파일 크기 제한 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    try:
        image_bytes = await file.read()
        if len(image_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="파일 크기는 10MB 이하여야 합니다")
        
        if not image_bytes:
            raise HTTPException(status_code=400, detail="비어있는 파일은 업로드할 수 없습니다")
        

    except Exception as e:
        raise HTTPException(status_code=400, detail="파일 읽기 중 오류가 발생했습니다")
    
    # DB에 저장
    db = get_db()
    photo_doc = PhotoDoc(
        anon_id=anon_id,
        filename=file.filename,
        content_type=file.content_type,
        data=image_bytes
    )
    
    try:
        result = await db["photos"].insert_one(photo_doc.dict())
        return {
            "success": True,
            "photo_id": str(result.inserted_id),
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(image_bytes),
            "uploaded_at": photo_doc.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="사진 저장 중 오류가 발생했습니다")

@router.get("/list")
async def list_photos(anon_id: str = Depends(get_or_set_anon_id), limit: int = 20, skip: int = 0):
    """
    사용자의 업로드된 사진 목록을 조회하는 API
    """
    db = get_db()
    
    try:
        # 사진 목록 조회 (data 필드는 제외하여 용량 절약)
        cursor = db["photos"].find(
            {"anon_id": anon_id},
            {"data": 0}  # data 필드 제외
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        photos = await cursor.to_list(length=limit)
        
        # ObjectId를 문자열로 변환
        for photo in photos:
            photo["_id"] = str(photo["_id"])
            photo["created_at"] = photo["created_at"].isoformat()
        
        return {
            "photos": photos,
            "total": len(photos),
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="사진 목록 조회 중 오류가 발생했습니다")

@router.get("/{photo_id}")
async def get_photo(photo_id: str, anon_id: str = Depends(get_or_set_anon_id)):
    """
    특정 사진을 조회하는 API
    """
    if not ObjectId.is_valid(photo_id):
        raise HTTPException(status_code=400, detail=f"'{photo_id}'는 유효한 ObjectId 형식이 아닙니다.")

    db = get_db()
    
    try:
        photo = await db["photos"].find_one({
            "_id": ObjectId(photo_id),
            "anon_id": anon_id
        })
        
        if not photo:
            raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")
        
        if "data" not in photo or not photo["data"]:
            logging.error(f"DB 문서에 'data' 필드가 없습니다. 문서 내용: {photo}")
            raise HTTPException(status_code=500, detail="사진 데이터가 손상되었습니다.")
        
        filename = photo.get('filename', 'photo.jpg')
        encoded_filename = quote(filename.encode('utf-8'))

        return Response(
            content=photo["data"],
            media_type=photo.get("content_type", "image/jpeg"),
            headers={
                # filename*=UTF-8''... 형식은 표준 RFC 5987 방식입니다.
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        # 어떤 종류의 에러가 발생했는지 로그로 출력
        logging.error(f"사진 조회 중 예상치 못한 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="사진 조회 중 오류가 발생했습니다")

@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, anon_id: str = Depends(get_or_set_anon_id)):
    """
    특정 사진을 삭제하는 API
    """
    
    db = get_db()
    
    try:
        result = await db["photos"].delete_one({
            "_id": ObjectId(photo_id),
            "anon_id": anon_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="삭제할 사진을 찾을 수 없습니다")
        
        return {"success": True, "message": "사진이 삭제되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="사진 삭제 중 오류가 발생했습니다")

@router.post("/analyze")
async def analyze_photo(
    file: UploadFile = File(...),
    anon_id: str = Depends(get_or_set_anon_id)
):
    """
    Google Cloud Vision API를 사용한 이미지 분석
    """
    # 파일 타입 검증
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="이미지 파일만 분석 가능합니다")
    
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="비어있는 파일은 분석할 수 없습니다")
        
        # Google Cloud Vision API를 사용한 이미지 분석
        analysis_result = await analyze_image_detailed(image_bytes)
        
        return {
            "success": True,
            "filename": file.filename,
            "analysis": analysis_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}")

@router.post("/analyze/{photo_id}")
async def analyze_stored_photo(
    photo_id: str,
    anon_id: str = Depends(get_or_set_anon_id)
):
    """
    저장된 사진을 Google Cloud Vision API로 분석
    """
    if not ObjectId.is_valid(photo_id):
        raise HTTPException(status_code=400, detail=f"'{photo_id}'는 유효한 ObjectId 형식이 아닙니다.")

    db = get_db()
    
    try:
        photo = await db["photos"].find_one({
            "_id": ObjectId(photo_id),
            "anon_id": anon_id
        })
        
        if not photo:
            raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")
        
        if "data" not in photo or not photo["data"]:
            raise HTTPException(status_code=500, detail="사진 데이터가 손상되었습니다.")
        
        # Google Cloud Vision API를 사용한 이미지 분석
        analysis_result = await analyze_image_detailed(photo["data"])
        
        return {
            "success": True,
            "photo_id": photo_id,
            "filename": photo.get("filename", "unknown"),
            "analysis": analysis_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}")

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

    # 재료 정규화
    normalized_ings = normalize_ingredients(ings)
    
    db = get_db()
    cards = await hybrid_recommend(db["recipes"], normalized_ings, top_k=12)

    # 프론트 카드 스키마에 맞춰 변환
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

    # 재료 정규화
    normalized_ings = normalize_ingredients(ings)
    
    db = get_db()
    cards = await hybrid_recommend(db["recipes"], normalized_ings, top_k=12)

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
