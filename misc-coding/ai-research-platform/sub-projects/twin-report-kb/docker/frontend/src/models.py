"""Pydantic models for Twin-Report KB Frontend."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AnalysisDepth(str, Enum):
    """Analysis depth options."""
    QUICK = "quick"
    COMPREHENSIVE = "comprehensive"
    DETAILED = "detailed"


class DocumentType(str, Enum):
    """Document type enumeration."""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    TXT = "txt"
    HTML = "html"
    URL = "url"
    GOOGLE_DOC = "google_doc"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PARSING = "parsing"
    CATEGORIZING = "categorizing"
    QUALITY_CHECK = "quality_check"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# Service Health Models
class ServiceHealthResponse(BaseModel):
    """Response model for service health check."""
    service: str
    status: ServiceStatus
    response_time: Optional[float] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemHealthResponse(BaseModel):
    """Response model for overall system health."""
    services: Dict[str, ServiceHealthResponse]
    overall_status: ServiceStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Document Models
class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    analysis_depth: AnalysisDepth = AnalysisDepth.COMPREHENSIVE
    categories: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class URLParseRequest(BaseModel):
    """Request model for URL parsing."""
    url: str
    analysis_depth: AnalysisDepth = AnalysisDepth.COMPREHENSIVE
    categories: Optional[List[str]] = None


class GoogleDocParseRequest(BaseModel):
    """Request model for Google Doc parsing."""
    doc_id: str
    analysis_depth: AnalysisDepth = AnalysisDepth.COMPREHENSIVE
    categories: Optional[List[str]] = None


class BatchProcessRequest(BaseModel):
    """Request model for batch processing."""
    analysis_depth: AnalysisDepth = AnalysisDepth.COMPREHENSIVE
    categories: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


# Processing Models
class ProcessingTask(BaseModel):
    """Model for tracking processing tasks."""
    task_id: str
    document_id: Optional[str] = None
    status: ProcessingStatus
    current_step: str
    progress: float = Field(ge=0, le=100)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentResult(BaseModel):
    """Model for document processing results."""
    document_id: str
    filename: Optional[str] = None
    document_type: DocumentType
    content: str
    metadata: Dict[str, Any]
    categories: List[str]
    quality_score: Optional[float] = None
    gap_analysis: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Analysis Models
class QualityAssessment(BaseModel):
    """Model for quality assessment results."""
    overall_score: float = Field(ge=0, le=100)
    completeness: float = Field(ge=0, le=100)
    accuracy: float = Field(ge=0, le=100)
    usefulness: float = Field(ge=0, le=100)
    coherence: float = Field(ge=0, le=100)
    suggestions: List[str]
    flagged_issues: List[str]


class GapAnalysis(BaseModel):
    """Model for gap analysis results."""
    gaps_found: List[Dict[str, Any]]
    priority_score: float = Field(ge=0, le=100)
    recommendations: List[str]
    comparative_analysis: Dict[str, Any]


class TopicCategories(BaseModel):
    """Model for topic categorization results."""
    primary_category: str
    secondary_categories: List[str]
    confidence_scores: Dict[str, float]
    keywords: List[str]
    topics: List[str]


# Dashboard Models
class DashboardStats(BaseModel):
    """Model for dashboard statistics."""
    total_documents: int
    documents_today: int
    processing_queue: int
    average_processing_time: float
    success_rate: float
    service_health: Dict[str, ServiceStatus]


class RecentActivity(BaseModel):
    """Model for recent activity display."""
    document_id: str
    filename: str
    status: ProcessingStatus
    timestamp: datetime
    processing_time: Optional[float] = None


# Response Models
class APIResponse(BaseModel):
    """Generic API response model."""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FileUploadResponse(APIResponse):
    """Response model for file upload."""
    task_id: Optional[str] = None
    document_id: Optional[str] = None


class BatchProcessResponse(APIResponse):
    """Response model for batch processing."""
    batch_id: str
    task_ids: List[str]
    total_files: int 