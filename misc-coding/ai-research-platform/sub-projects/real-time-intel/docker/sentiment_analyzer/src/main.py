from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response as PrometheusResponse

from .config import settings
from .models.sentiment_models import (
    BatchSentimentRequest,
    SentimentRequest,
    SentimentResponse,
)
from .processors.sentiment_engine import get_engine
from .services.background_tasks import task_manager
from .utils.database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sentiment_analyzer")

# Prometheus metrics
REQUEST_COUNT = Counter('sentiment_requests_total', 'Total sentiment analysis requests', ['endpoint', 'method'])
REQUEST_DURATION = Histogram('sentiment_request_duration_seconds', 'Request duration', ['endpoint'])
ANALYSIS_COUNT = Counter('sentiment_analysis_total', 'Total sentiment analyses performed', ['type'])
ANALYSIS_DURATION = Histogram('sentiment_analysis_duration_seconds', 'Analysis duration', ['type'])

app = FastAPI(
    title="Sentiment Analyzer",
    version="1.0.0",
    description="Real-time sentiment analysis service with financial context"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record metrics
    REQUEST_COUNT.labels(endpoint=request.url.path, method=request.method).inc()
    REQUEST_DURATION.labels(endpoint=request.url.path).observe(process_time)
    
    return response


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    await db.connect()
    await task_manager.start_workers(num_workers=2)
    
    # Initialize sentiment engine
    engine = get_engine()
    await engine._load()
    
    logger.info("Sentiment Analyzer service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await task_manager.stop_workers()
    await db.close()
    logger.info("Sentiment Analyzer service shutdown complete")


# Health and monitoring endpoints
@app.get("/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sentiment-analyzer",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@app.get("/v1/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return PrometheusResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/status")
async def service_status():
    """Detailed service status."""
    queue_status = task_manager.get_queue_status()
    
    return {
        "service": "sentiment-analyzer",
        "status": "running",
        "database_connected": db._pool is not None,
        "background_tasks": queue_status,
        "models_loaded": get_engine()._sentiment_pipe is not None,
        "timestamp": time.time()
    }


# Core sentiment analysis endpoints
@app.post("/v1/analyze/text", response_model=SentimentResponse)
async def analyze_text(req: SentimentRequest):
    """Analyze sentiment of a single text."""
    start_time = time.time()
    
    try:
        engine = get_engine()
        result = await engine.analyze(req.text, req.entities)
        
        # Record metrics
        duration = time.time() - start_time
        ANALYSIS_COUNT.labels(type="single").inc()
        ANALYSIS_DURATION.labels(type="single").observe(duration)
        
        return SentimentResponse(results=[result])
        
    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@app.post("/v1/analyze/batch", response_model=SentimentResponse)
async def analyze_batch(req: BatchSentimentRequest):
    """Analyze sentiment of multiple texts."""
    start_time = time.time()
    
    try:
        engine = get_engine()
        results = await engine.analyze_batch(req.texts, req.entities)
        
        # Record metrics
        duration = time.time() - start_time
        ANALYSIS_COUNT.labels(type="batch").inc(len(req.texts))
        ANALYSIS_DURATION.labels(type="batch").observe(duration)
        
        return SentimentResponse(results=results)
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Batch analysis failed")


@app.post("/v1/analyze/event")
async def analyze_event(event_id: str, text: str, entities: List[str] = None, sector: str = None):
    """Analyze sentiment for a specific event and save to database."""
    try:
        task_id = await task_manager.submit_event_analysis(event_id, text, entities, sector)
        
        return {
            "task_id": task_id,
            "event_id": event_id,
            "status": "submitted",
            "message": "Event sentiment analysis submitted for background processing"
        }
        
    except Exception as e:
        logger.error(f"Event analysis submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit analysis")


@app.post("/v1/analyze/batch-background")
async def analyze_batch_background(req: BatchSentimentRequest):
    """Submit batch analysis as background task."""
    try:
        task_id = await task_manager.submit_batch_analysis(req.texts, req.entities)
        
        return {
            "task_id": task_id,
            "batch_size": len(req.texts),
            "status": "submitted",
            "message": "Batch sentiment analysis submitted for background processing"
        }
        
    except Exception as e:
        logger.error(f"Background batch analysis submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit batch analysis")


# Task management endpoints
@app.get("/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a background task."""
    task_status = task_manager.get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_status


@app.get("/v1/tasks")
async def get_queue_status():
    """Get background task queue status."""
    return task_manager.get_queue_status()


# Database query endpoints
@app.get("/v1/sentiment/{event_id}")
async def get_event_sentiment(event_id: str):
    """Get sentiment analysis results for an event."""
    try:
        rows = await db.get_sentiment(event_id)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Sentiment data not found")
        
        return JSONResponse(content=rows)
        
    except Exception as e:
        logger.error(f"Failed to retrieve sentiment for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/v1/sentiment/search")
async def search_sentiment(
    limit: int = 50,
    offset: int = 0,
    min_confidence: float = 0.0,
    sentiment_range: str = None  # e.g., "positive", "negative", "neutral"
):
    """Search sentiment analysis results with filters."""
    try:
        # This would need to be implemented in the database utility
        # For now, return a placeholder
        return {
            "results": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "Search functionality coming soon"
        }
        
    except Exception as e:
        logger.error(f"Sentiment search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# Maintenance endpoints
@app.post("/v1/admin/cleanup-tasks")
async def cleanup_old_tasks(max_age_hours: int = 24):
    """Clean up old completed/failed tasks."""
    try:
        await task_manager.cleanup_old_tasks(max_age_hours)
        
        return {
            "status": "success",
            "message": f"Cleaned up tasks older than {max_age_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Task cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


@app.get("/v1/admin/stats")
async def get_service_stats():
    """Get detailed service statistics."""
    queue_status = task_manager.get_queue_status()
    
    return {
        "service": "sentiment-analyzer",
        "uptime_seconds": time.time(),  # Would need to track actual uptime
        "queue_status": queue_status,
        "database_pool_size": db._pool.get_size() if db._pool else 0,
        "models_loaded": {
            "sentiment_pipeline": get_engine()._sentiment_pipe is not None,
            "vader_analyzer": get_engine()._vader_analyzer is not None
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port) 