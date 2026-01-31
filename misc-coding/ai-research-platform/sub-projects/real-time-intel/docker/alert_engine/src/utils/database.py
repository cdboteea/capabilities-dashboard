"""Database utilities for Alert Engine service."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncpg
from asyncpg import Pool
import structlog

from ..config import config
from ..models.alert_models import (
    AlertEvent, NotificationDelivery, AlertCondition, UserPreferences,
    AlertBatch, AlertStatus
)

logger = structlog.get_logger(__name__)


class AlertDatabase:
    """Database interface for Alert Engine."""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=config.database.host,
                port=config.database.port,
                database=config.database.name,
                user=config.database.user,
                password=config.database.password,
                min_size=config.database.pool_size,
                max_size=config.database.pool_size + config.database.max_overflow,
                command_timeout=60
            )
            
            # Ensure tables exist
            await self._create_tables()
            
            logger.info("Alert database initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize alert database", error=str(e))
            raise
    
    async def _create_tables(self):
        """Create necessary database tables."""
        async with self.pool.acquire() as conn:
            # Alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    alert_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    source_service VARCHAR(100),
                    source_event_id VARCHAR(255),
                    asset_symbol VARCHAR(20),
                    portfolio_id VARCHAR(255),
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    summary TEXT,
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    INDEX idx_alerts_type (alert_type),
                    INDEX idx_alerts_priority (priority),
                    INDEX idx_alerts_created (created_at),
                    INDEX idx_alerts_asset (asset_symbol),
                    INDEX idx_alerts_expires (expires_at)
                )
            """)
            
            # Alert deliveries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_deliveries (
                    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    alert_id UUID NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    channel VARCHAR(20) NOT NULL,
                    recipient TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    subject TEXT,
                    content TEXT NOT NULL,
                    template_used VARCHAR(100),
                    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    sent_at TIMESTAMP WITH TIME ZONE,
                    failed_at TIMESTAMP WITH TIME ZONE,
                    error_message TEXT,
                    error_code VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX idx_deliveries_alert (alert_id),
                    INDEX idx_deliveries_user (user_id),
                    INDEX idx_deliveries_status (status),
                    INDEX idx_deliveries_channel (channel),
                    INDEX idx_deliveries_scheduled (scheduled_at)
                )
            """)
            
            # Alert conditions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_conditions (
                    condition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    asset_symbol VARCHAR(20),
                    condition_type VARCHAR(50) NOT NULL,
                    threshold_value DECIMAL(20,8),
                    comparison_operator VARCHAR(20) DEFAULT 'greater_than',
                    percentage_change DECIMAL(5,2),
                    time_window_minutes INTEGER DEFAULT 60,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX idx_conditions_user (user_id),
                    INDEX idx_conditions_asset (asset_symbol),
                    INDEX idx_conditions_type (condition_type),
                    INDEX idx_conditions_active (is_active)
                )
            """)
            
            # Notification preferences table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email_enabled BOOLEAN DEFAULT true,
                    sms_enabled BOOLEAN DEFAULT false,
                    push_enabled BOOLEAN DEFAULT true,
                    webhook_enabled BOOLEAN DEFAULT false,
                    email_address VARCHAR(255),
                    phone_number VARCHAR(20),
                    push_token TEXT,
                    webhook_url TEXT,
                    price_alerts BOOLEAN DEFAULT true,
                    sentiment_alerts BOOLEAN DEFAULT true,
                    portfolio_alerts BOOLEAN DEFAULT true,
                    news_alerts BOOLEAN DEFAULT true,
                    min_priority VARCHAR(20) DEFAULT 'low',
                    quiet_hours_start TIME,
                    quiet_hours_end TIME,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Alert batches table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_batches (
                    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    combined_title TEXT NOT NULL,
                    combined_message TEXT NOT NULL,
                    alert_count INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    INDEX idx_batches_user (user_id),
                    INDEX idx_batches_status (status),
                    INDEX idx_batches_scheduled (scheduled_at)
                )
            """)
            
            # Alert metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    alerts_created INTEGER DEFAULT 0,
                    alerts_sent INTEGER DEFAULT 0,
                    alerts_failed INTEGER DEFAULT 0,
                    email_sent INTEGER DEFAULT 0,
                    sms_sent INTEGER DEFAULT 0,
                    push_sent INTEGER DEFAULT 0,
                    webhook_sent INTEGER DEFAULT 0,
                    critical_alerts INTEGER DEFAULT 0,
                    high_alerts INTEGER DEFAULT 0,
                    medium_alerts INTEGER DEFAULT 0,
                    low_alerts INTEGER DEFAULT 0,
                    avg_delivery_time_seconds DECIMAL(10,2) DEFAULT 0,
                    rate_limited_count INTEGER DEFAULT 0,
                    email_errors INTEGER DEFAULT 0,
                    sms_errors INTEGER DEFAULT 0,
                    push_errors INTEGER DEFAULT 0,
                    webhook_errors INTEGER DEFAULT 0,
                    INDEX idx_metrics_timestamp (timestamp)
                )
            """)
    
    async def store_alert(self, alert: AlertEvent) -> str:
        """Store alert in database."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO alerts (
                    alert_type, priority, source_service, source_event_id,
                    asset_symbol, portfolio_id, title, message, summary,
                    data, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING alert_id
            """, 
                alert.alert_type.value,
                alert.priority.value,
                alert.source_service,
                alert.source_event_id,
                alert.asset_symbol,
                alert.portfolio_id,
                alert.title,
                alert.message,
                alert.summary,
                alert.data,
                alert.expires_at
            )
            
            return str(result['alert_id'])
    
    async def store_delivery(self, delivery: NotificationDelivery) -> str:
        """Store delivery record in database."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO alert_deliveries (
                    alert_id, user_id, channel, recipient, status,
                    attempts, max_attempts, subject, content, template_used,
                    scheduled_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING delivery_id
            """,
                delivery.alert_id,
                delivery.user_id,
                delivery.channel.value,
                delivery.recipient,
                delivery.status.value,
                delivery.attempts,
                delivery.max_attempts,
                delivery.subject,
                delivery.content,
                delivery.template_used,
                delivery.scheduled_at
            )
            
            return str(result['delivery_id'])
    
    async def update_delivery(self, delivery: NotificationDelivery):
        """Update delivery record."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE alert_deliveries SET
                    status = $1,
                    attempts = $2,
                    sent_at = $3,
                    failed_at = $4,
                    error_message = $5,
                    error_code = $6,
                    updated_at = NOW()
                WHERE delivery_id = $7
            """,
                delivery.status.value,
                delivery.attempts,
                delivery.sent_at,
                delivery.failed_at,
                delivery.error_message,
                delivery.error_code,
                delivery.delivery_id
            )
    
    async def store_batch(self, batch: AlertBatch) -> str:
        """Store alert batch in database."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO alert_batches (
                    user_id, priority, combined_title, combined_message,
                    alert_count, status, scheduled_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING batch_id
            """,
                batch.user_id,
                batch.priority.value,
                batch.combined_title,
                batch.combined_message,
                len(batch.alerts),
                batch.status.value,
                batch.scheduled_at
            )
            
            return str(result['batch_id'])
    
    async def get_matching_conditions(self, alert: AlertEvent) -> List[AlertCondition]:
        """Get alert conditions that match the alert."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alert_conditions
                WHERE is_active = true
                AND (asset_symbol IS NULL OR asset_symbol = $1)
                AND condition_type = $2
            """, alert.asset_symbol, alert.alert_type.value)
            
            conditions = []
            for row in rows:
                condition = AlertCondition(
                    condition_id=str(row['condition_id']),
                    user_id=row['user_id'],
                    asset_symbol=row['asset_symbol'],
                    condition_type=row['condition_type'],
                    threshold_value=float(row['threshold_value']) if row['threshold_value'] else None,
                    comparison_operator=row['comparison_operator'],
                    percentage_change=float(row['percentage_change']) if row['percentage_change'] else None,
                    time_window_minutes=row['time_window_minutes'],
                    is_active=row['is_active'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                conditions.append(condition)
            
            return conditions
    
    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get user notification preferences."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM notification_preferences WHERE user_id = $1
            """, user_id)
            
            if row:
                return NotificationPreferences(
                    user_id=row['user_id'],
                    email_enabled=row['email_enabled'],
                    sms_enabled=row['sms_enabled'],
                    push_enabled=row['push_enabled'],
                    webhook_enabled=row['webhook_enabled'],
                    email_address=row['email_address'],
                    phone_number=row['phone_number'],
                    push_token=row['push_token'],
                    webhook_url=row['webhook_url'],
                    price_alerts=row['price_alerts'],
                    sentiment_alerts=row['sentiment_alerts'],
                    portfolio_alerts=row['portfolio_alerts'],
                    news_alerts=row['news_alerts'],
                    min_priority=row['min_priority'],
                    quiet_hours_start=row['quiet_hours_start'].strftime('%H:%M') if row['quiet_hours_start'] else None,
                    quiet_hours_end=row['quiet_hours_end'].strftime('%H:%M') if row['quiet_hours_end'] else None,
                    timezone=row['timezone']
                )
            else:
                # Return default preferences
                return NotificationPreferences(user_id=user_id)
    
    async def update_user_preferences(self, preferences: UserPreferences):
        """Update user notification preferences."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO notification_preferences (
                    user_id, email_enabled, sms_enabled, push_enabled, webhook_enabled,
                    email_address, phone_number, push_token, webhook_url,
                    price_alerts, sentiment_alerts, portfolio_alerts, news_alerts,
                    min_priority, quiet_hours_start, quiet_hours_end, timezone,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    email_enabled = EXCLUDED.email_enabled,
                    sms_enabled = EXCLUDED.sms_enabled,
                    push_enabled = EXCLUDED.push_enabled,
                    webhook_enabled = EXCLUDED.webhook_enabled,
                    email_address = EXCLUDED.email_address,
                    phone_number = EXCLUDED.phone_number,
                    push_token = EXCLUDED.push_token,
                    webhook_url = EXCLUDED.webhook_url,
                    price_alerts = EXCLUDED.price_alerts,
                    sentiment_alerts = EXCLUDED.sentiment_alerts,
                    portfolio_alerts = EXCLUDED.portfolio_alerts,
                    news_alerts = EXCLUDED.news_alerts,
                    min_priority = EXCLUDED.min_priority,
                    quiet_hours_start = EXCLUDED.quiet_hours_start,
                    quiet_hours_end = EXCLUDED.quiet_hours_end,
                    timezone = EXCLUDED.timezone,
                    updated_at = NOW()
            """,
                preferences.user_id,
                preferences.email_enabled,
                preferences.sms_enabled,
                preferences.push_enabled,
                preferences.webhook_enabled,
                preferences.email_address,
                preferences.phone_number,
                preferences.push_token,
                preferences.webhook_url,
                preferences.price_alerts,
                preferences.sentiment_alerts,
                preferences.portfolio_alerts,
                preferences.news_alerts,
                preferences.min_priority.value,
                datetime.strptime(preferences.quiet_hours_start, '%H:%M').time() if preferences.quiet_hours_start else None,
                datetime.strptime(preferences.quiet_hours_end, '%H:%M').time() if preferences.quiet_hours_end else None,
                preferences.timezone
            )
    
    async def store_condition(self, condition: AlertCondition) -> str:
        """Store alert condition."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO alert_conditions (
                    user_id, asset_symbol, condition_type, threshold_value,
                    comparison_operator, percentage_change, time_window_minutes,
                    is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING condition_id
            """,
                condition.user_id,
                condition.asset_symbol,
                condition.condition_type.value,
                condition.threshold_value,
                condition.comparison_operator,
                condition.percentage_change,
                condition.time_window_minutes,
                condition.is_active
            )
            
            return str(result['condition_id'])
    
    async def get_user_conditions(self, user_id: str) -> List[AlertCondition]:
        """Get all conditions for a user."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alert_conditions
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)
            
            conditions = []
            for row in rows:
                condition = AlertCondition(
                    condition_id=str(row['condition_id']),
                    user_id=row['user_id'],
                    asset_symbol=row['asset_symbol'],
                    condition_type=row['condition_type'],
                    threshold_value=float(row['threshold_value']) if row['threshold_value'] else None,
                    comparison_operator=row['comparison_operator'],
                    percentage_change=float(row['percentage_change']) if row['percentage_change'] else None,
                    time_window_minutes=row['time_window_minutes'],
                    is_active=row['is_active'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                conditions.append(condition)
            
            return conditions
    
    async def delete_condition(self, condition_id: str, user_id: str) -> bool:
        """Delete alert condition."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM alert_conditions
                WHERE condition_id = $1 AND user_id = $2
            """, condition_id, user_id)
            
            return result == "DELETE 1"
    
    async def get_alerts(
        self,
        user_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AlertEvent]:
        """Get alerts with filtering."""
        query = """
            SELECT a.* FROM alerts a
            LEFT JOIN alert_deliveries d ON a.alert_id = d.alert_id
            WHERE 1=1
        """
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            query += f" AND d.user_id = ${param_count}"
            params.append(user_id)
        
        if alert_type:
            param_count += 1
            query += f" AND a.alert_type = ${param_count}"
            params.append(alert_type)
        
        if priority:
            param_count += 1
            query += f" AND a.priority = ${param_count}"
            params.append(priority)
        
        query += " ORDER BY a.created_at DESC"
        
        param_count += 1
        query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        query += f" OFFSET ${param_count}"
        params.append(offset)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            alerts = []
            for row in rows:
                alert = AlertEvent(
                    alert_id=str(row['alert_id']),
                    alert_type=row['alert_type'],
                    priority=row['priority'],
                    source_service=row['source_service'],
                    source_event_id=row['source_event_id'],
                    asset_symbol=row['asset_symbol'],
                    portfolio_id=row['portfolio_id'],
                    title=row['title'],
                    message=row['message'],
                    summary=row['summary'],
                    data=row['data'] or {},
                    created_at=row['created_at'],
                    expires_at=row['expires_at']
                )
                alerts.append(alert)
            
            return alerts
    
    async def get_delivery_status(self, delivery_id: str) -> Optional[AlertDelivery]:
        """Get delivery status."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM alert_deliveries WHERE delivery_id = $1
            """, delivery_id)
            
            if row:
                return AlertDelivery(
                    delivery_id=str(row['delivery_id']),
                    alert_id=str(row['alert_id']),
                    user_id=row['user_id'],
                    channel=row['channel'],
                    recipient=row['recipient'],
                    status=row['status'],
                    attempts=row['attempts'],
                    max_attempts=row['max_attempts'],
                    subject=row['subject'],
                    content=row['content'],
                    template_used=row['template_used'],
                    scheduled_at=row['scheduled_at'],
                    sent_at=row['sent_at'],
                    failed_at=row['failed_at'],
                    error_message=row['error_message'],
                    error_code=row['error_code'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            
            return None
    
    async def cleanup_expired_alerts(self) -> int:
        """Clean up expired alerts."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM alerts
                WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """)
            
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
            return count
    
    async def store_metrics(self, metrics: AlertMetrics):
        """Store alert metrics."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alert_metrics (
                    timestamp, alerts_created, alerts_sent, alerts_failed,
                    email_sent, sms_sent, push_sent, webhook_sent,
                    critical_alerts, high_alerts, medium_alerts, low_alerts,
                    avg_delivery_time_seconds, rate_limited_count,
                    email_errors, sms_errors, push_errors, webhook_errors
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """,
                metrics.timestamp,
                metrics.alerts_created,
                metrics.alerts_sent,
                metrics.alerts_failed,
                metrics.email_sent,
                metrics.sms_sent,
                metrics.push_sent,
                metrics.webhook_sent,
                metrics.critical_alerts,
                metrics.high_alerts,
                metrics.medium_alerts,
                metrics.low_alerts,
                metrics.avg_delivery_time_seconds,
                metrics.rate_limited_count,
                metrics.email_errors,
                metrics.sms_errors,
                metrics.push_errors,
                metrics.webhook_errors
            )
    
    async def get_metrics(self, hours: int = 24) -> List[AlertMetrics]:
        """Get recent metrics."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alert_metrics
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
            """, hours)
            
            metrics_list = []
            for row in rows:
                metrics = AlertMetrics(
                    timestamp=row['timestamp'],
                    alerts_created=row['alerts_created'],
                    alerts_sent=row['alerts_sent'],
                    alerts_failed=row['alerts_failed'],
                    email_sent=row['email_sent'],
                    sms_sent=row['sms_sent'],
                    push_sent=row['push_sent'],
                    webhook_sent=row['webhook_sent'],
                    critical_alerts=row['critical_alerts'],
                    high_alerts=row['high_alerts'],
                    medium_alerts=row['medium_alerts'],
                    low_alerts=row['low_alerts'],
                    avg_delivery_time_seconds=float(row['avg_delivery_time_seconds']),
                    rate_limited_count=row['rate_limited_count'],
                    email_errors=row['email_errors'],
                    sms_errors=row['sms_errors'],
                    push_errors=row['push_errors'],
                    webhook_errors=row['webhook_errors']
                )
                metrics_list.append(metrics)
            
            return metrics_list
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close() 