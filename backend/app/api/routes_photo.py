# 사진 업로드/분석/추천 — 시완(분석) + 지용(크롤/점수)
from fastapi import APIRouter, UploadFile, File, Depends
from typing import List
from datetime import datetime
from app.core.deps import get_or_set_anon_id
from app.db.init import get_db
from app.services.analyze import analyze_labels
from app.services.crawl_10000 import crawl_by_ingredients_norm
from app.services.reco import score_recipe

router = APIRouter()

@router.post("/analyze")
async def analyze_photo(file: UploadFile = File(...), anon_id: str = Depends(get_or_set_anon_id)):
    # 시완: 여기서 Google Lens/GCV를 붙여서 analyze_labels 내부를 교체하면 됨
    image_bytes = await file.read()
    labels: List[str] = analyze_labels(image_bytes)

    # 선택: 이미지/라벨 메타 저장 (추후 학습/통계용)
    db = get_db()
    img_doc = {"anon_id": anon_id, "filename": file.filename, "labels": labels, "created_at": datetime.utcnow()}
    await db["images"].insert_one(img_doc)

    return {"labels": labels}

@router.post("/recommend")
async def photo_recommend(file: UploadFile = File(...), top_k: int = 10, anon_id: str = Depends(get_or_set_anon_id)):
    # 1) 사진 → 라벨
    image_bytes = await file.read()
    labels: List[str] = analyze_labels(image_bytes)

    # 2) 라벨 → 크롤 (지용: 실제 구현 교체)
    crawled = crawl_by_ingredients_norm(labels, limit=top_k)

    # 3) 크롤 결과를 표준 스키마로 DB upsert
    db = get_db()
    upserted = []
    for r in crawled:
        r["updated_at"] = datetime.utcnow()
        r.setdefault("created_at", datetime.utcnow())
        await db["recipes"].update_one({"title": r["title"]}, {"$set": r}, upsert=True)
        upserted.append(r)

    # 4) 개인 타깃 kcal (없으면 기본 1800)
    prefs = await db["user_preferences"].find_one({"anon_id": anon_id})
    target_kcal = prefs.get("kcal_target", 1800) if prefs else 1800

    # 5) 점수화 후 상위 K 반환
    scored = sorted(upserted, key=lambda x: score_recipe(x, target_kcal), reverse=True)[:top_k]

    return {
        "labels": labels,
        "target": {"kcal": target_kcal, "goal": (prefs["diet_goal"] if prefs else "loss")},
        "items": [{
            "title": r["title"],
            "calories": r["nutrition"]["calories"],
            "macros": {"protein": r["nutrition"]["protein_g"], "carb": r["nutrition"]["carb_g"], "fat": r["nutrition"]["fat_g"]},
            "tags": r["tags"],
            "timeMin": r["time_min"],
            "thumbnail": r.get("thumbnail"),
            "source": r["source"]
        } for r in scored]
    }
