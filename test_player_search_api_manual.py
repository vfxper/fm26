"""
Manual test script for Player Search API

This script tests the player search API endpoints manually without requiring
a full test database setup. It's useful for quick verification.

Usage:
    python test_player_search_api_manual.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters
from app.schemas.player import PlayerSearchRequest, PlayerSearchResponse, PlayerResponse


async def test_search_service():
    """Test the PlayerSearchService directly"""
    
    print("=" * 80)
    print("Testing Player Search Service")
    print("=" * 80)
    
    # Create database connection
    DATABASE_URL = "postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        # Create search service
        search_service = PlayerSearchService(session)
        
        # Test 1: Get filter options
        print("\n1. Testing get_filter_options()...")
        try:
            options = await search_service.get_filter_options()
            print(f"   ✓ Found {len(options['positions'])} positions")
            print(f"   ✓ Found {len(options['nationalities'])} nationalities")
            print(f"   ✓ Found {len(options['clubs'])} clubs")
            print(f"   ✓ Age range: {options['age_range']['min']} - {options['age_range']['max']}")
            print(f"   ✓ CA range: {options['ca_range']['min']} - {options['ca_range']['max']}")
            print(f"   ✓ PA range: {options['pa_range']['min']} - {options['pa_range']['max']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 2: Search with no filters
        print("\n2. Testing search with no filters...")
        try:
            filters = PlayerSearchFilters(limit=10)
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} total players")
            print(f"   ✓ Returned {len(results['players'])} players")
            if results['players']:
                player = results['players'][0]
                print(f"   ✓ First player: {player.name} (CA: {player.ca}, Age: {player.age})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 3: Search with text search
        print("\n3. Testing search with text search...")
        try:
            filters = PlayerSearchFilters(
                search_text="Messi",
                order_by="relevance",
                limit=5
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} players matching 'Messi'")
            for player in results['players']:
                print(f"   ✓ {player.name} - {player.club} (CA: {player.ca})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 4: Search with position filter
        print("\n4. Testing search with position filter...")
        try:
            filters = PlayerSearchFilters(
                position="ST",
                order_by="ca",
                limit=5
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} strikers")
            for player in results['players'][:5]:
                print(f"   ✓ {player.name} - {player.position} (CA: {player.ca})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 5: Search with age filter
        print("\n5. Testing search with age filter...")
        try:
            filters = PlayerSearchFilters(
                min_age=18,
                max_age=21,
                order_by="pa",
                limit=5
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} young players (18-21)")
            for player in results['players'][:5]:
                print(f"   ✓ {player.name} - Age {player.age} (PA: {player.pa})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 6: Search with CA filter
        print("\n6. Testing search with CA filter...")
        try:
            filters = PlayerSearchFilters(
                min_ca=180,
                order_by="ca",
                limit=5
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} world-class players (CA >= 180)")
            for player in results['players'][:5]:
                print(f"   ✓ {player.name} - {player.club} (CA: {player.ca})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 7: Search with multiple filters
        print("\n7. Testing search with multiple filters...")
        try:
            filters = PlayerSearchFilters(
                position="ST",
                min_age=20,
                max_age=25,
                min_ca=170,
                order_by="ca",
                limit=5
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Found {results['total']} young strikers (20-25, CA >= 170)")
            for player in results['players'][:5]:
                print(f"   ✓ {player.name} - Age {player.age}, {player.position} (CA: {player.ca})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 8: Search with pagination
        print("\n8. Testing search with pagination...")
        try:
            # First page
            filters = PlayerSearchFilters(
                position="ST",
                limit=10,
                offset=0,
                order_by="ca"
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Page 1: {len(results['players'])} players (total: {results['total']})")
            print(f"   ✓ Has more: {results['has_more']}")
            
            # Second page
            filters = PlayerSearchFilters(
                position="ST",
                limit=10,
                offset=10,
                order_by="ca"
            )
            results = await search_service.search_players(filters)
            print(f"   ✓ Page 2: {len(results['players'])} players")
            print(f"   ✓ Has more: {results['has_more']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 9: Test Pydantic schema validation
        print("\n9. Testing Pydantic schema validation...")
        try:
            # Get a player
            filters = PlayerSearchFilters(limit=1)
            results = await search_service.search_players(filters)
            
            if results['players']:
                player = results['players'][0]
                
                # Convert to Pydantic model
                player_response = PlayerResponse.model_validate(player)
                print(f"   ✓ Successfully validated player: {player_response.name}")
                print(f"   ✓ Player has {len(player_response.model_dump())} attributes")
                
                # Test PlayerSearchResponse
                search_response = PlayerSearchResponse(
                    players=[player_response],
                    total=results['total'],
                    limit=results['limit'],
                    offset=results['offset'],
                    has_more=results['has_more']
                )
                print(f"   ✓ Successfully created PlayerSearchResponse")
                print(f"   ✓ Response has {search_response.total} total players")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 10: Test invalid filters
        print("\n10. Testing invalid filter validation...")
        try:
            # Invalid age range
            filters = PlayerSearchFilters(min_age=30, max_age=20)
            filters.validate()
            print(f"   ✗ Should have raised ValueError for invalid age range")
        except ValueError as e:
            print(f"   ✓ Correctly raised ValueError: {e}")
        except Exception as e:
            print(f"   ✗ Unexpected error: {e}")
        
        try:
            # Invalid CA range
            filters = PlayerSearchFilters(min_ca=200, max_ca=100)
            filters.validate()
            print(f"   ✗ Should have raised ValueError for invalid CA range")
        except ValueError as e:
            print(f"   ✓ Correctly raised ValueError: {e}")
        except Exception as e:
            print(f"   ✗ Unexpected error: {e}")
        
        try:
            # Relevance without search_text
            filters = PlayerSearchFilters(order_by="relevance")
            filters.validate()
            print(f"   ✗ Should have raised ValueError for relevance without search_text")
        except ValueError as e:
            print(f"   ✓ Correctly raised ValueError: {e}")
        except Exception as e:
            print(f"   ✗ Unexpected error: {e}")
    
    await engine.dispose()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_search_service())
