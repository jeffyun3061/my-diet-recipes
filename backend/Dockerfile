FROM python:3.11

# 런타임 의존 패키지 (필요시 git 등 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 복사/설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY app ./app

# 컨테이너 기본 명령 (개발 중 핫리로드 쓰려면 compose 쪽 command로 오버라이드)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

