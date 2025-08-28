# app/scripts/backfill_recipe_cards.py
import asyncio, re
from urllib.parse import urlparse
from typing import List, Any, Dict

from app.db.init import init_db, get_db
from app.models.schemas import RecipeCard, RecipeVariantCard
from app.models.tags import build_display_tags, CANON

# norm → 한글 칩 매핑 테이블
NORM2DISPLAY = {
    "potato": "감자",
    "egg": "달걀",
    "tomato": "토마토",
    "cheese": "치즈",
    "mozzarella": "모짜렐라",
    "parmesan": "파마산",
    "parsley": "파슬리",
}

# 템플릿 폴백: 태그/칩 보고 3줄 생성
def _fallback_steps(title: str, tags: list[str], chips: list[str]) -> list[str]:
    tags = tags or []
    chips = [c for c in (chips or []) if c]

    method = "basic"
    if ("팬프라이" in tags) or ("볶음" in tags):
        method = "pan"
    elif ("오븐구이" in tags) or ("굽기" in tags) or ("에어프라이어" in tags):
        method = "bake"
    elif ("삶기" in tags) or ("데치기" in tags):
        method = "boil"

    form = "chip" if "감자칩" in tags else ("pancake" if "패티/전" in tags else "cut")

    # 1) 손질
    if form == "chip":
        s1 = "감자 씻어 얇게 썰고 물기를 제거한다."
    elif form == "pancake":
        s1 = "감자 삶아 으깨고 기호 재료와 섞어 반죽한다."
    else:
        s1 = "감자 깨끗이 씻어 한입 크기로 썬다."

    # 2) 조리
    if method == "pan":
        s2 = "팬을 중약불로 달구고 기름을 약간 두른 뒤 노릇하게 익힌다."
    elif method == "bake":
        s2 = "200℃로 예열한 오븐/에어프라이어에서 10–15분 굽는다."
    elif method == "boil":
        s2 = "소금을 한 꼬집 넣은 끓는 물에 8–10분 삶는다."
    else:
        s2 = "중불에서 속까지 익을 때까지 조리한다."

    # 3) 마무리
    has_cheese = any(c in ("치즈", "모짜렐라", "파마산") for c in chips)
    has_parsley = "파슬리" in chips
    if has_cheese and has_parsley:
        s3 = "치즈를 올려 녹이고 파슬리를 뿌려 간한다."
    elif has_cheese:
        s3 = "치즈를 올려 녹이고 소금·후추로 간한다."
    elif has_parsley:
        s3 = "소금·후추로 간하고 파슬리를 뿌려 마무리한다."
    else:
        s3 = "소금·후추 또는 취향의 시즈닝으로 마무리한다."

    return [s1, s2, s3]

def pick_key_ingredients(src: dict) -> List[str]:
    # norm → 디스플레이 한글 칩(최대 3개)
    # 1) ingredients.norm 우선
    # 2) 부족하면 ingredients.raw(한글) + title에서 키워드 스캔
    # 3) tags/keywords 도우미
    chips: List[str] = []

    # 1) norm → 한글 매핑
    norm = (src.get("ingredients") or {}).get("norm") or []
    for x in norm:
        disp = NORM2DISPLAY.get(str(x).lower().strip())
        if disp and disp not in chips:
            chips.append(disp)
        if len(chips) >= 3:
            return chips

    # 2) 원문 재료(한글) / 제목에서 스캔
    raw_list = (src.get("ingredients") or {}).get("raw") or []
    raw_txt = " ".join(map(str, raw_list)) + " " + str(src.get("title") or "")
    ko_candidates = [
        ("모짜", "모짜렐라"),
        ("치즈", "치즈"),
        ("토마토", "토마토"),
        ("파마산", "파마산"),
        ("파슬리", "파슬리"),
        ("달걀", "달걀"),
        ("계란", "달걀"),
        ("감자", "감자"),
    ]
    for needle, disp in ko_candidates:
        if needle in raw_txt and disp not in chips:
            chips.append(disp)
        if len(chips) >= 3:
            return chips

    # 3) tags/keywords 보강 (이미 한글이면 그대로)
    raw_tags = (src.get("tags") or []) + re.split(r"[,\s]+", (src.get("keywords") or ""))
    for t in raw_tags:
        t = str(t).strip()
        if not t:
            continue
        if t in NORM2DISPLAY.values() and t not in chips:
            chips.append(t)
        if len(chips) >= 3:
            break

    return chips[:3]

# 가능한 필드 이름들(크롤러마다 제각각이라 다 받아줌)
URL_FIELDS = ["url", "link", "href", "page", "source_url", "origin_url"]
IMG_FIELDS = ["images", "image", "thumbnail", "thumb", "img", "imageUrl"]
ING_FIELDS = [
    ("ingredients", ["list", "lines", "original"]),  # dict 형태일 때
    "ingredients", "재료", "재료목록",
]
STEP_FIELDS = ["steps", "directions", "instructions", "조리과정", "조리방법", "만드는법", "recipeSteps"]

def _first_image(r: dict) -> str:
    for f in IMG_FIELDS:
        v = r.get(f)
        if isinstance(v, list) and v:
            return str(v[0])
        if isinstance(v, str) and v:
            return v
    return ""

def _get_url(r: dict) -> str:
    for f in URL_FIELDS:
        v = r.get(f)
        if isinstance(v, str) and v:
            return v
    src = r.get("source")
    if isinstance(src, dict):
        u = src.get("url") or src.get("href")
        if isinstance(u, str):
            return u
    return ""

def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""

def _detect_10000recipe(url: str, title: str) -> bool:
    d = _extract_domain(url)
    if "10000recipe" in d:
        return True
    return False

def _list_from(d: Any, keys: List[str]) -> List[str]:
    # 다양한 포맷(list/dict/str) → 리스트로 표준화
    if isinstance(d, dict):
        for k in keys:
            v = d.get(k)
            if isinstance(v, list):
                return [str(x) for x in v if x]
            if isinstance(v, str) and v.strip():
                parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", v)
                return [p.strip() for p in parts if p.strip()]
    if isinstance(d, list):
        return [str(x) for x in d if x]
    if isinstance(d, str) and d.strip():
        parts = re.split(r"\s*(?:\n|^\d+[)\.]|\r)+\s*", d)
        return [p.strip() for p in parts if p.strip()]
    return []

def _ingredients_from(r: dict) -> List[str]:
    for f in ING_FIELDS:
        if isinstance(f, tuple):
            v = r.get(f[0])
            if v:
                lst = _list_from(v, f[1])
                if lst:
                    return lst
        else:
            v = r.get(f)
            if v:
                lst = _list_from(v, [])
                if lst:
                    return lst
    return []

def _steps_from(r: dict) -> List[str]:
    for f in STEP_FIELDS:
        v = r.get(f)
        if v:
            lst = _list_from(v, [])
            if lst:
                return lst
    return []

def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)

def _sanitize_step(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"^\s*(?:\d+[.)]\s*|[-•]\s*)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _clean_steps(lines: List[str]) -> List[str]:
    # 쇼핑/가격/리뷰/추천레시피/광고성 줄 제거 + 조리 동사 포함된 줄만 남김.
    # 3줄까지만 반환.
    if not lines:
        return []

    # 차단 패턴
    block = re.compile(
        r"(?:"
        r"[0-9]{1,3}(?:[,]\d{3})*\s*원"   # 3,390 원
        r"|구매|리뷰|평점|만개의레시피|추천\s*레시피|광고|쇼핑|쿠폰|특가"
        r"|\b[0-5](?:\.\d)?\s*\(\d+\)"    # 4.9 (213)
        r")",
        flags=re.IGNORECASE,
    )

    # 조리 동사(살짝 넉넉하게)
    KEEP_VERBS = [
        "끓", "볶", "굽", "구워", "섞", "데치", "삶", "썰", "다지",
        "얇게", "두껍게", "올려", "넣", "익히", "부쳐", "튀기", "버무리",
        "비비", "재워", "체에", "물기", "팬", "오븐", "에어프라이", "약불", "중불", "강불"
    ]

    cleaned: List[str] = []
    for s in lines:
        s = str(s).strip()
        if not s:
            continue
        if block.search(s):
            continue
        s = re.sub(r"^\s*(?:\d+[.)]\s*|[-•]\s*)", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if not s:
            continue
        if not any(v in s for v in KEEP_VERBS):
            continue

        cleaned.append(s)
        if len(cleaned) >= 3:
            break

    return cleaned

def _gather_tags(src: dict, title: str, steps: List[str], ingredients: List[str]) -> List[str]:
    cand: List[str] = []
    # 원문 태그/키워드
    for k in ("tags", "categories", "keywords"):
        v = src.get(k)
        if isinstance(v, list):
            cand += [str(x) for x in v]
        elif isinstance(v, str):
            cand += re.split(r"[,\s]+", v)

    blob = f"{title} {' '.join(steps)}".lower()

    # 주재료(샘플)
    if any("감자" in s for s in ingredients) or "감자" in title:
        cand.append("감자")
    if any("토마토" in s for s in ingredients) or "토마토" in title:
        cand.append("토마토")
    if any(("모짜렐라" in s or "모차렐라" in s) for s in ingredients) or "모짜렐라" in title:
        cand.append("모짜렐라")
    if any("파마산" in s for s in ingredients):
        cand.append("파마산")
    if any("파슬리" in s for s in ingredients):
        cand.append("파슬리")
    if any("치즈" in s for s in ingredients) or "치즈" in title:
        cand.append("치즈")

    # 조리법
    if _contains_any(blob, ["팬", "프라이팬", "지짐", "전"]) and "튀김" not in cand:
        cand.append("팬프라이")
    if _contains_any(blob, ["굽", "구워", "구이"]) and "오븐" not in blob:
        cand.append("굽기")
    if _contains_any(blob, ["오븐"]):
        cand.append("오븐구이")
    if _contains_any(blob, ["에어프라이", "에프", "af "]):
        cand.append("에어프라이어")
    if _contains_any(blob, ["볶", "볶아", "볶음"]):
        cand.append("볶음")
    if _contains_any(blob, ["튀김", "튀겨"]):
        cand.append("튀김")
    if _contains_any(blob, ["찌기", "찜"]):
        cand.append("찌기")
    if _contains_any(blob, ["삶", "데치"]):
        cand.append("삶기"); cand.append("데치기")
    if _contains_any(blob, ["끓여", "끓이", "국물"]):
        cand.append("끓이기")

    # 형태/메뉴
    if _contains_any(title, ["칩", "웨지"]):
        cand.append("감자칩")
    if _contains_any(title, ["전", "부침"]):
        cand.append("패티/전")
    if _contains_any(title, ["국", "탕"]):
        cand.append("국")
    if "찌개" in title:
        cand.append("찌개")
    for w, t in [
        ("전골", "전골"), ("샐러드", "샐러드"), ("면", "면"), ("국수", "면"), ("우동", "면"), ("라면", "면"),
        ("파스타", "파스타"), ("덮밥", "덮밥"), ("볶음밥", "볶음밥"), ("무침", "무침"),
        ("조림", "조림"), ("찜", "찜"), ("스프", "스프"), ("샌드위치", "샌드위치")
    ]:
        if w in title:
            cand.append(t)

    # 시간/특성
    cand.append("30분이내")
    if _contains_any(blob, ["바삭", "크리스피"]):
        cand.append("바삭함")
    if _contains_any(blob, ["안주", "술안주"]):
        cand.append("술안주")
    if _contains_any(blob, ["간식"]):
        cand.append("간식")

    return build_display_tags(list(dict.fromkeys(cand)))

async def main(limit: int = 5000, only_10000: bool = True):
    await init_db()
    db = get_db()

    cur = db["recipes"].find({}, {"_id": 0}).limit(limit)

    n = 0
    m_candidates = 0

    async for r in cur:
        title = (r.get("title") or "").strip()
        if not title:
            continue

        url = _get_url(r)
        is_10000 = _detect_10000recipe(url, title)

        # 만개의레시피만 카드화 옵션
        if only_10000 and not is_10000:
            continue

        m_candidates += 1

        # 원본 재료/스텝
        ingredients = _ingredients_from(r)
        raw_steps = _steps_from(r)
        steps = _clean_steps(raw_steps)

        # 태그/요약
        # steps를 먼저 정리한 뒤 태그를 뽑아야 조리법 신호가 잘 잡힘
        tags = _gather_tags(r, title, steps, ingredients)
        summary = (r.get("summary") or r.get("description") or " ".join(steps[:3]) or title).strip()[:80]

        # key_ingredients는 pick_key_ingredients 우선
        key_ing = pick_key_ingredients(r)
        if not key_ing:
            key_ing = [k for k in CANON["main"] if any(k in s for s in ingredients)][:3]

        # 템플릿 생성
        tmpl = _fallback_steps(title, tags, key_ing)

        # 항상 3줄 보장: 부족하면 템플릿으로 채움(중복 방지)
        if len(steps) < 3:
            for s in tmpl:
                if s not in steps:
                    steps.append(s)
                if len(steps) == 3:
                    break

        # recipe_id (만개의레시피 URL 패턴)
        rid = None
        m = re.search(r"/recipe/(\d+)", url) if url else None
        if m:
            rid = int(m.group(1))

        # variant는 한 번만 생성
        variant = RecipeVariantCard(
            name="기본",
            key_ingredients=key_ing,
            summary=summary,
            steps_compact=steps[:3],  # 3줄 저장
            tags=tags,
        )

        source = {
            "site": "만개의레시피" if is_10000 else "unknown",
            "url": url,
            "domain": _extract_domain(url),
            "recipe_id": rid,
        }

        card = RecipeCard(
            id=f"10000-{rid}" if rid else (r.get('id') or title),
            title=title,
            subtitle=r.get("subtitle") or "간단 요약",
            tags=tags,
            variants=[variant],
            source=source,
            imageUrl=_first_image(r),
        )

        await db["recipe_cards"].update_one(
            {"id": card.id},
            {"$set": card.model_dump()},
            upsert=True,
        )
        n += 1

    print(f"[backfill] candidates: {m_candidates}, upserted cards: {n}")

if __name__ == "__main__":
    asyncio.run(main())
