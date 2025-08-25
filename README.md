
cd C:\Users\diva\Desktop\mydiet\backend 에서

pip install -r requirements.txt 패키지 설치


docker compose up -d 컨테이너 실행


docker compose down 컨테이너 종료

컨테이너 재빌드
docker compose build --no-cache api
docker compose up -d



(프론트용)

Base URL
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Run (root)
- git checkout dev && git pull
- docker compose up -d
- (stop) docker compose down
- (rebuild if deps changed)
  docker compose build --no-cache api
  docker compose up -d

CORS / Cookie
- 개발용 CORS 허용됨 → 바로 호출 OK
- anon_id 쿠키 자동 발급 → fetch에 credentials:"include" 필수

Endpoints
- GET /health
- POST /preferences  (JSON body: height_cm, weight_kg, age, target_weight_kg, period_days)
- GET /preferences?anon_id=...
- POST /photo/recommend (Form-Data: file=image/*)

Notes
- 이미지 업로드는 multipart/form-data 사용예정
- API 스펙 변화는 dev 기준



엔드포인트 목록
메서드	경로	설명
GET	/	루트 핑
GET	/health	서버/DB 헬스 체크
GET	/preferences	현재 사용자(쿠키 anon_id) 선호/개인정보 조회
POST	/preferences	현재 사용자(쿠키 anon_id) 선호/개인정보 저장(Upsert)
POST	/crawl/seed	만개의레시피 크롤 → 정규화/업서트 → (선택)임베딩 저장
POST	/recipes/recommend	(단일 필드들) 이미지 업로드 추천
POST	/recipes/recommend/files	(배열 1개) 다중 이미지 업로드 추천

1) 루트 핑 — GET /

200

{ "status": "ok" }

2) 헬스 체크 — GET /health

DB 연결 포함 상태 반환

200 (예)

{ "status": "ok", "db": "ok" }

3) 선호/개인정보 조회 — GET /preferences

설명: 쿠키 anon_id 기준 문서 조회 (user_preferences 컬렉션). 없으면 {} 반환.

200 (예)

{
  "ok": true,
  "anonId": "c1c7...a15",
  "prefs": {
    "anon_id": "c1c7...a15",
    "weight_kg": 72.5,
    "target_weight_kg": 68,
    "period_days": 60,
    "diet": "lowcarb",
    "diet_tags": ["low_sugar"],
    "max_cook_minutes": 20,
    "allergies": ["peanut", "shrimp"],
    "age": 35,
    "height_cm": 175,
    "sex": "male",
    "activity_level": "moderate",
    "calorie_target": 1800,
    "kcal_target": 1750,
    "diet_goal": "loss",
    "updated_at": "2025-08-25T02:34:56+00:00",
    "created_at": "2025-08-25T02:30:00+00:00"
  }
}

4) 선호/개인정보 저장(Upsert) — POST /preferences

설명: 본문 JSON을 현재 사용자(쿠키 anon_id) 문서에 병합/갱신. 없으면 생성.

Headers: Content-Type: application/json

Body(JSON) — 프로젝트에서 실제 사용 중인 키들(모두 선택적)
(서버는 camelCase/일부 alias 혼용 지원)

{
  "weightKg": 72.5,
  "targetWeightKg": 68,
  "periodDays": 60,

  "diet": "저탄고지",               // 한글 라벨도 허용 → 서버가 코드("lowcarb")로 저장
  "dietTags": ["low_sugar"],
  "maxCookMinutes": 20,
  "allergies": ["peanut", "shrimp"],

  "age": 35,
  "heightCm": 175,
  "sex": "남성",                    // 한글 라벨 허용 → 서버가 "male"로 저장
  "activityLevel": "moderate",

  "calorie_target": 1800,          // alias 허용: calorie_target | calorieTarget
  "calorieTarget": 1800
}

서버 저장 형태(snake_case)

{
  "anon_id": "...",
  "weight_kg": 72.5,
  "target_weight_kg": 68,
  "period_days": 60,
  "diet": "lowcarb",
  "diet_tags": ["low_sugar"],
  "max_cook_minutes": 20,
  "allergies": ["peanut", "shrimp"],
  "age": 35,
  "height_cm": 175,
  "sex": "male",
  "activity_level": "moderate",
  "calorie_target": 1800,
  "kcal_target": 1750,             // 서버 계산(calc_target_kcal)
  "diet_goal": "loss",             // weight vs target 비교로 결정
  "updated_at": "ISO8601",
  "created_at": "ISO8601"          // 최초 생성 시만
}


200 (예)

{
  "ok": true,
  "anonId": "c1c7...a15",
  "kcal_target": 1750,
  "diet_goal": "loss",
  "saved": { "...": "위 snake_case 구조" },
  "mode": "inserted"               // 또는 "upserted"
}

200 (예)

{
  "ok": true,
  "anonId": "c1c7...a15",
  "kcal_target": 1750,
  "diet_goal": "loss",
  "saved": { "...": "위 snake_case 구조" },
  "mode": "inserted"               // 또는 "upserted"
}


오류

503: DB 핸들 획득 실패 등

5) 레시피 시드/갱신 — POST /crawl/seed

설명: 만개의레시피 검색 결과 pages 페이지만 수집 → 상세 파싱 → 정규화/업서트 → (키 있으면) 임베딩 저장
(임베딩: OPENAI_API_KEY 없으면 자동 스킵)

Query Params

이름	타입	필수	설명
q	string	✅	검색어. 예) 감자, 양파, 마늘, 가지
pages	int(1~5)		수집 페이지 수(권장 1~2)

200 (예)

{ "ok": true, "inserted": 80 }

6) 이미지 추천(단일 필드들) — POST /recipes/recommend

설명: 이미지 최대 9장을 업로드 → 재료 인식/정규화 → DB 교집합 + (선택)임베딩 보너스 → 카드 배열

Body (multipart/form-data)

필드	타입	필수	설명
image_0	file	✅	대표 이미지
image_1 ~ image_8	file		추가 이미지

없는 파일 필드는 보내지 말 것(빈 문자열 전송 금지)

200 (배열, 예)

[
  {
    "id": "665f9c...f3",
    "title": "감자볶음",
    "description": "간단하고 맛있는...",
    "ingredients": ["감자 2개", "양파 1/2개", "소금 약간"],
    "steps": ["...", "..."],
    "imageUrl": "https://...",
    "tags": ["한식", "밑반찬"]
  }
]


오류

400: 이미지 없음

415: 미지원 이미지 타입

503: Vision/모델 오류

7) 이미지 추천(배열 1개) — POST /recipes/recommend/files

설명: 단일 키 files 로 다중 이미지 업로드

Body (multipart/form-data)

필드	타입	필수	설명
files	file[]	✅	동일 키 files 로 여러 장 첨부

응답/오류: /recipes/recommend 와 동일

응답 모델(프론트 계약) — RecipeRecommendationOut
type RecipeRecommendationOut = {
  id: string;            // 레시피 문서 ID(string)
  title: string;         // 제목
  description: string;   // 요약/설명
  ingredients: string[]; // 재료(원문 라인)
  steps: string[];       // 조리 단계
  imageUrl: string;      // 대표 이미지 URL
  tags: string[];        // 태그/카테고리
}

Postman 테스트 플로우 (권장)

GET /health → 200 확인

POST /preferences → 위 Body 전체 또는 필요한 필드만 전송

POST /crawl/seed?q=감자&pages=2 → 이어서 양파/마늘/가지도 1~2p 시드

POST /recipes/recommend → image_0 파일 첨부(감자/양파 보이는 이미지)

(옵션) POST /recipes/recommend/files → files 키로 다중 이미지