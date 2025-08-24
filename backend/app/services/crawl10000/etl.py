# 목적: (1) 재료 문자열 → 토큰(slug) 정규화, (2) Mongo 업서트, (3) 인덱스 생성
# 특징: 토큰 규칙이 단순해도 시드가 넓으면 교집합 매칭은 충분히 동작
# 확장: _KOR2SLUG 사전 확장 / 동의어 테이블을 컬렉션으로 분리 가능

import re
from typing import Dict, List, Optional, Set
from motor.motor_asyncio import AsyncIOMotorCollection

# 기본 매핑(초기 커버) — 부족하면 점진적으로 확장
_KOR2SLUG = {
    "삼겹살": "porkbelly", "돼지고기": "pork", "감자": "potato", "양파": "onion",
    "대파": "scallion", "파": "scallion", "마늘": "garlic", "소금": "salt",
    "후추": "pepper", "설탕": "sugar", "간장": "soy_sauce", "식용유": "oil",
    "버터": "butter", "닭가슴살": "chickenbreast", "닭고기": "chicken",
    "달걀": "egg", "계란": "egg", "고추장": "gochujang", "된장": "doenjang",
    "김치": "kimchi", "두부": "tofu", "파프리카": "bellpepper",
    "고구마": "sweetpotato", "당근": "carrot", "오이": "cucumber",
    "브로콜리": "broccoli", "가지": "eggplant", "버섯": "mushroom",
}

def kor_to_slug(token: str) -> Optional[str]:
    # 한글/영문 토큰을 내부 slug로 통일
    token = (token or "").strip()
    if not token:
        return None
    if token in _KOR2SLUG:
        return _KOR2SLUG[token]
    if re.fullmatch(r"[a-zA-Z_]+", token):
        return token.lower()
    # 공백/기호 제거 후 재매핑 시도
    t = re.sub(r"[\s·,()/\[\]-]+", "", token)
    return _KOR2SLUG.get(t) or None

def extract_ingredient_tokens(line: str) -> List[str]:
    # 양파(다진 것) 100g' → ['양파', '다진', ...] 같은 형태로 토큰 후보 추출
    line = re.sub(r"\([^)]*\)", " ", line)
    line = re.sub(r"\d+[gml컵스푼큰작티]+", " ", line, flags=re.IGNORECASE)
    line = re.sub(r"[0-9]+", " ", line)
    parts = re.split(r"[,\s]+", line)
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if p and len(p) <= 20:
            out.append(p)
    return out

def normalize_ingredients(raws: List[str]) -> List[str]:
    # 재료 문자열 배열 → slug 집합(정렬)
    found: Set[str] = set()
    for line in raws or []:
        for token in extract_ingredient_tokens(line):
            slug = kor_to_slug(token)
            if slug:
                found.add(slug)
    return sorted(found)

async def ensure_indexes(recipes: AsyncIOMotorCollection):
    # URL 유니크 인덱스(문서에 url이 '문자열'로 있을 때만) + sparse
    await recipes.create_index(
        "url",
        unique=True,
        background=True,
        sparse=True,
        partialFilterExpression={"url": {"$type": "string", "$ne": ""}},
        name="url_1",
    )
    await recipes.create_index("title", background=True)
    await recipes.create_index("ingredients.norm", background=True)
    await recipes.create_index([("tags", 1)], background=True)

async def upsert_recipe(recipes: AsyncIOMotorCollection, doc: Dict) -> str:
    # url 기준 업서트. 임베딩은 별도 단계에서 처리
    norm = normalize_ingredients(doc.get("ingredients_raw") or [])
    payload = {
        "url": doc["url"],
        "title": doc.get("title") or "",
        "summary": doc.get("summary") or "",
        "steps": doc.get("steps") or [],
        "image": doc.get("image") or "",
        "tags": doc.get("tags") or [],
        "ingredients": {"raw": doc.get("ingredients_raw") or [], "norm": norm},
    }
    res = await recipes.update_one({"url": doc["url"]}, {"$set": payload}, upsert=True)
    rid = res.upserted_id
    if not rid:
        one = await recipes.find_one({"url": doc["url"]}, {"_id": 1})
        rid = one and one["_id"]
    return str(rid)
