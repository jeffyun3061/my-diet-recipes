# app/db/models/schemas.py
# Pydantic 모델 정의
# PreferencesIn: 개인정보/목표 입력 (유연 필드, 대부분 optional)
# RecipeRecommendationOut: 프론트 카드 스키마
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

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

# # 텍스트(재료) 기반 추천 입력
class RecipeRecommendIn(BaseModel):
    ingredients: List[str] = Field(default_factory=list)

# # 사진 업로드용 스키마
class PhotoDoc(BaseModel):
    anon_id: str
    filename: str
    content_type: str
    data: bytes
    created_at: datetime = Field(default_factory=datetime.utcnow)

# # 개인정보/목표 입력 — 프론트 폼 대응 (optional로 두어 폼 확장 여지)
class PreferencesIn(BaseModel):
    # ▼ 프론트는 camelCase로 보내므로 alias 허용 (특히 calorieTarget)
    model_config = ConfigDict(populate_by_name=True)

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

    # 추가 정보
    age: Optional[int] = None
    heightCm: Optional[float] = None
    sex: Optional[str] = None                  # "male" | "female" 등
    activityLevel: Optional[str] = None        # "low" | "mid" | "high"

    # 프론트 calorieTarget(camel)로 보내면 calorie_target에 매핑
    calorie_target: Optional[int] = Field(default=None, alias="calorieTarget")
