"""Enhanced error handling for the X Post Content Extraction Service."""

import traceback
from datetime import datetime
from typing import Dict, Any, Optional

import structlog
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .models import ErrorResponse

logger = structlog.get_logger()


class ServiceError(Exception):
    """Base exception for service-specific errors."""
    
    def __init__(self, message: str, status_code: int = 500, detail: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class ExtractionError(ServiceError):
    """Exception raised when content extraction fails."""
    
    def __init__(self, message: str, url: str, detail: Optional[str] = None):
        self.url = url
        super().__init__(message, status_code=422, detail=detail)


class ValidationError(ServiceError):
    """Exception raised when request validation fails."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, status_code=400, detail=detail)


class RateLimitError(ServiceError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, status_code=429, detail=detail)


def create_error_response(
    error_message: str,
    status_code: int = 500,
    detail: Optional[str] = None,
    request: Optional[Request] = None
) -> JSONResponse:
    """Create a standardized error response."""
    
    error_data = ErrorResponse(
        error=error_message,
        detail=detail,
        timestamp=datetime.now()
    )
    
    # Log the error
    log_data = {
        "error": error_message,
        "status_code": status_code,
        "detail": detail,
        "timestamp": error_data.timestamp.isoformat()
    }
    
    if request:
        log_data.update({
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None
        })
    
    if status_code >= 500:
        logger.error("Server error", **log_data)
    else:
        logger.warning("Client error", **log_data)
    
    return JSONResponse(
        status_code=status_code,
        content=error_data.model_dump()
    )


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Handle service-specific errors."""
    return create_error_response(
        error_message=exc.message,
        status_code=exc.status_code,
        detail=exc.detail,
        request=request
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    detail = None
    if isinstance(exc.detail, dict):
        detail = str(exc.detail)
    elif isinstance(exc.detail, str):
        detail = exc.detail
    
    return create_error_response(
        error_message="HTTP error",
        status_code=exc.status_code,
        detail=detail,
        request=request
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return create_error_response(
        error_message="Validation error",
        status_code=422,
        detail=f"Invalid request data: {error_details}",
        request=request
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    # Log the full traceback for debugging
    logger.error(
        "Unhandled exception",
        error=str(exc),
        traceback=traceback.format_exc(),
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    return create_error_response(
        error_message="Internal server error",
        status_code=500,
        detail="An unexpected error occurred. Please try again later.",
        request=request
    )


def get_error_handlers() -> Dict[Any, Any]:
    """Get all error handlers for the FastAPI app."""
    return {
        ServiceError: service_error_handler,
        HTTPException: http_exception_handler,
        ValidationError: validation_exception_handler,
        Exception: general_exception_handler
    }

