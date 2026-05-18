"""
Unit tests for StaffService - Contract Expiry Handling

Tests for task 13.6: Staff contract expiry handling
- check_contract_expiries: checks for expired/expiring contracts
- renew_staff_contract: renews a staff contract
- process_expired_contracts: removes staff with expired contracts
- get_expiring_contracts: returns staff with contracts expiring soon
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService
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


def _default_attributes():
    """Helper to create default staff attributes."""
    return {
        "coaching": 15,
        "tactical_knowledge": 14,
        "man_management": 13,
        "scouting": 10,
        "medical": 10,
        "fitness": 16,
        "technical": 12,
        "mental": 11,
    }


async def _hire_staff_with_expiry(
    service: StaffService,
    db_session: AsyncSession,
    name: str,
    role: StaffRole,
    contract_start: datetime,
    contract_expiry: datetime,
    career_id: int = 1,
    club_id: int = 1,
    wage: int = 15000,
) -> Staff:
    """Helper to hire staff and set specific contract dates (bypassing CHECK constraint issues)."""
    staff = await service.hire_staff(
        career_id=career_id,
        club_id=club_id,
        name=name,
        role=role,
        age=45,
        nationality="England",
        attributes=_default_attributes(),
        wage=wage,
        contract_years=1,
    )
    # Update contract dates directly - both start and expiry to satisfy CHECK constraint
    staff.contract_start_date = contract_start
    staff.contract_expiry_date = contract_expiry
    await db_session.commit()
    await db_session.refresh(staff)
    return staff


@pytest.mark.asyncio
class TestCheckContractExpiries:
    """Test suite for check_contract_expiries()"""

    async def test_no_expiring_contracts(self, db_session: AsyncSession):
        """Test when no contracts are expiring"""
        service = StaffService(db_session)

        # Hire staff with long contracts (default 5 years)
        await service.hire_staff(
            career_id=1, club_id=1, name="Long Contract Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=_default_attributes(), wage=15000, contract_years=5
        )

        result = await service.check_contract_expiries(
            career_id=1, club_id=1, current_season=1, current_week=10
        )

        assert result["expired"] == []
        assert result["expiring_soon"] == []
        assert result["notifications"] == []

    async def test_expired_contract_detected(self, db_session: AsyncSession):
        """Test that expired contracts are detected"""
        service = StaffService(db_session)

        # Hire staff with contract that started 2 years ago and expired 7 days ago
        now = datetime.now()
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expired Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=730),
            contract_expiry=now - timedelta(days=7),
        )

        result = await service.check_contract_expiries(
            career_id=1, club_id=1, current_season=1, current_week=10
        )

        assert len(result["expired"]) == 1
        assert result["expired"][0]["name"] == "Expired Coach"
        # Should have a notification about the expired contract
        expired_notifications = [
            n for n in result["notifications"] if n["type"] == "contract_expired"
        ]
        assert len(expired_notifications) == 1
        assert "Expired Coach" in expired_notifications[0]["message"]

    async def test_expiring_soon_contract_detected(self, db_session: AsyncSession):
        """Test that contracts expiring within 26 weeks are detected"""
        service = StaffService(db_session)

        now = datetime.now()
        # Contract started 1 year ago, expires in 60 days (within 26 weeks)
        await _hire_staff_with_expiry(
            service, db_session,
            name="Soon Expiring Coach",
            role=StaffRole.DEFENSIVE_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=60),
        )

        result = await service.check_contract_expiries(
            career_id=1, club_id=1, current_season=1, current_week=20
        )

        assert result["expired"] == []
        assert len(result["expiring_soon"]) == 1
        assert result["expiring_soon"][0]["name"] == "Soon Expiring Coach"
        # Should have a notification about expiring soon
        expiring_notifications = [
            n for n in result["notifications"] if n["type"] == "contract_expiring_soon"
        ]
        assert len(expiring_notifications) == 1
        assert "Soon Expiring Coach" in expiring_notifications[0]["message"]

    async def test_mixed_expired_and_expiring(self, db_session: AsyncSession):
        """Test with both expired and expiring contracts"""
        service = StaffService(db_session)
        now = datetime.now()

        # Expired contract
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expired",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=730),
            contract_expiry=now - timedelta(days=10),
        )
        # Expiring soon contract
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expiring",
            role=StaffRole.DEFENSIVE_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=90),
        )
        # Safe contract (far in the future)
        await service.hire_staff(
            career_id=1, club_id=1, name="Safe",
            role=StaffRole.CHIEF_SCOUT, age=40, nationality="Germany",
            attributes=_default_attributes(), wage=20000, contract_years=5
        )

        result = await service.check_contract_expiries(
            career_id=1, club_id=1, current_season=1, current_week=15
        )

        assert len(result["expired"]) == 1
        assert len(result["expiring_soon"]) == 1
        assert len(result["notifications"]) == 2
        assert result["expired"][0]["name"] == "Expired"
        assert result["expiring_soon"][0]["name"] == "Expiring"


@pytest.mark.asyncio
class TestRenewStaffContract:
    """Test suite for renew_staff_contract()"""

    async def test_renew_contract_successfully(self, db_session: AsyncSession):
        """Test successful contract renewal"""
        service = StaffService(db_session)
        now = datetime.now()

        # Hire staff with contract expiring soon
        coach = await _hire_staff_with_expiry(
            service, db_session,
            name="Renewing Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=30),
        )

        # Renew the contract
        renewed = await service.renew_staff_contract(
            staff_id=coach.id, career_id=1, new_years=3, new_wage=20000
        )

        assert renewed is not None
        assert renewed.contract_years == 3
        assert renewed.wage == 20000
        # Contract should now expire in ~3 years from now
        expected_min_expiry = now + timedelta(days=365 * 2)
        assert renewed.contract_expiry_date > expected_min_expiry

    async def test_renew_contract_invalid_years(self, db_session: AsyncSession):
        """Test that invalid contract years raises ValueError"""
        service = StaffService(db_session)

        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=_default_attributes(), wage=15000, contract_years=2
        )

        with pytest.raises(ValueError, match="Contract years must be between 1 and 5"):
            await service.renew_staff_contract(
                staff_id=coach.id, career_id=1, new_years=6, new_wage=20000
            )

    async def test_renew_contract_invalid_wage(self, db_session: AsyncSession):
        """Test that invalid wage raises ValueError"""
        service = StaffService(db_session)

        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=_default_attributes(), wage=15000, contract_years=2
        )

        with pytest.raises(ValueError, match="Wage must be positive"):
            await service.renew_staff_contract(
                staff_id=coach.id, career_id=1, new_years=3, new_wage=0
            )

    async def test_renew_contract_staff_not_found(self, db_session: AsyncSession):
        """Test renewal returns None when staff not found"""
        service = StaffService(db_session)

        result = await service.renew_staff_contract(
            staff_id=999, career_id=1, new_years=3, new_wage=20000
        )

        assert result is None

    async def test_renew_contract_wrong_career(self, db_session: AsyncSession):
        """Test renewal returns None when career doesn't match"""
        service = StaffService(db_session)

        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=_default_attributes(), wage=15000, contract_years=2
        )

        # Try to renew with wrong career_id
        result = await service.renew_staff_contract(
            staff_id=coach.id, career_id=999, new_years=3, new_wage=20000
        )

        assert result is None


@pytest.mark.asyncio
class TestProcessExpiredContracts:
    """Test suite for process_expired_contracts()"""

    async def test_remove_expired_staff(self, db_session: AsyncSession):
        """Test that expired staff are removed from the club"""
        service = StaffService(db_session)
        now = datetime.now()

        await _hire_staff_with_expiry(
            service, db_session,
            name="Expired Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=730),
            contract_expiry=now - timedelta(days=7),
        )

        removed = await service.process_expired_contracts(career_id=1, club_id=1)

        assert len(removed) == 1
        assert removed[0]["name"] == "Expired Coach"
        assert removed[0]["role"] == StaffRole.FITNESS_COACH.value

        # Verify staff is actually removed from database
        all_staff = await service.get_all_staff(career_id=1)
        assert len(all_staff) == 0

    async def test_no_expired_contracts(self, db_session: AsyncSession):
        """Test when no contracts have expired"""
        service = StaffService(db_session)

        await service.hire_staff(
            career_id=1, club_id=1, name="Active Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=_default_attributes(), wage=15000, contract_years=5
        )

        removed = await service.process_expired_contracts(career_id=1, club_id=1)

        assert removed == []

        # Staff should still be there
        all_staff = await service.get_all_staff(career_id=1)
        assert len(all_staff) == 1

    async def test_only_expired_removed(self, db_session: AsyncSession):
        """Test that only expired contracts are removed, not expiring ones"""
        service = StaffService(db_session)
        now = datetime.now()

        # Expired contract
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expired",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=730),
            contract_expiry=now - timedelta(days=5),
        )
        # Active contract (long)
        await service.hire_staff(
            career_id=1, club_id=1, name="Active",
            role=StaffRole.DEFENSIVE_COACH, age=50, nationality="Spain",
            attributes=_default_attributes(), wage=18000, contract_years=5
        )
        # Expiring soon but not yet expired
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expiring Soon",
            role=StaffRole.CHIEF_SCOUT,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=60),
        )

        removed = await service.process_expired_contracts(career_id=1, club_id=1)

        assert len(removed) == 1
        assert removed[0]["name"] == "Expired"

        # 2 staff should remain
        all_staff = await service.get_all_staff(career_id=1)
        assert len(all_staff) == 2
        remaining_names = {s.name for s in all_staff}
        assert "Active" in remaining_names
        assert "Expiring Soon" in remaining_names

    async def test_multiple_expired_removed(self, db_session: AsyncSession):
        """Test that multiple expired contracts are all removed"""
        service = StaffService(db_session)
        now = datetime.now()

        roles = [StaffRole.FITNESS_COACH, StaffRole.DEFENSIVE_COACH, StaffRole.CHIEF_SCOUT]
        for i, role in enumerate(roles):
            await _hire_staff_with_expiry(
                service, db_session,
                name=f"Expired Coach {i+1}",
                role=role,
                contract_start=now - timedelta(days=730),
                contract_expiry=now - timedelta(days=i + 1),
            )

        removed = await service.process_expired_contracts(career_id=1, club_id=1)

        assert len(removed) == 3

        # All should be gone
        all_staff = await service.get_all_staff(career_id=1)
        assert len(all_staff) == 0


@pytest.mark.asyncio
class TestGetExpiringContracts:
    """Test suite for get_expiring_contracts()"""

    async def test_get_expiring_within_threshold(self, db_session: AsyncSession):
        """Test getting staff with contracts expiring within threshold"""
        service = StaffService(db_session)
        now = datetime.now()

        # Expiring in 80 days (within 26 weeks)
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expiring Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=80),
        )
        # Safe - far in the future
        await service.hire_staff(
            career_id=1, club_id=1, name="Safe Coach",
            role=StaffRole.DEFENSIVE_COACH, age=50, nationality="Spain",
            attributes=_default_attributes(), wage=18000, contract_years=5
        )

        result = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=26
        )

        assert len(result) == 1
        assert result[0]["name"] == "Expiring Coach"
        assert result[0]["role"] == StaffRole.FITNESS_COACH.value
        assert result[0]["months_remaining"] >= 0
        assert result[0]["weeks_remaining"] >= 0

    async def test_excludes_already_expired(self, db_session: AsyncSession):
        """Test that already expired contracts are excluded"""
        service = StaffService(db_session)
        now = datetime.now()

        # Already expired
        await _hire_staff_with_expiry(
            service, db_session,
            name="Expired Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=730),
            contract_expiry=now - timedelta(days=7),
        )

        result = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=26
        )

        assert len(result) == 0

    async def test_sorted_by_expiry_date(self, db_session: AsyncSession):
        """Test that results are sorted by expiry date (soonest first)"""
        service = StaffService(db_session)
        now = datetime.now()

        # Coach A - expires in 90 days
        await _hire_staff_with_expiry(
            service, db_session,
            name="Coach A",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=90),
        )
        # Coach B - expires in 30 days (soonest)
        await _hire_staff_with_expiry(
            service, db_session,
            name="Coach B",
            role=StaffRole.DEFENSIVE_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=30),
        )
        # Coach C - expires in 60 days
        await _hire_staff_with_expiry(
            service, db_session,
            name="Coach C",
            role=StaffRole.CHIEF_SCOUT,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(days=60),
        )

        result = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=26
        )

        assert len(result) == 3
        # Should be sorted: B (30 days), C (60 days), A (90 days)
        assert result[0]["name"] == "Coach B"
        assert result[1]["name"] == "Coach C"
        assert result[2]["name"] == "Coach A"

    async def test_custom_weeks_threshold(self, db_session: AsyncSession):
        """Test with a custom weeks threshold"""
        service = StaffService(db_session)
        now = datetime.now()

        # Contract expires in 10 weeks
        await _hire_staff_with_expiry(
            service, db_session,
            name="Coach",
            role=StaffRole.FITNESS_COACH,
            contract_start=now - timedelta(days=365),
            contract_expiry=now + timedelta(weeks=10),
        )

        # With 8-week threshold, should not be included
        result_8 = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=8
        )
        assert len(result_8) == 0

        # With 12-week threshold, should be included
        result_12 = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=12
        )
        assert len(result_12) == 1

    async def test_includes_staff_quality_info(self, db_session: AsyncSession):
        """Test that results include staff quality information"""
        service = StaffService(db_session)
        now = datetime.now()

        elite_attrs = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 19,  # Elite level
            "technical": 10,
            "mental": 10,
        }

        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Elite Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=elite_attrs, wage=25000, contract_years=1
        )

        # Set contract to expire soon
        coach.contract_start_date = now - timedelta(days=365)
        coach.contract_expiry_date = now + timedelta(days=60)
        await db_session.commit()

        result = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=26
        )

        assert len(result) == 1
        assert result[0]["primary_attribute"] == 19
        assert result[0]["is_elite"] is True
        assert result[0]["is_good"] is True

    async def test_empty_when_no_staff(self, db_session: AsyncSession):
        """Test returns empty list when no staff exist"""
        service = StaffService(db_session)

        result = await service.get_expiring_contracts(
            career_id=1, club_id=1, weeks_threshold=26
        )

        assert result == []
