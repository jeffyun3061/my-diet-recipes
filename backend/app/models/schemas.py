# app/models/schemas.py  (하단에 추가)

from typing import List, Optional
from pydantic import BaseModel, Field, validator
from app.models.tags import (
    build_display_tags,
    MAX_SUMMARY, MAX_STEP_LINES, MAX_STEP_TEXT, MAX_TAGS
)

def _clip_text(s: str, limit: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= limit else s[:limit].rstrip() + "…"

class RecipeVariantCard(BaseModel):
    name: str
    key_ingredients: List[str] = Field(default_factory=list, min_items=1, max_items=3)
    summary: str = ""
    steps_compact: List[str] = Field(default_factory=list)  # 3줄 고정
    tags: List[str] = Field(default_factory=list)           # 3~4개

    @validator("summary", pre=True, always=True)
    def _v_clip_summary(cls, v):
        return _clip_text(v, MAX_SUMMARY)

    @validator("steps_compact", pre=True, always=True)
    def _v_clip_steps(cls, v):
        v = [ _clip_text(s, MAX_STEP_TEXT) for s in (v or []) ]
        return v[:MAX_STEP_LINES]  # 3단계만 표시

    @validator("tags", pre=True, always=True)
    def _v_norm_tags(cls, v):
        # 중복 제거 후 카드용 3~4개로 정제
        base = list(dict.fromkeys(v or []))
        return build_display_tags(base, MAX_TAGS)

class RecipeCard(BaseModel):
    id: str
    title: str
    subtitle: str
    tags: List[str] = Field(default_factory=list)           # 카드 상단 3~4개
    variants: List[RecipeVariantCard]
    source: Optional[dict] = None                           # {"site": "...", "url": "...", "recipe_id": 123}

    @validator("tags", pre=True, always=True)
    def _v_head_tags(cls, v):
        base = list(dict.fromkeys(v or []))
        return build_display_tags(base, MAX_TAGS)
