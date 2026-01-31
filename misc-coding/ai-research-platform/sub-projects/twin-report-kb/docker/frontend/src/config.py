"""Configuration management for Twin-Report KB Frontend."""

import os
from typing import Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    app_name: str = "Twin-Report KB Dashboard"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 3000
    
    # Service endpoints
    document_parser_url: str = "http://localhost:8000"
    topic_manager_url: str = "http://localhost:8101"
    quality_controller_url: str = "http://localhost:8102"
    diff_worker_url: str = "http://localhost:8103"
    
    # Database settings (for direct access if needed)
    database_url: str = "postgresql://twin_report:secure_password@localhost:5432/twin_report_kb"
    
    # File upload settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: list = [
        ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".html", ".md"
    ]
    upload_dir: str = "/tmp/uploads"
    
    # Analysis settings
    default_analysis_depth: str = "comprehensive"
    batch_size_limit: int = 50
    
    class Config:
        env_file = ".env"
        # Accept either FRONTEND_* variables or direct names e.g. DOCUMENT_PARSER_URL
        env_prefix = ""


# Global settings instance
settings = Settings()

# Service endpoints mapping
SERVICES: Dict[str, str] = {
    "document_parser": settings.document_parser_url,
    "topic_manager": settings.topic_manager_url,
    "quality_controller": settings.quality_controller_url,
    "diff_worker": settings.diff_worker_url
}

# Service health endpoints
HEALTH_ENDPOINTS: Dict[str, str] = {
    "document_parser": f"{settings.document_parser_url}/health",
    "topic_manager": f"{settings.topic_manager_url}/health",
    "quality_controller": f"{settings.quality_controller_url}/health",
    "diff_worker": f"{settings.diff_worker_url}/health"
} 