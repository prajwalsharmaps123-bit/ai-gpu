import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-GPUShare"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "aigpushare_super_secret_jwt_key_2026_secure_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database - default to async SQLite for local lightweight testing and PostgreSQL ready
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gpu_share.db")
    
    # Scheduler weights
    SCHEDULER_W_AVAIL: float = 0.35
    SCHEDULER_W_COST: float = 0.25
    SCHEDULER_W_TIME: float = 0.20
    SCHEDULER_W_REL: float = 0.10
    SCHEDULER_W_PERF: float = 0.10
    
    # Agent timeouts
    HEARTBEAT_TIMEOUT_SECONDS: int = 15
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True

settings = Settings()
