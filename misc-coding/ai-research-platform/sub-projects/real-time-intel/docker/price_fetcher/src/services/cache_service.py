"""
Cache Service for Price Data

Handles Redis-based caching of price data with intelligent TTL management
based on market hours and data freshness requirements.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import asyncio

import redis.asyncio as aioredis
from pytz import timezone

from ..config import get_settings
from ..models.price_models import PriceData, DataSource, PriceQuality, MarketStatus

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    """
    Redis-based caching service for financial price data.
    
    Features:
    - Intelligent TTL based on market hours
    - Data quality-aware caching
    - Bulk operations for performance
    - Cache warming and prefetching
    """
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.market_tz = timezone(settings.market_timezone)
        
        # Cache key prefixes
        self.PRICE_PREFIX = "price:"
        self.HISTORICAL_PREFIX = "historical:"
        self.MARKET_DATA_PREFIX = "market:"
        self.BATCH_PREFIX = "batch:"
        
        # Performance tracking
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get cached price data for a symbol."""
        try:
            key = f"{self.PRICE_PREFIX}{symbol.upper()}"
            cached_data = await self.redis.get(key)
            
            if cached_data:
                self.cache_stats['hits'] += 1
                data = json.loads(cached_data)
                return PriceData(**data)
            else:
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached price for {symbol}: {e}")
            self.cache_stats['errors'] += 1
            return None
    
    async def set_price(self, price_data: PriceData, custom_ttl: Optional[int] = None) -> bool:
        """Cache price data with intelligent TTL."""
        try:
            key = f"{self.PRICE_PREFIX}{price_data.symbol.upper()}"
            ttl = custom_ttl or self._calculate_ttl(price_data)
            
            # Serialize price data
            data = price_data.dict()
            # Convert datetime objects to ISO strings for JSON serialization
            for field in ['timestamp', 'market_time', 'last_updated']:
                if data.get(field):
                    data[field] = data[field].isoformat()
            
            await self.redis.setex(key, ttl, json.dumps(data))
            self.cache_stats['sets'] += 1
            
            logger.debug(f"Cached price for {price_data.symbol} with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Error caching price for {price_data.symbol}: {e}")
            self.cache_stats['errors'] += 1
            return False
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Get multiple cached prices in batch."""
        try:
            keys = [f"{self.PRICE_PREFIX}{symbol.upper()}" for symbol in symbols]
            cached_values = await self.redis.mget(keys)
            
            results = {}
            for symbol, cached_data in zip(symbols, cached_values):
                if cached_data:
                    try:
                        data = json.loads(cached_data)
                        results[symbol] = PriceData(**data)
                        self.cache_stats['hits'] += 1
                    except Exception as e:
                        logger.error(f"Error deserializing cached data for {symbol}: {e}")
                        results[symbol] = None
                        self.cache_stats['errors'] += 1
                else:
                    results[symbol] = None
                    self.cache_stats['misses'] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting batch prices: {e}")
            self.cache_stats['errors'] += 1
            return {symbol: None for symbol in symbols}
    
    async def set_batch_prices(self, price_data_list: List[PriceData]) -> bool:
        """Cache multiple prices in batch."""
        try:
            pipe = self.redis.pipeline()
            
            for price_data in price_data_list:
                key = f"{self.PRICE_PREFIX}{price_data.symbol.upper()}"
                ttl = self._calculate_ttl(price_data)
                
                # Serialize price data
                data = price_data.dict()
                for field in ['timestamp', 'market_time', 'last_updated']:
                    if data.get(field):
                        data[field] = data[field].isoformat()
                
                pipe.setex(key, ttl, json.dumps(data))
            
            await pipe.execute()
            self.cache_stats['sets'] += len(price_data_list)
            
            logger.debug(f"Batch cached {len(price_data_list)} prices")
            return True
            
        except Exception as e:
            logger.error(f"Error batch caching prices: {e}")
            self.cache_stats['errors'] += 1
            return False
    
    async def delete_price(self, symbol: str) -> bool:
        """Delete cached price data."""
        try:
            key = f"{self.PRICE_PREFIX}{symbol.upper()}"
            result = await self.redis.delete(key)
            
            if result:
                self.cache_stats['deletes'] += 1
                logger.debug(f"Deleted cached price for {symbol}")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error deleting cached price for {symbol}: {e}")
            self.cache_stats['errors'] += 1
            return False
    
    async def cache_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        data: List[Dict],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache historical price data."""
        try:
            key = f"{self.HISTORICAL_PREFIX}{symbol.upper()}:{start_date}:{end_date}"
            cache_ttl = ttl or settings.default_cache_ttl * 12  # Longer TTL for historical
            
            await self.redis.setex(key, cache_ttl, json.dumps(data))
            self.cache_stats['sets'] += 1
            
            logger.debug(f"Cached historical data for {symbol} ({start_date} to {end_date})")
            return True
            
        except Exception as e:
            logger.error(f"Error caching historical data for {symbol}: {e}")
            self.cache_stats['errors'] += 1
            return False
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> Optional[List[Dict]]:
        """Get cached historical data."""
        try:
            key = f"{self.HISTORICAL_PREFIX}{symbol.upper()}:{start_date}:{end_date}"
            cached_data = await self.redis.get(key)
            
            if cached_data:
                self.cache_stats['hits'] += 1
                return json.loads(cached_data)
            else:
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting cached historical data for {symbol}: {e}")
            self.cache_stats['errors'] += 1
            return None
    
    async def warm_cache(self, symbols: List[str]) -> int:
        """Warm cache by checking which symbols need fresh data."""
        try:
            keys = [f"{self.PRICE_PREFIX}{symbol.upper()}" for symbol in symbols]
            cached_values = await self.redis.mget(keys)
            
            stale_symbols = []
            for symbol, cached_data in zip(symbols, cached_values):
                if not cached_data:
                    stale_symbols.append(symbol)
                else:
                    try:
                        data = json.loads(cached_data)
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        
                        # Check if data is stale
                        if self._is_data_stale(timestamp, data.get('quality')):
                            stale_symbols.append(symbol)
                            
                    except Exception:
                        stale_symbols.append(symbol)
            
            return len(stale_symbols)
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return len(symbols)  # Assume all need refresh on error
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        try:
            # Redis info
            redis_info = await self.redis.info()
            
            # Calculate hit rate
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = (self.cache_stats['hits'] / total_requests) if total_requests > 0 else 0
            
            return {
                'cache_stats': self.cache_stats.copy(),
                'hit_rate': hit_rate,
                'redis_info': {
                    'used_memory': redis_info.get('used_memory_human'),
                    'connected_clients': redis_info.get('connected_clients'),
                    'keyspace_hits': redis_info.get('keyspace_hits'),
                    'keyspace_misses': redis_info.get('keyspace_misses')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern."""
        try:
            if pattern:
                keys = await self.redis.keys(pattern)
            else:
                keys = await self.redis.keys(f"{self.PRICE_PREFIX}*")
            
            if keys:
                deleted = await self.redis.delete(*keys)
                self.cache_stats['deletes'] += deleted
                logger.info(f"Cleared {deleted} cache entries")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def _calculate_ttl(self, price_data: PriceData) -> int:
        """Calculate appropriate TTL based on market status and data quality."""
        
        # Base TTL from settings
        if self._is_market_hours():
            base_ttl = settings.market_hours_ttl
        else:
            base_ttl = settings.after_hours_ttl
        
        # Adjust based on data quality
        quality_multipliers = {
            PriceQuality.REAL_TIME: 1.0,
            PriceQuality.DELAYED: 2.0,
            PriceQuality.END_OF_DAY: 4.0,
            PriceQuality.STALE: 0.5,
            PriceQuality.ESTIMATED: 0.5
        }
        
        multiplier = quality_multipliers.get(price_data.quality, 1.0)
        
        # Adjust based on data source reliability
        source_multipliers = {
            DataSource.YFINANCE: 1.0,
            DataSource.ALPHA_VANTAGE: 1.2,
            DataSource.IEX_CLOUD: 0.8,
            DataSource.FINNHUB: 1.1,
            DataSource.MANUAL: 0.5
        }
        
        source_multiplier = source_multipliers.get(price_data.data_source, 1.0)
        
        # Calculate final TTL
        final_ttl = int(base_ttl * multiplier * source_multiplier)
        
        # Ensure minimum and maximum bounds
        return max(30, min(final_ttl, 3600))  # 30 seconds to 1 hour
    
    def _is_market_hours(self) -> bool:
        """Check if current time is during market hours."""
        try:
            now = datetime.now(self.market_tz)
            market_open = now.replace(
                hour=int(settings.market_open_time.split(':')[0]),
                minute=int(settings.market_open_time.split(':')[1]),
                second=0, microsecond=0
            )
            market_close = now.replace(
                hour=int(settings.market_close_time.split(':')[0]),
                minute=int(settings.market_close_time.split(':')[1]),
                second=0, microsecond=0
            )
            
            # Check if it's a weekday and within market hours
            is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
            is_market_time = market_open <= now <= market_close
            
            return is_weekday and is_market_time
            
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return False  # Default to non-market hours on error
    
    def _is_data_stale(self, timestamp: datetime, quality: Optional[str] = None) -> bool:
        """Check if data is considered stale."""
        try:
            now = datetime.now(timestamp.tzinfo or self.market_tz)
            age_seconds = (now - timestamp).total_seconds()
            
            # Different thresholds based on quality
            if quality == PriceQuality.REAL_TIME:
                threshold = 60  # 1 minute
            elif quality == PriceQuality.DELAYED:
                threshold = 1200  # 20 minutes
            else:
                threshold = settings.stale_data_threshold
            
            return age_seconds > threshold
            
        except Exception as e:
            logger.error(f"Error checking data staleness: {e}")
            return True  # Default to stale on error


# Global cache service instance
cache_service = CacheService() 