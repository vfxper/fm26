"""
Redis Cache Configuration - Async Redis client setup
"""

from typing import Optional
from redis.asyncio import Redis, ConnectionPool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client and connection pool
_redis_client: Optional[Redis] = None
_connection_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """
    Get or create Redis connection pool
    
    Returns:
        ConnectionPool: Redis connection pool
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=settings.REDIS_DECODE_RESPONSES,
        )
        logger.info(f"Created Redis connection pool: {settings.REDIS_URL}")
        
    return _connection_pool


async def get_redis_client() -> Redis:
    """
    Get or create async Redis client
    
    Returns:
        Redis: Async Redis client
    """
    global _redis_client
    
    if _redis_client is None:
        pool = get_connection_pool()
        _redis_client = Redis(connection_pool=pool)
        logger.info("Created Redis client")
        
    return _redis_client


async def init_cache() -> None:
    """
    Initialize Redis cache
    Should be called on application startup
    """
    redis = await get_redis_client()
    
    # Test connection
    try:
        await redis.ping()
        logger.info("Redis cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_cache() -> None:
    """
    Close Redis connections
    Should be called on application shutdown
    """
    global _redis_client, _connection_pool
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")
        
    if _connection_pool is not None:
        await _connection_pool.disconnect()
        _connection_pool = None
        logger.info("Redis connection pool closed")


class CacheKeys:
    """
    Redis cache key patterns
    """
    
    # Player data
    PLAYER_BY_ID = "player:{player_id}"
    PLAYERS_BY_CLUB = "players:club:{club_id}"
    PLAYER_SEARCH = "search:players:{query_hash}"
    
    # Career data
    CAREER_BY_ID = "career:{career_id}"
    CAREER_BY_USER = "career:user:{user_id}"
    
    # Match data
    MATCH_EVENTS = "match:{match_id}:events"
    MATCH_STATE = "match:{match_id}:state"
    MATCH_RESULT = "match:{match_id}:result"
    
    # Session data
    USER_SESSION = "session:{user_id}"
    
    # Rate limiting
    RATE_LIMIT = "ratelimit:{user_id}:{endpoint}"
    
    @staticmethod
    def player_by_id(player_id: int) -> str:
        """Get cache key for player by ID"""
        return CacheKeys.PLAYER_BY_ID.format(player_id=player_id)
    
    @staticmethod
    def players_by_club(club_id: int) -> str:
        """Get cache key for players by club"""
        return CacheKeys.PLAYERS_BY_CLUB.format(club_id=club_id)
    
    @staticmethod
    def career_by_id(career_id: int) -> str:
        """Get cache key for career by ID"""
        return CacheKeys.CAREER_BY_ID.format(career_id=career_id)
    
    @staticmethod
    def match_events(match_id: int) -> str:
        """Get cache key for match events"""
        return CacheKeys.MATCH_EVENTS.format(match_id=match_id)
