"""
Unit Tests for SquadPlayer Model
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.squad_player import SquadPlayer, SquadStatus
from app.models.player import Player
from app.models.career import Career
from app.models.user import User
from app.models.club import Club


class TestSquadPlayerModel:
    """Test suite for SquadPlayer model"""
    
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
            uid="test_squad_player_001",
            name="Test Squad Player",
            position="ST",
            age=25,
            ca=150,
            pa=180,
            nationality="England",
            club="Test FC",
            corners=10, crossing=10, dribbling=15, finishing=18,
            first_touch=15, free_kicks=10, heading=14, long_shots=15,
            long_throws=8, marking=6, passing=12, penalty=16,
            tackling=5, technique=14,
            aggression=10, anticipation=16, bravery=14, composure=16,
            concentration=14, decisions=15, determination=16, flair=14,
            leadership=12, off_the_ball=17, positioning=16, teamwork=13,
            vision=13, work_rate=14,
            acceleration=17, agility=16, balance=15, jumping=14,
            stamina=15, pace=18, endurance=14, strength=13,
            price="£45,000,000", wage=70000,
            height=183, weight=78, left_foot=10, right_foot=18
        )
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        return player
    
    @pytest.mark.asyncio
    async def test_create_squad_player_with_all_attributes(
        self, test_db_session, test_career, test_player
    ):
        """Test creating a squad player with all required attributes"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 3)  # 3 year contract
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=75000,
            release_clause=50000000,
            contract_months_remaining=36,
            squad_status=SquadStatus.KEY_PLAYER,
            squad_number=9,
            morale=85,
            appearances=25,
            goals=15,
            assists=8,
            minutes_played=2100,
            yellow_cards=3,
            red_cards=0,
            joined_date=today
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        
        assert squad_player.id is not None
        assert squad_player.career_id == test_career.id
        assert squad_player.player_id == test_player.id
        assert squad_player.wage == 75000
        assert squad_player.release_clause == 50000000
        assert squad_player.squad_status == SquadStatus.KEY_PLAYER
        assert squad_player.squad_number == 9
        assert squad_player.morale == 85
        assert squad_player.appearances == 25
        assert squad_player.goals == 15
    
    @pytest.mark.asyncio
    async def test_squad_player_unique_career_player_constraint(
        self, test_db_session, test_career, test_player
    ):
        """Test that a player can only be in a career's squad once"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player1 = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70
        )
        
        test_db_session.add(squad_player1)
        await test_db_session.commit()
        
        # Try to add the same player to the same career again
        squad_player2 = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=60000,
            squad_number=11,
            morale=75
        )
        
        test_db_session.add(squad_player2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_squad_number_unique_per_career(
        self, test_db_session, test_career
    ):
        """Test that squad numbers must be unique within a career"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        # Create two different players
        player1 = Player(
            uid="squad_num_test_1",
            name="Player One",
            position="ST",
            age=25,
            ca=150,
            pa=170,
            nationality="England",
            club="Test FC",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            price="£10M", wage=30000,
            height=180, weight=75, left_foot=10, right_foot=10
        )
        
        player2 = Player(
            uid="squad_num_test_2",
            name="Player Two",
            position="CM",
            age=26,
            ca=140,
            pa=160,
            nationality="Spain",
            club="Test FC",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            price="£8M", wage=25000,
            height=178, weight=73, left_foot=10, right_foot=10
        )
        
        test_db_session.add(player1)
        test_db_session.add(player2)
        await test_db_session.commit()
        await test_db_session.refresh(player1)
        await test_db_session.refresh(player2)
        
        # Add first player with squad number 10
        squad_player1 = SquadPlayer(
            career_id=test_career.id,
            player_id=player1.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70
        )
        
        test_db_session.add(squad_player1)
        await test_db_session.commit()
        
        # Try to add second player with same squad number
        squad_player2 = SquadPlayer(
            career_id=test_career.id,
            player_id=player2.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=45000,
            squad_number=10,  # Same squad number
            morale=75
        )
        
        test_db_session.add(squad_player2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_squad_number_range_constraint(
        self, test_db_session, test_career, test_player
    ):
        """Test that squad number must be between 1 and 99"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        # Test squad number too high
        squad_player_high = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=100,  # Invalid: > 99
            morale=70
        )
        
        test_db_session.add(squad_player_high)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
        
        # Test squad number too low
        squad_player_low = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=0,  # Invalid: < 1
            morale=70
        )
        
        test_db_session.add(squad_player_low)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_morale_range_constraint(
        self, test_db_session, test_career, test_player
    ):
        """Test that morale must be between 1 and 100"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        # Test morale too high
        squad_player_high = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=101  # Invalid: > 100
        )
        
        test_db_session.add(squad_player_high)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
        
        # Test morale too low
        squad_player_low = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=0  # Invalid: < 1
        )
        
        test_db_session.add(squad_player_low)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_contract_dates_constraint(
        self, test_db_session, test_career, test_player
    ):
        """Test that contract end date must be after start date"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=yesterday,  # Invalid: before start date
            wage=50000,
            squad_number=10,
            morale=70
        )
        
        test_db_session.add(squad_player)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_squad_player_to_dict(
        self, test_db_session, test_career, test_player
    ):
        """Test converting squad player to dictionary"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 3)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=75000,
            release_clause=50000000,
            contract_months_remaining=36,
            squad_status=SquadStatus.KEY_PLAYER,
            squad_number=9,
            morale=85,
            appearances=25,
            goals=15,
            assists=8,
            minutes_played=2100,
            yellow_cards=3,
            red_cards=0,
            joined_date=today
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        
        squad_dict = squad_player.to_dict()
        
        assert squad_dict["career_id"] == test_career.id
        assert squad_dict["player_id"] == test_player.id
        
        # Check contract information
        assert "contract" in squad_dict
        assert squad_dict["contract"]["wage"] == 75000
        assert squad_dict["contract"]["release_clause"] == 50000000
        assert squad_dict["contract"]["months_remaining"] == 36
        
        # Check squad management
        assert "squad" in squad_dict
        assert squad_dict["squad"]["status"] == "KEY_PLAYER"
        assert squad_dict["squad"]["number"] == 9
        assert squad_dict["squad"]["morale"] == 85
        
        # Check statistics
        assert "statistics" in squad_dict
        assert squad_dict["statistics"]["appearances"] == 25
        assert squad_dict["statistics"]["goals"] == 15
        assert squad_dict["statistics"]["assists"] == 8
    
    @pytest.mark.asyncio
    async def test_is_contract_expiring_soon(
        self, test_db_session, test_career, test_player
    ):
        """Test checking if contract is expiring soon"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70,
            contract_months_remaining=5  # Less than 6 months
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.is_contract_expiring_soon() is True
        
        # Update to more than 6 months
        squad_player.contract_months_remaining = 12
        assert squad_player.is_contract_expiring_soon() is False
    
    @pytest.mark.asyncio
    async def test_is_low_morale(
        self, test_db_session, test_career, test_player
    ):
        """Test checking if player has low morale"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=35  # Low morale
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.is_low_morale() is True
        
        squad_player.morale = 50
        assert squad_player.is_low_morale() is False
    
    @pytest.mark.asyncio
    async def test_is_very_low_morale(
        self, test_db_session, test_career, test_player
    ):
        """Test checking if player has very low morale"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=15  # Very low morale
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.is_very_low_morale() is True
        
        squad_player.morale = 25
        assert squad_player.is_very_low_morale() is False
    
    @pytest.mark.asyncio
    async def test_squad_status_checks(
        self, test_db_session, test_career, test_player
    ):
        """Test squad status check methods"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70,
            squad_status=SquadStatus.KEY_PLAYER
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.is_key_player() is True
        assert squad_player.is_not_needed() is False
        
        squad_player.squad_status = SquadStatus.NOT_NEEDED
        assert squad_player.is_key_player() is False
        assert squad_player.is_not_needed() is True
    
    @pytest.mark.asyncio
    async def test_get_goals_per_appearance(
        self, test_db_session, test_career, test_player
    ):
        """Test calculating goals per appearance"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70,
            appearances=20,
            goals=10
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.get_goals_per_appearance() == 0.5
        
        # Test with no appearances
        squad_player.appearances = 0
        assert squad_player.get_goals_per_appearance() == 0.0
    
    @pytest.mark.asyncio
    async def test_get_goal_contributions(
        self, test_db_session, test_career, test_player
    ):
        """Test calculating total goal contributions"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70,
            goals=15,
            assists=8
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        assert squad_player.get_goal_contributions() == 23
    
    @pytest.mark.asyncio
    async def test_update_morale(
        self, test_db_session, test_career, test_player
    ):
        """Test updating player morale"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=50
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        # Increase morale
        squad_player.update_morale(20)
        assert squad_player.morale == 70
        
        # Decrease morale
        squad_player.update_morale(-30)
        assert squad_player.morale == 40
        
        # Test upper bound
        squad_player.update_morale(100)
        assert squad_player.morale == 100
        
        # Test lower bound
        squad_player.update_morale(-200)
        assert squad_player.morale == 1
    
    @pytest.mark.asyncio
    async def test_record_appearance(
        self, test_db_session, test_career, test_player
    ):
        """Test recording a match appearance"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        # Record an appearance with goals and assists
        squad_player.record_appearance(
            minutes=90,
            goals=2,
            assists=1,
            yellow_card=True,
            red_card=False
        )
        
        assert squad_player.appearances == 1
        assert squad_player.minutes_played == 90
        assert squad_player.goals == 2
        assert squad_player.assists == 1
        assert squad_player.yellow_cards == 1
        assert squad_player.red_cards == 0
        
        # Record another appearance
        squad_player.record_appearance(
            minutes=85,
            goals=1,
            assists=0,
            yellow_card=False,
            red_card=False
        )
        
        assert squad_player.appearances == 2
        assert squad_player.minutes_played == 175
        assert squad_player.goals == 3
        assert squad_player.assists == 1
    
    @pytest.mark.asyncio
    async def test_calculate_contract_months_remaining(
        self, test_db_session, test_career, test_player
    ):
        """Test calculating contract months remaining"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)  # 2 years from now
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        
        # Calculate from today
        months = squad_player.calculate_contract_months_remaining(today)
        assert months == 24  # 2 years = 24 months
        assert squad_player.contract_months_remaining == 24
        
        # Calculate from 1 year in the future
        future_date = today + timedelta(days=365)
        months = squad_player.calculate_contract_months_remaining(future_date)
        assert months == 12  # 1 year remaining
        
        # Calculate from after contract end
        past_end = contract_end + timedelta(days=30)
        months = squad_player.calculate_contract_months_remaining(past_end)
        assert months == 0
    
    @pytest.mark.asyncio
    async def test_squad_player_repr(
        self, test_db_session, test_career, test_player
    ):
        """Test squad player string representation"""
        today = date.today()
        contract_end = today + timedelta(days=365 * 2)
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=test_player.id,
            contract_start_date=today,
            contract_end_date=contract_end,
            wage=50000,
            squad_number=10,
            morale=70,
            squad_status=SquadStatus.FIRST_TEAM
        )
        
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        
        repr_str = repr(squad_player)
        
        assert "SquadPlayer" in repr_str
        assert str(test_career.id) in repr_str
        assert str(test_player.id) in repr_str
        assert "10" in repr_str
        assert "FIRST_TEAM" in repr_str
