# 목적: 만개의레시피 검색 목록/상세 페이지 크롤링(비동기)
# 의존: httpx, beautifulsoup4, lxml
# 확장: HEADERS/파싱 셀렉터를 운영 중 실패 로그 보고 점진 보정

from typing import List, Optional, Dict
import httpx
from bs4 import BeautifulSoup

BASE = "https://www.10000recipe.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")

def _abs(url: str) -> str:
    return url if url.startswith("http") else BASE + url

async def search_list_urls(query: str, page: int = 1) -> List[str]:
    """검색어/페이지로 레시피 카드 리스트에서 상세 링크 수집."""
    url = f"{BASE}/recipe/list.html?q={query}&order=reco&page={page}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as cli:
        r = await cli.get(url)
        r.raise_for_status()
        soup = _soup(r.text)

    urls: List[str] = []
    for a in soup.select("a.common_sp_link, a.common_sp_link[href*='/recipe/']"):
        href = a.get("href", "")
        if "/recipe/" in href:
            urls.append(_abs(href))

    # 중복 제거 (순서 보존)
    return list(dict.fromkeys(urls))

async def fetch_recipe(url: str) -> Optional[Dict]:
    # 상세 페이지 파싱. 실패는 None 반환(운영 안전)
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=25) as cli:
            r = await cli.get(url)
            r.raise_for_status()
            soup = _soup(r.text)

        title = (soup.select_one("meta[property='og:title']") or {}).get("content") or ""
        summary = (soup.select_one("meta[property='og:description']") or {}).get("content") or ""
        image = (soup.select_one("meta[property='og:image']") or {}).get("content") or ""
        if not title:
            h3 = soup.select_one("div.view2_summary h3")
            title = h3.get_text(strip=True) if h3 else ""

        # 재료 섹션 파싱(여러 템플릿 대응)
        ingredients_raw: List[str] = []
        for li in soup.select("div.ready_ingre3 li"):
            t = li.get_text(" ", strip=True)
            if t:
                ingredients_raw.append(t)
        if not ingredients_raw:
            for sel in ["ul#divConfirmedMaterialArea li", "div.ingre_view li", "table tr td"]:
                for node in soup.select(sel):
                    t = node.get_text(" ", strip=True)
                    if t and len(t) < 80:
                        ingredients_raw.append(t)

        # 조리 단계
        steps: List[str] = []
        for li in soup.select("div.view_step li"):
            t = li.get_text(" ", strip=True)
            if t:
                steps.append(t)
        if not steps:
            for p in soup.select("div.view_step_cont, div.step_box p"):
                t = p.get_text(" ", strip=True)
                if t:
                    steps.append(t)

        # 태그(있으면 랭킹 가점에 사용)
        tags: List[str] = []
        for a in soup.select("a#expand_tag, a[href*='/profile/tag/']"):
            t = a.get_text(" ", strip=True)
            if t:
                tags.append(t)

        if not summary and steps:
            summary = steps[0][:120]

        return {
            "url": url,
            "title": title,
            "summary": summary,
            "ingredients_raw": ingredients_raw,
            "steps": steps,
            "image": image,
            "tags": tags,
        }
    except Exception:
        return None

async def crawl_query(query: str, pages: int = 1) -> List[Dict]:
    # 검색어 기준 페이지를 순회하며 상세를 긁어 일괄 반환
    seen = set()
    out: List[Dict] = []
    for page in range(1, pages + 1):
        urls = await search_list_urls(query, page=page)
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            doc = await fetch_recipe(u)
            if doc:
                out.append(doc)
    return out
