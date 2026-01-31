"""Alert Engine Service - Main FastAPI Application."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server
import uvicorn

from .models.alert_models import (
    CreateAlertRequest, CreateRuleRequest, AlertResponse, AlertListResponse,
    AlertStatsResponse, AlertEvent, AlertRule, UserPreferences,
    AlertType, AlertPriority, AlertStatus, NotificationChannel
)
from .services.alert_manager import AlertManager
from .utils.database import DatabaseManager, initialize_alert_schema
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
alert_requests_total = Counter(
    'alert_engine_requests_total',
    'Total number of alert requests',
    ['endpoint', 'status']
)

alert_processing_duration = Histogram(
    'alert_engine_processing_duration_seconds',
    'Time spent processing alerts',
    ['alert_type']
)

alert_deliveries_total = Counter(
    'alert_engine_deliveries_total',
    'Total number of alert deliveries',
    ['channel', 'status']
)

# Global service instances
alert_manager = None
db_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global alert_manager, db_manager
    
    try:
        # Initialize services
        logger.info("Initializing Alert Engine service...")
        
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        await initialize_alert_schema(db_manager)
        
        # Initialize alert manager
        alert_manager = AlertManager()
        await alert_manager.initialize()
        
        # Start Prometheus metrics server
        if config.monitoring.enable_metrics:
            start_http_server(config.monitoring.metrics_port)
            logger.info(f"Prometheus metrics server started on port {config.monitoring.metrics_port}")
        
        logger.info("Alert Engine service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Service initialization failed", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Alert Engine service...")
        
        if alert_manager:
            await alert_manager.cleanup()
        
        if db_manager:
            await db_manager.close()
        
        logger.info("Alert Engine service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Alert Engine Service",
    description="Multi-channel alert and notification system",
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


# Dependency to get alert manager
async def get_alert_manager() -> AlertManager:
    """Get alert manager instance."""
    if alert_manager is None:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    return alert_manager


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
        
        # Check alert manager
        manager_healthy = alert_manager is not None
        
        # Check notification services
        notification_services_healthy = True
        if alert_manager:
            try:
                # Quick check of notification services
                await alert_manager.email_service.health_check()
            except:
                notification_services_healthy = False
        
        status = "healthy" if db_healthy and manager_healthy and notification_services_healthy else "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "alert-engine",
            "version": "1.0.0",
            "checks": {
                "database": "healthy" if db_healthy else "unhealthy",
                "alert_manager": "healthy" if manager_healthy else "unhealthy",
                "notification_services": "healthy" if notification_services_healthy else "unhealthy"
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


# Core Alert Endpoints

@app.post("/alerts/send", response_model=AlertResponse)
async def send_alert(
    request: CreateAlertRequest,
    background_tasks: BackgroundTasks,
    manager: AlertManager = Depends(get_alert_manager)
):
    """Send an immediate alert."""
    start_time = datetime.utcnow()
    
    try:
        # Create alert event
        alert = AlertEvent(
            alert_type=request.alert_type,
            priority=request.priority,
            title=request.title,
            message=request.message,
            symbol=request.symbol,
            portfolio_id=request.portfolio_id,
            data=request.data
        )
        
        # Set expiry if specified
        if request.expiry_minutes:
            alert.expiry_timestamp = datetime.utcnow() + timedelta(minutes=request.expiry_minutes)
        
        with alert_processing_duration.labels(alert_type=request.alert_type.value).time():
            # Process alert
            deliveries = await manager.process_alert(alert)
        
        alert_requests_total.labels(
            endpoint="send_alert",
            status="success"
        ).inc()
        
        # Track deliveries
        for delivery in deliveries:
            alert_deliveries_total.labels(
                channel=delivery.channel.value,
                status="queued"
            ).inc()
        
        return AlertResponse(
            success=True,
            alert_id=alert.event_id,
            message=f"Alert sent successfully with {len(deliveries)} deliveries",
            deliveries=deliveries
        )
        
    except Exception as e:
        alert_requests_total.labels(
            endpoint="send_alert",
            status="error"
        ).inc()
        
        logger.error("Alert sending failed", error=str(e))
        
        return AlertResponse(
            success=False,
            message=str(e),
            deliveries=[]
        )


@app.post("/alerts/batch")
async def send_batch_alert(
    alerts: List[CreateAlertRequest],
    manager: AlertManager = Depends(get_alert_manager)
):
    """Send multiple alerts in batch."""
    try:
        results = []
        
        for alert_request in alerts:
            # Create alert event
            alert = AlertEvent(
                alert_type=alert_request.alert_type,
                priority=alert_request.priority,
                title=alert_request.title,
                message=alert_request.message,
                symbol=alert_request.symbol,
                portfolio_id=alert_request.portfolio_id,
                data=alert_request.data
            )
            
            # Process alert
            deliveries = await manager.process_alert(alert)
            
            results.append({
                "alert_id": alert.event_id,
                "deliveries_count": len(deliveries),
                "success": True
            })
        
        alert_requests_total.labels(
            endpoint="send_batch_alert",
            status="success"
        ).inc()
        
        return {
            "success": True,
            "processed_count": len(results),
            "results": results
        }
        
    except Exception as e:
        alert_requests_total.labels(
            endpoint="send_batch_alert",
            status="error"
        ).inc()
        
        logger.error("Batch alert sending failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Alert Rule Management

@app.post("/rules", response_model=dict)
async def create_alert_rule(
    request: CreateRuleRequest,
    manager: AlertManager = Depends(get_alert_manager)
):
    """Create a new alert rule."""
    try:
        # Create alert rule
        rule = AlertRule(
            name=request.name,
            description=request.description,
            alert_type=request.alert_type,
            priority=request.priority,
            conditions=request.conditions,
            condition_logic=request.condition_logic,
            portfolio_ids=request.portfolio_ids,
            symbols=request.symbols,
            channels=request.channels,
            recipients=request.recipients,
            cooldown_minutes=request.cooldown_minutes
        )
        
        success = await manager.create_alert_rule(rule)
        
        if success:
            alert_requests_total.labels(
                endpoint="create_alert_rule",
                status="success"
            ).inc()
            
            return {
                "success": True,
                "rule_id": rule.rule_id,
                "message": "Alert rule created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create alert rule")
            
    except HTTPException:
        raise
    except Exception as e:
        alert_requests_total.labels(
            endpoint="create_alert_rule",
            status="error"
        ).inc()
        
        logger.error("Alert rule creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rules")
async def list_alert_rules():
    """List all alert rules."""
    try:
        rules = await db_manager.get_alert_rules()
        
        return {
            "rules": [rule.dict() for rule in rules],
            "count": len(rules)
        }
        
    except Exception as e:
        logger.error("Alert rules listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    """Get a specific alert rule."""
    try:
        rule = await db_manager.get_alert_rule(rule_id)
        
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        return rule.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alert rule retrieval failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    request: CreateRuleRequest,
    manager: AlertManager = Depends(get_alert_manager)
):
    """Update an existing alert rule."""
    try:
        # Get existing rule
        existing_rule = await db_manager.get_alert_rule(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        # Update rule
        existing_rule.name = request.name
        existing_rule.description = request.description
        existing_rule.alert_type = request.alert_type
        existing_rule.priority = request.priority
        existing_rule.conditions = request.conditions
        existing_rule.condition_logic = request.condition_logic
        existing_rule.portfolio_ids = request.portfolio_ids
        existing_rule.symbols = request.symbols
        existing_rule.channels = request.channels
        existing_rule.recipients = request.recipients
        existing_rule.cooldown_minutes = request.cooldown_minutes
        existing_rule.updated_at = datetime.utcnow()
        
        success = await manager.create_alert_rule(existing_rule)  # This will update
        
        if success:
            return {
                "success": True,
                "message": "Alert rule updated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update alert rule")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alert rule update failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule."""
    try:
        success = await db_manager.delete_alert_rule(rule_id)
        
        if success:
            return {
                "success": True,
                "message": "Alert rule deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Alert rule not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alert rule deletion failed", rule_id=rule_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Alert History and Management

@app.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    alert_type: Optional[AlertType] = Query(default=None),
    priority: Optional[AlertPriority] = Query(default=None),
    status: Optional[AlertStatus] = Query(default=None),
    portfolio_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """List alerts with filtering and pagination."""
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        filters = {
            'alert_type': alert_type,
            'priority': priority,
            'status': status,
            'portfolio_id': portfolio_id,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        }
        
        alerts, total_count = await db_manager.get_alerts(
            page=page,
            page_size=page_size,
            filters=filters
        )
        
        return AlertListResponse(
            alerts=alerts,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Alert listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert."""
    try:
        alert = await db_manager.get_alert(alert_id)
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Get delivery records
        deliveries = await db_manager.get_alert_deliveries(alert_id)
        
        return {
            "alert": alert.dict(),
            "deliveries": [delivery.dict() for delivery in deliveries]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alert retrieval failed", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    try:
        success = await db_manager.acknowledge_alert(alert_id)
        
        if success:
            return {
                "success": True,
                "message": "Alert acknowledged successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alert acknowledgment failed", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Statistics and Analytics

@app.get("/stats", response_model=AlertStatsResponse)
async def get_alert_statistics(
    days: int = Query(default=7, ge=1, le=365),
    manager: AlertManager = Depends(get_alert_manager)
):
    """Get alert statistics."""
    try:
        stats = await manager.get_alert_statistics(days)
        
        return AlertStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Alert statistics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/deliveries")
async def get_delivery_statistics(
    days: int = Query(default=7, ge=1, le=365)
):
    """Get delivery statistics."""
    try:
        stats = await db_manager.get_delivery_statistics(days)
        
        return stats
        
    except Exception as e:
        logger.error("Delivery statistics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# User Preferences Management

@app.post("/preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    manager: AlertManager = Depends(get_alert_manager)
):
    """Update user notification preferences."""
    try:
        success = await manager.update_user_preferences(preferences)
        
        if success:
            return {
                "success": True,
                "message": "User preferences updated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update preferences")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User preferences update failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user notification preferences."""
    try:
        preferences = await db_manager.get_user_preferences_by_id(user_id)
        
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        return preferences.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User preferences retrieval failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Testing and Debugging

@app.post("/test/alert")
async def send_test_alert(
    channel: NotificationChannel,
    recipient: str,
    manager: AlertManager = Depends(get_alert_manager)
):
    """Send a test alert for debugging."""
    try:
        # Create test alert
        test_alert = CreateAlertRequest(
            alert_type=AlertType.CUSTOM,
            priority=AlertPriority.LOW,
            title="Test Alert",
            message="This is a test alert from the Alert Engine service.",
            recipients=[recipient],
            channels=[channel],
            data={"test": True}
        )
        
        # Send alert
        response = await send_alert(test_alert, None, manager)
        
        return response
        
    except Exception as e:
        logger.error("Test alert failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/channels")
async def test_notification_channels():
    """Test notification channel connectivity."""
    try:
        results = {}
        
        if alert_manager:
            # Test email service
            try:
                results["email"] = await alert_manager.email_service.health_check()
            except:
                results["email"] = False
            
            # Test SMS service
            try:
                results["sms"] = await alert_manager.sms_service.health_check()
            except:
                results["sms"] = False
            
            # Test push service
            try:
                results["push"] = await alert_manager.push_service.health_check()
            except:
                results["push"] = False
            
            # Test webhook service
            try:
                results["webhook"] = await alert_manager.webhook_service.health_check()
            except:
                results["webhook"] = False
        
        return {
            "channel_status": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Channel testing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Administrative Endpoints

@app.post("/admin/reload-rules")
async def reload_alert_rules(
    manager: AlertManager = Depends(get_alert_manager)
):
    """Reload alert rules from database."""
    try:
        await manager._load_active_rules()
        
        return {
            "success": True,
            "message": f"Reloaded {len(manager.active_rules)} alert rules",
            "rule_count": len(manager.active_rules)
        }
        
    except Exception as e:
        logger.error("Alert rules reload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reload-preferences")
async def reload_user_preferences(
    manager: AlertManager = Depends(get_alert_manager)
):
    """Reload user preferences from database."""
    try:
        await manager._load_user_preferences()
        
        return {
            "success": True,
            "message": f"Reloaded {len(manager.user_preferences)} user preferences",
            "preference_count": len(manager.user_preferences)
        }
        
    except Exception as e:
        logger.error("User preferences reload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/cache")
async def clear_alert_cache(
    manager: AlertManager = Depends(get_alert_manager)
):
    """Clear alert processing cache."""
    try:
        if manager.redis_client:
            # Clear all alert-related cache keys
            keys = await manager.redis_client.keys("alert_*")
            if keys:
                await manager.redis_client.delete(*keys)
        
        return {
            "success": True,
            "message": "Alert cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Cache clearing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug
    ) 