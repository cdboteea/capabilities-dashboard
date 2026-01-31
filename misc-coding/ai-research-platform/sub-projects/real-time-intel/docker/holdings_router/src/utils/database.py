"""Database utilities for Holdings Router service."""

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
    """Initialize database schema for holdings router."""
    
    schema_sql = """
    -- Event routing decisions
    CREATE TABLE IF NOT EXISTS event_routing (
        id SERIAL PRIMARY KEY,
        event_id VARCHAR(255) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        relevance_score DECIMAL(5,4) NOT NULL,
        relevance_level VARCHAR(20) NOT NULL,
        entity_match_score DECIMAL(5,4) NOT NULL,
        sector_correlation_score DECIMAL(5,4) NOT NULL,
        sentiment_impact_score DECIMAL(5,4) NOT NULL,
        position_weight_score DECIMAL(5,4) NOT NULL,
        matched_entities TEXT[],
        affected_positions TEXT[],
        reasoning TEXT,
        confidence DECIMAL(5,4) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        INDEX (event_id),
        INDEX (user_id),
        INDEX (relevance_level),
        INDEX (created_at)
    );
    
    -- Portfolio summaries
    CREATE TABLE IF NOT EXISTS portfolios (
        user_id VARCHAR(255) PRIMARY KEY,
        total_value DECIMAL(15,2) NOT NULL,
        cash_balance DECIMAL(15,2) DEFAULT 0,
        total_return_pct DECIMAL(8,4),
        risk_level VARCHAR(20) DEFAULT 'medium',
        last_updated TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Individual holdings
    CREATE TABLE IF NOT EXISTS holdings (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        name VARCHAR(255) NOT NULL,
        shares DECIMAL(15,4) NOT NULL,
        avg_cost DECIMAL(10,4) NOT NULL,
        market_value DECIMAL(15,2) NOT NULL,
        sector VARCHAR(50),
        position_pct DECIMAL(6,3),
        unrealized_pnl DECIMAL(15,2),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES portfolios(user_id),
        INDEX (user_id),
        INDEX (symbol),
        INDEX (sector)
    );
    
    -- User preferences
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id VARCHAR(255) PRIMARY KEY,
        min_relevance_level VARCHAR(20) DEFAULT 'low',
        notification_channels TEXT[],
        quiet_hours_start TIME,
        quiet_hours_end TIME,
        timezone VARCHAR(50) DEFAULT 'UTC',
        sentiment_threshold DECIMAL(3,2) DEFAULT 0.3,
        position_threshold DECIMAL(4,3) DEFAULT 0.01,
        last_updated TIMESTAMP DEFAULT NOW()
    );
    
    -- Routing performance tracking
    CREATE TABLE IF NOT EXISTS routing_decisions (
        id SERIAL PRIMARY KEY,
        event_id VARCHAR(255) NOT NULL,
        total_users_matched INTEGER NOT NULL,
        processing_time_ms DECIMAL(8,2) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        INDEX (event_id),
        INDEX (created_at)
    );
    """
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(schema_sql)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise
