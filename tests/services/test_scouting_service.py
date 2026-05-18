"""
Tests for ScoutingService - Comprehensive scouting system tests.

Tests cover:
- 15.1: Scout assignment to players
- 15.2: Scouting report generation
- 15.3: Progressive attribute revelation
- 15.4: Scouting shortlist (up to 50 players)
- 15.5: Shortlist filtering
- 15.6: Scouting completion notifications
- 15.7: Youth scouting for 15-18 year olds
- 15.8: Procedural youth player generation
- 15.9: Scout idle warning notifications
- 15.10: World map view for scouting assignments
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.models.staff import Staff, StaffRole
from app.models.career import Career
from app.models.club import Club
from app.models.user import User
from app.models.scouting_assignment import (
    ScoutingAssignment,
    AssignmentType,
    AssignmentStatus,
)
from app.models.scouting_shortlist import ScoutingShortlist
from app.services.scouting_service import (
    ScoutingService,
    MAX_SHORTLIST_SIZE,
    ALL_ATTRIBUTES,
    SCOUTING_REGIONS,
    YOUTH_POSITIONS,
)


# Use SQLite for testing (no PostgreSQL dependency)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def engine():
    """Create test database engine using SQLite."""
    eng = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        # Create tables individually, skipping PostgreSQL-specific indexes
        for table in Base.metadata.sorted_tables:
            # Filter out PostgreSQL-specific indexes (GIN/tsvector)
            pg_indexes = [
                idx for idx in table.indexes
                if 'fts' in idx.name or 'tsvector' in str(idx.expressions)
            ]
            for idx in pg_indexes:
                table.indexes.discard(idx)

            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))

            # Restore indexes
            for idx in pg_indexes:
                table.indexes.add(idx)

    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture(scope="function")
async def session(engine):
    """Create test database session."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def setup_data(session):
    """Create base test data: user, club, career, scout, and players."""
    # Create user
    user = User(id=1, telegram_user_id=123456, username="testuser", first_name="Test")
    session.add(user)
    await session.flush()

    # Create club
    club = Club(
        id=1,
        name="Test FC",
        reputation=70,
        league="Premier League",
        country="England",
        balance=50_000_000,
        wage_budget=500_000,
        transfer_budget=20_000_000,
        stadium_level=3,
        training_facilities_level=3,
        youth_academy_level=3,
        medical_centre_level=3,
        scouting_network_level=3,
    )
    session.add(club)
    await session.flush()

    # Create career
    career = Career(
        id=1,
        user_id=1,
        club_id=1,
        manager_name="Test Manager",
        current_season=1,
        current_week=5,
    )
    session.add(career)
    await session.flush()

    # Create scout
    scout = Staff(
        id=1,
        career_id=1,
        club_id=1,
        name="John Scout",
        role=StaffRole.CHIEF_SCOUT,
        age=45,
        nationality="England",
        coaching=10,
        tactical_knowledge=10,
        man_management=10,
        scouting=16,
        medical=5,
        fitness=5,
        technical=8,
        mental=10,
        wage=15000,
        contract_start_date=datetime.now(timezone.utc),
        contract_expiry_date=datetime.now(timezone.utc) + timedelta(days=730),
        contract_years=2,
        morale=70,
        performance_rating=14,
    )
    session.add(scout)
    await session.flush()

    # Create test players
    players = []
    for i in range(5):
        player = Player(
            id=i + 1,
            uid=f"TEST{i+1:03d}",
            name=f"Player {i+1}",
            position=["ST", "AM C", "M C", "D C", "GK"][i],
            age=20 + i,
            ca=120 + i * 10,
            pa=160 + i * 5,
            nationality=["England", "Spain", "Germany", "France", "Italy"][i],
            club=f"Club {i+1}",
            corners=10 + i, crossing=10 + i, dribbling=12 + i, finishing=14 + i,
            first_touch=11 + i, free_kicks=8 + i, heading=10 + i, long_shots=9 + i,
            long_throws=5 + i, marking=8 + i, passing=12 + i, penalty=10 + i,
            tackling=9 + i, technique=13 + i,
            aggression=10 + i, anticipation=12 + i, bravery=11 + i, composure=13 + i,
            concentration=11 + i, decisions=12 + i, determination=14 + i, flair=10 + i,
            leadership=8 + i, off_the_ball=12 + i, positioning=11 + i, teamwork=13 + i,
            vision=11 + i, work_rate=12 + i,
            acceleration=14 + i, agility=13 + i, balance=12 + i, jumping=11 + i,
            stamina=13 + i, pace=15 + i, endurance=12 + i, strength=11 + i,
            price="10M", wage=50000 + i * 10000,
            height=175 + i, weight=70 + i * 2,
            left_foot=10 + i, right_foot=14 + i,
        )
        players.append(player)
        session.add(player)

    await session.commit()

    return {
        "user": user,
        "club": club,
        "career": career,
        "scout": scout,
        "players": players,
    }


# ─── Task 15.1: Scout Assignment to Players ─────────────────────────────────


class TestAssignScoutToPlayer:
    """Test ScoutingService.assign_scout_to_player method."""

    @pytest.mark.asyncio
    async def test_assign_scout_to_player_success(self, session, setup_data):
        """Test successful scout assignment to a player."""
        service = ScoutingService(session)
        assignment = await service.assign_scout_to_player(
            career_id=1, scout_id=1, player_id=1
        )

        assert assignment.id is not None
        assert assignment.career_id == 1
        assert assignment.staff_id == 1
        assert assignment.target_player_id == 1
        assert assignment.assignment_type == AssignmentType.PLAYER
        assert assignment.assignment_status == AssignmentStatus.ASSIGNED
        assert assignment.estimated_weeks == 2  # scout has scouting=16

    @pytest.mark.asyncio
    async def test_assign_scout_invalid_scout(self, session, setup_data):
        """Test assignment with non-existent scout raises ValueError."""
        service = ScoutingService(session)
        with pytest.raises(ValueError, match="not found"):
            await service.assign_scout_to_player(
                career_id=1, scout_id=999, player_id=1
            )

    @pytest.mark.asyncio
    async def test_assign_scout_invalid_player(self, session, setup_data):
        """Test assignment with non-existent player raises ValueError."""
        service = ScoutingService(session)
        with pytest.raises(ValueError, match="Player with ID 999 not found"):
            await service.assign_scout_to_player(
                career_id=1, scout_id=1, player_id=999
            )

    @pytest.mark.asyncio
    async def test_assign_scout_duplicate_assignment(self, session, setup_data):
        """Test duplicate assignment raises ValueError."""
        service = ScoutingService(session)
        await service.assign_scout_to_player(career_id=1, scout_id=1, player_id=1)
        with pytest.raises(ValueError, match="already has an active assignment"):
            await service.assign_scout_to_player(career_id=1, scout_id=1, player_id=1)

    @pytest.mark.asyncio
    async def test_assign_non_scout_role(self, session, setup_data):
        """Test assignment with non-scout staff raises ValueError."""
        # Create a fitness coach
        coach = Staff(
            id=2, career_id=1, club_id=1, name="Fitness Guy",
            role=StaffRole.FITNESS_COACH, age=40, nationality="England",
            coaching=15, tactical_knowledge=10, man_management=10,
            scouting=5, medical=5, fitness=18, technical=8, mental=10,
            wage=12000,
            contract_start_date=datetime.now(timezone.utc),
            contract_expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            contract_years=1, morale=70, performance_rating=12,
        )
        session.add(coach)
        await session.commit()

        service = ScoutingService(session)
        with pytest.raises(ValueError, match="not 'chief_scout'"):
            await service.assign_scout_to_player(career_id=1, scout_id=2, player_id=1)


# ─── Task 15.2: Scouting Report Generation ──────────────────────────────────


class TestProcessWeeklyScouting:
    """Test ScoutingService.process_weekly_scouting method."""

    @pytest.mark.asyncio
    async def test_starts_assigned_assignments(self, session, setup_data):
        """Test that ASSIGNED assignments move to IN_PROGRESS."""
        service = ScoutingService(session)
        await service.assign_scout_to_player(career_id=1, scout_id=1, player_id=1)

        result = await service.process_weekly_scouting(career_id=1, season=1, week=5)

        assert result["started"] == 1
        assert result["still_in_progress"] >= 0

    @pytest.mark.asyncio
    async def test_completes_overdue_assignments(self, session, setup_data):
        """Test that assignments past estimated_weeks get completed."""
        # Create an assignment that started 3 weeks ago with estimated 2 weeks
        assignment = ScoutingAssignment(
            career_id=1,
            staff_id=1,
            assignment_type=AssignmentType.PLAYER,
            target_player_id=1,
            assignment_status=AssignmentStatus.IN_PROGRESS,
            estimated_weeks=2,
            start_date=datetime.now(timezone.utc) - timedelta(weeks=3),
        )
        session.add(assignment)
        await session.commit()

        service = ScoutingService(session)
        result = await service.process_weekly_scouting(career_id=1, season=1, week=8)

        assert len(result["completed"]) == 1
        assert result["completed"][0]["type"] == "player"

    @pytest.mark.asyncio
    async def test_no_assignments_returns_empty(self, session, setup_data):
        """Test with no assignments returns zeros."""
        service = ScoutingService(session)
        result = await service.process_weekly_scouting(career_id=1, season=1, week=5)

        assert result["started"] == 0
        assert result["completed"] == []
        assert result["still_in_progress"] == 0


# ─── Task 15.3: Progressive Attribute Revelation ────────────────────────────


class TestProgressiveAttributeRevelation:
    """Test ScoutingService progressive attribute revelation."""

    @pytest.mark.asyncio
    async def test_reveal_attributes_high_quality_scout(self, session, setup_data):
        """Test that high quality scout reveals accurate attributes."""
        service = ScoutingService(session)
        data = setup_data
        player = data["players"][0]

        # Scout quality 20 = no noise
        revealed = service._reveal_attributes(player, scout_quality=20)

        # With quality 20, max_deviation = 0, so values should be exact
        assert revealed["finishing"] == player.finishing
        assert revealed["passing"] == player.passing

    @pytest.mark.asyncio
    async def test_reveal_attributes_low_quality_scout(self, session, setup_data):
        """Test that low quality scout reveals noisy attributes."""
        service = ScoutingService(session)
        data = setup_data
        player = data["players"][0]

        # Run multiple times to verify noise is applied
        with patch("app.services.scouting_service.random.randint", return_value=3):
            revealed = service._reveal_attributes(player, scout_quality=5)
            # With quality 5: max_deviation = (20-5)//4 = 3
            # All values should be true_value + 3 (clamped to 1-20)
            assert revealed["finishing"] == min(20, player.finishing + 3)

    @pytest.mark.asyncio
    async def test_get_scouted_player_attributes_no_report(self, session, setup_data):
        """Test returns None when player has not been scouted."""
        service = ScoutingService(session)
        result = await service.get_scouted_player_attributes(player_id=1, career_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_scouted_player_attributes_with_report(self, session, setup_data):
        """Test returns revealed attributes from completed report."""
        # Create a completed assignment with report data
        report_data = {
            "type": "player",
            "player_id": 1,
            "revealed_attributes": {"finishing": 15, "passing": 12},
        }
        assignment = ScoutingAssignment(
            career_id=1,
            staff_id=1,
            assignment_type=AssignmentType.PLAYER,
            target_player_id=1,
            assignment_status=AssignmentStatus.COMPLETED,
            estimated_weeks=2,
            start_date=datetime.now(timezone.utc) - timedelta(weeks=3),
            completion_date=datetime.now(timezone.utc),
            report_data=json.dumps(report_data),
        )
        session.add(assignment)
        await session.commit()

        service = ScoutingService(session)
        result = await service.get_scouted_player_attributes(player_id=1, career_id=1)

        assert result is not None
        assert result["finishing"] == 15
        assert result["passing"] == 12


# ─── Task 15.4: Scouting Shortlist ──────────────────────────────────────────


class TestScoutingShortlist:
    """Test ScoutingService shortlist management."""

    @pytest.mark.asyncio
    async def test_add_to_shortlist_success(self, session, setup_data):
        """Test adding a player to the shortlist."""
        service = ScoutingService(session)
        entry = await service.add_to_shortlist(career_id=1, player_id=1)

        assert entry.id is not None
        assert entry.career_id == 1
        assert entry.player_id == 1
        assert entry.added_date is not None

    @pytest.mark.asyncio
    async def test_add_duplicate_raises_error(self, session, setup_data):
        """Test adding same player twice raises ValueError."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)

        with pytest.raises(ValueError, match="already on the shortlist"):
            await service.add_to_shortlist(career_id=1, player_id=1)

    @pytest.mark.asyncio
    async def test_add_invalid_player_raises_error(self, session, setup_data):
        """Test adding non-existent player raises ValueError."""
        service = ScoutingService(session)
        with pytest.raises(ValueError, match="Player with ID 999 not found"):
            await service.add_to_shortlist(career_id=1, player_id=999)

    @pytest.mark.asyncio
    async def test_shortlist_max_size_limit(self, session, setup_data):
        """Test that shortlist enforces 50-player maximum."""
        service = ScoutingService(session)

        # Add 50 players (we only have 5 in DB, so create more)
        for i in range(6, 51):
            player = Player(
                id=i, uid=f"EXTRA{i:03d}", name=f"Extra Player {i}",
                position="ST", age=22, ca=100, pa=140,
                nationality="England", club="Extra FC",
                corners=10, crossing=10, dribbling=10, finishing=10,
                first_touch=10, free_kicks=10, heading=10, long_shots=10,
                long_throws=10, marking=10, passing=10, penalty=10,
                tackling=10, technique=10,
                aggression=10, anticipation=10, bravery=10, composure=10,
                concentration=10, decisions=10, determination=10, flair=10,
                leadership=10, off_the_ball=10, positioning=10, teamwork=10,
                vision=10, work_rate=10,
                acceleration=10, agility=10, balance=10, jumping=10,
                stamina=10, pace=10, endurance=10, strength=10,
                price="1M", wage=10000, height=180, weight=75,
                left_foot=10, right_foot=10,
            )
            session.add(player)
        await session.commit()

        # Add all 50 players
        for i in range(1, 51):
            await service.add_to_shortlist(career_id=1, player_id=i)

        # 51st should fail
        player_51 = Player(
            id=51, uid="EXTRA051", name="Extra Player 51",
            position="ST", age=22, ca=100, pa=140,
            nationality="England", club="Extra FC",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            price="1M", wage=10000, height=180, weight=75,
            left_foot=10, right_foot=10,
        )
        session.add(player_51)
        await session.commit()

        with pytest.raises(ValueError, match="Shortlist is full"):
            await service.add_to_shortlist(career_id=1, player_id=51)

    @pytest.mark.asyncio
    async def test_remove_from_shortlist(self, session, setup_data):
        """Test removing a player from the shortlist."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)

        result = await service.remove_from_shortlist(career_id=1, player_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent_returns_false(self, session, setup_data):
        """Test removing non-existent entry returns False."""
        service = ScoutingService(session)
        result = await service.remove_from_shortlist(career_id=1, player_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_shortlist(self, session, setup_data):
        """Test getting the full shortlist."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)
        await service.add_to_shortlist(career_id=1, player_id=2)

        shortlist = await service.get_shortlist(career_id=1)

        assert len(shortlist) == 2
        assert shortlist[0]["player_id"] in [1, 2]
        assert "name" in shortlist[0]
        assert "position" in shortlist[0]
        assert "age" in shortlist[0]


# ─── Task 15.5: Shortlist Filtering ─────────────────────────────────────────


class TestShortlistFiltering:
    """Test ScoutingService.filter_shortlist method."""

    @pytest.mark.asyncio
    async def test_filter_by_position(self, session, setup_data):
        """Test filtering shortlist by position."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)  # ST
        await service.add_to_shortlist(career_id=1, player_id=2)  # AM C
        await service.add_to_shortlist(career_id=1, player_id=3)  # M C

        result = await service.filter_shortlist(career_id=1, filters={"position": "ST"})
        assert len(result) == 1
        assert result[0]["position"] == "ST"

    @pytest.mark.asyncio
    async def test_filter_by_age_range(self, session, setup_data):
        """Test filtering shortlist by age range."""
        service = ScoutingService(session)
        for i in range(1, 6):
            await service.add_to_shortlist(career_id=1, player_id=i)

        result = await service.filter_shortlist(
            career_id=1, filters={"min_age": 22, "max_age": 23}
        )
        # Players ages are 20, 21, 22, 23, 24 - so 22 and 23 match
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filter_by_ca(self, session, setup_data):
        """Test filtering shortlist by current ability."""
        service = ScoutingService(session)
        for i in range(1, 6):
            await service.add_to_shortlist(career_id=1, player_id=i)

        # CAs are 120, 130, 140, 150, 160
        result = await service.filter_shortlist(
            career_id=1, filters={"min_ca": 140}
        )
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_filter_by_nationality(self, session, setup_data):
        """Test filtering shortlist by nationality."""
        service = ScoutingService(session)
        for i in range(1, 6):
            await service.add_to_shortlist(career_id=1, player_id=i)

        result = await service.filter_shortlist(
            career_id=1, filters={"nationality": "Spain"}
        )
        assert len(result) == 1
        assert result[0]["nationality"] == "Spain"

    @pytest.mark.asyncio
    async def test_filter_no_matches(self, session, setup_data):
        """Test filtering with no matches returns empty list."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)

        result = await service.filter_shortlist(
            career_id=1, filters={"min_ca": 999}
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_filter_empty_filters(self, session, setup_data):
        """Test filtering with empty filters returns all."""
        service = ScoutingService(session)
        await service.add_to_shortlist(career_id=1, player_id=1)
        await service.add_to_shortlist(career_id=1, player_id=2)

        result = await service.filter_shortlist(career_id=1, filters={})
        assert len(result) == 2


# ─── Task 15.6: Scouting Completion Notifications ────────────────────────────


class TestScoutingNotifications:
    """Test ScoutingService.get_scouting_notifications method."""

    @pytest.mark.asyncio
    async def test_get_notifications_with_completed_reports(self, session, setup_data):
        """Test getting notifications for completed assignments."""
        # Create a completed assignment with report
        report_data = {"type": "player", "summary": "Good player found"}
        assignment = ScoutingAssignment(
            career_id=1,
            staff_id=1,
            assignment_type=AssignmentType.PLAYER,
            target_player_id=1,
            assignment_status=AssignmentStatus.COMPLETED,
            estimated_weeks=2,
            start_date=datetime.now(timezone.utc) - timedelta(weeks=3),
            completion_date=datetime.now(timezone.utc),
            report_data=json.dumps(report_data),
        )
        session.add(assignment)
        await session.commit()

        service = ScoutingService(session)
        notifications = await service.get_scouting_notifications(career_id=1)

        assert len(notifications) == 1
        assert notifications[0]["scout_name"] == "John Scout"
        assert notifications[0]["assignment_type"] == "player"
        assert notifications[0]["report_summary"] == "Good player found"

    @pytest.mark.asyncio
    async def test_get_notifications_empty(self, session, setup_data):
        """Test getting notifications when none exist."""
        service = ScoutingService(session)
        notifications = await service.get_scouting_notifications(career_id=1)
        assert notifications == []


# ─── Task 15.7: Youth Scouting ───────────────────────────────────────────────


class TestYouthScouting:
    """Test ScoutingService.assign_youth_scouting method."""

    @pytest.mark.asyncio
    async def test_assign_youth_scouting_success(self, session, setup_data):
        """Test successful youth scouting assignment."""
        service = ScoutingService(session)
        assignment = await service.assign_youth_scouting(
            career_id=1, scout_id=1, region="England"
        )

        assert assignment.id is not None
        assert assignment.assignment_type == AssignmentType.REGION
        assert assignment.target_region == "YOUTH:England"
        assert assignment.estimated_weeks == 2

    @pytest.mark.asyncio
    async def test_assign_youth_scouting_invalid_region(self, session, setup_data):
        """Test youth scouting with invalid region raises ValueError."""
        service = ScoutingService(session)
        with pytest.raises(ValueError, match="Invalid region"):
            await service.assign_youth_scouting(
                career_id=1, scout_id=1, region="Mars"
            )

    @pytest.mark.asyncio
    async def test_assign_youth_scouting_duplicate(self, session, setup_data):
        """Test duplicate youth scouting assignment raises ValueError."""
        service = ScoutingService(session)
        await service.assign_youth_scouting(career_id=1, scout_id=1, region="Spain")

        with pytest.raises(ValueError, match="already has an active youth scouting"):
            await service.assign_youth_scouting(career_id=1, scout_id=1, region="Spain")


# ─── Task 15.8: Procedural Youth Player Generation ───────────────────────────


class TestYouthPlayerGeneration:
    """Test ScoutingService.generate_youth_prospect method."""

    def test_generate_youth_prospect_basic(self):
        """Test basic youth prospect generation."""
        service = ScoutingService.__new__(ScoutingService)
        prospect = service.generate_youth_prospect(region="England", academy_level=3)

        assert prospect["age"] >= 15
        assert prospect["age"] <= 18
        assert prospect["position"] in YOUTH_POSITIONS
        assert prospect["nationality"] == "England"
        assert prospect["ca"] >= 30
        assert prospect["pa"] >= prospect["ca"]
        assert prospect["academy_level"] == 3
        assert "attributes" in prospect
        assert len(prospect["attributes"]) == len(ALL_ATTRIBUTES)

    def test_generate_youth_prospect_level_1(self):
        """Test level 1 academy produces lower quality prospects."""
        service = ScoutingService.__new__(ScoutingService)
        prospects = [service.generate_youth_prospect("England", 1) for _ in range(20)]

        avg_pa = sum(p["pa"] for p in prospects) / len(prospects)
        # Level 1: PA range 80-120, average should be around 100
        assert 60 <= avg_pa <= 140

    def test_generate_youth_prospect_level_5(self):
        """Test level 5 academy produces higher quality prospects."""
        service = ScoutingService.__new__(ScoutingService)
        prospects = [service.generate_youth_prospect("Spain", 5) for _ in range(20)]

        avg_pa = sum(p["pa"] for p in prospects) / len(prospects)
        # Level 5: PA range 160-200, average should be around 180
        assert 140 <= avg_pa <= 220

    def test_generate_youth_prospect_attributes_in_range(self):
        """Test all generated attributes are within valid range."""
        service = ScoutingService.__new__(ScoutingService)
        for _ in range(50):
            prospect = service.generate_youth_prospect("Germany", 3)
            for attr_name, value in prospect["attributes"].items():
                assert 1 <= value <= 20, f"{attr_name} = {value} out of range"

    def test_generate_youth_prospect_different_regions(self):
        """Test generation works for all regions."""
        service = ScoutingService.__new__(ScoutingService)
        for region in SCOUTING_REGIONS:
            prospect = service.generate_youth_prospect(region, 3)
            assert prospect["region"] == region
            assert prospect["name"]  # Has a name


# ─── Task 15.9: Scout Idle Warning Notifications ─────────────────────────────


class TestIdleScoutWarnings:
    """Test ScoutingService.get_idle_scout_warnings method."""

    @pytest.mark.asyncio
    async def test_idle_scout_with_no_assignments(self, session, setup_data):
        """Test idle scout warning when scout has no assignments."""
        service = ScoutingService(session)
        warnings = await service.get_idle_scout_warnings(career_id=1)

        assert len(warnings) == 1
        assert warnings[0]["scout_id"] == 1
        assert warnings[0]["scout_name"] == "John Scout"
        assert "no active assignments" in warnings[0]["message"]

    @pytest.mark.asyncio
    async def test_no_warning_when_scout_is_busy(self, session, setup_data):
        """Test no warning when scout has active assignment."""
        service = ScoutingService(session)
        await service.assign_scout_to_player(career_id=1, scout_id=1, player_id=1)

        warnings = await service.get_idle_scout_warnings(career_id=1)
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_no_warnings_when_no_scouts(self, session, setup_data):
        """Test no warnings when career has no scouts."""
        service = ScoutingService(session)
        # Use career_id that doesn't have scouts
        warnings = await service.get_idle_scout_warnings(career_id=999)
        assert warnings == []


# ─── Task 15.10: World Map View ──────────────────────────────────────────────


class TestWorldMapView:
    """Test ScoutingService.get_scouting_world_map method."""

    @pytest.mark.asyncio
    async def test_world_map_empty(self, session, setup_data):
        """Test world map with no active assignments."""
        service = ScoutingService(session)
        world_map = await service.get_scouting_world_map(career_id=1)

        assert world_map["total_active"] == 0
        assert world_map["total_scouts"] == 1
        assert len(world_map["unassigned_regions"]) == len(SCOUTING_REGIONS)
        assert len(world_map["regions"]) == len(SCOUTING_REGIONS)

    @pytest.mark.asyncio
    async def test_world_map_with_region_assignment(self, session, setup_data):
        """Test world map shows region assignments."""
        # Create a region assignment
        assignment = ScoutingAssignment(
            career_id=1,
            staff_id=1,
            assignment_type=AssignmentType.REGION,
            target_region="England",
            assignment_status=AssignmentStatus.IN_PROGRESS,
            estimated_weeks=3,
            start_date=datetime.now(timezone.utc) - timedelta(weeks=1),
        )
        session.add(assignment)
        await session.commit()

        service = ScoutingService(session)
        world_map = await service.get_scouting_world_map(career_id=1)

        assert world_map["total_active"] == 1
        assert world_map["regions"]["England"]["has_activity"] is True
        assert world_map["regions"]["England"]["scout_count"] == 1
        assert len(world_map["regions"]["England"]["assignments"]) == 1
        assert "England" not in world_map["unassigned_regions"]

    @pytest.mark.asyncio
    async def test_world_map_with_youth_scouting(self, session, setup_data):
        """Test world map shows youth scouting assignments."""
        service = ScoutingService(session)
        await service.assign_youth_scouting(career_id=1, scout_id=1, region="Spain")

        world_map = await service.get_scouting_world_map(career_id=1)

        assert world_map["total_active"] == 1
        assert world_map["regions"]["Spain"]["has_activity"] is True
        spain_assignments = world_map["regions"]["Spain"]["assignments"]
        assert len(spain_assignments) == 1
        assert spain_assignments[0]["is_youth"] is True

    @pytest.mark.asyncio
    async def test_world_map_available_regions(self, session, setup_data):
        """Test world map includes all available regions."""
        service = ScoutingService(session)
        world_map = await service.get_scouting_world_map(career_id=1)

        assert world_map["available_regions"] == SCOUTING_REGIONS
