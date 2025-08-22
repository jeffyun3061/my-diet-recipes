# 사진 업로드/분석/추천 — 시완(분석) + 지용(크롤/점수)
from fastapi import APIRouter, UploadFile, File, Depends, Response
from typing import List
from datetime import datetime
from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.services.analyze import analyze_labels
from app.services.crawl_10000 import crawl_by_ingredients_norm
from app.services.reco import score_recipe, calc_target_kcal

router = APIRouter()

@router.post("/analyze")
async def analyze_photo(file: UploadFile = File(...), anon_id: str = Depends(get_or_set_anon_id)):
    # 시완: 여기서 Google Lens/GCV를 붙여서 analyze_labels 내부를 교체하면 됨
    image_bytes = await file.read()
    labels: List[str] = analyze_labels(image_bytes)

    # 선택: 이미지/라벨 메타 저장 (추후 학습/통계용)
    db = get_db()
    img_doc = {
        "anon_id": anon_id,
        "filename": file.filename,
        "labels": labels,
        "created_at": datetime.utcnow()
    }
    await db["images"].insert_one(img_doc)

    return {"labels": labels}

@router.post("/recommend")
async def photo_recommend(file: UploadFile = File(...), top_k: int = 10, anon_id: str = Depends(get_or_set_anon_id)):
    # 1) 사진 → 라벨
    image_bytes = await file.read()
    labels: List[str] = analyze_labels(image_bytes)

    # 2) 사용자 선호 불러오기 (없으면 보수적 기본값)
    db = get_db()
    prefs = await db["user_preferences"].find_one({"anon_id": anon_id})
    if prefs:
        target_kcal = int(prefs.get("kcal_target"))
        goal = prefs.get("diet_goal", "maintain")
    else:
        # 기본 추정치: 체중 70kg, 30일에 65kg 목표 가정
        target_kcal = calc_target_kcal(70, 65, 30)
        goal = "loss"

    # 3) 라벨 → 크롤 후보
    candidates = crawl_by_ingredients_norm(labels, limit=max(20, top_k * 2))

    # 4) 점수화(타깃 kcal 적합도 + 트렌드)
    scored = sorted(
        candidates,
        key=lambda r: score_recipe(r, target_kcal),
        reverse=True
    )[:top_k]

    # 5) 응답 조립 (프론트 표시 친화)
    return {
        "labels": labels,
        "target": {"kcal": target_kcal, "goal": goal},
        "items": [{
            "title": r["title"],
            "calories": r["nutrition"]["calories"],
            "macros": {
                "protein": r["nutrition"]["protein_g"],
                "carb": r["nutrition"]["carb_g"],
                "fat": r["nutrition"]["fat_g"]
            },
            "tags": r["tags"],
            "timeMin": r["time_min"],
            "thumbnail": r.get("thumbnail"),
            "source": r["source"]
        } for r in scored]
    }
