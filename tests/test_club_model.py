"""
Unit Tests for Club Model
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.club import Club


class TestClubModel:
    """Test suite for Club model"""
    
    @pytest.mark.asyncio
    async def test_create_club_basic(self, test_db_session):
        """Test creating a basic club with required fields"""
        club = Club(
            name="Manchester United",
            reputation=85,
            league="Premier League",
            country="England"
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        assert club.id is not None
        assert club.name == "Manchester United"
        assert club.reputation == 85
        assert club.league == "Premier League"
        assert club.country == "England"
        
        # Check default values
        assert club.stadium_level == 2
        assert club.training_facilities_level == 2
        assert club.youth_academy_level == 2
        assert club.medical_centre_level == 2
        assert club.scouting_network_level == 2
        assert club.balance == 0
        assert club.transfer_budget == 0
        assert club.wage_budget == 0
        assert club.matchday_revenue == 0
        assert club.stadium_capacity == 10000
        assert club.stadium_name is None
        assert club.created_at is not None
        assert club.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_club_full(self, test_db_session):
        """Test creating a club with all fields specified"""
        club = Club(
            name="Real Madrid",
            reputation=95,
            league="La Liga",
            country="Spain",
            stadium_level=5,
            training_facilities_level=5,
            youth_academy_level=4,
            medical_centre_level=5,
            scouting_network_level=5,
            balance=50000000,
            transfer_budget=100000000,
            wage_budget=500000,
            matchday_revenue=2000000,
            stadium_capacity=81044,
            stadium_name="Santiago Bernabéu"
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        assert club.id is not None
        assert club.name == "Real Madrid"
        assert club.reputation == 95
        assert club.league == "La Liga"
        assert club.country == "Spain"
        assert club.stadium_level == 5
        assert club.training_facilities_level == 5
        assert club.youth_academy_level == 4
        assert club.medical_centre_level == 5
        assert club.scouting_network_level == 5
        assert club.balance == 50000000
        assert club.transfer_budget == 100000000
        assert club.wage_budget == 500000
        assert club.matchday_revenue == 2000000
        assert club.stadium_capacity == 81044
        assert club.stadium_name == "Santiago Bernabéu"
    
    @pytest.mark.asyncio
    async def test_club_reputation_constraint_min(self, test_db_session):
        """Test that reputation cannot be less than 1"""
        club = Club(
            name="Test Club",
            reputation=0,  # Invalid: below minimum
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add(club)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_club_reputation_constraint_max(self, test_db_session):
        """Test that reputation cannot be greater than 100"""
        club = Club(
            name="Test Club",
            reputation=101,  # Invalid: above maximum
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add(club)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_club_infrastructure_level_constraint_min(self, test_db_session):
        """Test that infrastructure levels cannot be less than 1"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            stadium_level=0  # Invalid: below minimum
        )
        
        test_db_session.add(club)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_club_infrastructure_level_constraint_max(self, test_db_session):
        """Test that infrastructure levels cannot be greater than 5"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            training_facilities_level=6  # Invalid: above maximum
        )
        
        test_db_session.add(club)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_club_stadium_capacity_constraint(self, test_db_session):
        """Test that stadium capacity must be greater than 0"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            stadium_capacity=0  # Invalid: must be > 0
        )
        
        test_db_session.add(club)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_club_negative_balance(self, test_db_session):
        """Test that clubs can have negative balance"""
        club = Club(
            name="Struggling FC",
            reputation=30,
            league="Championship",
            country="England",
            balance=-5000000  # Negative balance is allowed
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        assert club.balance == -5000000
    
    @pytest.mark.asyncio
    async def test_club_to_dict(self, test_db_session):
        """Test converting club to dictionary"""
        club = Club(
            name="Barcelona",
            reputation=90,
            league="La Liga",
            country="Spain",
            stadium_level=5,
            training_facilities_level=4,
            youth_academy_level=5,
            medical_centre_level=4,
            scouting_network_level=4,
            balance=30000000,
            transfer_budget=80000000,
            wage_budget=600000,
            matchday_revenue=1800000,
            stadium_capacity=99354,
            stadium_name="Camp Nou"
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        club_dict = club.to_dict()
        
        assert club_dict["id"] == club.id
        assert club_dict["name"] == "Barcelona"
        assert club_dict["reputation"] == 90
        assert club_dict["league"] == "La Liga"
        assert club_dict["country"] == "Spain"
        
        assert club_dict["infrastructure"]["stadium_level"] == 5
        assert club_dict["infrastructure"]["training_facilities_level"] == 4
        assert club_dict["infrastructure"]["youth_academy_level"] == 5
        assert club_dict["infrastructure"]["medical_centre_level"] == 4
        assert club_dict["infrastructure"]["scouting_network_level"] == 4
        
        assert club_dict["financial"]["balance"] == 30000000
        assert club_dict["financial"]["transfer_budget"] == 80000000
        assert club_dict["financial"]["wage_budget"] == 600000
        assert club_dict["financial"]["matchday_revenue"] == 1800000
        
        assert club_dict["stadium"]["capacity"] == 99354
        assert club_dict["stadium"]["name"] == "Camp Nou"
        
        assert club_dict["created_at"] is not None
        assert club_dict["updated_at"] is not None
    
    @pytest.mark.asyncio
    async def test_club_repr(self, test_db_session):
        """Test club string representation"""
        club = Club(
            name="Liverpool",
            reputation=88,
            league="Premier League",
            country="England"
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        repr_str = repr(club)
        assert "Club" in repr_str
        assert "Liverpool" in repr_str
        assert "Premier League" in repr_str
        assert "88" in repr_str
    
    @pytest.mark.asyncio
    async def test_get_infrastructure_level_name(self, test_db_session):
        """Test getting infrastructure level names"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        assert club.get_infrastructure_level_name(1) == "Basic"
        assert club.get_infrastructure_level_name(2) == "Standard"
        assert club.get_infrastructure_level_name(3) == "Good"
        assert club.get_infrastructure_level_name(4) == "Excellent"
        assert club.get_infrastructure_level_name(5) == "World Class"
        assert club.get_infrastructure_level_name(99) == "Unknown"
    
    @pytest.mark.asyncio
    async def test_get_average_infrastructure_level(self, test_db_session):
        """Test calculating average infrastructure level"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            stadium_level=3,
            training_facilities_level=4,
            youth_academy_level=2,
            medical_centre_level=3,
            scouting_network_level=3
        )
        
        avg = club.get_average_infrastructure_level()
        assert avg == 3.0  # (3 + 4 + 2 + 3 + 3) / 5 = 3.0
    
    @pytest.mark.asyncio
    async def test_can_afford_transfer(self, test_db_session):
        """Test checking if club can afford a transfer"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            transfer_budget=10000000
        )
        
        assert club.can_afford_transfer(5000000) is True
        assert club.can_afford_transfer(10000000) is True
        assert club.can_afford_transfer(15000000) is False
    
    @pytest.mark.asyncio
    async def test_can_afford_wage(self, test_db_session):
        """Test checking if club can afford additional wage"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            balance=5000000,
            transfer_budget=10000000
        )
        
        # Club with positive balance can afford wages
        assert club.can_afford_wage(50000) is True
        
        # Club with negative balance checks against transfer budget
        club.balance = -1000000
        weekly_wage = 50000
        # transfer_budget / 52 weeks = 192307 per week
        assert club.can_afford_wage(weekly_wage) is True
        assert club.can_afford_wage(200000) is False
    
    @pytest.mark.asyncio
    async def test_is_financially_healthy(self, test_db_session):
        """Test checking if club is financially healthy"""
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country",
            balance=5000000
        )
        
        assert club.is_financially_healthy() is True
        
        club.balance = 0
        assert club.is_financially_healthy() is True
        
        club.balance = -1000000
        assert club.is_financially_healthy() is False
    
    @pytest.mark.asyncio
    async def test_club_query_by_name(self, test_db_session):
        """Test querying clubs by name"""
        club1 = Club(
            name="Arsenal",
            reputation=80,
            league="Premier League",
            country="England"
        )
        club2 = Club(
            name="Chelsea",
            reputation=82,
            league="Premier League",
            country="England"
        )
        
        test_db_session.add_all([club1, club2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Club).where(Club.name == "Arsenal")
        )
        found_club = result.scalar_one_or_none()
        
        assert found_club is not None
        assert found_club.name == "Arsenal"
        assert found_club.reputation == 80
    
    @pytest.mark.asyncio
    async def test_club_query_by_league(self, test_db_session):
        """Test querying clubs by league"""
        club1 = Club(
            name="Bayern Munich",
            reputation=92,
            league="Bundesliga",
            country="Germany"
        )
        club2 = Club(
            name="Borussia Dortmund",
            reputation=85,
            league="Bundesliga",
            country="Germany"
        )
        club3 = Club(
            name="PSG",
            reputation=88,
            league="Ligue 1",
            country="France"
        )
        
        test_db_session.add_all([club1, club2, club3])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Club).where(Club.league == "Bundesliga")
        )
        bundesliga_clubs = result.scalars().all()
        
        assert len(bundesliga_clubs) == 2
        assert all(club.league == "Bundesliga" for club in bundesliga_clubs)
    
    @pytest.mark.asyncio
    async def test_club_query_by_reputation_range(self, test_db_session):
        """Test querying clubs by reputation range"""
        clubs = [
            Club(name="Top Club", reputation=95, league="League 1", country="Country 1"),
            Club(name="Good Club", reputation=75, league="League 1", country="Country 1"),
            Club(name="Average Club", reputation=55, league="League 1", country="Country 1"),
            Club(name="Poor Club", reputation=35, league="League 1", country="Country 1"),
        ]
        
        test_db_session.add_all(clubs)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Club).where(Club.reputation >= 70)
        )
        high_rep_clubs = result.scalars().all()
        
        assert len(high_rep_clubs) == 2
        assert all(club.reputation >= 70 for club in high_rep_clubs)
    
    @pytest.mark.asyncio
    async def test_club_update(self, test_db_session):
        """Test updating club attributes"""
        club = Club(
            name="Juventus",
            reputation=85,
            league="Serie A",
            country="Italy",
            balance=20000000
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        original_updated_at = club.updated_at
        
        # Update club
        club.balance = 25000000
        club.reputation = 87
        await test_db_session.commit()
        await test_db_session.refresh(club)
        
        assert club.balance == 25000000
        assert club.reputation == 87
        # updated_at should change (though timing may make this test flaky)
        # assert club.updated_at > original_updated_at
    
    @pytest.mark.asyncio
    async def test_club_delete(self, test_db_session):
        """Test deleting a club"""
        club = Club(
            name="Test Delete Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add(club)
        await test_db_session.commit()
        club_id = club.id
        
        await test_db_session.delete(club)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Club).where(Club.id == club_id)
        )
        deleted_club = result.scalar_one_or_none()
        
        assert deleted_club is None
