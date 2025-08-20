# 레시피 표준 스키마 — 지용 담당
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Nutrition(BaseModel):
    calories: int
    protein_g: float
    carb_g: float
    fat_g: float
    sodium_mg: int

class RecipeDoc(BaseModel):
    title: str
    tags: List[str] = []
    ingredients: dict = {"norm": []}   # {"norm": ["chicken-breast", ...]}
    nutrition: Nutrition
    time_min: int
    thumbnail: Optional[str] = None
    source: dict = {"type": "internal"}  # {"type":"external","site":"10000recipe","url":"..."}
    trend_score: float = 0.0
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
