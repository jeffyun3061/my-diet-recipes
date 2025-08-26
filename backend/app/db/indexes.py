# 컬렉션 인덱스 생성 — 지용 담당
# 앱 스타트업에서 한 번 ensure_indexes()를 await로 호출한다.

from app.db.init import get_db

async def ensure_indexes():
    db = get_db()

    # 가람: 사용자 선호 저장 컬렉션
    await db["user_preferences"].create_index("anon_id", unique=True)

    # 지용: 레시피 검색/추천용 컬렉션
    await db["recipes"].create_index("tags")
    await db["recipes"].create_index("ingredients.norm")
    await db["recipes"].create_index("nutrition.calories")
    await db["recipes"].create_index([("trend_score", -1)])
    
    # 텍스트 검색 인덱스
    await db["recipes"].create_index([
        ("title", "text"),
        ("description", "text"),
        ("ingredients.raw", "text")
    ])
    
    # URL 중복 방지
    await db["recipes"].create_index("url", unique=True)

    # 시완: 이미지/분석 확장 대비(있어도 에러 안 남, 없으면 자동 생성됨)
    await db["images"].create_index([("anon_id", 1), ("created_at", -1)])
    await db["image_analyses"].create_index("image_id")
    await db["image_analyses"].create_index([("status", 1), ("created_at", -1)])

    # 사진 업로드/저장 컬렉션
    await db["photos"].create_index([("anon_id", 1), ("created_at", -1)])
    await db["photos"].create_index("content_type")
    
    # 추천 이력 컬렉션
    await db["recommendations"].create_index([("anon_id", 1), ("created_at", -1)])
    await db["recommendations"].create_index("used.tokens")
