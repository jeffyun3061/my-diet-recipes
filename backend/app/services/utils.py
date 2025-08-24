# app/services/utils.py
# 재료명 정규화/동의어 처리 유틸
# - Vision이 뽑은 "다진 마늘 2큰술" → "garlic" 같은 검색 키로 수렴
# - 매핑에 없으면 원문(공백 제거, 소문자) 그대로 사용 → 모든 재료 검색 OK

from __future__ import annotations
import re
import unicodedata
from typing import Iterable, List

# 한글 재료명 → 검색용 대표키 (필요시 계속 확장) (영문 slug, 공백제거) 패턴 (매핑 테이블)
_KOR2SLUG = {
    "삼겹살": "porkbelly",
    "돼지고기": "pork",
    "감자": "potato",
    "양파": "onion",
    "대파": "scallion",
    "쪽파": "scallion",
    "파": "scallion",
    "마늘": "garlic",
    "소금": "salt",
    "후추": "pepper",
    "설탕": "sugar",
    "간장": "soysauce",
    "식용유": "oil",
    "버터": "butter",
    "닭가슴살": "chickenbreast",
    "달걀": "egg",
    "계란": "egg",
    "고추장": "gochujang",
    "된장": "doenjang",
    "김치": "kimchi",
    "두부": "tofu",
    "파프리카": "bellpepper",
}

_UNITS = r"(g|kg|ml|l|cup|cups|tsp|tbsp|큰술|작은술|스푼|컵|개|쪽|줌|줌가량|소량|약간)"
_MODIFIERS = r"(다진|썬|채썬|채|간|익힌|삶은|데친|볶은|구운|말린|신선한|잘게|곱게|다듬은|씻은|손질한|통)"
_PUNCT = r"[·•,()\[\]\{\}\-_/\\\.]"

def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

def normalize_name(name: str) -> str:
    
    # 재료 표시 문자열을 검색 키로 정규화.
    # 1) NFKC/소문자 → 구두점 제거 → 수량/단위 제거 → 수식어 제거 → 공백 정리
    # 2) 동의어 매핑(_KOR2SLUG) 적용
    # 3) 남은 공백 제거
    
    s = _nfkc((name or "").strip().lower())

    # 구두점류 제거
    s = re.sub(_PUNCT, " ", s)

    # 숫자+단위 제거 (예: 200g, 1컵, 2 큰술)
    s = re.sub(rf"\b\d+(\.\d+)?\s*{_UNITS}\b", " ", s)

    # 수식어 제거 (예: 다진 마늘 -> 마늘)
    s = re.sub(rf"\b{_MODIFIERS}\b", " ", s)

    # 연결어 제거
    s = re.sub(r"\b(및|그리고|or|and|&)\b", " ", s)

    # 다중 공백 -> 단일 공백
    s = re.sub(r"\s+", " ", s).strip()

    # 동의어/대표키 치환 (있으면)
    s = _KOR2SLUG.get(s, s)

    # 최종 키: 공백 제거
    return s.replace(" ", "")

def normalize_many(names: Iterable[str]) -> List[str]:
    
    # 다수 재료명을 정규화 → 중복 제거 → 정렬
    
    toks = [normalize_name(n) for n in names if isinstance(n, str) and n.strip()]
    uniq = sorted(set(t for t in toks if t))
    return uniq
