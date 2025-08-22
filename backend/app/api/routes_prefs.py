# 사용자 개인정보 입력 저장/조회 — 가람 담당
from fastapi import APIRouter, Depends, Response
from datetime import datetime
from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.user_prefs import UserPrefsIn, UserPrefsDoc
from app.services.reco import calc_target_kcal

router = APIRouter()

@router.post("")
async def upsert_prefs(payload: UserPrefsIn, response: Response, anon_id: str = Depends(get_or_set_anon_id)):
    # 서버 계산: kcal 타깃 + goal
    kcal_target = calc_target_kcal(payload.weight_kg, payload.target_weight_kg, payload.period_days)

    if payload.target_weight_kg < payload.weight_kg:
        goal = "loss"
    elif payload.target_weight_kg > payload.weight_kg:
        goal = "gain"
    else:
        goal = "maintain"

    # DB 문서
    doc = UserPrefsDoc(
        **payload.model_dump(),
        anon_id=anon_id,
        kcal_target=kcal_target,
        diet_goal=goal,
        updated_at=datetime.utcnow()
    )

    # upsert
    db = get_db()
    await db["user_preferences"].update_one(
        {"anon_id": anon_id},
        {"$set": doc.model_dump()},
        upsert=True
    )

    # 응답
    return {"ok": True, "kcal_target": kcal_target, "diet_goal": goal, "mode": "upserted"}

@router.get("")
async def get_prefs(anon_id: str = Depends(get_or_set_anon_id)):
    # 저장된 값 조회 (프리필)
    db = get_db()
    doc = await db["user_preferences"].find_one({"anon_id": anon_id}, {"_id": 0})
    return {"prefs": doc}
