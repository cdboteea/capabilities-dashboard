"""
Alpha Vantage Data Source

Premium data source with real-time data and comprehensive market information.
Requires API key and has rate limits.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import httpx

from ...models.price_models import (
    PriceData, HistoricalPrice, DataSource, PriceQuality, MarketStatus
)
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AlphaVantageSource:
    """
    Alpha Vantage data source implementation.
    
    Features:
    - Real-time data (with API key)
    - Comprehensive fundamental data
    - Rate limited (5 requests per minute for free tier)
    - High data quality
    """
    
    def __init__(self):
        self.source_type = DataSource.ALPHA_VANTAGE
        self.is_initialized = False
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
        
        # Rate limiting
        self.requests_per_minute = settings.alpha_vantage_rate_limit
        self.request_times = []
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize the Alpha Vantage source."""
        try:
            if not self.api_key:
                raise Exception("Alpha Vantage API key not provided")
            
            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.request_timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
            
            # Test API connection
            test_response = await self._make_request("GLOBAL_QUOTE", symbol="AAPL")
            
            if test_response and "Global Quote" in test_response:
                self.is_initialized = True
                logger.info("Alpha Vantage source initialized successfully")
            else:
                raise Exception("Failed to get test data from Alpha Vantage")
                
        except Exception as e:
            logger.error(f"Failed to initialize Alpha Vantage source: {e}")
            self.last_error = str(e)
            raise
    
    async def shutdown(self):
        """Shutdown the Alpha Vantage source."""
        if self.client:
            await self.client.aclose()
        
        self.is_initialized = False
        logger.info("Alpha Vantage source shutdown complete")
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price for a single symbol."""
        try:
            if not await self._check_rate_limit():
                logger.warning("Alpha Vantage rate limit exceeded")
                return None
            
            self.request_count += 1
            
            # Get quote data
            response = await self._make_request("GLOBAL_QUOTE", symbol=symbol)
            
            if not response or "Global Quote" not in response:
                return None
            
            quote_data = response["Global Quote"]
            
            # Parse price data
            current_price = float(quote_data.get("05. price", 0))
            if current_price <= 0:
                return None
            
            previous_close = float(quote_data.get("08. previous close", 0))
            price_change = float(quote_data.get("09. change", 0))
            price_change_pct = float(quote_data.get("10. change percent", "0%").rstrip('%'))
            
            # Parse other fields
            open_price = float(quote_data.get("02. open", 0)) or None
            high_price = float(quote_data.get("03. high", 0)) or None
            low_price = float(quote_data.get("04. low", 0)) or None
            volume = int(quote_data.get("06. volume", 0)) or None
            
            # Parse timestamp
            latest_trading_day = quote_data.get("07. latest trading day", "")
            timestamp = self._parse_timestamp(latest_trading_day)
            
            return PriceData(
                symbol=symbol.upper(),
                current_price=current_price,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=previous_close,
                price_change=price_change,
                price_change_pct=price_change_pct,
                volume=volume,
                data_source=self.source_type,
                quality=PriceQuality.REAL_TIME,  # Alpha Vantage provides real-time data
                market_status=self._determine_market_status(),
                timestamp=timestamp,
                market_time=timestamp,
                is_valid=True
            )
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error fetching price for {symbol} from Alpha Vantage: {e}")
            return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Get prices for multiple symbols (sequential due to rate limits)."""
        try:
            results = {}
            
            # Alpha Vantage doesn't support true batch requests
            # Process sequentially to respect rate limits
            for symbol in symbols:
                if not await self._check_rate_limit():
                    logger.warning(f"Rate limit reached, skipping remaining symbols")
                    # Fill remaining with None
                    for remaining_symbol in symbols[len(results):]:
                        results[remaining_symbol] = None
                    break
                
                price_data = await self.get_price(symbol)
                results[symbol] = price_data
                
                # Small delay between requests to avoid rate limiting
                await asyncio.sleep(12)  # 5 requests per minute = 12 seconds between requests
            
            return results
            
        except Exception as e:
            self.error_count += len(symbols)
            self.last_error = str(e)
            logger.error(f"Error fetching batch prices from Alpha Vantage: {e}")
            return {symbol: None for symbol in symbols}
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """Get historical price data."""
        try:
            if not await self._check_rate_limit():
                return []
            
            # Map interval to Alpha Vantage function
            if interval == "1d":
                function = "TIME_SERIES_DAILY"
            elif interval == "1wk":
                function = "TIME_SERIES_WEEKLY"
            elif interval == "1mo":
                function = "TIME_SERIES_MONTHLY"
            else:
                function = "TIME_SERIES_DAILY"
            
            response = await self._make_request(function, symbol=symbol)
            
            if not response:
                return []
            
            # Get the time series data
            time_series_key = None
            for key in response.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                return []
            
            time_series = response[time_series_key]
            historical_prices = []
            
            for date_str, price_data in time_series.items():
                try:
                    price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Filter by date range if specified
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                    if price_date < start_dt:
                        continue
                    
                    if end_date:
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                        if price_date > end_dt:
                            continue
                    
                    historical_price = HistoricalPrice(
                        symbol=symbol.upper(),
                        date=price_date,
                        open_price=float(price_data.get("1. open", 0)),
                        high_price=float(price_data.get("2. high", 0)),
                        low_price=float(price_data.get("3. low", 0)),
                        close_price=float(price_data.get("4. close", 0)),
                        volume=int(price_data.get("5. volume", 0)) or None,
                        data_source=self.source_type,
                        created_at=datetime.now()
                    )
                    
                    historical_prices.append(historical_price)
                    
                except Exception as e:
                    logger.error(f"Error parsing historical data point: {e}")
                    continue
            
            # Sort by date (most recent first)
            historical_prices.sort(key=lambda x: x.date, reverse=True)
            
            return historical_prices
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []
    
    async def _make_request(self, function: str, **params) -> Optional[Dict[str, Any]]:
        """Make API request to Alpha Vantage."""
        try:
            if not self.client:
                return None
            
            # Build request parameters
            request_params = {
                "function": function,
                "apikey": self.api_key,
                **params
            }
            
            # Make request
            response = await self.client.get(self.base_url, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return None
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage note: {data['Note']}")
                return None
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Alpha Vantage: {e}")
            return None
        except Exception as e:
            logger.error(f"Error making Alpha Vantage request: {e}")
            return None
    
    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        try:
            now = datetime.now()
            
            # Remove requests older than 1 minute
            self.request_times = [
                req_time for req_time in self.request_times
                if (now - req_time).total_seconds() < 60
            ]
            
            # Check if we can make another request
            if len(self.request_times) >= self.requests_per_minute:
                return False
            
            # Add current request time
            self.request_times.append(now)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from Alpha Vantage response."""
        try:
            if timestamp_str:
                return datetime.strptime(timestamp_str, "%Y-%m-%d")
            else:
                return datetime.now()
        except Exception:
            return datetime.now()
    
    def _determine_market_status(self) -> MarketStatus:
        """Determine current market status."""
        try:
            now = datetime.now()
            
            # Simple market hours check
            if now.weekday() >= 5:  # Weekend
                return MarketStatus.CLOSED
            
            hour = now.hour
            if 9 <= hour < 16:  # Simplified market hours
                return MarketStatus.OPEN
            elif 4 <= hour < 9:  # Pre-market
                return MarketStatus.PRE_MARKET
            elif 16 <= hour < 20:  # After hours
                return MarketStatus.AFTER_HOURS
            else:
                return MarketStatus.CLOSED
                
        except Exception:
            return MarketStatus.CLOSED
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get source status and metrics."""
        return {
            'source': self.source_type.value,
            'initialized': self.is_initialized,
            'api_key_configured': bool(self.api_key),
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.request_count),
            'rate_limit_remaining': max(0, self.requests_per_minute - len(self.request_times)),
            'last_error': self.last_error
        } 