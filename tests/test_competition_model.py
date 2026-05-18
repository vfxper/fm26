"""
Unit Tests for Competition Model
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.competition import Competition, CompetitionType


class TestCompetitionModel:
    """Test suite for Competition model"""
    
    @pytest.mark.asyncio
    async def test_create_competition_basic(self, test_db_session):
        """Test creating a basic competition with required fields"""
        competition = Competition(
            name="Premier League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="England",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        assert competition.id is not None
        assert competition.name == "Premier League"
        assert competition.competition_type == CompetitionType.DOMESTIC_LEAGUE
        assert competition.season == 2024
        assert competition.country == "England"
        assert competition.num_teams == 20
        assert competition.num_matchdays == 38
        
        # Check default values
        assert competition.current_matchday == 1
        assert competition.prize_money is None
        assert competition.reputation_winner == 10
        assert competition.reputation_runner_up == 5
        assert competition.promotion_places == 0
        assert competition.relegation_places == 0
        assert competition.playoff_places == 0
        assert competition.champions_league_places == 0
        assert competition.europa_league_places == 0
        assert competition.is_active is True
        assert competition.is_completed is False
        assert competition.created_at is not None
        assert competition.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_competition_full(self, test_db_session):
        """Test creating a competition with all fields specified"""
        competition = Competition(
            name="La Liga",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Spain",
            num_teams=20,
            num_matchdays=38,
            current_matchday=10,
            prize_money='{"1": 50000000, "2": 40000000, "3": 30000000}',
            reputation_winner=15,
            reputation_runner_up=8,
            promotion_places=0,
            relegation_places=3,
            playoff_places=0,
            champions_league_places=4,
            europa_league_places=2,
            is_active=True,
            is_completed=False
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        assert competition.id is not None
        assert competition.name == "La Liga"
        assert competition.competition_type == CompetitionType.DOMESTIC_LEAGUE
        assert competition.season == 2024
        assert competition.country == "Spain"
        assert competition.num_teams == 20
        assert competition.num_matchdays == 38
        assert competition.current_matchday == 10
        assert competition.prize_money == '{"1": 50000000, "2": 40000000, "3": 30000000}'
        assert competition.reputation_winner == 15
        assert competition.reputation_runner_up == 8
        assert competition.relegation_places == 3
        assert competition.champions_league_places == 4
        assert competition.europa_league_places == 2
    
    @pytest.mark.asyncio
    async def test_create_domestic_cup(self, test_db_session):
        """Test creating a domestic cup competition"""
        competition = Competition(
            name="FA Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="England",
            num_teams=64,
            num_matchdays=6,  # Round of 64, 32, 16, QF, SF, Final
            reputation_winner=12,
            reputation_runner_up=6
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        assert competition.id is not None
        assert competition.name == "FA Cup"
        assert competition.competition_type == CompetitionType.DOMESTIC_CUP
        assert competition.num_teams == 64
        assert competition.num_matchdays == 6
    
    @pytest.mark.asyncio
    async def test_create_continental_cup(self, test_db_session):
        """Test creating a continental cup competition"""
        competition = Competition(
            name="Champions League",
            competition_type=CompetitionType.CONTINENTAL_CUP,
            season=2024,
            country="Europe",
            num_teams=32,
            num_matchdays=13,  # 6 group stage + 7 knockout rounds
            reputation_winner=20,
            reputation_runner_up=10
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        assert competition.id is not None
        assert competition.name == "Champions League"
        assert competition.competition_type == CompetitionType.CONTINENTAL_CUP
        assert competition.num_teams == 32
        assert competition.num_matchdays == 13
        assert competition.reputation_winner == 20
    
    @pytest.mark.asyncio
    async def test_competition_season_constraint_min(self, test_db_session):
        """Test that season cannot be less than 2020"""
        competition = Competition(
            name="Test Competition",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2019,  # Invalid: below minimum
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_competition_season_constraint_max(self, test_db_session):
        """Test that season cannot be greater than 2100"""
        competition = Competition(
            name="Test Competition",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2101,  # Invalid: above maximum
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_competition_num_teams_constraint(self, test_db_session):
        """Test that num_teams must be greater than 0"""
        competition = Competition(
            name="Test Competition",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=0,  # Invalid: must be > 0
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_competition_current_matchday_constraint(self, test_db_session):
        """Test that current_matchday cannot exceed num_matchdays"""
        competition = Competition(
            name="Test Competition",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            current_matchday=39  # Invalid: exceeds num_matchdays
        )
        
        test_db_session.add(competition)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_competition_to_dict(self, test_db_session):
        """Test converting competition to dictionary"""
        competition = Competition(
            name="Bundesliga",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Germany",
            num_teams=18,
            num_matchdays=34,
            current_matchday=15,
            reputation_winner=12,
            reputation_runner_up=7,
            relegation_places=2,
            playoff_places=1,
            champions_league_places=4,
            europa_league_places=2
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        comp_dict = competition.to_dict()
        
        assert comp_dict["id"] == competition.id
        assert comp_dict["name"] == "Bundesliga"
        assert comp_dict["competition_type"] == CompetitionType.DOMESTIC_LEAGUE
        assert comp_dict["season"] == 2024
        assert comp_dict["country"] == "Germany"
        
        assert comp_dict["structure"]["num_teams"] == 18
        assert comp_dict["structure"]["num_matchdays"] == 34
        assert comp_dict["structure"]["current_matchday"] == 15
        
        assert comp_dict["reputation"]["winner"] == 12
        assert comp_dict["reputation"]["runner_up"] == 7
        
        assert comp_dict["promotion_relegation"]["relegation_places"] == 2
        assert comp_dict["promotion_relegation"]["playoff_places"] == 1
        
        assert comp_dict["european_qualification"]["champions_league_places"] == 4
        assert comp_dict["european_qualification"]["europa_league_places"] == 2
        
        assert comp_dict["status"]["is_active"] is True
        assert comp_dict["status"]["is_completed"] is False
        
        assert comp_dict["created_at"] is not None
        assert comp_dict["updated_at"] is not None
    
    @pytest.mark.asyncio
    async def test_competition_repr(self, test_db_session):
        """Test competition string representation"""
        competition = Competition(
            name="Serie A",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Italy",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        repr_str = repr(competition)
        assert "Competition" in repr_str
        assert "Serie A" in repr_str
        assert "2024" in repr_str
    
    @pytest.mark.asyncio
    async def test_is_league(self, test_db_session):
        """Test checking if competition is a league"""
        league = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        cup = Competition(
            name="Test Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="Test Country",
            num_teams=64,
            num_matchdays=6
        )
        
        assert league.is_league() is True
        assert cup.is_league() is False
    
    @pytest.mark.asyncio
    async def test_is_cup(self, test_db_session):
        """Test checking if competition is a cup"""
        league = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        domestic_cup = Competition(
            name="Test Domestic Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="Test Country",
            num_teams=64,
            num_matchdays=6
        )
        
        continental_cup = Competition(
            name="Test Continental Cup",
            competition_type=CompetitionType.CONTINENTAL_CUP,
            season=2024,
            country="Europe",
            num_teams=32,
            num_matchdays=13
        )
        
        assert league.is_cup() is False
        assert domestic_cup.is_cup() is True
        assert continental_cup.is_cup() is True
    
    @pytest.mark.asyncio
    async def test_has_promotion_relegation(self, test_db_session):
        """Test checking if competition has promotion/relegation"""
        comp_with_relegation = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            relegation_places=3
        )
        
        comp_without = Competition(
            name="Test Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="Test Country",
            num_teams=64,
            num_matchdays=6
        )
        
        assert comp_with_relegation.has_promotion_relegation() is True
        assert comp_without.has_promotion_relegation() is False
    
    @pytest.mark.asyncio
    async def test_has_european_qualification(self, test_db_session):
        """Test checking if competition offers European qualification"""
        comp_with_europe = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            champions_league_places=4
        )
        
        comp_without = Competition(
            name="Test Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="Test Country",
            num_teams=64,
            num_matchdays=6
        )
        
        assert comp_with_europe.has_european_qualification() is True
        assert comp_without.has_european_qualification() is False
    
    @pytest.mark.asyncio
    async def test_get_progress_percentage(self, test_db_session):
        """Test calculating competition progress percentage"""
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            current_matchday=19
        )
        
        progress = competition.get_progress_percentage()
        assert progress == 50.0  # 19/38 = 50%
    
    @pytest.mark.asyncio
    async def test_is_final_matchday(self, test_db_session):
        """Test checking if on final matchday"""
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            current_matchday=38
        )
        
        assert competition.is_final_matchday() is True
        
        competition.current_matchday = 37
        assert competition.is_final_matchday() is False
    
    @pytest.mark.asyncio
    async def test_advance_matchday(self, test_db_session):
        """Test advancing to next matchday"""
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            current_matchday=10
        )
        
        result = competition.advance_matchday()
        assert result is True
        assert competition.current_matchday == 11
        
        # Try advancing from final matchday
        competition.current_matchday = 38
        result = competition.advance_matchday()
        assert result is False
        assert competition.current_matchday == 38
    
    @pytest.mark.asyncio
    async def test_complete_competition(self, test_db_session):
        """Test completing a competition"""
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            is_active=True,
            is_completed=False
        )
        
        competition.complete_competition()
        
        assert competition.is_completed is True
        assert competition.is_active is False
    
    @pytest.mark.asyncio
    async def test_competition_query_by_season(self, test_db_session):
        """Test querying competitions by season"""
        comp1 = Competition(
            name="League 2024",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        comp2 = Competition(
            name="League 2025",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2025,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add_all([comp1, comp2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Competition).where(Competition.season == 2024)
        )
        comps_2024 = result.scalars().all()
        
        assert len(comps_2024) == 1
        assert comps_2024[0].season == 2024
    
    @pytest.mark.asyncio
    async def test_competition_query_by_type(self, test_db_session):
        """Test querying competitions by type"""
        league = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        cup = Competition(
            name="Test Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="Test Country",
            num_teams=64,
            num_matchdays=6
        )
        
        test_db_session.add_all([league, cup])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Competition).where(Competition.competition_type == CompetitionType.DOMESTIC_LEAGUE)
        )
        leagues = result.scalars().all()
        
        assert len(leagues) == 1
        assert leagues[0].competition_type == CompetitionType.DOMESTIC_LEAGUE
    
    @pytest.mark.asyncio
    async def test_competition_update(self, test_db_session):
        """Test updating competition attributes"""
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38,
            current_matchday=1
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        # Update competition
        competition.current_matchday = 10
        competition.is_active = True
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        
        assert competition.current_matchday == 10
        assert competition.is_active is True
    
    @pytest.mark.asyncio
    async def test_competition_delete(self, test_db_session):
        """Test deleting a competition"""
        competition = Competition(
            name="Test Delete Competition",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        
        test_db_session.add(competition)
        await test_db_session.commit()
        comp_id = competition.id
        
        await test_db_session.delete(competition)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Competition).where(Competition.id == comp_id)
        )
        deleted_comp = result.scalar_one_or_none()
        
        assert deleted_comp is None
