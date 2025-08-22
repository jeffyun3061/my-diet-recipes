
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
