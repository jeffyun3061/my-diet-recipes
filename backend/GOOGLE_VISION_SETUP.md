# Google Cloud Vision API 설정 가이드

## 1. Google Cloud 프로젝트 설정

### 1.1 Google Cloud Console에서 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 ID를 메모해두세요

### 1.2 Cloud Vision API 활성화
1. Google Cloud Console에서 "API 및 서비스" > "라이브러리"로 이동
2. "Cloud Vision API" 검색 후 활성화

### 1.3 서비스 계정 키 생성
1. "IAM 및 관리" > "서비스 계정"으로 이동
2. "서비스 계정 만들기" 클릭
3. 계정 이름 입력 (예: `vision-api-service`)
4. "키 만들기" > "JSON" 선택
5. 다운로드된 JSON 파일을 안전한 위치에 저장

## 2. 환경변수 설정

### 2.1 .env 파일 생성
프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```bash
# Google Cloud Vision API 설정
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-project-id
```

### 2.2 서비스 계정 키 경로 설정
다운로드한 JSON 파일의 절대 경로를 `GOOGLE_APPLICATION_CREDENTIALS`에 설정

예시:
```bash
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\username\Downloads\vision-api-service-key.json
```

## 3. API 사용법

### 3.1 이미지 분석 엔드포인트

#### 새 이미지 업로드 및 분석
```bash
POST /photo/analyze
Content-Type: multipart/form-data

file: [이미지 파일]
```

#### 저장된 이미지 분석
```bash
POST /photo/analyze/{photo_id}
```

### 3.2 응답 예시

```json
{
  "success": true,
  "filename": "food.jpg",
  "analysis": {
    "labels": [
      {
        "name": "Food",
        "confidence": 0.95,
        "type": "label"
      },
      {
        "name": "Vegetable",
        "confidence": 0.87,
        "type": "label"
      }
    ],
    "objects": [
      {
        "name": "Tomato",
        "confidence": 0.92,
        "type": "object"
      },
      {
        "name": "Lettuce",
        "confidence": 0.85,
        "type": "object"
      }
    ],
    "texts": [
      {
        "text": "Fresh Vegetables",
        "confidence": 0.78,
        "type": "text"
      }
    ],
    "ingredients": [
      {
        "name": "tomato",
        "confidence": 0.92,
        "source": "object_detection",
        "type": "ingredient"
      },
      {
        "name": "lettuce",
        "confidence": 0.85,
        "source": "object_detection",
        "type": "ingredient"
      }
    ]
  }
}
```

## 4. 지원하는 이미지 형식

- JPEG
- PNG
- GIF
- BMP
- WEBP
- RAW

## 5. 제한사항

- 이미지 크기: 최대 10MB
- 파일 형식: 위에서 명시한 형식만 지원
- API 호출 제한: Google Cloud Vision API 할당량에 따름

## 6. 오류 처리

### 6.1 일반적인 오류

#### 인증 오류
```
Google Cloud Vision API가 설치되지 않았습니다
```
**해결방법**: `pip install google-cloud-vision` 실행

#### 인증 정보 오류
```
GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되지 않았습니다
```
**해결방법**: `.env` 파일에서 경로 확인

#### API 할당량 초과
```
Quota exceeded for quota group 'default'
```
**해결방법**: Google Cloud Console에서 할당량 확인 및 증가 요청

### 6.2 폴백 동작

Google Cloud Vision API를 사용할 수 없는 경우, 시스템은 자동으로 더미 데이터를 반환하여 서비스가 중단되지 않도록 합니다.

## 7. 개발 환경에서 테스트

### 7.1 로컬 테스트
```bash
# 환경변수 설정
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/key.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# 서버 실행
docker compose up -d
```

### 7.2 API 테스트
```bash
# 이미지 분석 테스트
curl -X POST "http://localhost:8000/photo/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_image.jpg"
```

## 8. 보안 고려사항

1. **서비스 계정 키 보안**: JSON 키 파일을 절대 Git에 커밋하지 마세요
2. **환경변수 사용**: 프로덕션에서는 환경변수를 통해 인증 정보 관리
3. **API 키 제한**: Google Cloud Console에서 API 키 사용 범위 제한
4. **네트워크 보안**: HTTPS 사용 및 적절한 CORS 설정

## 9. 비용 관리

Google Cloud Vision API는 사용량에 따라 과금됩니다:
- 라벨 감지: $1.50 per 1,000 images
- 객체 감지: $2.50 per 1,000 images
- 텍스트 감지: $1.50 per 1,000 images

비용을 절약하려면:
1. 이미지 크기 최적화
2. 캐싱 구현
3. 사용량 모니터링
4. 할당량 설정
