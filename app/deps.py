# app/deps.py
from functools import lru_cache
from pydantic_settings import BaseSettings

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
    LOG_LEVEL: str = "INFO"

    APP_BOOT_MODE: str = "bare"  # bare/full toggle

    class Config:
        env_file = ".env"   # load local overrides if present

@lru_cache
def get_settings() -> Settings:
    return Settings()
