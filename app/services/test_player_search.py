"""
Unit tests for Player Search Service

Tests the search filters implementation for position, age, CA, PA, nationality, and club.
Task 9.2: Create search filters (position, age, CA, PA, nationality, club)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.services.player_search import PlayerSearchService, PlayerSearchFilters


# Test database setup
@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing"""
    # Use SQLite in-memory database for tests
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
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def sample_players(db_session: AsyncSession):
    """Create sample players for testing"""
    players = [
        # Lionel Messi - High CA/PA, Argentina, Barcelona
        Player(
            uid="messi_001",
            name="Lionel Messi",
            position="AM/ST RL",
            age=35,
            ca=195,
            pa=200,
            nationality="Argentina",
            club="Barcelona",
            # Technical attributes
            corners=15, crossing=16, dribbling=20, finishing=19,
            first_touch=20, free_kicks=18, heading=12, long_shots=18,
            long_throws=8, marking=8, passing=19, penalty=17,
            tackling=7, technique=20,
            # Mental attributes
            aggression=10, anticipation=18, bravery=14, composure=19,
            concentration=17, decisions=19, determination=18, flair=20,
            leadership=16, off_the_ball=19, positioning=18, teamwork=17,
            vision=20, work_rate=16,
            # Physical attributes
            acceleration=16, agility=18, balance=19, jumping=11,
            stamina=15, pace=16, endurance=15, strength=12,
            # Financial and physical stats
            price="€100M", wage=500000, height=170, weight=72,
            left_foot=20, right_foot=8,
            traits="Tries tricks, Cuts inside from right"
        ),
        # Cristiano Ronaldo - High CA/PA, Portugal, Manchester United
        Player(
            uid="ronaldo_001",
            name="Cristiano Ronaldo",
            position="ST/AM RL",
            age=38,
            ca=190,
            pa=195,
            nationality="Portugal",
            club="Manchester United",
            # Technical attributes
            corners=12, crossing=14, dribbling=18, finishing=19,
            first_touch=18, free_kicks=16, heading=19, long_shots=18,
            long_throws=10, marking=7, passing=16, penalty=18,
            tackling=6, technique=18,
            # Mental attributes
            aggression=12, anticipation=19, bravery=16, composure=18,
            concentration=17, decisions=18, determination=20, flair=18,
            leadership=19, off_the_ball=20, positioning=19, teamwork=15,
            vision=17, work_rate=18,
            # Physical attributes
            acceleration=17, agility=16, balance=15, jumping=19,
            stamina=17, pace=17, endurance=17, strength=16,
            # Financial and physical stats
            price="€80M", wage=450000, height=187, weight=84,
            left_foot=8, right_foot=20,
            traits="Tries long shots, Powerful header"
        ),
        # Young prospect - Low CA, High PA
        Player(
            uid="prospect_001",
            name="João Silva",
            position="ST C",
            age=18,
            ca=120,
            pa=180,
            nationality="Brazil",
            club="Santos",
            # Technical attributes
            corners=8, crossing=9, dribbling=14, finishing=13,
            first_touch=13, free_kicks=7, heading=10, long_shots=11,
            long_throws=6, marking=6, passing=11, penalty=10,
            tackling=5, technique=13,
            # Mental attributes
            aggression=9, anticipation=12, bravery=11, composure=11,
            concentration=10, decisions=11, determination=15, flair=14,
            leadership=8, off_the_ball=13, positioning=12, teamwork=12,
            vision=12, work_rate=14,
            # Physical attributes
            acceleration=16, agility=15, balance=14, jumping=12,
            stamina=14, pace=16, endurance=14, strength=10,
            # Financial and physical stats
            price="€5M", wage=10000, height=178, weight=73,
            left_foot=12, right_foot=15,
            traits="Tries to beat offside trap"
        ),
        # Midfielder - Medium CA/PA
        Player(
            uid="midfielder_001",
            name="Kevin De Bruyne",
            position="AM/M C",
            age=31,
            ca=185,
            pa=185,
            nationality="Belgium",
            club="Manchester City",
            # Technical attributes
            corners=17, crossing=19, dribbling=17, finishing=15,
            first_touch=18, free_kicks=16, heading=11, long_shots=18,
            long_throws=12, marking=10, passing=20, penalty=14,
            tackling=9, technique=18,
            # Mental attributes
            aggression=11, anticipation=17, bravery=13, composure=17,
            concentration=16, decisions=18, determination=16, flair=17,
            leadership=15, off_the_ball=16, positioning=15, teamwork=16,
            vision=20, work_rate=15,
            # Physical attributes
            acceleration=14, agility=15, balance=14, jumping=10,
            stamina=16, pace=14, endurance=16, strength=13,
            # Financial and physical stats
            price="€90M", wage=400000, height=181, weight=76,
            left_foot=10, right_foot=18,
            traits="Plays one-twos, Tries killer balls"
        ),
        # Defender - Lower CA
        Player(
            uid="defender_001",
            name="Virgil van Dijk",
            position="D C",
            age=32,
            ca=180,
            pa=180,
            nationality="Netherlands",
            club="Liverpool",
            # Technical attributes
            corners=6, crossing=8, dribbling=11, finishing=8,
            first_touch=14, free_kicks=9, heading=18, long_shots=10,
            long_throws=14, marking=19, passing=15, penalty=10,
            tackling=18, technique=13,
            # Mental attributes
            aggression=13, anticipation=18, bravery=18, composure=17,
            concentration=18, decisions=18, determination=17, flair=10,
            leadership=19, off_the_ball=12, positioning=19, teamwork=16,
            vision=14, work_rate=15,
            # Physical attributes
            acceleration=13, agility=12, balance=13, jumping=17,
            stamina=15, pace=13, endurance=15, strength=18,
            # Financial and physical stats
            price="€70M", wage=350000, height=193, weight=92,
            left_foot=10, right_foot=15,
            traits="Plays short simple passes"
        ),
    ]
    
    # Add players to database
    for player in players:
        db_session.add(player)
    
    await db_session.commit()
    
    return players


@pytest.mark.asyncio
async def test_search_by_name(db_session: AsyncSession, sample_players):
    """Test full-text search by player name"""
    service = PlayerSearchService(db_session)
    
    # Search for "Messi"
    filters = PlayerSearchFilters(search_text="Messi")
    results = await service.search_players(filters)
    
    assert results["total"] == 1
    assert len(results["players"]) == 1
    assert results["players"][0].name == "Lionel Messi"
    assert results["has_more"] is False


@pytest.mark.asyncio
async def test_search_by_position(db_session: AsyncSession, sample_players):
    """Test filtering by position"""
    service = PlayerSearchService(db_session)
    
    # Search for strikers (ST)
    filters = PlayerSearchFilters(position="ST")
    results = await service.search_players(filters)
    
    # Should find Messi, Ronaldo, and João Silva (all have ST in position)
    assert results["total"] == 3
    positions = [p.position for p in results["players"]]
    assert all("ST" in pos for pos in positions)


@pytest.mark.asyncio
async def test_search_by_age_range(db_session: AsyncSession, sample_players):
    """Test filtering by age range"""
    service = PlayerSearchService(db_session)
    
    # Search for young players (18-25)
    filters = PlayerSearchFilters(min_age=18, max_age=25)
    results = await service.search_players(filters)
    
    assert results["total"] == 1
    assert results["players"][0].name == "João Silva"
    assert results["players"][0].age == 18


@pytest.mark.asyncio
async def test_search_by_ca_range(db_session: AsyncSession, sample_players):
    """Test filtering by Current Ability range"""
    service = PlayerSearchService(db_session)
    
    # Search for high CA players (CA >= 185)
    filters = PlayerSearchFilters(min_ca=185, order_by="ca")
    results = await service.search_players(filters)
    
    assert results["total"] == 3  # Messi, Ronaldo, De Bruyne
    assert all(p.ca >= 185 for p in results["players"])
    # Check descending order
    cas = [p.ca for p in results["players"]]
    assert cas == sorted(cas, reverse=True)


@pytest.mark.asyncio
async def test_search_by_pa_range(db_session: AsyncSession, sample_players):
    """Test filtering by Potential Ability range"""
    service = PlayerSearchService(db_session)
    
    # Search for high potential players (PA >= 190)
    filters = PlayerSearchFilters(min_pa=190, order_by="pa")
    results = await service.search_players(filters)
    
    assert results["total"] == 2  # Messi, Ronaldo
    assert all(p.pa >= 190 for p in results["players"])


@pytest.mark.asyncio
async def test_search_by_nationality(db_session: AsyncSession, sample_players):
    """Test filtering by nationality"""
    service = PlayerSearchService(db_session)
    
    # Search for Portuguese players
    filters = PlayerSearchFilters(nationality="Portugal")
    results = await service.search_players(filters)
    
    assert results["total"] == 1
    assert results["players"][0].name == "Cristiano Ronaldo"
    assert results["players"][0].nationality == "Portugal"


@pytest.mark.asyncio
async def test_search_by_club(db_session: AsyncSession, sample_players):
    """Test filtering by club"""
    service = PlayerSearchService(db_session)
    
    # Search for Manchester United players
    filters = PlayerSearchFilters(club="Manchester United")
    results = await service.search_players(filters)
    
    assert results["total"] == 1
    assert results["players"][0].name == "Cristiano Ronaldo"
    assert results["players"][0].club == "Manchester United"


@pytest.mark.asyncio
async def test_combined_filters(db_session: AsyncSession, sample_players):
    """Test combining multiple filters"""
    service = PlayerSearchService(db_session)
    
    # Search for high CA strikers aged 30+
    filters = PlayerSearchFilters(
        position="ST",
        min_ca=180,
        min_age=30
    )
    results = await service.search_players(filters)
    
    # Should find Messi and Ronaldo
    assert results["total"] == 2
    names = [p.name for p in results["players"]]
    assert "Lionel Messi" in names
    assert "Cristiano Ronaldo" in names


@pytest.mark.asyncio
async def test_pagination(db_session: AsyncSession, sample_players):
    """Test pagination with limit and offset"""
    service = PlayerSearchService(db_session)
    
    # Get first 2 players
    filters = PlayerSearchFilters(limit=2, offset=0, order_by="name")
    results = await service.search_players(filters)
    
    assert len(results["players"]) == 2
    assert results["total"] == 5
    assert results["has_more"] is True
    
    # Get next 2 players
    filters = PlayerSearchFilters(limit=2, offset=2, order_by="name")
    results = await service.search_players(filters)
    
    assert len(results["players"]) == 2
    assert results["total"] == 5
    assert results["has_more"] is True
    
    # Get last player
    filters = PlayerSearchFilters(limit=2, offset=4, order_by="name")
    results = await service.search_players(filters)
    
    assert len(results["players"]) == 1
    assert results["total"] == 5
    assert results["has_more"] is False


@pytest.mark.asyncio
async def test_order_by_ca(db_session: AsyncSession, sample_players):
    """Test ordering by Current Ability"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(order_by="ca")
    results = await service.search_players(filters)
    
    # Check descending order
    cas = [p.ca for p in results["players"]]
    assert cas == sorted(cas, reverse=True)
    assert results["players"][0].name == "Lionel Messi"  # Highest CA


@pytest.mark.asyncio
async def test_order_by_age(db_session: AsyncSession, sample_players):
    """Test ordering by age"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(order_by="age")
    results = await service.search_players(filters)
    
    # Check ascending order
    ages = [p.age for p in results["players"]]
    assert ages == sorted(ages)
    assert results["players"][0].name == "João Silva"  # Youngest


@pytest.mark.asyncio
async def test_order_by_name(db_session: AsyncSession, sample_players):
    """Test ordering by name"""
    service = PlayerSearchService(db_session)
    
    filters = PlayerSearchFilters(order_by="name")
    results = await service.search_players(filters)
    
    # Check alphabetical order
    names = [p.name for p in results["players"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_filter_validation_age(db_session: AsyncSession):
    """Test filter validation for age"""
    service = PlayerSearchService(db_session)
    
    # Invalid min_age
    with pytest.raises(ValueError, match="min_age must be at least 15"):
        filters = PlayerSearchFilters(min_age=10)
        filters.validate()
    
    # Invalid max_age
    with pytest.raises(ValueError, match="max_age must be at most 50"):
        filters = PlayerSearchFilters(max_age=60)
        filters.validate()
    
    # min_age > max_age
    with pytest.raises(ValueError, match="min_age cannot be greater than max_age"):
        filters = PlayerSearchFilters(min_age=30, max_age=25)
        filters.validate()


@pytest.mark.asyncio
async def test_filter_validation_ca(db_session: AsyncSession):
    """Test filter validation for CA"""
    service = PlayerSearchService(db_session)
    
    # Invalid min_ca
    with pytest.raises(ValueError, match="min_ca must be between 1 and 200"):
        filters = PlayerSearchFilters(min_ca=0)
        filters.validate()
    
    # Invalid max_ca
    with pytest.raises(ValueError, match="max_ca must be between 1 and 200"):
        filters = PlayerSearchFilters(max_ca=250)
        filters.validate()
    
    # min_ca > max_ca
    with pytest.raises(ValueError, match="min_ca cannot be greater than max_ca"):
        filters = PlayerSearchFilters(min_ca=150, max_ca=100)
        filters.validate()


@pytest.mark.asyncio
async def test_filter_validation_pa(db_session: AsyncSession):
    """Test filter validation for PA"""
    service = PlayerSearchService(db_session)
    
    # Invalid min_pa
    with pytest.raises(ValueError, match="min_pa must be between -200 and 200"):
        filters = PlayerSearchFilters(min_pa=-250)
        filters.validate()
    
    # Invalid max_pa
    with pytest.raises(ValueError, match="max_pa must be between -200 and 200"):
        filters = PlayerSearchFilters(max_pa=250)
        filters.validate()
    
    # min_pa > max_pa
    with pytest.raises(ValueError, match="min_pa cannot be greater than max_pa"):
        filters = PlayerSearchFilters(min_pa=150, max_pa=100)
        filters.validate()


@pytest.mark.asyncio
async def test_filter_validation_pagination(db_session: AsyncSession):
    """Test filter validation for pagination"""
    service = PlayerSearchService(db_session)
    
    # Invalid limit (too small)
    with pytest.raises(ValueError, match="limit must be between 1 and 200"):
        filters = PlayerSearchFilters(limit=0)
        filters.validate()
    
    # Invalid limit (too large)
    with pytest.raises(ValueError, match="limit must be between 1 and 200"):
        filters = PlayerSearchFilters(limit=300)
        filters.validate()
    
    # Invalid offset
    with pytest.raises(ValueError, match="offset must be non-negative"):
        filters = PlayerSearchFilters(offset=-1)
        filters.validate()


@pytest.mark.asyncio
async def test_filter_validation_order_by(db_session: AsyncSession):
    """Test filter validation for order_by"""
    service = PlayerSearchService(db_session)
    
    # Invalid order_by
    with pytest.raises(ValueError, match="order_by must be one of"):
        filters = PlayerSearchFilters(order_by="invalid")
        filters.validate()
    
    # Relevance without search_text
    with pytest.raises(ValueError, match="order_by='relevance' requires search_text"):
        filters = PlayerSearchFilters(order_by="relevance")
        filters.validate()


@pytest.mark.asyncio
async def test_get_filter_options(db_session: AsyncSession, sample_players):
    """Test getting available filter options"""
    service = PlayerSearchService(db_session)
    
    options = await service.get_filter_options()
    
    # Check positions
    assert len(options["positions"]) > 0
    assert "AM/ST RL" in options["positions"]
    
    # Check nationalities
    assert len(options["nationalities"]) == 5
    assert "Argentina" in options["nationalities"]
    assert "Portugal" in options["nationalities"]
    
    # Check clubs
    assert len(options["clubs"]) == 5
    assert "Barcelona" in options["clubs"]
    assert "Manchester United" in options["clubs"]
    
    # Check age range
    assert options["age_range"]["min"] == 18
    assert options["age_range"]["max"] == 38
    
    # Check CA range
    assert options["ca_range"]["min"] == 120
    assert options["ca_range"]["max"] == 195
    
    # Check PA range
    assert options["pa_range"]["min"] == 180
    assert options["pa_range"]["max"] == 200


@pytest.mark.asyncio
async def test_search_players_simple(db_session: AsyncSession, sample_players):
    """Test the simplified search method"""
    service = PlayerSearchService(db_session)
    
    # Search using simple method
    results = await service.search_players_simple(
        position="ST",
        min_ca=180,
        nationality="Argentina"
    )
    
    assert results["total"] == 1
    assert results["players"][0].name == "Lionel Messi"


@pytest.mark.asyncio
async def test_empty_results(db_session: AsyncSession, sample_players):
    """Test search with no matching results"""
    service = PlayerSearchService(db_session)
    
    # Search for non-existent player
    filters = PlayerSearchFilters(search_text="NonExistentPlayer")
    results = await service.search_players(filters)
    
    assert results["total"] == 0
    assert len(results["players"]) == 0
    assert results["has_more"] is False


@pytest.mark.asyncio
async def test_position_partial_match(db_session: AsyncSession, sample_players):
    """Test position filter with partial matching"""
    service = PlayerSearchService(db_session)
    
    # Search for "AM" should match "AM/ST RL", "ST/AM RL", "AM/M C"
    filters = PlayerSearchFilters(position="AM")
    results = await service.search_players(filters)
    
    assert results["total"] == 3
    names = [p.name for p in results["players"]]
    assert "Lionel Messi" in names
    assert "Cristiano Ronaldo" in names
    assert "Kevin De Bruyne" in names


@pytest.mark.asyncio
async def test_relevance_scoring(db_session: AsyncSession, sample_players):
    """Test relevance scoring orders results by search match quality"""
    service = PlayerSearchService(db_session)
    
    # Search for "Messi" with relevance sorting
    filters = PlayerSearchFilters(search_text="Messi", order_by="relevance")
    results = await service.search_players(filters)
    
    # Lionel Messi should be ranked first (name match is strongest)
    assert results["total"] >= 1
    assert results["players"][0].name == "Lionel Messi"
    print(f"✓ Relevance scoring: 'Messi' search ranked Lionel Messi first")


@pytest.mark.asyncio
async def test_relevance_scoring_club(db_session: AsyncSession, sample_players):
    """Test relevance scoring with club search"""
    service = PlayerSearchService(db_session)
    
    # Search for "Manchester" with relevance sorting
    filters = PlayerSearchFilters(search_text="Manchester", order_by="relevance")
    results = await service.search_players(filters)
    
    # Should find Manchester United and Manchester City players
    assert results["total"] >= 1
    # All results should have "Manchester" in club name
    for player in results["players"]:
        assert "Manchester" in player.club
    print(f"✓ Relevance scoring: 'Manchester' search found {results['total']} players")


@pytest.mark.asyncio
async def test_relevance_vs_ca_sorting(db_session: AsyncSession, sample_players):
    """Test that relevance sorting differs from CA sorting"""
    service = PlayerSearchService(db_session)
    
    # Search with relevance sorting
    filters_rel = PlayerSearchFilters(search_text="ST", order_by="relevance")
    results_rel = await service.search_players(filters_rel)
    
    # Search with CA sorting
    filters_ca = PlayerSearchFilters(search_text="ST", order_by="ca")
    results_ca = await service.search_players(filters_ca)
    
    # Should find same players but potentially different order
    assert results_rel["total"] == results_ca["total"]
    
    # CA sorting should be in descending CA order
    cas = [p.ca for p in results_ca["players"]]
    assert cas == sorted(cas, reverse=True)
    print(f"✓ Relevance vs CA sorting: Both found {results_rel['total']} players")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
