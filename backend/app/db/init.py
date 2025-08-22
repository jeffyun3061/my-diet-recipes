# app/db/init.py
import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = None
_db = None

def _uri() -> str:
    # 로컬: mongodb://localhost:27017 / 도커: mongodb://mongo:27017
    return os.getenv("MONGODB_URI") or "mongodb://localhost:27017"

def _db_name() -> str:
    return os.getenv("MONGODB_DB") or "mydiet"

async def init_mongo() -> None:
    # 앱 시작 시 한 번 호출되어 Mongo 연결
    global _client, _db
    if _db is not None:
        return
    _client = AsyncIOMotorClient(_uri())
    _db = _client[_db_name()]
    # 연결 확인
    await _db.command("ping")

def get_db():
    # 라우트/서비스에서 DB 객체를 가져갈 때 사용
    if _db is None:
        raise RuntimeError("MongoDB is not initialized yet.")
    return _db

async def close_mongo() -> None:
    # 앱 종료 시 연결 닫기
    global _client
    if _client is not None:
        _client.close()
        _client = None
