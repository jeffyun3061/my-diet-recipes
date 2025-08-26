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

def _regex_union(words: List[str]) -> re.Pattern:
    safe = [re.escape(w.strip()) for w in (words or []) if w and w.strip()]
    if not safe:
        safe = ["$"]  # 매치 불가
    return re.compile("|".join(safe), re.I)

def _match_count(text: str, pats: List[re.Pattern]) -> int:
    if not text:
        return 0
    return sum(1 for p in pats if p.search(text))

def _arr_to_text(v: Any) -> str:
    """
    - list[str] → "a b c"
    - dict -> values 중 list/str만 평탄화
    - 그 외 -> str(v)
    """
    if isinstance(v, list):
        return " ".join(str(x) for x in v if x)
    if isinstance(v, dict):
        parts: List[str] = []
        for val in v.values():
            if isinstance(val, list):
                parts.extend(str(x) for x in val if x)
            elif isinstance(val, str):
                parts.append(val)
        return " ".join(parts)
    return str(v or "")

# --- 하이브리드 추천 --------------------------------------------------------

async def hybrid_recommend(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    ingredients: List[str],
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    입력 토큰(정규화된 재료명)이 문서(제목/태그/재료)에 등장하는지로 1차 필터·랭킹.
    - 감자 같은 하드코딩/폴백 없음
    - 정규식 매칭 기반 가중 점수로 정렬
    - 결과 부족 시 '품질 보강'으로 채움(중복 방지)
    - 스키마 혼종(ingredients가 배열/문서) 모두 지원
    """
    col = db["recipe_cards"]

    # 0) 토큰 준비
    tokens = [t for t in (ingredients or []) if t]
    if not tokens:
        return []
    pats = _compile_terms(tokens)
    rx_union = _regex_union(tokens)

    # 1) 1차 후보 쿼리 (배열/스칼라/중첩 경로 모두 커버)
    # 배열 필드는 {field: /regex/} 만으로 요소 매칭이 됨.
    # dict 스키마는 하위 경로로 직접 지정.
    q = {
        "$or": [
            {"ingredients_full": rx_union},            # array[str]
            {"ingredients_clean": rx_union},           # array[str]
            {"ingredients": rx_union},                 # array[str] (레거시)
            {"ingredients.raw": rx_union},             # dict{ raw: array[str] }
            {"ingredients.norm_ko": rx_union},         # dict{ norm_ko: array[str] }  ← KO 정규화
            {"ingredients.norm_slug": rx_union},       # dict{ norm_slug: array[str] }
            {"tags": rx_union},                        # array[str]
            {"chips": rx_union},                       # array[str]
            {"title": rx_union},                       # str
            {"summary": rx_union},                     # str (보조)
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

    # 2) 스코어링: 제목 > 태그/칩 > 재료들 > 요약 (+풀 필드 보유 가점)
    def score(d: Dict[str, Any]) -> float:
        title = d.get("title") or ""
        tags  = _arr_to_text(d.get("tags"))
        chips = _arr_to_text(d.get("chips"))

        ings_text = " ".join([
            _arr_to_text(d.get("ingredients_full")),
            _arr_to_text(d.get("ingredients_clean")),
            # ingredients가 배열 혹은 dict 모두 커버
            _arr_to_text(d.get("ingredients")),
            _arr_to_text(d.get("ingredients", {}).get("raw") if isinstance(d.get("ingredients"), dict) else None),
            _arr_to_text(d.get("ingredients", {}).get("norm_ko") if isinstance(d.get("ingredients"), dict) else None),
            _arr_to_text(d.get("ingredients", {}).get("norm_slug") if isinstance(d.get("ingredients"), dict) else None),
        ])
        summ  = d.get("summary") or ""

        s  = 3.0 * _match_count(title, pats)
        s += 2.0 * _match_count(f"{tags} {chips}", pats)
        s += 1.2 * _match_count(ings_text, pats)
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
