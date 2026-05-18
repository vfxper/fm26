"""
Unit tests for Staff Wage Budget Management (Task 13.10)

Tests the following methods in StaffService:
- get_staff_wage_budget_status()
- can_afford_staff_wage()
- get_staff_wage_breakdown()
- Budget check integration in hire_staff()
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService
from app.models.staff import Staff, StaffRole
from app.models.club import Club
from app.models.career import Career


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


@pytest.fixture
async def club_with_budget(db_session: AsyncSession):
    """Create a club with a known wage budget for testing."""
    club = Club(
        name="Test FC",
        reputation=60,
        league="Premier League",
        country="England",
        wage_budget=200000,  # 200k/week total wage budget
        balance=10000000,
        transfer_budget=5000000,
        matchday_revenue=500000,
        stadium_capacity=40000,
    )
    db_session.add(club)
    await db_session.commit()
    await db_session.refresh(club)
    return club


DEFAULT_ATTRIBUTES = {
    "coaching": 14,
    "tactical_knowledge": 12,
    "man_management": 13,
    "scouting": 10,
    "medical": 10,
    "fitness": 14,
    "technical": 12,
    "mental": 11,
}


@pytest.mark.asyncio
class TestStaffWageBudgetStatus:
    """Tests for get_staff_wage_budget_status()"""

    async def test_budget_status_no_staff(self, db_session: AsyncSession, club_with_budget: Club):
        """Test budget status when no staff are hired."""
        service = StaffService(db_session)

        status = await service.get_staff_wage_budget_status(
            career_id=1, club_id=club_with_budget.id
        )

        # 30% of 200,000 = 60,000
        assert status["total_wage_budget"] == 200000
        assert status["staff_wage_allocation"] == 60000
        assert status["current_staff_wages"] == 0
        assert status["remaining_budget"] == 60000
        assert status["utilization_percentage"] == 0.0
        assert status["is_over_budget"] is False
        assert status["staff_count"] == 0

    async def test_budget_status_with_staff(self, db_session: AsyncSession, club_with_budget: Club):
        """Test budget status with some staff hired."""
        service = StaffService(db_session)

        # Hire two staff members (total wages: 15000 + 20000 = 35000)
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach A", role=StaffRole.FITNESS_COACH,
            age=40, nationality="England",
            attributes=DEFAULT_ATTRIBUTES, wage=15000, contract_years=2
        )
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach B", role=StaffRole.DEFENSIVE_COACH,
            age=45, nationality="Spain",
            attributes=DEFAULT_ATTRIBUTES, wage=20000, contract_years=3
        )

        status = await service.get_staff_wage_budget_status(
            career_id=1, club_id=club_with_budget.id
        )

        assert status["total_wage_budget"] == 200000
        assert status["staff_wage_allocation"] == 60000
        assert status["current_staff_wages"] == 35000
        assert status["remaining_budget"] == 25000
        # 35000/60000 * 100 = 58.3%
        assert status["utilization_percentage"] == 58.3
        assert status["is_over_budget"] is False
        assert status["staff_count"] == 2

    async def test_budget_status_invalid_club(self, db_session: AsyncSession):
        """Test budget status with non-existent club raises error."""
        service = StaffService(db_session)

        with pytest.raises(ValueError, match="Club with ID 9999 not found"):
            await service.get_staff_wage_budget_status(career_id=1, club_id=9999)


@pytest.mark.asyncio
class TestCanAffordStaffWage:
    """Tests for can_afford_staff_wage()"""

    async def test_can_afford_within_budget(self, db_session: AsyncSession, club_with_budget: Club):
        """Test that hiring within budget returns True."""
        service = StaffService(db_session)

        # Budget allocation is 60,000. Hiring at 30,000 should be affordable.
        result = await service.can_afford_staff_wage(
            career_id=1, club_id=club_with_budget.id, additional_wage=30000
        )
        assert result is True

    async def test_cannot_afford_exceeds_budget(self, db_session: AsyncSession, club_with_budget: Club):
        """Test that hiring exceeding budget returns False."""
        service = StaffService(db_session)

        # Budget allocation is 60,000. Hiring at 70,000 should not be affordable.
        result = await service.can_afford_staff_wage(
            career_id=1, club_id=club_with_budget.id, additional_wage=70000
        )
        assert result is False

    async def test_can_afford_exactly_at_budget(self, db_session: AsyncSession, club_with_budget: Club):
        """Test that hiring exactly at budget limit returns True."""
        service = StaffService(db_session)

        # Budget allocation is 60,000. Hiring at exactly 60,000 should be affordable.
        result = await service.can_afford_staff_wage(
            career_id=1, club_id=club_with_budget.id, additional_wage=60000
        )
        assert result is True

    async def test_cannot_afford_after_existing_staff(self, db_session: AsyncSession, club_with_budget: Club):
        """Test budget check accounts for existing staff wages."""
        service = StaffService(db_session)

        # Hire staff using 50,000 of the 60,000 budget
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Expensive Coach", role=StaffRole.ASSISTANT_MANAGER,
            age=50, nationality="Germany",
            attributes=DEFAULT_ATTRIBUTES, wage=50000, contract_years=3
        )

        # Now only 10,000 remains. Trying to hire at 15,000 should fail.
        result = await service.can_afford_staff_wage(
            career_id=1, club_id=club_with_budget.id, additional_wage=15000
        )
        assert result is False

    async def test_can_afford_after_existing_staff_within_remaining(self, db_session: AsyncSession, club_with_budget: Club):
        """Test budget check allows hiring within remaining budget."""
        service = StaffService(db_session)

        # Hire staff using 40,000 of the 60,000 budget
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach A", role=StaffRole.ASSISTANT_MANAGER,
            age=50, nationality="Germany",
            attributes=DEFAULT_ATTRIBUTES, wage=40000, contract_years=3
        )

        # 20,000 remains. Hiring at 15,000 should be fine.
        result = await service.can_afford_staff_wage(
            career_id=1, club_id=club_with_budget.id, additional_wage=15000
        )
        assert result is True


@pytest.mark.asyncio
class TestStaffWageBreakdown:
    """Tests for get_staff_wage_breakdown()"""

    async def test_breakdown_no_staff(self, db_session: AsyncSession, club_with_budget: Club):
        """Test wage breakdown with no staff."""
        service = StaffService(db_session)

        breakdown = await service.get_staff_wage_breakdown(
            career_id=1, club_id=club_with_budget.id
        )

        assert breakdown["by_role"] == {}
        assert breakdown["total_wages"] == 0
        assert breakdown["highest_earner"] is None
        assert breakdown["lowest_earner"] is None
        assert breakdown["average_wage"] == 0

    async def test_breakdown_with_multiple_roles(self, db_session: AsyncSession, club_with_budget: Club):
        """Test wage breakdown with staff in multiple roles."""
        service = StaffService(db_session)

        # Hire staff in different roles
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Fitness Coach", role=StaffRole.FITNESS_COACH,
            age=40, nationality="England",
            attributes=DEFAULT_ATTRIBUTES, wage=12000, contract_years=2
        )
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Defensive Coach", role=StaffRole.DEFENSIVE_COACH,
            age=45, nationality="Spain",
            attributes=DEFAULT_ATTRIBUTES, wage=15000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Chief Scout", role=StaffRole.CHIEF_SCOUT,
            age=50, nationality="Italy",
            attributes=DEFAULT_ATTRIBUTES, wage=18000, contract_years=2
        )

        breakdown = await service.get_staff_wage_breakdown(
            career_id=1, club_id=club_with_budget.id
        )

        assert breakdown["total_wages"] == 45000
        assert breakdown["average_wage"] == 15000
        assert len(breakdown["by_role"]) == 3

        # Check highest and lowest earners
        assert breakdown["highest_earner"]["name"] == "Chief Scout"
        assert breakdown["highest_earner"]["wage"] == 18000
        assert breakdown["lowest_earner"]["name"] == "Fitness Coach"
        assert breakdown["lowest_earner"]["wage"] == 12000

        # Check role breakdown
        assert breakdown["by_role"]["fitness_coach"]["total_wages"] == 12000
        assert breakdown["by_role"]["fitness_coach"]["count"] == 1
        assert breakdown["by_role"]["defensive_coach"]["total_wages"] == 15000
        assert breakdown["by_role"]["chief_scout"]["total_wages"] == 18000

    async def test_breakdown_multiple_staff_same_role(self, db_session: AsyncSession, club_with_budget: Club):
        """Test wage breakdown with multiple staff in the same role."""
        service = StaffService(db_session)

        # Hire two fitness coaches
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach A", role=StaffRole.FITNESS_COACH,
            age=40, nationality="England",
            attributes=DEFAULT_ATTRIBUTES, wage=10000, contract_years=2
        )
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach B", role=StaffRole.FITNESS_COACH,
            age=42, nationality="France",
            attributes=DEFAULT_ATTRIBUTES, wage=12000, contract_years=3
        )

        breakdown = await service.get_staff_wage_breakdown(
            career_id=1, club_id=club_with_budget.id
        )

        assert breakdown["by_role"]["fitness_coach"]["total_wages"] == 22000
        assert breakdown["by_role"]["fitness_coach"]["count"] == 2
        assert len(breakdown["by_role"]["fitness_coach"]["staff_members"]) == 2


@pytest.mark.asyncio
class TestHireStaffBudgetIntegration:
    """Tests for budget check integration in hire_staff()"""

    async def test_hire_staff_within_budget(self, db_session: AsyncSession, club_with_budget: Club):
        """Test that hiring within budget succeeds."""
        service = StaffService(db_session)

        # Budget allocation is 60,000. Hiring at 20,000 should work.
        staff = await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="New Coach", role=StaffRole.FITNESS_COACH,
            age=40, nationality="England",
            attributes=DEFAULT_ATTRIBUTES, wage=20000, contract_years=2
        )

        assert staff.id is not None
        assert staff.wage == 20000

    async def test_hire_staff_exceeds_budget_raises_error(self, db_session: AsyncSession, club_with_budget: Club):
        """Test that hiring exceeding budget raises ValueError."""
        service = StaffService(db_session)

        # Budget allocation is 60,000. Hiring at 70,000 should fail.
        with pytest.raises(ValueError, match="Cannot afford staff wage"):
            await service.hire_staff(
                career_id=1, club_id=club_with_budget.id,
                name="Expensive Coach", role=StaffRole.CHIEF_SCOUT,
                age=50, nationality="England",
                attributes=DEFAULT_ATTRIBUTES, wage=70000, contract_years=3
            )

    async def test_hire_multiple_staff_until_budget_exceeded(self, db_session: AsyncSession, club_with_budget: Club):
        """Test hiring multiple staff until budget is exceeded."""
        service = StaffService(db_session)

        # Budget allocation is 60,000
        # Hire first coach at 25,000 (remaining: 35,000)
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach 1", role=StaffRole.FITNESS_COACH,
            age=40, nationality="England",
            attributes=DEFAULT_ATTRIBUTES, wage=25000, contract_years=2
        )

        # Hire second coach at 25,000 (remaining: 10,000)
        await service.hire_staff(
            career_id=1, club_id=club_with_budget.id,
            name="Coach 2", role=StaffRole.DEFENSIVE_COACH,
            age=42, nationality="Spain",
            attributes=DEFAULT_ATTRIBUTES, wage=25000, contract_years=2
        )

        # Third hire at 15,000 should fail (only 10,000 remaining)
        with pytest.raises(ValueError, match="Cannot afford staff wage"):
            await service.hire_staff(
                career_id=1, club_id=club_with_budget.id,
                name="Coach 3", role=StaffRole.ATTACKING_COACH,
                age=38, nationality="France",
                attributes=DEFAULT_ATTRIBUTES, wage=15000, contract_years=2
            )

    async def test_hire_staff_zero_wage_budget_club(self, db_session: AsyncSession):
        """Test hiring when club has zero wage budget."""
        # Create a club with zero wage budget
        club = Club(
            name="Broke FC",
            reputation=30,
            league="League Two",
            country="England",
            wage_budget=0,
            balance=100000,
            transfer_budget=0,
            matchday_revenue=10000,
            stadium_capacity=5000,
        )
        db_session.add(club)
        await db_session.commit()
        await db_session.refresh(club)

        service = StaffService(db_session)

        # Any hire should fail since 30% of 0 = 0
        with pytest.raises(ValueError, match="Cannot afford staff wage"):
            await service.hire_staff(
                career_id=1, club_id=club.id,
                name="Coach", role=StaffRole.FITNESS_COACH,
                age=40, nationality="England",
                attributes=DEFAULT_ATTRIBUTES, wage=5000, contract_years=1
            )
