"""Configuration settings for Price Fetcher service."""

from functools import lru_cache
from typing import List, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = "price-fetcher"
    service_port: int = 8306
    debug: bool = False
    workers: int = 4
    
    # Database configuration
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT") 
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="password", env="DB_PASSWORD")
    db_name: str = Field(default="real_time_intel", env="DB_NAME")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/2", env="REDIS_URL")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    
    # API Keys (from environment)
    alpha_vantage_api_key: str = Field(default="", env="ALPHA_VANTAGE_API_KEY")
    iex_cloud_api_key: str = Field(default="", env="IEX_CLOUD_API_KEY")
    finnhub_api_key: str = Field(default="", env="FINNHUB_API_KEY")
    
    # Data source settings
    primary_data_source: str = Field(default="yfinance", env="PRIMARY_DATA_SOURCE")
    fallback_sources: List[str] = Field(default=["alpha_vantage", "iex_cloud"], env="FALLBACK_SOURCES")
    
    # Cache settings
    default_cache_ttl: int = Field(default=300, env="DEFAULT_CACHE_TTL")  # 5 minutes
    market_hours_ttl: int = Field(default=60, env="MARKET_HOURS_TTL")    # 1 minute
    after_hours_ttl: int = Field(default=900, env="AFTER_HOURS_TTL")     # 15 minutes
    
    # Rate limiting
    yfinance_rate_limit: int = Field(default=2000, env="YFINANCE_RATE_LIMIT")  # per hour
    alpha_vantage_rate_limit: int = Field(default=5, env="ALPHA_VANTAGE_RATE_LIMIT")  # per minute
    iex_cloud_rate_limit: int = Field(default=100, env="IEX_CLOUD_RATE_LIMIT")  # per second
    finnhub_rate_limit: int = Field(default=60, env="FINNHUB_RATE_LIMIT")  # per minute
    
    # Performance settings
    max_concurrent_requests: int = Field(default=50, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    batch_size: int = Field(default=50, env="BATCH_SIZE")
    
    # Market hours (Eastern Time)
    market_timezone: str = Field(default="US/Eastern", env="MARKET_TIMEZONE")
    market_open_time: str = Field(default="09:30", env="MARKET_OPEN_TIME")
    market_close_time: str = Field(default="16:00", env="MARKET_CLOSE_TIME")
    
    # Data quality thresholds
    max_price_change_pct: float = Field(default=20.0, env="MAX_PRICE_CHANGE_PCT")
    stale_data_threshold: int = Field(default=600, env="STALE_DATA_THRESHOLD")  # seconds
    min_volume_threshold: int = Field(default=1000, env="MIN_VOLUME_THRESHOLD")
    
    # External service URLs
    holdings_router_url: str = Field(default="http://holdings-router:8305", env="HOLDINGS_ROUTER_URL")
    alert_engine_url: str = Field(default="http://alert-engine:8307", env="ALERT_ENGINE_URL")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 