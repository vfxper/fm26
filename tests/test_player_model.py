"""
Unit Tests for Player Model
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.player import Player


class TestPlayerModel:
    """Test suite for Player model"""
    
    @pytest.mark.asyncio
    async def test_create_player_with_all_attributes(self, test_db_session):
        """Test creating a player with all required attributes"""
        player = Player(
            uid="test_player_001",
            name="Test Player",
            position="ST",
            age=25,
            ca=150,
            pa=180,
            nationality="England",
            club="Test FC",
            # Technical attributes
            corners=15,
            crossing=14,
            dribbling=16,
            finishing=18,
            first_touch=17,
            free_kicks=12,
            heading=13,
            long_shots=15,
            long_throws=10,
            marking=8,
            passing=14,
            penalty=16,
            tackling=7,
            technique=16,
            # Mental attributes
            aggression=12,
            anticipation=16,
            bravery=14,
            composure=17,
            concentration=15,
            decisions=16,
            determination=18,
            flair=15,
            leadership=12,
            off_the_ball=17,
            positioning=16,
            teamwork=14,
            vision=15,
            work_rate=16,
            # Physical attributes
            acceleration=18,
            agility=17,
            balance=16,
            jumping=14,
            stamina=16,
            pace=19,
            endurance=15,
            strength=14,
            # Financial
            price="£50,000,000",
            wage=75000,
            # Physical stats
            height=185,
            weight=78,
            left_foot=8,
            right_foot=18,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        
        assert player.id is not None
        assert player.uid == "test_player_001"
        assert player.name == "Test Player"
        assert player.position == "ST"
        assert player.ca == 150
        assert player.pa == 180
        assert player.finishing == 18
        assert player.pace == 19
    
    @pytest.mark.asyncio
    async def test_player_uid_unique_constraint(self, test_db_session):
        """Test that uid must be unique"""
        player1 = Player(
            uid="duplicate_uid",
            name="Player One",
            position="CM",
            age=24,
            ca=140,
            pa=160,
            nationality="Spain",
            club="Club A",
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
            price="£10,000,000", wage=30000,
            height=180, weight=75, left_foot=10, right_foot=10,
        )
        
        player2 = Player(
            uid="duplicate_uid",  # Same UID
            name="Player Two",
            position="CB",
            age=26,
            ca=130,
            pa=150,
            nationality="France",
            club="Club B",
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
            price="£8,000,000", wage=25000,
            height=188, weight=82, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player1)
        await test_db_session.commit()
        
        test_db_session.add(player2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_player_ca_check_constraint(self, test_db_session):
        """Test that CA must be between 1 and 200"""
        # Test CA too high
        player_high = Player(
            uid="test_ca_high",
            name="High CA Player",
            position="GK",
            age=30,
            ca=201,  # Invalid: > 200
            pa=200,
            nationality="Germany",
            club="Test Club",
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
            price="£5,000,000", wage=20000,
            height=190, weight=85, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player_high)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
        
        # Test CA too low
        player_low = Player(
            uid="test_ca_low",
            name="Low CA Player",
            position="GK",
            age=30,
            ca=0,  # Invalid: < 1
            pa=100,
            nationality="Germany",
            club="Test Club",
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
            price="£5,000,000", wage=20000,
            height=190, weight=85, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player_low)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_player_attribute_check_constraints(self, test_db_session):
        """Test that individual attributes must be between 1 and 20"""
        # Test technical attribute out of range
        player = Player(
            uid="test_attr_range",
            name="Attribute Test Player",
            position="CM",
            age=25,
            ca=150,
            pa=170,
            nationality="Brazil",
            club="Test Club",
            corners=10, crossing=10, dribbling=25,  # Invalid: > 20
            finishing=10, first_touch=10, free_kicks=10, heading=10,
            long_shots=10, long_throws=10, marking=10, passing=10,
            penalty=10, tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            price="£20,000,000", wage=40000,
            height=175, weight=70, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_player_to_dict(self, test_db_session):
        """Test converting player to dictionary"""
        player = Player(
            uid="test_to_dict",
            name="Dict Test Player",
            position="AM/ST RL",
            age=22,
            ca=160,
            pa=190,
            nationality="Argentina",
            club="Test FC",
            corners=12, crossing=13, dribbling=18, finishing=17,
            first_touch=16, free_kicks=14, heading=10, long_shots=16,
            long_throws=8, marking=6, passing=15, penalty=15,
            tackling=5, technique=17,
            aggression=10, anticipation=15, bravery=12, composure=16,
            concentration=14, decisions=15, determination=17, flair=18,
            leadership=10, off_the_ball=16, positioning=14, teamwork=13,
            vision=16, work_rate=15,
            acceleration=19, agility=18, balance=17, jumping=12,
            stamina=15, pace=19, endurance=14, strength=11,
            price="£80,000,000", wage=100000,
            height=175, weight=72, left_foot=18, right_foot=10,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        
        player_dict = player.to_dict()
        
        assert player_dict["uid"] == "test_to_dict"
        assert player_dict["name"] == "Dict Test Player"
        assert player_dict["position"] == "AM/ST RL"
        assert player_dict["ca"] == 160
        assert player_dict["pa"] == 190
        
        # Check nested dictionaries
        assert "technical" in player_dict
        assert player_dict["technical"]["dribbling"] == 18
        assert player_dict["technical"]["finishing"] == 17
        
        assert "mental" in player_dict
        assert player_dict["mental"]["flair"] == 18
        assert player_dict["mental"]["determination"] == 17
        
        assert "physical" in player_dict
        assert player_dict["physical"]["pace"] == 19
        assert player_dict["physical"]["acceleration"] == 19
        
        assert "financial" in player_dict
        assert player_dict["financial"]["price"] == "£80,000,000"
        assert player_dict["financial"]["wage"] == 100000
        
        assert "physical_stats" in player_dict
        assert player_dict["physical_stats"]["height"] == 175
        assert player_dict["physical_stats"]["left_foot"] == 18
    
    @pytest.mark.asyncio
    async def test_player_repr(self, test_db_session):
        """Test player string representation"""
        player = Player(
            uid="test_repr",
            name="Repr Test Player",
            position="CB",
            age=28,
            ca=145,
            pa=155,
            nationality="Italy",
            club="Test United",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=15, long_shots=10,
            long_throws=10, marking=16, passing=12, penalty=10,
            tackling=17, technique=12,
            aggression=14, anticipation=16, bravery=17, composure=14,
            concentration=15, decisions=15, determination=16, flair=10,
            leadership=14, off_the_ball=10, positioning=16, teamwork=15,
            vision=12, work_rate=15,
            acceleration=12, agility=13, balance=14, jumping=16,
            stamina=15, pace=13, endurance=15, strength=17,
            price="£25,000,000", wage=50000,
            height=188, weight=84, left_foot=10, right_foot=12,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        
        repr_str = repr(player)
        
        assert "Player" in repr_str
        assert "test_repr" in repr_str
        assert "Repr Test Player" in repr_str
        assert "CB" in repr_str
        assert "145" in repr_str
        assert "155" in repr_str
        assert "Test United" in repr_str
    
    @pytest.mark.asyncio
    async def test_get_technical_average(self, test_db_session):
        """Test calculating technical attribute average"""
        player = Player(
            uid="test_tech_avg",
            name="Tech Average Player",
            position="CM",
            age=26,
            ca=150,
            pa=160,
            nationality="Spain",
            club="Test FC",
            # All technical attributes set to 10 for easy calculation
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
            price="£15,000,000", wage=35000,
            height=180, weight=75, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        
        tech_avg = player.get_technical_average()
        assert tech_avg == 10.0
    
    @pytest.mark.asyncio
    async def test_get_mental_average(self, test_db_session):
        """Test calculating mental attribute average"""
        player = Player(
            uid="test_mental_avg",
            name="Mental Average Player",
            position="CM",
            age=26,
            ca=150,
            pa=160,
            nationality="Germany",
            club="Test FC",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            # All mental attributes set to 15
            aggression=15, anticipation=15, bravery=15, composure=15,
            concentration=15, decisions=15, determination=15, flair=15,
            leadership=15, off_the_ball=15, positioning=15, teamwork=15,
            vision=15, work_rate=15,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
            price="£20,000,000", wage=40000,
            height=182, weight=77, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        
        mental_avg = player.get_mental_average()
        assert mental_avg == 15.0
    
    @pytest.mark.asyncio
    async def test_get_physical_average(self, test_db_session):
        """Test calculating physical attribute average"""
        player = Player(
            uid="test_physical_avg",
            name="Physical Average Player",
            position="ST",
            age=24,
            ca=155,
            pa=175,
            nationality="France",
            club="Test FC",
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            # All physical attributes set to 18
            acceleration=18, agility=18, balance=18, jumping=18,
            stamina=18, pace=18, endurance=18, strength=18,
            price="£40,000,000", wage=60000,
            height=183, weight=79, left_foot=10, right_foot=18,
        )
        
        test_db_session.add(player)
        await test_db_session.commit()
        
        physical_avg = player.get_physical_average()
        assert physical_avg == 18.0
    
    @pytest.mark.asyncio
    async def test_query_players_by_position(self, test_db_session):
        """Test querying players by position"""
        # Create multiple players with different positions
        striker = Player(
            uid="striker_001",
            name="Striker Player",
            position="ST",
            age=25,
            ca=160,
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
            height=183, weight=78, left_foot=10, right_foot=18,
        )
        
        midfielder = Player(
            uid="midfielder_001",
            name="Midfielder Player",
            position="CM",
            age=26,
            ca=155,
            pa=170,
            nationality="Spain",
            club="Test FC",
            corners=12, crossing=13, dribbling=14, finishing=12,
            first_touch=16, free_kicks=13, heading=10, long_shots=14,
            long_throws=8, marking=12, passing=17, penalty=12,
            tackling=13, technique=16,
            aggression=11, anticipation=15, bravery=13, composure=16,
            concentration=16, decisions=16, determination=15, flair=14,
            leadership=14, off_the_ball=13, positioning=14, teamwork=17,
            vision=17, work_rate=16,
            acceleration=14, agility=15, balance=16, jumping=11,
            stamina=16, pace=14, endurance=16, strength=12,
            price="£35,000,000", wage=55000,
            height=178, weight=73, left_foot=15, right_foot=15,
        )
        
        test_db_session.add(striker)
        test_db_session.add(midfielder)
        await test_db_session.commit()
        
        # Query strikers
        result = await test_db_session.execute(
            select(Player).where(Player.position == "ST")
        )
        strikers = result.scalars().all()
        
        assert len(strikers) == 1
        assert strikers[0].name == "Striker Player"
        assert strikers[0].position == "ST"
    
    @pytest.mark.asyncio
    async def test_query_players_by_ca_range(self, test_db_session):
        """Test querying players by CA range"""
        # Create players with different CA values
        high_ca_player = Player(
            uid="high_ca_001",
            name="High CA Player",
            position="ST",
            age=28,
            ca=180,
            pa=185,
            nationality="Portugal",
            club="Elite FC",
            corners=10, crossing=10, dribbling=17, finishing=19,
            first_touch=18, free_kicks=12, heading=15, long_shots=17,
            long_throws=8, marking=7, passing=15, penalty=18,
            tackling=6, technique=18,
            aggression=11, anticipation=18, bravery=15, composure=18,
            concentration=17, decisions=17, determination=18, flair=17,
            leadership=15, off_the_ball=19, positioning=18, teamwork=14,
            vision=16, work_rate=15,
            acceleration=18, agility=17, balance=17, jumping=15,
            stamina=16, pace=19, endurance=15, strength=14,
            price="£100,000,000", wage=150000,
            height=185, weight=80, left_foot=12, right_foot=19,
        )
        
        low_ca_player = Player(
            uid="low_ca_001",
            name="Low CA Player",
            position="CM",
            age=20,
            ca=100,
            pa=150,
            nationality="England",
            club="Youth FC",
            corners=8, crossing=8, dribbling=10, finishing=8,
            first_touch=10, free_kicks=7, heading=8, long_shots=8,
            long_throws=6, marking=9, passing=11, penalty=8,
            tackling=9, technique=10,
            aggression=9, anticipation=10, bravery=10, composure=9,
            concentration=10, decisions=10, determination=12, flair=9,
            leadership=7, off_the_ball=9, positioning=10, teamwork=11,
            vision=10, work_rate=12,
            acceleration=12, agility=11, balance=11, jumping=9,
            stamina=12, pace=12, endurance=11, strength=9,
            price="£2,000,000", wage=10000,
            height=175, weight=70, left_foot=10, right_foot=10,
        )
        
        test_db_session.add(high_ca_player)
        test_db_session.add(low_ca_player)
        await test_db_session.commit()
        
        # Query players with CA >= 150
        result = await test_db_session.execute(
            select(Player).where(Player.ca >= 150)
        )
        high_ca_players = result.scalars().all()
        
        assert len(high_ca_players) == 1
        assert high_ca_players[0].name == "High CA Player"
        assert high_ca_players[0].ca == 180
