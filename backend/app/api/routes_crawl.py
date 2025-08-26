# app/api/routes_crawl.py
# 레시피 크롤링/시드 — 지용 담당

from __future__ import annotations
from typing import Dict, Any, List
import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.init import get_db
from app.services.crawl_10000 import crawl_recipes

router = APIRouter(prefix="/crawl", tags=["crawl"])

class CrawlResponse(BaseModel):
    ok: bool
    inserted: int
    message: str

@router.post("/seed", response_model=CrawlResponse)
async def seed_recipes(
    q: str = Query(..., description="검색어 (예: 감자, 양파, 마늘, 가지)"),
    pages: int = Query(1, ge=1, le=5, description="수집 페이지 수 (권장 1-2)")
):
    """만개의레시피 검색 결과 크롤링 → 정규화/업서트 → (선택)임베딩 저장"""
    
    if not q.strip():
        raise HTTPException(status_code=400, detail="검색어가 필요합니다")
    
    try:
        db = get_db()
        
        # 크롤링 실행
        inserted_count = await crawl_recipes(db, q.strip(), pages)
        
        return CrawlResponse(
            ok=True,
            inserted=inserted_count,
            message=f"'{q}' 검색 결과 {inserted_count}개 레시피가 저장되었습니다"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 오류: {str(e)}")

@router.post("/batch-seed")
async def batch_seed_recipes(
    queries: List[str] = Query(..., description="검색어 목록"),
    pages_per_query: int = Query(1, ge=1, le=3, description="검색어당 페이지 수")
):
    """여러 검색어를 한 번에 크롤링"""
    
    if not queries:
        raise HTTPException(status_code=400, detail="검색어 목록이 필요합니다")
    
    try:
        db = get_db()
        total_inserted = 0
        results = []
        
        # 각 검색어별로 크롤링 실행
        for query in queries:
            try:
                inserted = await crawl_recipes(db, query.strip(), pages_per_query)
                total_inserted += inserted
                results.append({
                    "query": query,
                    "inserted": inserted,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "query": query,
                    "inserted": 0,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "ok": True,
            "total_inserted": total_inserted,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 크롤링 오류: {str(e)}")
