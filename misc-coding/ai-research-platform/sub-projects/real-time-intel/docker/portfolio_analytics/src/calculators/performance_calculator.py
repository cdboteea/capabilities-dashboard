"""Performance calculation engine for portfolio analytics."""

import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from decimal import Decimal
import structlog

from ..models.analytics_models import (
    PerformanceMetrics, TimePeriod, AssetAnalytics
)
from ..config import config

logger = structlog.get_logger(__name__)


class PerformanceCalculator:
    """Calculator for portfolio and asset performance metrics."""
    
    def __init__(self):
        self.trading_days_per_year = config.analytics.trading_days_per_year
        self.risk_free_rate = config.analytics.risk_free_rate
    
    async def calculate_portfolio_performance(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        period: TimePeriod = TimePeriod.ONE_YEAR
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a portfolio."""
        try:
            if returns.empty:
                raise ValueError("Returns series is empty")
            
            # Basic return calculations
            total_return = self._calculate_total_return(returns)
            annualized_return = self._calculate_annualized_return(returns)
            cumulative_return = self._calculate_cumulative_return(returns)
            
            # Volatility calculations
            volatility = self._calculate_volatility(returns)
            downside_deviation = self._calculate_downside_deviation(returns)
            
            # Risk-adjusted returns
            sharpe_ratio = self._calculate_sharpe_ratio(returns, annualized_return, volatility)
            sortino_ratio = self._calculate_sortino_ratio(returns, annualized_return, downside_deviation)
            
            # Drawdown calculations
            max_drawdown, current_drawdown, drawdown_duration = self._calculate_drawdowns(returns)
            
            # Calmar ratio
            calmar_ratio = self._calculate_calmar_ratio(annualized_return, max_drawdown)
            
            # Win rate and profit factor
            win_rate = self._calculate_win_rate(returns)
            profit_factor = self._calculate_profit_factor(returns)
            
            # Benchmark comparison (if benchmark provided)
            alpha, beta, information_ratio, tracking_error = None, None, None, None
            if benchmark_returns is not None and not benchmark_returns.empty:
                alpha, beta = self._calculate_alpha_beta(returns, benchmark_returns)
                information_ratio = self._calculate_information_ratio(returns, benchmark_returns)
                tracking_error = self._calculate_tracking_error(returns, benchmark_returns)
            
            # Period information
            start_date = returns.index[0].date() if not returns.empty else date.today()
            end_date = returns.index[-1].date() if not returns.empty else date.today()
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                cumulative_return=cumulative_return,
                volatility=volatility,
                downside_deviation=downside_deviation,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                drawdown_duration=drawdown_duration,
                win_rate=win_rate,
                profit_factor=profit_factor,
                alpha=alpha,
                beta=beta,
                information_ratio=information_ratio,
                tracking_error=tracking_error,
                period=period,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(
                "Performance calculation error",
                error=str(e),
                returns_length=len(returns) if returns is not None else 0
            )
            raise
    
    def _calculate_total_return(self, returns: pd.Series) -> float:
        """Calculate total return over the period."""
        if returns.empty:
            return 0.0
        return float((1 + returns).prod() - 1)
    
    def _calculate_annualized_return(self, returns: pd.Series) -> float:
        """Calculate annualized return."""
        if returns.empty:
            return 0.0
        
        total_return = self._calculate_total_return(returns)
        days = len(returns)
        
        if days == 0:
            return 0.0
        
        # Annualize based on trading days
        years = days / self.trading_days_per_year
        return float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
    
    def _calculate_cumulative_return(self, returns: pd.Series) -> float:
        """Calculate cumulative return."""
        if returns.empty:
            return 0.0
        return float((1 + returns).cumprod().iloc[-1] - 1)
    
    def _calculate_volatility(self, returns: pd.Series) -> float:
        """Calculate annualized volatility."""
        if returns.empty or len(returns) < 2:
            return 0.0
        
        daily_vol = returns.std()
        return float(daily_vol * np.sqrt(self.trading_days_per_year))
    
    def _calculate_downside_deviation(self, returns: pd.Series, target_return: float = 0.0) -> float:
        """Calculate downside deviation."""
        if returns.empty:
            return 0.0
        
        downside_returns = returns[returns < target_return]
        if downside_returns.empty:
            return 0.0
        
        downside_variance = ((downside_returns - target_return) ** 2).mean()
        return float(np.sqrt(downside_variance) * np.sqrt(self.trading_days_per_year))
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, annualized_return: float, volatility: float) -> float:
        """Calculate Sharpe ratio."""
        if volatility == 0:
            return 0.0
        
        excess_return = annualized_return - self.risk_free_rate
        return float(excess_return / volatility)
    
    def _calculate_sortino_ratio(self, returns: pd.Series, annualized_return: float, downside_deviation: float) -> float:
        """Calculate Sortino ratio."""
        if downside_deviation == 0:
            return 0.0
        
        excess_return = annualized_return - self.risk_free_rate
        return float(excess_return / downside_deviation)
    
    def _calculate_drawdowns(self, returns: pd.Series) -> Tuple[float, float, int]:
        """Calculate maximum drawdown, current drawdown, and duration."""
        if returns.empty:
            return 0.0, 0.0, 0
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.expanding().max()
        
        # Calculate drawdowns
        drawdowns = (cumulative - running_max) / running_max
        
        # Maximum drawdown
        max_drawdown = float(drawdowns.min())
        
        # Current drawdown
        current_drawdown = float(drawdowns.iloc[-1])
        
        # Drawdown duration (days since last peak)
        last_peak_idx = (cumulative == running_max.iloc[-1]).last_valid_index()
        if last_peak_idx is not None:
            drawdown_duration = len(cumulative) - cumulative.index.get_loc(last_peak_idx) - 1
        else:
            drawdown_duration = 0
        
        return max_drawdown, current_drawdown, drawdown_duration
    
    def _calculate_calmar_ratio(self, annualized_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown == 0:
            return 0.0
        
        return float(annualized_return / abs(max_drawdown))
    
    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate (percentage of positive periods)."""
        if returns.empty:
            return 0.0
        
        positive_returns = (returns > 0).sum()
        return float(positive_returns / len(returns))
    
    def _calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor (ratio of gross profit to gross loss)."""
        if returns.empty:
            return 0.0
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        gross_profit = positive_returns.sum() if not positive_returns.empty else 0
        gross_loss = abs(negative_returns.sum()) if not negative_returns.empty else 0
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return float(gross_profit / gross_loss)
    
    def _calculate_alpha_beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> Tuple[Optional[float], Optional[float]]:
        """Calculate alpha and beta vs benchmark."""
        if returns.empty or benchmark_returns.empty:
            return None, None
        
        # Align the series
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) < 2:
            return None, None
        
        try:
            # Calculate beta using covariance
            covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
            benchmark_variance = np.var(aligned_benchmark)
            
            if benchmark_variance == 0:
                return None, None
            
            beta = covariance / benchmark_variance
            
            # Calculate alpha
            portfolio_return = aligned_returns.mean() * self.trading_days_per_year
            benchmark_return = aligned_benchmark.mean() * self.trading_days_per_year
            
            alpha = portfolio_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))
            
            return float(alpha), float(beta)
            
        except Exception as e:
            logger.warning("Alpha/Beta calculation error", error=str(e))
            return None, None
    
    def _calculate_information_ratio(self, returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
        """Calculate information ratio."""
        if returns.empty or benchmark_returns.empty:
            return None
        
        # Align the series
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) < 2:
            return None
        
        try:
            # Calculate active returns
            active_returns = aligned_returns - aligned_benchmark
            
            # Information ratio = mean active return / tracking error
            mean_active_return = active_returns.mean() * self.trading_days_per_year
            tracking_error = active_returns.std() * np.sqrt(self.trading_days_per_year)
            
            if tracking_error == 0:
                return None
            
            return float(mean_active_return / tracking_error)
            
        except Exception as e:
            logger.warning("Information ratio calculation error", error=str(e))
            return None
    
    def _calculate_tracking_error(self, returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
        """Calculate tracking error vs benchmark."""
        if returns.empty or benchmark_returns.empty:
            return None
        
        # Align the series
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) < 2:
            return None
        
        try:
            # Calculate active returns
            active_returns = aligned_returns - aligned_benchmark
            
            # Tracking error = standard deviation of active returns
            tracking_error = active_returns.std() * np.sqrt(self.trading_days_per_year)
            
            return float(tracking_error)
            
        except Exception as e:
            logger.warning("Tracking error calculation error", error=str(e))
            return None
    
    async def calculate_rolling_metrics(
        self,
        returns: pd.Series,
        window: int = 30,
        metrics: List[str] = None
    ) -> pd.DataFrame:
        """Calculate rolling performance metrics."""
        if metrics is None:
            metrics = ['volatility', 'sharpe_ratio', 'max_drawdown']
        
        if returns.empty or len(returns) < window:
            return pd.DataFrame()
        
        try:
            rolling_metrics = {}
            
            for metric in metrics:
                if metric == 'volatility':
                    rolling_metrics[metric] = returns.rolling(window).std() * np.sqrt(self.trading_days_per_year)
                elif metric == 'sharpe_ratio':
                    rolling_returns = returns.rolling(window).mean() * self.trading_days_per_year
                    rolling_vol = returns.rolling(window).std() * np.sqrt(self.trading_days_per_year)
                    rolling_metrics[metric] = (rolling_returns - self.risk_free_rate) / rolling_vol
                elif metric == 'max_drawdown':
                    rolling_metrics[metric] = returns.rolling(window).apply(
                        lambda x: self._calculate_drawdowns(x)[0]
                    )
            
            return pd.DataFrame(rolling_metrics)
            
        except Exception as e:
            logger.error("Rolling metrics calculation error", error=str(e))
            return pd.DataFrame()
    
    def calculate_period_returns(
        self,
        prices: pd.Series,
        period: TimePeriod
    ) -> pd.Series:
        """Calculate returns for specified period."""
        if prices.empty:
            return pd.Series()
        
        try:
            # Determine the lookback period
            end_date = prices.index[-1]
            
            if period == TimePeriod.ONE_DAY:
                start_date = end_date - timedelta(days=1)
            elif period == TimePeriod.ONE_WEEK:
                start_date = end_date - timedelta(weeks=1)
            elif period == TimePeriod.ONE_MONTH:
                start_date = end_date - timedelta(days=30)
            elif period == TimePeriod.THREE_MONTHS:
                start_date = end_date - timedelta(days=90)
            elif period == TimePeriod.SIX_MONTHS:
                start_date = end_date - timedelta(days=180)
            elif period == TimePeriod.ONE_YEAR:
                start_date = end_date - timedelta(days=365)
            elif period == TimePeriod.TWO_YEARS:
                start_date = end_date - timedelta(days=730)
            elif period == TimePeriod.FIVE_YEARS:
                start_date = end_date - timedelta(days=1825)
            else:  # MAX
                start_date = prices.index[0]
            
            # Filter prices for the period
            period_prices = prices[prices.index >= start_date]
            
            if len(period_prices) < 2:
                return pd.Series()
            
            # Calculate returns
            returns = period_prices.pct_change().dropna()
            
            return returns
            
        except Exception as e:
            logger.error("Period returns calculation error", error=str(e), period=period.value)
            return pd.Series()
    
    async def batch_calculate_performance(
        self,
        assets_data: Dict[str, pd.Series],
        benchmark_data: Optional[pd.Series] = None,
        period: TimePeriod = TimePeriod.ONE_YEAR
    ) -> Dict[str, PerformanceMetrics]:
        """Calculate performance metrics for multiple assets in batch."""
        results = {}
        
        tasks = []
        for symbol, returns in assets_data.items():
            task = self.calculate_portfolio_performance(returns, benchmark_data, period)
            tasks.append((symbol, task))
        
        # Execute calculations concurrently
        for symbol, task in tasks:
            try:
                results[symbol] = await task
            except Exception as e:
                logger.error("Batch performance calculation error", symbol=symbol, error=str(e))
                continue
        
        return results 