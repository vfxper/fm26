"""
Unit tests for StaffService - Scout Assignment to Regions/Competitions
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService
from app.models.staff import Staff, StaffRole
from app.models.scouting_assignment import ScoutingAssignment, AssignmentType, AssignmentStatus


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine"""
    from app.models import (
        User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
        Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
        Competition, Fixture
    )
    from app.models.player import Player as PlayerModel

    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        future=True,
        connect_args={"check_same_thread": False}
    )

    # Remove the GIN index from the players table before creating tables
    players_table = PlayerModel.__table__
    gin_index = None
    for idx in list(players_table.indexes):
        if idx.name == 'idx_players_fts':
            gin_index = idx
            players_table.indexes.discard(idx)
            break

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Restore the GIN index
    if gin_index:
        players_table.indexes.add(gin_index)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create test database session"""
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


async def _create_scout(db_session: AsyncSession, career_id: int = 1, club_id: int = 1,
                        name: str = "Chief Scout", scouting: int = 16) -> Staff:
    """Helper to create a scout staff member."""
    service = StaffService(db_session)
    attributes = {
        "coaching": 10,
        "tactical_knowledge": 10,
        "man_management": 12,
        "scouting": scouting,
        "medical": 8,
        "fitness": 9,
        "technical": 10,
        "mental": 11,
    }
    return await service.hire_staff(
        career_id=career_id,
        club_id=club_id,
        name=name,
        role=StaffRole.CHIEF_SCOUT,
        age=50,
        nationality="England",
        attributes=attributes,
        wage=18000,
        contract_years=3,
    )


@pytest.mark.asyncio
class TestScoutAssignmentToRegion:
    """Test suite for assign_scout_to_region"""

    async def test_assign_scout_to_valid_region(self, db_session: AsyncSession):
        """Test assigning a scout to a valid region"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="England"
        )

        assert assignment.id is not None
        assert assignment.career_id == 1
        assert assignment.staff_id == scout.id
        assert assignment.assignment_type == AssignmentType.REGION
        assert assignment.target_region == "England"
        assert assignment.assignment_status == AssignmentStatus.ASSIGNED
        assert assignment.target_player_id is None
        assert assignment.target_competition is None

    async def test_assign_scout_to_region_estimated_weeks_high_scouting(self, db_session: AsyncSession):
        """Scout with scouting >= 16 gets 2 weeks estimate"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session, scouting=18)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Spain"
        )

        assert assignment.estimated_weeks == 2

    async def test_assign_scout_to_region_estimated_weeks_medium_scouting(self, db_session: AsyncSession):
        """Scout with scouting 12-15 gets 3 weeks estimate"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session, scouting=14)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Germany"
        )

        assert assignment.estimated_weeks == 3

    async def test_assign_scout_to_region_estimated_weeks_low_scouting(self, db_session: AsyncSession):
        """Scout with scouting < 12 gets 4 weeks estimate"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session, scouting=10)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="France"
        )

        assert assignment.estimated_weeks == 4

    async def test_assign_scout_to_invalid_region_raises(self, db_session: AsyncSession):
        """Test that assigning to an invalid region raises ValueError"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        with pytest.raises(ValueError, match="Invalid region"):
            await service.assign_scout_to_region(
                career_id=1, scout_id=scout.id, region="Atlantis"
            )

    async def test_assign_non_scout_raises(self, db_session: AsyncSession):
        """Test that assigning a non-scout staff member raises ValueError"""
        service = StaffService(db_session)

        # Hire a fitness coach (not a scout)
        attributes = {
            "coaching": 15, "tactical_knowledge": 10, "man_management": 11,
            "scouting": 8, "medical": 9, "fitness": 17, "technical": 10, "mental": 10,
        }
        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Fitness Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3,
        )

        with pytest.raises(ValueError, match="not a scout role"):
            await service.assign_scout_to_region(
                career_id=1, scout_id=coach.id, region="England"
            )

    async def test_assign_nonexistent_scout_raises(self, db_session: AsyncSession):
        """Test that assigning a nonexistent staff member raises ValueError"""
        service = StaffService(db_session)

        with pytest.raises(ValueError, match="not found"):
            await service.assign_scout_to_region(
                career_id=1, scout_id=9999, region="England"
            )

    async def test_duplicate_active_region_assignment_raises(self, db_session: AsyncSession):
        """Test that assigning same scout to same region twice raises ValueError"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Italy"
        )

        with pytest.raises(ValueError, match="already has an active assignment"):
            await service.assign_scout_to_region(
                career_id=1, scout_id=scout.id, region="Italy"
            )


@pytest.mark.asyncio
class TestScoutAssignmentToCompetition:
    """Test suite for assign_scout_to_competition"""

    async def test_assign_scout_to_competition(self, db_session: AsyncSession):
        """Test assigning a scout to a competition"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_competition(
            career_id=1, scout_id=scout.id, competition="Premier League"
        )

        assert assignment.id is not None
        assert assignment.career_id == 1
        assert assignment.staff_id == scout.id
        assert assignment.assignment_type == AssignmentType.COMPETITION
        assert assignment.target_competition == "Premier League"
        assert assignment.assignment_status == AssignmentStatus.ASSIGNED
        assert assignment.target_player_id is None
        assert assignment.target_region is None

    async def test_assign_scout_to_competition_trims_whitespace(self, db_session: AsyncSession):
        """Test that competition name is trimmed"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_competition(
            career_id=1, scout_id=scout.id, competition="  La Liga  "
        )

        assert assignment.target_competition == "La Liga"

    async def test_assign_scout_to_empty_competition_raises(self, db_session: AsyncSession):
        """Test that empty competition name raises ValueError"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        with pytest.raises(ValueError, match="Competition name cannot be empty"):
            await service.assign_scout_to_competition(
                career_id=1, scout_id=scout.id, competition=""
            )

    async def test_assign_scout_to_whitespace_competition_raises(self, db_session: AsyncSession):
        """Test that whitespace-only competition name raises ValueError"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        with pytest.raises(ValueError, match="Competition name cannot be empty"):
            await service.assign_scout_to_competition(
                career_id=1, scout_id=scout.id, competition="   "
            )

    async def test_duplicate_active_competition_assignment_raises(self, db_session: AsyncSession):
        """Test that assigning same scout to same competition twice raises ValueError"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        await service.assign_scout_to_competition(
            career_id=1, scout_id=scout.id, competition="Champions League"
        )

        with pytest.raises(ValueError, match="already has an active assignment"):
            await service.assign_scout_to_competition(
                career_id=1, scout_id=scout.id, competition="Champions League"
            )

    async def test_assign_non_scout_to_competition_raises(self, db_session: AsyncSession):
        """Test that assigning a non-scout to a competition raises ValueError"""
        service = StaffService(db_session)

        attributes = {
            "coaching": 15, "tactical_knowledge": 10, "man_management": 11,
            "scouting": 8, "medical": 9, "fitness": 17, "technical": 10, "mental": 10,
        }
        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Physio",
            role=StaffRole.PHYSIO, age=40, nationality="Spain",
            attributes=attributes, wage=14000, contract_years=2,
        )

        with pytest.raises(ValueError, match="not a scout role"):
            await service.assign_scout_to_competition(
                career_id=1, scout_id=coach.id, competition="La Liga"
            )


@pytest.mark.asyncio
class TestGetScoutAssignments:
    """Test suite for get_scout_assignments"""

    async def test_get_assignments_empty(self, db_session: AsyncSession):
        """Test getting assignments when none exist"""
        service = StaffService(db_session)

        assignments = await service.get_scout_assignments(career_id=1)
        assert assignments == []

    async def test_get_assignments_returns_active_only(self, db_session: AsyncSession):
        """Test that only non-completed assignments are returned"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        # Create two assignments
        a1 = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="England"
        )
        a2 = await service.assign_scout_to_competition(
            career_id=1, scout_id=scout.id, competition="Serie A"
        )

        # Complete one assignment
        a1.assignment_status = AssignmentStatus.COMPLETED
        await db_session.commit()

        assignments = await service.get_scout_assignments(career_id=1)
        assert len(assignments) == 1
        assert assignments[0].id == a2.id

    async def test_get_assignments_multiple(self, db_session: AsyncSession):
        """Test getting multiple active assignments"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Spain"
        )
        await service.assign_scout_to_competition(
            career_id=1, scout_id=scout.id, competition="Bundesliga"
        )

        assignments = await service.get_scout_assignments(career_id=1)
        assert len(assignments) == 2


@pytest.mark.asyncio
class TestRemoveScoutAssignment:
    """Test suite for remove_scout_assignment"""

    async def test_remove_existing_assignment(self, db_session: AsyncSession):
        """Test removing an existing assignment"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Africa"
        )

        result = await service.remove_scout_assignment(
            assignment_id=assignment.id, career_id=1
        )
        assert result is True

        # Verify it's gone
        assignments = await service.get_scout_assignments(career_id=1)
        assert len(assignments) == 0

    async def test_remove_nonexistent_assignment(self, db_session: AsyncSession):
        """Test removing a nonexistent assignment returns False"""
        service = StaffService(db_session)

        result = await service.remove_scout_assignment(
            assignment_id=9999, career_id=1
        )
        assert result is False

    async def test_remove_assignment_wrong_career(self, db_session: AsyncSession):
        """Test that removing an assignment from wrong career returns False"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="Asia"
        )

        # Try to remove with wrong career_id
        result = await service.remove_scout_assignment(
            assignment_id=assignment.id, career_id=999
        )
        assert result is False


@pytest.mark.asyncio
class TestGetAvailableRegions:
    """Test suite for get_available_regions"""

    def test_get_available_regions_returns_list(self):
        """Test that get_available_regions returns a non-empty list"""
        regions = StaffService.get_available_regions()
        assert isinstance(regions, list)
        assert len(regions) > 0

    def test_get_available_regions_contains_expected(self):
        """Test that expected regions are in the list"""
        regions = StaffService.get_available_regions()
        assert "England" in regions
        assert "Spain" in regions
        assert "Germany" in regions
        assert "South America" in regions
        assert "Africa" in regions
        assert "Asia" in regions

    def test_get_available_regions_returns_copy(self):
        """Test that modifying the returned list doesn't affect the class"""
        regions = StaffService.get_available_regions()
        regions.append("Mars")
        assert "Mars" not in StaffService.get_available_regions()


@pytest.mark.asyncio
class TestGetIdleScouts:
    """Test suite for get_idle_scouts"""

    async def test_get_idle_scouts_no_scouts(self, db_session: AsyncSession):
        """Test getting idle scouts when no scouts exist"""
        service = StaffService(db_session)

        idle = await service.get_idle_scouts(career_id=1)
        assert idle == []

    async def test_get_idle_scouts_all_idle(self, db_session: AsyncSession):
        """Test that scouts without assignments are returned as idle"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        idle = await service.get_idle_scouts(career_id=1)
        assert len(idle) == 1
        assert idle[0].id == scout.id

    async def test_get_idle_scouts_with_active_assignment(self, db_session: AsyncSession):
        """Test that scouts with active assignments are not idle"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="England"
        )

        idle = await service.get_idle_scouts(career_id=1)
        assert len(idle) == 0

    async def test_get_idle_scouts_with_completed_assignment(self, db_session: AsyncSession):
        """Test that scouts with only completed assignments are idle"""
        service = StaffService(db_session)
        scout = await _create_scout(db_session)

        assignment = await service.assign_scout_to_region(
            career_id=1, scout_id=scout.id, region="France"
        )

        # Complete the assignment
        assignment.assignment_status = AssignmentStatus.COMPLETED
        await db_session.commit()

        idle = await service.get_idle_scouts(career_id=1)
        assert len(idle) == 1
        assert idle[0].id == scout.id

    async def test_get_idle_scouts_mixed(self, db_session: AsyncSession):
        """Test with mix of idle and busy scouts"""
        service = StaffService(db_session)
        scout1 = await _create_scout(db_session, name="Scout A", scouting=16)
        scout2 = await _create_scout(db_session, name="Scout B", scouting=14)

        # Assign only scout1
        await service.assign_scout_to_region(
            career_id=1, scout_id=scout1.id, region="Italy"
        )

        idle = await service.get_idle_scouts(career_id=1)
        assert len(idle) == 1
        assert idle[0].id == scout2.id
