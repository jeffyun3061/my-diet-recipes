# app/models/tags.py
from typing import List, Optional
import re

# === 표준 태그(카드 칩용) ======================================================
CANON = {
    # 주재료(카드 칩 우선순위에 쓰임) – 자주 쓰는 애들까지 확장
    "main": [
        "감자","고구마","호박","토마토","양파","당근","버섯","브로콜리",
        "두부","닭가슴살","닭고기","계란","치즈","모짜렐라","파마산","파슬리",
    ],
    # 조리법/열원
    "method": ["팬프라이","팬구이","굽기","볶음","튀김","삶기","데치기","찌기","끓이기","오븐구이","에어프라이어"],
    # 형태/메뉴
    "form": ["감자칩","패티/전","웨지","국","찌개","전골","조림","무침","찜","볶음밥","덮밥","비빔","샐러드","면","파스타","스프","샌드위치"],
    # 시간/특성
    "time": ["30분이내","15분이내"],
    "feature": ["바삭함","간식","술안주","쉬움","저지방","오일절감"],
}
PRIORITY = ["main","method","form","time","feature"]

MAX_TAGS = 4
MAX_TITLE = 14
MAX_SUBTITLE = 18
MAX_SUMMARY = 70   # 80 → 70
MAX_STEP_LINES = 3
MAX_STEP_TEXT = 48 # 60 → 48

def is_valid(tag: str) -> bool:
    return any(tag in vals for vals in CANON.values())

def build_display_tags(candidates: List[str], max_tags: int = MAX_TAGS) -> List[str]:
    """후보 태그를 표준/우선순위 기준으로 정제해 카드 칩으로 사용"""
    uniq: List[str] = []
    for group in PRIORITY:
        for t in CANON[group]:
            if t in candidates and t not in uniq:
                uniq.append(t)
    for t in candidates:
        if t not in uniq and is_valid(t):
            uniq.append(t)
    return uniq[:max_tags]

# === 정규화(캐노나이즈) =======================================================

# 동의어/영문 → 표준 한글 라벨
_CANON_SYNONYMS = {
    # 호박 계열
    "호박":"호박","단호박":"호박","애호박":"호박","zucchini":"호박","pumpkin":"호박","butternut":"호박",
    # 감자
    "감자":"감자","potato":"감자","potatoes":"감자",
    # 고구마
    "고구마":"고구마","sweet potato":"고구마","sweet":"고구마",
    # 양파/당근/토마토
    "양파":"양파","onion":"양파","onions":"양파",
    "당근":"당근","carrot":"당근","carrots":"당근",
    "토마토":"토마토","방울토마토":"토마토","tomato":"토마토","tomatoes":"토마토",
    # 단백질/두부
    "닭가슴살":"닭가슴살","chicken breast":"닭가슴살",
    "닭고기":"닭고기","chicken":"닭고기",
    "두부":"두부","tofu":"두부",
    # 기타 자주 쓰는 것들
    "버섯":"버섯","mushroom":"버섯","mushrooms":"버섯",
    "브로콜리":"브로콜리","broccoli":"브로콜리",
    "계란":"계란","달걀":"계란","egg":"계란","eggs":"계란",
}

# 정규식 보조(오탈자/복수형)
_CANON_REGEX = [
    (re.compile(r"(단|애)?호박", re.I), "호박"),
    (re.compile(r"zucc?hini", re.I), "호박"),
    (re.compile(r"pumpkin", re.I), "호박"),
    (re.compile(r"potato(es)?", re.I), "감자"),
    (re.compile(r"sweet\s*potato", re.I), "고구마"),
    (re.compile(r"carrot(s)?", re.I), "당근"),
    (re.compile(r"onion(s)?", re.I), "양파"),
    (re.compile(r"tomato(es)?", re.I), "토마토"),
]

# 불용어
KOREAN_STOP = {
    "소금","후추","물","설탕","간장","식용유","올리브유","식초","참기름","깨",
    "대파","쪽파","마늘","다진마늘","후추가루","고춧가루","밀가루",
    "약간","적당량","스푼","큰술","작은술","티스푼","컵"
}
EN_STOP = {"salt","pepper","water","sugar","soy","sauce","vinegar","oil","olive","garlic","spoon","tbsp","tsp","cup"}

# 문장 → 토큰 추출(한글/영문)
RX_WORD = re.compile(r"[가-힣]+|[A-Za-z]+(?:[ -][A-Za-z]+)*")

def extract_words(text: str) -> List[str]:
    return [m.group(0).strip() for m in RX_WORD.finditer(text or "") if m.group(0).strip()]

def is_stop(tok: str) -> bool:
    s = (tok or "").strip().lower()
    return s in EN_STOP or s in KOREAN_STOP

def canonicalize_token_ko(tok: str) -> Optional[str]:
    """토큰을 서비스 표준(한글) 라벨로 변환. 실패 시 None."""
    s = (tok or "").strip().lower()
    if not s:
        return None
    if s in _CANON_SYNONYMS:
        return _CANON_SYNONYMS[s]
    for rx, label in _CANON_REGEX:
        if rx.search(s):
            return label
    # 그대로 한글 단어면 그대로 두되, 불용어는 제외
    if re.fullmatch(r"[가-힣]+", s) and not is_stop(s):
        return s
    return None
