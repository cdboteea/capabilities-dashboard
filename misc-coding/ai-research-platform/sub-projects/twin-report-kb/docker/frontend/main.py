"""Twin-Report KB Frontend - Main FastAPI Application."""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

import structlog
from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.models import (
    ServiceStatus, SystemHealthResponse, DashboardStats, RecentActivity,
    DocumentUploadRequest, URLParseRequest, GoogleDocParseRequest,
    APIResponse, FileUploadResponse
)
from src.api_client import client
from src.utils import (
    generate_task_id, is_allowed_file, format_file_size, 
    create_error_response, create_success_response,
    sanitize_filename, validate_url, extract_google_doc_id
)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global state for tracking tasks and statistics
processing_tasks: Dict[str, Dict[str, Any]] = {}
dashboard_stats = {
    "total_documents": 0,
    "documents_today": 0,
    "processing_queue": 0,
    "average_processing_time": 0.0,
    "success_rate": 100.0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Twin-Report KB Frontend", version="1.0.0")
    
    # Startup
    try:
        # Test service connectivity
        health = await client.check_system_health()
        logger.info("Service health check completed", 
                   overall_status=health.overall_status.value)
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.upload_dir, exist_ok=True)
        
        logger.info("Frontend service startup completed")
        
    except Exception as e:
        logger.error("Frontend service startup failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    try:
        await client.close()
        logger.info("Frontend service shutdown completed")
    except Exception as e:
        logger.error("Frontend service shutdown failed", error=str(e))


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Web interface for Twin-Report KB document analysis system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Template context processor
async def get_template_context(request: Request) -> Dict[str, Any]:
    """Get common template context."""
    return {
        "request": request,
        "app_name": settings.app_name,
        "current_time": datetime.utcnow(),
        "processing_queue": len([t for t in processing_tasks.values() 
                               if t.get("status") not in ["completed", "failed"]])
    }


# Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Dashboard home page."""
    try:
        # Get system health
        health = await client.check_system_health()
        
        # Get recent activity (mock data for now)
        recent_activity = [
            {
                "document_id": "doc_123",
                "filename": "research_paper.pdf",
                "status": "completed",
                "timestamp": datetime.utcnow(),
                "processing_time": 45.2
            }
        ]
        
        # Update dashboard stats
        dashboard_stats.update({
            "processing_queue": len([t for t in processing_tasks.values() 
                                   if t.get("status") not in ["completed", "failed"]]),
            "service_health": {name: resp.status.value for name, resp in health.services.items()}
        })
        
        context = await get_template_context(request)
        context.update({
            "health": health,
            "stats": dashboard_stats,
            "recent_activity": recent_activity
        })
        
        return templates.TemplateResponse("index.html", context)
        
    except Exception as e:
        logger.error("Dashboard home failed", error=str(e))
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Document upload page."""
    context = await get_template_context(request)
    context.update({
        "max_file_size": format_file_size(settings.max_file_size),
        "allowed_extensions": settings.allowed_extensions
    })
    
    return templates.TemplateResponse("upload.html", context)


@app.post("/upload", response_model=FileUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    analysis_depth: str = Form("comprehensive"),
    categories: Optional[str] = Form(None)
):
    """Handle document upload and start processing."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not is_allowed_file(file.filename, settings.allowed_extensions):
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        # Read file data
        file_data = await file.read()
        
        if len(file_data) > settings.max_file_size:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        
        # Parse categories
        category_list = []
        if categories:
            category_list = [c.strip() for c in categories.split(",") if c.strip()]
        
        # Store task info
        processing_tasks[task_id] = {
            "task_id": task_id,
            "filename": safe_filename,
            "status": "pending",
            "current_step": "pending",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "analysis_depth": analysis_depth,
            "categories": category_list
        }
        
        # Start background processing
        asyncio.create_task(process_document_background(task_id, file_data, safe_filename, analysis_depth))
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            task_id=task_id,
            data={"filename": safe_filename, "size": len(file_data)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Upload failed")


@app.post("/upload/url", response_model=FileUploadResponse)
async def upload_url(request: URLParseRequest):
    """Handle URL upload and start processing."""
    try:
        # Validate URL
        if not validate_url(request.url):
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Store task info
        processing_tasks[task_id] = {
            "task_id": task_id,
            "url": request.url,
            "status": "pending",
            "current_step": "pending",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "analysis_depth": request.analysis_depth.value,
            "categories": request.categories or []
        }
        
        # Start background processing
        asyncio.create_task(process_url_background(task_id, request.url, request.analysis_depth.value))
        
        return FileUploadResponse(
            success=True,
            message="URL submitted successfully",
            task_id=task_id,
            data={"url": request.url}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("URL upload failed", url=request.url, error=str(e))
        raise HTTPException(status_code=500, detail="URL processing failed")


@app.post("/upload/google-doc", response_model=FileUploadResponse)
async def upload_google_doc(request: GoogleDocParseRequest):
    """Handle Google Doc upload and start processing."""
    try:
        # Extract and validate doc ID
        doc_id = extract_google_doc_id(request.doc_id)
        if not doc_id:
            raise HTTPException(status_code=400, detail="Invalid Google Doc ID or URL")
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Store task info
        processing_tasks[task_id] = {
            "task_id": task_id,
            "google_doc_id": doc_id,
            "status": "pending",
            "current_step": "pending",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "analysis_depth": request.analysis_depth.value,
            "categories": request.categories or []
        }
        
        # Start background processing
        asyncio.create_task(process_google_doc_background(task_id, doc_id, request.analysis_depth.value))
        
        return FileUploadResponse(
            success=True,
            message="Google Doc submitted successfully",
            task_id=task_id,
            data={"doc_id": doc_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Google Doc upload failed", doc_id=request.doc_id, error=str(e))
        raise HTTPException(status_code=500, detail="Google Doc processing failed")


@app.get("/analysis/{task_id}")
async def get_analysis_status(task_id: str):
    """Get processing status for a task."""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    return JSONResponse(content=task)


@app.get("/results/{task_id}", response_class=HTMLResponse)
async def view_results(request: Request, task_id: str):
    """View processing results."""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    
    context = await get_template_context(request)
    context.update({
        "task": task,
        "task_id": task_id
    })
    
    return templates.TemplateResponse("results.html", context)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check system health
        health = await client.check_system_health()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {name: resp.status.value for name, resp in health.services.items()},
            "overall_status": health.overall_status.value
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/health/detailed", response_class=HTMLResponse)
async def health_monitor(request: Request):
    """Detailed health monitoring page."""
    try:
        health = await client.check_system_health()
        
        context = await get_template_context(request)
        context.update({
            "health": health,
            "services": health.services
        })
        
        return templates.TemplateResponse("health.html", context)
        
    except Exception as e:
        logger.error("Health monitor failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health monitor unavailable")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings and configuration page."""
    context = await get_template_context(request)
    context.update({
        "current_settings": {
            "analysis": {
                "default_depth": settings.default_analysis_depth,
                "batch_size_limit": settings.batch_size_limit,
                "max_file_size": settings.max_file_size,
                "allowed_extensions": settings.allowed_extensions
            },
            "services": {
                "document_parser": settings.document_parser_url,
                "topic_manager": settings.topic_manager_url,
                "quality_controller": settings.quality_controller_url,
                "diff_worker": settings.diff_worker_url
            },
            "application": {
                "app_name": settings.app_name,
                "debug": settings.debug,
                "upload_dir": settings.upload_dir
            }
        }
    })
    
    return templates.TemplateResponse("settings.html", context)


@app.post("/settings/analysis")
async def update_analysis_settings(
    default_depth: str = Form(...),
    batch_size_limit: int = Form(...),
    max_file_size: int = Form(...)
):
    """Update analysis settings."""
    try:
        # Validate inputs
        if default_depth not in ["quick", "comprehensive", "detailed"]:
            raise HTTPException(status_code=400, detail="Invalid analysis depth")
        
        if batch_size_limit < 1 or batch_size_limit > 100:
            raise HTTPException(status_code=400, detail="Batch size must be between 1 and 100")
        
        if max_file_size < 1024 or max_file_size > 500 * 1024 * 1024:  # 1KB to 500MB
            raise HTTPException(status_code=400, detail="File size must be between 1KB and 500MB")
        
        # Update settings (in production, these would be persisted)
        settings.default_analysis_depth = default_depth
        settings.batch_size_limit = batch_size_limit
        settings.max_file_size = max_file_size
        
        logger.info("Analysis settings updated", 
                   depth=default_depth, 
                   batch_size=batch_size_limit, 
                   max_file_size=max_file_size)
        
        return {"success": True, "message": "Analysis settings updated successfully"}
        
    except Exception as e:
        logger.error("Failed to update analysis settings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/settings/services")
async def update_service_settings(
    document_parser_url: str = Form(...),
    topic_manager_url: str = Form(...),
    quality_controller_url: str = Form(...),
    diff_worker_url: str = Form(...)
):
    """Update service endpoint settings."""
    try:
        # Basic URL validation
        urls = {
            "document_parser": document_parser_url,
            "topic_manager": topic_manager_url,
            "quality_controller": quality_controller_url,
            "diff_worker": diff_worker_url
        }
        
        for name, url in urls.items():
            if not url.startswith(("http://", "https://")):
                raise HTTPException(status_code=400, detail=f"Invalid URL format for {name}")
        
        # Update settings
        settings.document_parser_url = document_parser_url
        settings.topic_manager_url = topic_manager_url
        settings.quality_controller_url = quality_controller_url
        settings.diff_worker_url = diff_worker_url
        
        # Update global SERVICES mapping
        from src.config import SERVICES
        SERVICES.update(urls)
        
        logger.info("Service settings updated", services=urls)
        
        return {"success": True, "message": "Service settings updated successfully"}
        
    except Exception as e:
        logger.error("Failed to update service settings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings/export/{format}")
async def export_settings(format: str):
    """Export current settings."""
    try:
        settings_data = {
            "analysis": {
                "default_depth": settings.default_analysis_depth,
                "batch_size_limit": settings.batch_size_limit,
                "max_file_size": settings.max_file_size,
                "allowed_extensions": settings.allowed_extensions
            },
            "services": {
                "document_parser": settings.document_parser_url,
                "topic_manager": settings.topic_manager_url,
                "quality_controller": settings.quality_controller_url,
                "diff_worker": settings.diff_worker_url
            },
            "application": {
                "app_name": settings.app_name,
                "debug": settings.debug,
                "upload_dir": settings.upload_dir
            },
            "exported_at": datetime.utcnow().isoformat()
        }
        
        if format.lower() == "json":
            return JSONResponse(
                content=settings_data,
                headers={"Content-Disposition": "attachment; filename=settings.json"}
            )
        else:
            raise HTTPException(status_code=400, detail="Only JSON format supported")
            
    except Exception as e:
        logger.error("Settings export failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Background processing functions

async def process_document_background(task_id: str, file_data: bytes, filename: str, analysis_depth: str):
    """Process document in background."""
    try:
        # Update status
        processing_tasks[task_id].update({
            "status": "parsing",
            "current_step": "parsing",
            "progress": 20
        })
        
        # Process through full pipeline
        result = await client.process_document_full_pipeline(
            file_data, filename, analysis_depth
        )
        
        # Update with results
        processing_tasks[task_id].update({
            "status": "completed",
            "current_step": "completed",
            "progress": 100,
            "result": result,
            "document_id": result.get("document_id"),
            "completed_at": datetime.utcnow()
        })
        
        logger.info("Document processing completed", task_id=task_id, filename=filename)
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "current_step": "failed",
            "progress": 0,
            "error": str(e),
            "failed_at": datetime.utcnow()
        })
        logger.error("Document processing failed", task_id=task_id, error=str(e))


async def process_url_background(task_id: str, url: str, analysis_depth: str):
    """Process URL in background."""
    try:
        # Update status
        processing_tasks[task_id].update({
            "status": "parsing",
            "current_step": "parsing",
            "progress": 20
        })
        
        # Process through full pipeline
        result = await client.process_url_full_pipeline(url, analysis_depth)
        
        # Update with results
        processing_tasks[task_id].update({
            "status": "completed",
            "current_step": "completed",
            "progress": 100,
            "result": result,
            "document_id": result.get("document_id"),
            "completed_at": datetime.utcnow()
        })
        
        logger.info("URL processing completed", task_id=task_id, url=url)
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "current_step": "failed",
            "progress": 0,
            "error": str(e),
            "failed_at": datetime.utcnow()
        })
        logger.error("URL processing failed", task_id=task_id, error=str(e))


async def process_google_doc_background(task_id: str, doc_id: str, analysis_depth: str):
    """Process Google Doc in background."""
    try:
        # Update status
        processing_tasks[task_id].update({
            "status": "parsing",
            "current_step": "parsing",
            "progress": 20
        })
        
        # Parse Google Doc
        parse_result = await client.parse_google_doc(doc_id)
        content = parse_result.get("content", "")
        
        # Continue with analysis pipeline
        processing_tasks[task_id].update({
            "status": "analyzing",
            "current_step": "analyzing",
            "progress": 60
        })
        
        # For now, just store parse result (full pipeline would continue here)
        result = {
            "document_id": parse_result.get("document_id"),
            "google_doc_id": doc_id,
            "content": content,
            "parse_result": parse_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update with results
        processing_tasks[task_id].update({
            "status": "completed",
            "current_step": "completed",
            "progress": 100,
            "result": result,
            "document_id": result.get("document_id"),
            "completed_at": datetime.utcnow()
        })
        
        logger.info("Google Doc processing completed", task_id=task_id, doc_id=doc_id)
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "current_step": "failed",
            "progress": 0,
            "error": str(e),
            "failed_at": datetime.utcnow()
        })
        logger.error("Google Doc processing failed", task_id=task_id, error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 