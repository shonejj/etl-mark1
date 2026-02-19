"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "ETL Platform"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_UPLOAD_SIZE_MB: int = 100
    CONCURRENCY: int = 4
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5178",
        "http://localhost:3000",
    ]

    # MySQL
    MYSQL_URL: str = "mysql+pymysql://root:admin@localhost:3306/etl_platform"
    ASYNC_MYSQL_URL: str = "mysql+aiomysql://root:admin@localhost:3306/etl_platform"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "etl-files"
    MINIO_SECURE: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRY_DAYS: int = 7

    # Super Admin Seed
    SUPER_ADMIN_EMAIL: str = "admin@etl.local"
    SUPER_ADMIN_PASSWORD: str = "changeme123"

    # Features
    FEATURE_PDF_EXTRACT: bool = True
    FEATURE_AI_ASSISTANT: bool = False
    FEATURE_KAFKA: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
