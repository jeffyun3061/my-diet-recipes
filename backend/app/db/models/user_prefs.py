# 사용자 입력/저장 스키마 — 가람 담당
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserPrefsIn(BaseModel):
    # 프론트에서 받는 값 (필드명 고정)
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    age: int = Field(gt=0)
    target_weight_kg: float = Field(gt=0)
    period_days: int = Field(gt=0)

class UserPrefsDoc(UserPrefsIn):
    # DB에 저장되는 값 (서버 계산 포함)
    kcal_target: int
    diet_goal: str                 # "loss|maintain|gain"
    updated_at: datetime = datetime.utcnow()
    anon_id: Optional[str] = None  # 쿠키 기반 익명 사용자 식별
