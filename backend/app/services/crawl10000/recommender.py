# app/services/crawl10000/recommender.py
from __future__ import annotations
from typing import List, Dict, Any
import re
import motor.motor_asyncio

# -----------------------------------------------------------------------------
# 하이브리드 추천 (정규화된 재료 토큰 기반 정규식 매칭 + AND 우선 재정렬)
# - 입력 토큰이 실제로 등장하는 카드만 반환
# - 배열/문서 혼합 스키마(ingredients가 list 또는 dict) 모두 지원
# - 제목/태그/칩/재료/요약에 대한 매칭 개수를 점수로 환산해 정렬
# - "모든 토큰이 등장(AND)" 문서를 먼저, 그 외(OR 매칭)는 보충으로 뒤에 배치
# -----------------------------------------------------------------------------

def _regex_union(words: List[str]) -> re.Pattern:
    """토큰들을 안전 이스케이프 후 OR 정규식으로 묶음. 토큰 없으면 매치 불가 패턴."""
    safe = [re.escape(w.strip()) for w in (words or []) if w and w.strip()]
    if not safe:
        safe = ["$"]  # 매치 불가
    return re.compile("|".join(safe), re.I)

def _as_text(v: Any) -> str:
    """
    - list[str] → "a b c"
    - dict     → values 중 list/str만 평탄화
    - 기타     → str(v)
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

def _searchable_text(doc: Dict[str, Any]) -> str:
    """AND 판정을 위해 문서의 주요 검색 필드를 하나의 문자열로 합침."""
    title = doc.get("title") or ""
    tags  = _as_text(doc.get("tags"))
    chips = _as_text(doc.get("chips"))
    summ  = doc.get("summary") or ""
    ings_text = " ".join([
        _as_text(doc.get("ingredients_full")),
        _as_text(doc.get("ingredients_clean")),
        _as_text(doc.get("ingredients")),
        _as_text(doc.get("ingredients", {}).get("raw") if isinstance(doc.get("ingredients"), dict) else None),
        _as_text(doc.get("ingredients", {}).get("norm_ko") if isinstance(doc.get("ingredients"), dict) else None),
        _as_text(doc.get("ingredients", {}).get("norm_slug") if isinstance(doc.get("ingredients"), dict) else None),
    ])
    return " ".join([title, tags, chips, ings_text, summ])

def _contains_all(doc: Dict[str, Any], tokens: List[str]) -> bool:
    """모든 토큰이 문서 텍스트에 등장하는지(AND) 체크."""
    if not tokens:
        return False
    text = _searchable_text(doc)
    return all(re.search(re.escape(t), text, re.I) for t in tokens)

def _score(doc: Dict[str, Any], tokens: List[str]) -> float:
    """
    단순: 토큰이 등장한 필드 수/횟수로 점수화.
    - 제목 가중치 > 태그/칩 > 재료들 > 요약
    - 풀 필드 보유(steps_full/ingredients_full) 약간 가점
    """
    title = doc.get("title") or ""
    tags  = _as_text(doc.get("tags"))
    chips = _as_text(doc.get("chips"))
    summ  = doc.get("summary") or ""

    ings_text = " ".join([
        _as_text(doc.get("ingredients_full")),
        _as_text(doc.get("ingredients_clean")),
        _as_text(doc.get("ingredients")),
        _as_text(doc.get("ingredients", {}).get("raw") if isinstance(doc.get("ingredients"), dict) else None),
        _as_text(doc.get("ingredients", {}).get("norm_ko") if isinstance(doc.get("ingredients"), dict) else None),
        _as_text(doc.get("ingredients", {}).get("norm_slug") if isinstance(doc.get("ingredients"), dict) else None),
    ])

    s = 0.0
    for t in (tokens or []):
        pat = re.compile(re.escape(t), re.I)
        if pat.search(title):                 s += 2.0
        if pat.search(f"{tags} {chips}"):     s += 1.5
        if pat.search(ings_text):             s += 1.2
        if pat.search(summ):                  s += 0.5

    if doc.get("steps_full") or doc.get("ingredients_full"):
        s += 0.2
    return s

async def hybrid_recommend(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    ingredients: List[str],
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    입력 토큰(정규화된 재료명)이 문서(제목/태그/칩/재료/요약)에 등장하는지로 필터·랭킹.
    - 감자 같은 하드코딩/폴백 없음
    - 무관한 카드 보강 없음 (매칭된 것만 반환)
    - 다중 재료 입력 시: 모든 토큰이 등장하는 문서(AND)를 먼저, 나머지(OR)는 뒤에
    """
    col = db["recipe_cards"]

    # 0) 토큰 준비
    tokens = [t.strip() for t in (ingredients or []) if t and t.strip()]
    if not tokens:
        return []

    rx = _regex_union(tokens)

    # 1) 후보 쿼리: 배열/스칼라/중첩 경로 모두 커버
    q = {
        "$or": [
            {"ingredients_full": rx},            # array[str]
            {"ingredients_clean": rx},           # array[str]
            {"ingredients": rx},                 # array[str] (레거시)
            {"ingredients.raw": rx},             # dict{ raw: array[str] }
            {"ingredients.norm_ko": rx},         # dict{ norm_ko: array[str] }
            {"ingredients.norm_slug": rx},       # dict{ norm_slug: array[str] }
            {"tags": rx},                        # array[str]
            {"chips": rx},                       # array[str]
            {"title": rx},                       # str
            {"summary": rx},                     # str
        ]
    }

    proj = {
        "_id": 1,
        "title": 1, "summary": 1, "imageUrl": 1,
        "tags": 1, "chips": 1,
        "ingredients": 1, "ingredients_full": 1, "ingredients_clean": 1,
        "steps": 1, "steps_full": 1,
    }

    # 2) 후보 로드 (넓게)
    docs = await col.find(q, proj).limit(800).to_list(length=800)

    if not docs:
        return []

    # 3) AND 우선 분리
    #    모든 토큰이 등장하는 문서(must) / 일부만 등장(rest)
    must_docs = [d for d in docs if _contains_all(d, tokens)]
    must_ids = {str(d.get("_id")) for d in must_docs}
    rest_docs = [d for d in docs if str(d.get("_id")) not in must_ids]

    # 4) 각 그룹 내부 점수화 + 정렬
    must_sorted = sorted(must_docs, key=lambda d: _score(d, tokens), reverse=True)
    rest_sorted = sorted(rest_docs, key=lambda d: _score(d, tokens), reverse=True)

    # 5) 병합 후 상위 limit 반환
    return (must_sorted + rest_sorted)[:limit]
