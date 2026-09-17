import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CareFlow AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    
    # Security
    SECRET_KEY: str = "careflow-super-secure-production-secret-key-change-me-in-prod-32bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Database: Supports PostgreSQL (default in prod) and SQLite fallback for local test/dev
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./careflow.db")
    
    # AI settings
    AI_PROVIDER: str = "smart_agent"  # 'gemini', 'openai', or 'smart_agent'
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"
    
    # Mock EHR
    MOCK_EHR_DEFAULT_MODE: str = "NORMAL"  # NORMAL, TIMEOUT, FAILURE, UNKNOWN_OUTCOME
    MOCK_EHR_SIMULATED_LATENCY_MS: int = 200

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
