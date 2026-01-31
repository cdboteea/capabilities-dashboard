"""
Real-Time Intel News Crawler - Enhanced Modular Implementation
FastAPI service with Web Actions AI Agent compatibility
"""

import os
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg
import httpx
import structlog

# Import our modules
from .models.job_config import CrawlJobConfig, CrawlJobResponse, JobStatus, JobResults
from .models.implementations import ImplementationInfo, SwitchRequest, SwitchResponse
from .implementations.browser_use import BrowserUseAdapter
from .implementations.web_actions_ai import WebActionsAIAdapter
from .implementations.base import BaseCrawlerAdapter
from .utils.quality_scorer import QualityScorer
from .utils.database import DatabaseManager
from .websocket_manager import WebSocketManager

# Configure structured logging
logger = structlog.get_logger()

# Global variables
db_manager: DatabaseManager = None
websocket_manager: WebSocketManager = None
active_implementations: Dict[str, BaseCrawlerAdapter] = {}
current_implementation = "browser_use"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, websocket_manager, active_implementations
    
    # Startup
    logger.info("Starting Real-Time Intel News Crawler")
    
    # Initialize database connection
    db_manager = DatabaseManager(os.getenv("DATABASE_URL"))
    await db_manager.initialize()
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    
    # Initialize available implementations
    active_implementations = {
        "browser_use": BrowserUseAdapter(),
        "web_actions_ai": WebActionsAIAdapter()
    }
    
    # Initialize implementations
    for name, adapter in active_implementations.items():
        try:
            await adapter.initialize()
            logger.info(f"Initialized {name} implementation")
        except Exception as e:
            logger.error(f"Failed to initialize {name}: {e}")
    
    logger.info("News Crawler started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down News Crawler")
    
    # Cleanup implementations
    for adapter in active_implementations.values():
        await adapter.cleanup()
    
    # Close database connection
    if db_manager:
        await db_manager.close()
    
    logger.info("News Crawler shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Real-Time Intel News Crawler",
    description="Enhanced modular news crawler with Web Actions AI Agent compatibility",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    global current_implementation, active_implementations
    
    try:
        # Check database connection
        db_healthy = await db_manager.health_check()
        
        # Check current implementation
        impl_healthy = False
        if current_implementation in active_implementations:
            impl_healthy = await active_implementations[current_implementation].health_check()
        
        status = "healthy" if (db_healthy and impl_healthy) else "degraded"
        
        return {
            "status": status,
            "implementation": current_implementation,
            "version": "1.0.0",
            "uptime_seconds": int((datetime.now() - app.state.start_time).total_seconds()) if hasattr(app.state, 'start_time') else 0,
            "active_crawls": websocket_manager.active_connections,
            "last_crawl": None,  # TODO: Get from database
            "database_healthy": db_healthy,
            "implementation_healthy": impl_healthy
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/v1/crawl/jobs", response_model=CrawlJobResponse)
async def submit_crawl_job(
    job_config: CrawlJobConfig,
    background_tasks: BackgroundTasks
):
    """Submit a new crawl job"""
    global current_implementation, active_implementations
    
    try:
        # Generate job ID
        job_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Get current implementation
        if current_implementation not in active_implementations:
            raise HTTPException(status_code=500, detail=f"Implementation {current_implementation} not available")
        
        adapter = active_implementations[current_implementation]
        
        # Create job record in database
        await db_manager.create_crawl_job(job_id, job_config.dict(), current_implementation)
        
        # Start crawl job in background
        background_tasks.add_task(execute_crawl_job, job_id, job_config, adapter)
        
        # Return response
        response = CrawlJobResponse(
            job_id=job_id,
            status="submitted",
            estimated_duration="00:08:30",  # Default estimate
            estimated_articles=job_config.source_config.parameters.max_articles,
            created_at=datetime.now(),
            implementation=current_implementation,
            tracking_url=f"/v1/crawl/jobs/{job_id}",
            websocket_url=f"ws://localhost:8300/v1/crawl/jobs/{job_id}/stream"
        )
        
        logger.info(f"Crawl job submitted: {job_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to submit crawl job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/crawl/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        status = await db_manager.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatus(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/crawl/jobs/{job_id}/results", response_model=JobResults)
async def get_job_results(
    job_id: str,
    format: str = "json",
    include: str = "metadata,content,sentiment,entities",
    page: int = 1,
    limit: int = 50
):
    """Get job results"""
    try:
        results = await db_manager.get_job_results(job_id, page, limit, include.split(","))
        if not results:
            raise HTTPException(status_code=404, detail="Job results not found")
        
        return JobResults(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/v1/crawl/jobs/{job_id}/stream")
async def websocket_job_stream(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job updates"""
    await websocket_manager.connect(websocket, job_id)
    try:
        while True:
            # Keep connection alive and handle any client messages
            message = await websocket.receive_text()
            # Echo back for now, could implement commands later
            await websocket.send_json({"type": "ack", "message": message})
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, job_id)

@app.get("/v1/implementations", response_model=List[ImplementationInfo])
async def get_implementations():
    """List available implementations"""
    global active_implementations, current_implementation
    
    implementations = []
    
    for name, adapter in active_implementations.items():
        try:
            info = await adapter.get_implementation_info()
            info.status = "available" if await adapter.health_check() else "unavailable"
            implementations.append(info)
        except Exception as e:
            logger.error(f"Failed to get info for {name}: {e}")
    
    return {
        "implementations": implementations,
        "current_default": current_implementation,
        "switching_enabled": True,
        "hot_swap_supported": True
    }

@app.post("/v1/implementations/switch", response_model=SwitchResponse)
async def switch_implementation(
    switch_request: SwitchRequest,
    background_tasks: BackgroundTasks
):
    """Switch between implementations"""
    global current_implementation, active_implementations
    
    try:
        target = switch_request.target_implementation
        
        if target not in active_implementations:
            raise HTTPException(status_code=400, detail=f"Implementation {target} not available")
        
        # Generate switch ID
        switch_id = f"switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Perform switch in background
        if switch_request.migration_strategy == "immediate":
            current_implementation = target
            logger.info(f"Implementation switched to {target}")
            
            return SwitchResponse(
                switch_id=switch_id,
                status="completed",
                current_implementation=current_implementation,
                target_implementation=target,
                estimated_downtime="00:00:30",
                test_job_submitted=False,
                rollback_available=True
            )
        else:
            # Gradual switch - implement logic here
            background_tasks.add_task(perform_gradual_switch, switch_id, target, switch_request)
            
            return SwitchResponse(
                switch_id=switch_id,
                status="in_progress",
                current_implementation=current_implementation,
                target_implementation=target,
                estimated_downtime="00:02:30",
                test_job_submitted=switch_request.test_job_first,
                rollback_available=True
            )
            
    except Exception as e:
        logger.error(f"Failed to switch implementation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def execute_crawl_job(job_id: str, job_config: CrawlJobConfig, adapter: BaseCrawlerAdapter):
    """Execute a crawl job"""
    try:
        logger.info(f"Starting crawl job: {job_id}")
        
        # Update job status
        await db_manager.update_job_status(job_id, "running")
        await websocket_manager.broadcast_to_job(job_id, {
            "type": "progress_update",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "status": "starting",
                "articles_processed": 0,
                "estimated_remaining": "calculating..."
            }
        })
        
        # Execute crawl using the adapter
        async for update in adapter.execute_crawl(job_id, job_config):
            # Update database
            await db_manager.update_job_progress(job_id, update)
            
            # Broadcast via WebSocket
            await websocket_manager.broadcast_to_job(job_id, {
                "type": "progress_update",
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "data": update
            })
            
            # If article extracted, broadcast that too
            if update.get("type") == "article_extracted":
                await websocket_manager.broadcast_to_job(job_id, {
                    "type": "article_extracted",
                    "job_id": job_id,
                    "timestamp": datetime.now().isoformat(),
                    "data": update["article_data"]
                })
        
        # Mark job as completed
        await db_manager.update_job_status(job_id, "completed")
        await websocket_manager.broadcast_to_job(job_id, {
            "type": "progress_update",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "status": "completed",
                "completion_time": datetime.now().isoformat()
            }
        })
        
        logger.info(f"Crawl job completed: {job_id}")
        
    except Exception as e:
        logger.error(f"Crawl job failed: {job_id} - {e}")
        
        # Mark job as failed
        await db_manager.update_job_status(job_id, "failed", str(e))
        await websocket_manager.broadcast_to_job(job_id, {
            "type": "error",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "status": "failed",
                "error": str(e)
            }
        })

async def perform_gradual_switch(switch_id: str, target_implementation: str, switch_request: SwitchRequest):
    """Perform gradual implementation switch"""
    global current_implementation
    
    try:
        logger.info(f"Starting gradual switch to {target_implementation}")
        
        # Test job first if requested
        if switch_request.test_job_first:
            # TODO: Implement test job logic
            await asyncio.sleep(30)  # Simulate test
        
        # Perform switch
        await asyncio.sleep(60)  # Simulate gradual migration
        current_implementation = target_implementation
        
        logger.info(f"Gradual switch completed to {target_implementation}")
        
    except Exception as e:
        logger.error(f"Gradual switch failed: {e}")
        if switch_request.fallback_on_failure:
            logger.info("Rolling back due to failure")

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Set startup time for health checks"""
    app.state.start_time = datetime.now()
    logger.info("Real-Time Intel News Crawler API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300) 