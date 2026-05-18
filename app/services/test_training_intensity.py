"""
Unit tests for Training Intensity Settings (Task 10.11)

Tests the set_training_intensity() and get_training_intensity() methods
in TrainingService, and verifies that intensity persists and is applied
when creating new training schedules.
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


@pytest.fixture
async def test_data(db_session):
    """Create test data for training intensity tests"""
    # Create user
    user = User(
        telegram_id=99999,
        username="intensity_test_user",
        first_name="Intensity",
        language_code="en"
    )
    db_session.add(user)
    await db_session.flush()

    # Create club
    club = Club(
        name="Intensity FC",
        reputation=60,
        balance=2000000,
        transfer_budget=1000000,
        wage_budget=80000
    )
    db_session.add(club)
    await db_session.flush()

    # Create career with default NORMAL intensity
    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Intensity Manager",
        current_season=1,
        current_week=5,
        training_intensity=TrainingIntensity.NORMAL
    )
    db_session.add(career)
    await db_session.flush()

    # Create a player
    player = Player(
        uid="intensity_player_001",
        name="Test Player",
        position="CM",
        age=22,
        ca=120,
        pa=160,
        nationality="England",
        club="Intensity FC",
        corners=10, crossing=10, dribbling=12, finishing=14, first_touch=12,
        free_kicks=10, heading=11, long_shots=12, long_throws=8, marking=8,
        passing=11, penalty=12, tackling=8, technique=13,
        aggression=10, anticipation=12, bravery=11, composure=12, concentration=11,
        decisions=11, determination=13, flair=12, leadership=8, off_the_ball=13,
        positioning=11, teamwork=12, vision=11, work_rate=13,
        acceleration=14, agility=13, balance=12, jumping=11, stamina=13,
        pace=14, endurance=13, strength=11,
        price="5M", wage=10000,
        height=180, weight=75, left_foot=8, right_foot=16
    )
    db_session.add(player)
    await db_session.flush()

    # Create squad player
    squad_player = SquadPlayer(
        career_id=career.id,
        player_id=player.id,
        squad_status="first_team",
        morale=75,
        contract_expiry_season=5,
        contract_expiry_week=1,
        wage=10000
    )
    db_session.add(squad_player)
    await db_session.flush()

    # Create a training schedule for the current week
    schedule = TrainingSchedule(
        career_id=career.id,
        player_id=player.id,
        squad_player_id=squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=5,
        consecutive_weeks=2
    )
    db_session.add(schedule)
    await db_session.commit()

    return {
        "user": user,
        "club": club,
        "career": career,
        "player": player,
        "squad_player": squad_player,
        "schedule": schedule
    }


@pytest.mark.asyncio
async def test_get_training_intensity_default(training_service, test_data):
    """Test that default training intensity is NORMAL"""
    career = test_data["career"]

    result = await training_service.get_training_intensity(career.id)

    assert result["career_id"] == career.id
    assert result["intensity"] == "normal"
    assert result["development_multiplier"] == 1.0
    assert result["injury_risk_multiplier"] == 1.0
    assert "description" in result


@pytest.mark.asyncio
async def test_set_training_intensity_to_heavy(training_service, test_data, db_session):
    """Test setting training intensity to HEAVY"""
    career = test_data["career"]

    result = await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.HEAVY
    )

    assert result["career_id"] == career.id
    assert result["previous_intensity"] == "normal"
    assert result["new_intensity"] == "heavy"
    assert result["development_multiplier"] == 1.2
    assert result["injury_risk_multiplier"] == 1.5
    assert result["schedules_updated"] == 1  # One schedule exists for current week

    # Verify career was updated
    await db_session.refresh(career)
    assert career.training_intensity == TrainingIntensity.HEAVY


@pytest.mark.asyncio
async def test_set_training_intensity_to_light(training_service, test_data, db_session):
    """Test setting training intensity to LIGHT"""
    career = test_data["career"]

    result = await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.LIGHT
    )

    assert result["previous_intensity"] == "normal"
    assert result["new_intensity"] == "light"
    assert result["development_multiplier"] == 0.8
    assert result["injury_risk_multiplier"] == 0.7

    # Verify career was updated
    await db_session.refresh(career)
    assert career.training_intensity == TrainingIntensity.LIGHT


@pytest.mark.asyncio
async def test_set_training_intensity_updates_existing_schedules(
    training_service, test_data, db_session
):
    """Test that setting intensity updates all current week schedules"""
    career = test_data["career"]
    schedule = test_data["schedule"]

    # Verify initial intensity on schedule
    assert schedule.training_intensity == TrainingIntensity.NORMAL

    # Set to heavy
    await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.HEAVY
    )

    # Refresh schedule and verify it was updated
    await db_session.refresh(schedule)
    assert schedule.training_intensity == TrainingIntensity.HEAVY


@pytest.mark.asyncio
async def test_set_training_intensity_invalid_career(training_service):
    """Test that setting intensity for invalid career raises ValueError"""
    with pytest.raises(ValueError, match="Career 99999 not found"):
        await training_service.set_training_intensity(
            career_id=99999,
            intensity=TrainingIntensity.HEAVY
        )


@pytest.mark.asyncio
async def test_get_training_intensity_invalid_career(training_service):
    """Test that getting intensity for invalid career raises ValueError"""
    with pytest.raises(ValueError, match="Career 99999 not found"):
        await training_service.get_training_intensity(career_id=99999)


@pytest.mark.asyncio
async def test_intensity_persists_across_calls(training_service, test_data, db_session):
    """Test that intensity setting persists and can be retrieved"""
    career = test_data["career"]

    # Set to heavy
    await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.HEAVY
    )

    # Get intensity - should be heavy
    result = await training_service.get_training_intensity(career.id)
    assert result["intensity"] == "heavy"

    # Set to light
    await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.LIGHT
    )

    # Get intensity - should be light
    result = await training_service.get_training_intensity(career.id)
    assert result["intensity"] == "light"


@pytest.mark.asyncio
async def test_assign_training_focus_uses_career_intensity(
    training_service, test_data, db_session
):
    """Test that assign_training_focus uses career's intensity when none provided"""
    career = test_data["career"]
    squad_player = test_data["squad_player"]

    # Set career intensity to HEAVY
    await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.HEAVY
    )

    # Assign training focus without specifying intensity (should use career's HEAVY)
    new_schedule = await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=squad_player.id,
        training_focus=TrainingFocus.DEFENDING,
        season=1,
        week=6  # Different week to avoid conflict with existing schedule
    )

    assert new_schedule.training_intensity == TrainingIntensity.HEAVY


@pytest.mark.asyncio
async def test_assign_training_focus_explicit_intensity_overrides(
    training_service, test_data, db_session
):
    """Test that explicit intensity in assign_training_focus overrides career setting"""
    career = test_data["career"]
    squad_player = test_data["squad_player"]

    # Set career intensity to HEAVY
    await training_service.set_training_intensity(
        career_id=career.id,
        intensity=TrainingIntensity.HEAVY
    )

    # Assign training focus with explicit LIGHT intensity
    new_schedule = await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=squad_player.id,
        training_focus=TrainingFocus.FITNESS,
        season=1,
        week=7,
        training_intensity=TrainingIntensity.LIGHT
    )

    assert new_schedule.training_intensity == TrainingIntensity.LIGHT


@pytest.mark.asyncio
async def test_intensity_multiplier_values():
    """Test that intensity multiplier static methods return correct values"""
    assert TrainingService._get_development_multiplier(TrainingIntensity.LIGHT) == 0.8
    assert TrainingService._get_development_multiplier(TrainingIntensity.NORMAL) == 1.0
    assert TrainingService._get_development_multiplier(TrainingIntensity.HEAVY) == 1.2

    assert TrainingService._get_injury_risk_multiplier(TrainingIntensity.LIGHT) == 0.7
    assert TrainingService._get_injury_risk_multiplier(TrainingIntensity.NORMAL) == 1.0
    assert TrainingService._get_injury_risk_multiplier(TrainingIntensity.HEAVY) == 1.5


@pytest.mark.asyncio
async def test_get_training_intensity_descriptions(training_service, test_data, db_session):
    """Test that each intensity level has a meaningful description"""
    career = test_data["career"]

    # Test NORMAL description
    result = await training_service.get_training_intensity(career.id)
    assert "Normal" in result["description"] or "normal" in result["description"].lower()
    assert "1.0x" in result["description"]

    # Set to LIGHT and check description
    await training_service.set_training_intensity(career.id, TrainingIntensity.LIGHT)
    result = await training_service.get_training_intensity(career.id)
    assert "0.7x" in result["description"]
    assert "0.8x" in result["description"]

    # Set to HEAVY and check description
    await training_service.set_training_intensity(career.id, TrainingIntensity.HEAVY)
    result = await training_service.get_training_intensity(career.id)
    assert "1.2x" in result["description"]
    assert "1.5x" in result["description"]
