"""Database utilities for Price Fetcher service."""

import asyncpg
import logging
from typing import Optional

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_db_pool() -> asyncpg.Pool:
    """Create and return database connection pool."""
    try:
        pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        
        logger.info("Database connection pool created successfully")
        return pool
        
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise


async def init_database_schema(pool: asyncpg.Pool):
    """Initialize database schema for price fetcher."""
    
    schema_sql = """
    -- Price data storage
    CREATE TABLE IF NOT EXISTS price_data (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(10) NOT NULL,
        current_price DECIMAL(12,4) NOT NULL,
        open_price DECIMAL(12,4),
        high_price DECIMAL(12,4),
        low_price DECIMAL(12,4),
        close_price DECIMAL(12,4),
        price_change DECIMAL(12,4),
        price_change_pct DECIMAL(8,4),
        volume BIGINT,
        market_cap BIGINT,
        data_source VARCHAR(20) NOT NULL,
        quality VARCHAR(20) NOT NULL,
        market_status VARCHAR(20),
        timestamp TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        INDEX (symbol),
        INDEX (timestamp),
        INDEX (data_source),
        INDEX (created_at)
    );
    
    -- Historical price data
    CREATE TABLE IF NOT EXISTS historical_prices (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(10) NOT NULL,
        date DATE NOT NULL,
        open_price DECIMAL(12,4) NOT NULL,
        high_price DECIMAL(12,4) NOT NULL,
        low_price DECIMAL(12,4) NOT NULL,
        close_price DECIMAL(12,4) NOT NULL,
        adj_close_price DECIMAL(12,4),
        volume BIGINT,
        dividend DECIMAL(8,4),
        split_ratio DECIMAL(8,4),
        data_source VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (symbol, date, data_source),
        INDEX (symbol),
        INDEX (date),
        INDEX (data_source)
    );
    
    -- Price alerts
    CREATE TABLE IF NOT EXISTS price_alerts (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        alert_type VARCHAR(20) NOT NULL,
        threshold_value DECIMAL(12,4) NOT NULL,
        is_active BOOLEAN DEFAULT true,
        notification_channels TEXT[],
        created_at TIMESTAMP DEFAULT NOW(),
        last_triggered TIMESTAMP,
        trigger_count INTEGER DEFAULT 0,
        INDEX (user_id),
        INDEX (symbol),
        INDEX (is_active)
    );
    
    -- Price subscriptions
    CREATE TABLE IF NOT EXISTS price_subscriptions (
        id SERIAL PRIMARY KEY,
        subscription_id VARCHAR(255) UNIQUE NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        symbols TEXT[] NOT NULL,
        update_frequency INTEGER DEFAULT 30,
        include_extended_hours BOOLEAN DEFAULT false,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW(),
        last_update TIMESTAMP,
        INDEX (user_id),
        INDEX (is_active),
        INDEX (subscription_id)
    );
    
    -- Data source status tracking
    CREATE TABLE IF NOT EXISTS data_source_status (
        id SERIAL PRIMARY KEY,
        source VARCHAR(20) NOT NULL,
        is_available BOOLEAN DEFAULT true,
        last_successful_request TIMESTAMP,
        error_count INTEGER DEFAULT 0,
        rate_limit_remaining INTEGER,
        rate_limit_reset TIMESTAMP,
        average_response_time_ms DECIMAL(8,2),
        last_updated TIMESTAMP DEFAULT NOW(),
        UNIQUE (source)
    );
    
    -- Performance metrics
    CREATE TABLE IF NOT EXISTS price_fetcher_metrics (
        id SERIAL PRIMARY KEY,
        metric_name VARCHAR(50) NOT NULL,
        metric_value DECIMAL(12,4) NOT NULL,
        metric_type VARCHAR(20) NOT NULL,
        tags JSONB,
        timestamp TIMESTAMP DEFAULT NOW(),
        INDEX (metric_name),
        INDEX (timestamp),
        INDEX (metric_type)
    );
    """
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(schema_sql)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise 