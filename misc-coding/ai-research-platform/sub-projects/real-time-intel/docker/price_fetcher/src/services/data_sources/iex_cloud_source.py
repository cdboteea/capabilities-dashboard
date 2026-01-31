"""
IEX Cloud Data Source

High-quality financial data source with excellent API and reasonable pricing.
Good balance between cost and data quality.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import httpx

from ...models.price_models import (
    PriceData, HistoricalPrice, DataSource, PriceQuality, MarketStatus
)
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class IEXCloudSource:
    """
    IEX Cloud data source implementation.
    
    Features:
    - High-quality real-time data
    - Excellent API design
    - Batch request support
    - Reasonable rate limits
    """
    
    def __init__(self):
        self.source_type = DataSource.IEX_CLOUD
        self.is_initialized = False
        self.api_key = settings.iex_cloud_api_key
        self.base_url = "https://cloud.iexapis.com/stable"
        
        # Rate limiting
        self.requests_per_second = settings.iex_cloud_rate_limit
        self.request_times = []
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize the IEX Cloud source."""
        try:
            if not self.api_key:
                raise Exception("IEX Cloud API key not provided")
            
            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.request_timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
            
            # Test API connection
            test_response = await self._make_request("/stock/aapl/quote")
            
            if test_response and "symbol" in test_response:
                self.is_initialized = True
                logger.info("IEX Cloud source initialized successfully")
            else:
                raise Exception("Failed to get test data from IEX Cloud")
                
        except Exception as e:
            logger.error(f"Failed to initialize IEX Cloud source: {e}")
            self.last_error = str(e)
            raise
    
    async def shutdown(self):
        """Shutdown the IEX Cloud source."""
        if self.client:
            await self.client.aclose()
        
        self.is_initialized = False
        logger.info("IEX Cloud source shutdown complete")
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price for a single symbol."""
        try:
            if not await self._check_rate_limit():
                logger.warning("IEX Cloud rate limit exceeded")
                return None
            
            self.request_count += 1
            
            # Get quote data
            endpoint = f"/stock/{symbol.lower()}/quote"
            response = await self._make_request(endpoint)
            
            if not response:
                return None
            
            # Parse price data
            current_price = response.get("latestPrice")
            if not current_price or current_price <= 0:
                return None
            
            # Calculate changes
            previous_close = response.get("previousClose", 0)
            price_change = response.get("change", 0)
            price_change_pct = response.get("changePercent", 0) * 100  # IEX returns decimal
            
            # Parse timestamp
            latest_time = response.get("latestTime", "")
            timestamp = self._parse_timestamp(latest_time, response.get("latestUpdate"))
            
            # Determine data quality based on source
            latest_source = response.get("latestSource", "")
            quality = self._determine_quality(latest_source)
            
            return PriceData(
                symbol=symbol.upper(),
                current_price=float(current_price),
                open_price=response.get("open"),
                high_price=response.get("high"),
                low_price=response.get("low"),
                close_price=previous_close,
                price_change=price_change,
                price_change_pct=price_change_pct,
                volume=response.get("latestVolume"),
                avg_volume=response.get("avgTotalVolume"),
                market_cap=response.get("marketCap"),
                bid_price=response.get("iexBidPrice"),
                ask_price=response.get("iexAskPrice"),
                bid_size=response.get("iexBidSize"),
                ask_size=response.get("iexAskSize"),
                data_source=self.source_type,
                quality=quality,
                market_status=self._determine_market_status(),
                timestamp=timestamp,
                market_time=timestamp,
                is_valid=True
            )
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error fetching price for {symbol} from IEX Cloud: {e}")
            return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Get prices for multiple symbols efficiently using batch API."""
        try:
            if not await self._check_rate_limit():
                logger.warning("IEX Cloud rate limit exceeded")
                return {symbol: None for symbol in symbols}
            
            self.request_count += 1  # Batch counts as single request
            
            # IEX Cloud supports batch requests
            symbols_str = ",".join(symbols).lower()
            endpoint = f"/stock/market/batch"
            
            params = {
                "symbols": symbols_str,
                "types": "quote",
                "format": "json"
            }
            
            response = await self._make_request(endpoint, params=params)
            
            if not response:
                return {symbol: None for symbol in symbols}
            
            results = {}
            
            for symbol in symbols:
                symbol_upper = symbol.upper()
                symbol_lower = symbol.lower()
                
                # Check if data exists for this symbol
                if symbol_lower in response and "quote" in response[symbol_lower]:
                    quote_data = response[symbol_lower]["quote"]
                    
                    try:
                        # Parse similar to single request
                        current_price = quote_data.get("latestPrice")
                        if not current_price or current_price <= 0:
                            results[symbol] = None
                            continue
                        
                        previous_close = quote_data.get("previousClose", 0)
                        price_change = quote_data.get("change", 0)
                        price_change_pct = quote_data.get("changePercent", 0) * 100
                        
                        latest_time = quote_data.get("latestTime", "")
                        timestamp = self._parse_timestamp(latest_time, quote_data.get("latestUpdate"))
                        
                        latest_source = quote_data.get("latestSource", "")
                        quality = self._determine_quality(latest_source)
                        
                        price_data = PriceData(
                            symbol=symbol_upper,
                            current_price=float(current_price),
                            open_price=quote_data.get("open"),
                            high_price=quote_data.get("high"),
                            low_price=quote_data.get("low"),
                            close_price=previous_close,
                            price_change=price_change,
                            price_change_pct=price_change_pct,
                            volume=quote_data.get("latestVolume"),
                            avg_volume=quote_data.get("avgTotalVolume"),
                            market_cap=quote_data.get("marketCap"),
                            bid_price=quote_data.get("iexBidPrice"),
                            ask_price=quote_data.get("iexAskPrice"),
                            bid_size=quote_data.get("iexBidSize"),
                            ask_size=quote_data.get("iexAskSize"),
                            data_source=self.source_type,
                            quality=quality,
                            market_status=self._determine_market_status(),
                            timestamp=timestamp,
                            market_time=timestamp,
                            is_valid=True
                        )
                        
                        results[symbol] = price_data
                        
                    except Exception as e:
                        logger.error(f"Error parsing batch data for {symbol}: {e}")
                        results[symbol] = None
                else:
                    results[symbol] = None
            
            return results
            
        except Exception as e:
            self.error_count += len(symbols)
            self.last_error = str(e)
            logger.error(f"Error fetching batch prices from IEX Cloud: {e}")
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
            
            # IEX Cloud historical data endpoint
            endpoint = f"/stock/{symbol.lower()}/chart"
            
            # Calculate date range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
            
            # Determine range parameter
            days_diff = (end_dt - start_dt).days
            
            if days_diff <= 30:
                range_param = "1m"
            elif days_diff <= 90:
                range_param = "3m"
            elif days_diff <= 180:
                range_param = "6m"
            elif days_diff <= 365:
                range_param = "1y"
            else:
                range_param = "5y"
            
            params = {"range": range_param}
            
            response = await self._make_request(endpoint, params=params)
            
            if not response or not isinstance(response, list):
                return []
            
            historical_prices = []
            
            for data_point in response:
                try:
                    price_date_str = data_point.get("date")
                    if not price_date_str:
                        continue
                    
                    price_date = datetime.strptime(price_date_str, "%Y-%m-%d").date()
                    
                    # Filter by date range
                    if price_date < start_dt or price_date > end_dt:
                        continue
                    
                    historical_price = HistoricalPrice(
                        symbol=symbol.upper(),
                        date=price_date,
                        open_price=float(data_point.get("open", 0)),
                        high_price=float(data_point.get("high", 0)),
                        low_price=float(data_point.get("low", 0)),
                        close_price=float(data_point.get("close", 0)),
                        volume=data_point.get("volume"),
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
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make API request to IEX Cloud."""
        try:
            if not self.client:
                return None
            
            # Build URL
            url = f"{self.base_url}{endpoint}"
            
            # Add API key to parameters
            request_params = params or {}
            request_params["token"] = self.api_key
            
            # Make request
            response = await self.client.get(url, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Symbol not found in IEX Cloud: {endpoint}")
            else:
                logger.error(f"HTTP error from IEX Cloud: {e}")
            return None
        except Exception as e:
            logger.error(f"Error making IEX Cloud request: {e}")
            return None
    
    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        try:
            now = datetime.now()
            
            # Remove requests older than 1 second
            self.request_times = [
                req_time for req_time in self.request_times
                if (now - req_time).total_seconds() < 1
            ]
            
            # Check if we can make another request
            if len(self.request_times) >= self.requests_per_second:
                return False
            
            # Add current request time
            self.request_times.append(now)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    def _parse_timestamp(self, latest_time: str, latest_update: Optional[int] = None) -> datetime:
        """Parse timestamp from IEX Cloud response."""
        try:
            if latest_update:
                # Unix timestamp in milliseconds
                return datetime.fromtimestamp(latest_update / 1000)
            elif latest_time:
                # Try to parse time string
                return datetime.now()  # Simplified for now
            else:
                return datetime.now()
        except Exception:
            return datetime.now()
    
    def _determine_quality(self, latest_source: str) -> PriceQuality:
        """Determine data quality based on IEX source."""
        if latest_source in ["IEX real time price", "15 minute delayed price"]:
            return PriceQuality.REAL_TIME
        elif "delayed" in latest_source.lower():
            return PriceQuality.DELAYED
        elif "close" in latest_source.lower():
            return PriceQuality.END_OF_DAY
        else:
            return PriceQuality.DELAYED
    
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
            'rate_limit_remaining': max(0, self.requests_per_second - len(self.request_times)),
            'last_error': self.last_error
        } 