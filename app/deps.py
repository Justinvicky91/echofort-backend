# app/deps.py
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    PORT: int = 8000

    DATABASE_URL: str
    JWT_SECRET: str

    OTP_PROVIDER: str = "mock"
    OTP_FROM: str = "EchoFort"
    TRIAL_HOURS: int = 48

    BILLING_PROVIDER: str = "razorpay"
    CURRENCY: str = "INR"

    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    OPENAI_API_KEY: str = "dummy-placeholder"

    AI_ENABLED: bool = True
    AI_MODE: str = "admin_only"
    AI_MONTHLY_CAP_RS: int = 2000

    ALLOW_ORIGINS: str = "*"
    ADMIN_USER_IDS_CSV: str = "1"
    ADMIN_KEY: str | None = None
    LOG_LEVEL: str = "INFO"

    APP_BOOT_MODE: str = "bare"  # bare/full toggle

    @field_validator('DATABASE_URL')
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Fix DATABASE_URL if it has the wrong password due to Railway UI bug"""
        # Known wrong password from Railway UI
        wrong_password = "cMoeoOlFKQRosoMfIMetyZqASli1JOHsm"
        # Correct password from Postgres service
        correct_password = "cMoeoOlFKQRosoMfIMetyZqASl1JlOHsm"
        
        # Replace wrong password with correct one if found
        if wrong_password in v:
            v = v.replace(wrong_password, correct_password)
        
        return v

    class Config:
        env_file = ".env"   # load local overrides if present

@lru_cache
def get_settings() -> Settings:
    return Settings()


# Database dependency for FastAPI endpoints
from fastapi import Request

async def get_db(request: Request):
    """Get database connection from app state"""
    return request.app.state.db
