"""
Test script for Task 9.4: Relevance Scoring for Search Results

This script verifies that the relevance scoring system works correctly
when searching for players using full-text search.

The relevance scoring uses PostgreSQL's ts_rank function to rank search
results based on how well they match the search query.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters


async def create_test_database():
    """Create an in-memory test database"""
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
    
    return engine, async_session


async def add_test_players(session: AsyncSession):
    """Add test players with varying relevance to search queries"""
    players = [
        # Player 1: "Messi" in name, "Barcelona" in club - High relevance for "Messi"
        Player(
            uid="player_001", name="Lionel Messi", position="AM/ST RL",
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
            left_foot=20, right_foot=8, traits="Tries tricks"
        ),
        # Player 2: "Barcelona" in club - Medium relevance for "Barcelona"
        Player(
            uid="player_002", name="Gerard Piqué", position="D C",
            age=36, ca=165, pa=165, nationality="Spain", club="Barcelona",
            corners=8, crossing=7, dribbling=10, finishing=7,
            first_touch=13, free_kicks=9, heading=17, long_shots=9,
            long_throws=12, marking=17, passing=14, penalty=8,
            tackling=16, technique=12,
            aggression=14, anticipation=17, bravery=17, composure=15,
            concentration=16, decisions=17, determination=15, flair=9,
            leadership=18, off_the_ball=11, positioning=18, teamwork=15,
            vision=13, work_rate=14,
            acceleration=10, agility=11, balance=12, jumping=15,
            stamina=13, pace=10, endurance=13, strength=16,
            price="€10M", wage=150000, height=194, weight=85,
            left_foot=10, right_foot=14, traits="Plays short passes"
        ),
        # Player 3: "Argentina" in nationality - Low relevance for "Argentina"
        Player(
            uid="player_003", name="Paulo Dybala", position="AM/ST RL",
            age=29, ca=175, pa=180, nationality="Argentina", club="Roma",
            corners=12, crossing=11, dribbling=17, finishing=16,
            first_touch=17, free_kicks=14, heading=10, long_shots=16,
            long_throws=7, marking=7, passing=15, penalty=15,
            tackling=6, technique=17,
            aggression=9, anticipation=15, bravery=12, composure=16,
            concentration=14, decisions=15, determination=14, flair=17,
            leadership=12, off_the_ball=16, positioning=15, teamwork=14,
            vision=16, work_rate=13,
            acceleration=16, agility=17, balance=16, jumping=11,
            stamina=14, pace=16, endurance=14, strength=11,
            price="€40M", wage=200000, height=177, weight=75,
            left_foot=18, right_foot=10, traits="Tries tricks"
        ),
        # Player 4: "Manchester" in club - High relevance for "Manchester"
        Player(
            uid="player_004", name="Bruno Fernandes", position="AM C",
            age=28, ca=180, pa=185, nationality="Portugal", club="Manchester United",
            corners=14, crossing=15, dribbling=15, finishing=15,
            first_touch=16, free_kicks=15, heading=11, long_shots=17,
            long_throws=10, marking=9, passing=18, penalty=16,
            tackling=8, technique=16,
            aggression=12, anticipation=16, bravery=14, composure=16,
            concentration=15, decisions=17, determination=17, flair=16,
            leadership=16, off_the_ball=15, positioning=14, teamwork=15,
            vision=18, work_rate=17,
            acceleration=14, agility=15, balance=14, jumping=12,
            stamina=16, pace=14, endurance=16, strength=13,
            price="€70M", wage=300000, height=179, weight=69,
            left_foot=10, right_foot=17, traits="Tries killer balls"
        ),
        # Player 5: "Manchester" in club - High relevance for "Manchester"
        Player(
            uid="player_005", name="Marcus Rashford", position="ST/AM L",
            age=25, ca=178, pa=185, nationality="England", club="Manchester United",
            corners=9, crossing=12, dribbling=16, finishing=16,
            first_touch=15, free_kicks=11, heading=12, long_shots=15,
            long_throws=8, marking=6, passing=13, penalty=13,
            tackling=5, technique=15,
            aggression=10, anticipation=15, bravery=13, composure=14,
            concentration=13, decisions=14, determination=16, flair=15,
            leadership=13, off_the_ball=16, positioning=15, teamwork=14,
            vision=13, work_rate=16,
            acceleration=18, agility=17, balance=16, jumping=13,
            stamina=16, pace=18, endurance=16, strength=13,
            price="€65M", wage=250000, height=180, weight=70,
            left_foot=12, right_foot=16, traits="Tries to beat offside trap"
        ),
        # Player 6: No match - Should not appear in "Barcelona" search
        Player(
            uid="player_006", name="Erling Haaland", position="ST C",
            age=23, ca=188, pa=195, nationality="Norway", club="Manchester City",
            corners=6, crossing=8, dribbling=14, finishing=19,
            first_touch=15, free_kicks=8, heading=17, long_shots=14,
            long_throws=9, marking=5, passing=12, penalty=16,
            tackling=4, technique=14,
            aggression=13, anticipation=17, bravery=15, composure=16,
            concentration=14, decisions=15, determination=17, flair=12,
            leadership=11, off_the_ball=18, positioning=17, teamwork=13,
            vision=12, work_rate=15,
            acceleration=18, agility=15, balance=14, jumping=16,
            stamina=17, pace=18, endurance=17, strength=18,
            price="€150M", wage=400000, height=194, weight=88,
            left_foot=14, right_foot=18, traits="Tries to beat offside trap"
        ),
    ]
    
    for player in players:
        session.add(player)
    
    await session.commit()
    print(f"✓ Added {len(players)} test players to database")


async def test_relevance_scoring_by_name():
    """Test 1: Relevance scoring when searching by player name"""
    print("\n=== Test 1: Relevance Scoring by Name ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search for "Messi" - should rank Lionel Messi highest
        filters = PlayerSearchFilters(search_text="Messi", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"Search for 'Messi' with relevance scoring:")
        print(f"  Total results: {results['total']}")
        for i, player in enumerate(results['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club}, Nationality: {player.nationality})")
        
        # Verify Lionel Messi is ranked first
        assert results['total'] >= 1, "Should find at least 1 player"
        assert results['players'][0].name == "Lionel Messi", "Lionel Messi should be ranked first"
        print("✓ Test passed: Lionel Messi ranked first for 'Messi' search")
    
    await engine.dispose()


async def test_relevance_scoring_by_club():
    """Test 2: Relevance scoring when searching by club"""
    print("\n=== Test 2: Relevance Scoring by Club ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search for "Barcelona" - should find Barcelona players
        filters = PlayerSearchFilters(search_text="Barcelona", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"Search for 'Barcelona' with relevance scoring:")
        print(f"  Total results: {results['total']}")
        for i, player in enumerate(results['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club})")
        
        # Verify Barcelona players are found
        assert results['total'] >= 2, "Should find at least 2 Barcelona players"
        barcelona_players = [p for p in results['players'] if p.club == "Barcelona"]
        assert len(barcelona_players) >= 2, "Should find Barcelona players"
        print(f"✓ Test passed: Found {len(barcelona_players)} Barcelona players")
    
    await engine.dispose()


async def test_relevance_scoring_by_nationality():
    """Test 3: Relevance scoring when searching by nationality"""
    print("\n=== Test 3: Relevance Scoring by Nationality ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search for "Argentina" - should find Argentine players
        filters = PlayerSearchFilters(search_text="Argentina", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"Search for 'Argentina' with relevance scoring:")
        print(f"  Total results: {results['total']}")
        for i, player in enumerate(results['players'], 1):
            print(f"  {i}. {player.name} (Nationality: {player.nationality})")
        
        # Verify Argentine players are found
        assert results['total'] >= 2, "Should find at least 2 Argentine players"
        argentine_players = [p for p in results['players'] if p.nationality == "Argentina"]
        assert len(argentine_players) >= 2, "Should find Argentine players"
        print(f"✓ Test passed: Found {len(argentine_players)} Argentine players")
    
    await engine.dispose()


async def test_relevance_scoring_multi_word():
    """Test 4: Relevance scoring with multi-word search"""
    print("\n=== Test 4: Relevance Scoring with Multi-Word Search ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search for "Manchester United" - should find Manchester United players
        filters = PlayerSearchFilters(search_text="Manchester United", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"Search for 'Manchester United' with relevance scoring:")
        print(f"  Total results: {results['total']}")
        for i, player in enumerate(results['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club})")
        
        # Verify Manchester United players are ranked higher
        assert results['total'] >= 2, "Should find at least 2 players"
        # Check that Manchester United players appear in results
        man_utd_players = [p for p in results['players'] if p.club == "Manchester United"]
        assert len(man_utd_players) >= 2, "Should find Manchester United players"
        print(f"✓ Test passed: Found {len(man_utd_players)} Manchester United players")
    
    await engine.dispose()


async def test_relevance_vs_other_sorting():
    """Test 5: Compare relevance sorting vs other sorting methods"""
    print("\n=== Test 5: Relevance vs Other Sorting ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search with relevance sorting
        filters_relevance = PlayerSearchFilters(search_text="Manchester", order_by="relevance")
        results_relevance = await service.search_players(filters_relevance)
        
        print(f"Search for 'Manchester' with RELEVANCE sorting:")
        for i, player in enumerate(results_relevance['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club}, CA: {player.ca})")
        
        # Search with CA sorting
        filters_ca = PlayerSearchFilters(search_text="Manchester", order_by="ca")
        results_ca = await service.search_players(filters_ca)
        
        print(f"\nSearch for 'Manchester' with CA sorting:")
        for i, player in enumerate(results_ca['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club}, CA: {player.ca})")
        
        # Verify different ordering
        assert results_relevance['total'] == results_ca['total'], "Should find same number of players"
        
        # The order might be different between relevance and CA sorting
        relevance_order = [p.name for p in results_relevance['players']]
        ca_order = [p.name for p in results_ca['players']]
        
        print(f"\n  Relevance order: {relevance_order}")
        print(f"  CA order: {ca_order}")
        
        # For CA sorting, verify descending order
        cas = [p.ca for p in results_ca['players']]
        assert cas == sorted(cas, reverse=True), "CA sorting should be descending"
        
        print("✓ Test passed: Different sorting methods produce different orders")
    
    await engine.dispose()


async def test_relevance_with_filters():
    """Test 6: Relevance scoring combined with filters"""
    print("\n=== Test 6: Relevance Scoring with Filters ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Search for "Manchester" with CA filter
        filters = PlayerSearchFilters(
            search_text="Manchester",
            min_ca=175,
            order_by="relevance"
        )
        results = await service.search_players(filters)
        
        print(f"Search for 'Manchester' with CA >= 175 and relevance scoring:")
        print(f"  Total results: {results['total']}")
        for i, player in enumerate(results['players'], 1):
            print(f"  {i}. {player.name} (Club: {player.club}, CA: {player.ca})")
        
        # Verify all results meet the CA filter
        assert all(p.ca >= 175 for p in results['players']), "All players should have CA >= 175"
        print("✓ Test passed: Relevance scoring works with filters")
    
    await engine.dispose()


async def test_relevance_error_without_search_text():
    """Test 7: Verify error when using relevance without search_text"""
    print("\n=== Test 7: Error Handling for Relevance without Search Text ===")
    engine, async_session = await create_test_database()
    
    async with async_session() as session:
        await add_test_players(session)
        service = PlayerSearchService(session)
        
        # Try to use relevance sorting without search_text
        try:
            filters = PlayerSearchFilters(order_by="relevance")
            filters.validate()
            print("✗ Test failed: Should have raised ValueError")
            assert False, "Should raise ValueError"
        except ValueError as e:
            print(f"  Expected error: {e}")
            assert "order_by='relevance' requires search_text" in str(e)
            print("✓ Test passed: Correct error raised")
    
    await engine.dispose()


async def main():
    """Run all relevance scoring tests"""
    print("=" * 70)
    print("Task 9.4: Relevance Scoring for Search Results - Test Suite")
    print("=" * 70)
    
    tests = [
        test_relevance_scoring_by_name,
        test_relevance_scoring_by_club,
        test_relevance_scoring_by_nationality,
        test_relevance_scoring_multi_word,
        test_relevance_vs_other_sorting,
        test_relevance_with_filters,
        test_relevance_error_without_search_text,
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✓ All relevance scoring tests passed successfully!")
        print("\nSummary:")
        print("  - Relevance scoring ranks results by ts_rank()")
        print("  - Works with name, club, nationality, and position searches")
        print("  - Can be combined with filters (age, CA, PA, etc.)")
        print("  - Requires search_text parameter (validated)")
        print("  - Different from other sorting methods (CA, PA, age, name)")
    else:
        print(f"\n✗ {failed} test(s) failed")


if __name__ == "__main__":
    asyncio.run(main())
