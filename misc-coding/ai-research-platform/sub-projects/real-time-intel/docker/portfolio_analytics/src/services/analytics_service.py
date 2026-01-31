"""Main analytics service for portfolio performance and risk analysis."""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import redis.asyncio as redis
import json
import structlog

from ..models.analytics_models import (
    PortfolioAnalytics, PerformanceMetrics, RiskMetrics, AttributionMetrics,
    CorrelationMatrix, OptimizationResult, ScenarioAnalysis,
    TimePeriod, AnalyticsRequest, AnalyticsResponse
)
from ..calculators.performance_calculator import PerformanceCalculator
from ..calculators.risk_calculator import RiskCalculator
from ..utils.database import DatabaseManager
from ..config import config

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Main service for portfolio analytics calculations."""
    
    def __init__(self):
        self.performance_calculator = PerformanceCalculator()
        self.risk_calculator = RiskCalculator()
        self.db_manager = DatabaseManager()
        self.redis_client = None
        self._cache_ttl = config.calculations.cache_ttl_seconds
    
    async def initialize(self):
        """Initialize service connections."""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(config.redis.url)
            await self.redis_client.ping()
            
            logger.info("Analytics service initialized successfully")
            
        except Exception as e:
            logger.error("Analytics service initialization failed", error=str(e))
            raise
    
    async def calculate_portfolio_analytics(
        self,
        request: AnalyticsRequest
    ) -> AnalyticsResponse:
        """Calculate comprehensive portfolio analytics."""
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            cache_key = f"analytics:{request.portfolio_id}:{request.period.value}"
            cached_result = await self._get_cached_analytics(cache_key)
            
            if cached_result:
                calculation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                return AnalyticsResponse(
                    success=True,
                    analytics=cached_result,
                    calculation_time_ms=calculation_time
                )
            
            # Get portfolio data
            portfolio_data = await self._get_portfolio_data(request.portfolio_id)
            if not portfolio_data:
                return AnalyticsResponse(
                    success=False,
                    error_message=f"Portfolio {request.portfolio_id} not found",
                    calculation_time_ms=0
                )
            
            # Get price data and calculate returns
            returns_data = await self._get_portfolio_returns(
                portfolio_data, request.period
            )
            
            if returns_data.empty:
                return AnalyticsResponse(
                    success=False,
                    error_message="Insufficient price data for analysis",
                    calculation_time_ms=0
                )
            
            # Get benchmark data if specified
            benchmark_returns = None
            if request.benchmark_symbol:
                benchmark_returns = await self._get_benchmark_returns(
                    request.benchmark_symbol, request.period
                )
            
            # Calculate core analytics
            analytics = await self._calculate_core_analytics(
                portfolio_data, returns_data, benchmark_returns, request
            )
            
            # Cache the results
            await self._cache_analytics(cache_key, analytics)
            
            calculation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return AnalyticsResponse(
                success=True,
                analytics=analytics,
                calculation_time_ms=calculation_time
            )
            
        except Exception as e:
            logger.error(
                "Portfolio analytics calculation failed",
                portfolio_id=request.portfolio_id,
                error=str(e)
            )
            
            calculation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return AnalyticsResponse(
                success=False,
                error_message=str(e),
                calculation_time_ms=calculation_time
            )
    
    async def _get_portfolio_data(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Get portfolio holdings and metadata."""
        try:
            query = """
                SELECT p.*, h.symbol, h.quantity, h.current_price, h.market_value,
                       h.sector, h.asset_class, h.allocation_percentage
                FROM portfolios p
                LEFT JOIN holdings h ON p.portfolio_id = h.portfolio_id
                WHERE p.portfolio_id = $1 AND p.status = 'active'
            """
            
            rows = await self.db_manager.fetch_all(query, portfolio_id)
            
            if not rows:
                return None
            
            # Group data by portfolio
            portfolio_info = {
                'portfolio_id': rows[0]['portfolio_id'],
                'name': rows[0]['name'],
                'total_value': rows[0]['total_value'],
                'holdings': []
            }
            
            for row in rows:
                if row['symbol']:  # Skip if no holdings
                    portfolio_info['holdings'].append({
                        'symbol': row['symbol'],
                        'quantity': row['quantity'],
                        'current_price': row['current_price'],
                        'market_value': row['market_value'],
                        'sector': row['sector'],
                        'asset_class': row['asset_class'],
                        'allocation_percentage': row['allocation_percentage']
                    })
            
            return portfolio_info
            
        except Exception as e:
            logger.error("Portfolio data retrieval failed", portfolio_id=portfolio_id, error=str(e))
            return None
    
    async def _get_portfolio_returns(
        self,
        portfolio_data: Dict[str, Any],
        period: TimePeriod
    ) -> pd.Series:
        """Calculate portfolio returns based on holdings."""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return pd.Series()
            
            # Get price data for all holdings
            symbols = [holding['symbol'] for holding in holdings]
            weights = {holding['symbol']: holding['allocation_percentage'] / 100 
                      for holding in holdings}
            
            # Get historical prices
            price_data = await self._get_historical_prices(symbols, period)
            
            if price_data.empty:
                return pd.Series()
            
            # Calculate individual asset returns
            returns_data = price_data.pct_change().dropna()
            
            # Calculate weighted portfolio returns
            portfolio_returns = pd.Series(0.0, index=returns_data.index)
            
            for symbol in symbols:
                if symbol in returns_data.columns:
                    weight = weights.get(symbol, 0)
                    portfolio_returns += returns_data[symbol] * weight
            
            return portfolio_returns
            
        except Exception as e:
            logger.error("Portfolio returns calculation failed", error=str(e))
            return pd.Series()
    
    async def _get_historical_prices(
        self,
        symbols: List[str],
        period: TimePeriod
    ) -> pd.DataFrame:
        """Get historical price data for symbols."""
        try:
            # Determine date range
            end_date = datetime.utcnow().date()
            
            if period == TimePeriod.ONE_DAY:
                start_date = end_date - timedelta(days=7)  # Get more data for calculation
            elif period == TimePeriod.ONE_WEEK:
                start_date = end_date - timedelta(days=30)
            elif period == TimePeriod.ONE_MONTH:
                start_date = end_date - timedelta(days=60)
            elif period == TimePeriod.THREE_MONTHS:
                start_date = end_date - timedelta(days=120)
            elif period == TimePeriod.SIX_MONTHS:
                start_date = end_date - timedelta(days=200)
            elif period == TimePeriod.ONE_YEAR:
                start_date = end_date - timedelta(days=400)
            elif period == TimePeriod.TWO_YEARS:
                start_date = end_date - timedelta(days=800)
            elif period == TimePeriod.FIVE_YEARS:
                start_date = end_date - timedelta(days=2000)
            else:  # MAX
                start_date = end_date - timedelta(days=3650)  # 10 years max
            
            # Query price data
            query = """
                SELECT symbol, date, close_price
                FROM price_history
                WHERE symbol = ANY($1) AND date >= $2 AND date <= $3
                ORDER BY symbol, date
            """
            
            rows = await self.db_manager.fetch_all(query, symbols, start_date, end_date)
            
            if not rows:
                return pd.DataFrame()
            
            # Convert to DataFrame and pivot
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            
            price_data = df.pivot(index='date', columns='symbol', values='close_price')
            price_data = price_data.fillna(method='ffill').dropna()
            
            return price_data
            
        except Exception as e:
            logger.error("Historical prices retrieval failed", symbols=symbols, error=str(e))
            return pd.DataFrame()
    
    async def _get_benchmark_returns(
        self,
        benchmark_symbol: str,
        period: TimePeriod
    ) -> Optional[pd.Series]:
        """Get benchmark returns for comparison."""
        try:
            benchmark_prices = await self._get_historical_prices([benchmark_symbol], period)
            
            if benchmark_prices.empty or benchmark_symbol not in benchmark_prices.columns:
                return None
            
            benchmark_returns = benchmark_prices[benchmark_symbol].pct_change().dropna()
            return benchmark_returns
            
        except Exception as e:
            logger.error("Benchmark returns retrieval failed", symbol=benchmark_symbol, error=str(e))
            return None
    
    async def _calculate_core_analytics(
        self,
        portfolio_data: Dict[str, Any],
        returns_data: pd.Series,
        benchmark_returns: Optional[pd.Series],
        request: AnalyticsRequest
    ) -> PortfolioAnalytics:
        """Calculate core analytics metrics."""
        try:
            # Calculate performance metrics
            performance = await self.performance_calculator.calculate_portfolio_performance(
                returns_data, benchmark_returns, request.period
            )
            
            # Calculate risk metrics
            risk = await self.risk_calculator.calculate_portfolio_risk(
                returns_data, period=request.period
            )
            
            # Calculate attribution metrics
            attribution = await self._calculate_attribution(
                portfolio_data, returns_data, benchmark_returns, request.period
            )
            
            # Calculate correlation analysis if requested
            correlation = None
            if len(portfolio_data.get('holdings', [])) > 1:
                correlation = await self._calculate_correlation_analysis(
                    portfolio_data, request.period
                )
            
            # Calculate optimization if requested
            optimization = None
            if request.include_optimization:
                optimization = await self._calculate_optimization(
                    portfolio_data, returns_data
                )
            
            # Calculate scenario analysis if requested
            scenarios = None
            if request.include_scenarios:
                scenarios = await self._calculate_scenario_analysis(
                    portfolio_data, returns_data
                )
            
            # Calculate sector and asset class allocations
            sector_allocation, asset_class_allocation = self._calculate_allocations(portfolio_data)
            
            return PortfolioAnalytics(
                portfolio_id=request.portfolio_id,
                performance=performance,
                risk=risk,
                attribution=attribution,
                correlation=correlation,
                optimization=optimization,
                scenarios=scenarios,
                total_value=Decimal(str(portfolio_data.get('total_value', 0))),
                asset_count=len(portfolio_data.get('holdings', [])),
                sector_allocation=sector_allocation,
                asset_class_allocation=asset_class_allocation
            )
            
        except Exception as e:
            logger.error("Core analytics calculation failed", error=str(e))
            raise
    
    async def _calculate_attribution(
        self,
        portfolio_data: Dict[str, Any],
        returns_data: pd.Series,
        benchmark_returns: Optional[pd.Series],
        period: TimePeriod
    ) -> AttributionMetrics:
        """Calculate performance attribution."""
        try:
            holdings = portfolio_data.get('holdings', [])
            
            # Basic attribution calculation
            sector_attribution = {}
            asset_class_attribution = {}
            top_contributors = []
            top_detractors = []
            
            # Calculate sector-wise attribution
            sector_performance = {}
            for holding in holdings:
                sector = holding.get('sector', 'Unknown')
                weight = holding.get('allocation_percentage', 0) / 100
                
                # Simplified attribution - would need individual asset returns for full calculation
                contribution = weight * 0.1  # Placeholder calculation
                
                if sector not in sector_attribution:
                    sector_attribution[sector] = 0
                sector_attribution[sector] += contribution
            
            # Calculate asset class attribution
            for holding in holdings:
                asset_class = holding.get('asset_class', 'Unknown')
                weight = holding.get('allocation_percentage', 0) / 100
                
                contribution = weight * 0.1  # Placeholder calculation
                
                if asset_class not in asset_class_attribution:
                    asset_class_attribution[asset_class] = 0
                asset_class_attribution[asset_class] += contribution
            
            # Top contributors and detractors (simplified)
            for holding in holdings[:5]:  # Top 5
                top_contributors.append({
                    'symbol': holding['symbol'],
                    'contribution': holding.get('allocation_percentage', 0) * 0.01,
                    'weight': holding.get('allocation_percentage', 0) / 100
                })
            
            benchmark_return = benchmark_returns.sum() if benchmark_returns is not None else 0.0
            active_return = returns_data.sum() - benchmark_return
            
            return AttributionMetrics(
                allocation_effect=0.02,  # Placeholder
                selection_effect=0.01,  # Placeholder
                interaction_effect=0.005,  # Placeholder
                sector_attribution=sector_attribution,
                asset_class_attribution=asset_class_attribution,
                top_contributors=top_contributors,
                top_detractors=top_detractors,
                period=period,
                benchmark_return=benchmark_return,
                active_return=active_return
            )
            
        except Exception as e:
            logger.error("Attribution calculation failed", error=str(e))
            # Return empty attribution on error
            return AttributionMetrics(
                allocation_effect=0.0,
                selection_effect=0.0,
                interaction_effect=0.0,
                period=period,
                benchmark_return=0.0,
                active_return=0.0
            )
    
    async def _calculate_correlation_analysis(
        self,
        portfolio_data: Dict[str, Any],
        period: TimePeriod
    ) -> Optional[CorrelationMatrix]:
        """Calculate correlation analysis for portfolio holdings."""
        try:
            holdings = portfolio_data.get('holdings', [])
            symbols = [holding['symbol'] for holding in holdings]
            
            if len(symbols) < 2:
                return None
            
            # Get price data for correlation calculation
            price_data = await self._get_historical_prices(symbols, period)
            
            if price_data.empty:
                return None
            
            # Calculate returns
            returns_data = price_data.pct_change().dropna()
            
            # Calculate correlation matrix
            corr_matrix = self.risk_calculator.calculate_correlation_matrix(returns_data)
            
            if corr_matrix.empty:
                return None
            
            # Convert to dictionary format
            correlation_dict = {}
            for i, asset1 in enumerate(corr_matrix.index):
                correlation_dict[asset1] = {}
                for j, asset2 in enumerate(corr_matrix.columns):
                    correlation_dict[asset1][asset2] = float(corr_matrix.iloc[i, j])
            
            # Calculate summary statistics
            correlations = []
            for i in range(len(corr_matrix.index)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    correlations.append(corr_matrix.iloc[i, j])
            
            avg_correlation = np.mean(correlations) if correlations else 0.0
            max_correlation = np.max(correlations) if correlations else 0.0
            min_correlation = np.min(correlations) if correlations else 0.0
            
            return CorrelationMatrix(
                correlation_matrix=correlation_dict,
                average_correlation=avg_correlation,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                period=period,
                lookback_days=252  # Approximate trading days in a year
            )
            
        except Exception as e:
            logger.error("Correlation analysis failed", error=str(e))
            return None
    
    async def _calculate_optimization(
        self,
        portfolio_data: Dict[str, Any],
        returns_data: pd.Series
    ) -> Optional[OptimizationResult]:
        """Calculate portfolio optimization results."""
        # Placeholder for optimization - would implement modern portfolio theory
        try:
            holdings = portfolio_data.get('holdings', [])
            
            # Current weights
            current_weights = {
                holding['symbol']: holding.get('allocation_percentage', 0) / 100
                for holding in holdings
            }
            
            # Simplified optimization result
            return OptimizationResult(
                optimal_weights=current_weights,
                expected_return=0.08,  # 8% expected return
                expected_volatility=0.15,  # 15% expected volatility
                expected_sharpe=0.53,  # Expected Sharpe ratio
                method="mean_variance",
                objective="max_sharpe"
            )
            
        except Exception as e:
            logger.error("Optimization calculation failed", error=str(e))
            return None
    
    async def _calculate_scenario_analysis(
        self,
        portfolio_data: Dict[str, Any],
        returns_data: pd.Series
    ) -> Optional[ScenarioAnalysis]:
        """Calculate scenario analysis results."""
        # Placeholder for scenario analysis
        try:
            # Base case performance
            base_performance = await self.performance_calculator.calculate_portfolio_performance(
                returns_data
            )
            
            return ScenarioAnalysis(
                base_case=base_performance,
                stress_scenarios={},
                monte_carlo_results={},
                scenario_probabilities={}
            )
            
        except Exception as e:
            logger.error("Scenario analysis failed", error=str(e))
            return None
    
    def _calculate_allocations(self, portfolio_data: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Calculate sector and asset class allocations."""
        holdings = portfolio_data.get('holdings', [])
        
        sector_allocation = {}
        asset_class_allocation = {}
        
        for holding in holdings:
            weight = holding.get('allocation_percentage', 0) / 100
            
            # Sector allocation
            sector = holding.get('sector', 'Unknown')
            if sector not in sector_allocation:
                sector_allocation[sector] = 0
            sector_allocation[sector] += weight
            
            # Asset class allocation
            asset_class = holding.get('asset_class', 'Unknown')
            if asset_class not in asset_class_allocation:
                asset_class_allocation[asset_class] = 0
            asset_class_allocation[asset_class] += weight
        
        return sector_allocation, asset_class_allocation
    
    async def _get_cached_analytics(self, cache_key: str) -> Optional[PortfolioAnalytics]:
        """Get cached analytics result."""
        try:
            if not self.redis_client:
                return None
            
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return PortfolioAnalytics(**data)
            
            return None
            
        except Exception as e:
            logger.warning("Cache retrieval failed", cache_key=cache_key, error=str(e))
            return None
    
    async def _cache_analytics(self, cache_key: str, analytics: PortfolioAnalytics):
        """Cache analytics result."""
        try:
            if not self.redis_client:
                return
            
            # Convert to JSON-serializable format
            data = analytics.dict()
            
            await self.redis_client.setex(
                cache_key,
                self._cache_ttl,
                json.dumps(data, default=str)
            )
            
        except Exception as e:
            logger.warning("Cache storage failed", cache_key=cache_key, error=str(e))
    
    async def cleanup(self):
        """Cleanup service resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("Analytics service cleanup completed")
            
        except Exception as e:
            logger.error("Analytics service cleanup failed", error=str(e)) 