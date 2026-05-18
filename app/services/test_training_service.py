"""
Unit tests for TrainingService

Tests weekly training session simulation, attribute progression/decline,
and training-related functionality.
"""

import pytest
import json
from datetime import datetime
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


@pytest.fixture
async def test_data(db_session):
    """Create test data"""
    # Create user
    user = User(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        language_code="en"
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create club
    club = Club(
        name="Test FC",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=50000
    )
    db_session.add(club)
    await db_session.flush()
    
    # Create career
    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Test Manager",
        current_season=1,
        current_week=1
    )
    db_session.add(career)
    await db_session.flush()
    
    # Create young player (age 22)
    young_player = Player(
        uid="young_001",
        name="Young Talent",
        position="ST",
        age=22,
        ca=120,
        pa=160,
        nationality="England",
        club="Test FC",
        # Technical attributes
        corners=10, crossing=10, dribbling=12, finishing=14, first_touch=12,
        free_kicks=10, heading=11, long_shots=12, long_throws=8, marking=8,
        passing=11, penalty=12, tackling=8, technique=13,
        # Mental attributes
        aggression=10, anticipation=12, bravery=11, composure=12, concentration=11,
        decisions=11, determination=13, flair=12, leadership=8, off_the_ball=13,
        positioning=11, teamwork=12, vision=11, work_rate=13,
        # Physical attributes
        acceleration=14, agility=13, balance=12, jumping=11, stamina=13,
        pace=14, endurance=13, strength=11,
        # Financial
        price="5M", wage=10000,
        # Physical stats
        height=180, weight=75, left_foot=8, right_foot=16
    )
    db_session.add(young_player)
    await db_session.flush()
    
    # Create old player (age 32)
    old_player = Player(
        uid="old_001",
        name="Veteran Player",
        position="CM",
        age=32,
        ca=140,
        pa=140,
        nationality="Spain",
        club="Test FC",
        # Technical attributes
        corners=12, crossing=13, dribbling=14, finishing=13, first_touch=15,
        free_kicks=14, heading=12, long_shots=14, long_throws=10, marking=13,
        passing=16, penalty=14, tackling=13, technique=15,
        # Mental attributes
        aggression=11, anticipation=16, bravery=14, composure=16, concentration=15,
        decisions=17, determination=15, flair=13, leadership=16, off_the_ball=14,
        positioning=16, teamwork=16, vision=17, work_rate=14,
        # Physical attributes
        acceleration=11, agility=12, balance=13, jumping=11, stamina=12,
        pace=11, endurance=12, strength=12,
        # Financial
        price="2M", wage=25000,
        # Physical stats
        height=178, weight=73, left_foot=14, right_foot=15
    )
    db_session.add(old_player)
    await db_session.flush()
    
    # Create squad players
    young_squad_player = SquadPlayer(
        career_id=career.id,
        player_id=young_player.id,
        squad_status="first_team",
        morale=75,
        contract_expiry_season=5,
        contract_expiry_week=1,
        wage=10000
    )
    db_session.add(young_squad_player)
    
    old_squad_player = SquadPlayer(
        career_id=career.id,
        player_id=old_player.id,
        squad_status="key_player",
        morale=80,
        contract_expiry_season=3,
        contract_expiry_week=1,
        wage=25000
    )
    db_session.add(old_squad_player)
    await db_session.flush()
    
    await db_session.commit()
    
    return {
        "user": user,
        "club": club,
        "career": career,
        "young_player": young_player,
        "old_player": old_player,
        "young_squad_player": young_squad_player,
        "old_squad_player": old_squad_player
    }


@pytest.mark.asyncio
async def test_young_player_improvement(training_service, test_data, db_session):
    """Test that young players improve after 4 consecutive weeks"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Record initial finishing attribute
    initial_finishing = young_player.finishing
    
    # Create training schedule for 4 consecutive weeks on attacking focus
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training for week 4
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=4,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Refresh player data
    await db_session.refresh(young_player)
    
    # Check that player improved
    assert result["players_trained"] == 1
    assert len(result["improvements"]) == 1
    assert young_player.finishing > initial_finishing
    
    improvement = result["improvements"][0]
    assert improvement["player_id"] == young_player.id
    assert improvement["age"] == 22
    assert "finishing" in improvement["improvements"]


@pytest.mark.asyncio
async def test_old_player_decline(training_service, test_data, db_session):
    """Test that old players decline without fitness training"""
    career = test_data["career"]
    old_player = test_data["old_player"]
    old_squad_player = test_data["old_squad_player"]
    
    # Record initial stamina and pace
    initial_stamina = old_player.stamina
    initial_pace = old_player.pace
    
    # Create training schedule for 8 consecutive weeks on tactics (not fitness)
    for week in range(1, 9):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=old_player.id,
            squad_player_id=old_squad_player.id,
            training_focus=TrainingFocus.TACTICS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training for week 8
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=8,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Refresh player data
    await db_session.refresh(old_player)
    
    # Check that player declined
    assert result["players_trained"] == 1
    assert len(result["declines"]) == 1
    assert old_player.stamina < initial_stamina or old_player.pace < initial_pace
    
    decline = result["declines"][0]
    assert decline["player_id"] == old_player.id
    assert decline["age"] == 32


@pytest.mark.asyncio
async def test_fitness_training_prevents_decline(training_service, test_data, db_session):
    """Test that fitness training prevents old player decline"""
    career = test_data["career"]
    old_player = test_data["old_player"]
    old_squad_player = test_data["old_squad_player"]
    
    # Record initial stamina and pace
    initial_stamina = old_player.stamina
    initial_pace = old_player.pace
    
    # Create training schedule for 8 consecutive weeks on fitness
    for week in range(1, 9):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=old_player.id,
            squad_player_id=old_squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training for week 8
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=8,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Refresh player data
    await db_session.refresh(old_player)
    
    # Check that player did NOT decline
    assert result["players_trained"] == 1
    assert len(result["declines"]) == 0
    assert old_player.stamina == initial_stamina
    assert old_player.pace == initial_pace


@pytest.mark.asyncio
async def test_training_intensity_affects_development(training_service, test_data, db_session):
    """Test that training intensity affects development rate"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create training schedule with heavy intensity
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.HEAVY,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training with heavy intensity
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=4,
        training_intensity=TrainingIntensity.HEAVY
    )
    
    # Check that multiplier was applied
    assert result["players_trained"] == 1
    if result["improvements"]:
        improvement = result["improvements"][0]
        assert improvement["multiplier"] > 1.0  # Heavy intensity should increase multiplier


@pytest.mark.asyncio
async def test_coach_bonus_application(training_service, test_data, db_session):
    """Test that coach bonuses are applied correctly"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create training schedule
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training with coach bonus (10% bonus for attacking)
    coach_bonuses = {
        TrainingFocus.ATTACKING: 1.1
    }
    
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=4,
        training_intensity=TrainingIntensity.NORMAL,
        coach_bonuses=coach_bonuses
    )
    
    # Check that bonus was applied
    assert result["players_trained"] == 1
    if result["improvements"]:
        improvement = result["improvements"][0]
        assert improvement["multiplier"] >= 1.1


@pytest.mark.asyncio
async def test_infrastructure_bonus_application(training_service, test_data, db_session):
    """Test that infrastructure bonuses are applied correctly"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create training schedule
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training with infrastructure bonus (20% bonus)
    result = await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=4,
        training_intensity=TrainingIntensity.NORMAL,
        infrastructure_bonus=1.2
    )
    
    # Check that bonus was applied
    assert result["players_trained"] == 1
    if result["improvements"]:
        improvement = result["improvements"][0]
        assert improvement["multiplier"] >= 1.2


@pytest.mark.asyncio
async def test_attribute_capped_at_pa(training_service, test_data, db_session):
    """Test that attributes cannot exceed PA"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Set finishing to PA - 1
    young_player.finishing = young_player.pa - 1
    await db_session.commit()
    
    # Create training schedule
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Simulate training
    await training_service.simulate_weekly_training(
        career_id=career.id,
        season=1,
        week=4,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Refresh player data
    await db_session.refresh(young_player)
    
    # Check that finishing did not exceed PA
    assert young_player.finishing <= young_player.pa


@pytest.mark.asyncio
async def test_assign_training_focus(training_service, test_data, db_session):
    """Test assigning training focus to a player"""
    career = test_data["career"]
    young_squad_player = test_data["young_squad_player"]
    
    # Assign training focus
    schedule = await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        season=1,
        week=1,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    assert schedule is not None
    assert schedule.training_focus == TrainingFocus.ATTACKING
    assert schedule.consecutive_weeks == 1


@pytest.mark.asyncio
async def test_consecutive_weeks_reset_on_focus_change(training_service, test_data, db_session):
    """Test that consecutive weeks resets when training focus changes"""
    career = test_data["career"]
    young_squad_player = test_data["young_squad_player"]
    
    # Assign initial focus
    schedule1 = await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        season=1,
        week=1,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Manually set consecutive weeks to 3
    schedule1.consecutive_weeks = 3
    await db_session.commit()
    
    # Change focus
    schedule2 = await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.DEFENDING,
        season=1,
        week=1,
        training_intensity=TrainingIntensity.NORMAL
    )
    
    # Check that consecutive weeks was reset
    assert schedule2.consecutive_weeks == 1


@pytest.mark.asyncio
async def test_get_training_schedule(training_service, test_data, db_session):
    """Test retrieving training schedule for a week"""
    career = test_data["career"]
    young_squad_player = test_data["young_squad_player"]
    old_squad_player = test_data["old_squad_player"]
    
    # Create schedules for both players
    await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        season=1,
        week=1
    )
    
    await training_service.assign_training_focus(
        career_id=career.id,
        squad_player_id=old_squad_player.id,
        training_focus=TrainingFocus.FITNESS,
        season=1,
        week=1
    )
    
    # Get training schedule
    schedules = await training_service.get_training_schedule(
        career_id=career.id,
        season=1,
        week=1
    )
    
    assert len(schedules) == 2


@pytest.mark.asyncio
async def test_get_player_attribute_history(training_service, test_data, db_session):
    """Test retrieving player attribute history"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create training schedule with improvements
    for week in range(1, 5):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week,
            attribute_improvements=json.dumps({
                "finishing": {"old": 14, "new": 15, "change": 1}
            })
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Get attribute history
    history = await training_service.get_player_attribute_history(
        player_id=young_player.id,
        career_id=career.id
    )
    
    assert len(history) == 4
    assert history[0]["training_focus"] == "attacking"
    assert "finishing" in history[0]["changes"]


@pytest.mark.asyncio
async def test_get_player_attribute_history_with_season_filter(training_service, test_data, db_session):
    """Test retrieving player attribute history filtered by season"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create training schedules with improvements across two seasons
    for week in range(1, 3):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=week,
            consecutive_weeks=week,
            attribute_improvements=json.dumps({
                "finishing": {"old": 14, "new": 15, "change": 1}
            })
        )
        db_session.add(schedule)
    
    for week in range(1, 4):
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.DEFENDING,
            training_intensity=TrainingIntensity.NORMAL,
            season=2,
            week=week,
            consecutive_weeks=week,
            attribute_improvements=json.dumps({
                "tackling": {"old": 8, "new": 9, "change": 1}
            })
        )
        db_session.add(schedule)
    
    await db_session.commit()
    
    # Get history for season 1 only
    history_s1 = await training_service.get_player_attribute_history(
        player_id=young_player.id,
        career_id=career.id,
        season=1
    )
    assert len(history_s1) == 2
    assert all(h["season"] == 1 for h in history_s1)
    
    # Get history for season 2 only
    history_s2 = await training_service.get_player_attribute_history(
        player_id=young_player.id,
        career_id=career.id,
        season=2
    )
    assert len(history_s2) == 3
    assert all(h["season"] == 2 for h in history_s2)
    
    # Get all history (no season filter)
    history_all = await training_service.get_player_attribute_history(
        player_id=young_player.id,
        career_id=career.id
    )
    assert len(history_all) == 5


@pytest.mark.asyncio
async def test_get_player_attribute_history_summary(training_service, test_data, db_session):
    """Test summary statistics for attribute history"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create improvements
    schedule1 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=4,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 14, "new": 15, "change": 1},
            "dribbling": {"old": 12, "new": 13, "change": 1}
        })
    )
    db_session.add(schedule1)
    
    schedule2 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=8,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 15, "new": 16, "change": 1}
        })
    )
    db_session.add(schedule2)
    
    # Create a decline record
    old_player = test_data["old_player"]
    old_squad_player = test_data["old_squad_player"]
    schedule3 = TrainingSchedule(
        career_id=career.id,
        player_id=old_player.id,
        squad_player_id=old_squad_player.id,
        training_focus=TrainingFocus.TACTICS,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=8,
        consecutive_weeks=8,
        attribute_improvements=json.dumps({
            "stamina": {"old": 12, "new": 11, "change": -1},
            "pace": {"old": 11, "new": 10, "change": -1}
        })
    )
    db_session.add(schedule3)
    
    await db_session.commit()
    
    # Get summary for young player
    summary = await training_service.get_player_attribute_history_summary(
        player_id=young_player.id,
        career_id=career.id
    )
    
    assert summary["total_changes"] == 2
    assert summary["total_improvements"] == 3  # finishing x2, dribbling x1
    assert summary["total_declines"] == 0
    assert summary["net_change"] == 3
    assert summary["total_points_gained"] == 3
    assert summary["attributes_improved"]["finishing"] == 2
    assert summary["attributes_improved"]["dribbling"] == 1
    assert summary["best_attribute_gain"]["attribute"] == "finishing"
    assert summary["best_attribute_gain"]["points_gained"] == 2
    
    # Get summary for old player
    old_summary = await training_service.get_player_attribute_history_summary(
        player_id=old_player.id,
        career_id=career.id
    )
    
    assert old_summary["total_changes"] == 1
    assert old_summary["total_improvements"] == 0
    assert old_summary["total_declines"] == 2  # stamina, pace
    assert old_summary["net_change"] == -2
    assert old_summary["total_points_lost"] == 2
    assert old_summary["worst_attribute_loss"]["attribute"] in ["stamina", "pace"]


@pytest.mark.asyncio
async def test_get_player_attribute_progression(training_service, test_data, db_session):
    """Test attribute progression chart data"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create a series of improvements over time
    schedule1 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=4,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 14, "new": 15, "change": 1}
        })
    )
    db_session.add(schedule1)
    
    schedule2 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=8,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 15, "new": 16, "change": 1}
        })
    )
    db_session.add(schedule2)
    
    schedule3 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.DEFENDING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=12,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "tackling": {"old": 8, "new": 9, "change": 1}
        })
    )
    db_session.add(schedule3)
    
    await db_session.commit()
    
    # Get full progression
    progression = await training_service.get_player_attribute_progression(
        player_id=young_player.id,
        career_id=career.id
    )
    
    assert progression["player_id"] == young_player.id
    assert progression["career_id"] == career.id
    assert len(progression["timeline"]) == 3
    
    # Check timeline is chronological
    assert progression["timeline"][0]["week"] == 4
    assert progression["timeline"][1]["week"] == 8
    assert progression["timeline"][2]["week"] == 12
    
    # Check attribute series
    assert "finishing" in progression["attribute_series"]
    assert "tackling" in progression["attribute_series"]
    
    # Finishing should have initial + 2 data points
    finishing_series = progression["attribute_series"]["finishing"]
    assert len(finishing_series) == 3  # initial(14) + 15 + 16
    assert finishing_series[0]["value"] == 14
    assert finishing_series[0]["is_initial"] is True
    assert finishing_series[1]["value"] == 15
    assert finishing_series[2]["value"] == 16
    
    # Check current values are populated
    assert "finishing" in progression["current_values"]


@pytest.mark.asyncio
async def test_get_player_attribute_progression_filtered(training_service, test_data, db_session):
    """Test attribute progression with specific attribute filter"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Create improvements for multiple attributes
    schedule = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=4,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 14, "new": 15, "change": 1},
            "dribbling": {"old": 12, "new": 13, "change": 1},
            "composure": {"old": 12, "new": 13, "change": 1}
        })
    )
    db_session.add(schedule)
    await db_session.commit()
    
    # Get progression for only finishing
    progression = await training_service.get_player_attribute_progression(
        player_id=young_player.id,
        career_id=career.id,
        attributes=["finishing"]
    )
    
    assert "finishing" in progression["attribute_series"]
    assert "dribbling" not in progression["attribute_series"]
    assert "composure" not in progression["attribute_series"]
    assert len(progression["timeline"]) == 1
    assert progression["timeline"][0]["attribute"] == "finishing"


@pytest.mark.asyncio
async def test_get_player_attribute_history_summary_by_season(training_service, test_data, db_session):
    """Test summary statistics filtered by season"""
    career = test_data["career"]
    young_player = test_data["young_player"]
    young_squad_player = test_data["young_squad_player"]
    
    # Season 1 improvements
    schedule1 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=4,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "finishing": {"old": 14, "new": 15, "change": 1}
        })
    )
    db_session.add(schedule1)
    
    # Season 2 improvements
    schedule2 = TrainingSchedule(
        career_id=career.id,
        player_id=young_player.id,
        squad_player_id=young_squad_player.id,
        training_focus=TrainingFocus.DEFENDING,
        training_intensity=TrainingIntensity.NORMAL,
        season=2,
        week=4,
        consecutive_weeks=4,
        attribute_improvements=json.dumps({
            "tackling": {"old": 8, "new": 9, "change": 1},
            "marking": {"old": 8, "new": 9, "change": 1}
        })
    )
    db_session.add(schedule2)
    
    await db_session.commit()
    
    # Get summary for season 1 only
    summary_s1 = await training_service.get_player_attribute_history_summary(
        player_id=young_player.id,
        career_id=career.id,
        season=1
    )
    
    assert summary_s1["total_changes"] == 1
    assert summary_s1["total_improvements"] == 1
    assert "finishing" in summary_s1["attributes_improved"]
    assert "tackling" not in summary_s1["attributes_improved"]
    
    # Get summary for season 2 only
    summary_s2 = await training_service.get_player_attribute_history_summary(
        player_id=young_player.id,
        career_id=career.id,
        season=2
    )
    
    assert summary_s2["total_changes"] == 1
    assert summary_s2["total_improvements"] == 2
    assert "tackling" in summary_s2["attributes_improved"]
    assert "marking" in summary_s2["attributes_improved"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
