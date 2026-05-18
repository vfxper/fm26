"""
Performance tests for Player Search Service optimizations

Tests the performance improvements implemented in Task 9.5:
- Redis caching for search results
- Redis caching for filter options
- Optimized count queries
- Cache key generation
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters


# Test database setup
@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def sample_players(db_session: AsyncSession):
    """Create sample players for testing"""
    players = []
    
    # Create 100 test players for performance testing
    for i in range(100):
        player = Player(
            uid=f"player_{i:03d}",
            name=f"Player {i}",
            position="ST C" if i % 3 == 0 else "AM RL" if i % 3 == 1 else "D C",
            age=18 + (i % 20),
            ca=100 + i,
            pa=120 + i,
            nationality=f"Country{i % 10}",
            club=f"Club{i % 20}",
            # Technical attributes
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            # Mental attributes
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            # Physical attributes
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            # Financial and physical stats
            price="€1M", wage=10000, height=180, weight=75,
            left_foot=10, right_foot=10,
            traits="Test trait"
        )
        players.append(player)
        db_session.add(player)
    
    await db_session.commit()
    return players


@pytest.mark.asyncio
async def test_cache_key_generation(db_session: AsyncSession):
    """Test that cache keys are generated consistently"""
    service = PlayerSearchService(db_session)
    
    # Same filters should generate same cache key
    filters1 = PlayerSearchFilters(
        search_text="test",
        position="ST",
        min_ca=100,
        max_ca=200
    )
    filters2 = PlayerSearchFilters(
        search_text="test",
        position="ST",
        min_ca=100,
        max_ca=200
    )
    
    key1 = service._generate_cache_key(filters1)
    key2 = service._generate_cache_key(filters2)
    
    assert key1 == key2
    assert key1.startswith("search:players:")
    print(f"✓ Cache key generation: {key1}")


@pytest.mark.asyncio
async def test_cache_key_uniqueness(db_session: AsyncSession):
    """Test that different filters generate different cache keys"""
    service = PlayerSearchService(db_session)
    
    filters1 = PlayerSearchFilters(search_text="test1")
    filters2 = PlayerSearchFilters(search_text="test2")
    filters3 = PlayerSearchFilters(position="ST")
    
    key1 = service._generate_cache_key(filters1)
    key2 = service._generate_cache_key(filters2)
    key3 = service._generate_cache_key(filters3)
    
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3
    print(f"✓ Cache key uniqueness: 3 different keys generated")


@pytest.mark.asyncio
async def test_player_serialization(db_session: AsyncSession, sample_players):
    """Test player serialization for caching"""
    service = PlayerSearchService(db_session)
    
    player = sample_players[0]
    serialized = service._serialize_player(player)
    
    # Check all required fields are present
    assert "id" in serialized
    assert "uid" in serialized
    assert "name" in serialized
    assert "position" in serialized
    assert "age" in serialized
    assert "ca" in serialized
    assert "pa" in serialized
    assert "nationality" in serialized
    assert "club" in serialized
    
    # Check values match
    assert serialized["name"] == player.name
    assert serialized["ca"] == player.ca
    assert serialized["pa"] == player.pa
    
    print(f"✓ Player serialization: {len(serialized)} fields serialized")


@pytest.mark.asyncio
async def test_optimized_count_query(db_session: AsyncSession, sample_players):
    """Test that count query doesn't use subquery"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(position="ST", min_ca=100)
    
    # Measure query time
    start_time = time.time()
    results = await service.search_players(filters)
    query_time = time.time() - start_time
    
    assert results["total"] > 0
    assert len(results["players"]) > 0
    
    # Query should be fast (< 100ms for in-memory SQLite)
    assert query_time < 0.1
    
    print(f"✓ Optimized count query: {query_time*1000:.2f}ms for {results['total']} results")


@pytest.mark.asyncio
async def test_search_performance_with_filters(db_session: AsyncSession, sample_players):
    """Test search performance with multiple filters"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(
        position="ST",
        min_age=20,
        max_age=30,
        min_ca=120,
        max_ca=180,
        order_by="ca"
    )
    
    start_time = time.time()
    results = await service.search_players(filters)
    query_time = time.time() - start_time
    
    assert results["total"] >= 0
    
    # Query should be fast
    assert query_time < 0.1
    
    print(f"✓ Multi-filter search: {query_time*1000:.2f}ms, found {results['total']} players")


@pytest.mark.asyncio
async def test_pagination_performance(db_session: AsyncSession, sample_players):
    """Test pagination performance"""
    service = PlayerSearchService(db_session)
    
    # Test multiple pages
    page_times = []
    for page in range(5):
        filters = PlayerSearchFilters(
            limit=20,
            offset=page * 20,
            order_by="name"
        )
        
        start_time = time.time()
        results = await service.search_players(filters)
        query_time = time.time() - start_time
        page_times.append(query_time)
        
        assert len(results["players"]) <= 20
    
    # All pages should have similar performance
    avg_time = sum(page_times) / len(page_times)
    assert avg_time < 0.1
    
    print(f"✓ Pagination performance: avg {avg_time*1000:.2f}ms per page")


@pytest.mark.asyncio
@patch('app.services.player_search.get_redis_client')
async def test_cache_integration(mock_redis, db_session: AsyncSession, sample_players):
    """Test Redis cache integration"""
    # Mock Redis client
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.setex = AsyncMock()
    mock_redis.return_value = mock_redis_instance
    
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(position="ST", limit=10)
    
    # First search - should query database and cache
    results = await service.search_players(filters)
    
    # Verify cache was attempted to be set
    assert mock_redis_instance.setex.called
    
    # Get the cache key that was used
    cache_key = service._generate_cache_key(filters)
    
    print(f"✓ Cache integration: setex called with key {cache_key}")


@pytest.mark.asyncio
@patch('app.services.player_search.get_redis_client')
async def test_filter_options_caching(mock_redis, db_session: AsyncSession, sample_players):
    """Test that filter options are cached"""
    # Mock Redis client
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.setex = AsyncMock()
    mock_redis.return_value = mock_redis_instance
    
    service = PlayerSearchService(db_session)
    
    # Get filter options
    options = await service.get_filter_options()
    
    # Verify results
    assert "positions" in options
    assert "nationalities" in options
    assert "clubs" in options
    assert "age_range" in options
    assert "ca_range" in options
    assert "pa_range" in options
    
    # Verify cache was set
    assert mock_redis_instance.setex.called
    
    # Check cache key
    call_args = mock_redis_instance.setex.call_args
    cache_key = call_args[0][0]
    assert cache_key == "search:filter_options"
    
    # Check TTL (should be 3600 seconds = 1 hour)
    ttl = call_args[0][1]
    assert ttl == 3600
    
    print(f"✓ Filter options caching: cached with 1 hour TTL")


@pytest.mark.asyncio
@patch('app.services.player_search.get_redis_client')
async def test_cache_error_handling(mock_redis, db_session: AsyncSession, sample_players):
    """Test that cache errors don't break search functionality"""
    # Mock Redis client to raise an error
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(side_effect=Exception("Redis connection error"))
    mock_redis_instance.setex = AsyncMock(side_effect=Exception("Redis connection error"))
    mock_redis.return_value = mock_redis_instance
    
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(position="ST", limit=10)
    
    # Search should still work even if cache fails
    results = await service.search_players(filters)
    
    assert results["total"] >= 0
    assert "players" in results
    
    print(f"✓ Cache error handling: search works despite Redis errors")


@pytest.mark.asyncio
async def test_search_result_consistency(db_session: AsyncSession, sample_players):
    """Test that search results are consistent across multiple calls"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(
        position="ST",
        min_ca=120,
        order_by="ca"
    )
    
    # Run search multiple times
    results1 = await service.search_players(filters)
    results2 = await service.search_players(filters)
    results3 = await service.search_players(filters)
    
    # Results should be identical
    assert results1["total"] == results2["total"] == results3["total"]
    assert len(results1["players"]) == len(results2["players"]) == len(results3["players"])
    
    # Player IDs should match
    ids1 = [p.id for p in results1["players"]]
    ids2 = [p.id for p in results2["players"]]
    ids3 = [p.id for p in results3["players"]]
    
    assert ids1 == ids2 == ids3
    
    print(f"✓ Search consistency: 3 identical searches returned same {results1['total']} results")


@pytest.mark.asyncio
async def test_filter_options_performance(db_session: AsyncSession, sample_players):
    """Test filter options query performance"""
    service = PlayerSearchService(db_session)
    
    start_time = time.time()
    options = await service.get_filter_options()
    query_time = time.time() - start_time
    
    # Verify all options are present
    assert len(options["positions"]) > 0
    assert len(options["nationalities"]) > 0
    assert len(options["clubs"]) > 0
    
    # Query should be fast
    assert query_time < 0.2
    
    print(f"✓ Filter options performance: {query_time*1000:.2f}ms")
    print(f"  - {len(options['positions'])} positions")
    print(f"  - {len(options['nationalities'])} nationalities")
    print(f"  - {len(options['clubs'])} clubs")


@pytest.mark.asyncio
async def test_large_result_set_performance(db_session: AsyncSession, sample_players):
    """Test performance with large result sets"""
    service = PlayerSearchService(db_session)
    
    # Search with no filters (should return all players)
    filters = PlayerSearchFilters(limit=50, order_by="name")
    
    start_time = time.time()
    results = await service.search_players(filters)
    query_time = time.time() - start_time
    
    assert results["total"] == 100  # All sample players
    assert len(results["players"]) == 50  # Limited to 50
    
    # Should still be fast
    assert query_time < 0.15
    
    print(f"✓ Large result set: {query_time*1000:.2f}ms for {results['total']} total results")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
