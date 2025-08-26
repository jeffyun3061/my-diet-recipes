# app/services/crawl_10000.py
# 목적: 재료/태그(예: 다이어트) 기반으로 10000recipe 검색 페이지를 크롤해 상위 레시피를 파싱한다.
# 주의: robots.txt를 준수하고, 요청 속도를 제한한다.

import asyncio
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus
import httpx
from bs4 import BeautifulSoup
import urllib.robotparser

BASE = "https://www.10000recipe.com"
SEARCH_PATH = "/recipe/list.html"
USER_AGENT = "MyDietRecipesBot/0.1 (+for study; contact: team@example.com)"

# 간단 로봇 파서 캐시
_rp: Optional[urllib.robotparser.RobotFileParser] = None

async def _get_robot_parser() -> urllib.robotparser.RobotFileParser:
    # robots.txt를 읽어와서 파싱 결과를 캐시한다.
    global _rp
    if _rp is not None:
        return _rp
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE, "/robots.txt"))
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(rp.url)
            resp.raise_for_status()
            rp.parse(resp.text.splitlines())
    except Exception:
        # 실패 시 보수적으로 허용 안 함 처리
        rp = urllib.robotparser.RobotFileParser()
        rp.parse([])
        rp.can_fetch = lambda agent, url: False  # type: ignore
    _rp = rp
    return _rp

async def _allowed(url: str) -> bool:
    # robots.txt 정책을 그대로 따른다 (테스트 우회 없음)
    rp = await _get_robot_parser()
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False

def _build_query(ingredients: List[str], tags: List[str]) -> str:
    # 재료 + 태그(예: 다이어트)로 검색어 구성
    terms = [t.strip() for t in (ingredients + tags) if t and t.strip()]
    return " ".join(terms) if terms else ""

# 다이어트 키워드 가중치 (간단 룰)
DIET_PLUS  = ["샐러드","구이","찜","오븐","저염","저지방","에어프라이어","라이트","저칼로리"]
DIET_MINUS = ["튀김","버터","크림","마요네즈","설탕","달달","기름진","치즈듬뿍","느끼한","헤비"]

def _diet_adjust(title: str, desc: str) -> float:
    text = f"{title} {desc}".lower()
    score = 0.0
    for w in DIET_PLUS:
        if w.lower() in text:
            score += 0.3
    for w in DIET_MINUS:
        if w.lower() in text:
            score -= 0.4
    return score

def _score_item(item: Dict, ingredients: List[str], tags: List[str]) -> float:
    # 매우 단순한 스코어: 제목/요약에 포함된 재료 수 + 다이어트 태그 가산 + 키워드 가/감점
    title = (item.get("title") or "").lower()
    desc = (item.get("desc") or "").lower()
    ko_in = 0
    for ing in ingredients:
        s = (ing or "").lower()
        if s and (s in title or s in desc):
            ko_in += 1
    tag_bonus = 0.5 if any(t in ["다이어트","저염","저지방"] for t in tags) else 0.0
    diet_adj = _diet_adjust(title, desc)
    return ko_in + tag_bonus + diet_adj

def _pick_attr(img_tag) -> Optional[str]:
    # 썸네일 src 추출(data-src 우선)
    if not img_tag:
        return None
    return img_tag.get("data-src") or img_tag.get("src")

def _parse_list(html: str) -> List[Dict]:
    # HTML을 파싱해 레시피 카드 목록을 표준 스키마로 변환
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []

    # 보편적인 리스트 셀렉터들 (변경될 수 있으므로 여럿 시도)
    candidates = soup.select("ul.common_sp_list_ul > li") or soup.select("ul > li.common_sp_list_li") or []

    for li in candidates:
        a = li.select_one("a.common_sp_link") or li.select_one("a")
        if not a:
            continue
        href = a.get("href") or ""
        url = urljoin(BASE, href)

        title_el = li.select_one(".common_sp_caption_tit") or li.select_one(".tit") or a
        title = (title_el.get_text(strip=True) if title_el else "").strip()

        # 설명/요약(있으면)
        desc_el = li.select_one(".common_sp_caption_dsc") or li.select_one(".common_sp_caption") or li.select_one("p")
        desc = (desc_el.get_text(" ", strip=True) if desc_el else "").strip()

        # 썸네일
        img = li.select_one("img")
        thumb = _pick_attr(img)
        if thumb and thumb.startswith("//"):
            thumb = "https:" + thumb
        if thumb and thumb.startswith("/"):
            thumb = urljoin(BASE, thumb)

        # 시간(있으면)
        time_el = li.select_one(".common_sp_caption_rv") or li.select_one(".time")
        time_min = None
        if time_el:
            import re
            m = re.search(r"(\d+)\s*분", time_el.get_text())
            if m:
                time_min = int(m.group(1))

        items.append({
            "title": title,
            "url": url,
            "desc": desc,
            "thumbnail": thumb,
            "timeMin": time_min,
            "source": {"type": "external", "site": "10000recipe"}
        })

    # 중복 제거 (url 기준)
    seen = set()
    uniq: List[Dict] = []
    for it in items:
        u = it["url"]
        if u in seen:
            continue
        seen.add(u)
        uniq.append(it)

    return uniq

async def crawl_10000_by_ingredients(ingredients: List[str], tags: List[str], limit: int = 12) -> List[Dict]:
    # 10000recipe에서 재료/태그로 레시피를 크롤링한다.
    # 반환 스키마: 각 item에 score 포함
    query = _build_query(ingredients, tags)
    if not query:
        return []

    # robots.txt 체크
    search_url = f"{BASE}{SEARCH_PATH}?q={quote_plus(query)}"
    if not await _allowed(search_url):
        # 허용 안되면 비어있게 반환
        return []

    # HTTP 요청
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
        # 속도 제한: 서버 예의상 약간의 sleep
        await asyncio.sleep(0.8)
        resp = await client.get(search_url)
        resp.raise_for_status()
        html = resp.text

    items = _parse_list(html)

    # 간단 스코어링
    for it in items:
        it["score"] = _score_item(it, ingredients, tags)

    # 스코어 순 정렬 + 상위 N개
    items.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return items[:limit]

# -------------------------
# 하위호환 별칭 
crawl_by_ingredients_norm = crawl_10000_by_ingredients

# 모듈 외부에 노출할 심볼
__all__ = [
    "crawl_10000_by_ingredients",
    "crawl_by_ingredients_norm"
]
