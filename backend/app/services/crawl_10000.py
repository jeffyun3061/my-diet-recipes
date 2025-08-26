# app/services/crawl_10000.py
# 만개의레시피 크롤링 서비스 — 지용 담당

from __future__ import annotations
from typing import List, Dict, Any, Optional
import asyncio
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import logging

from app.services.crawl10000.etl import normalize_ingredients, upsert_recipe
from app.services.crawl10000.embeddings import upsert_vector_for_recipe

logger = logging.getLogger(__name__)

async def crawl_recipes(db, query: str, pages: int = 1) -> int:
    """만개의레시피 검색 결과 크롤링"""
    
    recipes_collection = db["recipes"]
    inserted_count = 0
    
    try:
        # 검색 결과 페이지 크롤링
        recipe_urls = await crawl_search_results(query, pages)
        
        # 각 레시피 상세 페이지 크롤링
        for url in recipe_urls:
            try:
                recipe_data = await crawl_recipe_detail(url)
                if recipe_data:
                    # DB에 저장
                    await upsert_recipe(recipes_collection, recipe_data)
                    
                    # 저장된 문서 재조회하여 임베딩 생성
                    saved_recipe = await recipes_collection.find_one({"url": url})
                    if saved_recipe:
                        await upsert_vector_for_recipe(recipes_collection, saved_recipe)
                        inserted_count += 1
                        
            except Exception as e:
                logger.error(f"레시피 크롤링 실패 {url}: {e}")
                continue
                
        return inserted_count
        
    except Exception as e:
        logger.error(f"크롤링 오류: {e}")
        raise

async def crawl_search_results(query: str, pages: int) -> List[str]:
    """검색 결과에서 레시피 URL 수집"""
    
    urls = []
    base_url = "https://www.10000recipe.com/recipe/list.html"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, pages + 1):
            try:
                params = {
                    "q": query,
                    "page": page
                }
                
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 레시피 링크 추출
                recipe_links = soup.find_all('a', href=re.compile(r'/recipe/\d+'))
                
                for link in recipe_links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)
                            
                # 페이지 간 딜레이
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"검색 결과 크롤링 실패 (페이지 {page}): {e}")
                continue
                
    return urls

async def crawl_recipe_detail(url: str) -> Optional[Dict[str, Any]]:
    """레시피 상세 페이지 크롤링"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 기본 정보 추출
            title = extract_title(soup)
            description = extract_description(soup)
            ingredients = extract_ingredients(soup)
            steps = extract_steps(soup)
            image_url = extract_image(soup)
            tags = extract_tags(soup)
            
            if not title:
                return None
                
            # 정규화된 재료 추출
            normalized_ingredients = normalize_ingredients([ing.get('name', '') for ing in ingredients])
            
            recipe_data = {
                "url": url,
                "title": title,
                "description": description,
                "ingredients": {
                    "raw": [ing.get('name', '') for ing in ingredients],
                    "norm": normalized_ingredients
                },
                "steps": steps,
                "image": image_url,
                "tags": tags,
                "source": "10000recipe",
                "crawled_at": asyncio.get_event_loop().time()
            }
            
            return recipe_data
            
        except Exception as e:
            logger.error(f"레시피 상세 크롤링 실패 {url}: {e}")
            return None

def extract_title(soup: BeautifulSoup) -> str:
    """제목 추출"""
    title_elem = soup.find('h3', class_='view2_summary') or soup.find('h1', class_='view2_summary')
    if title_elem:
        return title_elem.get_text(strip=True)
    return ""

def extract_description(soup: BeautifulSoup) -> str:
    """설명 추출"""
    desc_elem = soup.find('div', class_='view2_summary_in')
    if desc_elem:
        return desc_elem.get_text(strip=True)
    return ""

def extract_ingredients(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """재료 추출"""
    ingredients = []
    
    # 재료 섹션 찾기
    ingredient_section = soup.find('div', class_='ready_ingre3')
    if not ingredient_section:
        return ingredients
        
    # 재료 항목들 추출
    ingredient_items = ingredient_section.find_all('li')
    
    for item in ingredient_items:
        name_elem = item.find('a') or item.find('span')
        if name_elem:
            name = name_elem.get_text(strip=True)
            if name:
                ingredients.append({"name": name})
                
    return ingredients

def extract_steps(soup: BeautifulSoup) -> List[str]:
    """조리 단계 추출"""
    steps = []
    
    # 조리 단계 섹션 찾기
    steps_section = soup.find('div', class_='view_step_cont')
    if not steps_section:
        return steps
        
    # 단계별 내용 추출
    step_items = steps_section.find_all('div', class_='view_step')
    
    for item in step_items:
        step_text = item.get_text(strip=True)
        if step_text:
            steps.append(step_text)
            
    return steps

def extract_image(soup: BeautifulSoup) -> str:
    """대표 이미지 추출"""
    img_elem = soup.find('img', class_='center-croping')
    if img_elem and img_elem.get('src'):
        return img_elem['src']
    return ""

def extract_tags(soup: BeautifulSoup) -> List[str]:
    """태그 추출"""
    tags = []
    
    # 태그 섹션 찾기
    tag_section = soup.find('div', class_='view_tag')
    if not tag_section:
        return tags
        
    # 태그 링크들 추출
    tag_links = tag_section.find_all('a')
    
    for link in tag_links:
        tag_text = link.get_text(strip=True)
        if tag_text:
            tags.append(tag_text)
            
    return tags
