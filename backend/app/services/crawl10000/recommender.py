# 목적: 하이브리드 추천
#  교집합 기반 Jaccard(주 점수)
#  임베딩 존재 보너스(+0.15): 임베딩 유무만 반영(간단)
#  식단 태그 가점(+0.05): 예) prefs에서 "lowcarb"로 매핑되면 해당 태그 포함시 보너스
# 확장:
#  - 임베딩 코사인 유사도 반영(벡터DB/Atlas Vector)
#  - 피드백(좋아요/저장)에 따른 가중치 조정

from typing import Dict, Iterable, List, Tuple
from motor.motor_asyncio import AsyncIOMotorCollection

def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

async def hybrid_recommend(
    recipes: AsyncIOMotorCollection,
    detected_slugs: List[str],
    user_diet: str = "",
    top_k: int = 12,
) -> List[Dict]:
    
    # detected_slugs: 비전/LLM에서 감지된 재료 slug 배열
    # user_diet: "lowcarb" 등 내부 태그 문자열(없어도 됨)
  
    # 1차 후보: 정규화 재료 교집합
    cond = {"ingredients.norm": {"$in": list(set(detected_slugs) or ["__none__"])}} if detected_slugs else {}
    candidates = await recipes.find(cond).limit(1000).to_list(length=1000)

    scored: List[Tuple[float, Dict]] = []
    for rec in candidates:
        ing = rec.get("ingredients", {}).get("norm") or []
        j = _jaccard(detected_slugs, ing)

        # 임베딩 존재 여부 보너스(간단)
        has_emb = isinstance(rec.get("embedding"), list) and len(rec["embedding"]) > 10
        emb_score = 0.15 if has_emb else 0.0

        # 식단 태그 보너스
        diet_bonus = 0.0
        if user_diet:
            tags = [t.lower() for t in (rec.get("tags") or [])]
            if user_diet.lower() in tags:
                diet_bonus = 0.05

        score = (0.80 * j) + emb_score + diet_bonus
        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for _, r in scored[:top_k]]

    # 프론트 카드 스키마에 맞춰 축약(이미지/요약/재료/단계)
    out: List[Dict] = []
    for r in top:
        out.append({
            "id": str(r["_id"]),
            "title": r.get("title") or "",
            "description": r.get("summary") or "",
            "ingredients": r.get("ingredients", {}).get("raw") or [],
            "steps": r.get("steps") or [],
            "imageUrl": r.get("image") or "",
            "tags": r.get("tags") or [],
        })
    return out
