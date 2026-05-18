"""
Unit tests for Staff Morale Simulation (Task 13.8)

Tests the following methods in StaffService:
- simulate_weekly_morale(career_id, club_id, match_results)
- get_morale_factors(staff, match_results, club)
- apply_morale_effects(career_id)
"""

import pytest
import random
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService
from app.models.staff import Staff, StaffRole
from app.models.club import Club
from app.models.user import User
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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if gin_index:
        players_table.indexes.add(gin_index)

    yield engine

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
async def setup_data(db_session):
    """Create test user, club, career, and staff members"""
    # Create user
    user = User(telegram_user_id=12345, username="test_user")
    db_session.add(user)
    await db_session.flush()

    # Create club
    club = Club(
        name="Test FC",
        reputation=60,
        league="Test League",
        country="England",
        balance=5000000,
        transfer_budget=1000000,
        wage_budget=200000,
        matchday_revenue=50000,
        stadium_capacity=30000,
    )
    db_session.add(club)
    await db_session.flush()

    # Create career
    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Test Manager",
        current_season=1,
        current_week=10,
    )
    db_session.add(career)
    await db_session.flush()

    # Create staff members with varying attributes
    now = datetime.now()

    # High quality, well-paid staff (happy)
    staff_happy = Staff(
        career_id=career.id,
        club_id=club.id,
        name="John Smith",
        role=StaffRole.FITNESS_COACH,
        age=45,
        nationality="England",
        coaching=16,
        tactical_knowledge=14,
        man_management=15,
        scouting=10,
        medical=10,
        fitness=18,
        technical=14,
        mental=13,
        wage=15000,
        contract_start_date=now - timedelta(days=180),
        contract_expiry_date=now + timedelta(days=730),
        contract_years=3,
        morale=75,
        performance_rating=15,
    )

    # Average quality, underpaid staff (unhappy about wages)
    staff_underpaid = Staff(
        career_id=career.id,
        club_id=club.id,
        name="Carlos Garcia",
        role=StaffRole.ATTACKING_COACH,
        age=38,
        nationality="Spain",
        coaching=14,
        tactical_knowledge=13,
        man_management=12,
        scouting=8,
        medical=7,
        fitness=11,
        technical=13,
        mental=12,
        wage=5000,  # Underpaid for quality
        contract_start_date=now - timedelta(days=365),
        contract_expiry_date=now + timedelta(days=365),
        contract_years=2,
        morale=50,
        performance_rating=12,
    )

    # Staff with expiring contract (low morale)
    staff_expiring = Staff(
        career_id=career.id,
        club_id=club.id,
        name="Hans Mueller",
        role=StaffRole.CHIEF_SCOUT,
        age=52,
        nationality="Germany",
        coaching=10,
        tactical_knowledge=12,
        man_management=11,
        scouting=17,
        medical=8,
        fitness=9,
        technical=10,
        mental=11,
        wage=12000,
        contract_start_date=now - timedelta(days=700),
        contract_expiry_date=now + timedelta(days=60),  # ~2 months remaining
        contract_years=2,
        morale=35,
        performance_rating=14,
    )

    # High quality staff at low reputation club (overqualified)
    staff_overqualified = Staff(
        career_id=career.id,
        club_id=club.id,
        name="Pierre Dupont",
        role=StaffRole.ASSISTANT_MANAGER,
        age=48,
        nationality="France",
        coaching=18,
        tactical_knowledge=19,
        man_management=17,
        scouting=14,
        medical=12,
        fitness=15,
        technical=16,
        mental=17,
        wage=25000,
        contract_start_date=now - timedelta(days=90),
        contract_expiry_date=now + timedelta(days=1095),
        contract_years=3,
        morale=60,
        performance_rating=17,
    )

    db_session.add_all([staff_happy, staff_underpaid, staff_expiring, staff_overqualified])
    await db_session.commit()

    return {
        "user": user,
        "club": club,
        "career": career,
        "staff_happy": staff_happy,
        "staff_underpaid": staff_underpaid,
        "staff_expiring": staff_expiring,
        "staff_overqualified": staff_overqualified,
    }


class TestGetMoraleFactors:
    """Tests for get_morale_factors method"""

    @pytest.mark.asyncio
    async def test_winning_matches_positive_morale(self, db_session, setup_data):
        """Winning matches should increase morale"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]
        match_results = [{"result": "win", "score_diff": 2}]

        factors = service.get_morale_factors(staff, match_results, setup_data["club"])

        assert factors["team_performance"] > 0
        assert factors["team_performance"] == 3.0

    @pytest.mark.asyncio
    async def test_losing_matches_negative_morale(self, db_session, setup_data):
        """Losing matches should decrease morale"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]
        match_results = [{"result": "loss", "score_diff": -2}]

        factors = service.get_morale_factors(staff, match_results, setup_data["club"])

        assert factors["team_performance"] < 0
        assert factors["team_performance"] == -4.0

    @pytest.mark.asyncio
    async def test_draw_slight_positive(self, db_session, setup_data):
        """Draws should give a slight positive morale change"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]
        match_results = [{"result": "draw", "score_diff": 0}]

        factors = service.get_morale_factors(staff, match_results, setup_data["club"])

        assert factors["team_performance"] == 0.5

    @pytest.mark.asyncio
    async def test_multiple_matches_cumulative(self, db_session, setup_data):
        """Multiple match results should accumulate"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]
        match_results = [
            {"result": "win", "score_diff": 1},
            {"result": "win", "score_diff": 3},
        ]

        factors = service.get_morale_factors(staff, match_results, setup_data["club"])

        assert factors["team_performance"] == 6.0  # 3.0 + 3.0

    @pytest.mark.asyncio
    async def test_underpaid_staff_negative_wage_factor(self, db_session, setup_data):
        """Underpaid staff should have negative wage satisfaction"""
        service = StaffService(db_session)
        staff = setup_data["staff_underpaid"]

        factors = service.get_morale_factors(staff, [], setup_data["club"])

        assert factors["wage_satisfaction"] < 0

    @pytest.mark.asyncio
    async def test_well_paid_staff_positive_wage_factor(self, db_session, setup_data):
        """Well-paid staff should have positive or neutral wage satisfaction"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]

        factors = service.get_morale_factors(staff, [], setup_data["club"])

        # Staff with avg attr ~13.75, expected wage ~13750, actual wage 15000
        # 15000 >= 13750 * 1.2 = 16500? No. So should be 0.0
        assert factors["wage_satisfaction"] >= 0

    @pytest.mark.asyncio
    async def test_expiring_contract_negative_factor(self, db_session, setup_data):
        """Staff with expiring contract should have negative contract factor"""
        service = StaffService(db_session)
        staff = setup_data["staff_expiring"]

        factors = service.get_morale_factors(staff, [], setup_data["club"])

        assert factors["contract_length"] < 0

    @pytest.mark.asyncio
    async def test_long_contract_no_penalty(self, db_session, setup_data):
        """Staff with long contract should have no contract penalty"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]

        factors = service.get_morale_factors(staff, [], setup_data["club"])

        assert factors["contract_length"] == 0.0

    @pytest.mark.asyncio
    async def test_overqualified_staff_negative_reputation_factor(self, db_session, setup_data):
        """Overqualified staff at lower reputation club should have negative factor"""
        service = StaffService(db_session)
        staff = setup_data["staff_overqualified"]
        club = setup_data["club"]  # reputation=60

        factors = service.get_morale_factors(staff, [], club)

        # Staff avg attr ~16, scaled = 80. Club rep = 60. Diff = 20.
        # quality_diff > 10 so should be -2.0 or -4.0
        assert factors["reputation_mismatch"] < 0

    @pytest.mark.asyncio
    async def test_random_events_within_range(self, db_session, setup_data):
        """Random events factor should be within -2 to +2"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]

        # Run multiple times to check range
        for _ in range(50):
            factors = service.get_morale_factors(staff, [], setup_data["club"])
            assert -2.0 <= factors["random_events"] <= 2.0

    @pytest.mark.asyncio
    async def test_no_match_results_zero_performance(self, db_session, setup_data):
        """No match results should give zero team performance factor"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]

        factors = service.get_morale_factors(staff, None, setup_data["club"])

        assert factors["team_performance"] == 0.0

    @pytest.mark.asyncio
    async def test_no_club_zero_reputation_factor(self, db_session, setup_data):
        """No club provided should give zero reputation mismatch factor"""
        service = StaffService(db_session)
        staff = setup_data["staff_happy"]

        factors = service.get_morale_factors(staff, [], None)

        assert factors["reputation_mismatch"] == 0.0


class TestSimulateWeeklyMorale:
    """Tests for simulate_weekly_morale method"""

    @pytest.mark.asyncio
    async def test_morale_updates_all_staff(self, db_session, setup_data):
        """Should update morale for all staff at the club"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]

        match_results = [{"result": "win", "score_diff": 2}]

        with patch("random.uniform", return_value=0.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        assert len(updates) == 4  # 4 staff members

    @pytest.mark.asyncio
    async def test_winning_increases_morale(self, db_session, setup_data):
        """Winning matches should generally increase staff morale"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]
        staff_happy = setup_data["staff_happy"]
        old_morale = staff_happy.morale

        match_results = [
            {"result": "win", "score_diff": 3},
            {"result": "win", "score_diff": 1},
        ]

        with patch("random.uniform", return_value=0.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        # Find the happy staff update
        happy_update = next(u for u in updates if u["staff_id"] == staff_happy.id)
        assert happy_update["new_morale"] >= old_morale

    @pytest.mark.asyncio
    async def test_losing_decreases_morale(self, db_session, setup_data):
        """Losing matches should generally decrease staff morale"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]
        staff_happy = setup_data["staff_happy"]
        old_morale = staff_happy.morale

        match_results = [
            {"result": "loss", "score_diff": -3},
            {"result": "loss", "score_diff": -2},
        ]

        with patch("random.uniform", return_value=0.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        happy_update = next(u for u in updates if u["staff_id"] == staff_happy.id)
        assert happy_update["new_morale"] <= old_morale

    @pytest.mark.asyncio
    async def test_morale_clamped_to_valid_range(self, db_session, setup_data):
        """Morale should never go below 1 or above 100"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]

        # Set staff to extreme morale values
        staff_happy = setup_data["staff_happy"]
        staff_happy.morale = 99
        await db_session.commit()

        match_results = [
            {"result": "win", "score_diff": 5},
            {"result": "win", "score_diff": 5},
        ]

        with patch("random.uniform", return_value=2.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        for update in updates:
            assert 1 <= update["new_morale"] <= 100

    @pytest.mark.asyncio
    async def test_weekly_change_clamped(self, db_session, setup_data):
        """Weekly morale change should be clamped to ±15"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]

        # Many losses to try to exceed the limit
        match_results = [
            {"result": "loss", "score_diff": -5},
            {"result": "loss", "score_diff": -5},
            {"result": "loss", "score_diff": -5},
            {"result": "loss", "score_diff": -5},
            {"result": "loss", "score_diff": -5},
        ]

        with patch("random.uniform", return_value=-2.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        for update in updates:
            assert abs(update["change"]) <= 15

    @pytest.mark.asyncio
    async def test_empty_staff_returns_empty(self, db_session, setup_data):
        """Should return empty list if no staff at the club"""
        service = StaffService(db_session)
        career = setup_data["career"]

        # Use a non-existent club_id
        updates = await service.simulate_weekly_morale(
            career.id, 99999, [{"result": "win", "score_diff": 1}]
        )

        assert updates == []

    @pytest.mark.asyncio
    async def test_update_contains_factors(self, db_session, setup_data):
        """Each update should contain the individual factors"""
        service = StaffService(db_session)
        career = setup_data["career"]
        club = setup_data["club"]

        match_results = [{"result": "win", "score_diff": 1}]

        with patch("random.uniform", return_value=1.0):
            updates = await service.simulate_weekly_morale(
                career.id, club.id, match_results
            )

        for update in updates:
            assert "factors" in update
            assert "team_performance" in update["factors"]
            assert "wage_satisfaction" in update["factors"]
            assert "contract_length" in update["factors"]
            assert "reputation_mismatch" in update["factors"]
            assert "random_events" in update["factors"]


class TestApplyMoraleEffects:
    """Tests for apply_morale_effects method"""

    @pytest.mark.asyncio
    async def test_high_morale_full_effectiveness(self, db_session, setup_data):
        """Staff with high morale should have full effectiveness"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff_happy = setup_data["staff_happy"]

        # Ensure high morale
        staff_happy.morale = 80
        await db_session.commit()

        result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff_happy.id] == 1.0

    @pytest.mark.asyncio
    async def test_medium_morale_normal_effectiveness(self, db_session, setup_data):
        """Staff with medium morale should have normal effectiveness"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff_underpaid = setup_data["staff_underpaid"]

        # Set medium morale
        staff_underpaid.morale = 55
        await db_session.commit()

        result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff_underpaid.id] == 1.0

    @pytest.mark.asyncio
    async def test_low_morale_reduced_effectiveness(self, db_session, setup_data):
        """Staff with low morale should have reduced effectiveness"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff_expiring = setup_data["staff_expiring"]

        # Ensure low morale
        staff_expiring.morale = 25
        await db_session.commit()

        result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff_expiring.id] == 0.75

    @pytest.mark.asyncio
    async def test_low_morale_may_request_leave(self, db_session, setup_data):
        """Staff with low morale may request to leave"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff_expiring = setup_data["staff_expiring"]

        # Set very low morale
        staff_expiring.morale = 20
        await db_session.commit()

        # Force the random check to trigger a leave request
        with patch("random.random", return_value=0.05):  # Below 0.15 threshold
            result = await service.apply_morale_effects(career.id)

        assert len(result["leave_requests"]) >= 1
        leave_request = next(
            (r for r in result["leave_requests"] if r["staff_id"] == staff_expiring.id),
            None
        )
        assert leave_request is not None
        assert "requested to leave" in leave_request["message"]

    @pytest.mark.asyncio
    async def test_low_morale_no_leave_request_when_random_high(self, db_session, setup_data):
        """Staff with low morale should not always request to leave"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff_expiring = setup_data["staff_expiring"]

        # Set low morale
        staff_expiring.morale = 30
        # Set other staff to high morale so they don't interfere
        setup_data["staff_happy"].morale = 80
        setup_data["staff_underpaid"].morale = 50
        setup_data["staff_overqualified"].morale = 70
        await db_session.commit()

        # Force the random check to NOT trigger a leave request
        with patch("random.random", return_value=0.90):  # Above 0.15 threshold
            result = await service.apply_morale_effects(career.id)

        # staff_expiring should be in low_morale_warnings, not leave_requests
        leave_ids = [r["staff_id"] for r in result["leave_requests"]]
        assert staff_expiring.id not in leave_ids

        warning_ids = [w["staff_id"] for w in result["low_morale_warnings"]]
        assert staff_expiring.id in warning_ids

    @pytest.mark.asyncio
    async def test_returns_all_effectiveness_modifiers(self, db_session, setup_data):
        """Should return effectiveness modifiers for all staff"""
        service = StaffService(db_session)
        career = setup_data["career"]

        result = await service.apply_morale_effects(career.id)

        assert len(result["effectiveness_modifiers"]) == 4

    @pytest.mark.asyncio
    async def test_boundary_morale_70_is_high(self, db_session, setup_data):
        """Morale of exactly 70 should be considered high"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff = setup_data["staff_happy"]

        staff.morale = 70
        await db_session.commit()

        result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff.id] == 1.0

    @pytest.mark.asyncio
    async def test_boundary_morale_40_is_medium(self, db_session, setup_data):
        """Morale of exactly 40 should be considered medium"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff = setup_data["staff_happy"]

        staff.morale = 40
        await db_session.commit()

        result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff.id] == 1.0

    @pytest.mark.asyncio
    async def test_boundary_morale_39_is_low(self, db_session, setup_data):
        """Morale of 39 should be considered low"""
        service = StaffService(db_session)
        career = setup_data["career"]
        staff = setup_data["staff_happy"]

        staff.morale = 39
        await db_session.commit()

        with patch("random.random", return_value=0.99):
            result = await service.apply_morale_effects(career.id)

        assert result["effectiveness_modifiers"][staff.id] == 0.75
