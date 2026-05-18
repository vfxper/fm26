"""
Unit tests for automatic rehabilitation system for injured players.

Tests the complete rehabilitation workflow:
1. Injured players are automatically assigned to REHABILITATION training
2. Injured players cannot be assigned to other training focus areas
3. When a player recovers, their training focus is restored to previous focus or GENERAL
4. REHABILITATION provides no attribute improvements
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
from app.models.injury import Injury, InjurySeverity, InjuryStatus
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
    """Create test data for rehabilitation tests"""
    # Create user
    user = User(
        telegram_id=99999,
        username="rehab_test_user",
        first_name="Rehab",
        language_code="en"
    )
    db_session.add(user)
    await db_session.flush()

    # Create club
    club = Club(
        name="Rehab FC",
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
        manager_name="Rehab Manager",
        current_season=1,
        current_week=5
    )
    db_session.add(career)
    await db_session.flush()

    # Create player
    player = Player(
        uid="rehab_player_001",
        name="Test Player",
        position="CM",
        age=25,
        ca=130,
        pa=160,
        nationality="England",
        club="Rehab FC",
        corners=10, crossing=10, dribbling=12, finishing=12, first_touch=12,
        free_kicks=10, heading=11, long_shots=12, long_throws=8, marking=10,
        passing=13, penalty=12, tackling=11, technique=13,
        aggression=10, anticipation=12, bravery=11, composure=12, concentration=11,
        decisions=12, determination=13, flair=11, leadership=10, off_the_ball=12,
        positioning=12, teamwork=13, vision=12, work_rate=13,
        acceleration=13, agility=12, balance=12, jumping=11, stamina=14,
        pace=13, endurance=13, strength=12,
        price="3M", wage=15000,
        height=180, weight=75, left_foot=10, right_foot=16
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
        wage=15000
    )
    db_session.add(squad_player)
    await db_session.flush()

    await db_session.commit()

    return {
        "user": user,
        "club": club,
        "career": career,
        "player": player,
        "squad_player": squad_player
    }


class TestRehabilitationAutoAssignment:
    """Test that injured players are automatically assigned to REHABILITATION"""

    @pytest.mark.asyncio
    async def test_set_injured_assigns_rehabilitation(self, db_session, test_data):
        """Test that set_injured() changes training focus to REHABILITATION"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create a training schedule with ATTACKING focus
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3
        )
        db_session.add(schedule)
        await db_session.commit()

        # Simulate injury
        schedule.set_injured()
        await db_session.commit()

        assert schedule.is_injured is True
        assert schedule.training_focus == TrainingFocus.REHABILITATION
        assert schedule.previous_training_focus == "attacking"
        assert schedule.consecutive_weeks == 1

    @pytest.mark.asyncio
    async def test_set_player_injured_service_method(
        self, training_service, test_data, db_session
    ):
        """Test TrainingService.set_player_injured() method"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create a training schedule with TACTICS focus
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.TACTICS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=2
        )
        db_session.add(schedule)
        await db_session.commit()

        # Use service method to set player injured
        result = await training_service.set_player_injured(
            career_id=career.id,
            squad_player_id=squad_player.id,
            season=1,
            week=5
        )

        assert result is not None
        assert result.is_injured is True
        assert result.training_focus == TrainingFocus.REHABILITATION
        assert result.previous_training_focus == "tactics"

    @pytest.mark.asyncio
    async def test_set_player_injured_creates_schedule_if_none_exists(
        self, training_service, test_data, db_session
    ):
        """Test that set_player_injured creates a REHABILITATION schedule if none exists"""
        career = test_data["career"]
        squad_player = test_data["squad_player"]

        # No schedule exists for this week
        result = await training_service.set_player_injured(
            career_id=career.id,
            squad_player_id=squad_player.id,
            season=1,
            week=10  # Different week with no existing schedule
        )

        assert result is not None
        assert result.is_injured is True
        assert result.training_focus == TrainingFocus.REHABILITATION
        assert result.previous_training_focus == "general"

    @pytest.mark.asyncio
    async def test_training_injury_sets_rehabilitation(
        self, training_service, test_data, db_session
    ):
        """Test that training injuries automatically set REHABILITATION via set_injured()"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create a training schedule
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.HEAVY,
            season=1,
            week=5,
            consecutive_weeks=1
        )
        db_session.add(schedule)
        await db_session.commit()

        # Simulate what _simulate_training_injury does when injury occurs
        schedule.set_injured()
        await db_session.commit()

        assert schedule.is_injured is True
        assert schedule.training_focus == TrainingFocus.REHABILITATION
        assert schedule.previous_training_focus == "fitness"


class TestInjuredPlayerCannotChangeTraining:
    """Test that injured players cannot be assigned to non-REHABILITATION focus"""

    @pytest.mark.asyncio
    async def test_cannot_assign_injured_player_to_attacking(
        self, training_service, test_data, db_session
    ):
        """Test that assigning injured player to ATTACKING raises ValueError"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create an injured training schedule
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True,
            previous_training_focus="attacking"
        )
        db_session.add(schedule)
        await db_session.commit()

        # Try to assign to ATTACKING - should raise ValueError
        with pytest.raises(ValueError, match="Cannot assign injured player"):
            await training_service.assign_training_focus(
                career_id=career.id,
                squad_player_id=squad_player.id,
                training_focus=TrainingFocus.ATTACKING,
                season=1,
                week=5
            )

    @pytest.mark.asyncio
    async def test_cannot_assign_injured_player_to_fitness(
        self, training_service, test_data, db_session
    ):
        """Test that assigning injured player to FITNESS raises ValueError"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create an injured training schedule
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True
        )
        db_session.add(schedule)
        await db_session.commit()

        with pytest.raises(ValueError, match="Cannot assign injured player"):
            await training_service.assign_training_focus(
                career_id=career.id,
                squad_player_id=squad_player.id,
                training_focus=TrainingFocus.FITNESS,
                season=1,
                week=5
            )

    @pytest.mark.asyncio
    async def test_can_assign_injured_player_to_rehabilitation(
        self, training_service, test_data, db_session
    ):
        """Test that assigning injured player to REHABILITATION is allowed"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create an injured training schedule
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True
        )
        db_session.add(schedule)
        await db_session.commit()

        # Assigning to REHABILITATION should work fine
        result = await training_service.assign_training_focus(
            career_id=career.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            season=1,
            week=5
        )

        assert result.training_focus == TrainingFocus.REHABILITATION
        assert result.is_injured is True

    @pytest.mark.asyncio
    async def test_cannot_assign_new_schedule_for_injured_player(
        self, training_service, test_data, db_session
    ):
        """Test that creating a new schedule for an injured player validates injury status"""
        career = test_data["career"]
        squad_player = test_data["squad_player"]

        # Create an active injury for the player
        injury = Injury(
            career_id=career.id,
            player_id=test_data["player"].id,
            squad_player_id=squad_player.id,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=datetime.now(),
            expected_recovery_date=datetime(2025, 12, 31),
            recovery_weeks=4,
            season=1,
            week=5
        )
        db_session.add(injury)
        await db_session.commit()

        # Try to create a new schedule with non-REHABILITATION focus
        with pytest.raises(ValueError, match="Cannot assign injured player"):
            await training_service.assign_training_focus(
                career_id=career.id,
                squad_player_id=squad_player.id,
                training_focus=TrainingFocus.ATTACKING,
                season=1,
                week=6  # New week, no existing schedule
            )


class TestRecoveryRestoresFocus:
    """Test that recovery restores previous training focus"""

    @pytest.mark.asyncio
    async def test_recovery_restores_previous_focus(self, db_session, test_data):
        """Test that clear_injured() restores the previous training focus"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create schedule with ATTACKING focus, then injure
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3
        )
        db_session.add(schedule)
        await db_session.commit()

        # Injure the player
        schedule.set_injured()
        await db_session.commit()

        assert schedule.training_focus == TrainingFocus.REHABILITATION
        assert schedule.previous_training_focus == "attacking"

        # Recover the player
        schedule.clear_injured()
        await db_session.commit()

        assert schedule.is_injured is False
        assert schedule.training_focus == TrainingFocus.ATTACKING
        assert schedule.previous_training_focus is None
        assert schedule.consecutive_weeks == 1

    @pytest.mark.asyncio
    async def test_recovery_defaults_to_general_if_no_previous(self, db_session, test_data):
        """Test that recovery defaults to GENERAL if no previous focus was saved"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create schedule already on REHABILITATION with no previous focus
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True,
            previous_training_focus=None
        )
        db_session.add(schedule)
        await db_session.commit()

        # Recover the player
        schedule.clear_injured()
        await db_session.commit()

        assert schedule.is_injured is False
        assert schedule.training_focus == TrainingFocus.GENERAL
        assert schedule.previous_training_focus is None

    @pytest.mark.asyncio
    async def test_recover_player_service_method(
        self, training_service, test_data, db_session
    ):
        """Test TrainingService.recover_player_from_injury() method"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create injured schedule with previous focus
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=2,
            is_injured=True,
            previous_training_focus="defending"
        )
        db_session.add(schedule)
        await db_session.commit()

        # Recover using service method
        result = await training_service.recover_player_from_injury(
            career_id=career.id,
            squad_player_id=squad_player.id,
            season=1,
            week=5
        )

        assert result is not None
        assert result.is_injured is False
        assert result.training_focus == TrainingFocus.DEFENDING
        assert result.previous_training_focus is None
        assert result.consecutive_weeks == 1

    @pytest.mark.asyncio
    async def test_recovery_with_various_previous_focuses(self, db_session, test_data):
        """Test recovery restores various training focus types correctly"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        focus_types = [
            TrainingFocus.FITNESS,
            TrainingFocus.TACTICS,
            TrainingFocus.DEFENDING,
            TrainingFocus.SET_PIECES,
            TrainingFocus.INDIVIDUAL_TECHNICAL,
            TrainingFocus.INDIVIDUAL_MENTAL,
        ]

        for i, focus in enumerate(focus_types):
            schedule = TrainingSchedule(
                career_id=career.id,
                player_id=player.id,
                squad_player_id=squad_player.id,
                training_focus=focus,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=10 + i,
                consecutive_weeks=2
            )
            db_session.add(schedule)
            await db_session.flush()

            # Injure and recover
            schedule.set_injured()
            assert schedule.training_focus == TrainingFocus.REHABILITATION
            assert schedule.previous_training_focus == focus.value

            schedule.clear_injured()
            assert schedule.training_focus == focus
            assert schedule.previous_training_focus is None


class TestRehabilitationNoImprovements:
    """Test that REHABILITATION provides no attribute improvements"""

    @pytest.mark.asyncio
    async def test_rehabilitation_has_no_affected_attributes(self, db_session, test_data):
        """Test that REHABILITATION training focus returns empty affected attributes"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True
        )
        db_session.add(schedule)
        await db_session.commit()

        # REHABILITATION should return empty list
        affected = schedule.get_affected_attributes()
        assert affected == []

    @pytest.mark.asyncio
    async def test_injured_player_skipped_in_training_simulation(
        self, training_service, test_data, db_session
    ):
        """Test that injured players on rehabilitation are skipped during training"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Create injured schedule
        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=4,
            is_injured=True
        )
        db_session.add(schedule)
        await db_session.commit()

        # Record initial attributes
        initial_stamina = player.stamina
        initial_pace = player.pace
        initial_finishing = player.finishing

        # Simulate training
        result = await training_service.simulate_weekly_training(
            career_id=career.id,
            season=1,
            week=5,
            training_intensity=TrainingIntensity.NORMAL,
            auto_fetch_coach_bonuses=False
        )

        # Refresh player data
        await db_session.refresh(player)

        # Player should be trained (counted) but no improvements
        assert result["players_trained"] == 1
        assert len(result["improvements"]) == 0
        assert player.stamina == initial_stamina
        assert player.pace == initial_pace
        assert player.finishing == initial_finishing


class TestRehabilitationIntegration:
    """Integration tests for the full rehabilitation workflow"""

    @pytest.mark.asyncio
    async def test_full_injury_recovery_workflow(
        self, training_service, test_data, db_session
    ):
        """Test the complete workflow: training -> injury -> rehab -> recovery -> restored focus"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        # Step 1: Player is training ATTACKING
        schedule = await training_service.assign_training_focus(
            career_id=career.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            season=1,
            week=5
        )
        assert schedule.training_focus == TrainingFocus.ATTACKING

        # Step 2: Player gets injured
        await training_service.set_player_injured(
            career_id=career.id,
            squad_player_id=squad_player.id,
            season=1,
            week=5
        )
        await db_session.refresh(schedule)
        assert schedule.is_injured is True
        assert schedule.training_focus == TrainingFocus.REHABILITATION
        assert schedule.previous_training_focus == "attacking"

        # Step 3: Try to change training while injured - should fail
        with pytest.raises(ValueError, match="Cannot assign injured player"):
            await training_service.assign_training_focus(
                career_id=career.id,
                squad_player_id=squad_player.id,
                training_focus=TrainingFocus.FITNESS,
                season=1,
                week=5
            )

        # Step 4: Player recovers
        result = await training_service.recover_player_from_injury(
            career_id=career.id,
            squad_player_id=squad_player.id,
            season=1,
            week=5
        )
        assert result.is_injured is False
        assert result.training_focus == TrainingFocus.ATTACKING
        assert result.previous_training_focus is None

        # Step 5: Player can now be assigned to other training
        new_schedule = await training_service.assign_training_focus(
            career_id=career.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            season=1,
            week=5
        )
        assert new_schedule.training_focus == TrainingFocus.FITNESS

    @pytest.mark.asyncio
    async def test_to_dict_includes_previous_focus(self, db_session, test_data):
        """Test that to_dict() includes previous_training_focus field"""
        career = test_data["career"]
        player = test_data["player"]
        squad_player = test_data["squad_player"]

        schedule = TrainingSchedule(
            career_id=career.id,
            player_id=player.id,
            squad_player_id=squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=1,
            is_injured=True,
            previous_training_focus="attacking"
        )
        db_session.add(schedule)
        await db_session.commit()

        result = schedule.to_dict()
        assert "previous_training_focus" in result
        assert result["previous_training_focus"] == "attacking"
        assert result["is_injured"] is True
        assert result["training_focus"] == "rehabilitation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
