"""
Pytest Configuration and Fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db_session
from app.core.config import settings


# Test database URL (use separate test database)
TEST_DATABASE_URL = "postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_test_db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """
    Create test database engine
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session
    """
    session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test HTTP client with database session override
    """
    async def override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_player_data() -> dict:
    """
    Sample player data for testing
    """
    return {
        "uid": "TEST001",
        "name": "Test Player",
        "position": "ST",
        "age": 25,
        "nationality": "England",
        "club": "Test FC",
        "ca": 150,
        "pa": 170,
        "finishing": 18,
        "passing": 15,
        "dribbling": 16,
        "pace": 17,
        "stamina": 16,
    }


@pytest.fixture
def sample_career_data() -> dict:
    """
    Sample career data for testing
    """
    return {
        "manager_name": "Test Manager",
        "club_id": 1,
        "current_season": 1,
        "current_week": 1,
    }
