import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "Walters Opticians Backend API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security / JWT
    # Reads SECRET_KEY from .env (generated via secrets.token_hex(32))
    SECRET_KEY: str = "a79777f9e78bd030ebfa0055947e6a4465cc1b92cc581899185909c4462e0145"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./walters_opticians.db"

    # CORS Origins (Supports list parsing or comma-separated strings)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instantiate settings instance
settings = Settings()