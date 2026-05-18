"""
Database Configuration - Async SQLAlchemy setup
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create declarative base for models
Base = declarative_base()

# Global engine and session factory
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create async database engine
    
    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _engine
    
    if _engine is None:
        # Use different pool configurations based on environment
        if settings.ENVIRONMENT == "production":
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                poolclass=AsyncAdaptedQueuePool,
                future=True,
            )
        else:
            # NullPool doesn't accept pool_size and max_overflow
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                poolclass=NullPool,
                future=True,
            )
        logger.info(f"Created database engine: {settings.DATABASE_URL}")
        
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create async session factory
    
    Returns:
        async_sessionmaker: SQLAlchemy async session factory
    """
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Created async session factory")
        
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create all tables
    Should be called on application startup
    """
    engine = get_engine()
    
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import (
            User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
            Injury, Staff, TrainingSchedule
        )
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db() -> None:
    """
    Close database connections
    Should be called on application shutdown
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connections closed")


async def check_db_health() -> bool:
    """
    Check database connection health
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            # Execute simple query to verify connection
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Alias for convenience (used by API routes)
get_db = get_db_session
