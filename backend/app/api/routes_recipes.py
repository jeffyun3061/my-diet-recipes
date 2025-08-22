# app/api/routes_recipes.py
# 목적: 프론트에서 재료/태그를 보내면 즉시 크롤해서 후보 레시피를 반환한다.

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.crawl_10000 import crawl_10000_by_ingredients
# 올바른 임포트: from app.services.crawl_10000 import crawl_10000_by_ingredients

router = APIRouter()

class CrawlIn(BaseModel):
    ingredients: List[str] = Field(..., example=["돼지고기", "감자", "계란"])
    tags: List[str] = Field(default_factory=lambda: ["다이어트"])
    limit: int = Field(12, ge=1, le=30)

class RecipeItem(BaseModel):
    title: str
    url: str
    desc: Optional[str] = None
    thumbnail: Optional[str] = None
    timeMin: Optional[int] = None
    source: dict
    score: float

class CrawlOut(BaseModel):
    query_terms: List[str]
    total: int
    items: List[RecipeItem]

@router.post("/crawl", response_model=CrawlOut)
async def crawl(inb: CrawlIn):
    # 크롤 서비스 호출
    items = await crawl_10000_by_ingredients(inb.ingredients, inb.tags, inb.limit)
    return {
        "query_terms": [*inb.ingredients, *inb.tags],
        "total": len(items),
        "items": items
    }
