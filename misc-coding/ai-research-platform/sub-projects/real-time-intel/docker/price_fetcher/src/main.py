"""
Price Fetcher Service - FastAPI Application

Provides REST API endpoints for fetching financial price data from multiple sources
with caching, rate limiting, and intelligent fallback mechanisms.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .models.price_models import (
    PriceRequest, PriceResponse, BatchPriceRequest, BatchPriceResponse,
    HistoricalPriceRequest, DataSource, PriceType
)
from .services.price_service import price_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


# Request/Response Models for API
class SinglePriceRequest(BaseModel):
    """Request for a single symbol price."""
    symbol: str = Field(..., description="Stock ticker symbol")
    force_refresh: bool = Field(default=False, description="Force cache refresh")
    preferred_source: Optional[DataSource] = Field(None, description="Preferred data source")


class MultiplePriceRequest(BaseModel):
    """Request for multiple symbol prices."""
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="Stock ticker symbols")
    force_refresh: bool = Field(default=False, description="Force cache refresh")
    preferred_source: Optional[DataSource] = Field(None, description="Preferred data source")


class CacheWarmRequest(BaseModel):
    """Request to warm cache for symbols."""
    symbols: List[str] = Field(..., min_items=1, max_items=500, description="Symbols to warm")


class HistoricalRequest(BaseModel):
    """Request for historical price data."""
    symbol: str = Field(..., description="Stock ticker symbol")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    interval: str = Field(default="1d", description="Data interval (1d, 1wk, 1mo)")


# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    
    # Startup
    logger.info("Starting Price Fetcher Service")
    
    try:
        # Initialize price service
        await price_service.initialize()
        
        logger.info("Price Fetcher Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Price Fetcher Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Price Fetcher Service")
        
        try:
            await price_service.shutdown()
            logger.info("Price Fetcher Service shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Price Fetcher Service",
    description="Real-time financial data fetching service with multi-source support",
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
        "service": "price-fetcher",
        "version": "1.0.0",
        "timestamp": time.time(),
        "sources_available": len([
            source for source, status in price_service.source_status.items() 
            if status
        ])
    }


# Core price endpoints
@app.post("/price/single", response_model=PriceResponse)
async def get_single_price(request: SinglePriceRequest):
    """
    Get current price for a single symbol.
    
    Returns real-time or cached price data with source information.
    """
    try:
        response = await price_service.get_price(
            symbol=request.symbol,
            force_refresh=request.force_refresh,
            preferred_source=request.preferred_source
        )
        
        if not response.success:
            raise HTTPException(status_code=404, detail=response.error_message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/price/{symbol}", response_model=PriceResponse)
async def get_price_by_symbol(
    symbol: str,
    force_refresh: bool = Query(default=False, description="Force cache refresh"),
    preferred_source: Optional[DataSource] = Query(default=None, description="Preferred data source")
):
    """
    Get current price for a symbol via path parameter.
    
    Convenient endpoint for simple price lookups.
    """
    request = SinglePriceRequest(
        symbol=symbol,
        force_refresh=force_refresh,
        preferred_source=preferred_source
    )
    return await get_single_price(request)


@app.post("/price/batch", response_model=BatchPriceResponse)
async def get_batch_prices(request: MultiplePriceRequest):
    """
    Get current prices for multiple symbols efficiently.
    
    Optimized for bulk price fetching with intelligent caching and source selection.
    """
    try:
        if len(request.symbols) > 100:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 100 symbols allowed per batch request"
            )
        
        response = await price_service.get_batch_prices(
            symbols=request.symbols,
            force_refresh=request.force_refresh,
            preferred_source=request.preferred_source
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch prices: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/price/historical")
async def get_historical_prices(request: HistoricalRequest):
    """
    Get historical price data for a symbol.
    
    Returns daily, weekly, or monthly historical data.
    """
    try:
        historical_data = await price_service.get_historical_prices(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            interval=request.interval
        )
        
        return {
            "success": True,
            "symbol": request.symbol,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "interval": request.interval,
            "data_points": len(historical_data),
            "data": [item.dict() for item in historical_data]
        }
        
    except Exception as e:
        logger.error(f"Error getting historical data for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Cache management endpoints
@app.post("/cache/warm")
async def warm_cache(request: CacheWarmRequest, background_tasks: BackgroundTasks):
    """
    Warm cache for frequently accessed symbols.
    
    Proactively fetches and caches price data for specified symbols.
    """
    try:
        if len(request.symbols) > 500:
            raise HTTPException(
                status_code=400,
                detail="Maximum 500 symbols allowed for cache warming"
            )
        
        # Run cache warming in background
        background_tasks.add_task(price_service.warm_cache, request.symbols)
        
        return {
            "success": True,
            "message": f"Cache warming started for {len(request.symbols)} symbols",
            "symbols_count": len(request.symbols)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache performance statistics.
    
    Returns hit rates, memory usage, and other cache metrics.
    """
    try:
        cache_stats = await price_service.cache.get_cache_stats()
        return {
            "success": True,
            "cache_stats": cache_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(default=None, description="Cache key pattern to clear")
):
    """
    Clear cache entries.
    
    Clears all or specific cache entries based on pattern.
    """
    try:
        cleared_count = await price_service.cache.clear_cache(pattern)
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Monitoring and analytics endpoints
@app.get("/metrics")
async def get_service_metrics():
    """
    Get service performance metrics.
    
    Returns request counts, response times, source usage, and other performance data.
    """
    try:
        metrics = await price_service.get_service_metrics()
        return {
            "success": True,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/sources/status")
async def get_source_status():
    """
    Get status of all data sources.
    
    Returns availability and performance metrics for each data source.
    """
    try:
        source_status = {}
        
        for source_type, is_available in price_service.source_status.items():
            source_status[source_type.value] = {
                "available": is_available,
                "usage_count": price_service.metrics['source_usage'].get(source_type.value, 0)
            }
        
        return {
            "success": True,
            "sources": source_status,
            "total_sources": len(source_status),
            "available_sources": sum(1 for s in source_status.values() if s["available"])
        }
        
    except Exception as e:
        logger.error(f"Error getting source status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Portfolio integration endpoints
@app.post("/portfolio/prices")
async def get_portfolio_prices(
    portfolio_symbols: List[str] = Field(..., description="Portfolio symbols"),
    user_id: Optional[str] = Field(None, description="User ID for tracking")
):
    """
    Get prices for all symbols in a portfolio.
    
    Optimized endpoint for portfolio price updates.
    """
    try:
        if len(portfolio_symbols) > 200:
            raise HTTPException(
                status_code=400,
                detail="Maximum 200 symbols allowed for portfolio price fetch"
            )
        
        response = await price_service.get_batch_prices(
            symbols=portfolio_symbols,
            force_refresh=False  # Use cache for portfolio updates
        )
        
        # Extract successful prices
        successful_prices = {}
        failed_symbols = []
        
        for result in response.results:
            if result.success and result.data:
                successful_prices[result.data.symbol] = {
                    "current_price": result.data.current_price,
                    "price_change": result.data.price_change,
                    "price_change_pct": result.data.price_change_pct,
                    "volume": result.data.volume,
                    "timestamp": result.data.timestamp.isoformat() if result.data.timestamp else None,
                    "source": result.source_used.value if result.source_used else None
                }
            else:
                failed_symbols.append(result.error_message or "Unknown error")
        
        return {
            "success": True,
            "user_id": user_id,
            "total_symbols": len(portfolio_symbols),
            "successful_count": len(successful_prices),
            "failed_count": len(failed_symbols),
            "prices": successful_prices,
            "failed_symbols": failed_symbols,
            "cache_hit_rate": response.cache_hit_rate,
            "response_time_ms": response.total_response_time_ms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio prices: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Admin endpoints
@app.post("/admin/sources/{source_name}/toggle")
async def toggle_source_status(source_name: str, enabled: bool):
    """
    Enable or disable a specific data source.
    
    Admin endpoint for managing data source availability.
    """
    try:
        # Convert string to DataSource enum
        source_type = None
        for source in DataSource:
            if source.value == source_name.lower():
                source_type = source
                break
        
        if not source_type:
            raise HTTPException(
                status_code=404,
                detail=f"Data source '{source_name}' not found"
            )
        
        price_service.source_status[source_type] = enabled
        
        return {
            "success": True,
            "message": f"Data source '{source_name}' {'enabled' if enabled else 'disabled'}",
            "source": source_name,
            "enabled": enabled
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling source status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/admin/performance")
async def get_performance_summary():
    """
    Get detailed performance summary for monitoring.
    
    Admin endpoint with comprehensive service health information.
    """
    try:
        metrics = await price_service.get_service_metrics()
        cache_stats = await price_service.cache.get_cache_stats()
        
        return {
            "success": True,
            "service_health": {
                "uptime_seconds": time.time() - getattr(app.state, 'start_time', time.time()),
                "total_requests": metrics.get('request_metrics', {}).get('total_requests', 0),
                "success_rate": metrics.get('request_metrics', {}).get('success_rate', 0),
                "avg_response_time_ms": metrics.get('performance_metrics', {}).get('average_response_time_ms', 0)
            },
            "cache_health": {
                "hit_rate": cache_stats.get('hit_rate', 0),
                "total_hits": cache_stats.get('cache_stats', {}).get('hits', 0),
                "total_misses": cache_stats.get('cache_stats', {}).get('misses', 0)
            },
            "source_health": {
                "available_sources": len([
                    s for s in price_service.source_status.values() if s
                ]),
                "total_sources": len(price_service.source_status),
                "source_usage": metrics.get('source_metrics', {}).get('usage_count', {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8306,
        reload=False,
        log_level="info"
    ) 