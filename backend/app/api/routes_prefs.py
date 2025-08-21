# routes_prefs.py
from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from user_prefs import UserPrefs, Goal

router = APIRouter()

# MongoDB 연결
client = MongoClient("mongodb://localhost:27017/")
db = client["recipes"]
prefs_collection = db["user_prefs"]

# ======================
# 1) 사용자 체형/목적 정보 저장
# ======================
@router.post("/prefs/")
def create_user_prefs(prefs: UserPrefs):
    data = prefs.dict()
    result = prefs_collection.insert_one(data)
    return {"message": "사용자 선호 정보 저장 완료", "id": str(result.inserted_id)}

# ======================
# 2) 단일 사용자 정보 조회 (_id 기반)
# ======================
@router.get("/prefs/{user_id}")
def get_user_prefs(user_id: str):
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다.")

    user_data = prefs_collection.find_one({"_id": obj_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

    user_data["_id"] = str(user_data["_id"])
    return user_data

# ======================
# 3) 사용자 목표 기반 레시피 추천
# ======================
@router.get("/prefs/{user_id}/recommend")
def recommend_recipe(user_id: str):
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다.")

    user_data = prefs_collection.find_one({"_id": obj_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

    goals = user_data.get("goals", [])

    # 목표별 추천 메시지 생성 (실제 로직은 추후 연결)
    recommendations = []
    for goal in goals:
        if goal == Goal.diet.value:
            recommendations.append("저칼로리 다이어트 레시피 5가지")
        elif goal == Goal.bulk.value:
            recommendations.append("단백질 풍부한 근육 강화 레시피 5가지")
        elif goal == Goal.high_protein_low_carb.value:
            recommendations.append("고단백 저탄수 레시피 5가지")
        elif goal == Goal.maintain.value:
            recommendations.append("균형 잡힌 일반 레시피 5가지")

    return {"user_id": str(user_data["_id"]), "goals": goals, "recommendations": recommendations}
