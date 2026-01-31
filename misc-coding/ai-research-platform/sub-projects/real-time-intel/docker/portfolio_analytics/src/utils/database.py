"""Database utilities for Portfolio Analytics service."""

import asyncio
import asyncpg
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import structlog

from ..config import config

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database connection and query manager."""
    
    def __init__(self):
        self.pool = None
        self.connection_config = {
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.name,
            'user': config.database.user,
            'password': config.database.password,
            'min_size': 5,
            'max_size': config.database.pool_size
        }
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(**self.connection_config)
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(query, *args)
                return dict(row) if row else None
                
        except Exception as e:
            logger.error("Database fetch_one failed", query=query, error=str(e))
            raise
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows from the database."""
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query, *args)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error("Database fetch_all failed", query=query, error=str(e))
            raise
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return the result status."""
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, *args)
                return result
                
        except Exception as e:
            logger.error("Database execute failed", query=query, error=str(e))
            raise
    
    async def execute_many(self, query: str, args_list: List[tuple]) -> None:
        """Execute a query multiple times with different arguments."""
        try:
            async with self.pool.acquire() as connection:
                await connection.executemany(query, args_list)
                
        except Exception as e:
            logger.error("Database execute_many failed", query=query, error=str(e))
            raise
    
    async def save_analytics_result(
        self,
        portfolio_id: str,
        analytics_data: Dict[str, Any],
        calculation_time_ms: int
    ) -> bool:
        """Save analytics calculation result to database."""
        try:
            query = """
                INSERT INTO portfolio_analytics_history 
                (portfolio_id, analysis_date, analytics_data, calculation_time_ms)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (portfolio_id, analysis_date) 
                DO UPDATE SET 
                    analytics_data = EXCLUDED.analytics_data,
                    calculation_time_ms = EXCLUDED.calculation_time_ms,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await self.execute(
                query,
                portfolio_id,
                datetime.utcnow().date(),
                analytics_data,
                calculation_time_ms
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save analytics result",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return False
    
    async def get_analytics_history(
        self,
        portfolio_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get historical analytics data for a portfolio."""
        try:
            query = """
                SELECT analysis_date, analytics_data, calculation_time_ms, created_at
                FROM portfolio_analytics_history
                WHERE portfolio_id = $1 
                AND analysis_date BETWEEN $2 AND $3
                ORDER BY analysis_date DESC
            """
            
            return await self.fetch_all(query, portfolio_id, start_date, end_date)
            
        except Exception as e:
            logger.error(
                "Failed to get analytics history",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return []
    
    async def get_portfolio_holdings(self, portfolio_id: str) -> List[Dict[str, Any]]:
        """Get current holdings for a portfolio."""
        try:
            query = """
                SELECT 
                    h.symbol,
                    h.quantity,
                    h.current_price,
                    h.market_value,
                    h.allocation_percentage,
                    h.sector,
                    h.asset_class,
                    h.last_updated,
                    a.name as asset_name,
                    a.exchange,
                    a.currency
                FROM holdings h
                LEFT JOIN assets a ON h.symbol = a.symbol
                WHERE h.portfolio_id = $1 
                AND h.status = 'active'
                ORDER BY h.allocation_percentage DESC
            """
            
            return await self.fetch_all(query, portfolio_id)
            
        except Exception as e:
            logger.error(
                "Failed to get portfolio holdings",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return []
    
    async def get_price_history(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get historical price data for symbols."""
        try:
            query = """
                SELECT symbol, date, open_price, high_price, low_price, 
                       close_price, volume, adjusted_close
                FROM price_history
                WHERE symbol = ANY($1) 
                AND date BETWEEN $2 AND $3
                ORDER BY symbol, date
            """
            
            return await self.fetch_all(query, symbols, start_date, end_date)
            
        except Exception as e:
            logger.error(
                "Failed to get price history",
                symbols=symbols,
                error=str(e)
            )
            return []
    
    async def save_performance_metrics(
        self,
        portfolio_id: str,
        period: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Save performance metrics to database."""
        try:
            query = """
                INSERT INTO performance_metrics 
                (portfolio_id, period, total_return, annualized_return, volatility,
                 sharpe_ratio, max_drawdown, alpha, beta, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (portfolio_id, period, DATE(created_at))
                DO UPDATE SET 
                    total_return = EXCLUDED.total_return,
                    annualized_return = EXCLUDED.annualized_return,
                    volatility = EXCLUDED.volatility,
                    sharpe_ratio = EXCLUDED.sharpe_ratio,
                    max_drawdown = EXCLUDED.max_drawdown,
                    alpha = EXCLUDED.alpha,
                    beta = EXCLUDED.beta,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await self.execute(
                query,
                portfolio_id,
                period,
                metrics.get('total_return'),
                metrics.get('annualized_return'),
                metrics.get('volatility'),
                metrics.get('sharpe_ratio'),
                metrics.get('max_drawdown'),
                metrics.get('alpha'),
                metrics.get('beta'),
                datetime.utcnow()
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save performance metrics",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return False
    
    async def save_risk_metrics(
        self,
        portfolio_id: str,
        period: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Save risk metrics to database."""
        try:
            query = """
                INSERT INTO risk_metrics 
                (portfolio_id, period, var_95, var_99, cvar_95, cvar_99,
                 historical_volatility, skewness, kurtosis, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (portfolio_id, period, DATE(created_at))
                DO UPDATE SET 
                    var_95 = EXCLUDED.var_95,
                    var_99 = EXCLUDED.var_99,
                    cvar_95 = EXCLUDED.cvar_95,
                    cvar_99 = EXCLUDED.cvar_99,
                    historical_volatility = EXCLUDED.historical_volatility,
                    skewness = EXCLUDED.skewness,
                    kurtosis = EXCLUDED.kurtosis,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await self.execute(
                query,
                portfolio_id,
                period,
                metrics.get('var_95'),
                metrics.get('var_99'),
                metrics.get('cvar_95'),
                metrics.get('cvar_99'),
                metrics.get('historical_volatility'),
                metrics.get('skewness'),
                metrics.get('kurtosis'),
                datetime.utcnow()
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save risk metrics",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return False
    
    async def get_benchmark_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get benchmark price data."""
        try:
            query = """
                SELECT date, close_price, volume
                FROM price_history
                WHERE symbol = $1 
                AND date BETWEEN $2 AND $3
                ORDER BY date
            """
            
            return await self.fetch_all(query, symbol, start_date, end_date)
            
        except Exception as e:
            logger.error(
                "Failed to get benchmark data",
                symbol=symbol,
                error=str(e)
            )
            return []
    
    async def save_correlation_matrix(
        self,
        portfolio_id: str,
        period: str,
        correlation_data: Dict[str, Any]
    ) -> bool:
        """Save correlation matrix to database."""
        try:
            query = """
                INSERT INTO correlation_matrices 
                (portfolio_id, period, correlation_data, average_correlation, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (portfolio_id, period, DATE(created_at))
                DO UPDATE SET 
                    correlation_data = EXCLUDED.correlation_data,
                    average_correlation = EXCLUDED.average_correlation,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await self.execute(
                query,
                portfolio_id,
                period,
                correlation_data,
                correlation_data.get('average_correlation'),
                datetime.utcnow()
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save correlation matrix",
                portfolio_id=portfolio_id,
                error=str(e)
            )
            return False
    
    async def get_portfolio_performance_summary(
        self,
        portfolio_ids: List[str],
        period: str
    ) -> List[Dict[str, Any]]:
        """Get performance summary for multiple portfolios."""
        try:
            query = """
                SELECT 
                    p.portfolio_id,
                    p.name,
                    p.total_value,
                    pm.total_return,
                    pm.annualized_return,
                    pm.volatility,
                    pm.sharpe_ratio,
                    pm.max_drawdown,
                    pm.created_at
                FROM portfolios p
                LEFT JOIN performance_metrics pm ON p.portfolio_id = pm.portfolio_id
                WHERE p.portfolio_id = ANY($1)
                AND (pm.period = $2 OR pm.period IS NULL)
                AND pm.created_at = (
                    SELECT MAX(created_at) 
                    FROM performance_metrics pm2 
                    WHERE pm2.portfolio_id = p.portfolio_id 
                    AND pm2.period = $2
                )
                ORDER BY pm.annualized_return DESC NULLS LAST
            """
            
            return await self.fetch_all(query, portfolio_ids, period)
            
        except Exception as e:
            logger.error(
                "Failed to get portfolio performance summary",
                portfolio_ids=portfolio_ids,
                error=str(e)
            )
            return []
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            return True
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Database schema creation queries
ANALYTICS_SCHEMA_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS portfolio_analytics_history (
        id SERIAL PRIMARY KEY,
        portfolio_id VARCHAR(50) NOT NULL,
        analysis_date DATE NOT NULL,
        analytics_data JSONB NOT NULL,
        calculation_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, analysis_date)
    );
    """,
    
    """
    CREATE TABLE IF NOT EXISTS performance_metrics (
        id SERIAL PRIMARY KEY,
        portfolio_id VARCHAR(50) NOT NULL,
        period VARCHAR(20) NOT NULL,
        total_return DECIMAL(10, 6),
        annualized_return DECIMAL(10, 6),
        volatility DECIMAL(10, 6),
        sharpe_ratio DECIMAL(10, 6),
        max_drawdown DECIMAL(10, 6),
        alpha DECIMAL(10, 6),
        beta DECIMAL(10, 6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, period, DATE(created_at))
    );
    """,
    
    """
    CREATE TABLE IF NOT EXISTS risk_metrics (
        id SERIAL PRIMARY KEY,
        portfolio_id VARCHAR(50) NOT NULL,
        period VARCHAR(20) NOT NULL,
        var_95 DECIMAL(10, 6),
        var_99 DECIMAL(10, 6),
        cvar_95 DECIMAL(10, 6),
        cvar_99 DECIMAL(10, 6),
        historical_volatility DECIMAL(10, 6),
        skewness DECIMAL(10, 6),
        kurtosis DECIMAL(10, 6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, period, DATE(created_at))
    );
    """,
    
    """
    CREATE TABLE IF NOT EXISTS correlation_matrices (
        id SERIAL PRIMARY KEY,
        portfolio_id VARCHAR(50) NOT NULL,
        period VARCHAR(20) NOT NULL,
        correlation_data JSONB NOT NULL,
        average_correlation DECIMAL(6, 4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, period, DATE(created_at))
    );
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_portfolio_analytics_portfolio_date 
    ON portfolio_analytics_history(portfolio_id, analysis_date);
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_performance_metrics_portfolio_period 
    ON performance_metrics(portfolio_id, period, created_at);
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_risk_metrics_portfolio_period 
    ON risk_metrics(portfolio_id, period, created_at);
    """
]


async def initialize_analytics_schema(db_manager: DatabaseManager):
    """Initialize analytics database schema."""
    try:
        for query in ANALYTICS_SCHEMA_QUERIES:
            await db_manager.execute(query)
        
        logger.info("Analytics database schema initialized successfully")
        
    except Exception as e:
        logger.error("Analytics schema initialization failed", error=str(e))
        raise 