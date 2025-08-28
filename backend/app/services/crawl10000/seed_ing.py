# app/services/crawl10000/seed_ing.py
# 목적: (1) 재료 문자열 → 토큰 정규화, (2) Mongo 업서트, (3) 인덱스 생성

import re
from typing import Dict, List, Optional, Set
from motor.motor_asyncio import AsyncIOMotorCollection

from app.models.tags import (
    canonicalize_token_ko, extract_words, is_stop,
)

# --- slug 매핑(영문/내부용) ----------------------------------------------------
_KOR2SLUG = {
    "삼겹살":"porkbelly","돼지고기":"pork","감자":"potato","양파":"onion",
    "대파":"scallion","파":"scallion","마늘":"garlic","소금":"salt",
    "후추":"pepper","설탕":"sugar","간장":"soy_sauce","식용유":"oil",
    "버터":"butter","닭가슴살":"chickenbreast","닭고기":"chicken",
    "달걀":"egg","계란":"egg","고추장":"gochujang","된장":"doenjang",
    "김치":"kimchi","두부":"tofu","파프리카":"bellpepper",
    "고구마":"sweetpotato","당근":"carrot","오이":"cucumber",
    "브로콜리":"broccoli","가지":"eggplant","버섯":"mushroom",
    "호박":"pumpkin","단호박":"pumpkin","애호박":"pumpkin","zucchini":"pumpkin",
}

def kor_to_slug(token: str) -> Optional[str]:
    token = (token or "").strip()
    if not token:
        return None
    if token in _KOR2SLUG:
        return _KOR2SLUG[token]
    if re.fullmatch(r"[a-zA-Z_]+", token):
        return token.lower()
    t = re.sub(r"[\s·,()/\[\]-]+", "", token)
    return _KOR2SLUG.get(t) or None

# --- 정규화: KO/slug 모두 만들기 ----------------------------------------------
def normalize_ingredients_ko(raws: List[str]) -> List[str]:
    seen, out = set(), []
    for line in raws or []:
        for w in extract_words(line):
            canon = canonicalize_token_ko(w)
            if canon and canon not in seen and not is_stop(canon):
                seen.add(canon); out.append(canon)
    return out

def normalize_ingredients_slug(raws: List[str]) -> List[str]:
    seen, out = set(), []
    for line in raws or []:
        for w in extract_words(line):
            slug = kor_to_slug(w)
            if slug and slug not in seen:
                seen.add(slug); out.append(slug)
    return out

# --- 인덱스/업서트 -------------------------------------------------------------
async def ensure_indexes(recipes: AsyncIOMotorCollection):
    await recipes.create_index("url",
        unique=True, background=True, sparse=True,
        partialFilterExpression={"url": {"$type": "string", "$ne": ""}},
        name="url_1")
    await recipes.create_index("title", background=True)
    await recipes.create_index("ingredients.norm_ko", background=True)
    await recipes.create_index("ingredients.norm_slug", background=True)
    await recipes.create_index([("tags", 1)], background=True)

async def upsert_recipe(recipes: AsyncIOMotorCollection, doc: Dict) -> str:
    raws = doc.get("ingredients_raw") or []
    norm_ko   = normalize_ingredients_ko(raws)
    norm_slug = normalize_ingredients_slug(raws)
    payload = {
        "url": doc.get("url",""),
        "title": doc.get("title") or "",
        "summary": doc.get("summary") or "",
        "steps": doc.get("steps") or [],
        "image": doc.get("image") or "",
        "tags": doc.get("tags") or [],
        "ingredients": {"raw": raws, "norm_ko": norm_ko, "norm_slug": norm_slug},
    }
    res = await recipes.update_one({"url": payload["url"]}, {"$set": payload}, upsert=True)
    rid = res.upserted_id
    if not rid:
        one = await recipes.find_one({"url": payload["url"]}, {"_id": 1})
        rid = one and one["_id"]
    return str(rid)

def normalize_ingredients(items):  # backwards compat
    return normalize_ingredients_ko(items)
