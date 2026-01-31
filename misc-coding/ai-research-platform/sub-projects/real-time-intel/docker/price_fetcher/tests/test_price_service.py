"""Tests for Price Fetcher Service."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.services.price_service import PriceService
from src.models.price_models import PriceData, DataSource, PriceQuality, MarketStatus


class TestPriceService:
    """Test cases for PriceService."""
    
    @pytest.fixture
    async def price_service(self):
        """Create a price service instance for testing."""
        service = PriceService()
        
        # Mock the cache and sources
        service.cache = Mock()
        service.cache.connect = AsyncMock()
        service.cache.disconnect = AsyncMock()
        service.cache.get_price = AsyncMock(return_value=None)
        service.cache.set_price = AsyncMock(return_value=True)
        
        # Mock sources
        for source_type in service.sources:
            service.sources[source_type] = Mock()
            service.sources[source_type].initialize = AsyncMock()
            service.sources[source_type].shutdown = AsyncMock()
            service.sources[source_type].get_price = AsyncMock()
        
        await service.initialize()
        yield service
        await service.shutdown()
    
    def test_price_service_initialization(self):
        """Test price service can be created."""
        service = PriceService()
        assert service is not None
        assert len(service.sources) > 0
        assert DataSource.YFINANCE in service.sources
    
    @pytest.mark.asyncio
    async def test_get_price_success(self, price_service):
        """Test successful price fetch."""
        # Mock price data
        mock_price = PriceData(
            symbol="AAPL",
            current_price=150.0,
            price_change=2.5,
            price_change_pct=1.69,
            volume=1000000,
            data_source=DataSource.YFINANCE,
            quality=PriceQuality.DELAYED,
            market_status=MarketStatus.OPEN,
            timestamp=datetime.now(),
            is_valid=True
        )
        
        # Mock source to return price data
        price_service.sources[DataSource.YFINANCE].get_price.return_value = mock_price
        
        # Test the service
        response = await price_service.get_price("AAPL")
        
        assert response.success is True
        assert response.data is not None
        assert response.data.symbol == "AAPL"
        assert response.data.current_price == 150.0
        assert response.source_used == DataSource.YFINANCE
    
    @pytest.mark.asyncio
    async def test_get_price_cache_hit(self, price_service):
        """Test price fetch from cache."""
        # Mock cached price data
        mock_price = PriceData(
            symbol="AAPL",
            current_price=150.0,
            data_source=DataSource.YFINANCE,
            quality=PriceQuality.DELAYED,
            market_status=MarketStatus.OPEN,
            timestamp=datetime.now(),
            is_valid=True
        )
        
        # Mock cache to return data
        price_service.cache.get_price.return_value = mock_price
        
        # Test the service
        response = await price_service.get_price("AAPL")
        
        assert response.success is True
        assert response.cache_hit is True
        assert response.data.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_get_batch_prices(self, price_service):
        """Test batch price fetching."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Mock batch results
        mock_results = {}
        for symbol in symbols:
            mock_price = PriceData(
                symbol=symbol,
                current_price=100.0,
                data_source=DataSource.YFINANCE,
                quality=PriceQuality.DELAYED,
                market_status=MarketStatus.OPEN,
                timestamp=datetime.now(),
                is_valid=True
            )
            mock_results[symbol] = mock_price
        
        # Mock cache to return empty (force fetch)
        price_service.cache.get_batch_prices.return_value = {s: None for s in symbols}
        
        # Mock source batch fetch
        with patch.object(price_service, '_batch_fetch_from_sources') as mock_fetch:
            mock_responses = {}
            for symbol in symbols:
                mock_responses[symbol] = Mock()
                mock_responses[symbol].success = True
                mock_responses[symbol].data = mock_results[symbol]
            
            mock_fetch.return_value = mock_responses
            
            # Test the service
            response = await price_service.get_batch_prices(symbols)
            
            assert response.success is True
            assert response.total_requested == 3
            assert response.successful_count == 3
            assert len(response.results) == 3
    
    @pytest.mark.asyncio
    async def test_price_validation(self, price_service):
        """Test price data validation."""
        # Valid price data
        valid_price = PriceData(
            symbol="AAPL",
            current_price=150.0,
            data_source=DataSource.YFINANCE,
            quality=PriceQuality.DELAYED,
            market_status=MarketStatus.OPEN,
            timestamp=datetime.now(),
            is_valid=True
        )
        
        assert price_service._validate_price_data(valid_price) is True
        
        # Invalid price data (negative price)
        invalid_price = PriceData(
            symbol="AAPL",
            current_price=-10.0,
            data_source=DataSource.YFINANCE,
            quality=PriceQuality.DELAYED,
            market_status=MarketStatus.OPEN,
            timestamp=datetime.now(),
            is_valid=True
        )
        
        assert price_service._validate_price_data(invalid_price) is False
    
    def test_source_order(self, price_service):
        """Test source priority ordering."""
        # Test default order
        order = price_service._get_source_order(None)
        assert order[0] == DataSource.YFINANCE  # Should be primary
        
        # Test with preferred source
        order = price_service._get_source_order(DataSource.IEX_CLOUD)
        assert order[0] == DataSource.IEX_CLOUD
    
    @pytest.mark.asyncio
    async def test_service_metrics(self, price_service):
        """Test service metrics collection."""
        # Simulate some requests
        price_service.metrics['total_requests'] = 100
        price_service.metrics['successful_requests'] = 95
        price_service.metrics['failed_requests'] = 5
        price_service.metrics['response_times'] = [100, 150, 200]
        
        metrics = await price_service.get_service_metrics()
        
        assert 'request_metrics' in metrics
        assert 'performance_metrics' in metrics
        assert 'source_metrics' in metrics
        assert metrics['request_metrics']['total_requests'] == 100
        assert metrics['request_metrics']['success_rate'] == 0.95


if __name__ == "__main__":
    pytest.main([__file__]) 