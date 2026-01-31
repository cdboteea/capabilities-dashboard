"""
Holdings Router Service - FastAPI Application

Routes events to users based on portfolio relevance.
This is the orchestration layer between Event Processor and Alert Engine.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .models.portfolio_models import *
from .processors.portfolio_router import portfolio_router, RelevanceLevel
from .utils.database import get_db_pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


# Request/Response Models
class EventRoutingRequest(BaseModel):
    """Request to route an event to users."""
    event_id: str
    event_text: str
    event_entities: List[str] = Field(default_factory=list)
    event_sentiment: Optional[Dict] = None
    event_metadata: Optional[Dict] = None
    min_relevance_level: RelevanceLevel = RelevanceLevel.LOW


class BatchEventRoutingRequest(BaseModel):
    """Request to route multiple events."""
    events: List[Dict]
    min_relevance_level: RelevanceLevel = RelevanceLevel.LOW


class PortfolioUpdateRequest(BaseModel):
    """Request to update a user's portfolio."""
    user_id: str
    holdings: List[HoldingCreate]
    total_value: float
    cash_balance: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM


class UserEventsRequest(BaseModel):
    """Request to get relevant events for a user."""
    user_id: str
    hours_back: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    min_relevance_level: RelevanceLevel = RelevanceLevel.LOW


# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    
    # Startup
    logger.info("Starting Holdings Router Service")
    
    try:
        # Initialize database connection pool
        db_pool = await get_db_pool()
        app.state.db_pool = db_pool
        
        # Initialize portfolio router with database
        portfolio_router.db_pool = db_pool
        
        logger.info("Holdings Router Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Holdings Router Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Holdings Router Service")
        
        if hasattr(app.state, 'db_pool'):
            await app.state.db_pool.close()


# Create FastAPI application
app = FastAPI(
    title="Holdings Router Service",
    description="Routes events to users based on portfolio relevance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "holdings-router",
        "version": "1.0.0",
        "timestamp": time.time()
    }


# Core routing endpoints
@app.post("/route/event")
async def route_event(request: EventRoutingRequest, background_tasks: BackgroundTasks):
    """
    Route a single event to relevant users based on portfolio analysis.
    
    This is the main endpoint called by the Event Processor.
    """
    try:
        start_time = time.time()
        
        logger.info(f"Routing event {request.event_id}")
        
        # Route the event
        routing_decision = await portfolio_router.route_event(
            event_id=request.event_id,
            event_text=request.event_text,
            event_entities=request.event_entities,
            event_sentiment=request.event_sentiment,
            event_metadata=request.event_metadata,
            min_relevance_level=request.min_relevance_level
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "status": "success",
            "event_id": request.event_id,
            "users_matched": routing_decision.total_users_matched,
            "users_by_level": routing_decision.users_by_level,
            "processing_time_ms": processing_time,
            "timestamp": routing_decision.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error routing event {request.event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@app.post("/route/batch")
async def route_batch_events(request: BatchEventRoutingRequest):
    """
    Route multiple events in batch for efficiency.
    
    Used for bulk processing of events.
    """
    try:
        start_time = time.time()
        
        logger.info(f"Batch routing {len(request.events)} events")
        
        # Route all events
        routing_decisions = await portfolio_router.route_batch_events(
            events=request.events,
            min_relevance_level=request.min_relevance_level
        )
        
        processing_time = (time.time() - start_time) * 1000
        total_users = sum(d.total_users_matched for d in routing_decisions)
        
        return {
            "status": "success",
            "events_processed": len(routing_decisions),
            "total_users_matched": total_users,
            "processing_time_ms": processing_time,
            "results": [
                {
                    "event_id": d.event_id,
                    "users_matched": d.total_users_matched,
                    "users_by_level": d.users_by_level
                }
                for d in routing_decisions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in batch routing: {e}")
        raise HTTPException(status_code=500, detail=f"Batch routing failed: {str(e)}")


# User-specific endpoints
@app.post("/user/events")
async def get_user_relevant_events(request: UserEventsRequest):
    """
    Get recent events relevant to a specific user's portfolio.
    
    Used by frontend to show personalized event feed.
    """
    try:
        events = await portfolio_router.get_user_relevant_events(
            user_id=request.user_id,
            hours_back=request.hours_back,
            min_relevance_level=request.min_relevance_level
        )
        
        return {
            "status": "success",
            "user_id": request.user_id,
            "events_count": len(events),
            "hours_back": request.hours_back,
            "min_relevance_level": request.min_relevance_level.value,
            "events": events
        }
        
    except Exception as e:
        logger.error(f"Error getting events for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user events: {str(e)}")


@app.post("/portfolio/update")
async def update_user_portfolio(request: PortfolioUpdateRequest):
    """
    Update a user's portfolio holdings.
    
    Called when user makes trades or portfolio changes.
    """
    try:
        # Clear cache for this user
        if request.user_id in portfolio_router.portfolio_cache:
            del portfolio_router.portfolio_cache[request.user_id]
        
        # Store portfolio update in database
        async with app.state.db_pool.acquire() as conn:
            # Update portfolio summary
            await conn.execute("""
                INSERT INTO portfolios (user_id, total_value, cash_balance, risk_level, last_updated)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    total_value = $2,
                    cash_balance = $3,
                    risk_level = $4,
                    last_updated = NOW()
            """, request.user_id, request.total_value, request.cash_balance, request.risk_level.value)
            
            # Clear existing holdings
            await conn.execute("DELETE FROM holdings WHERE user_id = $1", request.user_id)
            
            # Insert new holdings
            for holding in request.holdings:
                await conn.execute("""
                    INSERT INTO holdings (
                        user_id, symbol, name, shares, avg_cost, market_value,
                        sector, position_pct, unrealized_pnl
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                    request.user_id, holding.symbol, holding.name, holding.shares,
                    holding.avg_cost, holding.market_value, holding.sector.value if holding.sector else None,
                    holding.position_pct, holding.unrealized_pnl
                )
        
        return {
            "status": "success",
            "user_id": request.user_id,
            "holdings_count": len(request.holdings),
            "total_value": request.total_value,
            "message": "Portfolio updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating portfolio for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio update failed: {str(e)}")


# Analytics endpoints
@app.get("/analytics/routing")
async def get_routing_analytics(hours_back: int = 24):
    """
    Get routing analytics and performance metrics.
    
    Used for monitoring and optimization.
    """
    try:
        analytics = await portfolio_router.get_routing_analytics(hours_back=hours_back)
        
        return {
            "status": "success",
            "hours_back": hours_back,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting routing analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


@app.get("/analytics/performance")
async def get_performance_metrics():
    """Get current performance metrics."""
    
    return {
        "status": "success",
        "metrics": portfolio_router.routing_stats,
        "cache_size": len(portfolio_router.portfolio_cache),
        "uptime_seconds": time.time() - getattr(app.state, 'start_time', time.time())
    }


# Admin endpoints
@app.post("/admin/cache/clear")
async def clear_portfolio_cache(user_id: Optional[str] = None):
    """Clear portfolio cache for specific user or all users."""
    
    if user_id:
        if user_id in portfolio_router.portfolio_cache:
            del portfolio_router.portfolio_cache[user_id]
            return {"status": "success", "message": f"Cache cleared for user {user_id}"}
        else:
            return {"status": "success", "message": f"No cache found for user {user_id}"}
    else:
        cache_size = len(portfolio_router.portfolio_cache)
        portfolio_router.portfolio_cache.clear()
        return {"status": "success", "message": f"Cleared cache for {cache_size} users"}


@app.get("/admin/cache/stats")
async def get_cache_stats():
    """Get detailed cache statistics."""
    
    cache_stats = {}
    for user_id, cache_entry in portfolio_router.portfolio_cache.items():
        cache_stats[user_id] = {
            "last_updated": cache_entry.last_updated.isoformat(),
            "holdings_count": len(cache_entry.portfolio.get('holdings', [])),
            "total_value": cache_entry.portfolio.get('total_value', 0)
        }
    
    return {
        "status": "success",
        "total_cached_users": len(cache_stats),
        "cache_hit_rate": portfolio_router.routing_stats.get('cache_hit_rate', 0.0),
        "cache_details": cache_stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8305,
        reload=False,
        log_level="info"
    )
