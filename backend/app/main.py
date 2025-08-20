# app/main.py
# FastAPI 엔트리 — 초기화/종료 훅 분리, CORS, 라우터 등록

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# DB 연결/종료 + 인덱스 생성
from app.db.init import init_mongo, close_mongo, get_db
from app.db.indexes import ensure_indexes

# 팀별 라우터
from app.api.routes_prefs import router as prefs_router      # 가람: 사용자 입력/저장/조회
from app.api.routes_photo import router as photo_router      # 시완: 사진 업로드/분석/추천
from app.api.routes_recipes import router as recipes_router  # 지용: 레시피 검색/확장

app = FastAPI(title="My Diet Recipes - API")

# CORS (프론트 로컬 개발 편의; 배포 시 도메인 제한 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # TODO: 배포 시 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 앱 라이프사이클: ----------
@app.on_event("startup")
async def on_startup():
    # 1) Mongo 연결
    await init_mongo()
    # 2) 인덱스 보장 (await 필수)
    await ensure_indexes()

@app.on_event("shutdown")
async def on_shutdown():
    # 종료 시 연결 닫기
    await close_mongo()
# ---------------------------------------------------

# 헬스체크/루트
@app.get("/")
async def root():
    return {"ok": True, "message": "API is up"}

@app.get("/health")
async def health():
    db = get_db()
    await db.command("ping")
    return {"status": "ok", "db": "ok"}

# 라우터 등록 (역할별로 분리)
app.include_router(prefs_router,   prefix="/preferences", tags=["preferences"])  # 가람
app.include_router(photo_router,   prefix="/photo",       tags=["photo"])        # 시완(+지용)
app.include_router(recipes_router, prefix="/recipes",     tags=["recipes"])      # 지용
