from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    MAX_BOT_TOKEN: str

    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""

    # Notification thresholds (days)
    EXPIRY_URGENT_THRESHOLD: int = 16
    EXPIRY_PLANNED_THRESHOLD: int = 46

    # Notification schedule
    NOTIFICATION_TIME: str = "09:00"          # HH:MM
    NOTIFICATION_BASE_DAY: str = "sunday"
    NOTIFICATION_MAX_PER_WEEK: int = 6

    class Config:
        env_file = ".env"


settings = Settings()
