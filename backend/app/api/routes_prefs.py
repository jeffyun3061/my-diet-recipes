# app/api/routes_prefs.py
# 사용자 개인정보 입력 저장/조회 — 가람 담당

from fastapi import APIRouter, Depends, Response, HTTPException, Request
from datetime import datetime, timezone

from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.schemas import PreferencesIn
from app.services.reco import calc_target_kcal

# prefix
router = APIRouter(prefix="/preferences", tags=["preferences"])

# 한글 > 코드 정규화 테이블
_DIET_MAP = {
    "균형식": "balanced",
    "저탄고지": "lowcarb",
    "키토": "keto",
    "고단백": "highprotein",
    "간헐적 단식": "intermittent",
}
_SEX_MAP = {
    "남성": "male",
    "여성": "female",
}

@router.post("")
async def upsert_prefs(
    payload: PreferencesIn,                      # camelCase 수용 + alias(스키마 설정 기준)
    response: Response,
    anon_id: str = Depends(get_or_set_anon_id),  # 쿠키 없으면 발급
):
    # DB 핸들 방어
    try:
        db = get_db()
    except RuntimeError as e:
        # 500 대신 503으로 명확히
        raise HTTPException(status_code=503, detail=str(e))

    # 입력 정규화 (라벨/코드 혼용 대응)
    sex = (payload.sex or "").strip()
    sex = _SEX_MAP.get(sex, sex) or None  # "남성"→"male", 이미 코드면 유지

    diet_input = (payload.diet or "").strip()
    diet_code = _DIET_MAP.get(diet_input, diet_input) or None  # "저탄고지" > "lowcarb"

    # camelCase로 왔지만 스키마 alias가 없을 수도 있으므로 보수적으로 병행 수용
    calorie_target = getattr(payload, "calorie_target", None)
    if calorie_target is None:
        calorie_target = getattr(payload, "calorieTarget", None)

    # 서버 계산 — camelCase 필드 접근 (폼 그대로 수용)
    w = payload.weightKg or 0
    t = payload.targetWeightKg or w
    d = payload.periodDays or 0

    try:
        kcal_target = calc_target_kcal(w, t, d)
    except Exception:
        kcal_target = None  # 계산 실패시 None

    if t < w:
        goal = "loss"
    elif t > w:
        goal = "gain"
    else:
        goal = "maintain"

    now = datetime.now(timezone.utc).isoformat()

    # DB 저장은 snake_case로 표준화 (조회/분석 편리)
    doc = {
        "anon_id": anon_id,
        "weight_kg": payload.weightKg,
        "target_weight_kg": payload.targetWeightKg,
        "period_days": payload.periodDays,
        "diet": diet_code,                        #한글 라벨도 코드로 저장
        "diet_tags": payload.dietTags,
        "max_cook_minutes": payload.maxCookMinutes,
        "allergies": payload.allergies,
        "age": payload.age,
        "height_cm": payload.heightCm,
        "sex": sex,                               #"남성/여성"도 코드로 저장
        "activity_level": payload.activityLevel,
        "calorie_target": calorie_target,         #alias/camel 혼용 대응
        "kcal_target": kcal_target,
        "diet_goal": goal,
        "updated_at": now,
    }

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
    # DB 핸들 방어
    try:
        db = get_db()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    doc = await db["user_preferences"].find_one({"anon_id": anon_id}, {"_id": 0})
    return {"ok": True, "anonId": anon_id, "prefs": (doc or {})}
