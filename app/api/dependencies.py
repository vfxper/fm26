"""
API Dependencies - Dependency injection for FastAPI routes
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.cache import get_redis_client
from redis.asyncio import Redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency
    Provides async SQLAlchemy session to route handlers
    """
    async for session in get_db_session():
        yield session


async def get_cache() -> AsyncGenerator[Redis, None]:
    """
    Redis cache dependency
    Provides async Redis client to route handlers
    """
    redis = await get_redis_client()
    try:
        yield redis
    finally:
        # Connection is managed by connection pool, no need to close
        pass


async def verify_telegram_auth(init_data: str) -> dict:
    """
    Verify Telegram Web App initData
    
    Args:
        init_data: Telegram initData string from Web App
        
    Returns:
        dict: Parsed and verified user data
        
    Raises:
        HTTPException: If authentication fails
    """
    # TODO: Implement Telegram initData validation with HMAC
    # This is a placeholder for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Telegram authentication not yet implemented"
    )


async def get_current_user(
    init_data: str = Depends(verify_telegram_auth),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from Telegram initData
    
    Args:
        init_data: Verified Telegram user data
        db: Database session
        
    Returns:
        dict: User data from database
        
    Raises:
        HTTPException: If user not found
    """
    # TODO: Implement user lookup from database
    # This is a placeholder for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User authentication not yet implemented"
    )
