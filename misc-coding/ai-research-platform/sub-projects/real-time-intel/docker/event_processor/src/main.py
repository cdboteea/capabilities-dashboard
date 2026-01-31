"""
Event Processor Service - FastAPI Application
Intelligent event classification, enrichment, and routing
"""

import asyncio
import os
import time
import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .models import (
    EventProcessingRequest, EventProcessingResponse, BatchProcessingRequest,
    BatchProcessingResponse, EventQuery, EventListResponse, ProcessingStatsResponse,
    NewsEvent, ProcessingStatus, EventType, EventSeverity, EventUrgency
)
from .processors.classifier import EventClassifier
from .processors.enricher import ContentEnricher
from .processors.entity_extractor import EntityExtractor
from .processors.severity_assessor import SeverityAssessor
from .processors.router import EventRouter
from .utils.database import DatabaseManager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global service instances
classifier: Optional[EventClassifier] = None
enricher: Optional[ContentEnricher] = None
entity_extractor: Optional[EntityExtractor] = None
severity_assessor: Optional[SeverityAssessor] = None
router: Optional[EventRouter] = None
db_manager: Optional[DatabaseManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Event Processor Service")
    
    try:
        # Initialize global services
        global classifier, enricher, entity_extractor, severity_assessor, router, db_manager
        
        # Database connection
        db_connection_string = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:password@postgres:5432/real_time_intel"
        )
        
        db_manager = DatabaseManager(db_connection_string)
        await db_manager.initialize()
        
        # Mac Studio LLM endpoint
        mac_studio_endpoint = os.getenv("MAC_STUDIO_ENDPOINT", "http://10.0.0.100:8000")
        
        # Initialize processing components
        classifier = EventClassifier(mac_studio_endpoint)
        await classifier.initialize()
        
        enricher = ContentEnricher(mac_studio_endpoint)
        await enricher.initialize()
        
        entity_extractor = EntityExtractor(mac_studio_endpoint)
        await entity_extractor.initialize()
        
        severity_assessor = SeverityAssessor(mac_studio_endpoint)
        await severity_assessor.initialize()
        
        router = EventRouter(mac_studio_endpoint)
        await router.initialize()
        
        logger.info("Event Processor Service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize Event Processor Service", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Event Processor Service")
    
    try:
        # Close all services
        if classifier:
            await classifier.close()
        if enricher:
            await enricher.close()
        if entity_extractor:
            await entity_extractor.close()
        if severity_assessor:
            await severity_assessor.close()
        if router:
            await router.close()
        if db_manager:
            await db_manager.close()
        
        logger.info("Event Processor Service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))

# Create FastAPI application
app = FastAPI(
    title="Event Processor Service",
    description="Intelligent event classification, enrichment, and routing for Real-Time Intel",
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

# Dependency to get database manager
async def get_db() -> DatabaseManager:
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_manager

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        if db_manager:
            async with db_manager.get_connection() as conn:
                await conn.execute('SELECT 1')
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "event_processor",
            "version": "1.0.0",
            "components": {
                "database": "healthy" if db_manager else "unavailable",
                "classifier": "healthy" if classifier and classifier.model_loaded else "unavailable",
                "enricher": "healthy" if enricher and enricher.models_loaded else "unavailable",
                "entity_extractor": "healthy" if entity_extractor and entity_extractor.models_loaded else "unavailable",
                "severity_assessor": "healthy" if severity_assessor else "unavailable",
                "router": "healthy" if router else "unavailable"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Event processing endpoints

@app.post("/process", response_model=EventProcessingResponse)
async def process_event(
    request: EventProcessingRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db)
):
    """Process a single news event"""
    logger.info("Processing event request", article_id=request.article_id)
    
    start_time = time.time()
    
    try:
        # Create initial event record
        event = NewsEvent(
            article_id=request.article_id,
            source_id=request.source_id,
            title=request.title,
            content=request.content,
            url=request.url,
            published_at=request.published_at,
            author=request.author,
            status=ProcessingStatus.PENDING
        )
        
        # Store initial event
        event_id = await db.store_event(event)
        event.event_id = event_id
        
        # Process in background
        background_tasks.add_task(
            process_event_pipeline,
            event, request, db
        )
        
        processing_time = time.time() - start_time
        
        return EventProcessingResponse(
            event_id=event_id,
            status=ProcessingStatus.PROCESSING,
            message="Event queued for processing",
            processing_time=processing_time,
            stages_completed=["queued"]
        )
        
    except Exception as e:
        logger.error("Failed to queue event for processing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/batch", response_model=BatchProcessingResponse)
async def process_batch(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db)
):
    """Process multiple events in batch"""
    logger.info("Processing batch request", batch_size=len(request.events))
    
    start_time = time.time()
    
    try:
        batch_id = request.batch_id or f"batch_{int(time.time())}"
        
        # Queue each event for processing
        event_responses = []
        for event_request in request.events:
            # Create initial event record
            event = NewsEvent(
                article_id=event_request.article_id,
                source_id=event_request.source_id,
                title=event_request.title,
                content=event_request.content,
                url=event_request.url,
                published_at=event_request.published_at,
                author=event_request.author,
                status=ProcessingStatus.PENDING
            )
            
            # Store initial event
            event_id = await db.store_event(event)
            event.event_id = event_id
            
            # Process in background
            background_tasks.add_task(
                process_event_pipeline,
                event, event_request, db
            )
            
            event_responses.append(EventProcessingResponse(
                event_id=event_id,
                status=ProcessingStatus.PROCESSING,
                message="Event queued for processing",
                processing_time=0.0,
                stages_completed=["queued"]
            ))
        
        processing_time = time.time() - start_time
        
        return BatchProcessingResponse(
            batch_id=batch_id,
            total_events=len(request.events),
            successful_events=len(request.events),
            failed_events=0,
            processing_time=processing_time,
            events_per_second=len(request.events) / processing_time if processing_time > 0 else 0,
            processed_events=event_responses,
            classification_summary={},
            severity_summary={}
        )
        
    except Exception as e:
        logger.error("Failed to process batch", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

async def process_event_pipeline(
    event: NewsEvent, 
    request: EventProcessingRequest, 
    db: DatabaseManager
):
    """Background event processing pipeline"""
    try:
        logger.info("Starting event processing pipeline", event_id=event.event_id)
        
        # Update status to processing
        await db.update_event_status(event.event_id, ProcessingStatus.PROCESSING)
        
        stages_completed = []
        
        # Stage 1: Classification
        if request.enable_classification and classifier:
            logger.info("Classifying event", event_id=event.event_id)
            event.classification = await classifier.classify_event(event)
            stages_completed.append("classification")
            await db.update_event_status(event.event_id, ProcessingStatus.CLASSIFIED)
        
        # Stage 2: Entity Extraction
        entities = []
        if request.enable_entity_extraction and entity_extractor:
            logger.info("Extracting entities", event_id=event.event_id)
            entities = await entity_extractor.extract_entities(event)
            event.entities = entities
            stages_completed.append("entity_extraction")
        
        # Stage 3: Content Enrichment
        if request.enable_enrichment and enricher:
            logger.info("Enriching content", event_id=event.event_id)
            event.enrichment = await enricher.enrich_content(event)
            stages_completed.append("enrichment")
            await db.update_event_status(event.event_id, ProcessingStatus.ENRICHED)
        
        # Stage 4: Severity Assessment
        severity_assessment = None
        if severity_assessor:
            logger.info("Assessing severity", event_id=event.event_id)
            severity_assessment = await severity_assessor.assess_severity(event, entities)
            event.severity_assessment = severity_assessment
            stages_completed.append("severity_assessment")
        
        # Stage 5: Routing Decision
        if request.enable_routing and router and severity_assessment:
            logger.info("Determining routing", event_id=event.event_id)
            event.routing = await router.route_event(event, entities, severity_assessment)
            stages_completed.append("routing")
            await db.update_event_status(event.event_id, ProcessingStatus.ROUTED)
        
        # Final status update
        event.status = ProcessingStatus.COMPLETED
        await db.store_event(event)  # Store complete event
        
        logger.info("Event processing pipeline completed", 
                   event_id=event.event_id,
                   stages=stages_completed)
        
    except Exception as e:
        logger.error("Event processing pipeline failed", 
                    error=str(e), 
                    event_id=event.event_id)
        
        # Update status to failed
        await db.update_event_status(
            event.event_id, 
            ProcessingStatus.FAILED, 
            error_details=str(e)
        )

# Event retrieval endpoints

@app.get("/events/{event_id}", response_model=NewsEvent)
async def get_event(
    event_id: str,
    db: DatabaseManager = Depends(get_db)
):
    """Get event by ID"""
    try:
        event = await db.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve event", error=str(e), event_id=event_id)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve event: {str(e)}")

@app.get("/events", response_model=EventListResponse)
async def list_events(
    db: DatabaseManager = Depends(get_db),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    event_types: Optional[List[EventType]] = Query(None, description="Event type filter"),
    severity_levels: Optional[List[EventSeverity]] = Query(None, description="Severity filter"),
    tickers: Optional[List[str]] = Query(None, description="Ticker symbols filter"),
    keywords: Optional[List[str]] = Query(None, description="Keywords filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    sort_by: str = Query("published_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order")
):
    """List events with filters"""
    try:
        query = EventQuery(
            start_date=start_date,
            end_date=end_date,
            event_types=event_types,
            severity_levels=severity_levels,
            tickers=tickers,
            keywords=keywords,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        events = await db.search_events(query)
        total_count = await db.get_event_count(query)
        total_pages = (total_count + page_size - 1) // page_size
        
        # Calculate summary statistics
        summary = {
            "total_events": total_count,
            "page_events": len(events),
            "event_types": {},
            "severity_levels": {}
        }
        
        for event in events:
            if event.classification:
                event_type = event.classification.event_type.value
                summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
            
            if event.severity_assessment:
                severity = event.severity_assessment.severity.value
                summary["severity_levels"][severity] = summary["severity_levels"].get(severity, 0) + 1
        
        return EventListResponse(
            events=events,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary
        )
        
    except Exception as e:
        logger.error("Failed to list events", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")

# Statistics and monitoring endpoints

@app.get("/stats", response_model=ProcessingStatsResponse)
async def get_processing_stats(db: DatabaseManager = Depends(get_db)):
    """Get processing statistics"""
    try:
        stats = await db.get_processing_stats()
        return stats
        
    except Exception as e:
        logger.error("Failed to get processing stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/status/{event_id}")
async def get_event_status(
    event_id: str,
    db: DatabaseManager = Depends(get_db)
):
    """Get event processing status"""
    try:
        event = await db.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {
            "event_id": event_id,
            "status": event.status.value,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            "error_details": event.error_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get event status", error=str(e), event_id=event_id)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

# Maintenance endpoints

@app.post("/maintenance/cleanup")
async def cleanup_old_events(
    days_to_keep: int = Query(30, ge=1, le=365, description="Days to keep"),
    db: DatabaseManager = Depends(get_db)
):
    """Clean up old processed events"""
    try:
        deleted_count = await db.cleanup_old_events(days_to_keep)
        
        return {
            "message": f"Cleaned up {deleted_count} old events",
            "deleted_count": deleted_count,
            "days_to_keep": days_to_keep
        }
        
    except Exception as e:
        logger.error("Failed to cleanup old events", error=str(e))
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Configuration endpoints

@app.get("/config")
async def get_service_config():
    """Get service configuration"""
    return {
        "service": "event_processor",
        "version": "1.0.0",
        "components": {
            "classifier": {
                "enabled": classifier is not None,
                "model_loaded": classifier.model_loaded if classifier else False
            },
            "enricher": {
                "enabled": enricher is not None,
                "models_loaded": enricher.models_loaded if enricher else False
            },
            "entity_extractor": {
                "enabled": entity_extractor is not None,
                "models_loaded": entity_extractor.models_loaded if entity_extractor else False
            },
            "severity_assessor": {
                "enabled": severity_assessor is not None
            },
            "router": {
                "enabled": router is not None
            }
        },
        "database": {
            "connected": db_manager is not None
        },
        "endpoints": {
            "process": "/process",
            "batch": "/process/batch",
            "events": "/events",
            "stats": "/stats",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8303,
        reload=True,
        log_config=None  # Use structlog instead
    ) 