# app/models/schemas.py
# Pydantic 모델 정의
# - PreferencesIn: 개인정보/목표 입력 (유연 필드, 대부분 optional)


from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# # 프론트 카드 타입 (배열로 반환)
class RecipeRecommendationOut(BaseModel):
    # 프론트 필드명/타입과 완전 일치
    id: str
    title: str
    description: str = ""
    ingredients: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    imageUrl: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# # 개인정보/목표 입력 — 프론트 폼 대응 (optional로 두어 폼 확장 여지)
class PreferencesIn(BaseModel):
    # 익명 식별 (없으면 서버가 쿠키로 발급)
    anon_id: Optional[str] = None

    # 신체/목표
    weightKg: Optional[float] = None
    targetWeightKg: Optional[float] = None
    periodDays: Optional[int] = None

    # 라이프스타일/제약
    diet: Optional[str] = None                 # "balanced" | "lowcarb" | "keto" | "highprotein" | "intermittent"
    dietTags: Optional[List[str]] = None       # 추가 태그
    maxCookMinutes: Optional[int] = None
    allergies: Optional[List[str]] = None

    # 추가 정보(폼 확장 대비)
    age: Optional[int] = None
    heightCm: Optional[int] = None
    sex: Optional[str] = None                  # "male" | "female" 등
    activityLevel: Optional[str] = None        # "low" | "mid" | "high"
    calorie_target: Optional[int] = None
