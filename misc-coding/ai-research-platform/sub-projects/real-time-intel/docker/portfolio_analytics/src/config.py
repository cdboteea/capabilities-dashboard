"""Configuration management for Portfolio Analytics service."""

import os
from typing import List, Dict, Any
from pydantic import BaseSettings, Field
import yaml


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="ai_research_platform", env="DB_NAME")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    pool_size: int = 10
    max_overflow: int = 20
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseSettings):
    """Redis configuration."""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = 4
    password: str = Field(default="", env="REDIS_PASSWORD")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class ServicesConfig(BaseSettings):
    """External services configuration."""
    price_fetcher_url: str = "http://price-fetcher:8306"
    holdings_router_url: str = "http://holdings-router:8305"
    sentiment_analyzer_url: str = "http://sentiment-analyzer:8304"


class AnalyticsConfig(BaseSettings):
    """Analytics calculation configuration."""
    risk_free_rate: float = 0.02
    trading_days_per_year: int = 252
    benchmark_symbol: str = "SPY"
    
    short_term_days: int = 30
    medium_term_days: int = 90
    long_term_days: int = 365
    
    var_confidence: float = 0.05
    cvar_confidence: float = 0.05
    max_lookback_days: int = 252
    
    min_correlation_threshold: float = 0.3
    lookback_periods: List[int] = [30, 90, 252]
    
    sector_weights_threshold: float = 0.05
    factor_analysis_enabled: bool = True


class CalculationsConfig(BaseSettings):
    """Calculation settings configuration."""
    cache_ttl_seconds: int = 3600
    batch_size: int = 100
    
    real_time_update_seconds: int = 300
    daily_update_hour: int = 6
    weekly_update_day: int = 1
    
    significant_return_threshold: float = 0.05
    significant_volatility_threshold: float = 0.20


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9308
    health_check_interval: int = 30
    performance_logging: bool = True


class PortfolioAnalyticsConfig(BaseSettings):
    """Main Portfolio Analytics configuration."""
    host: str = "0.0.0.0"
    port: int = 8308
    debug: bool = False
    log_level: str = "INFO"
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    services: ServicesConfig = ServicesConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()
    calculations: CalculationsConfig = CalculationsConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config/config.yml") -> "PortfolioAnalyticsConfig":
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                analytics_config = config_data.get('portfolio_analytics', {})
                return cls(**analytics_config)
        return cls()


# Global configuration instance
config = PortfolioAnalyticsConfig.load_from_yaml() 