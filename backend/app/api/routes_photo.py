<<<<<<< Updated upstream
# app/api/routes_photo.py
import os
import uuid
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
=======
# 사진 업로드/분석/추천 — 시완(분석) + 지용(크롤/점수)
from fastapi import APIRouter, UploadFile, File, Depends, Response, HTTPException
from typing import List
from datetime import datetime
from bson.objectid import ObjectId
from bson.errors import InvalidId  # ObjectId 유효성 검사를 위해 import
from urllib.parse import quote
import logging

from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.photo import PhotoDoc
from app.services.analyze import analyze_labels
from app.services.crawl_10000 import crawl_by_ingredients_norm
from app.services.reco import score_recipe, calc_target_kcal
>>>>>>> Stashed changes

router = APIRouter(prefix="/photo", tags=["photo"])

<<<<<<< Updated upstream
# 업로드 디렉토리 설정
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
=======
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
async def analyze_photo(file: UploadFile = File(...), anon_id: str = Depends(get_or_set_anon_id)):
    # 시완: 여기서 Google Lens/GCV를 붙여서 analyze_labels 내부를 교체하면 됨
    image_bytes = await file.read()
    labels: List[str] = analyze_labels(image_bytes)
>>>>>>> Stashed changes

# 허용되는 이미지 확장자
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_image_file(file: UploadFile) -> None:
    """업로드된 파일 유효성 검증"""
    # 파일 확장자 검증
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 파일 크기 검증
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 크기: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def get_image_info(file_path: str) -> Dict:
    """이미지 기본 정보 추출"""
    try:
        with Image.open(file_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_mb": round(os.path.getsize(file_path) / (1024*1024), 2)
            }
    except Exception as e:
        return {"error": f"이미지 정보 추출 실패: {str(e)}"}

@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(..., description="업로드할 음식 이미지")
) -> Dict:
    """
    1단계: 음식 이미지 업로드
    - 이미지 파일을 서버에 저장
    - 기본 이미지 정보 반환
    """
    # 파일 유효성 검증
    validate_image_file(file)
    
    # 고유한 파일명 생성 (UUID + 원본 확장자)
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower()
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        # 파일 저장
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 이미지 기본 정보 추출
        image_info = get_image_info(file_path)
        
        # 업로드 성공 응답
        return {
            "status": "success",
            "message": "이미지가 성공적으로 업로드되었습니다.",
            "file_id": file_id,
            "original_filename": file.filename,
            "saved_filename": filename,
            "file_path": f"/photo/view/{file_id}",  # 이미지 보기 URL
            "upload_path": file_path,
            "image_info": image_info
        }
        
    except Exception as e:
        # 오류 발생 시 파일 삭제
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/list")
async def get_uploaded_photos() -> Dict:
    """업로드된 이미지 목록 조회"""
    try:
        photos = []
        
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    file_stat = os.stat(file_path)
                    
                    # 파일명에서 UUID 추출 (확장자 제거)
                    file_id = Path(filename).stem
                    
                    photos.append({
                        "file_id": file_id,
                        "filename": filename,
                        "size_mb": round(file_stat.st_size / (1024*1024), 2),
                        "uploaded_at": file_stat.st_ctime,
                        "view_url": f"/photo/view/{file_id}"
                    })
        
        # 최신 업로드 순으로 정렬
        photos.sort(key=lambda x: x['uploaded_at'], reverse=True)
        
        return {
            "status": "success",
            "total_count": len(photos),
            "photos": photos
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 목록 조회 중 오류: {str(e)}"
        )

@router.delete("/delete/{file_id}")
async def delete_photo(file_id: str) -> Dict:
    """업로드된 이미지 삭제"""
    try:
        deleted_files = []
        
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                # file_id로 시작하는 파일 찾기
                if filename.startswith(file_id):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    os.remove(file_path)
                    deleted_files.append(filename)
        
        if not deleted_files:
            raise HTTPException(
                status_code=404,
                detail=f"파일 ID '{file_id}'에 해당하는 파일을 찾을 수 없습니다."
            )
        
        return {
            "status": "success",
            "message": f"{len(deleted_files)}개 파일이 삭제되었습니다.",
            "deleted_files": deleted_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 삭제 중 오류: {str(e)}"
        )

@router.get("/view/{file_id}")
async def view_photo(file_id: str):
    """
    2단계: 업로드된 사진 보기
    - file_id로 이미지 파일을 찾아서 반환
    """
    try:
        # file_id로 시작하는 파일 찾기
        found_file = None
        
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(file_id):
                    found_file = filename
                    break
        
        if not found_file:
            raise HTTPException(
                status_code=404,
                detail=f"파일 ID '{file_id}'에 해당하는 이미지를 찾을 수 없습니다."
            )
        
        file_path = os.path.join(UPLOAD_DIR, found_file)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail="이미지 파일이 존재하지 않습니다."
            )
        
        # 이미지 파일 반환
        return FileResponse(
            file_path,
            media_type="image/jpeg",
            filename=found_file
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 조회 중 오류: {str(e)}"
        )

@router.get("/info/{file_id}")
async def get_photo_info(file_id: str) -> Dict:
    """특정 이미지의 상세 정보 조회"""
    try:
        # file_id로 시작하는 파일 찾기
        found_file = None
        
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(file_id):
                    found_file = filename
                    break
        
        if not found_file:
            raise HTTPException(
                status_code=404,
                detail=f"파일 ID '{file_id}'에 해당하는 이미지를 찾을 수 없습니다."
            )
        
        file_path = os.path.join(UPLOAD_DIR, found_file)
        file_stat = os.stat(file_path)
        image_info = get_image_info(file_path)
        
        return {
            "status": "success",
            "file_id": file_id,
            "filename": found_file,
            "file_path": f"/photo/view/{file_id}",
            "upload_date": file_stat.st_ctime,
            "size_mb": round(file_stat.st_size / (1024*1024), 2),
            "image_info": image_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 정보 조회 중 오류: {str(e)}"
        )

@router.get("/health")
async def photo_service_health():
    """사진 업로드 서비스 상태 확인"""
    return {
        "status": "ok",
        "service": "photo_upload",
        "upload_directory": UPLOAD_DIR,
        "upload_dir_exists": os.path.exists(UPLOAD_DIR),
        "max_file_size_mb": MAX_FILE_SIZE // (1024*1024),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "message": "사진 업로드 서비스가 정상 작동 중입니다."
    }