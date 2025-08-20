# 만개의 레시피 크롤링 — 지용 담당
# 지금은 더미. 실제 구현 시 httpx + 파서 사용.
from typing import List, Dict

def crawl_by_ingredients_norm(ingredients: list[str], limit: int = 10) -> List[Dict]:
    # TODO: 실제 크롤 구현(표준 스키마로 반환)
    return [{
        "title": "닭가슴살 샐러드",
        "tags": ["chicken","salad","low-carb"],
        "ingredients": {"norm": ["chicken-breast","lettuce","tomato","olive-oil"]},
        "nutrition": {"calories": 430, "protein_g": 41, "carb_g": 16, "fat_g": 19, "sodium_mg": 720},
        "time_min": 20,
        "thumbnail": None,
        "source": {"type":"external","site":"10000recipe","url":"https://www.10000recipe.com/..."},
        "trend_score": 0.7
    }][:limit]
