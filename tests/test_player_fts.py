"""
Test Full-Text Search on Player Model

Tests the GIN index and full-text search functionality for the Player model.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


@pytest.mark.asyncio
async def test_player_fts_index_exists(db_session: AsyncSession):
    """
    Test that the full-text search GIN index exists on the players table.
    
    **Validates: Task 2.16 - Create full-text search GIN index on players table**
    """
    # Query to check if the GIN index exists
    result = await db_session.execute(
        text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = 'players'
            AND indexname = 'idx_players_fts'
        """)
    )
    
    index_info = result.fetchone()
    
    # Assert index exists
    assert index_info is not None, "Full-text search index 'idx_players_fts' does not exist"
    
    # Assert it's a GIN index
    assert 'gin' in index_info[1].lower(), "Index is not a GIN index"
    
    # Assert it uses to_tsvector
    assert 'to_tsvector' in index_info[1].lower(), "Index does not use to_tsvector"
    
    print(f"✅ GIN index exists: {index_info[0]}")
    print(f"   Definition: {index_info[1]}")


@pytest.mark.asyncio
async def test_player_fts_search_by_name(db_session: AsyncSession):
    """
    Test full-text search by player name.
    
    **Validates: Task 2.16 - Full-text search functionality**
    """
    # Create test players
    player1 = Player(
        uid="test_fts_001",
        name="Lionel Messi",
        position="RW",
        age=36,
        ca=180,
        pa=180,
        nationality="Argentina",
        club="Inter Miami",
        # Technical attributes
        corners=15, crossing=16, dribbling=20, finishing=19, first_touch=20,
        free_kicks=18, heading=12, long_shots=17, long_throws=8, marking=8,
        passing=18, penalty=16, tackling=7, technique=20,
        # Mental attributes
        aggression=10, anticipation=18, bravery=14, composure=19, concentration=17,
        decisions=18, determination=17, flair=20, leadership=16, off_the_ball=18,
        positioning=17, teamwork=15, vision=19, work_rate=14,
        # Physical attributes
        acceleration=15, agility=18, balance=17, jumping=11, stamina=14,
        pace=15, endurance=14, strength=10,
        # Financial
        price="50M", wage=500000,
        # Physical stats
        height=170, weight=72, left_foot=20, right_foot=8
    )
    
    player2 = Player(
        uid="test_fts_002",
        name="Cristiano Ronaldo",
        position="ST",
        age=38,
        ca=175,
        pa=175,
        nationality="Portugal",
        club="Al Nassr",
        # Technical attributes
        corners=12, crossing=14, dribbling=17, finishing=19, first_touch=18,
        free_kicks=16, heading=19, long_shots=18, long_throws=10, marking=9,
        passing=15, penalty=18, tackling=8, technique=18,
        # Mental attributes
        aggression=13, anticipation=19, bravery=16, composure=18, concentration=17,
        decisions=17, determination=19, flair=17, leadership=18, off_the_ball=19,
        positioning=19, teamwork=14, vision=16, work_rate=17,
        # Physical attributes
        acceleration=16, agility=16, balance=15, jumping=19, stamina=17,
        pace=16, endurance=17, strength=16,
        # Financial
        price="40M", wage=450000,
        # Physical stats
        height=187, weight=84, left_foot=8, right_foot=19
    )
    
    db_session.add_all([player1, player2])
    await db_session.commit()
    
    # Search for "Messi"
    stmt = select(Player).where(
        Player.search_query_expression("Messi")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert Messi is found
    assert len(players) == 1, f"Expected 1 player, found {len(players)}"
    assert players[0].name == "Lionel Messi"
    
    print("✅ Full-text search by name works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_by_club(db_session: AsyncSession):
    """
    Test full-text search by club name.
    
    **Validates: Task 2.16 - Full-text search includes club field**
    """
    # Create test players
    player1 = Player(
        uid="test_fts_003",
        name="Marcus Rashford",
        position="LW",
        age=26,
        ca=160,
        pa=170,
        nationality="England",
        club="Manchester United",
        # Technical attributes
        corners=10, crossing=13, dribbling=16, finishing=16, first_touch=15,
        free_kicks=12, heading=13, long_shots=15, long_throws=8, marking=7,
        passing=14, penalty=14, tackling=8, technique=15,
        # Mental attributes
        aggression=12, anticipation=15, bravery=14, composure=15, concentration=14,
        decisions=14, determination=16, flair=15, leadership=13, off_the_ball=16,
        positioning=15, teamwork=14, vision=14, work_rate=15,
        # Physical attributes
        acceleration=18, agility=17, balance=16, jumping=14, stamina=16,
        pace=18, endurance=16, strength=13,
        # Financial
        price="80M", wage=300000,
        # Physical stats
        height=180, weight=70, left_foot=8, right_foot=17
    )
    
    db_session.add(player1)
    await db_session.commit()
    
    # Search for "Manchester United"
    stmt = select(Player).where(
        Player.search_query_expression("Manchester United")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert player is found
    assert len(players) >= 1, f"Expected at least 1 player, found {len(players)}"
    assert any(p.club == "Manchester United" for p in players)
    
    print("✅ Full-text search by club works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_by_nationality(db_session: AsyncSession):
    """
    Test full-text search by nationality.
    
    **Validates: Task 2.16 - Full-text search includes nationality field**
    """
    # Create test players
    player1 = Player(
        uid="test_fts_004",
        name="Kylian Mbappé",
        position="ST",
        age=25,
        ca=185,
        pa=195,
        nationality="France",
        club="Real Madrid",
        # Technical attributes
        corners=10, crossing=13, dribbling=19, finishing=18, first_touch=18,
        free_kicks=12, heading=14, long_shots=16, long_throws=8, marking=7,
        passing=16, penalty=15, tackling=7, technique=18,
        # Mental attributes
        aggression=11, anticipation=18, bravery=14, composure=17, concentration=16,
        decisions=17, determination=16, flair=18, leadership=14, off_the_ball=19,
        positioning=18, teamwork=15, vision=17, work_rate=15,
        # Physical attributes
        acceleration=20, agility=19, balance=18, jumping=15, stamina=17,
        pace=20, endurance=17, strength=14,
        # Financial
        price="180M", wage=800000,
        # Physical stats
        height=178, weight=73, left_foot=8, right_foot=19
    )
    
    db_session.add(player1)
    await db_session.commit()
    
    # Search for "France"
    stmt = select(Player).where(
        Player.search_query_expression("France")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert player is found
    assert len(players) >= 1, f"Expected at least 1 player, found {len(players)}"
    assert any(p.nationality == "France" for p in players)
    
    print("✅ Full-text search by nationality works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_by_position(db_session: AsyncSession):
    """
    Test full-text search by position.
    
    **Validates: Task 2.16 - Full-text search includes position field**
    """
    # Create test players
    player1 = Player(
        uid="test_fts_005",
        name="Virgil van Dijk",
        position="DC",
        age=32,
        ca=175,
        pa=175,
        nationality="Netherlands",
        club="Liverpool",
        # Technical attributes
        corners=8, crossing=10, dribbling=12, finishing=10, first_touch=14,
        free_kicks=10, heading=18, long_shots=11, long_throws=12, marking=19,
        passing=15, penalty=12, tackling=18, technique=14,
        # Mental attributes
        aggression=14, anticipation=19, bravery=18, composure=17, concentration=18,
        decisions=18, determination=17, flair=11, leadership=18, off_the_ball=14,
        positioning=19, teamwork=17, vision=15, work_rate=16,
        # Physical attributes
        acceleration=14, agility=13, balance=14, jumping=17, stamina=16,
        pace=14, endurance=16, strength=18,
        # Financial
        price="70M", wage=350000,
        # Physical stats
        height=193, weight=92, left_foot=12, right_foot=16
    )
    
    db_session.add(player1)
    await db_session.commit()
    
    # Search for "DC" (Defender Central)
    stmt = select(Player).where(
        Player.search_query_expression("DC")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert player is found
    assert len(players) >= 1, f"Expected at least 1 player, found {len(players)}"
    assert any("DC" in p.position for p in players)
    
    print("✅ Full-text search by position works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_with_relevance_ranking(db_session: AsyncSession):
    """
    Test full-text search with relevance ranking.
    
    **Validates: Task 2.16 - Relevance scoring for search results**
    """
    # Create test players with varying relevance
    player1 = Player(
        uid="test_fts_006",
        name="Ronaldo Nazário",
        position="ST",
        age=47,
        ca=100,
        pa=100,
        nationality="Brazil",
        club="Retired",
        # Technical attributes
        corners=10, crossing=12, dribbling=18, finishing=19, first_touch=18,
        free_kicks=14, heading=16, long_shots=17, long_throws=9, marking=8,
        passing=15, penalty=17, tackling=7, technique=18,
        # Mental attributes
        aggression=12, anticipation=18, bravery=15, composure=18, concentration=16,
        decisions=17, determination=17, flair=19, leadership=15, off_the_ball=19,
        positioning=18, teamwork=14, vision=16, work_rate=14,
        # Physical attributes
        acceleration=18, agility=17, balance=16, jumping=15, stamina=15,
        pace=18, endurance=15, strength=15,
        # Financial
        price="0", wage=0,
        # Physical stats
        height=183, weight=82, left_foot=10, right_foot=19
    )
    
    player2 = Player(
        uid="test_fts_007",
        name="Cristiano Ronaldo",
        position="ST",
        age=38,
        ca=175,
        pa=175,
        nationality="Portugal",
        club="Al Nassr",
        # Technical attributes
        corners=12, crossing=14, dribbling=17, finishing=19, first_touch=18,
        free_kicks=16, heading=19, long_shots=18, long_throws=10, marking=9,
        passing=15, penalty=18, tackling=8, technique=18,
        # Mental attributes
        aggression=13, anticipation=19, bravery=16, composure=18, concentration=17,
        decisions=17, determination=19, flair=17, leadership=18, off_the_ball=19,
        positioning=19, teamwork=14, vision=16, work_rate=17,
        # Physical attributes
        acceleration=16, agility=16, balance=15, jumping=19, stamina=17,
        pace=16, endurance=17, strength=16,
        # Financial
        price="40M", wage=450000,
        # Physical stats
        height=187, weight=84, left_foot=8, right_foot=19
    )
    
    db_session.add_all([player1, player2])
    await db_session.commit()
    
    # Search for "Ronaldo" with relevance ranking
    rank = Player.search_rank_expression("Ronaldo")
    stmt = select(Player, rank.label('rank')).where(
        Player.search_query_expression("Ronaldo")
    ).order_by(rank.desc())
    
    result = await db_session.execute(stmt)
    rows = result.all()
    
    # Assert both players are found
    assert len(rows) >= 2, f"Expected at least 2 players, found {len(rows)}"
    
    # Assert results are ordered by relevance (rank > 0)
    for row in rows:
        player, rank_value = row
        assert rank_value > 0, f"Rank should be > 0, got {rank_value}"
        print(f"   Player: {player.name}, Rank: {rank_value}")
    
    print("✅ Full-text search with relevance ranking works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_combined_fields(db_session: AsyncSession):
    """
    Test full-text search across multiple fields simultaneously.
    
    **Validates: Task 2.16 - Search across name, club, nationality, position**
    """
    # Create test player
    player1 = Player(
        uid="test_fts_008",
        name="Erling Haaland",
        position="ST",
        age=23,
        ca=185,
        pa=195,
        nationality="Norway",
        club="Manchester City",
        # Technical attributes
        corners=8, crossing=10, dribbling=15, finishing=20, first_touch=16,
        free_kicks=10, heading=18, long_shots=16, long_throws=9, marking=7,
        passing=13, penalty=16, tackling=7, technique=15,
        # Mental attributes
        aggression=13, anticipation=19, bravery=15, composure=17, concentration=16,
        decisions=16, determination=18, flair=14, leadership=13, off_the_ball=19,
        positioning=19, teamwork=15, vision=14, work_rate=16,
        # Physical attributes
        acceleration=19, agility=16, balance=15, jumping=17, stamina=17,
        pace=19, endurance=17, strength=18,
        # Financial
        price="150M", wage=600000,
        # Physical stats
        height=194, weight=88, left_foot=15, right_foot=18
    )
    
    db_session.add(player1)
    await db_session.commit()
    
    # Search for "Haaland Manchester" (name + club)
    stmt = select(Player).where(
        Player.search_query_expression("Haaland Manchester")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert player is found
    assert len(players) >= 1, f"Expected at least 1 player, found {len(players)}"
    assert any(p.name == "Erling Haaland" and "Manchester" in p.club for p in players)
    
    # Search for "Norway ST" (nationality + position)
    stmt = select(Player).where(
        Player.search_query_expression("Norway ST")
    )
    result = await db_session.execute(stmt)
    players = result.scalars().all()
    
    # Assert player is found
    assert len(players) >= 1, f"Expected at least 1 player, found {len(players)}"
    assert any(p.nationality == "Norway" and "ST" in p.position for p in players)
    
    print("✅ Full-text search across combined fields works correctly")


@pytest.mark.asyncio
async def test_player_fts_search_performance(db_session: AsyncSession):
    """
    Test that full-text search uses the GIN index (performance check).
    
    **Validates: Task 2.16 - Search performance optimization**
    """
    # Create multiple test players
    players = []
    for i in range(10):
        player = Player(
            uid=f"test_fts_perf_{i:03d}",
            name=f"Test Player {i}",
            position="ST" if i % 2 == 0 else "MF",
            age=20 + i,
            ca=100 + i * 5,
            pa=120 + i * 5,
            nationality="TestLand",
            club=f"Test Club {i % 3}",
            # Technical attributes
            corners=10, crossing=10, dribbling=10, finishing=10, first_touch=10,
            free_kicks=10, heading=10, long_shots=10, long_throws=10, marking=10,
            passing=10, penalty=10, tackling=10, technique=10,
            # Mental attributes
            aggression=10, anticipation=10, bravery=10, composure=10, concentration=10,
            decisions=10, determination=10, flair=10, leadership=10, off_the_ball=10,
            positioning=10, teamwork=10, vision=10, work_rate=10,
            # Physical attributes
            acceleration=10, agility=10, balance=10, jumping=10, stamina=10,
            pace=10, endurance=10, strength=10,
            # Financial
            price="1M", wage=10000,
            # Physical stats
            height=180, weight=75, left_foot=10, right_foot=10
        )
        players.append(player)
    
    db_session.add_all(players)
    await db_session.commit()
    
    # Execute search with EXPLAIN ANALYZE to check index usage
    search_query = "Test Player"
    
    # Build the query
    stmt = select(Player).where(
        Player.search_query_expression(search_query)
    )
    
    # Get the compiled query
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    query_str = str(compiled)
    
    # Execute EXPLAIN ANALYZE
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query_str}"
    result = await db_session.execute(text(explain_query))
    explain_output = result.fetchall()
    
    # Check if GIN index is used
    explain_text = "\n".join([row[0] for row in explain_output])
    print("\n📊 Query Execution Plan:")
    print(explain_text)
    
    # Assert that the index is being used
    assert "idx_players_fts" in explain_text or "Bitmap Index Scan" in explain_text, \
        "GIN index is not being used for full-text search"
    
    print("\n✅ Full-text search uses GIN index for optimal performance")
