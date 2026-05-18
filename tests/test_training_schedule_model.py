"""
Unit Tests for TrainingSchedule Model
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.player import Player
from app.models.career import Career
from app.models.user import User
from app.models.club import Club
from app.models.squad_player import SquadPlayer, SquadStatus


class TestTrainingScheduleModel:
    """Test suite for TrainingSchedule model"""
    
    @pytest.fixture
    async def test_user(self, test_db_session):
        """Create a test user"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            language_code="en"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def test_club(self, test_db_session):
        """Create a test club"""
        club = Club(
            name="Test FC",
            country="England",
            league="Premier League",
            reputation=75,
            balance=50000000,
            transfer_budget=20000000,
            wage_budget=500000
        )
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        return club
    
    @pytest.fixture
    async def test_career(self, test_db_session, test_user, test_club):
        """Create a test career"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        return career
    
    @pytest.fixture
    async def test_player(self, test_db_session):
        """Create a test player"""
        player = Player(
            uid="test_training_player_001",
            name="Test Training Player",
            position="CM",
            age=22,
            ca=140,
            pa=180,
            nationality="England",
            club="Test FC",
            corners=10, crossing=10, dribbling=14, finishing=12,
            first_touch=15, free_kicks=10, heading=10, long_shots=12,
            long_throws=8, marking=12, passing=16, penalty=10,
            tackling=13, technique=15,
            aggression=10, anticipation=14, bravery=12, composure=14,
            concentration=15, decisions=15, determination=16, flair=12,
            leadership=10, off_the_ball=13, positioning=14, teamwork=15,
            vision=15, work_rate=16,
            acceleration=14, agility=15, balance=14, jumping=12,
            stamina=16, pace=14, endurance=15, strength=13,
            price="£25,000,000", wage=45000,
            height=180, weight=75, left_foot=15, right_foot=12
        )
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        return player
    
    @pytest.fixture
    async def test_squad_player(self, test_db_session, test_career, test_player):
        """Create a test squad player"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 3)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=45000,
            squad_status=SquadStatus.FIRST_TEAM,
            squad_number=8,
            morale=75
        )
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        return squad_player
    
    @pytest.mark.asyncio
    async def test_create_training_schedule_with_all_attributes(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test creating a training schedule with all required attributes"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=5,
            consecutive_weeks=3,
            attribute_improvements='{"passing": 1, "finishing": 1}',
            is_injured=False
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        await test_db_session.refresh(training_schedule)
        
        assert training_schedule.id is not None
        assert training_schedule.career_id == test_career.id
        assert training_schedule.player_id == test_player.id
        assert training_schedule.squad_player_id == test_squad_player.id
        assert training_schedule.training_focus == TrainingFocus.ATTACKING
        assert training_schedule.training_intensity == TrainingIntensity.NORMAL
        assert training_schedule.season == 1
        assert training_schedule.week == 5
        assert training_schedule.consecutive_weeks == 3
        assert training_schedule.is_injured is False
    
    @pytest.mark.asyncio
    async def test_training_schedule_unique_constraint(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that only one training schedule per player per week per season per career"""
        training_schedule1 = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule1)
        await test_db_session.commit()
        
        # Try to add another training schedule for the same player, season, and week
        training_schedule2 = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.TACTICS,
            training_intensity=TrainingIntensity.HEAVY,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_week_range_constraint(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that week must be between 1 and 52"""
        # Test week too high
        training_schedule_high = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=53  # Invalid: > 52
        )
        
        test_db_session.add(training_schedule_high)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
        
        # Test week too low
        training_schedule_low = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=0  # Invalid: < 1
        )
        
        test_db_session.add(training_schedule_low)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_season_positive_constraint(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that season must be positive"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=0,  # Invalid: must be >= 1
            week=1
        )
        
        test_db_session.add(training_schedule)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_consecutive_weeks_positive_constraint(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that consecutive_weeks must be positive"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=1,
            consecutive_weeks=0  # Invalid: must be >= 1
        )
        
        test_db_session.add(training_schedule)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_training_schedule_to_dict(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test converting training schedule to dictionary"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.DEFENDING,
            training_intensity=TrainingIntensity.HEAVY,
            season=2,
            week=15,
            consecutive_weeks=5,
            attribute_improvements='{"tackling": 2, "marking": 1}',
            is_injured=False
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        await test_db_session.refresh(training_schedule)
        
        schedule_dict = training_schedule.to_dict()
        
        assert schedule_dict["career_id"] == test_career.id
        assert schedule_dict["player_id"] == test_player.id
        assert schedule_dict["squad_player_id"] == test_squad_player.id
        assert schedule_dict["training_focus"] == "defending"
        assert schedule_dict["training_intensity"] == "heavy"
        assert schedule_dict["season"] == 2
        assert schedule_dict["week"] == 15
        assert schedule_dict["consecutive_weeks"] == 5
        assert schedule_dict["is_injured"] is False
    
    @pytest.mark.asyncio
    async def test_is_rehabilitation(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test checking if training focus is rehabilitation"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10,
            is_injured=True
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        assert training_schedule.is_rehabilitation() is True
        
        training_schedule.training_focus = TrainingFocus.FITNESS
        assert training_schedule.is_rehabilitation() is False
    
    @pytest.mark.asyncio
    async def test_is_fitness_training(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test checking if training focus is fitness"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        assert training_schedule.is_fitness_training() is True
        
        training_schedule.training_focus = TrainingFocus.TACTICS
        assert training_schedule.is_fitness_training() is False
    
    @pytest.mark.asyncio
    async def test_intensity_checks(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test training intensity check methods"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        assert training_schedule.is_light_intensity() is True
        assert training_schedule.is_heavy_intensity() is False
        
        training_schedule.training_intensity = TrainingIntensity.HEAVY
        assert training_schedule.is_light_intensity() is False
        assert training_schedule.is_heavy_intensity() is True
    
    @pytest.mark.asyncio
    async def test_is_ready_for_improvement(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test checking if player is ready for attribute improvement"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10,
            consecutive_weeks=4
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        # Young player (under 24) with 4 consecutive weeks
        assert training_schedule.is_ready_for_improvement(22) is True
        
        # Young player with less than 4 consecutive weeks
        training_schedule.consecutive_weeks = 3
        assert training_schedule.is_ready_for_improvement(22) is False
        
        # Older player (24+) with 4 consecutive weeks
        training_schedule.consecutive_weeks = 4
        assert training_schedule.is_ready_for_improvement(25) is False
    
    @pytest.mark.asyncio
    async def test_should_decline_attributes(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test checking if player should have attributes decline"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.TACTICS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10,
            consecutive_weeks=8
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        # Old player (over 30) not on fitness training for 8 weeks
        assert training_schedule.should_decline_attributes(31) is True
        
        # Old player on fitness training
        training_schedule.training_focus = TrainingFocus.FITNESS
        assert training_schedule.should_decline_attributes(31) is False
        
        # Old player not on fitness but less than 8 weeks
        training_schedule.training_focus = TrainingFocus.TACTICS
        training_schedule.consecutive_weeks = 7
        assert training_schedule.should_decline_attributes(31) is False
        
        # Young player
        training_schedule.consecutive_weeks = 8
        assert training_schedule.should_decline_attributes(28) is False
    
    @pytest.mark.asyncio
    async def test_get_injury_risk_multiplier(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test calculating injury risk multiplier based on intensity"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        # Light intensity: 0.7 multiplier
        assert training_schedule.get_injury_risk_multiplier() == 0.7
        
        # Normal intensity: 1.0 multiplier
        training_schedule.training_intensity = TrainingIntensity.NORMAL
        assert training_schedule.get_injury_risk_multiplier() == 1.0
        
        # Heavy intensity: 1.5 multiplier
        training_schedule.training_intensity = TrainingIntensity.HEAVY
        assert training_schedule.get_injury_risk_multiplier() == 1.5
    
    @pytest.mark.asyncio
    async def test_get_development_rate_multiplier(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test calculating development rate multiplier based on intensity"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        # Light intensity: 0.8 multiplier
        assert training_schedule.get_development_rate_multiplier() == 0.8
        
        # Normal intensity: 1.0 multiplier
        training_schedule.training_intensity = TrainingIntensity.NORMAL
        assert training_schedule.get_development_rate_multiplier() == 1.0
        
        # Heavy intensity: 1.2 multiplier
        training_schedule.training_intensity = TrainingIntensity.HEAVY
        assert training_schedule.get_development_rate_multiplier() == 1.2
    
    @pytest.mark.asyncio
    async def test_increment_consecutive_weeks(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test incrementing consecutive weeks counter"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10,
            consecutive_weeks=3
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        training_schedule.increment_consecutive_weeks()
        assert training_schedule.consecutive_weeks == 4
        
        training_schedule.increment_consecutive_weeks()
        assert training_schedule.consecutive_weeks == 5
    
    @pytest.mark.asyncio
    async def test_reset_consecutive_weeks(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test resetting consecutive weeks counter"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10,
            consecutive_weeks=5
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        training_schedule.reset_consecutive_weeks()
        assert training_schedule.consecutive_weeks == 1
    
    @pytest.mark.asyncio
    async def test_set_injured(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test marking player as injured and auto-assigning to rehabilitation"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.ATTACKING,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10,
            consecutive_weeks=3,
            is_injured=False
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        training_schedule.set_injured()
        
        assert training_schedule.is_injured is True
        assert training_schedule.training_focus == TrainingFocus.REHABILITATION
        assert training_schedule.consecutive_weeks == 1
    
    @pytest.mark.asyncio
    async def test_clear_injured(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test clearing injured flag when player recovers"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10,
            is_injured=True
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        training_schedule.clear_injured()
        
        assert training_schedule.is_injured is False
    
    @pytest.mark.asyncio
    async def test_get_affected_attributes(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test getting list of attributes affected by training focus"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=10
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        
        # Fitness training affects physical attributes
        fitness_attrs = training_schedule.get_affected_attributes()
        assert "stamina" in fitness_attrs
        assert "pace" in fitness_attrs
        assert "endurance" in fitness_attrs
        assert "strength" in fitness_attrs
        
        # Attacking training affects attacking attributes
        training_schedule.training_focus = TrainingFocus.ATTACKING
        attacking_attrs = training_schedule.get_affected_attributes()
        assert "finishing" in attacking_attrs
        assert "dribbling" in attacking_attrs
        assert "passing" in attacking_attrs
        
        # Defending training affects defensive attributes
        training_schedule.training_focus = TrainingFocus.DEFENDING
        defending_attrs = training_schedule.get_affected_attributes()
        assert "tackling" in defending_attrs
        assert "marking" in defending_attrs
        assert "heading" in defending_attrs
        
        # Rehabilitation has no attribute improvements
        training_schedule.training_focus = TrainingFocus.REHABILITATION
        rehab_attrs = training_schedule.get_affected_attributes()
        assert len(rehab_attrs) == 0
    
    @pytest.mark.asyncio
    async def test_training_schedule_repr(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test training schedule string representation"""
        training_schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=test_player.id,
            squad_player_id=test_squad_player.id,
            training_focus=TrainingFocus.TACTICS,
            training_intensity=TrainingIntensity.NORMAL,
            season=2,
            week=20,
            consecutive_weeks=4
        )
        
        test_db_session.add(training_schedule)
        await test_db_session.commit()
        await test_db_session.refresh(training_schedule)
        
        repr_str = repr(training_schedule)
        
        assert "TrainingSchedule" in repr_str
        assert str(test_player.id) in repr_str
        assert "tactics" in repr_str
        assert "2" in repr_str  # season
        assert "20" in repr_str  # week
        assert "4" in repr_str  # consecutive_weeks
    
    @pytest.mark.asyncio
    async def test_all_training_focus_options(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that all training focus options can be created"""
        focus_options = [
            TrainingFocus.GENERAL,
            TrainingFocus.FITNESS,
            TrainingFocus.TACTICS,
            TrainingFocus.ATTACKING,
            TrainingFocus.DEFENDING,
            TrainingFocus.SET_PIECES,
            TrainingFocus.INDIVIDUAL_TECHNICAL,
            TrainingFocus.INDIVIDUAL_MENTAL,
            TrainingFocus.REHABILITATION
        ]
        
        for week, focus in enumerate(focus_options, start=1):
            training_schedule = TrainingSchedule(
                career_id=test_career.id,
                player_id=test_player.id,
                squad_player_id=test_squad_player.id,
                training_focus=focus,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=week
            )
            
            test_db_session.add(training_schedule)
        
        await test_db_session.commit()
        
        # Verify all were created
        result = await test_db_session.execute(
            "SELECT COUNT(*) FROM training_schedules WHERE career_id = :career_id",
            {"career_id": test_career.id}
        )
        count = result.scalar()
        assert count == len(focus_options)
    
    @pytest.mark.asyncio
    async def test_all_training_intensity_options(
        self, test_db_session, test_career, test_player, test_squad_player
    ):
        """Test that all training intensity options can be created"""
        intensity_options = [
            TrainingIntensity.LIGHT,
            TrainingIntensity.NORMAL,
            TrainingIntensity.HEAVY
        ]
        
        for week, intensity in enumerate(intensity_options, start=1):
            training_schedule = TrainingSchedule(
                career_id=test_career.id,
                player_id=test_player.id,
                squad_player_id=test_squad_player.id,
                training_focus=TrainingFocus.GENERAL,
                training_intensity=intensity,
                season=1,
                week=week
            )
            
            test_db_session.add(training_schedule)
        
        await test_db_session.commit()
        
        # Verify all were created
        result = await test_db_session.execute(
            "SELECT COUNT(*) FROM training_schedules WHERE career_id = :career_id",
            {"career_id": test_career.id}
        )
        count = result.scalar()
        assert count == len(intensity_options)
