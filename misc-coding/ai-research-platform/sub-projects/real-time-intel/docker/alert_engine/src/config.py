"""Configuration management for Alert Engine service."""

import os
from typing import List, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
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
    db: int = 3
    password: str = Field(default="", env="REDIS_PASSWORD")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class EmailConfig(BaseSettings):
    """Email configuration."""
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str = Field(default="", env="SMTP_USER")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    from_email: str = Field(default="alerts@research-platform.ai", env="FROM_EMAIL")
    from_name: str = "AI Research Platform"
    use_tls: bool = True


class SMSConfig(BaseSettings):
    """SMS configuration."""
    twilio_account_sid: str = Field(default="", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", env="TWILIO_AUTH_TOKEN")
    from_number: str = Field(default="", env="TWILIO_FROM_NUMBER")


class PushConfig(BaseSettings):
    """Push notification configuration."""
    fcm_server_key: str = Field(default="", env="FCM_SERVER_KEY")
    vapid_public_key: str = Field(default="", env="VAPID_PUBLIC_KEY")
    vapid_private_key: str = Field(default="", env="VAPID_PRIVATE_KEY")
    vapid_email: str = Field(default="alerts@research-platform.ai", env="VAPID_EMAIL")


class WebhookConfig(BaseSettings):
    """Webhook configuration."""
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5


class ThresholdConfig(BaseSettings):
    """Alert threshold configuration."""
    price_change_minor: float = 2.0
    price_change_moderate: float = 5.0
    price_change_major: float = 10.0
    price_change_critical: float = 20.0
    
    sentiment_very_negative: float = -0.8
    sentiment_negative: float = -0.4
    sentiment_neutral_low: float = -0.1
    sentiment_neutral_high: float = 0.1
    sentiment_positive: float = 0.4
    sentiment_very_positive: float = 0.8
    
    portfolio_impact_low: float = 1000
    portfolio_impact_medium: float = 5000
    portfolio_impact_high: float = 25000
    portfolio_impact_critical: float = 100000


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    email_per_hour: int = 50
    sms_per_hour: int = 20
    push_per_hour: int = 100
    webhook_per_hour: int = 200


class PriorityConfig(BaseSettings):
    """Alert priority configuration."""
    low_channels: List[str] = ["email"]
    low_delay_minutes: int = 30
    low_batch_size: int = 10
    
    medium_channels: List[str] = ["email", "push"]
    medium_delay_minutes: int = 5
    medium_batch_size: int = 5
    
    high_channels: List[str] = ["email", "push", "sms"]
    high_delay_minutes: int = 1
    high_batch_size: int = 1
    
    critical_channels: List[str] = ["email", "push", "sms", "webhook"]
    critical_delay_minutes: int = 0
    critical_batch_size: int = 1
    critical_immediate: bool = True


class AlertEngineConfig(BaseSettings):
    """Main Alert Engine configuration."""
    host: str = "0.0.0.0"
    port: int = 8307
    debug: bool = False
    log_level: str = "INFO"
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    email: EmailConfig = EmailConfig()
    sms: SMSConfig = SMSConfig()
    push: PushConfig = PushConfig()
    webhook: WebhookConfig = WebhookConfig()
    thresholds: ThresholdConfig = ThresholdConfig()
    rate_limits: RateLimitConfig = RateLimitConfig()
    priorities: PriorityConfig = PriorityConfig()
    
    # Template configuration
    templates_email_dir: str = "templates/email"
    templates_sms_dir: str = "templates/sms"
    templates_push_dir: str = "templates/push"
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9307
    health_check_interval: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config/config.yml") -> "AlertEngineConfig":
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                alert_config = config_data.get('alert_engine', {})
                return cls(**alert_config)
        return cls()


# Global configuration instance
config = AlertEngineConfig.load_from_yaml() 