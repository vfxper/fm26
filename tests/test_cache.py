"""
Unit tests for Redis cache module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError

from app.core.cache import (
    get_connection_pool,
    get_redis_client,
    init_cache,
    close_cache,
    CacheKeys,
    _redis_client,
    _connection_pool,
)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch("app.core.cache.settings") as mock:
        mock.REDIS_URL = "redis://localhost:6379/0"
        mock.REDIS_MAX_CONNECTIONS = 50
        mock.REDIS_DECODE_RESPONSES = True
        yield mock


@pytest.fixture
def reset_globals():
    """Reset global Redis client and connection pool before each test"""
    import app.core.cache as cache_module
    cache_module._redis_client = None
    cache_module._connection_pool = None
    yield
    cache_module._redis_client = None
    cache_module._connection_pool = None


class TestConnectionPool:
    """Test Redis connection pool creation and management"""
    
    def test_get_connection_pool_creates_new_pool(self, mock_settings, reset_globals):
        """Test that get_connection_pool creates a new connection pool"""
        with patch("app.core.cache.ConnectionPool") as mock_pool_class:
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            
            pool = get_connection_pool()
            
            # Verify pool was created with correct parameters
            mock_pool_class.from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                max_connections=50,
                decode_responses=True,
            )
            assert pool == mock_pool_instance
    
    def test_get_connection_pool_returns_existing_pool(self, mock_settings, reset_globals):
        """Test that get_connection_pool returns existing pool on subsequent calls"""
        with patch("app.core.cache.ConnectionPool") as mock_pool_class:
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            
            # First call creates pool
            pool1 = get_connection_pool()
            # Second call returns same pool
            pool2 = get_connection_pool()
            
            # Verify pool was created only once
            assert mock_pool_class.from_url.call_count == 1
            assert pool1 == pool2


class TestRedisClient:
    """Test Redis client creation and management"""
    
    @pytest.mark.asyncio
    async def test_get_redis_client_creates_new_client(self, mock_settings, reset_globals):
        """Test that get_redis_client creates a new Redis client"""
        with patch("app.core.cache.ConnectionPool") as mock_pool_class, \
             patch("app.core.cache.Redis") as mock_redis_class:
            
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance
            
            client = await get_redis_client()
            
            # Verify client was created with connection pool
            mock_redis_class.assert_called_once_with(connection_pool=mock_pool_instance)
            assert client == mock_redis_instance
    
    @pytest.mark.asyncio
    async def test_get_redis_client_returns_existing_client(self, mock_settings, reset_globals):
        """Test that get_redis_client returns existing client on subsequent calls"""
        with patch("app.core.cache.ConnectionPool") as mock_pool_class, \
             patch("app.core.cache.Redis") as mock_redis_class:
            
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance
            
            # First call creates client
            client1 = await get_redis_client()
            # Second call returns same client
            client2 = await get_redis_client()
            
            # Verify client was created only once
            assert mock_redis_class.call_count == 1
            assert client1 == client2


class TestCacheInitialization:
    """Test cache initialization and shutdown"""
    
    @pytest.mark.asyncio
    async def test_init_cache_success(self, mock_settings, reset_globals):
        """Test successful cache initialization"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_redis
            
            # Should not raise exception
            await init_cache()
            
            # Verify ping was called
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_init_cache_connection_failure(self, mock_settings, reset_globals):
        """Test cache initialization with connection failure"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock_get_client.return_value = mock_redis
            
            # Should raise exception
            with pytest.raises(ConnectionError):
                await init_cache()
    
    @pytest.mark.asyncio
    async def test_init_cache_timeout(self, mock_settings, reset_globals):
        """Test cache initialization with timeout"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=TimeoutError("Connection timeout"))
            mock_get_client.return_value = mock_redis
            
            # Should raise exception
            with pytest.raises(TimeoutError):
                await init_cache()
    
    @pytest.mark.asyncio
    async def test_close_cache_with_active_connections(self, reset_globals):
        """Test closing cache with active client and pool"""
        import app.core.cache as cache_module
        
        # Set up mock client and pool
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.disconnect = AsyncMock()
        
        cache_module._redis_client = mock_client
        cache_module._connection_pool = mock_pool
        
        await close_cache()
        
        # Verify close and disconnect were called
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        
        # Verify globals were reset
        assert cache_module._redis_client is None
        assert cache_module._connection_pool is None
    
    @pytest.mark.asyncio
    async def test_close_cache_with_no_connections(self, reset_globals):
        """Test closing cache when no connections exist"""
        # Should not raise exception
        await close_cache()


class TestCacheKeys:
    """Test cache key generation"""
    
    def test_player_by_id_key(self):
        """Test player by ID cache key generation"""
        key = CacheKeys.player_by_id(123)
        assert key == "player:123"
    
    def test_players_by_club_key(self):
        """Test players by club cache key generation"""
        key = CacheKeys.players_by_club(456)
        assert key == "players:club:456"
    
    def test_career_by_id_key(self):
        """Test career by ID cache key generation"""
        key = CacheKeys.career_by_id(789)
        assert key == "career:789"
    
    def test_match_events_key(self):
        """Test match events cache key generation"""
        key = CacheKeys.match_events(101)
        assert key == "match:101:events"
    
    def test_cache_key_patterns(self):
        """Test cache key pattern constants"""
        assert CacheKeys.PLAYER_BY_ID == "player:{player_id}"
        assert CacheKeys.PLAYERS_BY_CLUB == "players:club:{club_id}"
        assert CacheKeys.CAREER_BY_ID == "career:{career_id}"
        assert CacheKeys.CAREER_BY_USER == "career:user:{user_id}"
        assert CacheKeys.MATCH_EVENTS == "match:{match_id}:events"
        assert CacheKeys.MATCH_STATE == "match:{match_id}:state"
        assert CacheKeys.MATCH_RESULT == "match:{match_id}:result"
        assert CacheKeys.USER_SESSION == "session:{user_id}"
        assert CacheKeys.RATE_LIMIT == "ratelimit:{user_id}:{endpoint}"


class TestRedisOperations:
    """Test actual Redis operations (integration-style tests)"""
    
    @pytest.mark.asyncio
    async def test_redis_set_and_get(self, mock_settings, reset_globals):
        """Test basic Redis set and get operations"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(return_value="test_value")
            mock_get_client.return_value = mock_redis
            
            client = await get_redis_client()
            
            # Test set
            result = await client.set("test_key", "test_value")
            assert result is True
            mock_redis.set.assert_called_once_with("test_key", "test_value")
            
            # Test get
            value = await client.get("test_key")
            assert value == "test_value"
            mock_redis.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_redis_set_with_expiry(self, mock_settings, reset_globals):
        """Test Redis set with expiration time"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_redis
            
            client = await get_redis_client()
            
            # Test setex (set with expiry)
            result = await client.setex("temp_key", 60, "temp_value")
            assert result is True
            mock_redis.setex.assert_called_once_with("temp_key", 60, "temp_value")
    
    @pytest.mark.asyncio
    async def test_redis_delete(self, mock_settings, reset_globals):
        """Test Redis delete operation"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.delete = AsyncMock(return_value=1)
            mock_get_client.return_value = mock_redis
            
            client = await get_redis_client()
            
            # Test delete
            result = await client.delete("test_key")
            assert result == 1
            mock_redis.delete.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_redis_exists(self, mock_settings, reset_globals):
        """Test Redis exists operation"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.exists = AsyncMock(return_value=1)
            mock_get_client.return_value = mock_redis
            
            client = await get_redis_client()
            
            # Test exists
            result = await client.exists("test_key")
            assert result == 1
            mock_redis.exists.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_redis_hash_operations(self, mock_settings, reset_globals):
        """Test Redis hash operations (hset, hget, hgetall)"""
        with patch("app.core.cache.get_redis_client") as mock_get_client:
            mock_redis = AsyncMock()
            mock_redis.hset = AsyncMock(return_value=1)
            mock_redis.hget = AsyncMock(return_value="field_value")
            mock_redis.hgetall = AsyncMock(return_value={"field1": "value1", "field2": "value2"})
            mock_get_client.return_value = mock_redis
            
            client = await get_redis_client()
            
            # Test hset
            result = await client.hset("hash_key", "field1", "value1")
            assert result == 1
            
            # Test hget
            value = await client.hget("hash_key", "field1")
            assert value == "field_value"
            
            # Test hgetall
            all_values = await client.hgetall("hash_key")
            assert all_values == {"field1": "value1", "field2": "value2"}


class TestConnectionPoolConfiguration:
    """Test connection pool configuration"""
    
    def test_connection_pool_uses_correct_url(self, reset_globals):
        """Test that connection pool uses URL from settings"""
        with patch("app.core.cache.settings") as mock_settings, \
             patch("app.core.cache.ConnectionPool") as mock_pool_class:
            
            mock_settings.REDIS_URL = "redis://custom-host:6380/5"
            mock_settings.REDIS_MAX_CONNECTIONS = 100
            mock_settings.REDIS_DECODE_RESPONSES = False
            
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            
            get_connection_pool()
            
            # Verify custom settings were used
            mock_pool_class.from_url.assert_called_once_with(
                "redis://custom-host:6380/5",
                max_connections=100,
                decode_responses=False,
            )
    
    def test_connection_pool_max_connections(self, reset_globals):
        """Test that connection pool respects max_connections setting"""
        with patch("app.core.cache.settings") as mock_settings, \
             patch("app.core.cache.ConnectionPool") as mock_pool_class:
            
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_MAX_CONNECTIONS = 25
            mock_settings.REDIS_DECODE_RESPONSES = True
            
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            
            get_connection_pool()
            
            # Verify max_connections was set correctly
            call_kwargs = mock_pool_class.from_url.call_args[1]
            assert call_kwargs["max_connections"] == 25
    
    def test_connection_pool_decode_responses(self, reset_globals):
        """Test that connection pool respects decode_responses setting"""
        with patch("app.core.cache.settings") as mock_settings, \
             patch("app.core.cache.ConnectionPool") as mock_pool_class:
            
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_MAX_CONNECTIONS = 50
            mock_settings.REDIS_DECODE_RESPONSES = False
            
            mock_pool_instance = MagicMock()
            mock_pool_class.from_url.return_value = mock_pool_instance
            
            get_connection_pool()
            
            # Verify decode_responses was set correctly
            call_kwargs = mock_pool_class.from_url.call_args[1]
            assert call_kwargs["decode_responses"] is False
