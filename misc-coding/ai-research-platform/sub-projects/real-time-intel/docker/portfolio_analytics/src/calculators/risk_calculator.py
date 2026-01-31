"""Risk calculation engine for portfolio analytics."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from scipy import stats
from sklearn.decomposition import PCA
import asyncio
import structlog

from ..models.analytics_models import RiskMetrics, TimePeriod
from ..config import config

logger = structlog.get_logger(__name__)


class RiskCalculator:
    """Calculator for portfolio and asset risk metrics."""
    
    def __init__(self):
        self.trading_days_per_year = config.analytics.trading_days_per_year
        self.default_confidence_levels = [0.95, 0.99]
    
    async def calculate_portfolio_risk(
        self,
        returns: pd.Series,
        weights: Optional[pd.Series] = None,
        confidence_levels: List[float] = None,
        period: TimePeriod = TimePeriod.ONE_YEAR
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for a portfolio."""
        try:
            if returns.empty:
                raise ValueError("Returns series is empty")
            
            if confidence_levels is None:
                confidence_levels = self.default_confidence_levels
            
            # Value at Risk calculations
            var_metrics = {}
            cvar_metrics = {}
            
            for confidence in confidence_levels:
                var = self._calculate_var(returns, confidence)
                cvar = self._calculate_cvar(returns, confidence)
                
                var_metrics[f"var_{int(confidence*100)}"] = var
                cvar_metrics[f"cvar_{int(confidence*100)}"] = cvar
            
            # Volatility measures
            historical_volatility = self._calculate_historical_volatility(returns)
            realized_volatility = self._calculate_realized_volatility(returns)
            
            # Correlation and diversification
            portfolio_correlation = 0.0  # Will be calculated if weights provided
            diversification_ratio = 1.0  # Will be calculated if weights provided
            
            if weights is not None:
                portfolio_correlation = self._calculate_portfolio_correlation(returns, weights)
                diversification_ratio = self._calculate_diversification_ratio(returns, weights)
            
            # Distribution characteristics
            skewness = float(returns.skew()) if len(returns) > 0 else 0.0
            kurtosis = float(returns.kurtosis()) if len(returns) > 0 else 0.0
            
            # Stress test scenarios
            stress_scenarios = await self._calculate_stress_scenarios(returns)
            
            return RiskMetrics(
                var_95=var_metrics.get("var_95", 0.0),
                var_99=var_metrics.get("var_99", 0.0),
                cvar_95=cvar_metrics.get("cvar_95", 0.0),
                cvar_99=cvar_metrics.get("cvar_99", 0.0),
                historical_volatility=historical_volatility,
                realized_volatility=realized_volatility,
                portfolio_correlation=portfolio_correlation,
                diversification_ratio=diversification_ratio,
                skewness=skewness,
                kurtosis=kurtosis,
                stress_test_scenarios=stress_scenarios,
                period=period,
                confidence_level=confidence_levels[0] if confidence_levels else 0.95
            )
            
        except Exception as e:
            logger.error(
                "Risk calculation error",
                error=str(e),
                returns_length=len(returns) if returns is not None else 0
            )
            raise
    
    def _calculate_var(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk using historical simulation."""
        if returns.empty:
            return 0.0
        
        try:
            # Calculate VaR as the percentile of returns
            var_percentile = 1 - confidence_level
            var = np.percentile(returns, var_percentile * 100)
            
            # Convert to positive number (loss)
            return float(-var)
            
        except Exception as e:
            logger.warning("VaR calculation error", error=str(e))
            return 0.0
    
    def _calculate_cvar(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        if returns.empty:
            return 0.0
        
        try:
            # Calculate VaR first
            var = self._calculate_var(returns, confidence_level)
            
            # CVaR is the mean of returns below VaR threshold
            var_threshold = -var  # Convert back to negative for comparison
            tail_returns = returns[returns <= var_threshold]
            
            if tail_returns.empty:
                return var
            
            cvar = tail_returns.mean()
            
            # Convert to positive number (loss)
            return float(-cvar)
            
        except Exception as e:
            logger.warning("CVaR calculation error", error=str(e))
            return 0.0
    
    def _calculate_historical_volatility(self, returns: pd.Series) -> float:
        """Calculate historical volatility (annualized standard deviation)."""
        if returns.empty or len(returns) < 2:
            return 0.0
        
        daily_vol = returns.std()
        return float(daily_vol * np.sqrt(self.trading_days_per_year))
    
    def _calculate_realized_volatility(self, returns: pd.Series, window: int = 30) -> float:
        """Calculate realized volatility using rolling window."""
        if returns.empty or len(returns) < window:
            return self._calculate_historical_volatility(returns)
        
        try:
            # Calculate rolling volatility
            rolling_vol = returns.rolling(window).std() * np.sqrt(self.trading_days_per_year)
            
            # Return the most recent realized volatility
            return float(rolling_vol.iloc[-1]) if not rolling_vol.empty else 0.0
            
        except Exception as e:
            logger.warning("Realized volatility calculation error", error=str(e))
            return self._calculate_historical_volatility(returns)
    
    def _calculate_portfolio_correlation(self, returns: pd.DataFrame, weights: pd.Series) -> float:
        """Calculate average correlation within portfolio."""
        if returns.empty or len(returns.columns) < 2:
            return 0.0
        
        try:
            # Calculate correlation matrix
            corr_matrix = returns.corr()
            
            # Calculate weighted average correlation
            total_weight_product = 0.0
            weighted_correlation_sum = 0.0
            
            for i, asset1 in enumerate(corr_matrix.index):
                for j, asset2 in enumerate(corr_matrix.columns):
                    if i != j:  # Exclude diagonal (self-correlation)
                        weight_product = weights.get(asset1, 0) * weights.get(asset2, 0)
                        correlation = corr_matrix.loc[asset1, asset2]
                        
                        if not np.isnan(correlation):
                            weighted_correlation_sum += weight_product * correlation
                            total_weight_product += weight_product
            
            if total_weight_product == 0:
                return 0.0
            
            return float(weighted_correlation_sum / total_weight_product)
            
        except Exception as e:
            logger.warning("Portfolio correlation calculation error", error=str(e))
            return 0.0
    
    def _calculate_diversification_ratio(self, returns: pd.DataFrame, weights: pd.Series) -> float:
        """Calculate diversification ratio."""
        if returns.empty or len(returns.columns) < 2:
            return 1.0
        
        try:
            # Calculate individual asset volatilities
            individual_vols = returns.std() * np.sqrt(self.trading_days_per_year)
            
            # Calculate weighted average of individual volatilities
            weighted_avg_vol = sum(weights.get(asset, 0) * individual_vols.get(asset, 0) 
                                 for asset in individual_vols.index)
            
            # Calculate portfolio volatility
            portfolio_returns = (returns * weights).sum(axis=1)
            portfolio_vol = self._calculate_historical_volatility(portfolio_returns)
            
            if portfolio_vol == 0:
                return 1.0
            
            # Diversification ratio = weighted avg vol / portfolio vol
            return float(weighted_avg_vol / portfolio_vol)
            
        except Exception as e:
            logger.warning("Diversification ratio calculation error", error=str(e))
            return 1.0
    
    async def _calculate_stress_scenarios(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate portfolio performance under stress scenarios."""
        scenarios = {}
        
        if returns.empty:
            return scenarios
        
        try:
            # Market crash scenario (-20% market shock)
            market_crash_return = -0.20
            scenarios["market_crash"] = float(market_crash_return)
            
            # High volatility scenario (3x normal volatility)
            if len(returns) > 1:
                normal_vol = returns.std()
                high_vol_return = np.random.normal(returns.mean(), 3 * normal_vol)
                scenarios["high_volatility"] = float(high_vol_return)
            
            # Interest rate shock (simulate impact of rate changes)
            # Simplified assumption: -10% for rate-sensitive assets
            scenarios["interest_rate_shock"] = -0.10
            
            # Liquidity crisis (wider spreads, forced selling)
            scenarios["liquidity_crisis"] = -0.15
            
            # Tail risk scenario (5th percentile historical return)
            if len(returns) > 20:
                tail_risk = np.percentile(returns, 5)
                scenarios["tail_risk"] = float(tail_risk)
            
            return scenarios
            
        except Exception as e:
            logger.warning("Stress scenario calculation error", error=str(e))
            return scenarios
    
    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> Optional[float]:
        """Calculate beta of an asset vs market."""
        if asset_returns.empty or market_returns.empty:
            return None
        
        try:
            # Align the series
            aligned_asset, aligned_market = asset_returns.align(market_returns, join='inner')
            
            if len(aligned_asset) < 2:
                return None
            
            # Calculate beta using covariance
            covariance = np.cov(aligned_asset, aligned_market)[0, 1]
            market_variance = np.var(aligned_market)
            
            if market_variance == 0:
                return None
            
            beta = covariance / market_variance
            return float(beta)
            
        except Exception as e:
            logger.warning("Beta calculation error", error=str(e))
            return None
    
    def calculate_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix for multiple assets."""
        if returns.empty:
            return pd.DataFrame()
        
        try:
            return returns.corr()
        except Exception as e:
            logger.error("Correlation matrix calculation error", error=str(e))
            return pd.DataFrame()
    
    def calculate_rolling_var(
        self,
        returns: pd.Series,
        window: int = 30,
        confidence_level: float = 0.95
    ) -> pd.Series:
        """Calculate rolling Value at Risk."""
        if returns.empty or len(returns) < window:
            return pd.Series()
        
        try:
            var_percentile = 1 - confidence_level
            
            rolling_var = returns.rolling(window).quantile(var_percentile)
            
            # Convert to positive numbers (losses)
            return -rolling_var
            
        except Exception as e:
            logger.error("Rolling VaR calculation error", error=str(e))
            return pd.Series()
    
    def detect_regime_changes(self, returns: pd.Series, window: int = 60) -> List[datetime]:
        """Detect regime changes in volatility using rolling statistics."""
        if returns.empty or len(returns) < window * 2:
            return []
        
        try:
            # Calculate rolling volatility
            rolling_vol = returns.rolling(window).std()
            
            # Calculate rolling mean and std of volatility
            vol_mean = rolling_vol.rolling(window).mean()
            vol_std = rolling_vol.rolling(window).std()
            
            # Detect regime changes (volatility > mean + 2*std)
            regime_changes = []
            
            for i in range(len(rolling_vol)):
                if (rolling_vol.iloc[i] > vol_mean.iloc[i] + 2 * vol_std.iloc[i] and
                    not pd.isna(rolling_vol.iloc[i])):
                    regime_changes.append(rolling_vol.index[i])
            
            return regime_changes
            
        except Exception as e:
            logger.error("Regime change detection error", error=str(e))
            return []
    
    async def calculate_factor_risk(
        self,
        returns: pd.DataFrame,
        factor_returns: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate factor-based risk decomposition."""
        if returns.empty or factor_returns.empty:
            return {}
        
        try:
            # Align data
            aligned_returns, aligned_factors = returns.align(factor_returns, join='inner', axis=0)
            
            if aligned_returns.empty or aligned_factors.empty:
                return {}
            
            factor_risk = {}
            
            for asset in aligned_returns.columns:
                asset_returns = aligned_returns[asset].dropna()
                
                if len(asset_returns) < len(aligned_factors.columns) + 10:
                    continue
                
                # Run factor regression
                try:
                    # Align asset returns with factors
                    common_dates = asset_returns.index.intersection(aligned_factors.index)
                    
                    if len(common_dates) < 10:
                        continue
                    
                    y = asset_returns.loc[common_dates]
                    X = aligned_factors.loc[common_dates]
                    
                    # Add constant term
                    X = X.assign(const=1.0)
                    
                    # Calculate factor loadings using least squares
                    factor_loadings = np.linalg.lstsq(X.values, y.values, rcond=None)[0]
                    
                    # Calculate factor risk contribution
                    factor_cov = X.iloc[:, :-1].cov().values  # Exclude constant
                    factor_loadings_no_const = factor_loadings[:-1]  # Exclude constant
                    
                    factor_variance = np.dot(factor_loadings_no_const, 
                                           np.dot(factor_cov, factor_loadings_no_const))
                    
                    specific_variance = np.var(y - np.dot(X.values, factor_loadings))
                    
                    factor_risk[asset] = {
                        'factor_loadings': dict(zip(aligned_factors.columns, factor_loadings_no_const)),
                        'factor_variance': float(factor_variance),
                        'specific_variance': float(specific_variance),
                        'total_variance': float(factor_variance + specific_variance)
                    }
                    
                except Exception as e:
                    logger.warning(f"Factor risk calculation error for {asset}", error=str(e))
                    continue
            
            return factor_risk
            
        except Exception as e:
            logger.error("Factor risk calculation error", error=str(e))
            return {}
    
    def calculate_maximum_drawdown_duration(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate detailed drawdown analysis."""
        if returns.empty:
            return {}
        
        try:
            # Calculate cumulative returns
            cumulative = (1 + returns).cumprod()
            
            # Calculate running maximum
            running_max = cumulative.expanding().max()
            
            # Calculate drawdowns
            drawdowns = (cumulative - running_max) / running_max
            
            # Find drawdown periods
            drawdown_periods = []
            in_drawdown = False
            start_date = None
            
            for date, dd in drawdowns.items():
                if dd < 0 and not in_drawdown:
                    # Start of drawdown
                    in_drawdown = True
                    start_date = date
                elif dd >= 0 and in_drawdown:
                    # End of drawdown
                    in_drawdown = False
                    if start_date:
                        duration = (date - start_date).days
                        max_dd_in_period = drawdowns[start_date:date].min()
                        
                        drawdown_periods.append({
                            'start_date': start_date,
                            'end_date': date,
                            'duration_days': duration,
                            'max_drawdown': float(max_dd_in_period)
                        })
            
            # Handle case where we're still in drawdown
            if in_drawdown and start_date:
                duration = (drawdowns.index[-1] - start_date).days
                max_dd_in_period = drawdowns[start_date:].min()
                
                drawdown_periods.append({
                    'start_date': start_date,
                    'end_date': drawdowns.index[-1],
                    'duration_days': duration,
                    'max_drawdown': float(max_dd_in_period),
                    'ongoing': True
                })
            
            # Summary statistics
            if drawdown_periods:
                avg_duration = np.mean([dd['duration_days'] for dd in drawdown_periods])
                max_duration = max([dd['duration_days'] for dd in drawdown_periods])
                avg_drawdown = np.mean([dd['max_drawdown'] for dd in drawdown_periods])
            else:
                avg_duration = 0
                max_duration = 0
                avg_drawdown = 0
            
            return {
                'drawdown_periods': drawdown_periods,
                'total_drawdown_periods': len(drawdown_periods),
                'average_duration_days': avg_duration,
                'maximum_duration_days': max_duration,
                'average_drawdown': avg_drawdown,
                'maximum_drawdown': float(drawdowns.min()),
                'current_drawdown': float(drawdowns.iloc[-1]),
                'recovery_factor': len([dd for dd in drawdown_periods if not dd.get('ongoing', False)]) / max(len(drawdown_periods), 1)
            }
            
        except Exception as e:
            logger.error("Drawdown analysis error", error=str(e))
            return {} 