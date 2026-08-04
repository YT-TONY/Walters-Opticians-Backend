from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Walters Opticians API"
    SECRET_KEY: str = "SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION_982371982"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 Hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./walters_opticians.db"  # Swap to postgresql://user:pass@localhost/db for PostgreSQL
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "https://*.vercel.app"]
    
    # AI API Key (Gemini / OpenAI)
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()