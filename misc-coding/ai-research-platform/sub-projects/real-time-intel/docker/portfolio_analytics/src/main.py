"""Portfolio Analytics Service - Main FastAPI Application."""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server
import uvicorn

from .models.analytics_models import (
    AnalyticsRequest, AnalyticsResponse, RiskAnalysisRequest,
    OptimizationRequest, CorrelationRequest, PerformanceComparisonRequest,
    PerformanceComparisonResponse, AnalyticsHistoryRequest, AnalyticsHistoryResponse,
    TimePeriod, PortfolioAnalytics
)
from .services.analytics_service import AnalyticsService
from .utils.database import DatabaseManager, initialize_analytics_schema
from .config import config

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

# Prometheus metrics
analytics_requests_total = Counter(
    'portfolio_analytics_requests_total',
    'Total number of analytics requests',
    ['endpoint', 'status']
)

analytics_calculation_duration = Histogram(
    'portfolio_analytics_calculation_duration_seconds',
    'Time spent calculating analytics',
    ['calculation_type']
)

# Global service instances
analytics_service = None
db_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global analytics_service, db_manager
    
    try:
        # Initialize services
        logger.info("Initializing Portfolio Analytics service...")
        
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        await initialize_analytics_schema(db_manager)
        
        # Initialize analytics service
        analytics_service = AnalyticsService()
        await analytics_service.initialize()
        
        # Start Prometheus metrics server
        if config.monitoring.enable_metrics:
            start_http_server(config.monitoring.metrics_port)
            logger.info(f"Prometheus metrics server started on port {config.monitoring.metrics_port}")
        
        logger.info("Portfolio Analytics service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Service initialization failed", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Portfolio Analytics service...")
        
        if analytics_service:
            await analytics_service.cleanup()
        
        if db_manager:
            await db_manager.close()
        
        logger.info("Portfolio Analytics service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Portfolio Analytics Service",
    description="Advanced portfolio performance and risk analytics",
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


# Dependency to get analytics service
async def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    if analytics_service is None:
        raise HTTPException(status_code=503, detail="Analytics service not initialized")
    return analytics_service


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connectivity
        if db_manager:
            db_healthy = await db_manager.health_check()
        else:
            db_healthy = False
        
        # Check analytics service
        service_healthy = analytics_service is not None
        
        status = "healthy" if db_healthy and service_healthy else "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "portfolio-analytics",
            "version": "1.0.0",
            "checks": {
                "database": "healthy" if db_healthy else "unhealthy",
                "analytics_service": "healthy" if service_healthy else "unhealthy"
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# Core Analytics Endpoints

@app.post("/analytics/calculate", response_model=AnalyticsResponse)
async def calculate_analytics(
    request: AnalyticsRequest,
    background_tasks: BackgroundTasks,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Calculate comprehensive portfolio analytics."""
    start_time = datetime.utcnow()
    
    try:
        with analytics_calculation_duration.labels(calculation_type="comprehensive").time():
            result = await service.calculate_portfolio_analytics(request)
        
        # Log calculation for monitoring
        if config.monitoring.performance_logging:
            logger.info(
                "Analytics calculation completed",
                portfolio_id=request.portfolio_id,
                period=request.period.value,
                calculation_time_ms=result.calculation_time_ms,
                success=result.success
            )
        
        # Save result to database in background
        if result.success and result.analytics:
            background_tasks.add_task(
                save_analytics_result,
                request.portfolio_id,
                result.analytics,
                result.calculation_time_ms
            )
        
        analytics_requests_total.labels(
            endpoint="calculate_analytics",
            status="success" if result.success else "error"
        ).inc()
        
        return result
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="calculate_analytics",
            status="error"
        ).inc()
        
        logger.error(
            "Analytics calculation failed",
            portfolio_id=request.portfolio_id,
            error=str(e)
        )
        
        calculation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AnalyticsResponse(
            success=False,
            error_message=str(e),
            calculation_time_ms=calculation_time
        )


@app.post("/analytics/risk", response_model=AnalyticsResponse)
async def analyze_risk(
    request: RiskAnalysisRequest,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Perform detailed risk analysis."""
    try:
        # Convert to analytics request
        analytics_request = AnalyticsRequest(
            portfolio_id=request.portfolio_id,
            period=TimePeriod.ONE_YEAR,
            include_optimization=False,
            include_scenarios=True
        )
        
        with analytics_calculation_duration.labels(calculation_type="risk").time():
            result = await service.calculate_portfolio_analytics(analytics_request)
        
        analytics_requests_total.labels(
            endpoint="analyze_risk",
            status="success" if result.success else "error"
        ).inc()
        
        return result
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="analyze_risk",
            status="error"
        ).inc()
        
        logger.error("Risk analysis failed", portfolio_id=request.portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/optimize", response_model=AnalyticsResponse)
async def optimize_portfolio(
    request: OptimizationRequest,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Perform portfolio optimization."""
    try:
        # Convert to analytics request
        analytics_request = AnalyticsRequest(
            portfolio_id=request.portfolio_id,
            period=TimePeriod.ONE_YEAR,
            include_optimization=True,
            include_scenarios=False
        )
        
        with analytics_calculation_duration.labels(calculation_type="optimization").time():
            result = await service.calculate_portfolio_analytics(analytics_request)
        
        analytics_requests_total.labels(
            endpoint="optimize_portfolio",
            status="success" if result.success else "error"
        ).inc()
        
        return result
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="optimize_portfolio",
            status="error"
        ).inc()
        
        logger.error("Portfolio optimization failed", portfolio_id=request.portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/correlation", response_model=AnalyticsResponse)
async def analyze_correlation(
    request: CorrelationRequest,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Perform correlation analysis."""
    try:
        # Convert to analytics request
        analytics_request = AnalyticsRequest(
            portfolio_id=request.portfolio_id,
            period=TimePeriod.ONE_YEAR,
            include_optimization=False,
            include_scenarios=False
        )
        
        with analytics_calculation_duration.labels(calculation_type="correlation").time():
            result = await service.calculate_portfolio_analytics(analytics_request)
        
        analytics_requests_total.labels(
            endpoint="analyze_correlation",
            status="success" if result.success else "error"
        ).inc()
        
        return result
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="analyze_correlation",
            status="error"
        ).inc()
        
        logger.error("Correlation analysis failed", portfolio_id=request.portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Comparison and History Endpoints

@app.post("/analytics/compare", response_model=PerformanceComparisonResponse)
async def compare_portfolios(
    request: PerformanceComparisonRequest,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Compare performance of multiple portfolios."""
    try:
        comparison_results = {}
        
        # Calculate analytics for each portfolio
        for portfolio_id in request.portfolio_ids:
            analytics_request = AnalyticsRequest(
                portfolio_id=portfolio_id,
                period=request.period
            )
            
            result = await service.calculate_portfolio_analytics(analytics_request)
            
            if result.success and result.analytics:
                comparison_results[portfolio_id] = result.analytics
        
        # Create ranking based on Sharpe ratio (or other metrics)
        ranking = []
        for portfolio_id, analytics in comparison_results.items():
            ranking.append({
                "portfolio_id": portfolio_id,
                "sharpe_ratio": analytics.performance.sharpe_ratio,
                "annualized_return": analytics.performance.annualized_return,
                "volatility": analytics.performance.volatility,
                "max_drawdown": analytics.performance.max_drawdown
            })
        
        ranking.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
        
        # Calculate summary statistics
        if ranking:
            returns = [r["annualized_return"] for r in ranking]
            volatilities = [r["volatility"] for r in ranking]
            
            summary_statistics = {
                "average_return": sum(returns) / len(returns),
                "average_volatility": sum(volatilities) / len(volatilities),
                "best_performer": ranking[0]["portfolio_id"] if ranking else None,
                "worst_performer": ranking[-1]["portfolio_id"] if ranking else None,
                "total_portfolios": len(ranking)
            }
        else:
            summary_statistics = {}
        
        analytics_requests_total.labels(
            endpoint="compare_portfolios",
            status="success"
        ).inc()
        
        return PerformanceComparisonResponse(
            comparison_results=comparison_results,
            ranking=ranking,
            summary_statistics=summary_statistics
        )
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="compare_portfolios",
            status="error"
        ).inc()
        
        logger.error("Portfolio comparison failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/history", response_model=AnalyticsHistoryResponse)
async def get_analytics_history(
    request: AnalyticsHistoryRequest
):
    """Get historical analytics data for a portfolio."""
    try:
        history_data = await db_manager.get_analytics_history(
            request.portfolio_id,
            request.start_date,
            request.end_date
        )
        
        # Convert to PortfolioAnalytics objects
        history = []
        for record in history_data:
            try:
                analytics = PortfolioAnalytics(**record['analytics_data'])
                history.append(analytics)
            except Exception as e:
                logger.warning(
                    "Failed to parse historical analytics",
                    portfolio_id=request.portfolio_id,
                    date=record['analysis_date'],
                    error=str(e)
                )
                continue
        
        # Calculate summary statistics
        if history:
            returns = [h.performance.annualized_return for h in history]
            volatilities = [h.performance.volatility for h in history]
            
            summary = {
                "average_return": sum(returns) / len(returns),
                "average_volatility": sum(volatilities) / len(volatilities),
                "best_return": max(returns),
                "worst_return": min(returns),
                "data_points": len(history)
            }
        else:
            summary = {}
        
        analytics_requests_total.labels(
            endpoint="get_analytics_history",
            status="success"
        ).inc()
        
        return AnalyticsHistoryResponse(
            portfolio_id=request.portfolio_id,
            history=history,
            summary=summary
        )
        
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="get_analytics_history",
            status="error"
        ).inc()
        
        logger.error("Analytics history retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Quick Analytics Endpoints

@app.get("/analytics/{portfolio_id}/summary")
async def get_portfolio_summary(
    portfolio_id: str,
    period: TimePeriod = Query(default=TimePeriod.ONE_YEAR),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get quick portfolio summary."""
    try:
        request = AnalyticsRequest(
            portfolio_id=portfolio_id,
            period=period,
            include_optimization=False,
            include_scenarios=False
        )
        
        result = await service.calculate_portfolio_analytics(request)
        
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        
        # Return simplified summary
        summary = {
            "portfolio_id": portfolio_id,
            "total_value": float(result.analytics.total_value),
            "asset_count": result.analytics.asset_count,
            "performance": {
                "total_return": result.analytics.performance.total_return,
                "annualized_return": result.analytics.performance.annualized_return,
                "volatility": result.analytics.performance.volatility,
                "sharpe_ratio": result.analytics.performance.sharpe_ratio,
                "max_drawdown": result.analytics.performance.max_drawdown
            },
            "risk": {
                "var_95": result.analytics.risk.var_95,
                "historical_volatility": result.analytics.risk.historical_volatility
            },
            "allocations": {
                "sectors": result.analytics.sector_allocation,
                "asset_classes": result.analytics.asset_class_allocation
            }
        }
        
        analytics_requests_total.labels(
            endpoint="get_portfolio_summary",
            status="success"
        ).inc()
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        analytics_requests_total.labels(
            endpoint="get_portfolio_summary",
            status="error"
        ).inc()
        
        logger.error("Portfolio summary failed", portfolio_id=portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/{portfolio_id}/performance")
async def get_performance_metrics(
    portfolio_id: str,
    period: TimePeriod = Query(default=TimePeriod.ONE_YEAR),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get performance metrics only."""
    try:
        request = AnalyticsRequest(
            portfolio_id=portfolio_id,
            period=period
        )
        
        result = await service.calculate_portfolio_analytics(request)
        
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        
        return result.analytics.performance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Performance metrics retrieval failed", portfolio_id=portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/{portfolio_id}/risk")
async def get_risk_metrics(
    portfolio_id: str,
    period: TimePeriod = Query(default=TimePeriod.ONE_YEAR),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get risk metrics only."""
    try:
        request = AnalyticsRequest(
            portfolio_id=portfolio_id,
            period=period
        )
        
        result = await service.calculate_portfolio_analytics(request)
        
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        
        return result.analytics.risk
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Risk metrics retrieval failed", portfolio_id=portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Administrative Endpoints

@app.get("/admin/portfolios")
async def list_portfolios():
    """List all portfolios with basic info."""
    try:
        query = """
            SELECT portfolio_id, name, total_value, created_at, updated_at
            FROM portfolios
            WHERE status = 'active'
            ORDER BY total_value DESC
        """
        
        portfolios = await db_manager.fetch_all(query)
        
        return {
            "portfolios": portfolios,
            "count": len(portfolios)
        }
        
    except Exception as e:
        logger.error("Portfolio listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/cache/{portfolio_id}")
async def clear_portfolio_cache(
    portfolio_id: str,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Clear cache for a specific portfolio."""
    try:
        # Clear Redis cache
        if service.redis_client:
            pattern = f"analytics:{portfolio_id}:*"
            keys = await service.redis_client.keys(pattern)
            if keys:
                await service.redis_client.delete(*keys)
        
        return {
            "message": f"Cache cleared for portfolio {portfolio_id}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Cache clearing failed", portfolio_id=portfolio_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


# Background tasks

async def save_analytics_result(
    portfolio_id: str,
    analytics: PortfolioAnalytics,
    calculation_time_ms: int
):
    """Save analytics result to database (background task)."""
    try:
        await db_manager.save_analytics_result(
            portfolio_id,
            analytics.dict(),
            calculation_time_ms
        )
        
        # Also save individual metrics
        await db_manager.save_performance_metrics(
            portfolio_id,
            analytics.performance.period.value,
            analytics.performance.dict()
        )
        
        await db_manager.save_risk_metrics(
            portfolio_id,
            analytics.risk.period.value,
            analytics.risk.dict()
        )
        
        if analytics.correlation:
            await db_manager.save_correlation_matrix(
                portfolio_id,
                analytics.correlation.period.value,
                analytics.correlation.dict()
            )
        
    except Exception as e:
        logger.error(
            "Failed to save analytics result",
            portfolio_id=portfolio_id,
            error=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug
    ) 