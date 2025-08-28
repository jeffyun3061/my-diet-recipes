# app/services/crawl_10000.py
# 목적: 재료/태그(예: 다이어트) 기반으로 10000recipe 검색 페이지를 크롤해 상위 레시피를 파싱한다.
#      (옵션) 상세 페이지까지 들어가 재료/조리과정까지 채운다.
# 주의: robots.txt를 준수하고, 요청 속도를 제한한다.

from __future__ import annotations
import asyncio
import re
import random  # ← 추가: 백오프용
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, quote_plus

import httpx
from bs4 import BeautifulSoup
import urllib.robotparser

BASE = "https://www.10000recipe.com"
SEARCH_PATH = "/recipe/list.html"
USER_AGENT = "MyDietRecipesBot/0.1 (+for study; contact: team@example.com)"

# ---------------------------------------------------------------------
# 로봇 파서 캐시
# ---------------------------------------------------------------------
_rp: Optional[urllib.robotparser.RobotFileParser] = None

async def _get_robot_parser() -> urllib.robotparser.RobotFileParser:
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
    rp = await _get_robot_parser()
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False

# ---------------------------------------------------------------------
# 공용: 리트라이 GET (타임아웃 재시도 + 지수형 백오프 약간의 지터)
# ---------------------------------------------------------------------
async def _get_with_retry(client: httpx.AsyncClient, url: str, tries: int = 3) -> httpx.Response:
    last: Optional[Exception] = None
    for i in range(tries):
        try:
            return await client.get(url)
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last = e
            # 1.2, 2.4, 3.6초 + 작은 지터
            await asyncio.sleep(1.2 * (i + 1) + random.random() * 0.5)
    # 마지막 예외 재던지기
    assert last is not None
    raise last

# ---------------------------------------------------------------------
# 검색어/스코어/다이어트 가중치
# ---------------------------------------------------------------------
def _build_query(ingredients: List[str], tags: List[str]) -> str:
    terms = [t.strip() for t in (ingredients + tags) if t and t.strip()]
    return " ".join(terms) if terms else ""

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

# ---------------------------------------------------------------------
# 리스트 파싱
# ---------------------------------------------------------------------
def _pick_attr(img_tag) -> Optional[str]:
    if not img_tag:
        return None
    return img_tag.get("data-src") or img_tag.get("src")

def _parse_list(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []

    # 구조 변화에 대비해 여러 셀렉터 시도
    candidates = soup.select("ul.common_sp_list_ul > li") or soup.select("ul > li.common_sp_list_li") or []

    for li in candidates:
        a = li.select_one("a.common_sp_link") or li.select_one("a")
        if not a:
            continue
        href = a.get("href") or ""
        url = urljoin(BASE, href)

        title_el = li.select_one(".common_sp_caption_tit") or li.select_one(".tit") or a
        title = (title_el.get_text(strip=True) if title_el else "").strip()

        desc_el = li.select_one(".common_sp_caption_dsc") or li.select_one(".common_sp_caption") or li.select_one("p")
        desc = (desc_el.get_text(" ", strip=True) if desc_el else "").strip()

        img = li.select_one("img")
        thumb = _pick_attr(img)
        if thumb and thumb.startswith("//"):
            thumb = "https:" + thumb
        if thumb and thumb.startswith("/"):
            thumb = urljoin(BASE, thumb)

        # 조리시간(있으면)
        time_el = li.select_one(".common_sp_caption_rv") or li.select_one(".time")
        time_min = None
        if time_el:
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

    # url 기준 중복 제거
    seen = set()
    uniq: List[Dict] = []
    for it in items:
        u = it["url"]
        if u in seen:
            continue
        seen.add(u)
        uniq.append(it)
    return uniq

# ---------------------------------------------------------------------
# 상세 파싱
# ---------------------------------------------------------------------
DETAIL_WAIT = 0.8      # 예의상 대기
DETAIL_CONC = 4        # 동시 상세 요청 제한

def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())

def _parse_detail(html: str) -> Tuple[List[str], List[str]]:
    """상세 페이지에서 재료/조리과정 추출"""
    soup = BeautifulSoup(html, "lxml")

    # --- 재료 ---
    ings: List[str] = []

    # (1) 대표 영역
    for li in soup.select(".ready_ingre3 ul li"):
        txt = li.get_text(" ", strip=True)
        txt = re.sub(r"\s*\([^)]+\)", "", txt)  # (소분류) 제거
        txt = re.sub(r"\s{2,}", " ", txt)
        txt = _clean(txt)
        if txt:
            ings.append(txt)

    # (2) 대체 셀렉터들
    if not ings:
        for sel in [".ingre_list li", ".lst_ingrd li", ".ingre_all li", ".cont_ingre li"]:
            for li in soup.select(sel):
                txt = _clean(li.get_text(" ", strip=True))
                if txt:
                    ings.append(txt)
            if ings:
                break

    # --- 조리 과정 ---
    steps: List[str] = []

    # (1) view_step 계열
    for box in soup.select(".view_step .media, .view_step li, .view_step .step"):
        txt = _clean(box.get_text(" ", strip=True))
        txt = re.sub(r"^STEP\s*\d+\s*", "", txt, flags=re.I)
        if len(txt) >= 2:
            steps.append(txt)

    # (2) 대체: ol/li
    if not steps:
        for li in soup.select("ol li"):
            txt = _clean(li.get_text(" ", strip=True))
            if len(txt) >= 2:
                steps.append(txt)

    return ings, steps

async def _fetch_detail(client: httpx.AsyncClient, url: str) -> Tuple[List[str], List[str]]:
    if not await _allowed(url):
        return [], []
    await asyncio.sleep(DETAIL_WAIT)
    # r = await client.get(url)  # ← 기존
    r = await _get_with_retry(client, url, tries=3)  # ← 리트라이 적용
    r.raise_for_status()
    return _parse_detail(r.text)

# ---------------------------------------------------------------------
# 메인 엔트리
# ---------------------------------------------------------------------
async def crawl_10000_by_ingredients(
    ingredients: List[str],
    tags: List[str],
    limit: int = 12,
    fetch_details: bool = False,   # ← True면 상세까지 채움
) -> List[Dict]:
    query = _build_query(ingredients, tags)
    if not query:
        return []

    # robots.txt 체크
    search_url = f"{BASE}{SEARCH_PATH}?q={quote_plus(query)}"
    if not await _allowed(search_url):
        return []

    # ---- 타임아웃/커넥션 제한 + 리트라이 ----
    timeout = httpx.Timeout(connect=15.0, read=20.0, write=20.0, pool=20.0)
    limits  = httpx.Limits(max_connections=3, max_keepalive_connections=2)

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        limits=limits,
        http2=False,
    ) as client:
        # 예의상 대기
        await asyncio.sleep(0.8)
        # resp = await client.get(search_url)   # ← 기존
        resp = await _get_with_retry(client, search_url, tries=3)  # ← 리트라이 적용
        resp.raise_for_status()
        html = resp.text

        items = _parse_list(html)

        # 점수 부여 및 상위 N개 선택
        for it in items:
            it["score"] = _score_item(it, ingredients, tags)
        items.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        items = items[:limit]

        # 상세 파싱(옵션)
        if fetch_details and items:
            sem = asyncio.Semaphore(DETAIL_CONC)

            async def _bound_fetch(it: Dict):
                try:
                    async with sem:
                        ings, steps = await _fetch_detail(client, it["url"])
                    it["ingredients"] = ings
                    it["steps"] = steps
                except Exception:
                    it["ingredients"] = []
                    it["steps"] = []

            await asyncio.gather(*[_bound_fetch(it) for it in items])

        return items

# 하위호환 별칭
crawl_by_ingredients_norm = crawl_10000_by_ingredients

__all__ = [
    "crawl_10000_by_ingredients",
    "crawl_by_ingredients_norm",
]
