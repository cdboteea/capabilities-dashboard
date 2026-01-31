"""Configuration settings for sentiment analyzer."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service Configuration
    host: str = Field(default="0.0.0.0", env="SENTIMENT_ANALYZER_HOST")
    port: int = Field(default=8304, env="SENTIMENT_ANALYZER_PORT")
    api_version: str = Field(default="v1", env="API_VERSION")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Model Configuration
    sentiment_model_name: str = Field(default="ProsusAI/finbert", env="SENTIMENT_MODEL_NAME")
    max_batch_size: int = Field(default=16, env="MAX_BATCH_SIZE")
    model_cache_dir: str = Field(default="/app/models", env="MODEL_CACHE_DIR")
    transformers_cache: str = Field(default="/app/models/transformers", env="TRANSFORMERS_CACHE")
    
    # API Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Background Processing
    background_workers: int = Field(default=2, env="BACKGROUND_WORKERS")
    task_cleanup_hours: int = Field(default=24, env="TASK_CLEANUP_HOURS")
    
    # Performance Configuration
    torch_device: str = Field(default="cpu", env="TORCH_DEVICE")
    enable_model_parallelism: bool = Field(default=False, env="ENABLE_MODEL_PARALLELISM")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8304, env="METRICS_PORT")  # Same port as main service
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 