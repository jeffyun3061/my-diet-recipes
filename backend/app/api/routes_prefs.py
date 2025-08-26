# app/api/routes_prefs.py
# 사용자 선호/개인정보 관리 — 가람 담당

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.db.models.schemas import PreferencesIn

router = APIRouter(prefix="/preferences", tags=["preferences"])

class PreferencesResponse(BaseModel):
    ok: bool
    anonId: str
    prefs: Optional[Dict[str, Any]] = None
    kcal_target: Optional[int] = None
    diet_goal: Optional[str] = None
    saved: Optional[Dict[str, Any]] = None
    mode: Optional[str] = None

def calc_target_kcal(weight_kg: float, target_weight_kg: float, days: int, activity: float = 1.35) -> int:
    """칼로리 타겟 계산"""
    maint = 22 * weight_kg * activity
    deficit = ((weight_kg - target_weight_kg) * 7700) / max(days, 1)
    deficit = max(300, min(deficit, 1000))  # 안전 범위
    return int(max(900, maint - deficit))

def determine_diet_goal(weight_kg: float, target_weight_kg: float) -> str:
    """다이어트 목표 결정"""
    if target_weight_kg < weight_kg:
        return "loss"
    elif target_weight_kg > weight_kg:
        return "gain"
    else:
        return "maintain"

def normalize_diet_label(diet: str) -> str:
    """다이어트 라벨 정규화"""
    diet_map = {
        "저탄고지": "lowcarb",
        "케토": "keto",
        "고단백": "highprotein",
        "간헐적단식": "intermittent",
        "균형": "balanced",
        "lowcarb": "lowcarb",
        "keto": "keto",
        "highprotein": "highprotein",
        "intermittent": "intermittent",
        "balanced": "balanced"
    }
    return diet_map.get(diet, "balanced")

def normalize_sex_label(sex: str) -> str:
    """성별 라벨 정규화"""
    sex_map = {
        "남성": "male",
        "여성": "female",
        "male": "male",
        "female": "female"
    }
    return sex_map.get(sex, "male")

@router.get("", response_model=PreferencesResponse)
async def get_preferences(anon_id: str = Depends(get_or_set_anon_id)):
    """사용자 선호/개인정보 조회"""
    db = get_db()
    
    try:
        prefs = await db["user_preferences"].find_one({"anon_id": anon_id})
        
        if not prefs:
            return PreferencesResponse(
                ok=True,
                anonId=anon_id,
                prefs={}
            )
        
        # ObjectId를 문자열로 변환
        prefs["_id"] = str(prefs["_id"])
        
        return PreferencesResponse(
            ok=True,
            anonId=anon_id,
            prefs=prefs
        )
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 조회 오류: {str(e)}")

@router.post("", response_model=PreferencesResponse)
async def save_preferences(
    payload: PreferencesIn,
    anon_id: str = Depends(get_or_set_anon_id)
):
    """사용자 선호/개인정보 저장 (Upsert)"""
    db = get_db()
    
    try:
        # 입력 데이터 정규화
        prefs_data = {
            "anon_id": anon_id,
            "updated_at": datetime.utcnow()
        }
        
        # 기본 필드들
        if payload.weightKg is not None:
            prefs_data["weight_kg"] = payload.weightKg
        if payload.targetWeightKg is not None:
            prefs_data["target_weight_kg"] = payload.targetWeightKg
        if payload.periodDays is not None:
            prefs_data["period_days"] = payload.periodDays
        if payload.maxCookMinutes is not None:
            prefs_data["max_cook_minutes"] = payload.maxCookMinutes
        if payload.age is not None:
            prefs_data["age"] = payload.age
        if payload.heightCm is not None:
            prefs_data["height_cm"] = payload.heightCm
            
        # 라벨 정규화
        if payload.diet:
            prefs_data["diet"] = normalize_diet_label(payload.diet)
        if payload.sex:
            prefs_data["sex"] = normalize_sex_label(payload.sex)
        if payload.activityLevel:
            prefs_data["activity_level"] = payload.activityLevel
            
        # 배열 필드들
        if payload.dietTags:
            prefs_data["diet_tags"] = payload.dietTags
        if payload.allergies:
            prefs_data["allergies"] = payload.allergies
            
        # 칼로리 타겟
        if payload.calorie_target is not None:
            prefs_data["calorie_target"] = payload.calorie_target
            
        # 자동 계산 필드들
        if payload.weightKg and payload.targetWeightKg and payload.periodDays:
            kcal_target = calc_target_kcal(
                payload.weightKg, 
                payload.targetWeightKg, 
                payload.periodDays
            )
            prefs_data["kcal_target"] = kcal_target
            prefs_data["diet_goal"] = determine_diet_goal(payload.weightKg, payload.targetWeightKg)
        
        # Upsert 실행
        result = await db["user_preferences"].update_one(
            {"anon_id": anon_id},
            {
                "$set": prefs_data,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        # 저장된 데이터 조회
        saved_prefs = await db["user_preferences"].find_one({"anon_id": anon_id})
        saved_prefs["_id"] = str(saved_prefs["_id"])
        
        return PreferencesResponse(
            ok=True,
            anonId=anon_id,
            kcal_target=saved_prefs.get("kcal_target"),
            diet_goal=saved_prefs.get("diet_goal"),
            saved=saved_prefs,
            mode="inserted" if result.upserted_id else "upserted"
        )
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 저장 오류: {str(e)}")
