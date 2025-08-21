from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
import os

# =========================
# 앱 설정
# =========================
app = FastAPI(title="my-diet-recipes", version="1.0.0")

# CORS (프론트엔드에서 호출할 예정이면 유지)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요시 도메인으로 제한하세요.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Mongo 연결
# =========================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
db = client["fitness_app"]
users_collection = db["users"]

# =========================
# 모델 정의
# =========================
class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class UserBodyInfo(BaseModel):
    name: str = Field(..., example="홍길동")
    age: int = Field(..., example=25, ge=1, le=120)
    height: float = Field(..., example=175.5, gt=0)
    weight: float = Field(..., example=70.2, gt=0)
    gender: Optional[Gender] = Field(None, example="male")

class UserOut(UserBodyInfo):
    id: str = Field(..., example="66c37c1a9d8c1e21f9e5a0ab")

# =========================
# 스타트업 훅: 연결 확인 + 인덱스 준비
# =========================
@app.on_event("startup")
def on_startup():
    try:
        client.admin.command("ping")  # 실제 DB 연결 확인
        # 이름 중복 방지를 위한 유니크 인덱스
        users_collection.create_index("name", unique=True)
    except Exception as e:
        # 여기서 예외가 나면 /health에서 잡아줍니다.
        print(f"[Startup] Mongo 연결 확인 실패: {e}")

# =========================
# 라우트
# =========================
@app.get("/")
async def root():
    return {"message": "Welcome to Fitness App API"}

@app.get("/health")
async def health_check():
    try:
        client.admin.command("ping")
        return {"status": "ok", "mongo": "ok"}
    except Exception as e:
        # 서버는 떠있지만 DB 연결 문제를 알려줌
        raise HTTPException(status_code=503, detail=f"MongoDB unreachable: {e}")

# 사용자 생성
@app.post("/users/", response_model=UserOut, status_code=201)
async def create_user(user: UserBodyInfo):
    try:
        doc = user.dict()
        result = users_collection.insert_one(doc)
        return {**doc, "id": str(result.inserted_id)}
    except DuplicateKeyError:
        # name이 유니크 인덱스라 중복일 경우
        raise HTTPException(status_code=409, detail="User with this name already exists")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

# 단일 사용자 조회 (name으로)
@app.get("/users/by-name/{name}", response_model=UserOut)
async def get_user(name: str):
    user = users_collection.find_one({"name": name})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "age": user["age"],
        "height": user["height"],
        "weight": user["weight"],
        "gender": user.get("gender"),
    }

# 여러 사용자 목록 조회 (페이징)
@app.get("/users", response_model=List[UserOut])
async def list_users(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    cursor = users_collection.find().skip(skip).limit(limit)
    results = []
    for u in cursor:
        results.append({
            "id": str(u["_id"]),
            "name": u["name"],
            "age": u["age"],
            "height": u["height"],
            "weight": u["weight"],
            "gender": u.get("gender"),
        })
    return results
