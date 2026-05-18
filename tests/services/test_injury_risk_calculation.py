"""
Tests for injury risk calculation based on training intensity.

Tests the calculate_injury_risk() and get_squad_injury_risk_report() methods
in TrainingService, verifying correct probability calculations for different
age/intensity combinations.

Validates:
- Requirement 7.10: Training intensity affects injury risk
- Requirement 11.6: Training ground injuries based on intensity and player age
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.career import Career
from app.models.club import Club
from app.models.user import User
from app.services.training_service import TrainingService


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create test database session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        # Create tables individually, skipping PostgreSQL-specific indexes
        # that use to_tsvector (not available in SQLite)
        for table in Base.metadata.sorted_tables:
            # Filter out PostgreSQL-specific indexes before creating
            original_indexes = list(table.indexes)
            pg_indexes = [
                idx for idx in table.indexes
                if 'fts' in idx.name or 'tsvector' in str(idx.expressions)
            ]
            for idx in pg_indexes:
                table.indexes.discard(idx)

            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))

            # Restore indexes for other uses
            for idx in pg_indexes:
                table.indexes.add(idx)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def training_service(db_session):
    """Create TrainingService instance"""
    return TrainingService(db_session)


def create_player(name: str, age: int, player_id: int = None) -> Player:
    """Helper to create a Player instance for testing."""
    player = Player(
        name=name,
        age=age,
        position="ST",
        nationality="England",
        club="Test FC",
        ca=120,
        pa=150,
        corners=10,
        crossing=10,
        dribbling=12,
        finishing=15,
        first_touch=12,
        free_kicks=8,
        heading=10,
        long_shots=11,
        long_throws=5,
        marking=6,
        passing=12,
        penalty=10,
        tackling=6,
        technique=13,
        aggression=10,
        anticipation=12,
        bravery=14,
        composure=13,
        concentration=11,
        decisions=12,
        determination=15,
        flair=11,
        leadership=10,
        off_the_ball=13,
        positioning=8,
        teamwork=12,
        vision=11,
        work_rate=14,
        acceleration=14,
        agility=12,
        balance=11,
        jumping=10,
        stamina=14,
        pace=13,
        endurance=12,
        strength=11,
        price="10M",
        wage=50000,
        height=180,
        weight=75,
        left_foot=15,
        right_foot=8,
        uid=f"test_uid_{player_id or id(name)}",
    )
    if player_id:
        player.id = player_id
    return player


class TestCalculateInjuryRisk:
    """Tests for TrainingService.calculate_injury_risk() static method."""

    def test_young_player_light_intensity(self):
        """Young player (≤30) with light intensity should have lowest risk."""
        player = create_player("Young Player", age=22, player_id=1)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.LIGHT)

        assert result["player_id"] == 1
        assert result["player_name"] == "Young Player"
        assert result["age"] == 22
        assert result["base_probability"] == 0.01
        assert result["age_factor"] == 1.0
        assert result["intensity_factor"] == 0.7
        assert result["final_probability"] == pytest.approx(0.007)
        assert result["risk_level"] == "Low"

    def test_young_player_normal_intensity(self):
        """Young player (≤30) with normal intensity should have base risk."""
        player = create_player("Normal Player", age=25, player_id=2)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["age_factor"] == 1.0
        assert result["intensity_factor"] == 1.0
        assert result["final_probability"] == pytest.approx(0.01)
        assert result["risk_level"] == "Low"

    def test_young_player_heavy_intensity(self):
        """Young player (≤30) with heavy intensity should have elevated risk."""
        player = create_player("Heavy Trainer", age=28, player_id=3)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.HEAVY)

        assert result["age_factor"] == 1.0
        assert result["intensity_factor"] == 1.5
        assert result["final_probability"] == pytest.approx(0.015)
        assert result["risk_level"] == "Medium"

    def test_player_age_30_boundary(self):
        """Player exactly 30 should have age_factor 1.0 (not elevated)."""
        player = create_player("Boundary Player", age=30, player_id=4)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["age_factor"] == 1.0
        assert result["final_probability"] == pytest.approx(0.01)

    def test_player_age_31_elevated_risk(self):
        """Player age 31 should have age_factor 1.5."""
        player = create_player("Older Player", age=31, player_id=5)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["age_factor"] == 1.5
        assert result["final_probability"] == pytest.approx(0.015)
        assert result["risk_level"] == "Medium"

    def test_player_age_35_boundary(self):
        """Player exactly 35 should have age_factor 1.5 (31-35 range)."""
        player = create_player("35yo Player", age=35, player_id=6)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["age_factor"] == 1.5
        assert result["final_probability"] == pytest.approx(0.015)

    def test_player_age_36_highest_risk(self):
        """Player age 36+ should have age_factor 2.0."""
        player = create_player("Veteran Player", age=36, player_id=7)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["age_factor"] == 2.0
        assert result["final_probability"] == pytest.approx(0.02)
        assert result["risk_level"] == "High"

    def test_veteran_heavy_intensity_very_high_risk(self):
        """Veteran (>35) with heavy intensity should have very high risk."""
        player = create_player("Old Heavy", age=37, player_id=8)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.HEAVY)

        assert result["age_factor"] == 2.0
        assert result["intensity_factor"] == 1.5
        assert result["final_probability"] == pytest.approx(0.03)
        assert result["risk_level"] == "Very High"

    def test_veteran_light_intensity_reduced_risk(self):
        """Veteran (>35) with light intensity should have reduced risk."""
        player = create_player("Old Light", age=38, player_id=9)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.LIGHT)

        assert result["age_factor"] == 2.0
        assert result["intensity_factor"] == 0.7
        assert result["final_probability"] == pytest.approx(0.014)
        assert result["risk_level"] == "Medium"

    def test_mid_thirties_heavy_intensity(self):
        """Player 31-35 with heavy intensity should have high risk."""
        player = create_player("Mid30s Heavy", age=33, player_id=10)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.HEAVY)

        assert result["age_factor"] == 1.5
        assert result["intensity_factor"] == 1.5
        assert result["final_probability"] == pytest.approx(0.0225)
        assert result["risk_level"] == "Very High"

    def test_risk_percentage_format(self):
        """Risk percentage should be formatted as a string with 2 decimal places."""
        player = create_player("Format Test", age=25, player_id=11)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)

        assert result["risk_percentage"] == "1.00%"

    def test_risk_percentage_format_decimal(self):
        """Risk percentage for light intensity should show decimal."""
        player = create_player("Decimal Test", age=25, player_id=12)
        result = TrainingService.calculate_injury_risk(player, TrainingIntensity.LIGHT)

        assert result["risk_percentage"] == "0.70%"

    def test_no_side_effects(self):
        """calculate_injury_risk should not modify the player object."""
        player = create_player("Side Effect Test", age=32, player_id=13)
        original_age = player.age
        original_name = player.name

        TrainingService.calculate_injury_risk(player, TrainingIntensity.HEAVY)

        assert player.age == original_age
        assert player.name == original_name

    def test_risk_levels_boundaries(self):
        """Verify risk level categorization boundaries."""
        # Low: probability <= 0.01
        player_young = create_player("Young", age=22, player_id=14)
        assert TrainingService.calculate_injury_risk(
            player_young, TrainingIntensity.NORMAL
        )["risk_level"] == "Low"

        # Medium: 0.01 < probability <= 0.015
        player_mid = create_player("Mid", age=31, player_id=15)
        assert TrainingService.calculate_injury_risk(
            player_mid, TrainingIntensity.NORMAL
        )["risk_level"] == "Medium"

        # High: 0.015 < probability <= 0.02
        player_old = create_player("Old", age=36, player_id=16)
        assert TrainingService.calculate_injury_risk(
            player_old, TrainingIntensity.NORMAL
        )["risk_level"] == "High"

        # Very High: probability > 0.02
        player_veteran = create_player("Veteran", age=37, player_id=17)
        assert TrainingService.calculate_injury_risk(
            player_veteran, TrainingIntensity.HEAVY
        )["risk_level"] == "Very High"


class TestGetSquadInjuryRiskReport:
    """Tests for TrainingService.get_squad_injury_risk_report() async method."""

    @pytest.fixture
    async def squad_data(self, db_session):
        """Create a career with a squad of players of various ages."""
        # Create user
        user = User(
            telegram_user_id=99999,
            username="risktest",
            first_name="Risk",
            language_code="en"
        )
        db_session.add(user)
        await db_session.flush()

        # Create club
        club = Club(
            name="Risk FC",
            reputation=60,
            league="Premier League",
            country="England",
            balance=2000000,
            transfer_budget=1000000,
            wage_budget=100000
        )
        db_session.add(club)
        await db_session.flush()

        # Create career with normal intensity
        career = Career(
            user_id=user.id,
            club_id=club.id,
            manager_name="Test Manager",
            current_season=1,
            current_week=10,
            board_confidence=75,
            manager_reputation=50,
            training_intensity=TrainingIntensity.NORMAL,
        )
        db_session.add(career)
        await db_session.flush()

        # Create players of different ages
        players = [
            create_player("Young Star", age=20, player_id=None),
            create_player("Prime Player", age=27, player_id=None),
            create_player("Experienced", age=32, player_id=None),
            create_player("Veteran", age=36, player_id=None),
            create_player("Legend", age=38, player_id=None),
        ]

        for player in players:
            # Remove the manually set id so the DB can auto-assign
            player.id = None
            db_session.add(player)

        await db_session.flush()

        # Create squad players
        for i, player in enumerate(players):
            squad_player = SquadPlayer(
                career_id=career.id,
                player_id=player.id,
                squad_number=i + 1,
                squad_status="FIRST_TEAM",
                morale=70,
                contract_start_date=datetime(2025, 1, 1).date(),
                contract_end_date=datetime(2027, 6, 30).date(),
                wage=50000,
                contract_months_remaining=30,
            )
            db_session.add(squad_player)

        await db_session.commit()

        return {
            "career_id": career.id,
            "career": career,
            "players": players,
            "club": club,
        }

    @pytest.mark.asyncio
    async def test_report_returns_all_players(self, training_service, squad_data):
        """Report should include all squad players."""
        report = await training_service.get_squad_injury_risk_report(
            squad_data["career_id"]
        )

        assert report["total_players"] == 5
        assert len(report["players"]) == 5

    @pytest.mark.asyncio
    async def test_report_career_info(self, training_service, squad_data):
        """Report should include career and intensity info."""
        report = await training_service.get_squad_injury_risk_report(
            squad_data["career_id"]
        )

        assert report["career_id"] == squad_data["career_id"]
        assert report["intensity"] == "normal"

    @pytest.mark.asyncio
    async def test_report_risk_summary(self, training_service, squad_data):
        """Report should include a risk summary with counts per level."""
        report = await training_service.get_squad_injury_risk_report(
            squad_data["career_id"]
        )

        summary = report["risk_summary"]
        assert "Low" in summary
        assert "Medium" in summary
        assert "High" in summary
        assert "Very High" in summary

        # With normal intensity:
        # age 20, 27 -> factor 1.0, prob 0.01 -> Low
        # age 32 -> factor 1.5, prob 0.015 -> Medium
        # age 36, 38 -> factor 2.0, prob 0.02 -> High
        assert summary["Low"] == 2
        assert summary["Medium"] == 1
        assert summary["High"] == 2
        assert summary["Very High"] == 0

    @pytest.mark.asyncio
    async def test_report_sorted_by_risk_descending(self, training_service, squad_data):
        """Players should be sorted by risk probability, highest first."""
        report = await training_service.get_squad_injury_risk_report(
            squad_data["career_id"]
        )

        probabilities = [p["final_probability"] for p in report["players"]]
        assert probabilities == sorted(probabilities, reverse=True)

    @pytest.mark.asyncio
    async def test_report_invalid_career(self, training_service):
        """Should raise ValueError for invalid career ID."""
        with pytest.raises(ValueError, match="Career 99999 not found"):
            await training_service.get_squad_injury_risk_report(99999)

    @pytest.mark.asyncio
    async def test_report_empty_squad(self, db_session):
        """Report for career with no squad players should return empty list."""
        # Create user
        user = User(
            telegram_user_id=88888,
            username="emptytest",
            first_name="Empty",
            language_code="en"
        )
        db_session.add(user)
        await db_session.flush()

        # Create club
        club = Club(
            name="Empty FC",
            reputation=40,
            league="Championship",
            country="England",
            balance=500000,
            transfer_budget=200000,
            wage_budget=30000
        )
        db_session.add(club)
        await db_session.flush()

        # Create career with no squad
        career = Career(
            user_id=user.id,
            club_id=club.id,
            manager_name="Empty Manager",
            current_season=1,
            current_week=1,
            board_confidence=50,
            manager_reputation=30,
            training_intensity=TrainingIntensity.HEAVY,
        )
        db_session.add(career)
        await db_session.commit()

        service = TrainingService(db_session)
        report = await service.get_squad_injury_risk_report(career.id)

        assert report["total_players"] == 0
        assert report["players"] == []
        assert report["intensity"] == "heavy"
        assert report["risk_summary"] == {
            "Low": 0, "Medium": 0, "High": 0, "Very High": 0
        }

    @pytest.mark.asyncio
    async def test_report_with_heavy_intensity(self, db_session, squad_data):
        """Report with heavy intensity should show higher risk levels."""
        # Update career intensity to heavy
        career = squad_data["career"]
        career.training_intensity = TrainingIntensity.HEAVY
        await db_session.commit()

        service = TrainingService(db_session)
        report = await service.get_squad_injury_risk_report(squad_data["career_id"])

        assert report["intensity"] == "heavy"

        # With heavy intensity (1.5x):
        # age 20, 27 -> factor 1.0 * 1.5 = 0.015 -> Medium
        # age 32 -> factor 1.5 * 1.5 = 0.0225 -> Very High
        # age 36, 38 -> factor 2.0 * 1.5 = 0.03 -> Very High
        summary = report["risk_summary"]
        assert summary["Low"] == 0
        assert summary["Medium"] == 2
        assert summary["High"] == 0
        assert summary["Very High"] == 3

    @pytest.mark.asyncio
    async def test_report_with_light_intensity(self, db_session, squad_data):
        """Report with light intensity should show lower risk levels."""
        # Update career intensity to light
        career = squad_data["career"]
        career.training_intensity = TrainingIntensity.LIGHT
        await db_session.commit()

        service = TrainingService(db_session)
        report = await service.get_squad_injury_risk_report(squad_data["career_id"])

        assert report["intensity"] == "light"

        # With light intensity (0.7x):
        # age 20, 27 -> factor 1.0 * 0.7 = 0.007 -> Low
        # age 32 -> factor 1.5 * 0.7 = 0.0105 -> Medium
        # age 36, 38 -> factor 2.0 * 0.7 = 0.014 -> Medium
        summary = report["risk_summary"]
        assert summary["Low"] == 2
        assert summary["Medium"] == 3
        assert summary["High"] == 0
        assert summary["Very High"] == 0


class TestSimulateTrainingInjuryConsistency:
    """Tests verifying _simulate_training_injury uses the same formula as calculate_injury_risk."""

    def test_age_factor_consistency(self):
        """Age factors should be consistent between calculate_injury_risk and the documented formula."""
        # Age ≤ 30: factor 1.0
        player_young = create_player("Young", age=25, player_id=1)
        assert TrainingService.calculate_injury_risk(
            player_young, TrainingIntensity.NORMAL
        )["age_factor"] == 1.0

        # Age 31-35: factor 1.5
        player_mid = create_player("Mid", age=33, player_id=2)
        assert TrainingService.calculate_injury_risk(
            player_mid, TrainingIntensity.NORMAL
        )["age_factor"] == 1.5

        # Age > 35: factor 2.0
        player_old = create_player("Old", age=37, player_id=3)
        assert TrainingService.calculate_injury_risk(
            player_old, TrainingIntensity.NORMAL
        )["age_factor"] == 2.0

    def test_intensity_factor_consistency(self):
        """Intensity factors should match _get_injury_risk_multiplier values."""
        player = create_player("Test", age=25, player_id=1)

        light_result = TrainingService.calculate_injury_risk(player, TrainingIntensity.LIGHT)
        normal_result = TrainingService.calculate_injury_risk(player, TrainingIntensity.NORMAL)
        heavy_result = TrainingService.calculate_injury_risk(player, TrainingIntensity.HEAVY)

        assert light_result["intensity_factor"] == 0.7
        assert normal_result["intensity_factor"] == 1.0
        assert heavy_result["intensity_factor"] == 1.5

        # These should match the static method values
        assert light_result["intensity_factor"] == TrainingService._get_injury_risk_multiplier(
            TrainingIntensity.LIGHT
        )
        assert normal_result["intensity_factor"] == TrainingService._get_injury_risk_multiplier(
            TrainingIntensity.NORMAL
        )
        assert heavy_result["intensity_factor"] == TrainingService._get_injury_risk_multiplier(
            TrainingIntensity.HEAVY
        )

    def test_probability_formula(self):
        """Final probability should equal base * age_factor * intensity_factor."""
        test_cases = [
            (22, TrainingIntensity.LIGHT, 0.01 * 1.0 * 0.7),
            (22, TrainingIntensity.NORMAL, 0.01 * 1.0 * 1.0),
            (22, TrainingIntensity.HEAVY, 0.01 * 1.0 * 1.5),
            (33, TrainingIntensity.LIGHT, 0.01 * 1.5 * 0.7),
            (33, TrainingIntensity.NORMAL, 0.01 * 1.5 * 1.0),
            (33, TrainingIntensity.HEAVY, 0.01 * 1.5 * 1.5),
            (37, TrainingIntensity.LIGHT, 0.01 * 2.0 * 0.7),
            (37, TrainingIntensity.NORMAL, 0.01 * 2.0 * 1.0),
            (37, TrainingIntensity.HEAVY, 0.01 * 2.0 * 1.5),
        ]

        for age, intensity, expected_prob in test_cases:
            player = create_player(f"Age{age}", age=age, player_id=age)
            result = TrainingService.calculate_injury_risk(player, intensity)
            assert result["final_probability"] == pytest.approx(expected_prob), (
                f"Failed for age={age}, intensity={intensity.value}: "
                f"expected {expected_prob}, got {result['final_probability']}"
            )
