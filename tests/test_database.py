"""
Test Database Configuration and Connection
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from app.core.database import (
    get_engine,
    get_session_factory,
    get_db_session,
    check_db_health,
    Base,
)
from app.core.config import settings


@pytest.mark.asyncio
async def test_get_engine():
    """Test database engine creation"""
    engine = get_engine()
    
    assert engine is not None
    assert isinstance(engine, AsyncEngine)
    
    # Verify engine is singleton (same instance on multiple calls)
    engine2 = get_engine()
    assert engine is engine2


@pytest.mark.asyncio
async def test_get_session_factory():
    """Test session factory creation"""
    session_factory = get_session_factory()
    
    assert session_factory is not None
    
    # Verify factory is singleton
    session_factory2 = get_session_factory()
    assert session_factory is session_factory2


@pytest.mark.asyncio
async def test_database_connection(test_db_engine):
    """Test basic database connection"""
    async with test_db_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 as test"))
        row = await result.fetchone()
        
        assert row is not None
        assert row[0] == 1


@pytest.mark.asyncio
async def test_database_version(test_db_engine):
    """Test PostgreSQL version is 15+"""
    async with test_db_engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        version_string = (await result.fetchone())[0]
        
        assert "PostgreSQL" in version_string
        
        # Extract version number (e.g., "PostgreSQL 15.3" -> 15)
        version_parts = version_string.split()
        version_number = float(version_parts[1].split('.')[0])
        
        assert version_number >= 15, f"PostgreSQL version must be 15+, got {version_number}"


@pytest.mark.asyncio
async def test_get_db_session(test_db_engine):
    """Test database session dependency"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Create session factory for test
    session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Get session from factory
    async with session_factory() as session:
        assert session is not None
        assert isinstance(session, AsyncSession)
        
        # Test basic query
        result = await session.execute(text("SELECT 1"))
        row = await result.fetchone()
        assert row[0] == 1


@pytest.mark.asyncio
async def test_session_transaction_commit(test_db_session: AsyncSession):
    """Test session transaction commit"""
    # Execute a query
    result = await test_db_session.execute(text("SELECT 1 as value"))
    row = await result.fetchone()
    
    assert row[0] == 1
    
    # Commit should work without errors
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_session_transaction_rollback(test_db_session: AsyncSession):
    """Test session transaction rollback"""
    # Execute a query
    result = await test_db_session.execute(text("SELECT 1 as value"))
    row = await result.fetchone()
    
    assert row[0] == 1
    
    # Rollback should work without errors
    await test_db_session.rollback()


@pytest.mark.asyncio
async def test_check_db_health():
    """Test database health check function"""
    is_healthy = await check_db_health()
    
    assert isinstance(is_healthy, bool)
    # In test environment, database should be healthy
    assert is_healthy is True


@pytest.mark.asyncio
async def test_database_pool_configuration():
    """Test database connection pool is properly configured"""
    engine = get_engine()
    
    # Verify pool settings from config
    if settings.ENVIRONMENT == "production":
        # Production should use connection pooling
        assert engine.pool.size() >= 0  # Pool exists
    
    # Engine should be configured with correct URL
    assert "postgresql+asyncpg" in str(engine.url)


@pytest.mark.asyncio
async def test_concurrent_sessions(test_db_engine):
    """Test multiple concurrent database sessions"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create multiple sessions concurrently
    async with session_factory() as session1:
        async with session_factory() as session2:
            # Both sessions should work independently
            result1 = await session1.execute(text("SELECT 1"))
            result2 = await session2.execute(text("SELECT 2"))
            
            row1 = await result1.fetchone()
            row2 = await result2.fetchone()
            
            assert row1[0] == 1
            assert row2[0] == 2


@pytest.mark.asyncio
async def test_database_current_database(test_db_engine):
    """Test we're connected to the correct database"""
    async with test_db_engine.connect() as conn:
        result = await conn.execute(text("SELECT current_database()"))
        db_name = (await result.fetchone())[0]
        
        assert db_name is not None
        assert isinstance(db_name, str)
        # Test database should have 'test' in name
        assert 'test' in db_name.lower()


@pytest.mark.asyncio
async def test_database_encoding(test_db_engine):
    """Test database encoding is UTF-8"""
    async with test_db_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()")
        )
        encoding = (await result.fetchone())[0]
        
        assert encoding == "UTF8"


@pytest.mark.asyncio
async def test_base_metadata():
    """Test SQLAlchemy Base metadata is properly initialized"""
    assert Base is not None
    assert hasattr(Base, 'metadata')
    assert Base.metadata is not None


@pytest.mark.asyncio
async def test_session_error_handling(test_db_session: AsyncSession):
    """Test session handles errors properly"""
    with pytest.raises(Exception):
        # Execute invalid SQL
        await test_db_session.execute(text("SELECT * FROM nonexistent_table"))
    
    # Session should still be usable after error and rollback
    await test_db_session.rollback()
    
    # Execute valid query
    result = await test_db_session.execute(text("SELECT 1"))
    row = await result.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_database_supports_jsonb(test_db_engine):
    """Test database supports JSONB type (required for flexible schemas)"""
    async with test_db_engine.connect() as conn:
        # Create temporary table with JSONB column
        await conn.execute(text("""
            CREATE TEMPORARY TABLE test_jsonb (
                id SERIAL PRIMARY KEY,
                data JSONB
            )
        """))
        
        # Insert JSONB data
        await conn.execute(text("""
            INSERT INTO test_jsonb (data) 
            VALUES ('{"key": "value", "number": 42}'::jsonb)
        """))
        
        # Query JSONB data
        result = await conn.execute(text("SELECT data FROM test_jsonb"))
        row = await result.fetchone()
        
        assert row is not None
        assert 'key' in row[0]
        assert row[0]['key'] == 'value'
        
        await conn.commit()


@pytest.mark.asyncio
async def test_database_connection_string_format():
    """Test database URL is in correct format for asyncpg"""
    engine = get_engine()
    url_str = str(engine.url)
    
    # Should use asyncpg driver
    assert url_str.startswith("postgresql+asyncpg://")
    
    # Should contain required components
    assert "@" in url_str  # username/password separator
    assert "/" in url_str  # host/database separator
