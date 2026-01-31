"""Configuration settings for the X Post Content Extraction Service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    app_name: str = "X Post Content Extraction Service"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 3000
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour in seconds
    
    # Request timeout settings
    request_timeout: int = 30
    max_concurrent_requests: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Redis configuration (optional, for rate limiting)
    redis_url: Optional[str] = None
    
    # User agent for web scraping
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

