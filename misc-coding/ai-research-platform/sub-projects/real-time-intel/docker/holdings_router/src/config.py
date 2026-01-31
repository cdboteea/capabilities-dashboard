"""Configuration settings for Holdings Router service."""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = "holdings-router"
    service_port: int = 8305
    debug: bool = False
    
    # Database configuration
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT") 
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="password", env="DB_PASSWORD")
    db_name: str = Field(default="real_time_intel", env="DB_NAME")
    
    # External service URLs
    event_processor_url: str = Field(default="http://event-processor:8303", env="EVENT_PROCESSOR_URL")
    sentiment_analyzer_url: str = Field(default="http://sentiment-analyzer:8304", env="SENTIMENT_ANALYZER_URL")
    alert_engine_url: str = Field(default="http://alert-engine:8307", env="ALERT_ENGINE_URL")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Performance settings
    max_concurrent_routes: int = Field(default=100, env="MAX_CONCURRENT_ROUTES")
    portfolio_cache_ttl_minutes: int = Field(default=30, env="PORTFOLIO_CACHE_TTL")
    batch_size_limit: int = Field(default=1000, env="BATCH_SIZE_LIMIT")
    
    # Routing thresholds
    critical_threshold: float = Field(default=0.8, env="CRITICAL_THRESHOLD")
    high_threshold: float = Field(default=0.6, env="HIGH_THRESHOLD") 
    medium_threshold: float = Field(default=0.4, env="MEDIUM_THRESHOLD")
    low_threshold: float = Field(default=0.2, env="LOW_THRESHOLD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
