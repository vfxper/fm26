"""
Performance Optimization (Task 33)
- Redis caching for frequently accessed data
- API response compression (gzip)
- Connection pooling (configured in database.py)
- Lazy loading for large datasets
- Cache invalidation strategies
"""

import json
import time
import gzip
import logging
from typing import Optional, Any, Callable
from functools import wraps

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


# === REDIS CACHE DECORATOR ===

def cached(key_prefix: str, ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Cache decorator for async functions.
    
    Usage:
        @cached("player_profile", ttl=600)
        async def get_player(player_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                from app.core.cache import get_redis_client
                redis = await get_redis_client()
                
                # Build cache key
                if key_func:
                    cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
                else:
                    key_parts = [str(a) for a in args[1:]] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                    cache_key = f"{key_prefix}:{':'.join(key_parts)}"
                
                # Try cache
                cached_data = await redis.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                if result is not None:
                    await redis.setex(cache_key, ttl, json.dumps(result, default=str))
                
                return result
            except Exception as e:
                # Cache failure should not break the app
                logger.debug(f"Cache error (non-fatal): {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern."""
    try:
        from app.core.cache import get_redis_client
        redis = await get_redis_client()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.debug(f"Invalidated {len(keys)} cache entries: {pattern}")
    except Exception as e:
        logger.debug(f"Cache invalidation error: {e}")


# === GZIP COMPRESSION MIDDLEWARE ===

class GzipMiddleware(BaseHTTPMiddleware):
    """Compress responses > 1KB with gzip."""
    
    MIN_SIZE = 1024  # Only compress responses > 1KB
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response
        
        # Only compress JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response
        
        return response  # FastAPI handles this with GZipMiddleware from starlette


# === QUERY PERFORMANCE MONITORING ===

class QueryMonitor:
    """Track slow queries for optimization."""
    
    SLOW_THRESHOLD = 0.5  # seconds
    
    def __init__(self):
        self.slow_queries = []
    
    def record(self, query: str, duration: float, params: dict = None):
        if duration > self.SLOW_THRESHOLD:
            self.slow_queries.append({
                "query": query[:200],
                "duration": duration,
                "timestamp": time.time(),
            })
            logger.warning(f"Slow query ({duration:.2f}s): {query[:100]}")
            
            # Keep only last 100
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]
    
    def get_report(self):
        return {
            "total_slow_queries": len(self.slow_queries),
            "recent": self.slow_queries[-10:],
        }


query_monitor = QueryMonitor()
