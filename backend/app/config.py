import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SAP Job Failure Resolution Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite:///./sap_jobs.db"
    
    # SAP Mock / Real BTP configuration
    JOB_PLATFORM: str = "mock"  # "mock" or "sap_btp"
    SAP_MODE: str = "MOCK"  # MOCK or S4HANA
    SAP_BASE_URL: str = "http://localhost:8000/mock-sap"
    SAP_CLIENT_ID: str = ""
    SAP_CLIENT_SECRET: str = ""
    SAP_TOKEN_URL: str = ""
    SAP_JOB_LOOKBACK_MINUTES: int = 30
    SAP_JOB_MAX_RUNS: int = 100
    
    # AI Config
    AI_PROVIDER: str = "FALLBACK" # GEMINI, GROQ, FALLBACK
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Deduplication / Idempotency
    EVENT_DEDUPLICATION_TTL: int = 3600 # 1 hour
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
