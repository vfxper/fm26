"""
Manual test script for Player Search Service

This script can be run directly to test the player search functionality.
Run with: python test_player_search_manual.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters


async def create_test_database():
    """Create an in-memory test database with sample players"""
    # Create engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    return engine, async_session


async def add_sample_players(session: AsyncSession):
    """Add sample players to the database"""
    players = [
        Player(
            uid="messi_001", name="Lionel Messi", position="AM/ST RL",
            age=35, ca=195, pa=200, nationality="Argentina", club="Barcelona",
            corners=15, crossing=16, dribbling=20, finishing=19,
            first_touch=20, free_kicks=18, heading=12, long_shots=18,
            long_throws=8, marking=8, passing=19, penalty=17,
            tackling=7, technique=20,
            aggression=10, anticipation=18, bravery=14, composure=19,
            concentration=17, decisions=19, determination=18, flair=20,
            leadership=16, off_the_ball=19, positioning=18, teamwork=17,
            vision=20, work_rate=16,
            acceleration=16, agility=18, balance=19, jumping=11,
            stamina=15, pace=16, endurance=15, strength=12,
            price="€100M", wage=500000, height=170, weight=72,
            left_foot=20, right_foot=8,
            traits="Tries tricks, Cuts inside from right"
        ),
        Player(
            uid="ronaldo_001", name="Cristiano Ronaldo", position="ST/AM RL",
            age=38, ca=190, pa=195, nationality="Portugal", club="Manchester United",
            corners=12, crossing=14, dribbling=18, finishing=19,
            first_touch=18, free_kicks=16, heading=19, long_shots=18,
            long_throws=10, marking=7, passing=16, penalty=18,
            tackling=6, technique=18,
            aggression=12, anticipation=19, bravery=16, composure=18,
            concentration=17, decisions=18, determination=20, flair=18,
            leadership=19, off_the_ball=20, positioning=19, teamwork=15,
            vision=17, work_rate=18,
            acceleration=17, agility=16, balance=15, jumping=19,
            stamina=17, pace=17, endurance=17, strength=16,
            price="€80M", wage=450000, height=187, weight=84,
            left_foot=8, right_foot=20,
            traits="Tries long shots, Powerful header"
        ),
        Player(
            uid="prospect_001", name="João Silva", position="ST C",
            age=18, ca=120, pa=180, nationality="Brazil", club="Santos",
            corners=8, crossing=9, dribbling=14, finishing=13,
            first_touch=13, free_kicks=7, heading=10, long_shots=11,
            long_throws=6, marking=6, passing=11, penalty=10,
            tackling=5, technique=13,
            aggression=9, anticipation=12, bravery=11, composure=11,
            concentration=10, decisions=11, determination=15, flair=14,
            leadership=8, off_the_ball=13, positioning=12, teamwork=12,
            vision=12, work_rate=14,
            acceleration=16, agility=15, balance=14, jumping=12,
            stamina=14, pace=16, endurance=14, strength=10,
            price="€5M", wage=10000, height=178, weight=73,
            left_foot=12, right_foot=15,
            traits="Tries to beat offside trap"
        ),
    ]
    
    for player in players:
        session.add(player)
    
    await session.commit()
    print(f"✓ Added {len(players)} sample players to database")


async def test_search_by_name():
    """Test 1: Search by player name"""
    print("\n=== Test 1: Search by Name ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(search_text="Messi")
        results = await service.search_players(filters)
        
        print(f"Search for 'Messi': Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (CA: {player.ca}, Club: {player.club})")
        
        assert results['total'] == 1, "Should find exactly 1 player"
        assert results['players'][0].name == "Lionel Messi", "Should find Messi"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_search_by_position():
    """Test 2: Search by position"""
    print("\n=== Test 2: Search by Position ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(position="ST")
        results = await service.search_players(filters)
        
        print(f"Search for position 'ST': Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} ({player.position})")
        
        assert results['total'] == 3, "Should find 3 strikers"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_search_by_age_range():
    """Test 3: Search by age range"""
    print("\n=== Test 3: Search by Age Range ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(min_age=18, max_age=25)
        results = await service.search_players(filters)
        
        print(f"Search for age 18-25: Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (Age: {player.age})")
        
        assert results['total'] == 1, "Should find 1 young player"
        assert results['players'][0].name == "João Silva", "Should find João Silva"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_search_by_ca_range():
    """Test 4: Search by Current Ability range"""
    print("\n=== Test 4: Search by CA Range ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(min_ca=185, order_by="ca")
        results = await service.search_players(filters)
        
        print(f"Search for CA >= 185: Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (CA: {player.ca})")
        
        assert results['total'] == 2, "Should find 2 high CA players"
        assert all(p.ca >= 185 for p in results['players']), "All should have CA >= 185"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_search_by_nationality():
    """Test 5: Search by nationality"""
    print("\n=== Test 5: Search by Nationality ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(nationality="Portugal")
        results = await service.search_players(filters)
        
        print(f"Search for nationality 'Portugal': Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (Nationality: {player.nationality})")
        
        assert results['total'] == 1, "Should find 1 Portuguese player"
        assert results['players'][0].name == "Cristiano Ronaldo", "Should find Ronaldo"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_search_by_club():
    """Test 6: Search by club"""
    print("\n=== Test 6: Search by Club ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(club="Barcelona")
        results = await service.search_players(filters)
        
        print(f"Search for club 'Barcelona': Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (Club: {player.club})")
        
        assert results['total'] == 1, "Should find 1 Barcelona player"
        assert results['players'][0].name == "Lionel Messi", "Should find Messi"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_combined_filters():
    """Test 7: Combined filters"""
    print("\n=== Test 7: Combined Filters ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        filters = PlayerSearchFilters(
            position="ST",
            min_ca=180,
            min_age=30
        )
        results = await service.search_players(filters)
        
        print(f"Search for ST, CA>=180, Age>=30: Found {results['total']} player(s)")
        for player in results['players']:
            print(f"  - {player.name} (Position: {player.position}, CA: {player.ca}, Age: {player.age})")
        
        assert results['total'] == 2, "Should find 2 players (Messi and Ronaldo)"
        print("✓ Test passed")
    
    await engine.dispose()


async def test_pagination():
    """Test 8: Pagination"""
    print("\n=== Test 8: Pagination ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_sample_players(session)
        service = PlayerSearchService(session)
        
        # First page
        filters = PlayerSearchFilters(limit=2, offset=0, order_by="name")
        results = await service.search_players(filters)
        
        print(f"Page 1 (limit=2, offset=0): Found {len(results['players'])} player(s)")
        print(f"  Total: {results['total']}, Has more: {results['has_more']}")
        for player in results['players']:
            print(f"  - {player.name}")
        
        assert len(results['players']) == 2, "Should return 2 players"
        assert results['total'] == 3, "Total should be 3"
        assert results['has_more'] is True, "Should have more results"
        
        # Second page
        filters = PlayerSearchFilters(limit=2, offset=2, order_by="name")
        results = await service.search_players(filters)
        
        print(f"Page 2 (limit=2, offset=2): Found {len(results['players'])} player(s)")
        print(f"  Total: {results['total']}, Has more: {results['has_more']}")
        for player in results['players']:
            print(f"  - {player.name}")
        
        assert len(results['players']) == 1, "Should return 1 player"
        assert results['has_more'] is False, "Should not have more results"
        print("✓ Test passed")
    
    await engine.dispose()


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Player Search Service - Manual Test Suite")
    print("=" * 60)
    
    tests = [
        test_search_by_name,
        test_search_by_position,
        test_search_by_age_range,
        test_search_by_ca_range,
        test_search_by_nationality,
        test_search_by_club,
        test_combined_filters,
        test_pagination,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All tests passed successfully!")
    else:
        print(f"\n✗ {failed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())
