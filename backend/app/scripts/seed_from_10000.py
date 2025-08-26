# scripts/seed_from_10000.py
import asyncio
import os
import re
import random
import time
from typing import List, Dict, Any, Iterable
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

# --- 내부 crawler 모듈 경로 호환 (언더스코어/미들하이픈 혼용 대비) -----------------
try:
    from app.services.crawl10000 import crawl_10000_by_ingredients
except ImportError:
    from app.services.crawl_10000 import crawl_10000_by_ingredients

# 재료 정규화(있으면 사용, 없으면 더미)
try:
    from app.services.crawl10000.seed_ing import normalize_ingredients_ko  # 권장 경로
except Exception:
    try:
        from app.services.crawl_10000.seed_ing import normalize_ingredients_ko  # 대체 경로
    except Exception:
        def normalize_ingredients_ko(xs: List[str]) -> List[str]:
            return [x.strip() for x in xs if x and str(x).strip()]

# ---------------------------------------------------------------------------

MONGO  = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DBNAME = os.getenv("MONGODB_DB", "mydiet")

# 동시성(너무 높이면 사이트가 막힐 수 있음)
CONCURRENCY = int(os.getenv("SEED_CONCURRENCY", "6"))
# 한 쿼리당 가져올 개수(크롤러가 limit 지원)
LIMIT_PER_QUERY = int(os.getenv("SEED_LIMIT", "20"))

# 1) 재료 토큰군(동의어/영문 포함) - 골고루 퍼지게 구성
VEGGIES = [
    ["감자", "potato"],
    ["고구마", "sweet potato"],
    ["호박", "애호박", "주키니", "zucchini", "단호박"],
    ["당근", "carrot"],
    ["양파", "대파", "파"],
    ["브로콜리", "broccoli"],
    ["버섯", "표고", "새송이", "느타리", "버섯류"],
    ["토마토", "tomato"],
    ["양배추", "배추", "cabbage"],
    ["가지", "eggplant"],
    ["오이", "cucumber"],
    ["김치"],
]

PROTEINS = [
    ["두부", "tofu"],
    ["계란", "달걀", "egg"],
    ["닭가슴살", "닭다리", "닭고기", "chicken"],
    ["돼지고기", "삼겹살", "목살", "pork"],
    ["소고기", "다짐육", "beef"],
    ["베이컨", "bacon"],
    ["참치", "tuna"],
    ["새우", "shrimp"],
    ["오징어", "squid"],
    ["고등어", "mackerel"],
]

STAPLES = [
    ["밥", "쌀", "rice"],
    ["면", "파스타", "스파게티", "noodle", "pasta"],
    ["떡", "rice cake"],
    ["빵", "bread"],
]

# 2) 조리법/메뉴 카테고리(검색 다양화 + 태그용)
COOK_CATS = [
    "볶음", "국", "찌개", "조림", "구이", "튀김", "찜", "무침",
    "샐러드", "비빔", "전", "수프", "덮밥", "볶음밥", "비빔밥",
    "김밥", "면", "파스타", "카레", "스튜"
]

# 3) 검색 질 확장을 위한 “조합 전략”
#    - 단일 재료
#    - 단일 재료 + 카테고리
#    - 단백질 + 채소
#    - 단백질 + 채소 + 카테고리
def _flatten(groups: List[List[str]]) -> List[str]:
    return [t for g in groups for t in g]

def _base_terms(groups: List[List[str]]) -> Iterable[List[str]]:
    # 각 그룹에서 대표 1~2개만 사용(너무 폭발하지 않도록)
    for g in groups:
        tops = g[:2] if len(g) > 1 else g
        for t in tops:
            yield [t]

def _with_cats(term_lists: Iterable[List[str]]) -> Iterable[List[str]]:
    for tl in term_lists:
        for cat in COOK_CATS:
            yield tl + [cat]

def _pair_terms(A: List[List[str]], B: List[List[str]]) -> Iterable[List[str]]:
    for a in A:
        for b in B:
            yield [a[0], b[0]]

def _pair_with_cats(A: List[List[str]], B: List[List[str]]) -> Iterable[List[str]]:
    for tl in _pair_terms(A, B):
        for cat in COOK_CATS:
            yield tl + [cat]

def build_query_plan() -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []

    # 단일 재료
    for tl in _base_terms(VEGGIES + PROTEINS + STAPLES):
        plan.append({"terms": tl, "tags": []})

    # 단일 재료 + 카테고리
    for tl in _with_cats(_base_terms(VEGGIES + PROTEINS + STAPLES)):
        plan.append({"terms": tl, "tags": []})

    # 단백질 + 채소
    for tl in _pair_terms(PROTEINS, VEGGIES):
        plan.append({"terms": tl, "tags": []})

    # 단백질 + 채소 + 카테고리
    for tl in _pair_with_cats(PROTEINS, VEGGIES):
        plan.append({"terms": tl, "tags": []})

    # 중복 제거(terms 리스트를 문자열로 키화)
    seen = set()
    uniq_plan = []
    for q in plan:
        key = " ".join(q["terms"])
        if key in seen:
            continue
        seen.add(key)
        uniq_plan.append(q)
    return uniq_plan


def make_doc(item: Dict[str, Any], terms: List[str], extra_tags: List[str]) -> Dict[str, Any]:
    # /recipe/123456 → recipe_id 추출
    rid = None
    m = re.search(r"/recipe/(\d+)", str(item.get("url", "")))
    if m:
        rid = m.group(1)

    # 태그: 검색어(정규화) + 사이트 태그 + 카테고리
    norm_terms = normalize_ingredients_ko(terms)
    tags = [*norm_terms, *extra_tags, "만개의레시피"]
    tags = list(dict.fromkeys([t for t in tags if t]))  # uniq & truthy

    return {
        "title": item.get("title") or "",
        "summary": item.get("desc") or "",
        "imageUrl": item.get("thumbnail") or "",
        "tags": tags,
        "ingredients": [],  # 라우터가 상세에서 보강
        "steps": [],
        "source": {"site": "만개의레시피", "url": item.get("url"), "recipe_id": rid},
        "is_recipe": True,
        "seeded_at": datetime.utcnow(),
    }


async def seed_one_query(db, terms: List[str], extra_tags: List[str], limit: int) -> Dict[str, int]:
    # 크롤
    items = await crawl_10000_by_ingredients(terms, tags=[], limit=limit)
    if not items:
        return {"matched": 0, "upserted": 0}

    # 문서화
    docs = [make_doc(it, terms, extra_tags) for it in items if it.get("url")]

    # 벌크 업서트 (source.url 기준)
    ops = []
    for d in docs:
        q = {"source.url": d["source"]["url"]}
        ops.append(UpdateOne(q, {"$setOnInsert": d}, upsert=True))

    matched = 0
    upserted = 0
    if ops:
        res = await db["recipe_cards"].bulk_write(ops, ordered=False)
        matched = res.matched_count or 0
        upserted = len(res.upserted_ids or {})
    return {"matched": matched, "upserted": upserted}


async def create_indexes(db):
    # 중복 방지 + 검색 속도
    await db["recipe_cards"].create_index("source.url", unique=True, name="uniq_source_url")
    await db["recipe_cards"].create_index("source.recipe_id", unique=True, sparse=True, name="uniq_recipe_id")
    await db["recipe_cards"].create_index([("tags", 1)], name="idx_tags")
    await db["recipe_cards"].create_index([("title", "text"), ("summary", "text")], name="txt_title_summary")


async def bounded_gather(sema: asyncio.Semaphore, coro_fn, *args, **kwargs):
    async with sema:
        return await coro_fn(*args, **kwargs)


async def main():
    cli = AsyncIOMotorClient(MONGO)
    db = cli[DBNAME]

    await create_indexes(db)

    # 쿼리 플랜 구성
    plan = build_query_plan()
    random.shuffle(plan)  # 특정 재료로 몰림 방지

    sema = asyncio.Semaphore(CONCURRENCY)
    tasks = []

    print(f"[seed] queries={len(plan)} limit={LIMIT_PER_QUERY} concurrency={CONCURRENCY}")

    for q in plan:
        terms = q["terms"]
        extra_tags = q.get("tags", [])
        tasks.append(
            bounded_gather(sema, seed_one_query, db, terms, extra_tags, LIMIT_PER_QUERY)
        )

    # 요청 사이에 가벼운 지연(사이트 보호 + 차단 방지)
    # NOTE: crawl 함수 내부에서 rate-limit이 없다면 아래 sleep을 더 키워도 됨.
    results = []
    for i in range(0, len(tasks), CONCURRENCY):
        batch = tasks[i : i + CONCURRENCY]
        results += await asyncio.gather(*batch)
        await asyncio.sleep(0.8 + random.random() * 0.7)

    total_upserted = sum(r.get("upserted", 0) for r in results)
    print(f"[seed] done. upserted={total_upserted}, queries_tried={len(plan)}")


if __name__ == "__main__":
    asyncio.run(main())
