# 환경변수 로딩 (.env)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"  # 필요 시 prod/staging로 분리
    MONGO_DB: str = "mydiet"
    OPENAI_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
