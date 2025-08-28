# 목적: 운영 중 DB에 레시피 시드를 빠르게/안전하게 채우기 위한 관리용 API
# 사용: POST /crawl/seed?q=감자&pages=2 → {"ok": true, "inserted": N}

from fastapi import APIRouter, HTTPException, Query, Depends
from app.db.init import get_db

from app.services.crawl10000.crawler import crawl_query
from app.services.crawl10000.seed_ing import ensure_indexes, upsert_recipe
from app.services.crawl10000.embeddings import upsert_vector_for_recipe

router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.post("/seed")
async def crawl_seed(
    q: str = Query(..., description="검색어 (예: 감자, 양파, 마늘 등)"),
    pages: int = Query(1, ge=1, le=5, description="검색 페이지 수(과도 수집 방지)"),
    db = Depends(get_db),
):
    
    # 만개의레시피 검색 결과 → 상세 페이지 파싱 → 정규화/업서트 → (선택)임베딩 저장
    # 임베딩은 OPENAI_API_KEY 없으면 자동 스킵(오류 없이 진행)

    try:
        recipes = db["recipes"]
        await ensure_indexes(recipes)

        docs = await crawl_query(q, pages=pages)
        inserted = 0
        for d in docs:
            # Mongo에 upsert (url 기준)
            await upsert_recipe(recipes, d)
            # upsert 이후 문서 재조회 (embedding은 _id 필요)
            rdoc = await recipes.find_one({"url": d["url"]})
            if rdoc:
                await upsert_vector_for_recipe(recipes, rdoc)
                inserted += 1

        return {"ok": True, "inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
