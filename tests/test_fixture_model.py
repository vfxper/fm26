"""
Unit Tests for Fixture Model
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.fixture import Fixture, FixtureStatus
from app.models.competition import Competition, CompetitionType
from app.models.club import Club


class TestFixtureModel:
    """Test suite for Fixture model"""
    
    @pytest.mark.asyncio
    async def test_create_fixture_basic(self, test_db_session):
        """Test creating a basic fixture with required fields"""
        # Create dependencies
        competition = Competition(
            name="Premier League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="England",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Manchester United",
            reputation=85,
            league="Premier League",
            country="England"
        )
        away_club = Club(
            name="Liverpool",
            reputation=88,
            league="Premier League",
            country="England"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        await test_db_session.commit()
        await test_db_session.refresh(fixture)
        
        assert fixture.id is not None
        assert fixture.competition_id == competition.id
        assert fixture.home_club_id == home_club.id
        assert fixture.away_club_id == away_club.id
        assert fixture.match_id is None
        assert fixture.matchday == 1
        assert fixture.round_name is None
        assert fixture.scheduled_date == scheduled_date
        assert fixture.status == FixtureStatus.SCHEDULED
        assert fixture.created_at is not None
        assert fixture.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_fixture_full(self, test_db_session):
        """Test creating a fixture with all fields specified"""
        # Create dependencies
        competition = Competition(
            name="FA Cup",
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=2024,
            country="England",
            num_teams=64,
            num_matchdays=6
        )
        home_club = Club(
            name="Arsenal",
            reputation=82,
            league="Premier League",
            country="England"
        )
        away_club = Club(
            name="Chelsea",
            reputation=83,
            league="Premier League",
            country="England"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=14)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=5,
            round_name="Semi Final",
            scheduled_date=scheduled_date,
            status=FixtureStatus.SCHEDULED
        )
        
        test_db_session.add(fixture)
        await test_db_session.commit()
        await test_db_session.refresh(fixture)
        
        assert fixture.id is not None
        assert fixture.competition_id == competition.id
        assert fixture.home_club_id == home_club.id
        assert fixture.away_club_id == away_club.id
        assert fixture.matchday == 5
        assert fixture.round_name == "Semi Final"
        assert fixture.scheduled_date == scheduled_date
        assert fixture.status == FixtureStatus.SCHEDULED
    
    @pytest.mark.asyncio
    async def test_fixture_matchday_constraint(self, test_db_session):
        """Test that matchday must be greater than 0"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture with invalid matchday
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=0,  # Invalid: must be > 0
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_fixture_different_clubs_constraint(self, test_db_session):
        """Test that home and away clubs must be different"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        club = Club(
            name="Test Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(club)
        
        # Create fixture with same home and away club
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=club.id,
            away_club_id=club.id,  # Invalid: same as home_club_id
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_fixture_to_dict(self, test_db_session):
        """Test converting fixture to dictionary"""
        # Create dependencies
        competition = Competition(
            name="Bundesliga",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Germany",
            num_teams=18,
            num_matchdays=34
        )
        home_club = Club(
            name="Bayern Munich",
            reputation=92,
            league="Bundesliga",
            country="Germany"
        )
        away_club = Club(
            name="Borussia Dortmund",
            reputation=85,
            league="Bundesliga",
            country="Germany"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=10,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        await test_db_session.commit()
        await test_db_session.refresh(fixture)
        
        fixture_dict = fixture.to_dict()
        
        assert fixture_dict["id"] == fixture.id
        assert fixture_dict["competition_id"] == competition.id
        assert fixture_dict["home_club_id"] == home_club.id
        assert fixture_dict["away_club_id"] == away_club.id
        assert fixture_dict["match_id"] is None
        
        assert fixture_dict["details"]["matchday"] == 10
        assert fixture_dict["details"]["round_name"] is None
        assert fixture_dict["details"]["scheduled_date"] is not None
        
        assert fixture_dict["status"] == FixtureStatus.SCHEDULED
        
        assert fixture_dict["created_at"] is not None
        assert fixture_dict["updated_at"] is not None
    
    @pytest.mark.asyncio
    async def test_fixture_repr(self, test_db_session):
        """Test fixture string representation"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        await test_db_session.commit()
        await test_db_session.refresh(fixture)
        
        repr_str = repr(fixture)
        assert "Fixture" in repr_str
        assert str(fixture.matchday) in repr_str
    
    @pytest.mark.asyncio
    async def test_is_scheduled(self, test_db_session):
        """Test checking if fixture is scheduled"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date,
            status=FixtureStatus.SCHEDULED
        )
        
        assert fixture.is_scheduled() is True
        
        fixture.status = FixtureStatus.COMPLETED
        assert fixture.is_scheduled() is False
    
    @pytest.mark.asyncio
    async def test_is_completed(self, test_db_session):
        """Test checking if fixture is completed"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date,
            status=FixtureStatus.COMPLETED
        )
        
        assert fixture.is_completed() is True
        
        fixture.status = FixtureStatus.SCHEDULED
        assert fixture.is_completed() is False
    
    @pytest.mark.asyncio
    async def test_has_match(self, test_db_session):
        """Test checking if fixture has an associated match"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        assert fixture.has_match() is False
        
        fixture.match_id = 123
        assert fixture.has_match() is True
    
    @pytest.mark.asyncio
    async def test_complete_fixture(self, test_db_session):
        """Test completing a fixture"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        fixture.complete_fixture(match_id=456)
        
        assert fixture.match_id == 456
        assert fixture.status == FixtureStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_postpone_fixture(self, test_db_session):
        """Test postponing a fixture"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        new_date = datetime.now(timezone.utc) + timedelta(days=14)
        fixture.postpone_fixture(new_date)
        
        assert fixture.scheduled_date == new_date
        assert fixture.status == FixtureStatus.POSTPONED
    
    @pytest.mark.asyncio
    async def test_cancel_fixture(self, test_db_session):
        """Test cancelling a fixture"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        fixture.cancel_fixture()
        
        assert fixture.status == FixtureStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_reschedule_fixture(self, test_db_session):
        """Test rescheduling a fixture"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date,
            status=FixtureStatus.POSTPONED
        )
        
        new_date = datetime.now(timezone.utc) + timedelta(days=21)
        fixture.reschedule_fixture(new_date)
        
        assert fixture.scheduled_date == new_date
        assert fixture.status == FixtureStatus.SCHEDULED
    
    @pytest.mark.asyncio
    async def test_fixture_query_by_competition(self, test_db_session):
        """Test querying fixtures by competition"""
        # Create dependencies
        comp1 = Competition(
            name="League 1",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        comp2 = Competition(
            name="League 2",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([comp1, comp2, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(comp1)
        await test_db_session.refresh(comp2)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixtures
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture1 = Fixture(
            competition_id=comp1.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        fixture2 = Fixture(
            competition_id=comp1.id,
            home_club_id=away_club.id,
            away_club_id=home_club.id,
            matchday=2,
            scheduled_date=scheduled_date + timedelta(days=7)
        )
        fixture3 = Fixture(
            competition_id=comp2.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add_all([fixture1, fixture2, fixture3])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Fixture).where(Fixture.competition_id == comp1.id)
        )
        comp1_fixtures = result.scalars().all()
        
        assert len(comp1_fixtures) == 2
        assert all(f.competition_id == comp1.id for f in comp1_fixtures)
    
    @pytest.mark.asyncio
    async def test_fixture_query_by_matchday(self, test_db_session):
        """Test querying fixtures by matchday"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixtures
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture1 = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        fixture2 = Fixture(
            competition_id=competition.id,
            home_club_id=away_club.id,
            away_club_id=home_club.id,
            matchday=2,
            scheduled_date=scheduled_date + timedelta(days=7)
        )
        
        test_db_session.add_all([fixture1, fixture2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Fixture).where(
                Fixture.competition_id == competition.id,
                Fixture.matchday == 1
            )
        )
        matchday1_fixtures = result.scalars().all()
        
        assert len(matchday1_fixtures) == 1
        assert matchday1_fixtures[0].matchday == 1
    
    @pytest.mark.asyncio
    async def test_fixture_delete(self, test_db_session):
        """Test deleting a fixture"""
        # Create dependencies
        competition = Competition(
            name="Test League",
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=2024,
            country="Test Country",
            num_teams=20,
            num_matchdays=38
        )
        home_club = Club(
            name="Home Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        away_club = Club(
            name="Away Club",
            reputation=50,
            league="Test League",
            country="Test Country"
        )
        
        test_db_session.add_all([competition, home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(competition)
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        # Create fixture
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=7)
        fixture = Fixture(
            competition_id=competition.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            matchday=1,
            scheduled_date=scheduled_date
        )
        
        test_db_session.add(fixture)
        await test_db_session.commit()
        fixture_id = fixture.id
        
        await test_db_session.delete(fixture)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )
        deleted_fixture = result.scalar_one_or_none()
        
        assert deleted_fixture is None
