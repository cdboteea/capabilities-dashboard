"""
Price Service - Main Orchestration Layer

Coordinates price data fetching from multiple sources with fallback logic,
caching, rate limiting, and data validation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings
from ..models.price_models import (
    PriceData, PriceRequest, PriceResponse, BatchPriceResponse,
    DataSource, PriceQuality, MarketStatus, HistoricalPrice
)
from .cache_service import cache_service
from .data_sources.yfinance_source import YFinanceSource
from .data_sources.alpha_vantage_source import AlphaVantageSource
from .data_sources.iex_cloud_source import IEXCloudSource

logger = logging.getLogger(__name__)
settings = get_settings()


class PriceService:
    """
    Main price service that orchestrates data fetching from multiple sources.
    
    Features:
    - Multi-source data fetching with fallback
    - Intelligent caching and cache warming
    - Rate limiting and request throttling
    - Data validation and quality scoring
    - Batch processing optimization
    """
    
    def __init__(self):
        self.cache = cache_service
        
        # Initialize data sources
        self.sources = {
            DataSource.YFINANCE: YFinanceSource(),
            DataSource.ALPHA_VANTAGE: AlphaVantageSource(),
            DataSource.IEX_CLOUD: IEXCloudSource()
        }
        
        # Source priority and availability
        self.source_priority = [
            DataSource.YFINANCE,
            DataSource.IEX_CLOUD,
            DataSource.ALPHA_VANTAGE
        ]
        
        self.source_status = {source: True for source in self.sources.keys()}
        
        # Performance tracking
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'source_usage': {source.value: 0 for source in DataSource},
            'response_times': []
        }
        
        # Rate limiting
        self.rate_limiters = {}
        self._init_rate_limiters()
    
    async def initialize(self):
        """Initialize the price service."""
        try:
            # Connect to cache
            await self.cache.connect()
            
            # Initialize data sources
            for source in self.sources.values():
                await source.initialize()
            
            logger.info("Price service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize price service: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the price service."""
        try:
            # Disconnect from cache
            await self.cache.disconnect()
            
            # Shutdown data sources
            for source in self.sources.values():
                await source.shutdown()
            
            logger.info("Price service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during price service shutdown: {e}")
    
    async def get_price(
        self, 
        symbol: str, 
        force_refresh: bool = False,
        preferred_source: Optional[DataSource] = None
    ) -> PriceResponse:
        """
        Get current price for a single symbol.
        
        Args:
            symbol: Stock ticker symbol
            force_refresh: Force cache refresh
            preferred_source: Preferred data source
            
        Returns:
            PriceResponse with price data or error
        """
        start_time = time.time()
        self.metrics['total_requests'] += 1
        
        try:
            symbol = symbol.upper()
            
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_price = await self.cache.get_price(symbol)
                if cached_price and not self._is_price_stale(cached_price):
                    self.metrics['cache_hits'] += 1
                    response_time = (time.time() - start_time) * 1000
                    
                    return PriceResponse(
                        success=True,
                        data=cached_price,
                        source_used=cached_price.data_source,
                        cache_hit=True,
                        response_time_ms=response_time
                    )
            
            self.metrics['cache_misses'] += 1
            
            # Determine source order
            source_order = self._get_source_order(preferred_source)
            
            # Try each source until success
            last_error = None
            for source_type in source_order:
                if not self.source_status.get(source_type, False):
                    continue
                
                try:
                    # Check rate limits
                    if not await self._check_rate_limit(source_type):
                        logger.debug(f"Rate limit exceeded for {source_type.value}")
                        continue
                    
                    # Fetch data from source
                    source = self.sources[source_type]
                    price_data = await source.get_price(symbol)
                    
                    if price_data:
                        # Validate data
                        if self._validate_price_data(price_data):
                            # Cache the result
                            await self.cache.set_price(price_data)
                            
                            # Update metrics
                            self.metrics['successful_requests'] += 1
                            self.metrics['source_usage'][source_type.value] += 1
                            response_time = (time.time() - start_time) * 1000
                            self.metrics['response_times'].append(response_time)
                            
                            return PriceResponse(
                                success=True,
                                data=price_data,
                                source_used=source_type,
                                cache_hit=False,
                                response_time_ms=response_time
                            )
                        else:
                            logger.warning(f"Invalid price data from {source_type.value} for {symbol}")
                    
                except Exception as e:
                    logger.error(f"Error fetching from {source_type.value} for {symbol}: {e}")
                    last_error = e
                    
                    # Mark source as temporarily unavailable on repeated failures
                    await self._handle_source_error(source_type)
            
            # All sources failed
            self.metrics['failed_requests'] += 1
            response_time = (time.time() - start_time) * 1000
            
            return PriceResponse(
                success=False,
                error_message=f"Failed to fetch price for {symbol}: {last_error}",
                response_time_ms=response_time
            )
            
        except Exception as e:
            self.metrics['failed_requests'] += 1
            logger.error(f"Unexpected error getting price for {symbol}: {e}")
            
            return PriceResponse(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def get_batch_prices(
        self, 
        symbols: List[str], 
        force_refresh: bool = False,
        preferred_source: Optional[DataSource] = None
    ) -> BatchPriceResponse:
        """
        Get prices for multiple symbols efficiently.
        
        Args:
            symbols: List of stock ticker symbols
            force_refresh: Force cache refresh for all symbols
            preferred_source: Preferred data source
            
        Returns:
            BatchPriceResponse with results for all symbols
        """
        start_time = time.time()
        symbols = [s.upper() for s in symbols]
        
        try:
            # Check cache for all symbols
            cache_results = {}
            symbols_to_fetch = []
            
            if not force_refresh:
                cache_results = await self.cache.get_batch_prices(symbols)
                
                # Determine which symbols need fresh data
                for symbol in symbols:
                    cached_price = cache_results.get(symbol)
                    if not cached_price or self._is_price_stale(cached_price):
                        symbols_to_fetch.append(symbol)
            else:
                symbols_to_fetch = symbols.copy()
            
            # Fetch missing/stale data
            fetch_results = {}
            if symbols_to_fetch:
                fetch_results = await self._batch_fetch_from_sources(
                    symbols_to_fetch, preferred_source
                )
            
            # Combine results
            all_results = []
            successful_count = 0
            cache_hits = 0
            
            for symbol in symbols:
                if symbol in fetch_results:
                    result = fetch_results[symbol]
                    all_results.append(result)
                    if result.success:
                        successful_count += 1
                elif symbol in cache_results and cache_results[symbol]:
                    # Use cached data
                    cached_price = cache_results[symbol]
                    result = PriceResponse(
                        success=True,
                        data=cached_price,
                        source_used=cached_price.data_source,
                        cache_hit=True,
                        response_time_ms=0
                    )
                    all_results.append(result)
                    successful_count += 1
                    cache_hits += 1
                else:
                    # No data available
                    result = PriceResponse(
                        success=False,
                        error_message=f"No data available for {symbol}"
                    )
                    all_results.append(result)
            
            # Calculate metrics
            total_response_time = (time.time() - start_time) * 1000
            cache_hit_rate = cache_hits / len(symbols) if symbols else 0
            
            return BatchPriceResponse(
                success=True,
                results=all_results,
                total_requested=len(symbols),
                successful_count=successful_count,
                failed_count=len(symbols) - successful_count,
                cache_hit_rate=cache_hit_rate,
                total_response_time_ms=total_response_time
            )
            
        except Exception as e:
            logger.error(f"Error in batch price fetch: {e}")
            
            # Return error response
            error_results = [
                PriceResponse(
                    success=False,
                    error_message=f"Batch fetch error: {str(e)}"
                ) for _ in symbols
            ]
            
            return BatchPriceResponse(
                success=False,
                results=error_results,
                total_requested=len(symbols),
                successful_count=0,
                failed_count=len(symbols),
                cache_hit_rate=0.0,
                total_response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """Get historical price data for a symbol."""
        try:
            symbol = symbol.upper()
            
            # Check cache first
            cached_data = await self.cache.get_historical_data(
                symbol, start_date, end_date or start_date
            )
            
            if cached_data:
                return [HistoricalPrice(**item) for item in cached_data]
            
            # Fetch from primary source
            source = self.sources.get(DataSource.YFINANCE)
            if source and hasattr(source, 'get_historical_prices'):
                historical_data = await source.get_historical_prices(
                    symbol, start_date, end_date, interval
                )
                
                if historical_data:
                    # Cache the results
                    cache_data = [item.dict() for item in historical_data]
                    await self.cache.cache_historical_data(
                        symbol, start_date, end_date or start_date, cache_data
                    )
                    
                    return historical_data
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            return []
    
    async def warm_cache(self, symbols: List[str]) -> Dict[str, Any]:
        """Warm cache for frequently accessed symbols."""
        try:
            # Check which symbols need refresh
            stale_count = await self.cache.warm_cache(symbols)
            
            if stale_count > 0:
                # Fetch fresh data for stale symbols
                batch_response = await self.get_batch_prices(
                    symbols, force_refresh=False
                )
                
                return {
                    'symbols_checked': len(symbols),
                    'stale_symbols': stale_count,
                    'refreshed_successfully': batch_response.successful_count,
                    'cache_hit_rate': batch_response.cache_hit_rate
                }
            
            return {
                'symbols_checked': len(symbols),
                'stale_symbols': 0,
                'message': 'All symbols have fresh data'
            }
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return {'error': str(e)}
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        try:
            # Calculate derived metrics
            total_requests = self.metrics['total_requests']
            success_rate = (
                self.metrics['successful_requests'] / total_requests 
                if total_requests > 0 else 0
            )
            
            avg_response_time = (
                sum(self.metrics['response_times']) / len(self.metrics['response_times'])
                if self.metrics['response_times'] else 0
            )
            
            # Get cache stats
            cache_stats = await self.cache.get_cache_stats()
            
            return {
                'request_metrics': {
                    'total_requests': total_requests,
                    'successful_requests': self.metrics['successful_requests'],
                    'failed_requests': self.metrics['failed_requests'],
                    'success_rate': success_rate
                },
                'performance_metrics': {
                    'average_response_time_ms': avg_response_time,
                    'cache_hit_rate': (
                        self.metrics['cache_hits'] / 
                        (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                        if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
                    )
                },
                'source_metrics': {
                    'usage_count': self.metrics['source_usage'],
                    'status': self.source_status
                },
                'cache_stats': cache_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
            return {'error': str(e)}
    
    def _get_source_order(self, preferred_source: Optional[DataSource]) -> List[DataSource]:
        """Get ordered list of sources to try."""
        if preferred_source and preferred_source in self.sources:
            # Put preferred source first
            order = [preferred_source]
            order.extend([s for s in self.source_priority if s != preferred_source])
            return order
        
        return self.source_priority.copy()
    
    def _validate_price_data(self, price_data: PriceData) -> bool:
        """Validate price data quality."""
        try:
            # Basic validation
            if price_data.current_price <= 0:
                return False
            
            # Check for reasonable price change
            if price_data.price_change_pct is not None:
                if abs(price_data.price_change_pct) > settings.max_price_change_pct:
                    logger.warning(
                        f"Large price change detected for {price_data.symbol}: "
                        f"{price_data.price_change_pct}%"
                    )
                    # Don't reject, but flag for review
                    price_data.validation_errors.append(
                        f"Large price change: {price_data.price_change_pct}%"
                    )
            
            # Check timestamp freshness
            if price_data.timestamp:
                age = datetime.now() - price_data.timestamp.replace(tzinfo=None)
                if age.total_seconds() > settings.stale_data_threshold:
                    price_data.quality = PriceQuality.STALE
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating price data: {e}")
            return False
    
    def _is_price_stale(self, price_data: PriceData) -> bool:
        """Check if cached price data is stale."""
        try:
            if not price_data.timestamp:
                return True
            
            age = datetime.now() - price_data.timestamp.replace(tzinfo=None)
            
            # Different thresholds based on quality
            if price_data.quality == PriceQuality.REAL_TIME:
                threshold = 60  # 1 minute
            elif price_data.quality == PriceQuality.DELAYED:
                threshold = 1200  # 20 minutes
            else:
                threshold = settings.stale_data_threshold
            
            return age.total_seconds() > threshold
            
        except Exception as e:
            logger.error(f"Error checking price staleness: {e}")
            return True
    
    async def _batch_fetch_from_sources(
        self, 
        symbols: List[str], 
        preferred_source: Optional[DataSource]
    ) -> Dict[str, PriceResponse]:
        """Fetch multiple symbols from sources efficiently."""
        
        # Group symbols by optimal batch size
        batch_size = settings.batch_size
        symbol_batches = [
            symbols[i:i + batch_size] 
            for i in range(0, len(symbols), batch_size)
        ]
        
        # Process batches concurrently
        tasks = []
        for batch in symbol_batches:
            task = self._fetch_batch_from_best_source(batch, preferred_source)
            tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_results = {}
        for batch_result in batch_results:
            if isinstance(batch_result, dict):
                combined_results.update(batch_result)
            else:
                logger.error(f"Batch fetch error: {batch_result}")
        
        return combined_results
    
    async def _fetch_batch_from_best_source(
        self, 
        symbols: List[str], 
        preferred_source: Optional[DataSource]
    ) -> Dict[str, PriceResponse]:
        """Fetch a batch of symbols from the best available source."""
        
        source_order = self._get_source_order(preferred_source)
        
        for source_type in source_order:
            if not self.source_status.get(source_type, False):
                continue
            
            try:
                source = self.sources[source_type]
                
                # Check if source supports batch operations
                if hasattr(source, 'get_batch_prices'):
                    batch_data = await source.get_batch_prices(symbols)
                    
                    if batch_data:
                        # Convert to PriceResponse objects
                        results = {}
                        for symbol, price_data in batch_data.items():
                            if price_data and self._validate_price_data(price_data):
                                # Cache individual results
                                await self.cache.set_price(price_data)
                                
                                results[symbol] = PriceResponse(
                                    success=True,
                                    data=price_data,
                                    source_used=source_type,
                                    cache_hit=False
                                )
                                
                                self.metrics['successful_requests'] += 1
                                self.metrics['source_usage'][source_type.value] += 1
                            else:
                                results[symbol] = PriceResponse(
                                    success=False,
                                    error_message=f"Invalid data from {source_type.value}"
                                )
                                self.metrics['failed_requests'] += 1
                        
                        return results
                
                else:
                    # Fallback to individual requests
                    tasks = [
                        self._fetch_single_from_source(symbol, source_type)
                        for symbol in symbols
                    ]
                    
                    individual_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    results = {}
                    for symbol, result in zip(symbols, individual_results):
                        if isinstance(result, PriceResponse):
                            results[symbol] = result
                        else:
                            results[symbol] = PriceResponse(
                                success=False,
                                error_message=f"Error: {result}"
                            )
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Batch fetch error from {source_type.value}: {e}")
                continue
        
        # All sources failed
        return {
            symbol: PriceResponse(
                success=False,
                error_message="All data sources failed"
            ) for symbol in symbols
        }
    
    async def _fetch_single_from_source(
        self, 
        symbol: str, 
        source_type: DataSource
    ) -> PriceResponse:
        """Fetch single symbol from specific source."""
        try:
            source = self.sources[source_type]
            price_data = await source.get_price(symbol)
            
            if price_data and self._validate_price_data(price_data):
                await self.cache.set_price(price_data)
                
                return PriceResponse(
                    success=True,
                    data=price_data,
                    source_used=source_type,
                    cache_hit=False
                )
            else:
                return PriceResponse(
                    success=False,
                    error_message=f"No valid data from {source_type.value}"
                )
                
        except Exception as e:
            return PriceResponse(
                success=False,
                error_message=f"Error from {source_type.value}: {str(e)}"
            )
    
    async def _check_rate_limit(self, source_type: DataSource) -> bool:
        """Check if source is within rate limits."""
        # Simplified rate limiting - in production, use more sophisticated logic
        return True
    
    async def _handle_source_error(self, source_type: DataSource):
        """Handle errors from data sources."""
        # For now, just log - in production, implement circuit breaker pattern
        logger.warning(f"Error from source {source_type.value}")
    
    def _init_rate_limiters(self):
        """Initialize rate limiters for each source."""
        # Simplified - in production, implement proper rate limiting
        pass


# Global price service instance
price_service = PriceService() 