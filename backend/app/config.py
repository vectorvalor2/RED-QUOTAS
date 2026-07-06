from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API
    API_TITLE: str = "RED-QUOTAS API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database / Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Job Queue
    QUEUE_URL: str = os.getenv("QUEUE_URL", "amqp://guest:guest@localhost:5672//")
    
    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/tmp/red-quotas")
    MAX_FILE_SIZE_MB: int = 5000  # 5GB
    
    # GPU
    ENABLE_GPU: bool = os.getenv("ENABLE_GPU", "True") == "True"
    GPU_DEVICE: int = int(os.getenv("GPU_DEVICE", "0"))
    
    # Processing
    MAX_CONCURRENT_JOBS: int = 4
    DEFAULT_FPS: int = 60
    DEFAULT_DURATION: float = 5.0
    DEFAULT_RESOLUTION: str = "1920x1080"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
