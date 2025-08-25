# app/models/tags.py
from typing import List

# 표준 태그(서비스 전역 동일 표기)
CANON = {
    # 주재료(예시는 최소만. 점진적으로 늘리면 됨)
    "main":   ["감자", "토마토", "치즈", "모짜렐라", "파마산", "파슬리"],

    # 조리법/열원
    "method": [
        "팬프라이", "팬구이", "굽기", "볶음", "튀김",
        "삶기", "데치기", "찌기", "끓이기",
        "오븐구이", "에어프라이어"
    ],

    # 요리 형태/메뉴 타입
    "form": [
        "감자칩", "패티/전", "웨지",
        "국", "찌개", "전골", "조림", "무침", "찜",
        "볶음밥", "덮밥", "비빔", "샐러드",
        "면", "파스타", "스프", "샌드위치"
    ],

    # 시간/특성
    "time": ["30분이내", "15분이내"],
    "feature": ["바삭함", "간식", "술안주", "쉬움", "저지방", "오일절감"]
}

PRIORITY = ["main", "method", "form", "time", "feature"]

# 카드 표시 길이 제한
MAX_TAGS = 4
MAX_TITLE = 14
MAX_SUBTITLE = 18
MAX_SUMMARY = 70 #기존 80
MAX_STEP_LINES = 3
MAX_STEP_TEXT = 48 #기존 60

def is_valid(tag: str) -> bool:
    return any(tag in vals for vals in CANON.values())

def build_display_tags(candidates: List[str], max_tags: int = MAX_TAGS) -> List[str]:
    # 후보 태그를 표준/우선순위 기준으로 3~4개로 정제
    uniq: List[str] = []
    for group in PRIORITY:
        for t in CANON[group]:
            if t in candidates and t not in uniq:
                uniq.append(t)
    for t in candidates:
        if t not in uniq and is_valid(t):
            uniq.append(t)
    return uniq[:max_tags]
