# app/api/routes_prefs.py
# 사용자 개인정보 입력 저장/조회 — 가람 담당

from fastapi import APIRouter, Depends, Response, HTTPException, Request
from datetime import datetime, timezone


from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.schemas import PreferencesIn
from app.services.reco import calc_target_kcal

# ▼ prefix 추가 (중요)
router = APIRouter(prefix="/preferences", tags=["preferences"])

@router.post("")
async def upsert_prefs(
    payload: PreferencesIn,
    response: Response,
    anon_id: str = Depends(get_or_set_anon_id),  # 쿠키 발급
):
    # 서버 계산 — camelCase 필드 접근
    w = payload.weightKg or 0
    t = payload.targetWeightKg or w
    d = payload.periodDays or 0

    try:
        kcal_target = calc_target_kcal(w, t, d)
    except Exception:
        kcal_target = None

    if t < w:
        goal = "loss"
    elif t > w:
        goal = "gain"
    else:
        goal = "maintain"

    now = datetime.now(timezone.utc).isoformat()

    # DB 저장은 snake_case로 표준화 (조회/분석 편함)
    doc = {
        "anon_id": anon_id,
        "weight_kg": payload.weightKg,
        "target_weight_kg": payload.targetWeightKg,
        "period_days": payload.periodDays,
        "diet": payload.diet,
        "diet_tags": payload.dietTags,
        "max_cook_minutes": payload.maxCookMinutes,
        "allergies": payload.allergies,
        "age": payload.age,
        "height_cm": payload.heightCm,
        "sex": payload.sex,
        "activity_level": payload.activityLevel,
        "calorie_target": payload.calorie_target,
        "kcal_target": kcal_target,
        "diet_goal": goal,
        "updated_at": now,
    }

    db = get_db()
    prev = await db["user_preferences"].find_one({"anon_id": anon_id})
    if not prev:
        doc["created_at"] = now

    await db["user_preferences"].update_one(
        {"anon_id": anon_id},
        {"$set": doc},
        upsert=True
    )

    return {
        "ok": True,
        "anonId": anon_id,
        "kcal_target": kcal_target,
        "diet_goal": goal,
        "saved": doc,
        "mode": "upserted" if prev else "inserted",
    }

@router.get("")
async def get_prefs(request: Request, anon_id: str = Depends(get_or_set_anon_id)):
    db = get_db()
    doc = await db["user_preferences"].find_one({"anon_id": anon_id}, {"_id": 0})
    return {"ok": True, "anonId": anon_id, "prefs": (doc or {})}
