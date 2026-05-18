"""
Tests for MedicalService - Comprehensive medical module testing.

Tests cover:
- Task 14.1: Injury simulation during matches
- Task 14.2: 3 injury severity levels (Minor, Moderate, Severe)
- Task 14.3: Injury recovery timeline system
- Task 14.4: Injury list screen
- Task 14.5: Matchday squad prevention for injured players
- Task 14.6: Training ground injury simulation
- Task 14.7: Match sharpness penalty after injury return
- Task 14.8: Injury history tracking
- Task 14.9: Injury-prone flag (3+ injuries per season)
- Task 14.10: Fatigue accumulation system
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.injury import Injury, InjurySeverity, InjuryStatus
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.career import Career
from app.models.club import Club
from app.models.user import User
from app.services.medical_service import (
    MedicalService,
    FATIGUE_PER_90_MINUTES,
    FATIGUE_RECOVERY_PER_WEEK,
    MAX_FATIGUE,
    MIN_FATIGUE,
    HIGH_FATIGUE_THRESHOLD,
    SHARPNESS_PENALTY_PERCENT,
    SHARPNESS_PENALTY_WEEKS,
    INJURY_PRONE_THRESHOLD,
    INJURY_PRONE_RISK_INCREASE,
    MATCH_INJURY_TYPES,
    TRAINING_INJURY_TYPES,
)


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create test database session with in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            # Filter out PostgreSQL-specific indexes
            pg_indexes = [
                idx for idx in table.indexes
                if 'fts' in idx.name or 'tsvector' in str(idx.expressions)
            ]
            for idx in pg_indexes:
                table.indexes.discard(idx)

            await conn.run_sync(
                lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True)
            )

            for idx in pg_indexes:
                table.indexes.add(idx)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def medical_service(db_session):
    """Create MedicalService instance."""
    return MedicalService(db_session)


@pytest.fixture
async def setup_career(db_session):
    """Create a career with club, user, player, and squad_player for testing."""
    from datetime import date

    # Create user
    user = User(
        telegram_user_id=123456789,
        username="test_manager",
        first_name="Test",
        last_name="Manager",
    )
    db_session.add(user)
    await db_session.flush()

    # Create club
    club = Club(
        name="Test FC",
        league="Premier League",
        country="England",
        reputation=80,
        stadium_level=3,
        training_facilities_level=3,
        youth_academy_level=2,
        medical_centre_level=3,
        scouting_network_level=2,
        transfer_budget=50000000,
        wage_budget=2000000,
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

    # Create player
    player = Player(
        uid="TEST_PLAYER_001",
        name="John Smith",
        position="ST",
        age=25,
        nationality="England",
        club="Test FC",
        ca=140,
        pa=160,
        corners=10,
        crossing=12,
        dribbling=14,
        finishing=16,
        first_touch=13,
        free_kicks=8,
        heading=12,
        long_shots=11,
        long_throws=5,
        marking=6,
        passing=13,
        penalty=12,
        tackling=7,
        technique=14,
        aggression=12,
        anticipation=14,
        bravery=13,
        composure=15,
        concentration=13,
        decisions=14,
        determination=16,
        flair=12,
        leadership=10,
        off_the_ball=15,
        positioning=8,
        teamwork=14,
        vision=12,
        work_rate=15,
        acceleration=15,
        agility=14,
        balance=13,
        jumping=12,
        stamina=16,
        pace=15,
        endurance=14,
        strength=13,
        price="£10M",
        wage=100000,
        height=180,
        weight=75,
        left_foot=15,
        right_foot=10,
    )
    db_session.add(player)
    await db_session.flush()

    # Create squad player
    squad_player = SquadPlayer(
        career_id=career.id,
        player_id=player.id,
        contract_start_date=date(2025, 7, 1),
        contract_end_date=date(2028, 6, 30),
        wage=100000,
        squad_number=9,
        squad_status="FIRST_TEAM",
        morale=75,
        appearances=15,
        goals=8,
        assists=3,
        minutes_played=1200,
    )
    db_session.add(squad_player)
    await db_session.flush()

    await db_session.commit()

    return {
        "career": career,
        "club": club,
        "player": player,
        "squad_player": squad_player,
        "user": user,
    }


# ─── Task 14.1: Match Injury Simulation Tests ─────────────────────────────


class TestMatchInjurySimulation:
    """Tests for match injury simulation (Task 14.1)."""

    def test_simulate_match_injury_returns_none_most_of_time(self, medical_service):
        """Most match simulations should not result in injury."""
        injuries = 0
        trials = 1000
        for _ in range(trials):
            result = medical_service.simulate_match_injury(
                player_ca=140,
                player_age=25,
                player_stamina=15,
                player_bravery=12,
                player_strength=14,
            )
            if result is not None:
                injuries += 1

        # With ~3% base rate, expect roughly 30 injuries in 1000 trials
        # Allow wide range due to randomness
        assert injuries < 200  # Should not be excessively high

    def test_simulate_match_injury_returns_valid_structure(self, medical_service):
        """When injury occurs, it should have correct structure."""
        with patch("random.random", side_effect=[0.01, 0.5]):
            # First random.random() < probability triggers injury
            # Second random.random() determines severity (0.5 = minor since < 0.70)
            result = medical_service.simulate_match_injury(
                player_ca=140,
                player_age=25,
                player_stamina=10,
                player_bravery=10,
                player_strength=10,
            )

        assert result is not None
        assert "injury_type" in result
        assert "severity" in result
        assert "recovery_weeks" in result
        assert "is_match_injury" in result
        assert result["is_match_injury"] is True
        assert result["injury_type"] in MATCH_INJURY_TYPES

    def test_older_players_have_higher_injury_risk(self, medical_service):
        """Players over 30 should have higher injury probability."""
        young_injuries = 0
        old_injuries = 0
        trials = 5000

        for _ in range(trials):
            young_result = medical_service.simulate_match_injury(
                player_ca=140, player_age=22, player_stamina=15,
                player_bravery=12, player_strength=14,
            )
            old_result = medical_service.simulate_match_injury(
                player_ca=140, player_age=33, player_stamina=15,
                player_bravery=12, player_strength=14,
            )
            if young_result:
                young_injuries += 1
            if old_result:
                old_injuries += 1

        # Older players should get injured more often
        assert old_injuries > young_injuries

    def test_injury_prone_increases_risk(self, medical_service):
        """Injury-prone flag should increase injury probability by 15%."""
        normal_injuries = 0
        prone_injuries = 0
        trials = 10000

        for _ in range(trials):
            normal = medical_service.simulate_match_injury(
                player_ca=140, player_age=25, player_stamina=12,
                player_bravery=12, player_strength=12, is_injury_prone=False,
            )
            prone = medical_service.simulate_match_injury(
                player_ca=140, player_age=25, player_stamina=12,
                player_bravery=12, player_strength=12, is_injury_prone=True,
            )
            if normal:
                normal_injuries += 1
            if prone:
                prone_injuries += 1

        # With 15% increase, prone rate should be higher
        # Use ratio check to avoid flakiness
        normal_rate = normal_injuries / trials
        prone_rate = prone_injuries / trials
        assert prone_rate > normal_rate * 1.05

    def test_high_fatigue_increases_injury_risk(self, medical_service):
        """High fatigue should increase injury probability."""
        rested_injuries = 0
        fatigued_injuries = 0
        trials = 5000

        for _ in range(trials):
            rested = medical_service.simulate_match_injury(
                player_ca=140, player_age=25, player_stamina=12,
                player_bravery=12, player_strength=12, fatigue=20.0,
            )
            fatigued = medical_service.simulate_match_injury(
                player_ca=140, player_age=25, player_stamina=12,
                player_bravery=12, player_strength=12, fatigue=90.0,
            )
            if rested:
                rested_injuries += 1
            if fatigued:
                fatigued_injuries += 1

        assert fatigued_injuries > rested_injuries


# ─── Task 14.2: Injury Severity Levels Tests ──────────────────────────────


class TestInjurySeverityLevels:
    """Tests for 3 injury severity levels (Task 14.2)."""

    def test_severity_distribution(self, medical_service):
        """Severity should follow 70% minor, 25% moderate, 5% severe."""
        minor_count = 0
        moderate_count = 0
        severe_count = 0
        total = 10000

        for _ in range(total):
            result = medical_service._generate_injury(is_match=True)
            if result["severity"] == InjurySeverity.MINOR:
                minor_count += 1
            elif result["severity"] == InjurySeverity.MODERATE:
                moderate_count += 1
            elif result["severity"] == InjurySeverity.SEVERE:
                severe_count += 1

        # Allow 5% tolerance
        assert abs(minor_count / total - 0.70) < 0.05
        assert abs(moderate_count / total - 0.25) < 0.05
        assert abs(severe_count / total - 0.05) < 0.03

    def test_minor_injury_recovery_1_to_2_weeks(self, medical_service):
        """Minor injuries should have 1-2 weeks recovery."""
        for _ in range(100):
            with patch("random.random", return_value=0.3):  # Minor
                result = medical_service._generate_injury(is_match=True)
                if result["severity"] == InjurySeverity.MINOR:
                    assert 1 <= result["recovery_weeks"] <= 2

    def test_moderate_injury_recovery_3_to_8_weeks(self, medical_service):
        """Moderate injuries should have 3-8 weeks recovery."""
        for _ in range(100):
            with patch("random.random", return_value=0.80):  # Moderate
                result = medical_service._generate_injury(is_match=True)
                if result["severity"] == InjurySeverity.MODERATE:
                    assert 3 <= result["recovery_weeks"] <= 8

    def test_severe_injury_recovery_9_plus_weeks(self, medical_service):
        """Severe injuries should have 9+ weeks recovery."""
        for _ in range(100):
            with patch("random.random", return_value=0.98):  # Severe
                result = medical_service._generate_injury(is_match=True)
                if result["severity"] == InjurySeverity.SEVERE:
                    assert result["recovery_weeks"] >= 9


# ─── Task 14.3: Injury Recovery Timeline Tests ────────────────────────────


class TestInjuryRecoveryTimeline:
    """Tests for injury recovery timeline system (Task 14.3)."""

    @pytest.mark.asyncio
    async def test_active_injury_transitions_to_recovering(
        self, db_session, medical_service, setup_career
    ):
        """Active injury should transition to RECOVERING when recovery time elapses."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create an injury that should have recovered by now
        past_date = datetime.now() - timedelta(weeks=3)
        expected_recovery = datetime.now() - timedelta(days=1)

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.ACTIVE,
            injury_date=past_date,
            expected_recovery_date=expected_recovery,
            recovery_weeks=2,
            season=1,
            week=8,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=11
        )

        assert len(result["recovered_from_injury"]) == 1
        assert result["recovered_from_injury"][0]["player_id"] == player.id
        assert result["recovered_from_injury"][0]["sharpness_penalty"] == SHARPNESS_PENALTY_PERCENT

    @pytest.mark.asyncio
    async def test_recovering_injury_transitions_to_recovered(
        self, db_session, medical_service, setup_career
    ):
        """RECOVERING injury should transition to RECOVERED after penalty period."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create a recovering injury whose penalty period has ended
        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Ankle Sprain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now() - timedelta(weeks=5),
            expected_recovery_date=datetime.now() - timedelta(weeks=3),
            actual_recovery_date=datetime.now() - timedelta(weeks=3),
            full_recovery_date=datetime.now() - timedelta(days=1),
            recovery_weeks=2,
            season=1,
            week=5,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=11
        )

        assert len(result["fully_recovered"]) == 1
        assert result["fully_recovered"][0]["player_id"] == player.id

    @pytest.mark.asyncio
    async def test_injury_not_yet_recovered_stays_active(
        self, db_session, medical_service, setup_career
    ):
        """Injury that hasn't reached recovery date should stay ACTIVE."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create an injury that hasn't recovered yet
        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Knee Ligament Damage",
            severity=InjurySeverity.SEVERE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(weeks=2),
            expected_recovery_date=datetime.now() + timedelta(weeks=8),
            recovery_weeks=10,
            season=1,
            week=8,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=10
        )

        assert len(result["recovered_from_injury"]) == 0
        assert result["still_injured"] == 1


# ─── Task 14.4: Injury List Screen Tests ──────────────────────────────────


class TestInjuryListScreen:
    """Tests for injury list screen (Task 14.4)."""

    @pytest.mark.asyncio
    async def test_get_injury_list_returns_active_injuries(
        self, db_session, medical_service, setup_career
    ):
        """Should return all ACTIVE injuries."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(weeks=1),
            expected_recovery_date=datetime.now() + timedelta(weeks=4),
            recovery_weeks=5,
            season=1,
            week=9,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.get_injury_list(career.id)

        assert len(result) == 1
        assert result[0]["player_name"] == "John Smith"
        assert result[0]["injury_type"] == "Hamstring Strain"
        assert result[0]["severity"] == "moderate"
        assert result[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_injury_list_includes_recovering(
        self, db_session, medical_service, setup_career
    ):
        """Should include RECOVERING players in the injury list."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Calf Muscle Tear",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now() - timedelta(weeks=3),
            expected_recovery_date=datetime.now() - timedelta(weeks=1),
            actual_recovery_date=datetime.now() - timedelta(weeks=1),
            full_recovery_date=datetime.now() + timedelta(weeks=1),
            recovery_weeks=2,
            season=1,
            week=7,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.get_injury_list(career.id)

        assert len(result) == 1
        assert result[0]["status"] == "recovering"
        assert result[0]["sharpness_penalty"] == 10

    @pytest.mark.asyncio
    async def test_get_injury_list_excludes_recovered(
        self, db_session, medical_service, setup_career
    ):
        """Should NOT include RECOVERED players in the injury list."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Ankle Sprain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERED,
            injury_date=datetime.now() - timedelta(weeks=6),
            expected_recovery_date=datetime.now() - timedelta(weeks=4),
            actual_recovery_date=datetime.now() - timedelta(weeks=4),
            full_recovery_date=datetime.now() - timedelta(weeks=2),
            recovery_weeks=2,
            season=1,
            week=4,
            sharpness_penalty=0,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.get_injury_list(career.id)

        assert len(result) == 0


# ─── Task 14.5: Matchday Squad Prevention Tests ──────────────────────────


class TestMatchdaySquadPrevention:
    """Tests for matchday squad prevention (Task 14.5)."""

    @pytest.mark.asyncio
    async def test_injured_player_unavailable(
        self, db_session, medical_service, setup_career
    ):
        """Player with ACTIVE injury should be unavailable for match."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Groin Strain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(weeks=1),
            expected_recovery_date=datetime.now() + timedelta(weeks=3),
            recovery_weeks=4,
            season=1,
            week=9,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        available, reason = await medical_service.is_player_available_for_match(
            squad_player.id, career.id
        )

        assert available is False
        assert "Injured" in reason
        assert "Groin Strain" in reason

    @pytest.mark.asyncio
    async def test_healthy_player_available(
        self, db_session, medical_service, setup_career
    ):
        """Player with no injuries should be available."""
        data = setup_career
        career = data["career"]
        squad_player = data["squad_player"]

        available, reason = await medical_service.is_player_available_for_match(
            squad_player.id, career.id
        )

        assert available is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_recovering_player_available(
        self, db_session, medical_service, setup_career
    ):
        """Player in RECOVERING status should be available (with penalty)."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Muscle Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now() - timedelta(weeks=4),
            expected_recovery_date=datetime.now() - timedelta(weeks=2),
            actual_recovery_date=datetime.now() - timedelta(weeks=2),
            full_recovery_date=datetime.now() + timedelta(days=5),
            recovery_weeks=2,
            season=1,
            week=6,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        available, reason = await medical_service.is_player_available_for_match(
            squad_player.id, career.id
        )

        assert available is True
        assert reason is None


# ─── Task 14.6: Training Ground Injury Simulation Tests ──────────────────


class TestTrainingGroundInjury:
    """Tests for training ground injury simulation (Task 14.6)."""

    def test_training_injury_low_base_probability(self, medical_service):
        """Training injuries should have low base probability (~1%)."""
        injuries = 0
        trials = 10000
        for _ in range(trials):
            result = medical_service.simulate_training_injury(
                player_age=25,
                training_intensity_multiplier=1.0,
            )
            if result is not None:
                injuries += 1

        # ~1% base rate, expect roughly 100 in 10000
        injury_rate = injuries / trials
        assert 0.005 < injury_rate < 0.03

    def test_training_injury_uses_training_types(self, medical_service):
        """Training injuries should use training-specific injury types."""
        with patch("random.random", side_effect=[0.001, 0.5]):
            result = medical_service.simulate_training_injury(
                player_age=25,
                training_intensity_multiplier=1.0,
            )

        if result is not None:
            assert result["injury_type"] in TRAINING_INJURY_TYPES
            assert result["is_match_injury"] is False

    def test_heavy_training_increases_injury_risk(self, medical_service):
        """Heavy training intensity should increase injury probability."""
        normal_injuries = 0
        heavy_injuries = 0
        trials = 10000

        for _ in range(trials):
            normal = medical_service.simulate_training_injury(
                player_age=25, training_intensity_multiplier=1.0,
            )
            heavy = medical_service.simulate_training_injury(
                player_age=25, training_intensity_multiplier=2.0,
            )
            if normal:
                normal_injuries += 1
            if heavy:
                heavy_injuries += 1

        assert heavy_injuries > normal_injuries


# ─── Task 14.7: Match Sharpness Penalty Tests ────────────────────────────


class TestMatchSharpnessPenalty:
    """Tests for match sharpness penalty after injury return (Task 14.7)."""

    @pytest.mark.asyncio
    async def test_recovering_player_has_penalty(
        self, db_session, medical_service, setup_career
    ):
        """Player in RECOVERING status should have sharpness penalty."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now() - timedelta(weeks=4),
            expected_recovery_date=datetime.now() - timedelta(weeks=2),
            actual_recovery_date=datetime.now() - timedelta(weeks=2),
            full_recovery_date=datetime.now() + timedelta(days=5),
            recovery_weeks=2,
            season=1,
            week=6,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        penalty = await medical_service.get_player_sharpness_penalty(
            squad_player.id, career.id
        )

        assert penalty == 10

    @pytest.mark.asyncio
    async def test_healthy_player_no_penalty(
        self, db_session, medical_service, setup_career
    ):
        """Healthy player should have no sharpness penalty."""
        data = setup_career
        career = data["career"]
        squad_player = data["squad_player"]

        penalty = await medical_service.get_player_sharpness_penalty(
            squad_player.id, career.id
        )

        assert penalty == 0

    def test_effective_ca_calculation_with_penalty(self, medical_service):
        """Effective CA should be reduced by penalty percentage."""
        # 10% penalty on CA 140 = 14 reduction = 126
        effective = medical_service.calculate_effective_ca(140, 10)
        assert effective == 126

    def test_effective_ca_no_penalty(self, medical_service):
        """No penalty should return original CA."""
        effective = medical_service.calculate_effective_ca(140, 0)
        assert effective == 140

    def test_effective_ca_minimum_is_1(self, medical_service):
        """Effective CA should never go below 1."""
        effective = medical_service.calculate_effective_ca(5, 100)
        assert effective >= 1


# ─── Task 14.8: Injury History Tracking Tests ─────────────────────────────


class TestInjuryHistoryTracking:
    """Tests for injury history tracking (Task 14.8)."""

    @pytest.mark.asyncio
    async def test_get_player_injury_history(
        self, db_session, medical_service, setup_career
    ):
        """Should return all injuries for a player ordered by date desc."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create multiple injuries at different times
        injury1 = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERED,
            injury_date=datetime.now() - timedelta(weeks=10),
            expected_recovery_date=datetime.now() - timedelta(weeks=8),
            actual_recovery_date=datetime.now() - timedelta(weeks=8),
            full_recovery_date=datetime.now() - timedelta(weeks=6),
            recovery_weeks=2,
            season=1,
            week=1,
            sharpness_penalty=0,
        )
        injury2 = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Ankle Sprain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(weeks=1),
            expected_recovery_date=datetime.now() + timedelta(weeks=4),
            recovery_weeks=5,
            season=1,
            week=9,
            sharpness_penalty=10,
        )
        db_session.add_all([injury1, injury2])
        await db_session.commit()

        history = await medical_service.get_player_injury_history(
            player.id, career.id
        )

        assert len(history) == 2
        # Most recent first
        assert history[0]["injury_type"] == "Ankle Sprain"
        assert history[1]["injury_type"] == "Hamstring Strain"
        assert history[0]["severity"] == "moderate"
        assert history[1]["severity"] == "minor"

    @pytest.mark.asyncio
    async def test_empty_injury_history(
        self, db_session, medical_service, setup_career
    ):
        """Player with no injuries should return empty list."""
        data = setup_career
        career = data["career"]
        player = data["player"]

        history = await medical_service.get_player_injury_history(
            player.id, career.id
        )

        assert history == []

    @pytest.mark.asyncio
    async def test_injury_history_includes_match_context(
        self, db_session, medical_service, setup_career
    ):
        """Injury history should include match context when available."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Knee Ligament Damage",
            severity=InjurySeverity.SEVERE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(days=3),
            expected_recovery_date=datetime.now() + timedelta(weeks=12),
            recovery_weeks=12,
            season=1,
            week=10,
            occurred_in_match_id=42,
            match_minute=67,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        history = await medical_service.get_player_injury_history(
            player.id, career.id
        )

        assert len(history) == 1
        assert history[0]["is_match_injury"] is True
        assert history[0]["match_minute"] == 67


# ─── Task 14.9: Injury-Prone Flag Tests ──────────────────────────────────


class TestInjuryProneFlag:
    """Tests for injury-prone flag system (Task 14.9)."""

    @pytest.mark.asyncio
    async def test_player_with_3_injuries_flagged(
        self, db_session, medical_service, setup_career
    ):
        """Player with 3+ injuries in a season should be flagged."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create 3 injuries in the same season
        for i in range(3):
            injury = Injury(
                career_id=career.id,
                player_id=player.id,
                squad_player_id=squad_player.id,
                injury_type=f"Injury {i+1}",
                severity=InjurySeverity.MINOR,
                status=InjuryStatus.RECOVERED,
                injury_date=datetime.now() - timedelta(weeks=10 - i * 3),
                expected_recovery_date=datetime.now() - timedelta(weeks=8 - i * 3),
                actual_recovery_date=datetime.now() - timedelta(weeks=8 - i * 3),
                full_recovery_date=datetime.now() - timedelta(weeks=6 - i * 3),
                recovery_weeks=2,
                season=1,
                week=i * 3 + 1,
                sharpness_penalty=0,
            )
            db_session.add(injury)

        await db_session.commit()

        flagged = await medical_service.check_injury_prone_players(career.id, 1)

        assert len(flagged) == 1
        assert flagged[0]["player_id"] == player.id
        assert flagged[0]["injury_count"] == 3
        assert flagged[0]["risk_increase"] == INJURY_PRONE_RISK_INCREASE

    @pytest.mark.asyncio
    async def test_player_with_2_injuries_not_flagged(
        self, db_session, medical_service, setup_career
    ):
        """Player with fewer than 3 injuries should NOT be flagged."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create only 2 injuries
        for i in range(2):
            injury = Injury(
                career_id=career.id,
                player_id=player.id,
                squad_player_id=squad_player.id,
                injury_type=f"Injury {i+1}",
                severity=InjurySeverity.MINOR,
                status=InjuryStatus.RECOVERED,
                injury_date=datetime.now() - timedelta(weeks=10 - i * 3),
                expected_recovery_date=datetime.now() - timedelta(weeks=8 - i * 3),
                actual_recovery_date=datetime.now() - timedelta(weeks=8 - i * 3),
                full_recovery_date=datetime.now() - timedelta(weeks=6 - i * 3),
                recovery_weeks=2,
                season=1,
                week=i * 3 + 1,
                sharpness_penalty=0,
            )
            db_session.add(injury)

        await db_session.commit()

        flagged = await medical_service.check_injury_prone_players(career.id, 1)

        assert len(flagged) == 0

    @pytest.mark.asyncio
    async def test_is_player_injury_prone(
        self, db_session, medical_service, setup_career
    ):
        """is_player_injury_prone should return True for 3+ injuries."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create 3 injuries
        for i in range(3):
            injury = Injury(
                career_id=career.id,
                player_id=player.id,
                squad_player_id=squad_player.id,
                injury_type=f"Injury {i+1}",
                severity=InjurySeverity.MINOR,
                status=InjuryStatus.RECOVERED,
                injury_date=datetime.now() - timedelta(weeks=10 - i * 3),
                expected_recovery_date=datetime.now() - timedelta(weeks=8 - i * 3),
                recovery_weeks=2,
                season=1,
                week=i * 3 + 1,
                sharpness_penalty=0,
            )
            db_session.add(injury)

        await db_session.commit()

        is_prone = await medical_service.is_player_injury_prone(
            player.id, career.id, 1
        )

        assert is_prone is True


# ─── Task 14.10: Fatigue Accumulation System Tests ────────────────────────


class TestFatigueAccumulation:
    """Tests for fatigue accumulation system (Task 14.10)."""

    def test_fatigue_from_full_match(self, medical_service):
        """90 minutes should add FATIGUE_PER_90_MINUTES fatigue."""
        result = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90]
        )
        assert result == FATIGUE_PER_90_MINUTES

    def test_fatigue_from_no_matches(self, medical_service):
        """No matches should result in zero fatigue."""
        result = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[]
        )
        assert result == MIN_FATIGUE

    def test_fatigue_accumulates_over_matches(self, medical_service):
        """Multiple matches should accumulate fatigue."""
        single_match = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90]
        )
        multiple_matches = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90, 90, 90]
        )
        assert multiple_matches > single_match

    def test_fatigue_capped_at_max(self, medical_service):
        """Fatigue should never exceed MAX_FATIGUE."""
        result = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[120, 120, 120, 120, 120]
        )
        assert result <= MAX_FATIGUE

    def test_fatigue_recovery_with_rest(self, medical_service):
        """Rest weeks should reduce fatigue."""
        no_rest = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90, 90, 90],
            weeks_since_last_match=0,
        )
        with_rest = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90, 90, 90],
            weeks_since_last_match=2,
        )
        assert with_rest < no_rest

    def test_fatigue_never_negative(self, medical_service):
        """Fatigue should never go below MIN_FATIGUE."""
        result = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[30],
            weeks_since_last_match=10,
        )
        assert result >= MIN_FATIGUE

    def test_partial_match_less_fatigue(self, medical_service):
        """Playing fewer minutes should result in less fatigue."""
        full_match = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90]
        )
        partial_match = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[45]
        )
        assert partial_match < full_match

    def test_fatigue_injury_risk_modifier_below_threshold(self, medical_service):
        """Below threshold, risk modifier should be 1.0."""
        modifier = medical_service.get_fatigue_injury_risk_modifier(50.0)
        assert modifier == 1.0

    def test_fatigue_injury_risk_modifier_at_threshold(self, medical_service):
        """At threshold, risk modifier should be 1.0."""
        modifier = medical_service.get_fatigue_injury_risk_modifier(
            HIGH_FATIGUE_THRESHOLD
        )
        assert modifier == 1.0

    def test_fatigue_injury_risk_modifier_above_threshold(self, medical_service):
        """Above threshold, risk modifier should be > 1.0."""
        modifier = medical_service.get_fatigue_injury_risk_modifier(85.0)
        assert modifier > 1.0

    def test_fatigue_injury_risk_modifier_at_max(self, medical_service):
        """At max fatigue, risk modifier should be 1.5."""
        modifier = medical_service.get_fatigue_injury_risk_modifier(MAX_FATIGUE)
        assert modifier == 1.5

    @pytest.mark.asyncio
    async def test_get_squad_fatigue(
        self, db_session, medical_service, setup_career
    ):
        """Should return fatigue data for all squad players."""
        data = setup_career
        career = data["career"]

        result = await medical_service.get_squad_fatigue(career.id)

        assert len(result) == 1
        assert result[0]["player_name"] == "John Smith"
        assert "estimated_fatigue" in result[0]
        assert "injury_risk_modifier" in result[0]
        assert "needs_rest" in result[0]

    @pytest.mark.asyncio
    async def test_update_player_fatigue(self, medical_service):
        """Should calculate fatigue gained from minutes played."""
        result = await medical_service.update_player_fatigue(
            squad_player_id=1, minutes_played=90
        )

        assert result["fatigue_gained"] == FATIGUE_PER_90_MINUTES
        assert result["minutes_played"] == 90

    def test_recent_matches_weighted_more(self, medical_service):
        """More recent matches should contribute more to fatigue."""
        # Same total minutes but distributed differently
        # [90, 0, 0, 0, 0] = recent heavy load
        recent_heavy = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[90, 0, 0, 0, 0]
        )
        # [0, 0, 0, 0, 90] = old heavy load (decayed more)
        old_heavy = medical_service.calculate_fatigue_from_matches(
            recent_minutes=[0, 0, 0, 0, 90]
        )
        assert recent_heavy > old_heavy


# ─── Integration Tests ────────────────────────────────────────────────────


class TestMedicalServiceIntegration:
    """Integration tests combining multiple medical features."""

    @pytest.mark.asyncio
    async def test_create_injury_and_check_availability(
        self, db_session, medical_service, setup_career
    ):
        """Creating an injury should make player unavailable."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create injury
        await medical_service.create_injury_record(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MODERATE,
            recovery_weeks=4,
            season=1,
            week=10,
        )

        # Check availability
        available, reason = await medical_service.is_player_available_for_match(
            squad_player.id, career.id
        )

        assert available is False
        assert "Hamstring Strain" in reason

    @pytest.mark.asyncio
    async def test_career_injury_summary(
        self, db_session, medical_service, setup_career
    ):
        """Should return correct injury summary statistics."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Create injuries with different statuses
        active_injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Active Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now() - timedelta(weeks=1),
            expected_recovery_date=datetime.now() + timedelta(weeks=3),
            recovery_weeks=4,
            season=1,
            week=9,
            sharpness_penalty=10,
        )
        recovering_injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Recovering Injury",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now() - timedelta(weeks=4),
            expected_recovery_date=datetime.now() - timedelta(weeks=2),
            actual_recovery_date=datetime.now() - timedelta(weeks=2),
            full_recovery_date=datetime.now() + timedelta(days=5),
            recovery_weeks=2,
            season=1,
            week=6,
            sharpness_penalty=10,
        )
        db_session.add_all([active_injury, recovering_injury])
        await db_session.commit()

        summary = await medical_service.get_career_injury_summary(career.id)

        assert summary["active_injuries"] == 1
        assert summary["recovering_players"] == 1
        assert summary["total_injuries_recorded"] == 2


# ─── Task 14.3: In-Game Week-Based Recovery Progression Tests ─────────────


class TestInGameWeekBasedRecovery:
    """
    Tests for in-game week-based injury recovery progression (Task 14.3).

    Validates that recovery is driven by the in-game (season, week) calendar
    rather than wall-clock time, so it composes correctly with advance_week.
    """

    @pytest.mark.asyncio
    async def test_active_to_recovering_when_recovery_weeks_elapsed(
        self, db_session, medical_service, setup_career
    ):
        """ACTIVE injury transitions to RECOVERING after recovery_weeks
        in-game weeks have elapsed (independent of wall-clock dates)."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # Future expected_recovery_date so wall-clock would say "still injured".
        # The in-game calendar progression is what should drive the transition.
        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        # Advance the in-game calendar by exactly recovery_weeks
        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=12
        )

        assert len(result["recovered_from_injury"]) == 1
        assert result["recovered_from_injury"][0]["weeks_out"] == 2

        await db_session.refresh(injury)
        assert injury.status == InjuryStatus.RECOVERING
        assert injury.sharpness_penalty == SHARPNESS_PENALTY_PERCENT

    @pytest.mark.asyncio
    async def test_active_stays_active_when_not_enough_weeks_elapsed(
        self, db_session, medical_service, setup_career
    ):
        """ACTIVE injury stays ACTIVE when fewer in-game weeks have elapsed
        than recovery_weeks (and the wall-clock recovery date is not yet)."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Knee Ligament Damage",
            severity=InjurySeverity.SEVERE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=10,
            season=1,
            week=5,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        # Only 3 in-game weeks elapsed; not enough for a 10-week injury
        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=8
        )

        assert len(result["recovered_from_injury"]) == 0
        assert result["still_injured"] == 1

        await db_session.refresh(injury)
        assert injury.status == InjuryStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_recovering_to_recovered_after_sharpness_weeks(
        self, db_session, medical_service, setup_career
    ):
        """RECOVERING transitions to RECOVERED after SHARPNESS_PENALTY_WEEKS
        more in-game weeks (recovery_weeks + 2 weeks total since injury)."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Calf Muscle Tear",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            actual_recovery_date=datetime.now(),
            full_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        # Injury at week 10 with recovery_weeks=2 -> RECOVERING at week 12.
        # After SHARPNESS_PENALTY_WEEKS more (=2), week 14, should be RECOVERED.
        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=14
        )

        assert len(result["fully_recovered"]) == 1
        await db_session.refresh(injury)
        assert injury.status == InjuryStatus.RECOVERED
        assert injury.sharpness_penalty == 0

    @pytest.mark.asyncio
    async def test_recovering_stays_recovering_within_penalty_window(
        self, db_session, medical_service, setup_career
    ):
        """RECOVERING stays RECOVERING during the 2-week sharpness window."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            actual_recovery_date=datetime.now(),
            full_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        # Week 13 = 1 week into the 2-week recovery window. Still RECOVERING.
        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=13
        )

        assert len(result["fully_recovered"]) == 0
        await db_session.refresh(injury)
        assert injury.status == InjuryStatus.RECOVERING

    @pytest.mark.asyncio
    async def test_progression_across_season_boundary(
        self, db_session, medical_service, setup_career
    ):
        """Recovery progression must work across season rollover (week 52 -> 1)."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        # 4-week injury starting in week 50 of season 1.
        # Should transition to RECOVERING in week 2 of season 2.
        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Ankle Sprain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=4,
            season=1,
            week=50,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        result = await medical_service.process_weekly_recovery(
            career_id=career.id, season=2, week=2
        )

        assert len(result["recovered_from_injury"]) == 1
        await db_session.refresh(injury)
        assert injury.status == InjuryStatus.RECOVERING

    @pytest.mark.asyncio
    async def test_recovery_is_idempotent_within_same_week(
        self, db_session, medical_service, setup_career
    ):
        """Calling process_weekly_recovery twice in the same in-game week
        should not cause double transitions."""
        data = setup_career
        career = data["career"]
        player = data["player"]
        squad_player = data["squad_player"]

        injury = Injury(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            injury_type="Groin Strain",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now() + timedelta(days=365),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
        )
        db_session.add(injury)
        await db_session.commit()

        first = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=12
        )
        second = await medical_service.process_weekly_recovery(
            career_id=career.id, season=1, week=12
        )

        # First call transitions to RECOVERING; second is a no-op for that
        # transition (the injury is no longer ACTIVE).
        assert len(first["recovered_from_injury"]) == 1
        assert len(second["recovered_from_injury"]) == 0

    def test_get_weeks_remaining_active(self, medical_service):
        """get_weeks_remaining returns recovery_weeks - elapsed for ACTIVE."""
        from app.models.injury import Injury, InjurySeverity, InjuryStatus

        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now(),
            recovery_weeks=5,
            season=1,
            week=10,
            sharpness_penalty=10,
        )

        # 0 weeks elapsed -> 5 remaining
        assert medical_service.get_weeks_remaining(injury, 1, 10) == 5
        # 2 weeks elapsed -> 3 remaining
        assert medical_service.get_weeks_remaining(injury, 1, 12) == 3
        # 5 weeks elapsed -> 0 remaining
        assert medical_service.get_weeks_remaining(injury, 1, 15) == 0
        # Overshoot -> still 0 (not negative)
        assert medical_service.get_weeks_remaining(injury, 1, 20) == 0

    def test_get_weeks_remaining_recovering(self, medical_service):
        """get_weeks_remaining accounts for sharpness window when RECOVERING."""
        from app.models.injury import Injury, InjurySeverity, InjuryStatus

        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now(),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
        )

        # Total target = recovery_weeks + SHARPNESS_PENALTY_WEEKS = 4
        # At week 12 (2 elapsed) -> 2 remaining
        assert medical_service.get_weeks_remaining(injury, 1, 12) == 2
        # At week 14 (4 elapsed) -> 0 remaining
        assert medical_service.get_weeks_remaining(injury, 1, 14) == 0

    def test_get_weeks_remaining_recovered(self, medical_service):
        """get_weeks_remaining is 0 for RECOVERED injuries regardless of week."""
        from app.models.injury import Injury, InjurySeverity, InjuryStatus

        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERED,
            injury_date=datetime.now(),
            expected_recovery_date=datetime.now(),
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=0,
        )

        assert medical_service.get_weeks_remaining(injury, 1, 5) == 0
        assert medical_service.get_weeks_remaining(injury, 99, 50) == 0


class TestInGameWeeksHelper:
    """Tests for the in_game_weeks_between helper."""

    def test_same_week(self):
        from app.services.medical_service import in_game_weeks_between
        assert in_game_weeks_between(1, 10, 1, 10) == 0

    def test_within_same_season(self):
        from app.services.medical_service import in_game_weeks_between
        assert in_game_weeks_between(1, 5, 1, 12) == 7

    def test_across_seasons(self):
        from app.services.medical_service import in_game_weeks_between, WEEKS_PER_SEASON
        # From S1W50 to S2W2 = 4 weeks (52-50 + 2)
        assert in_game_weeks_between(1, 50, 2, 2) == 4
        # From S1W1 to S3W1 = 2 full seasons
        assert in_game_weeks_between(1, 1, 3, 1) == 2 * WEEKS_PER_SEASON

    def test_negative_when_end_precedes_start(self):
        from app.services.medical_service import in_game_weeks_between
        assert in_game_weeks_between(2, 5, 1, 10) < 0
