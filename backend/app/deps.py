from functools import lru_cache
from pydantic import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    DB_PATH: str = "./data/owlin.db"
    LICENSE_DIR: str = "./license"
    LOG_DIR: str = "./logs"
    ALLOW_ORIGINS: str = "http://localhost:3000"
    OCR_LANG: str = "en"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()

def cors_origins(settings: Settings) -> List[str]:
    raw = settings.ALLOW_ORIGINS.strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]
