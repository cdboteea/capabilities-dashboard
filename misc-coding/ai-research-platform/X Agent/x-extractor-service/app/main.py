"""Main FastAPI application for X Post Content Extraction Service."""

import time
from datetime import datetime
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import structlog

from .config import settings
from .models import (
    ExtractRequest, ExtractResponse, HealthResponse, ErrorResponse,
    PostContent
)
from .extractor import XPostExtractor
from .logging_config import configure_logging
from .rate_limiter import rate_limit_middleware, limiter, rate_limit_exceeded_handler
from .error_handlers import get_error_handlers, ServiceError, ExtractionError

# Configure logging
configure_logging()
logger = structlog.get_logger()

# Application startup time
startup_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting X Post Content Extraction Service", version=settings.app_version)
    yield
    logger.info("Shutting down X Post Content Extraction Service")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A microservice for extracting content from X (Twitter) posts",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for microservice integration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Add slowapi limiter
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

# Add error handlers
error_handlers = get_error_handlers()
for exception_type, handler in error_handlers.items():
    app.add_exception_handler(exception_type, handler)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=round(process_time, 4)
        )
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time=round(process_time, 4)
        )
        raise


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - startup_time
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        uptime=uptime
    )


@app.post("/api/extract", response_model=ExtractResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}seconds")
async def extract_posts(request: Request, extract_request: ExtractRequest):
    """Extract content from X post URLs."""
    logger.info("Extraction request received", url_count=len(extract_request.urls))
    
    if not extract_request.urls:
        raise ServiceError("No URLs provided", status_code=400)
    
    if len(extract_request.urls) > 50:  # Limit batch size
        raise ServiceError("Too many URLs provided (maximum 50)", status_code=400)
    
    # Validate URLs
    for url in extract_request.urls:
        if not url.strip():
            raise ServiceError("Empty URL provided", status_code=400)
        
        if not any(domain in url.lower() for domain in ['x.com', 'twitter.com']):
            raise ServiceError(f"Invalid URL: {url}. Only X/Twitter URLs are supported.", status_code=400)
    
    posts: List[PostContent] = []
    errors: List[Dict[str, Any]] = []
    
    try:
        async with XPostExtractor() as extractor:
            extracted_posts = await extractor.extract_multiple_posts(extract_request.urls)
            
            # Process results
            for i, url in enumerate(extract_request.urls):
                if i < len(extracted_posts) and extracted_posts[i] is not None:
                    posts.append(extracted_posts[i])
                else:
                    errors.append({
                        "url": url,
                        "error": "Failed to extract content",
                        "timestamp": datetime.now().isoformat()
                    })
    
    except Exception as e:
        logger.error("Extraction failed", error=str(e), exc_info=True)
        
        # Add error for all URLs if extraction completely failed
        for url in extract_request.urls:
            errors.append({
                "url": url,
                "error": f"Extraction service error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    success = len(posts) > 0 or len(errors) == 0
    
    logger.info(
        "Extraction completed",
        success=success,
        posts_extracted=len(posts),
        errors_count=len(errors)
    )
    
    return ExtractResponse(
        success=success,
        posts=posts,
        errors=errors
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "extract": "/api/extract",
            "docs": "/docs" if settings.debug else "disabled"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

