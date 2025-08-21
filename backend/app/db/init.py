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
    global _client, _db
    _client = AsyncIOMotorClient(_uri())
    _db = _client[_db_name()]
    await _db.command("ping")  # 연결 확인

def get_db():
    if _db is None:
        raise RuntimeError("MongoDB is not initialized yet.")
    return _db

async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
