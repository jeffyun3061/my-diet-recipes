from typing import List, Optional, Union
import re

from pydantic import BaseModel, Field
# v1/v2 겸용 validator shim
try:
    from pydantic import field_validator as _field_validator  # v2
    def validator(*fields, **kwargs):
        # v1에서 쓰던 pre/always를 v2로 매핑
        pre = kwargs.pop("pre", False)
        kwargs.pop("always", None)  # v2에는 없음 → 무시
        mode = "before" if pre else "after"
        return _field_validator(*fields, mode=mode)
except ImportError:  # v1
    from pydantic import validator

from app.models.tags import (
    CANON,                     # ★ 추가: 주재료 사전
    build_display_tags,
    MAX_SUMMARY, MAX_STEP_LINES, MAX_STEP_TEXT, MAX_TAGS
)

# 공통 유틸
def _clip_text(s: str, limit: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= limit else s[:limit].rstrip() + "…"

def _split_phrases(text: str) -> List[str]:
    # 문장/구 단위로 잘라 후보 만들기
    parts = re.split(r"[\.!\?·,]|→| - |\u00B7|\u2022", (text or "").strip())
    return [p.strip() for p in parts if p and len(p.strip()) >= 4]

def _fallback_steps(summary: str, title: str) -> List[str]:
    # 요약/제목으로 3줄 생성
    cands = _split_phrases(summary) + _split_phrases(title)
    out: List[str] = []
    for s in cands:
        s = _clip_text(s, MAX_STEP_TEXT)
        if s and s not in out:
            out.append(s)
        if len(out) >= 3:
            break
    if not out:
        out = ["재료 준비", "중약불로 조리", "접시에 담기"]
    return out[:3]

# 풀 카드(원본 저장용)
class RecipeVariantCard(BaseModel):
    name: str
    key_ingredients: List[str] = Field(default_factory=list, min_items=0, max_items=3)
    summary: str = ""
    steps_compact: List[str] = Field(default_factory=list)   # 3줄 권장
    tags: List[str] = Field(default_factory=list)            # 3~4개

    @validator("summary", pre=True, always=True)
    def _v_clip_summary(cls, v):
        return _clip_text(v, MAX_SUMMARY)

    @validator("steps_compact", pre=True, always=True)
    def _v_clip_steps(cls, v):
        v = [ _clip_text(s, MAX_STEP_TEXT) for s in (v or []) ]
        return v[:MAX_STEP_LINES]  # 3단계만

    @validator("tags", pre=True, always=True)
    def _v_norm_tags(cls, v):
        base = list(dict.fromkeys(v or []))
        return build_display_tags(base, MAX_TAGS)

class RecipeCard(BaseModel):
    id: str
    title: str
    subtitle: str
    tags: List[str] = Field(default_factory=list)            # 상단 3~4개
    variants: List[RecipeVariantCard]
    source: Optional[dict] = None                            # {"site","url","recipe_id"}
    imageUrl: Optional[str] = None                           # 썸네일

    @validator("tags", pre=True, always=True)
    def _v_head_tags(cls, v):
        base = list(dict.fromkeys(v or []))
        return build_display_tags(base, MAX_TAGS)

# 카드 전용 "스트릭트" 뷰(분량 강제)
MAX_STRICT_SUMMARY = 90     # 요약 최대 길이
MAX_STRICT_STEPS   = 3      # 스텝 3 고정
MAX_STRICT_CHIPS   = 3      # 칩 3 고정

def _sanitize_step(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^\s*[\d\-\(\)\.]+[)\.]?\s*", "", s)                  # 앞 번호/불릿 제거
    s = re.sub(r"\s+\d{1,3}(,?\d{3})*원.*$", "", s)                   # 가격 줄 자르기
    s = re.sub(r"(구매|리뷰|평점|만개의레시피).*$", "", s)            # 쇼핑/리뷰 노이즈 제거
    return s.strip()

class RecipeVariantStrict(BaseModel):
    name: str = "기본"
    key_ingredients: List[str] = Field(default_factory=list, max_items=MAX_STRICT_CHIPS)
    summary: str = ""
    steps: List[str] = Field(default_factory=list, max_items=MAX_STRICT_STEPS)

    @validator("summary", pre=True, always=True)
    def _v_sum(cls, v):
        return _clip_text(v or "", MAX_STRICT_SUMMARY)

    @validator("steps", pre=True, always=True)
    def _v_steps(cls, v):
        import re
        block = re.compile(r"(?:[0-9]{1,3}(?:[,]\d{3})*\s*원|\b[0-5](?:\.\d)?\s*\(\d+\)|구매|리뷰|평점|추천\s*레시피|광고|쇼핑|쿠폰|특가)")
        out = []
        for x in (v or []):
            s = (x or "").strip()
            if not s or block.search(s):
                continue
            s = _clip_text(_sanitize_step(s), MAX_STEP_TEXT)
            if s:
                out.append(s)
            if len(out) >= MAX_STRICT_STEPS:
                break
        
        return out


class RecipeCardStrict(BaseModel):
    id: str
    title: str
    subtitle: str
    imageUrl: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_items=MAX_TAGS)
    variant: RecipeVariantStrict

def to_strict_card(card: Union["RecipeCard", dict]) -> "RecipeCardStrict":
    d = card if isinstance(card, dict) else card.model_dump()
    v0 = (d.get("variants") or [{}])[0]

    # 칩: 원본 → 없으면 태그에서 주재료만 추출
    chips = (v0.get("key_ingredients") or [])[:MAX_STRICT_CHIPS]
    if not chips:
        main_set = set(CANON.get("main", []))
        chips = [t for t in (d.get("tags") or []) if t in main_set][:MAX_STRICT_CHIPS]

    summary = v0.get("summary") or d.get("subtitle") or ""
    # 스텝: 원본 → 없으면 요약/제목으로 생성
    steps = v0.get("steps_compact") or v0.get("steps") or []
    if not steps:
        steps = _fallback_steps(summary, d.get("title", ""))

    return RecipeCardStrict(
        id=d.get("id",""),
        title=d.get("title",""),
        subtitle=d.get("subtitle",""),
        imageUrl=d.get("imageUrl"),
        tags=(d.get("tags") or [])[:MAX_TAGS],
        variant=RecipeVariantStrict(
            name=v0.get("name","기본"),
            key_ingredients=chips,
            summary=summary,
            steps=steps
        ),
    )
