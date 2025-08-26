# app/services/crawl10000/recommender.py
from __future__ import annotations
from typing import List, Dict, Any
import re
import motor.motor_asyncio

# --- 내부 헬퍼 ---------------------------------------------------------------

def _compile_terms(words: List[str]) -> List[re.Pattern]:
    # 비어있는/공백 토큰 제거 후 안전 이스케이프
    terms = [w.strip() for w in (words or []) if w and w.strip()]
    return [re.compile(re.escape(t), re.I) for t in terms]

def _match_count(text: str, pats: List[re.Pattern]) -> int:
    if not text:
        return 0
    return sum(1 for p in pats if p.search(text))

def _arr_to_text(arr: Any) -> str:
    if isinstance(arr, list):
        return " ".join(str(x) for x in arr if x)
    return str(arr or "")

# --- 하이브리드 추천 --------------------------------------------------------

async def hybrid_recommend(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    ingredients: List[str],
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    입력 토큰(정규화된 재료명)이 실제 문서(제목/태그/재료)에 등장하는지로 1차 필터·랭킹.
    - 감자 같은 하드코딩/폴백 없음
    - regex 매칭 기반 가중 점수로 정렬
    - 결과 부족 시 '품질 보강'으로만 채움(중복 방지)
    """
    col = db["recipe_cards"]

    # 0) 토큰 준비
    tokens = [t for t in (ingredients or []) if t]
    if not tokens:
        return []
    pats = _compile_terms(tokens)

    # 1) 1차 후보: 토큰이 하나라도 매칭되는 문서
    #    배열 필드는 $elemMatch + $regex, 스칼라는 $regex
    rx_union = re.compile("|".join(re.escape(t) for t in tokens), re.I)
    q = {
        "$or": [
            {"ingredients_full":  {"$elemMatch": {"$regex": rx_union}}},
            {"ingredients_clean": {"$elemMatch": {"$regex": rx_union}}},
            {"ingredients":       {"$elemMatch": {"$regex": rx_union}}},
            {"tags":              {"$elemMatch": {"$regex": rx_union}}},
            {"chips":             {"$elemMatch": {"$regex": rx_union}}},
            {"title":             {"$regex": rx_union}},
        ]
    }
    proj = {
        "_id": 1,
        "title": 1, "summary": 1, "imageUrl": 1,
        "tags": 1, "chips": 1,
        "ingredients": 1, "ingredients_full": 1, "ingredients_clean": 1,
        "steps": 1, "steps_full": 1,
    }
    docs = await col.find(q, proj).limit(400).to_list(length=400)

    # 2) 스코어링: 제목 > 태그/칩 > 재료들 > 요약
    #    토큰이 들어가면 1점씩 가산(필드별 가중치 적용)
    def score(d: Dict[str, Any]) -> float:
        title = d.get("title") or ""
        tags  = _arr_to_text(d.get("tags"))
        chips = _arr_to_text(d.get("chips"))
        ings  = " ".join([
            _arr_to_text(d.get("ingredients_full")),
            _arr_to_text(d.get("ingredients_clean")),
            _arr_to_text(d.get("ingredients")),
        ])
        summ  = d.get("summary") or ""

        s  = 3.0 * _match_count(title, pats)
        s += 2.0 * _match_count(f"{tags} {chips}", pats)
        s += 1.2 * _match_count(ings, pats)
        s += 0.5 * _match_count(summ, pats)

        # 데이터 품질 보정(풀 텍스트가 있으면 소폭 가점)
        if d.get("steps_full") or d.get("ingredients_full"):
            s += 0.2
        return s

    ranked = sorted(docs, key=score, reverse=True)

    # 3) 결과 부족 시 품질 보강(매칭 없는 문서로 채우되 앞 순위는 그대로 유지)
    out: List[Dict[str, Any]] = ranked[:limit]
    if len(out) < limit:
        need = limit - len(out)
        seen_ids = {str(x["_id"]) for x in out}
        # 품질 조건: 이미지/요약/풀스텝 중 일부라도 있는 카드 우선
        fill_q = {
            "$or": [
                {"imageUrl": {"$ne": None}},
                {"summary": {"$ne": ""}},
                {"steps_full.0": {"$exists": True}},
            ]
        }
        rest = await col.find(fill_q, proj).limit(limit * 2).to_list(length=limit * 2)
        for r in rest:
            rid = str(r["_id"])
            if rid in seen_ids:
                continue
            out.append(r)
            seen_ids.add(rid)
            if len(out) >= limit:
                break

    return out[:limit]
