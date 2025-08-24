# app/main.py
# FastAPI 앱 초기화 및 라우터 설정
# 라우터는 각 기능별로 분리하여 관리

from __future__ import annotations

from asyncio import sleep
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_prefs import router as prefs_router       # 가람: 사용자 입력/저장/조회
from app.api.routes_recipes import router as recipes_router   # 지용: 레시피 검색/확장
from app.api.routes_crawl import router as crawl_router     # 지용: 크롤링/ETL/임베딩

try:
    from app.api.routes_photo import router as photo_router   # 지용: 사진 분석/추천
    _HAS_PHOTO = True
except Exception:
    _HAS_PHOTO = False

# DB 초기화/인덱스
# init_db/close_db: 앱 시작/종료 시 커넥션 생성/정리
# get_db: 런타임에 DB 핸들 얻기
try:
    from app.db.init import get_db, init_db, close_db
    from app.db.indexes import ensure_indexes
except Exception:  # 초기 부팅 유연성
    get_db = None
    init_db = None
    close_db = None
    ensure_indexes = None

app = FastAPI(title="My Diet Recipes - API", version="0.1.0")

# CORS: 프론트 localhost:3000 허용 + 쿠키 전달
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # 필요 시 5173 등 추가
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 앱 시작/종료 이벤트 핸들러
@app.on_event("startup")
async def on_startup() -> None:
    # 1) DB 먼저 붙는다 (최대 20회, 1초 간격)
    db = None
    if init_db:
        for i in range(20):
            try:
                db = await init_db()
                print("[startup] db ready")
                break
            except Exception as e:
                print(f"[startup] db init retry {i+1}: {e}")
                await sleep(1.0)
        if db is None:
            print("[startup] db init failed after retries")
            return

    # 2) 인덱스 보장
    if ensure_indexes and db is not None:
        try:
            await ensure_indexes()
            print("[startup] indexes ensured")
        except Exception as e:
            print(f"[startup] ensure_indexes failed: {e}")

@app.on_event("shutdown")
async def on_shutdown() -> None:
    # 몽고db 커넥션 정리
    if close_db:
        try:
            await close_db()
        except Exception:
            pass

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/health")
async def health():
    # 간단한 헬스체크(필요하면 DB ping 추가)
    ok = {"status": "ok", "db": "skip"}
    if get_db:
        try:
            db = get_db()
            # 필요 시 MongoDB ping
            await db.command("ping")
            ok["db"] = "ok"
        except Exception as e:
            ok["db"] = f"error: {e}"
    return ok

# 라우터 prefix는 각 파일 내에서 정의함 , 중복 prefix 금지
app.include_router(prefs_router)
app.include_router(recipes_router)
app.include_router(crawl_router)

if _HAS_PHOTO:
    app.include_router(photo_router)
