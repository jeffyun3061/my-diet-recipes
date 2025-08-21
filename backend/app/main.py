# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init import init_mongo, close_mongo, get_db
from app.api.routes_photo import router as photo_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 MongoDB 연결
    await init_mongo()
    yield
    # 앱 종료 시 연결 해제
    await close_mongo()

app = FastAPI(
    title="My Diet Recipes - API", 
    description="음식 사진 분석 및 레시피 추천 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가 (프론트엔드 연동 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 실제 배포시 특정 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 사진 관련 API 라우터 등록
app.include_router(photo_router)

@app.get("/")
async def root():
    return {
        "ok": True, 
        "message": "My Diet Recipes API is running!",
        "version": "1.0.0",
        "available_features": [
            "사진 업로드 (/photo/upload)",
            "업로드된 사진 목록 (/photo/list)", 
            "사진 삭제 (/photo/delete/{file_id})",
            "서비스 상태 확인 (/photo/health)"
        ],
        "next_features": [
            "업로드된 사진 보기",
            "사진 분석",
            "분석 결과 표시"
        ]
    }

@app.get("/health")
async def health():
    """전체 서비스 헬스체크"""
    db = get_db()
    await db.command("ping")
    return {
        "status": "ok", 
        "database": "connected", 
        "message": "All systems operational"
    }