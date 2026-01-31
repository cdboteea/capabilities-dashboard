"""API tests for Portfolio Analytics service."""

import pytest
import asyncio
from datetime import date, timedelta
from httpx import AsyncClient
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

from ..src.main import app
from ..src.models.analytics_models import (
    AnalyticsRequest, TimePeriod, PerformanceComparisonRequest
)


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing."""
    return {
        'portfolio_id': 'test-portfolio-1',
        'name': 'Test Portfolio',
        'total_value': 100000.0,
        'holdings': [
            {
                'symbol': 'AAPL',
                'quantity': 100,
                'current_price': 150.0,
                'market_value': 15000.0,
                'sector': 'Technology',
                'asset_class': 'equity',
                'allocation_percentage': 15.0
            },
            {
                'symbol': 'GOOGL',
                'quantity': 50,
                'current_price': 2800.0,
                'market_value': 140000.0,
                'sector': 'Technology',
                'asset_class': 'equity',
                'allocation_percentage': 14.0
            }
        ]
    }


@pytest.fixture
def sample_returns_data():
    """Sample returns data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    returns = pd.Series(
        data=np.random.normal(0.001, 0.02, len(dates)),
        index=dates
    )
    return returns


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    async def test_health_check_success(self, client):
        """Test successful health check."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "portfolio-analytics"


class TestAnalyticsEndpoints:
    """Test analytics calculation endpoints."""
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_calculate_analytics_success(self, mock_calculate, client):
        """Test successful analytics calculation."""
        # Mock the analytics service response
        mock_response = Mock()
        mock_response.success = True
        mock_response.calculation_time_ms = 1500
        mock_response.analytics = Mock()
        mock_response.analytics.portfolio_id = "test-portfolio-1"
        
        mock_calculate.return_value = mock_response
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "period": "1y",
            "include_optimization": False,
            "include_scenarios": False
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "calculation_time_ms" in data
    
    async def test_calculate_analytics_invalid_portfolio(self, client):
        """Test analytics calculation with invalid portfolio."""
        request_data = {
            "portfolio_id": "nonexistent-portfolio",
            "period": "1y"
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        # Should handle gracefully - either 404 or success=false
        assert response.status_code in [200, 404, 500]
    
    async def test_calculate_analytics_invalid_request(self, client):
        """Test analytics calculation with invalid request."""
        request_data = {
            "portfolio_id": "",  # Empty portfolio ID
            "period": "invalid_period"
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_risk_analysis(self, mock_calculate, client):
        """Test risk analysis endpoint."""
        mock_response = Mock()
        mock_response.success = True
        mock_response.calculation_time_ms = 800
        mock_response.analytics = Mock()
        
        mock_calculate.return_value = mock_response
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "confidence_levels": [0.95, 0.99],
            "stress_scenarios": ["market_crash"],
            "monte_carlo_runs": 1000
        }
        
        response = await client.post("/analytics/risk", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_portfolio_optimization(self, mock_calculate, client):
        """Test portfolio optimization endpoint."""
        mock_response = Mock()
        mock_response.success = True
        mock_response.calculation_time_ms = 2000
        mock_response.analytics = Mock()
        
        mock_calculate.return_value = mock_response
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "objective": "max_sharpe",
            "constraints": {"max_weight": 0.3},
            "rebalance_frequency": "monthly"
        }
        
        response = await client.post("/analytics/optimize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_correlation_analysis(self, mock_calculate, client):
        """Test correlation analysis endpoint."""
        mock_response = Mock()
        mock_response.success = True
        mock_response.calculation_time_ms = 1200
        mock_response.analytics = Mock()
        
        mock_calculate.return_value = mock_response
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "lookback_periods": [30, 90, 252],
            "rolling_window": 30
        }
        
        response = await client.post("/analytics/correlation", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestComparisonEndpoints:
    """Test portfolio comparison endpoints."""
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_compare_portfolios(self, mock_calculate, client):
        """Test portfolio comparison."""
        # Mock analytics for multiple portfolios
        mock_analytics_1 = Mock()
        mock_analytics_1.performance = Mock()
        mock_analytics_1.performance.sharpe_ratio = 1.2
        mock_analytics_1.performance.annualized_return = 0.08
        mock_analytics_1.performance.volatility = 0.15
        mock_analytics_1.performance.max_drawdown = -0.05
        
        mock_analytics_2 = Mock()
        mock_analytics_2.performance = Mock()
        mock_analytics_2.performance.sharpe_ratio = 0.9
        mock_analytics_2.performance.annualized_return = 0.06
        mock_analytics_2.performance.volatility = 0.12
        mock_analytics_2.performance.max_drawdown = -0.03
        
        def mock_calculate_side_effect(request):
            mock_response = Mock()
            mock_response.success = True
            
            if request.portfolio_id == "portfolio-1":
                mock_response.analytics = mock_analytics_1
            else:
                mock_response.analytics = mock_analytics_2
            
            return mock_response
        
        mock_calculate.side_effect = mock_calculate_side_effect
        
        request_data = {
            "portfolio_ids": ["portfolio-1", "portfolio-2"],
            "period": "1y",
            "metrics": ["sharpe_ratio", "annualized_return"]
        }
        
        response = await client.post("/analytics/compare", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison_results" in data
        assert "ranking" in data
        assert "summary_statistics" in data
        assert len(data["ranking"]) == 2
        
        # Check ranking order (higher Sharpe ratio should be first)
        assert data["ranking"][0]["sharpe_ratio"] > data["ranking"][1]["sharpe_ratio"]


class TestQuickEndpoints:
    """Test quick analytics endpoints."""
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_portfolio_summary(self, mock_calculate, client):
        """Test portfolio summary endpoint."""
        # Mock analytics response
        mock_analytics = Mock()
        mock_analytics.total_value = 100000.0
        mock_analytics.asset_count = 10
        mock_analytics.performance = Mock()
        mock_analytics.performance.total_return = 0.12
        mock_analytics.performance.annualized_return = 0.10
        mock_analytics.performance.volatility = 0.15
        mock_analytics.performance.sharpe_ratio = 0.67
        mock_analytics.performance.max_drawdown = -0.08
        mock_analytics.risk = Mock()
        mock_analytics.risk.var_95 = 0.05
        mock_analytics.risk.historical_volatility = 0.15
        mock_analytics.sector_allocation = {"Technology": 0.6, "Healthcare": 0.4}
        mock_analytics.asset_class_allocation = {"equity": 1.0}
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.analytics = mock_analytics
        
        mock_calculate.return_value = mock_response
        
        response = await client.get("/analytics/test-portfolio-1/summary?period=1y")
        
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio_id"] == "test-portfolio-1"
        assert "performance" in data
        assert "risk" in data
        assert "allocations" in data
        assert data["total_value"] == 100000.0
        assert data["asset_count"] == 10
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_performance_metrics_only(self, mock_calculate, client):
        """Test performance metrics endpoint."""
        mock_performance = Mock()
        mock_performance.total_return = 0.12
        mock_performance.annualized_return = 0.10
        mock_performance.volatility = 0.15
        
        mock_analytics = Mock()
        mock_analytics.performance = mock_performance
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.analytics = mock_analytics
        
        mock_calculate.return_value = mock_response
        
        response = await client.get("/analytics/test-portfolio-1/performance?period=6m")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_return" in data
        assert "annualized_return" in data
        assert "volatility" in data
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_risk_metrics_only(self, mock_calculate, client):
        """Test risk metrics endpoint."""
        mock_risk = Mock()
        mock_risk.var_95 = 0.05
        mock_risk.var_99 = 0.08
        mock_risk.historical_volatility = 0.15
        
        mock_analytics = Mock()
        mock_analytics.risk = mock_risk
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.analytics = mock_analytics
        
        mock_calculate.return_value = mock_response
        
        response = await client.get("/analytics/test-portfolio-1/risk?period=3m")
        
        assert response.status_code == 200
        data = response.json()
        assert "var_95" in data
        assert "var_99" in data
        assert "historical_volatility" in data


class TestHistoryEndpoints:
    """Test analytics history endpoints."""
    
    @patch('..src.utils.database.DatabaseManager.get_analytics_history')
    async def test_analytics_history(self, mock_get_history, client):
        """Test analytics history endpoint."""
        # Mock historical data
        mock_history_data = [
            {
                'analysis_date': date.today() - timedelta(days=1),
                'analytics_data': {
                    'portfolio_id': 'test-portfolio-1',
                    'total_value': 100000.0,
                    'asset_count': 10,
                    'performance': {
                        'total_return': 0.12,
                        'annualized_return': 0.10,
                        'volatility': 0.15,
                        'sharpe_ratio': 0.67,
                        'max_drawdown': -0.08,
                        'period': '1y',
                        'start_date': '2023-01-01',
                        'end_date': '2023-12-31'
                    },
                    'risk': {
                        'var_95': 0.05,
                        'var_99': 0.08,
                        'historical_volatility': 0.15,
                        'period': '1y'
                    },
                    'attribution': {
                        'allocation_effect': 0.02,
                        'selection_effect': 0.01,
                        'interaction_effect': 0.005,
                        'period': '1y',
                        'benchmark_return': 0.08,
                        'active_return': 0.02
                    },
                    'sector_allocation': {'Technology': 0.6},
                    'asset_class_allocation': {'equity': 1.0},
                    'analysis_date': date.today().isoformat()
                }
            }
        ]
        
        mock_get_history.return_value = mock_history_data
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date": date.today().isoformat(),
            "frequency": "daily"
        }
        
        response = await client.post("/analytics/history", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio_id"] == "test-portfolio-1"
        assert "history" in data
        assert "summary" in data
        assert len(data["history"]) > 0


class TestAdminEndpoints:
    """Test administrative endpoints."""
    
    @patch('..src.utils.database.DatabaseManager.fetch_all')
    async def test_list_portfolios(self, mock_fetch_all, client):
        """Test portfolio listing endpoint."""
        mock_portfolios = [
            {
                'portfolio_id': 'portfolio-1',
                'name': 'Portfolio 1',
                'total_value': 100000.0,
                'created_at': date.today(),
                'updated_at': date.today()
            },
            {
                'portfolio_id': 'portfolio-2',
                'name': 'Portfolio 2',
                'total_value': 150000.0,
                'created_at': date.today(),
                'updated_at': date.today()
            }
        ]
        
        mock_fetch_all.return_value = mock_portfolios
        
        response = await client.get("/admin/portfolios")
        
        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["portfolios"]) == 2
    
    @patch('..src.services.analytics_service.AnalyticsService.redis_client')
    async def test_clear_cache(self, mock_redis, client):
        """Test cache clearing endpoint."""
        mock_redis.keys.return_value = ["analytics:test-portfolio-1:1y"]
        mock_redis.delete.return_value = 1
        
        response = await client.delete("/admin/cache/test-portfolio-1")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "timestamp" in data
        assert "test-portfolio-1" in data["message"]


class TestErrorHandling:
    """Test error handling scenarios."""
    
    async def test_invalid_portfolio_id_format(self, client):
        """Test handling of invalid portfolio ID format."""
        request_data = {
            "portfolio_id": "",  # Empty string
            "period": "1y"
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    async def test_invalid_period_format(self, client):
        """Test handling of invalid period format."""
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "period": "invalid"
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    async def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        request_data = {
            "period": "1y"
            # Missing portfolio_id
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('..src.services.analytics_service.AnalyticsService.calculate_portfolio_analytics')
    async def test_service_error_handling(self, mock_calculate, client):
        """Test handling of service errors."""
        mock_calculate.side_effect = Exception("Database connection failed")
        
        request_data = {
            "portfolio_id": "test-portfolio-1",
            "period": "1y"
        }
        
        response = await client.post("/analytics/calculate", json=request_data)
        
        assert response.status_code == 200  # Should return with success=false
        data = response.json()
        assert data["success"] is False
        assert "error_message" in data


if __name__ == "__main__":
    pytest.main([__file__]) 