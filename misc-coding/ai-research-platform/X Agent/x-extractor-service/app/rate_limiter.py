"""Rate limiting middleware for the X Post Content Extraction Service."""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

import structlog
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings

logger = structlog.get_logger()


class InMemoryRateLimiter:
    """In-memory rate limiter for tracking request counts."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit."""
        async with self.lock:
            now = time.time()
            window_start = now - window
            
            # Clean old requests
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()
            
            # Check if limit exceeded
            if len(self.requests[key]) >= limit:
                return False
            
            # Add current request
            self.requests[key].append(now)
            return True
    
    async def get_reset_time(self, key: str, window: int) -> int:
        """Get the time when the rate limit resets."""
        async with self.lock:
            if not self.requests[key]:
                return int(time.time())
            
            oldest_request = self.requests[key][0]
            return int(oldest_request + window)


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting."""
    # Use IP address as client identifier
    client_ip = get_remote_address(request)
    
    # You could also use API keys or other identifiers here
    # api_key = request.headers.get("X-API-Key")
    # if api_key:
    #     return f"api_key:{api_key}"
    
    return f"ip:{client_ip}"


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Skip rate limiting for health checks
    if request.url.path == "/api/health":
        return await call_next(request)
    
    client_id = get_client_id(request)
    
    # Check rate limit
    allowed = await rate_limiter.is_allowed(
        client_id,
        settings.rate_limit_requests,
        settings.rate_limit_window
    )
    
    if not allowed:
        reset_time = await rate_limiter.get_reset_time(client_id, settings.rate_limit_window)
        
        logger.warning(
            "Rate limit exceeded",
            client_id=client_id,
            path=request.url.path,
            reset_time=reset_time
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_requests,
                "window": settings.rate_limit_window,
                "reset_time": reset_time
            }
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    
    # Get current usage
    current_usage = len(rate_limiter.requests[client_id])
    reset_time = await rate_limiter.get_reset_time(client_id, settings.rate_limit_window)
    
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
    response.headers["X-RateLimit-Remaining"] = str(max(0, settings.rate_limit_requests - current_usage))
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    
    return response


# Slowapi limiter for additional rate limiting features
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler."""
    logger.warning(
        "Slowapi rate limit exceeded",
        path=request.url.path,
        client_ip=get_remote_address(request)
    )
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail)
        }
    )

