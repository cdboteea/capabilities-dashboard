"""
Yahoo Finance Data Source

Primary data source using yfinance library for free, reliable financial data.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import yfinance as yf
import pandas as pd

from ...models.price_models import (
    PriceData, HistoricalPrice, DataSource, PriceQuality, MarketStatus
)
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class YFinanceSource:
    """
    Yahoo Finance data source implementation.
    
    Features:
    - Free real-time and historical data
    - Batch processing support
    - Comprehensive market data
    - No API key required
    """
    
    def __init__(self):
        self.source_type = DataSource.YFINANCE
        self.is_initialized = False
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
    
    async def initialize(self):
        """Initialize the Yahoo Finance source."""
        try:
            # Test connection with a simple request
            test_ticker = yf.Ticker("AAPL")
            info = test_ticker.info
            
            if info and 'symbol' in info:
                self.is_initialized = True
                logger.info("Yahoo Finance source initialized successfully")
            else:
                raise Exception("Failed to get test data from Yahoo Finance")
                
        except Exception as e:
            logger.error(f"Failed to initialize Yahoo Finance source: {e}")
            self.last_error = str(e)
            raise
    
    async def shutdown(self):
        """Shutdown the Yahoo Finance source."""
        self.is_initialized = False
        logger.info("Yahoo Finance source shutdown complete")
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price for a single symbol."""
        try:
            self.request_count += 1
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            price_data = await loop.run_in_executor(
                None, self._fetch_single_price, symbol
            )
            
            return price_data
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error fetching price for {symbol} from Yahoo Finance: {e}")
            return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Get prices for multiple symbols efficiently."""
        try:
            self.request_count += len(symbols)
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            batch_data = await loop.run_in_executor(
                None, self._fetch_batch_prices, symbols
            )
            
            return batch_data
            
        except Exception as e:
            self.error_count += len(symbols)
            self.last_error = str(e)
            logger.error(f"Error fetching batch prices from Yahoo Finance: {e}")
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
            # Run in thread pool
            loop = asyncio.get_event_loop()
            historical_data = await loop.run_in_executor(
                None, self._fetch_historical_data, symbol, start_date, end_date, interval
            )
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []
    
    def _fetch_single_price(self, symbol: str) -> Optional[PriceData]:
        """Fetch single price synchronously."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current data
            info = ticker.info
            if not info:
                return None
            
            # Get recent price data
            hist = ticker.history(period="2d")
            if hist.empty:
                return None
            
            # Get latest price data
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else latest
            
            current_price = float(latest['Close'])
            previous_close = float(previous['Close'])
            
            # Calculate changes
            price_change = current_price - previous_close
            price_change_pct = (price_change / previous_close) * 100 if previous_close > 0 else 0
            
            # Determine market status
            market_status = self._determine_market_status()
            
            # Determine data quality
            quality = PriceQuality.DELAYED  # Yahoo Finance typically has 15-20 min delay
            
            return PriceData(
                symbol=symbol.upper(),
                current_price=current_price,
                open_price=float(latest['Open']) if 'Open' in latest else None,
                high_price=float(latest['High']) if 'High' in latest else None,
                low_price=float(latest['Low']) if 'Low' in latest else None,
                close_price=previous_close,
                price_change=price_change,
                price_change_pct=price_change_pct,
                volume=int(latest['Volume']) if 'Volume' in latest else None,
                market_cap=info.get('marketCap'),
                data_source=self.source_type,
                quality=quality,
                market_status=market_status,
                timestamp=datetime.now(),
                market_time=datetime.now(),  # Would need to convert to ET
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error in _fetch_single_price for {symbol}: {e}")
            return None
    
    def _fetch_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Fetch multiple prices synchronously."""
        try:
            # Yahoo Finance supports batch requests
            symbols_str = " ".join(symbols)
            tickers = yf.Tickers(symbols_str)
            
            results = {}
            
            for symbol in symbols:
                try:
                    ticker = getattr(tickers.tickers, symbol, None)
                    if not ticker:
                        results[symbol] = None
                        continue
                    
                    # Get price data for this symbol
                    price_data = self._fetch_single_price(symbol)
                    results[symbol] = price_data
                    
                except Exception as e:
                    logger.error(f"Error fetching {symbol} in batch: {e}")
                    results[symbol] = None
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            return {symbol: None for symbol in symbols}
    
    def _fetch_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str],
        interval: str
    ) -> List[HistoricalPrice]:
        """Fetch historical data synchronously."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Fetch historical data
            hist = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                actions=True  # Include dividends and splits
            )
            
            if hist.empty:
                return []
            
            historical_prices = []
            
            for date_idx, row in hist.iterrows():
                # Convert pandas Timestamp to date
                price_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                
                historical_price = HistoricalPrice(
                    symbol=symbol.upper(),
                    date=price_date,
                    open_price=float(row['Open']),
                    high_price=float(row['High']),
                    low_price=float(row['Low']),
                    close_price=float(row['Close']),
                    volume=int(row['Volume']) if pd.notna(row['Volume']) else None,
                    dividend=float(row.get('Dividends', 0)) if 'Dividends' in row else None,
                    split_ratio=float(row.get('Stock Splits', 1)) if 'Stock Splits' in row else None,
                    data_source=self.source_type,
                    created_at=datetime.now()
                )
                
                historical_prices.append(historical_price)
            
            return historical_prices
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []
    
    def _determine_market_status(self) -> MarketStatus:
        """Determine current market status."""
        try:
            now = datetime.now()
            
            # Simple market hours check (would need timezone handling for production)
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
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.request_count),
            'last_error': self.last_error
        } 