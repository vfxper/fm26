"""
Unit tests for Staff Contract Negotiation (Task 13.9)

Tests the negotiation logic including:
- get_staff_wage_expectation
- get_staff_contract_expectation
- negotiate_contract (accept, counter-offer, reject)
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService, NegotiationResult
from app.models.staff import Staff, StaffRole


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


def create_staff(
    career_id: int = 1,
    club_id: int = 1,
    name: str = "Test Coach",
    role: StaffRole = StaffRole.FITNESS_COACH,
    age: int = 40,
    coaching: int = 10,
    tactical_knowledge: int = 10,
    man_management: int = 10,
    scouting: int = 10,
    medical: int = 10,
    fitness: int = 10,
    technical: int = 10,
    mental: int = 10,
    wage: int = 15000,
    contract_years: int = 2,
    morale: int = 70,
) -> Staff:
    """Helper to create a Staff instance for testing."""
    now = datetime.now()
    return Staff(
        career_id=career_id,
        club_id=club_id,
        name=name,
        role=role,
        age=age,
        nationality="England",
        coaching=coaching,
        tactical_knowledge=tactical_knowledge,
        man_management=man_management,
        scouting=scouting,
        medical=medical,
        fitness=fitness,
        technical=technical,
        mental=mental,
        wage=wage,
        contract_start_date=now,
        contract_expiry_date=now + timedelta(days=365 * contract_years),
        contract_years=contract_years,
        morale=morale,
        performance_rating=10,
    )


@pytest.mark.asyncio
class TestStaffWageExpectation:
    """Tests for get_staff_wage_expectation"""

    async def test_average_staff_wage_expectation(self, db_session: AsyncSession):
        """Average staff (all attributes 10) expects 10 * 1500 = 15000"""
        service = StaffService(db_session)
        staff = create_staff()  # All attributes default to 10

        expected_wage = service.get_staff_wage_expectation(staff)
        assert expected_wage == 15000

    async def test_high_quality_staff_wage_expectation(self, db_session: AsyncSession):
        """High quality staff (all attributes 16) expects 16 * 1500 = 24000"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=16, tactical_knowledge=16, man_management=16,
            scouting=16, medical=16, fitness=16, technical=16, mental=16
        )

        expected_wage = service.get_staff_wage_expectation(staff)
        assert expected_wage == 24000

    async def test_elite_staff_wage_expectation(self, db_session: AsyncSession):
        """Elite staff (all attributes 18) expects 18 * 1500 = 27000"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=18, tactical_knowledge=18, man_management=18,
            scouting=18, medical=18, fitness=18, technical=18, mental=18
        )

        expected_wage = service.get_staff_wage_expectation(staff)
        assert expected_wage == 27000

    async def test_low_quality_staff_wage_expectation(self, db_session: AsyncSession):
        """Low quality staff (all attributes 5) expects 5 * 1500 = 7500"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=5, tactical_knowledge=5, man_management=5,
            scouting=5, medical=5, fitness=5, technical=5, mental=5
        )

        expected_wage = service.get_staff_wage_expectation(staff)
        assert expected_wage == 7500

    async def test_mixed_attributes_wage_expectation(self, db_session: AsyncSession):
        """Staff with mixed attributes uses average for wage calculation"""
        service = StaffService(db_session)
        # Average = (20 + 5 + 10 + 10 + 10 + 10 + 10 + 10) / 8 = 10.625
        staff = create_staff(coaching=20, tactical_knowledge=5)

        expected_wage = service.get_staff_wage_expectation(staff)
        # 10.625 * 1500 = 15937.5 -> int = 15937
        assert expected_wage == 15937


@pytest.mark.asyncio
class TestStaffContractExpectation:
    """Tests for get_staff_contract_expectation"""

    async def test_average_staff_expects_1_year(self, db_session: AsyncSession):
        """Average staff (attr < 16) expects minimum 1 year"""
        service = StaffService(db_session)
        staff = create_staff()  # All attributes 10

        expected_years = service.get_staff_contract_expectation(staff)
        assert expected_years == 1

    async def test_high_quality_staff_expects_2_years(self, db_session: AsyncSession):
        """High quality staff (attr >= 16) expects minimum 2 years"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=16, tactical_knowledge=16, man_management=16,
            scouting=16, medical=16, fitness=16, technical=16, mental=16
        )

        expected_years = service.get_staff_contract_expectation(staff)
        assert expected_years == 2

    async def test_elite_staff_expects_3_years(self, db_session: AsyncSession):
        """Elite staff (attr >= 18) expects minimum 3 years"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=18, tactical_knowledge=18, man_management=18,
            scouting=18, medical=18, fitness=18, technical=18, mental=18
        )

        expected_years = service.get_staff_contract_expectation(staff)
        assert expected_years == 3

    async def test_borderline_high_quality(self, db_session: AsyncSession):
        """Staff with exactly 16 average expects 2 years"""
        service = StaffService(db_session)
        staff = create_staff(
            coaching=16, tactical_knowledge=16, man_management=16,
            scouting=16, medical=16, fitness=16, technical=16, mental=16
        )

        expected_years = service.get_staff_contract_expectation(staff)
        assert expected_years == 2


@pytest.mark.asyncio
class TestNegotiateContract:
    """Tests for negotiate_contract"""

    async def test_accept_when_offer_meets_expectations(self, db_session: AsyncSession):
        """Staff accepts when offered wage and years meet expectations"""
        service = StaffService(db_session)

        # Create average staff (expects 15000/week, 1 year min)
        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=3,
            offered_wage=15000
        )

        assert result.outcome == "accepted"
        assert result.offered_years == 3
        assert result.offered_wage == 15000

    async def test_accept_when_offer_exceeds_expectations(self, db_session: AsyncSession):
        """Staff accepts when offered more than expected"""
        service = StaffService(db_session)

        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=5,
            offered_wage=25000
        )

        assert result.outcome == "accepted"

    async def test_counter_offer_when_wage_slightly_low(self, db_session: AsyncSession):
        """Staff counter-offers when wage is between 60-100% of expected"""
        service = StaffService(db_session)

        # Staff expects 15000/week (avg attr 10)
        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer 70% of expected wage (10500)
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=3,
            offered_wage=10500
        )

        assert result.outcome == "counter_offer"
        assert result.counter_wage == 15000  # They want their expected wage
        assert result.counter_years is not None

    async def test_counter_offer_when_years_too_short(self, db_session: AsyncSession):
        """High quality staff counter-offers with more years when offered too few"""
        service = StaffService(db_session)

        # High quality staff expects minimum 2 years
        staff = create_staff(
            coaching=16, tactical_knowledge=16, man_management=16,
            scouting=16, medical=16, fitness=16, technical=16, mental=16,
            wage=24000
        )
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer good wage but only 1 year (below their 2-year minimum)
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=1,
            offered_wage=20000  # ~83% of expected 24000
        )

        assert result.outcome == "counter_offer"
        assert result.counter_years >= 2  # They want at least 2 years

    async def test_reject_when_wage_far_too_low(self, db_session: AsyncSession):
        """Staff rejects when offered wage is below 60% of expected"""
        service = StaffService(db_session)

        # Staff expects 15000/week
        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer only 5000 (33% of expected) - far too low
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=3,
            offered_wage=5000
        )

        assert result.outcome == "rejected"

    async def test_low_morale_staff_accepts_lower_offer(self, db_session: AsyncSession):
        """Staff with low morale accepts offers below normal expectations"""
        service = StaffService(db_session)

        # Low morale staff (morale=30, below threshold of 40)
        # Expects 15000/week but will accept 80% (12000) due to morale
        staff = create_staff(morale=30)
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer 80% of expected wage - normally would counter, but low morale accepts
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=2,
            offered_wage=12000  # 80% of 15000
        )

        assert result.outcome == "accepted"

    async def test_invalid_years_raises_error(self, db_session: AsyncSession):
        """Negotiation raises ValueError for invalid contract years"""
        service = StaffService(db_session)

        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        with pytest.raises(ValueError, match="Contract years must be between 1 and 5"):
            await service.negotiate_contract(
                staff_id=staff.id,
                career_id=1,
                offered_years=0,
                offered_wage=15000
            )

        with pytest.raises(ValueError, match="Contract years must be between 1 and 5"):
            await service.negotiate_contract(
                staff_id=staff.id,
                career_id=1,
                offered_years=6,
                offered_wage=15000
            )

    async def test_invalid_wage_raises_error(self, db_session: AsyncSession):
        """Negotiation raises ValueError for invalid wage"""
        service = StaffService(db_session)

        staff = create_staff()
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        with pytest.raises(ValueError, match="Wage must be positive"):
            await service.negotiate_contract(
                staff_id=staff.id,
                career_id=1,
                offered_years=2,
                offered_wage=0
            )

    async def test_staff_not_found_raises_error(self, db_session: AsyncSession):
        """Negotiation raises ValueError when staff not found"""
        service = StaffService(db_session)

        with pytest.raises(ValueError, match="not found"):
            await service.negotiate_contract(
                staff_id=9999,
                career_id=1,
                offered_years=2,
                offered_wage=15000
            )

    async def test_elite_staff_rejects_short_contract_low_wage(self, db_session: AsyncSession):
        """Elite staff rejects when both wage and years are inadequate"""
        service = StaffService(db_session)

        # Elite staff expects 27000/week, 3 years minimum
        staff = create_staff(
            coaching=18, tactical_knowledge=18, man_management=18,
            scouting=18, medical=18, fitness=18, technical=18, mental=18,
            wage=30000
        )
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer far below expectations
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=1,
            offered_wage=10000  # ~37% of expected 27000
        )

        assert result.outcome == "rejected"

    async def test_negotiation_result_has_reason(self, db_session: AsyncSession):
        """All negotiation results include a reason string"""
        service = StaffService(db_session)

        staff = create_staff(name="Bob Smith")
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Test accepted
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=3,
            offered_wage=15000
        )
        assert "Bob Smith" in result.reason
        assert len(result.reason) > 0

    async def test_counter_offer_years_clamped_to_5(self, db_session: AsyncSession):
        """Counter-offer years are clamped to maximum of 5"""
        service = StaffService(db_session)

        # Elite staff expects 3 years minimum
        staff = create_staff(
            coaching=18, tactical_knowledge=18, man_management=18,
            scouting=18, medical=18, fitness=18, technical=18, mental=18,
            wage=30000
        )
        db_session.add(staff)
        await db_session.commit()
        await db_session.refresh(staff)

        # Offer 5 years but low wage -> counter-offer
        result = await service.negotiate_contract(
            staff_id=staff.id,
            career_id=1,
            offered_years=5,
            offered_wage=18000  # ~67% of expected 27000
        )

        assert result.outcome == "counter_offer"
        assert result.counter_years <= 5
        assert result.counter_years >= 1
