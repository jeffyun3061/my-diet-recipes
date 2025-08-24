# 목적: OpenAI 임베딩 저장(선택). 키 없거나 장애 시 조용히 스킵해 운영 안정성 확보.
# 확장: Qdrant/PGVector/Atlas Vector 등 외부 벡터DB로 이동 가능.

import os
from typing import Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection

try:
    from openai import AsyncOpenAI
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if (_OPENAI_OK and OPENAI_API_KEY) else None

def _build_search_text(rec: Dict) -> str:
    # 제목/요약/정규화 재료/태그를 한 문서로 이어붙여 임베딩 입력 생성
    title = rec.get("title") or ""
    summary = rec.get("summary") or ""
    ings = " ".join(rec.get("ingredients", {}).get("norm") or [])
    tags = " ".join(rec.get("tags") or [])
    return f"{title}\n{summary}\n{ings}\n{tags}".strip()

async def embed_text(text: str) -> Optional[List[float]]:
    if not _client:
        return None
    text = (text or "").strip()
    if not text:
        return None
    try:
        emb = await _client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
        return emb.data[0].embedding
    except Exception:
        # 운영 안전: 임베딩 장애는 추천 파이프라인을 막지 않는다
        return None

async def upsert_vector_for_recipe(recipes: AsyncIOMotorCollection, rec_doc: Dict):
    # 레시피 한 건에 embedding 필드를 추가/갱신
    vec = await embed_text(_build_search_text(rec_doc))
    if vec is None:
        return
    await recipes.update_one({"_id": rec_doc["_id"]}, {"$set": {"embedding": vec}})
