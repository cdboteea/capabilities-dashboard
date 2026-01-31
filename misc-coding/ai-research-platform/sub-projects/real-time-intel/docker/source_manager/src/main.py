"""
Source Manager Service - Main Application

FastAPI service for LLM-based source evaluation and intelligent discovery.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID
import os

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .models.source_models import (
    # Request/Response models
    EvaluateSourceRequest, EvaluateSourceResponse,
    DiscoverSourcesRequest, DiscoverSourcesResponse,
    SourceSearchRequest, SourceListResponse,
    SourceUpdateRequest, BulkEvaluationRequest, BulkEvaluationResponse,
    
    # Core models
    Source, SourceEvaluation, SourceDiscovery, DiscoveryResult,
    SourceType, SourceStatus, SourceQuality, ContentCategory,
    
    # Health and stats
    ServiceHealth, EvaluationStats
)
from .services.evaluator import SourceEvaluator
from .services.discovery import SourceDiscoveryService
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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# Global service instances
db_manager: Optional[DatabaseManager] = None
source_evaluator: Optional[SourceEvaluator] = None
discovery_service: Optional[SourceDiscoveryService] = None
config: Dict[str, Any] = {}


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file and environment variables."""
    config_path = "config/config.yml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override with environment variables
        config['database']['host'] = os.getenv('DATABASE_HOST', config['database']['host'])
        config['database']['port'] = int(os.getenv('DATABASE_PORT', config['database']['port']))
        config['database']['name'] = os.getenv('DATABASE_NAME', config['database']['name'])
        config['database']['user'] = os.getenv('DATABASE_USER', config['database']['user'])
        config['database']['password'] = os.getenv('DATABASE_PASSWORD', config['database']['password'])
        
        config['llm']['endpoint'] = os.getenv('LLM_ENDPOINT', config['llm']['endpoint'])
        config['llm']['model'] = os.getenv('LLM_MODEL', config['llm']['model'])
        
        return config
        
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global db_manager, source_evaluator, discovery_service, config
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize database
        database_url = f"postgresql://{config['database']['user']}:{config['database']['password']}@{config['database']['host']}:{config['database']['port']}/{config['database']['name']}"
        
        db_manager = DatabaseManager(
            database_url=database_url,
            pool_size=config['database']['pool_size'],
            max_overflow=config['database']['max_overflow']
        )
        await db_manager.initialize()
        
        # Initialize services
        source_evaluator = SourceEvaluator(
            db_manager=db_manager,
            llm_endpoint=config['llm']['endpoint'],
            llm_model=config['llm']['model']
        )
        
        discovery_service = SourceDiscoveryService(
            db_manager=db_manager,
            evaluator=source_evaluator
        )
        
        logger.info("Source Manager service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize service", error=str(e))
        raise
    finally:
        # Cleanup
        if source_evaluator:
            await source_evaluator.close()
        if discovery_service:
            await discovery_service.close()
        if db_manager:
            await db_manager.close()
        
        logger.info("Source Manager service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Source Manager Service",
    description="LLM-based source evaluation and intelligent discovery for Real-Time Intel platform",
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


# Dependency injection
async def get_db_manager() -> DatabaseManager:
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_manager


async def get_source_evaluator() -> SourceEvaluator:
    if not source_evaluator:
        raise HTTPException(status_code=503, detail="Source evaluator not initialized")
    return source_evaluator


async def get_discovery_service() -> SourceDiscoveryService:
    if not discovery_service:
        raise HTTPException(status_code=503, detail="Discovery service not initialized")
    return discovery_service


# Health and Status Endpoints

@app.get("/health", response_model=ServiceHealth)
async def health_check(db: DatabaseManager = Depends(get_db_manager)):
    """Get service health status."""
    try:
        health = await db.get_service_health()
        return health
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/stats", response_model=EvaluationStats)
async def get_evaluation_stats(db: DatabaseManager = Depends(get_db_manager)):
    """Get evaluation statistics."""
    try:
        stats = await db.get_evaluation_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# Source Management Endpoints

@app.get("/sources", response_model=SourceListResponse)
async def list_sources(
    query: Optional[str] = Query(None, description="Search query"),
    categories: Optional[List[ContentCategory]] = Query(None, description="Filter by categories"),
    source_types: Optional[List[SourceType]] = Query(None, description="Filter by source types"),
    quality_ratings: Optional[List[SourceQuality]] = Query(None, description="Filter by quality ratings"),
    statuses: Optional[List[SourceStatus]] = Query(None, description="Filter by status"),
    min_quality_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum quality score"),
    limit: int = Query(50, ge=1, le=500, description="Result limit"),
    offset: int = Query(0, ge=0, description="Result offset"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """List and search sources with filters."""
    try:
        sources, total = await db.search_sources(
            query=query,
            categories=categories or [],
            source_types=source_types or [],
            quality_ratings=quality_ratings or [],
            statuses=statuses or [],
            min_quality_score=min_quality_score,
            limit=limit,
            offset=offset
        )
        
        return SourceListResponse(
            sources=sources,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to list sources", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sources")


@app.get("/sources/{source_id}", response_model=Source)
async def get_source(
    source_id: UUID,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get source by ID."""
    try:
        source = await db.get_source_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source", source_id=str(source_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get source")


@app.put("/sources/{source_id}", response_model=Source)
async def update_source(
    source_id: UUID,
    update_request: SourceUpdateRequest,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Update source information."""
    try:
        # Get existing source
        source = await db.get_source_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Apply updates
        update_data = update_request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)
        
        # Save updated source
        updated_source = await db.save_source(source)
        return updated_source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source", source_id=str(source_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update source")


@app.delete("/sources/{source_id}")
async def delete_source(
    source_id: UUID,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Delete source (sets status to inactive)."""
    try:
        success = await db.update_source_status(source_id, SourceStatus.INACTIVE)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        
        return {"message": "Source deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete source", source_id=str(source_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete source")


# Source Evaluation Endpoints

@app.post("/evaluate", response_model=EvaluateSourceResponse)
async def evaluate_source(
    request: EvaluateSourceRequest,
    background_tasks: BackgroundTasks,
    evaluator: SourceEvaluator = Depends(get_source_evaluator)
):
    """Evaluate a source for quality and reliability."""
    try:
        logger.info("Starting source evaluation", url=str(request.url))
        
        source, evaluation = await evaluator.evaluate_source(
            url=str(request.url),
            source_type=request.source_type,
            force_reevaluation=request.force_reevaluation,
            sample_articles=request.sample_articles
        )
        
        # Check if this is a new source
        is_new_source = source.created_at == source.updated_at
        
        response = EvaluateSourceResponse(
            source=source,
            evaluation=evaluation,
            is_new_source=is_new_source,
            cached=False  # Would track actual cache usage
        )
        
        logger.info("Source evaluation completed", 
                   url=str(request.url), 
                   quality_score=evaluation.quality_score.overall_score)
        
        return response
        
    except Exception as e:
        logger.error("Source evaluation failed", url=str(request.url), error=str(e))
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/evaluate/bulk", response_model=BulkEvaluationResponse)
async def bulk_evaluate_sources(
    request: BulkEvaluationRequest,
    background_tasks: BackgroundTasks,
    evaluator: SourceEvaluator = Depends(get_source_evaluator),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Evaluate multiple sources in bulk."""
    try:
        logger.info("Starting bulk evaluation", source_count=len(request.source_ids))
        
        # Get sources
        sources = []
        for source_id in request.source_ids:
            source = await db.get_source_by_id(source_id)
            if source:
                sources.append(source)
        
        if not sources:
            raise HTTPException(status_code=404, detail="No valid sources found")
        
        # Evaluate sources with concurrency control
        semaphore = asyncio.Semaphore(request.parallel_evaluations)
        evaluations = []
        errors = []
        
        async def evaluate_single(source: Source) -> Optional[EvaluateSourceResponse]:
            async with semaphore:
                try:
                    evaluated_source, evaluation = await evaluator.evaluate_source(
                        url=str(source.url),
                        source_type=source.source_type,
                        force_reevaluation=request.force_reevaluation,
                        sample_articles=5  # Smaller sample for bulk operations
                    )
                    
                    return EvaluateSourceResponse(
                        source=evaluated_source,
                        evaluation=evaluation,
                        is_new_source=False,
                        cached=False
                    )
                except Exception as e:
                    errors.append(f"Failed to evaluate {source.url}: {str(e)}")
                    return None
        
        # Run evaluations concurrently
        tasks = [evaluate_single(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_evaluations = [r for r in results if isinstance(r, EvaluateSourceResponse)]
        failed_evaluations = len(sources) - len(successful_evaluations)
        
        response = BulkEvaluationResponse(
            total_requested=len(request.source_ids),
            successful_evaluations=len(successful_evaluations),
            failed_evaluations=failed_evaluations,
            cached_results=0,  # Would track actual cache usage
            evaluations=successful_evaluations,
            errors=errors
        )
        
        logger.info("Bulk evaluation completed", 
                   successful=len(successful_evaluations),
                   failed=failed_evaluations)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Bulk evaluation failed: {str(e)}")


@app.get("/sources/{source_id}/evaluation", response_model=SourceEvaluation)
async def get_source_evaluation(
    source_id: UUID,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get latest evaluation for a source."""
    try:
        evaluation = await db.get_latest_evaluation(source_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="No evaluation found for source")
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get evaluation", source_id=str(source_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get evaluation")


# Source Discovery Endpoints

@app.post("/discover", response_model=DiscoverSourcesResponse)
async def discover_sources(
    request: DiscoverSourcesRequest,
    background_tasks: BackgroundTasks,
    discovery: SourceDiscoveryService = Depends(get_discovery_service)
):
    """Discover new sources based on query and criteria."""
    try:
        logger.info("Starting source discovery", query=request.query)
        
        discovery_op, results = await discovery.discover_sources(
            query=request.query,
            categories=request.categories,
            source_types=request.source_types,
            max_results=request.max_results,
            quality_threshold=request.quality_threshold,
            include_evaluations=request.include_evaluations
        )
        
        response = DiscoverSourcesResponse(
            discovery=discovery_op,
            results=results,
            total_found=discovery_op.sources_found,
            total_evaluated=discovery_op.sources_evaluated
        )
        
        logger.info("Source discovery completed",
                   query=request.query,
                   sources_found=len(results))
        
        return response
        
    except Exception as e:
        logger.error("Source discovery failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@app.get("/discoveries/{discovery_id}", response_model=SourceDiscovery)
async def get_discovery(
    discovery_id: UUID,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get discovery operation by ID."""
    try:
        # This would need to be implemented in the database manager
        raise HTTPException(status_code=501, detail="Not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get discovery", discovery_id=str(discovery_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get discovery")


# Quality and Analytics Endpoints

@app.get("/quality/distribution")
async def get_quality_distribution(
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get quality rating distribution."""
    try:
        stats = await db.get_evaluation_stats()
        return {
            "quality_distribution": {
                rating.value: count 
                for rating, count in stats.quality_distribution.items()
            }
        }
        
    except Exception as e:
        logger.error("Failed to get quality distribution", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get quality distribution")


@app.get("/sources/quality/{quality_rating}")
async def get_sources_by_quality(
    quality_rating: SourceQuality,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get sources by quality rating."""
    try:
        sources, total = await db.search_sources(
            quality_ratings=[quality_rating],
            limit=limit,
            offset=offset
        )
        
        return SourceListResponse(
            sources=sources,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to get sources by quality", quality=quality_rating.value, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get sources by quality")


# Background Task Endpoints

@app.post("/tasks/reevaluate-all")
async def reevaluate_all_sources(
    background_tasks: BackgroundTasks,
    quality_threshold: float = Query(0.0, ge=0, le=1, description="Only re-evaluate sources below this threshold"),
    db: DatabaseManager = Depends(get_db_manager),
    evaluator: SourceEvaluator = Depends(get_source_evaluator)
):
    """Re-evaluate all sources (background task)."""
    async def reevaluate_task():
        try:
            logger.info("Starting full re-evaluation", quality_threshold=quality_threshold)
            
            # Get sources to re-evaluate
            sources, _ = await db.search_sources(
                statuses=[SourceStatus.ACTIVE],
                min_quality_score=None if quality_threshold == 0 else quality_threshold,
                limit=1000  # Process in batches
            )
            
            for source in sources:
                try:
                    await evaluator.evaluate_source(
                        url=str(source.url),
                        source_type=source.source_type,
                        force_reevaluation=True,
                        sample_articles=5
                    )
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error("Failed to re-evaluate source", url=str(source.url), error=str(e))
                    continue
            
            logger.info("Full re-evaluation completed", sources_processed=len(sources))
            
        except Exception as e:
            logger.error("Full re-evaluation failed", error=str(e))
    
    background_tasks.add_task(reevaluate_task)
    return {"message": "Re-evaluation task started"}


# Error Handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8302,
        reload=False,
        log_level="info"
    ) 