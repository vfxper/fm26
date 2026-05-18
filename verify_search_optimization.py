"""
Verification script for player search performance optimizations

This script verifies that the optimizations implemented in Task 9.5 are working correctly.
"""

import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters


async def verify_optimizations():
    """Verify all performance optimizations"""
    
    print("=" * 80)
    print("Player Search Performance Optimization Verification")
    print("=" * 80)
    print()
    
    # Create database connection
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        service = PlayerSearchService(session)
        
        # Test 1: Cache key generation
        print("Test 1: Cache Key Generation")
        print("-" * 80)
        filters1 = PlayerSearchFilters(search_text="Messi", min_ca=150)
        filters2 = PlayerSearchFilters(search_text="Messi", min_ca=150)
        filters3 = PlayerSearchFilters(search_text="Ronaldo", min_ca=150)
        
        key1 = service._generate_cache_key(filters1)
        key2 = service._generate_cache_key(filters2)
        key3 = service._generate_cache_key(filters3)
        
        print(f"Key 1: {key1}")
        print(f"Key 2: {key2}")
        print(f"Key 3: {key3}")
        
        if key1 == key2:
            print("✓ Same filters generate same cache key")
        else:
            print("✗ ERROR: Same filters generate different cache keys")
        
        if key1 != key3:
            print("✓ Different filters generate different cache keys")
        else:
            print("✗ ERROR: Different filters generate same cache key")
        
        print()
        
        # Test 2: Optimized count query
        print("Test 2: Optimized Count Query Performance")
        print("-" * 80)
        
        filters = PlayerSearchFilters(position="ST", min_ca=100, max_ca=200)
        
        start_time = time.time()
        results = await service.search_players(filters)
        query_time = time.time() - start_time
        
        print(f"Query time: {query_time*1000:.2f}ms")
        print(f"Total results: {results['total']}")
        print(f"Returned: {len(results['players'])} players")
        
        if query_time < 1.0:  # Should be under 1 second
            print("✓ Query performance is acceptable")
        else:
            print("⚠ WARNING: Query took longer than expected")
        
        print()
        
        # Test 3: Filter options caching
        print("Test 3: Filter Options Performance")
        print("-" * 80)
        
        start_time = time.time()
        options = await service.get_filter_options()
        query_time = time.time() - start_time
        
        print(f"Query time: {query_time*1000:.2f}ms")
        print(f"Positions: {len(options['positions'])}")
        print(f"Nationalities: {len(options['nationalities'])}")
        print(f"Clubs: {len(options['clubs'])}")
        print(f"Age range: {options['age_range']['min']} - {options['age_range']['max']}")
        print(f"CA range: {options['ca_range']['min']} - {options['ca_range']['max']}")
        print(f"PA range: {options['pa_range']['min']} - {options['pa_range']['max']}")
        
        if query_time < 2.0:  # Should be under 2 seconds
            print("✓ Filter options query performance is acceptable")
        else:
            print("⚠ WARNING: Filter options query took longer than expected")
        
        print()
        
        # Test 4: Player serialization
        print("Test 4: Player Serialization")
        print("-" * 80)
        
        if results['players']:
            player = results['players'][0]
            serialized = service._serialize_player(player)
            
            print(f"Serialized player: {serialized['name']}")
            print(f"Fields: {len(serialized)}")
            
            required_fields = ['id', 'uid', 'name', 'position', 'age', 'ca', 'pa', 
                             'nationality', 'club', 'price', 'wage']
            
            missing_fields = [f for f in required_fields if f not in serialized]
            
            if not missing_fields:
                print("✓ All required fields are present in serialization")
            else:
                print(f"✗ ERROR: Missing fields: {missing_fields}")
        else:
            print("⚠ No players found to test serialization")
        
        print()
        
        # Test 5: Search consistency
        print("Test 5: Search Result Consistency")
        print("-" * 80)
        
        filters = PlayerSearchFilters(position="ST", min_ca=150, order_by="ca", limit=10)
        
        results1 = await service.search_players(filters)
        results2 = await service.search_players(filters)
        
        if results1['total'] == results2['total']:
            print(f"✓ Consistent total count: {results1['total']}")
        else:
            print(f"✗ ERROR: Inconsistent total count: {results1['total']} vs {results2['total']}")
        
        if len(results1['players']) == len(results2['players']):
            print(f"✓ Consistent result count: {len(results1['players'])}")
        else:
            print(f"✗ ERROR: Inconsistent result count")
        
        ids1 = [p.id for p in results1['players']]
        ids2 = [p.id for p in results2['players']]
        
        if ids1 == ids2:
            print("✓ Consistent player IDs and order")
        else:
            print("✗ ERROR: Inconsistent player IDs or order")
        
        print()
        
        # Test 6: Multiple filter combinations
        print("Test 6: Multiple Filter Combinations")
        print("-" * 80)
        
        test_cases = [
            PlayerSearchFilters(search_text="Messi"),
            PlayerSearchFilters(position="ST", min_ca=180),
            PlayerSearchFilters(nationality="Brazil", min_age=20, max_age=25),
            PlayerSearchFilters(club="Barcelona"),
            PlayerSearchFilters(min_pa=190, order_by="pa"),
        ]
        
        for i, filters in enumerate(test_cases, 1):
            start_time = time.time()
            results = await service.search_players(filters)
            query_time = time.time() - start_time
            
            print(f"Test case {i}: {query_time*1000:.2f}ms, {results['total']} results")
        
        print("✓ All filter combinations executed successfully")
        print()
        
        # Test 7: Pagination performance
        print("Test 7: Pagination Performance")
        print("-" * 80)
        
        page_times = []
        for page in range(3):
            filters = PlayerSearchFilters(
                limit=20,
                offset=page * 20,
                order_by="name"
            )
            
            start_time = time.time()
            results = await service.search_players(filters)
            query_time = time.time() - start_time
            page_times.append(query_time)
            
            print(f"Page {page + 1}: {query_time*1000:.2f}ms, {len(results['players'])} players")
        
        avg_time = sum(page_times) / len(page_times)
        print(f"Average page time: {avg_time*1000:.2f}ms")
        
        if avg_time < 1.0:
            print("✓ Pagination performance is acceptable")
        else:
            print("⚠ WARNING: Pagination is slower than expected")
        
        print()
    
    await engine.dispose()
    
    print("=" * 80)
    print("Verification Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(verify_optimizations())
