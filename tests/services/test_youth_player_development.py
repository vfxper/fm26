"""
Unit tests for Youth Player Development System (Task 10.10)

Tests the specialized youth development path for players aged 15-18 with:
- Accelerated development (3 weeks instead of 4)
- Enhanced development rate (1.5x multiplier)
- Youth Academy infrastructure level impact
- Youth player identification
- Youth development report generation
"""

import pytest
import json
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.injury import Injury
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
        await conn.run_sync(Base.metadata.create_all)

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


def _create_player(uid, name, age, ca, pa, **kwargs):
    """Helper to create a Player with default attributes."""
    defaults = dict(
        position="ST", nationality="England", club="Test FC",
        corners=10, crossing=10, dribbling=10, finishing=10, first_touch=10,
        free_kicks=10, heading=10, long_shots=10, long_throws=10, marking=10,
        passing=10, penalty=10, tackling=10, technique=10,
        aggression=10, anticipation=10, bravery=10, composure=10, concentration=10,
        decisions=10, determination=10, flair=10, leadership=10, off_the_ball=10,
        positioning=10, teamwork=10, vision=10, work_rate=10,
        acceleration=10, agility=10, balance=10, jumping=10, stamina=10,
        pace=10, endurance=10, strength=10,
        price="1M", wage=5000, height=175, weight=70, left_foot=10, right_foot=15
    )
    defaults.update(kwargs)
    return Player(uid=uid, name=name, age=age, ca=ca, pa=pa, **defaults)


@pytest.fixture
async def test_data(db_session):
    """Create test data with youth players, young players, and old players."""
    # Create user
    user = User(
        telegram_user_id=99999,
        username="youthtest",
        first_name="Youth",
        language_code="en"
    )
    db_session.add(user)
    await db_session.flush()

    # Create club with Youth Academy level 3 (Good)
    club = Club(
        name="Youth FC",
        reputation=60,
        league="Premier League",
        country="England",
        balance=2000000,
        transfer_budget=500000,
        wage_budget=80000,
        youth_academy_level=3,
        training_facilities_level=3,
        stadium_level=3,
        medical_centre_level=3,
        scouting_network_level=3
    )
    db_session.add(club)
    await db_session.flush()

    # Create career
    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Youth Dev Manager",
        current_season=1,
        current_week=5
    )
    db_session.add(career)
    await db_session.flush()

    # Create youth player (age 16)
    youth_player_16 = _create_player(
        uid="youth_16", name="Young Prodigy", age=16, ca=80, pa=180,
        finishing=8, dribbling=9, passing=8, off_the_ball=9, composure=7
    )
    db_session.add(youth_player_16)
    await db_session.flush()

    # Create youth player (age 18 - upper boundary)
    youth_player_18 = _create_player(
        uid="youth_18", name="Academy Graduate", age=18, ca=100, pa=160,
        finishing=11, dribbling=12, passing=11, off_the_ball=11, composure=10
    )
    db_session.add(youth_player_18)
    await db_session.flush()

    # Create young player (age 22 - NOT youth, regular young)
    young_player_22 = _create_player(
        uid="young_22", name="Regular Young", age=22, ca=130, pa=165,
        finishing=13, dribbling=14, passing=13, off_the_ball=13, composure=12
    )
    db_session.add(young_player_22)
    await db_session.flush()

    # Create old player (age 33)
    old_player = _create_player(
        uid="old_33", name="Veteran", age=33, ca=140, pa=140,
        finishing=15, dribbling=14, passing=16, stamina=11, pace=10
    )
    db_session.add(old_player)
    await db_session.flush()

    # Create squad players
    youth_sp_16 = SquadPlayer(
        career_id=career.id, player_id=youth_player_16.id,
        squad_status="first_team", morale=80,
        contract_start_date=date(2025, 1, 1),
        contract_end_date=date(2029, 6, 30),
        wage=2000, squad_number=44
    )
    db_session.add(youth_sp_16)

    youth_sp_18 = SquadPlayer(
        career_id=career.id, player_id=youth_player_18.id,
        squad_status="first_team", morale=75,
        contract_start_date=date(2025, 1, 1),
        contract_end_date=date(2028, 6, 30),
        wage=5000, squad_number=45
    )
    db_session.add(youth_sp_18)

    young_sp_22 = SquadPlayer(
        career_id=career.id, player_id=young_player_22.id,
        squad_status="first_team", morale=70,
        contract_start_date=date(2024, 7, 1),
        contract_end_date=date(2027, 6, 30),
        wage=15000, squad_number=9
    )
    db_session.add(young_sp_22)

    old_sp = SquadPlayer(
        career_id=career.id, player_id=old_player.id,
        squad_status="key_player", morale=80,
        contract_start_date=date(2024, 7, 1),
        contract_end_date=date(2026, 6, 30),
        wage=30000, squad_number=7
    )
    db_session.add(old_sp)
    await db_session.flush()
    await db_session.commit()

    return {
        "user": user,
        "club": club,
        "career": career,
        "youth_player_16": youth_player_16,
        "youth_player_18": youth_player_18,
        "young_player_22": young_player_22,
        "old_player": old_player,
        "youth_sp_16": youth_sp_16,
        "youth_sp_18": youth_sp_18,
        "young_sp_22": young_sp_22,
        "old_sp": old_sp,
    }


class TestYouthPlayerIdentification:
    """Tests for identifying youth players (age 15-18)."""

    @pytest.mark.asyncio
    async def test_is_youth_player_age_16(self, training_service, test_data):
        """Youth player age 16 should be identified as youth."""
        player = test_data["youth_player_16"]
        assert training_service._is_youth_player(player) is True

    @pytest.mark.asyncio
    async def test_is_youth_player_age_18(self, training_service, test_data):
        """Youth player age 18 (upper boundary) should be identified as youth."""
        player = test_data["youth_player_18"]
        assert training_service._is_youth_player(player) is True

    @pytest.mark.asyncio
    async def test_is_not_youth_player_age_22(self, training_service, test_data):
        """Player age 22 should NOT be identified as youth."""
        player = test_data["young_player_22"]
        assert training_service._is_youth_player(player) is False

    @pytest.mark.asyncio
    async def test_is_not_youth_player_age_33(self, training_service, test_data):
        """Player age 33 should NOT be identified as youth."""
        player = test_data["old_player"]
        assert training_service._is_youth_player(player) is False

    @pytest.mark.asyncio
    async def test_is_youth_player_age_15_boundary(self, training_service):
        """Player age 15 (lower boundary) should be identified as youth."""
        player = _create_player(uid="youth_15", name="Youngest", age=15, ca=60, pa=170)
        assert training_service._is_youth_player(player) is True

    @pytest.mark.asyncio
    async def test_is_not_youth_player_age_14(self, training_service):
        """Player age 14 (below minimum) should NOT be identified as youth."""
        player = _create_player(uid="too_young", name="Too Young", age=14, ca=50, pa=170)
        assert training_service._is_youth_player(player) is False

    @pytest.mark.asyncio
    async def test_is_not_youth_player_age_19(self, training_service):
        """Player age 19 (just above max) should NOT be identified as youth."""
        player = _create_player(uid="not_youth", name="Not Youth", age=19, ca=110, pa=160)
        assert training_service._is_youth_player(player) is False

    @pytest.mark.asyncio
    async def test_get_youth_players_from_squad(self, training_service, test_data):
        """Should correctly filter youth players from a list."""
        all_players = [
            test_data["youth_player_16"],
            test_data["youth_player_18"],
            test_data["young_player_22"],
            test_data["old_player"],
        ]
        youth = training_service.get_youth_players_from_squad(all_players)
        assert len(youth) == 2
        assert test_data["youth_player_16"] in youth
        assert test_data["youth_player_18"] in youth


class TestYouthPlayerDevelopment:
    """Tests for youth player accelerated development."""

    @pytest.mark.asyncio
    async def test_youth_improves_after_3_weeks(self, training_service, test_data, db_session):
        """Youth player should improve after 3 consecutive weeks (not 4)."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        initial_finishing = player.finishing

        # Create training schedule with 3 consecutive weeks on attacking
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        # Process youth player training
        result = await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=1
        )

        assert result is not None
        assert result["is_youth_development"] is True
        assert player.finishing > initial_finishing

    @pytest.mark.asyncio
    async def test_youth_does_not_improve_after_2_weeks(self, training_service, test_data, db_session):
        """Youth player should NOT improve after only 2 consecutive weeks."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        initial_finishing = player.finishing

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=2,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        result = await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=1
        )

        assert result is None
        assert player.finishing == initial_finishing

    @pytest.mark.asyncio
    async def test_youth_enhanced_development_rate(self, training_service, test_data, db_session):
        """Youth player should get 1.5x development rate."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        result = await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=1
        )

        assert result is not None
        # With 1.5x multiplier and base 1, round(1 * 1.5 * 1.0) = 2
        assert result["multiplier"] == 1.5

    @pytest.mark.asyncio
    async def test_youth_academy_level_affects_development(self, training_service, test_data, db_session):
        """Higher Youth Academy level should increase development rate."""
        career = test_data["career"]
        player = test_data["youth_player_18"]
        sp = test_data["youth_sp_18"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        # Test with World Class academy (level 5 = 1.5 bonus)
        result = await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=5
        )

        assert result is not None
        # 1.0 * 1.5 (youth) * 1.5 (academy level 5) = 2.25
        assert result["multiplier"] == pytest.approx(2.25)
        assert result["youth_academy_level"] == 5

    @pytest.mark.asyncio
    async def test_youth_capped_at_pa(self, training_service, db_session, test_data):
        """Youth player attributes should not exceed PA."""
        career = test_data["career"]

        # Create a player with finishing already at PA
        player = _create_player(
            uid="capped_youth", name="Capped Youth", age=17, ca=100, pa=100,
            finishing=20  # Already at max attribute
        )
        db_session.add(player)
        await db_session.flush()

        sp = SquadPlayer(
            career_id=career.id, player_id=player.id,
            squad_status="first_team", morale=80,
            contract_expiry_season=5, contract_expiry_week=1,
            wage=3000, squad_number=50
        )
        db_session.add(sp)
        await db_session.flush()

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        result = await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=5
        )

        # All attacking attributes at max, so no improvement possible
        # finishing=20 is at MAX_ATTRIBUTE, others may still improve
        # The result depends on whether other attacking attrs can improve
        if result is not None:
            # If there were improvements, verify none exceed limits
            for attr_name, change in result["improvements"].items():
                assert change["new"] <= player.pa
                assert change["new"] <= 20

    @pytest.mark.asyncio
    async def test_youth_resets_consecutive_weeks_after_improvement(
        self, training_service, test_data, db_session
    ):
        """After improvement, consecutive weeks should reset."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.flush()

        await training_service._process_youth_player_training(
            player, schedule, multiplier=1.0, youth_academy_level=1
        )

        assert schedule.consecutive_weeks == 1


class TestYouthAcademyLevelFetch:
    """Tests for fetching Youth Academy level from career's club."""

    @pytest.mark.asyncio
    async def test_get_youth_academy_level(self, training_service, test_data):
        """Should fetch correct Youth Academy level from club."""
        career = test_data["career"]
        level = await training_service._get_youth_academy_level(career.id)
        assert level == 3  # Club was created with youth_academy_level=3

    @pytest.mark.asyncio
    async def test_get_youth_academy_level_nonexistent_career(self, training_service):
        """Should return default level 1 for non-existent career."""
        level = await training_service._get_youth_academy_level(99999)
        assert level == 1


class TestYouthDevelopmentReport:
    """Tests for the youth player development report."""

    @pytest.mark.asyncio
    async def test_report_identifies_all_youth_players(
        self, training_service, test_data, db_session
    ):
        """Report should include all youth players (age 15-18) in squad."""
        career = test_data["career"]
        report = await training_service.get_youth_player_development_report(career.id)

        assert report["total_youth_players"] == 2
        player_ids = [p["player_id"] for p in report["youth_players"]]
        assert test_data["youth_player_16"].id in player_ids
        assert test_data["youth_player_18"].id in player_ids
        # Regular young player (22) should NOT be in report
        assert test_data["young_player_22"].id not in player_ids

    @pytest.mark.asyncio
    async def test_report_includes_academy_level(self, training_service, test_data):
        """Report should include Youth Academy level info."""
        career = test_data["career"]
        report = await training_service.get_youth_player_development_report(career.id)

        assert report["youth_academy_level"] == 3
        assert report["youth_academy_level_name"] == "Good"

    @pytest.mark.asyncio
    async def test_report_includes_development_bonus_info(self, training_service, test_data):
        """Report should include development bonus calculations."""
        career = test_data["career"]
        report = await training_service.get_youth_player_development_report(career.id)

        bonus = report["development_bonus"]
        assert bonus["youth_multiplier"] == 1.5
        assert bonus["academy_bonus"] == 1.2  # Level 3 = 20% bonus
        assert bonus["combined_bonus"] == pytest.approx(1.8)
        assert bonus["weeks_to_improve"] == 3
        assert bonus["regular_weeks_to_improve"] == 4

    @pytest.mark.asyncio
    async def test_report_tracks_improvements(self, training_service, test_data, db_session):
        """Report should track attribute improvements for youth players."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        # Create a training schedule with recorded improvements
        improvements = {"finishing": {"old": 8, "new": 10, "change": 2}}
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=3,
            consecutive_weeks=1,
            is_injured=False,
            attribute_improvements=json.dumps(improvements)
        )
        db_session.add(schedule)
        await db_session.commit()

        report = await training_service.get_youth_player_development_report(career.id)

        assert report["total_improvements_this_season"] == 2
        # Find the youth player entry
        youth_entry = next(
            p for p in report["youth_players"] if p["player_id"] == player.id
        )
        assert youth_entry["season_improvements"]["total_points"] == 2

    @pytest.mark.asyncio
    async def test_report_shows_potential_gap(self, training_service, test_data):
        """Report should show gap between CA and PA for each youth player."""
        career = test_data["career"]
        report = await training_service.get_youth_player_development_report(career.id)

        youth_16_entry = next(
            p for p in report["youth_players"]
            if p["player_id"] == test_data["youth_player_16"].id
        )
        # CA=80, PA=180, gap=100
        assert youth_16_entry["potential_gap"] == 100


class TestImprovementProgressCalculation:
    """Tests for the progress calculation method with youth players."""

    @pytest.mark.asyncio
    async def test_youth_progress_type(self, training_service):
        """Youth player progress should be type 'youth_development'."""
        progress = training_service._calculate_improvement_progress(
            player_age=16, consecutive_weeks=2
        )
        assert progress["type"] == "youth_development"
        assert progress["required_weeks"] == 3

    @pytest.mark.asyncio
    async def test_youth_progress_percentage(self, training_service):
        """Youth player progress percentage should be based on 3 weeks."""
        progress = training_service._calculate_improvement_progress(
            player_age=17, consecutive_weeks=2
        )
        # 2/3 = 66%
        assert progress["percentage"] == 66

    @pytest.mark.asyncio
    async def test_regular_young_progress_type(self, training_service):
        """Regular young player (age 22) should use standard improvement type."""
        progress = training_service._calculate_improvement_progress(
            player_age=22, consecutive_weeks=3
        )
        assert progress["type"] == "improvement"
        assert progress["required_weeks"] == 4

    @pytest.mark.asyncio
    async def test_youth_at_boundary_age_15(self, training_service):
        """Age 15 should use youth development path."""
        progress = training_service._calculate_improvement_progress(
            player_age=15, consecutive_weeks=1
        )
        assert progress["type"] == "youth_development"

    @pytest.mark.asyncio
    async def test_non_youth_age_19(self, training_service):
        """Age 19 should use regular improvement path."""
        progress = training_service._calculate_improvement_progress(
            player_age=19, consecutive_weeks=2
        )
        assert progress["type"] == "improvement"
        assert progress["required_weeks"] == 4


class TestWeeklyTrainingWithYouth:
    """Tests for the full weekly training simulation with youth players."""

    @pytest.mark.asyncio
    async def test_simulate_weekly_training_separates_youth(
        self, training_service, test_data, db_session
    ):
        """Weekly training should track youth developments separately."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        # Create training schedule with 3 consecutive weeks
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.commit()

        result = await training_service.simulate_weekly_training(
            career_id=career.id,
            season=1,
            week=5,
            training_intensity=TrainingIntensity.NORMAL,
            coach_bonuses={},
            infrastructure_bonus=1.0,
            auto_fetch_coach_bonuses=False,
            youth_academy_level=3
        )

        assert "youth_developments" in result
        assert len(result["youth_developments"]) >= 1
        # Youth development should be in youth_developments, not improvements
        youth_dev = result["youth_developments"][0]
        assert youth_dev["is_youth_development"] is True
        assert youth_dev["player_id"] == player.id

    @pytest.mark.asyncio
    async def test_summary_includes_youth_developments(
        self, training_service, test_data, db_session
    ):
        """Training summary should mention youth player developments."""
        career = test_data["career"]
        player = test_data["youth_player_16"]
        sp = test_data["youth_sp_16"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=sp.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            is_injured=False
        )
        db_session.add(schedule)
        await db_session.commit()

        result = await training_service.simulate_weekly_training(
            career_id=career.id,
            season=1,
            week=5,
            training_intensity=TrainingIntensity.NORMAL,
            coach_bonuses={},
            infrastructure_bonus=1.0,
            auto_fetch_coach_bonuses=False,
            youth_academy_level=3
        )

        assert "youth players developed" in result["summary"]
