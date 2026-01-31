"""Market utilities for handling market hours, holidays, and time zones."""

from datetime import datetime, time, date
from typing import Optional, Tuple
import pytz
from enum import Enum

from ..config import get_settings
from ..models.price_models import MarketStatus

settings = get_settings()


class MarketHoliday(Enum):
    """US Market holidays."""
    NEW_YEARS = "New Year's Day"
    MLK_DAY = "Martin Luther King Jr. Day"
    PRESIDENTS_DAY = "Presidents' Day"
    GOOD_FRIDAY = "Good Friday"
    MEMORIAL_DAY = "Memorial Day"
    INDEPENDENCE_DAY = "Independence Day"
    LABOR_DAY = "Labor Day"
    THANKSGIVING = "Thanksgiving Day"
    CHRISTMAS = "Christmas Day"


def get_market_timezone() -> pytz.BaseTzInfo:
    """Get market timezone (Eastern Time)."""
    return pytz.timezone(settings.market_timezone)


def convert_to_market_time(dt: datetime) -> datetime:
    """Convert datetime to market timezone."""
    market_tz = get_market_timezone()
    
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(market_tz)


def get_market_hours() -> Tuple[time, time, time, time]:
    """
    Get market hours in Eastern Time.
    
    Returns:
        Tuple of (pre_market_start, market_open, market_close, after_hours_end)
    """
    try:
        # Parse times from settings
        market_open = time(*map(int, settings.market_open_time.split(':')))
        market_close = time(*map(int, settings.market_close_time.split(':')))
        
        # Standard pre-market and after-hours times
        pre_market_start = time(4, 0)  # 4:00 AM ET
        after_hours_end = time(20, 0)  # 8:00 PM ET
        
        return pre_market_start, market_open, market_close, after_hours_end
        
    except Exception:
        # Default times if parsing fails
        return time(4, 0), time(9, 30), time(16, 0), time(20, 0)


def is_market_holiday(check_date: Optional[date] = None) -> bool:
    """Check if a date is a market holiday."""
    if check_date is None:
        check_date = date.today()
    
    year = check_date.year
    
    # Calculate US market holidays for the year
    holidays = [
        # New Year's Day
        date(year, 1, 1),
        
        # Martin Luther King Jr. Day (3rd Monday in January)
        _get_nth_weekday(year, 1, 0, 3),
        
        # Presidents' Day (3rd Monday in February)
        _get_nth_weekday(year, 2, 0, 3),
        
        # Good Friday (Friday before Easter) - simplified calculation
        _get_good_friday(year),
        
        # Memorial Day (last Monday in May)
        _get_last_weekday(year, 5, 0),
        
        # Independence Day
        date(year, 7, 4),
        
        # Labor Day (1st Monday in September)
        _get_nth_weekday(year, 9, 0, 1),
        
        # Thanksgiving (4th Thursday in November)
        _get_nth_weekday(year, 11, 3, 4),
        
        # Christmas Day
        date(year, 12, 25)
    ]
    
    # If holiday falls on weekend, check if it's observed on Friday/Monday
    observed_holidays = []
    for holiday in holidays:
        if holiday.weekday() == 5:  # Saturday
            observed_holidays.append(holiday.replace(day=holiday.day - 1))  # Friday
        elif holiday.weekday() == 6:  # Sunday
            observed_holidays.append(holiday.replace(day=holiday.day + 1))  # Monday
        else:
            observed_holidays.append(holiday)
    
    return check_date in observed_holidays


def is_trading_day(check_date: Optional[date] = None) -> bool:
    """Check if a date is a trading day (weekday and not a holiday)."""
    if check_date is None:
        check_date = date.today()
    
    # Check if it's a weekend
    if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check if it's a market holiday
    return not is_market_holiday(check_date)


def get_market_status(dt: Optional[datetime] = None) -> MarketStatus:
    """
    Get current market status.
    
    Args:
        dt: Datetime to check (defaults to current time)
        
    Returns:
        MarketStatus enum value
    """
    if dt is None:
        dt = datetime.now()
    
    # Convert to market timezone
    market_time = convert_to_market_time(dt)
    market_date = market_time.date()
    current_time = market_time.time()
    
    # Check if it's a trading day
    if not is_trading_day(market_date):
        return MarketStatus.HOLIDAY if is_market_holiday(market_date) else MarketStatus.CLOSED
    
    # Get market hours
    pre_market_start, market_open, market_close, after_hours_end = get_market_hours()
    
    # Determine status based on time
    if current_time < pre_market_start:
        return MarketStatus.CLOSED
    elif pre_market_start <= current_time < market_open:
        return MarketStatus.PRE_MARKET
    elif market_open <= current_time < market_close:
        return MarketStatus.OPEN
    elif market_close <= current_time < after_hours_end:
        return MarketStatus.AFTER_HOURS
    else:
        return MarketStatus.CLOSED


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """Check if the market is currently open for trading."""
    status = get_market_status(dt)
    return status == MarketStatus.OPEN


def is_extended_hours(dt: Optional[datetime] = None) -> bool:
    """Check if it's extended hours trading (pre-market or after-hours)."""
    status = get_market_status(dt)
    return status in [MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS]


def get_next_market_open() -> datetime:
    """Get the next market open time."""
    market_tz = get_market_timezone()
    now = datetime.now(market_tz)
    
    # Start with today
    check_date = now.date()
    market_open_time = time(*map(int, settings.market_open_time.split(':')))
    
    for _ in range(10):  # Check up to 10 days ahead
        if is_trading_day(check_date):
            market_open_dt = datetime.combine(check_date, market_open_time)
            market_open_dt = market_tz.localize(market_open_dt)
            
            if market_open_dt > now:
                return market_open_dt
        
        # Move to next day
        check_date = date.fromordinal(check_date.toordinal() + 1)
    
    # Fallback - return tomorrow at market open
    tomorrow = date.fromordinal(now.date().toordinal() + 1)
    market_open_dt = datetime.combine(tomorrow, market_open_time)
    return market_tz.localize(market_open_dt)


def get_next_market_close() -> datetime:
    """Get the next market close time."""
    market_tz = get_market_timezone()
    now = datetime.now(market_tz)
    
    # Check today first
    check_date = now.date()
    market_close_time = time(*map(int, settings.market_close_time.split(':')))
    
    if is_trading_day(check_date):
        market_close_dt = datetime.combine(check_date, market_close_time)
        market_close_dt = market_tz.localize(market_close_dt)
        
        if market_close_dt > now:
            return market_close_dt
    
    # Look for next trading day
    for _ in range(10):
        check_date = date.fromordinal(check_date.toordinal() + 1)
        if is_trading_day(check_date):
            market_close_dt = datetime.combine(check_date, market_close_time)
            return market_tz.localize(market_close_dt)
    
    # Fallback
    tomorrow = date.fromordinal(now.date().toordinal() + 1)
    market_close_dt = datetime.combine(tomorrow, market_close_time)
    return market_tz.localize(market_close_dt)


def get_trading_session_info(dt: Optional[datetime] = None) -> dict:
    """Get comprehensive trading session information."""
    if dt is None:
        dt = datetime.now()
    
    market_time = convert_to_market_time(dt)
    status = get_market_status(dt)
    
    return {
        'market_time': market_time,
        'market_status': status.value,
        'is_trading_day': is_trading_day(market_time.date()),
        'is_market_holiday': is_market_holiday(market_time.date()),
        'is_market_open': status == MarketStatus.OPEN,
        'is_extended_hours': status in [MarketStatus.PRE_MARKET, MarketStatus.AFTER_HOURS],
        'next_market_open': get_next_market_open(),
        'next_market_close': get_next_market_close(),
        'market_hours': {
            'pre_market_start': get_market_hours()[0],
            'market_open': get_market_hours()[1],
            'market_close': get_market_hours()[2],
            'after_hours_end': get_market_hours()[3]
        }
    }


# Helper functions for holiday calculations
def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month."""
    # Find first occurrence
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()
    
    # Calculate days to add
    days_to_add = (weekday - first_weekday) % 7
    first_occurrence = first_day.replace(day=1 + days_to_add)
    
    # Add weeks to get nth occurrence
    nth_occurrence = first_occurrence.replace(day=first_occurrence.day + (n - 1) * 7)
    
    return nth_occurrence


def _get_last_weekday(year: int, month: int, weekday: int) -> date:
    """Get the last occurrence of a weekday in a month."""
    # Start from the last day of the month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    
    last_day = date.fromordinal(next_month.toordinal() - 1)
    
    # Find the last occurrence of the weekday
    days_back = (last_day.weekday() - weekday) % 7
    return date.fromordinal(last_day.toordinal() - days_back)


def _get_good_friday(year: int) -> date:
    """Calculate Good Friday (simplified - uses Easter calculation)."""
    # Simplified Easter calculation (Gregorian calendar)
    # This is a basic implementation - for production, use a proper library
    
    # Basic Easter calculation for Western Christianity
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    easter = date(year, month, day)
    
    # Good Friday is 2 days before Easter
    return date.fromordinal(easter.toordinal() - 2) 