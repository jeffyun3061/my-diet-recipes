# app/db/init.py
# Mongo 연결 유틸 — motor (on_event용)

from __future__ import annotations
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

async def init_db() -> AsyncIOMotorDatabase:
    # 앱 시작 시 1회 호출해서 전역 커넥션 구성
    global _client, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    name = os.getenv("MONGODB_DB", "mydiet")

    _client = AsyncIOMotorClient(uri)
    _db = _client[name]

    # 연결 확인 (준비 안 됐으면 예외)
    await _db.command("ping")
    return _db

def get_db() -> AsyncIOMotorDatabase:
    #라우터에서 쓰는 핸들. 미초기화면 예외 발생
    if _db is None:
        raise RuntimeError("MongoDB is not initialized yet.")
    return _db

async def close_db() -> None:
    #앱 종료 시 커넥션 정리
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None
