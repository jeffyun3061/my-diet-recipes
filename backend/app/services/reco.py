# 추천 점수/칼로리 타깃 계산 — 지용 담당
from typing import Dict

def calc_target_kcal(weight_kg: float, target_weight_kg: float, days: int, activity: float = 1.35) -> int:
    # 매우 단순한 일일 타깃 계산 (MVP)
    maint = 22 * weight_kg * activity
    deficit = ((weight_kg - target_weight_kg) * 7700) / max(days, 1)  # 1kg ≈ 7700 kcal
    deficit = max(300, min(deficit, 1000))  # 안전 범위 클램프
    return int(max(900, maint - deficit))

def score_recipe(recipe: Dict, target_kcal: int) -> float:
    # MVP 점수: 칼로리 적합(80%) + 트렌드(20%)
    kcal = recipe.get("nutrition", {}).get("calories", 0)
    calorie_fit = 1 - min(abs(kcal - target_kcal) / max(1, target_kcal), 1)  # 0~1
    trend = float(recipe.get("trend_score", 0.0))  # 0~1 가정
    return 0.8 * calorie_fit + 0.2 * trend
