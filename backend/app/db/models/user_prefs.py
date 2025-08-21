from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

# 식단 목적 Enum
class Goal(str, Enum):
    diet = "다이어트"                 # 다이어트
    bulk = "벌크업"                 # 벌크업
    high_protein_low_carb = "고단백 저탄수화물"  # 고단백 저탄수화물
    maintain = "일반 유지"         # 일반 유지

class UserPrefs(BaseModel):
    name: str = Field(..., example="홍길동")
    age: int = Field(..., ge=1, le=120, example=25)
    height: float = Field(..., gt=0, example=175.0)
    weight: float = Field(..., gt=0, example=70.0)
    gender: Optional[Gender] = Field(None, example="male")
    goals: List[Goal] = Field(..., example=["diet", "high_protein_low_carb"])
