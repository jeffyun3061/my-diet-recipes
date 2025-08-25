# app/models/tags.py
# 카드에 찍히는 컨트롤드 보캐브(표준 태그)와 표시 규칙

from typing import List

# 고정 표기(서비스 전역에서 재사용)
CANON = {
    "main": ["감자", "토마토", "치즈", "모짜렐라", "파마산", "파슬리"],
    "method": ["팬프라이", "팬구이", "굽기", "삶기", "데치기"],
    "form": ["감자칩", "패티/전", "웨지"],
    "time": ["30분이내", "15분이내"],
    "feature": ["바삭함", "간식", "술안주", "쉬움", "저지방", "오일절감"]
}

# 우선순위: 주재료 > 조리법 > 형태 > 시간 > 특성
PRIORITY = ["main", "method", "form", "time", "feature"]

# 카드 표시 길이 제한
MAX_TAGS = 4
MAX_TITLE = 14
MAX_SUBTITLE = 18
MAX_SUMMARY = 80
MAX_STEP_LINES = 3
MAX_STEP_TEXT = 60  # 한 단계당 최대 표시 글자 수

def is_valid(tag: str) -> bool:
    return any(tag in vals for vals in CANON.values())

def build_display_tags(candidates: List[str], max_tags: int = MAX_TAGS) -> List[str]:
    # 후보를 표준표기 + 우선순위에 따라 3~4개로 정제
    uniq = []
    # 우선순위 그룹 안에서 표준 표기가 후보에 있으면 먼저 채택
    for group in PRIORITY:
        for t in CANON[group]:
            if t in candidates and t not in uniq:
                uniq.append(t)
    # 남은 후보 중 표준표기인 것만 채택
    for t in candidates:
        if t not in uniq and is_valid(t):
            uniq.append(t)
    return uniq[:max_tags]
