# app/db/models/user_prefs.py
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

# 입력 바디 (프론트에서 보내는 값)
class UserPrefsIn(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: float
    target_weight_kg: float
    period_days: int = Field(..., ge=1)
    sex: Optional[Literal["male", "female"]] = None
    activity_level: Optional[Literal["low", "light", "moderate", "high"]] = "light"
    diet_tags: List[str] = []         # 예: ["저염","다이어트"]
    allergies: List[str] = []         # 예: ["우유","땅콩"]

# DB 저장 문서
class UserPrefsDoc(UserPrefsIn):
    anon_id: str
    kcal_target: int
    diet_goal: Literal["loss", "gain", "maintain"]
    updated_at: datetime = Field(default_factory=datetime.utcnow)
