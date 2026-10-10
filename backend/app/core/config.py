import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "CivitasID"
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Caching
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "86400")) # 24 hours
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ENABLE_TELEGRAM_BOT: bool = os.getenv("ENABLE_TELEGRAM_BOT", "false").lower() in ("true", "1", "yes")
    
    # Security & CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Upstream PDDIKTI
    PDDIKTI_BASE_URL: str = "https://pddikti.kemdiktisaintek.go.id"

settings = Settings()
