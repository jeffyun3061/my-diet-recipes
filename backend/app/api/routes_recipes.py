# 레시피 검색 — 지용 담당
from fastapi import APIRouter, Query
from app.db.init import get_db

router = APIRouter()

@router.get("/search")
async def search_recipes(q: str = Query("", description="태그 or 제목 검색"), limit: int = 20, skip: int = 0):
    db = get_db()
    cond = {"$or": [{"tags": q}, {"title": {"$regex": q, "$options": "i"}}]} if q else {}
    cursor = db["recipes"].find(cond, {"_id": 0}).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items}
