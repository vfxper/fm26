"""
Unit Tests for Match Model
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.match import Match, MatchStatus, WeatherCondition, PitchCondition
from app.models.club import Club
from app.models.career import Career
from app.models.user import User


class TestMatchModel:
    """Test suite for Match model"""
    
    @pytest.fixture
    async def sample_clubs(self, test_db_session):
        """Create sample clubs for testing"""
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
        
        test_db_session.add_all([home_club, away_club])
        await test_db_session.commit()
        await test_db_session.refresh(home_club)
        await test_db_session.refresh(away_club)
        
        return home_club, away_club
    
    @pytest.fixture
    async def sample_career(self, test_db_session, sample_clubs):
        """Create sample career for testing"""
        home_club, _ = sample_clubs
        
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            language_code="en"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        career = Career(
            user_id=user.id,
            club_id=home_club.id,
            manager_name="Test Manager"
        )
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        return career
    
    @pytest.mark.asyncio
    async def test_create_match_basic(self, test_db_session, sample_clubs):
        """Test creating a basic match with required fields"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        assert match.id is not None
        assert match.home_club_id == home_club.id
        assert match.away_club_id == away_club.id
        assert match.competition == "Premier League"
        
        # Check default values
        assert match.home_score == 0
        assert match.away_score == 0
        assert match.home_possession == 50
        assert match.away_possession == 50
        assert match.match_duration == 90
        assert match.extra_time_played is False
        assert match.home_advantage_applied is True
        assert match.status == MatchStatus.SCHEDULED
        assert match.weather == WeatherCondition.CLEAR
        assert match.pitch_condition == PitchCondition.GOOD
        assert match.created_at is not None
        assert match.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_match_full(self, test_db_session, sample_clubs, sample_career):
        """Test creating a match with all fields specified"""
        home_club, away_club = sample_clubs
        
        match = Match(
            career_id=sample_career.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=3,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            venue="Old Trafford",
            weather=WeatherCondition.RAIN,
            pitch_condition=PitchCondition.AVERAGE,
            attendance=75000,
            home_possession=55,
            away_possession=45,
            home_shots=15,
            away_shots=12,
            home_shots_on_target=8,
            away_shots_on_target=6,
            home_passes=450,
            away_passes=380,
            home_pass_accuracy=85,
            away_pass_accuracy=82,
            home_tackles=18,
            away_tackles=22,
            home_fouls=10,
            away_fouls=12,
            home_yellow_cards=2,
            away_yellow_cards=3,
            home_red_cards=0,
            away_red_cards=1,
            match_duration=95,
            extra_time_played=True,
            home_advantage_applied=True,
            player_ratings='{"1": 7.5, "2": 8.0}',
            status=MatchStatus.COMPLETED
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        assert match.id is not None
        assert match.career_id == sample_career.id
        assert match.home_score == 3
        assert match.away_score == 2
        assert match.venue == "Old Trafford"
        assert match.weather == WeatherCondition.RAIN
        assert match.pitch_condition == PitchCondition.AVERAGE
        assert match.attendance == 75000
        assert match.home_possession == 55
        assert match.away_possession == 45
        assert match.home_shots == 15
        assert match.away_shots == 12
        assert match.home_shots_on_target == 8
        assert match.away_shots_on_target == 6
        assert match.home_passes == 450
        assert match.away_passes == 380
        assert match.home_pass_accuracy == 85
        assert match.away_pass_accuracy == 82
        assert match.home_tackles == 18
        assert match.away_tackles == 22
        assert match.home_fouls == 10
        assert match.away_fouls == 12
        assert match.home_yellow_cards == 2
        assert match.away_yellow_cards == 3
        assert match.home_red_cards == 0
        assert match.away_red_cards == 1
        assert match.match_duration == 95
        assert match.extra_time_played is True
        assert match.status == MatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_match_score_constraint_negative(self, test_db_session, sample_clubs):
        """Test that scores cannot be negative"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=-1,  # Invalid: negative score
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_possession_constraint_min(self, test_db_session, sample_clubs):
        """Test that possession cannot be less than 0"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_possession=-1,  # Invalid: below minimum
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_possession_constraint_max(self, test_db_session, sample_clubs):
        """Test that possession cannot be greater than 100"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_possession=101,  # Invalid: above maximum
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_shots_on_target_constraint(self, test_db_session, sample_clubs):
        """Test that shots on target cannot exceed total shots"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_shots=10,
            home_shots_on_target=15,  # Invalid: more than total shots
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_duration_constraint(self, test_db_session, sample_clubs):
        """Test that match duration must be at least 90 minutes"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_duration=85,  # Invalid: less than 90
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_different_clubs_constraint(self, test_db_session, sample_clubs):
        """Test that home and away clubs must be different"""
        home_club, _ = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=home_club.id,  # Invalid: same club
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_match_to_dict(self, test_db_session, sample_clubs):
        """Test converting match to dictionary"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=2,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            venue="Old Trafford",
            weather=WeatherCondition.CLOUDY,
            pitch_condition=PitchCondition.GOOD,
            attendance=70000,
            home_possession=60,
            away_possession=40,
            home_shots=12,
            away_shots=8,
            home_shots_on_target=6,
            away_shots_on_target=4,
            status=MatchStatus.COMPLETED
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        match_dict = match.to_dict()
        
        assert match_dict["id"] == match.id
        assert match_dict["home_club_id"] == home_club.id
        assert match_dict["away_club_id"] == away_club.id
        assert match_dict["result"]["home_score"] == 2
        assert match_dict["result"]["away_score"] == 1
        assert match_dict["metadata"]["competition"] == "Premier League"
        assert match_dict["metadata"]["venue"] == "Old Trafford"
        assert match_dict["metadata"]["weather"] == WeatherCondition.CLOUDY
        assert match_dict["metadata"]["pitch_condition"] == PitchCondition.GOOD
        assert match_dict["metadata"]["attendance"] == 70000
        assert match_dict["statistics"]["possession"]["home"] == 60
        assert match_dict["statistics"]["possession"]["away"] == 40
        assert match_dict["statistics"]["shots"]["home"] == 12
        assert match_dict["statistics"]["shots"]["away"] == 8
        assert match_dict["status"] == MatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_match_repr(self, test_db_session, sample_clubs):
        """Test match string representation"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=3,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            status=MatchStatus.COMPLETED
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        repr_str = repr(match)
        assert "Match" in repr_str
        assert "3-1" in repr_str
        assert str(home_club.id) in repr_str
        assert str(away_club.id) in repr_str
    
    @pytest.mark.asyncio
    async def test_get_result_string(self, test_db_session, sample_clubs):
        """Test getting match result as string"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=4,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        assert match.get_result_string() == "4-2"
    
    @pytest.mark.asyncio
    async def test_get_winner(self, test_db_session, sample_clubs):
        """Test determining match winner"""
        home_club, away_club = sample_clubs
        
        # Home win
        match_home_win = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=3,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_home_win.get_winner() == "home"
        
        # Away win
        match_away_win = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=1,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_away_win.get_winner() == "away"
        
        # Draw
        match_draw = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=2,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_draw.get_winner() is None
    
    @pytest.mark.asyncio
    async def test_is_draw(self, test_db_session, sample_clubs):
        """Test checking if match is a draw"""
        home_club, away_club = sample_clubs
        
        match_draw = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=1,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_draw.is_draw() is True
        
        match_not_draw = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=2,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_not_draw.is_draw() is False
    
    @pytest.mark.asyncio
    async def test_match_status_checks(self, test_db_session, sample_clubs):
        """Test match status check methods"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            status=MatchStatus.SCHEDULED
        )
        
        assert match.is_scheduled() is True
        assert match.is_in_progress() is False
        assert match.is_completed() is False
        
        match.status = MatchStatus.IN_PROGRESS
        assert match.is_scheduled() is False
        assert match.is_in_progress() is True
        assert match.is_completed() is False
        
        match.status = MatchStatus.COMPLETED
        assert match.is_scheduled() is False
        assert match.is_in_progress() is False
        assert match.is_completed() is True
    
    @pytest.mark.asyncio
    async def test_get_total_goals(self, test_db_session, sample_clubs):
        """Test calculating total goals"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=3,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        assert match.get_total_goals() == 5
    
    @pytest.mark.asyncio
    async def test_get_total_cards(self, test_db_session, sample_clubs):
        """Test calculating total cards"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            home_yellow_cards=3,
            away_yellow_cards=2,
            home_red_cards=1,
            away_red_cards=0
        )
        
        assert match.get_total_cards() == 6
    
    @pytest.mark.asyncio
    async def test_get_shot_accuracy(self, test_db_session, sample_clubs):
        """Test calculating shot accuracy"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            home_shots=10,
            home_shots_on_target=6,
            away_shots=8,
            away_shots_on_target=4
        )
        
        assert match.get_shot_accuracy("home") == 60.0
        assert match.get_shot_accuracy("away") == 50.0
        
        # Test with no shots
        match_no_shots = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            home_shots=0,
            home_shots_on_target=0
        )
        assert match_no_shots.get_shot_accuracy("home") == 0.0
    
    @pytest.mark.asyncio
    async def test_was_high_scoring(self, test_db_session, sample_clubs):
        """Test checking if match was high-scoring"""
        home_club, away_club = sample_clubs
        
        match_high = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=4,
            away_score=2,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_high.was_high_scoring() is True
        
        match_low = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=2,
            away_score=1,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        assert match_low.was_high_scoring() is False
    
    @pytest.mark.asyncio
    async def test_was_clean_sheet(self, test_db_session, sample_clubs):
        """Test checking if team kept clean sheet"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            home_score=2,
            away_score=0,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        assert match.was_clean_sheet("home") is True
        assert match.was_clean_sheet("away") is False
    
    @pytest.mark.asyncio
    async def test_match_query_by_career(self, test_db_session, sample_clubs, sample_career):
        """Test querying matches by career"""
        home_club, away_club = sample_clubs
        
        match1 = Match(
            career_id=sample_career.id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        match2 = Match(
            career_id=sample_career.id,
            home_club_id=away_club.id,
            away_club_id=home_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add_all([match1, match2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Match).where(Match.career_id == sample_career.id)
        )
        career_matches = result.scalars().all()
        
        assert len(career_matches) == 2
        assert all(m.career_id == sample_career.id for m in career_matches)
    
    @pytest.mark.asyncio
    async def test_match_query_by_competition(self, test_db_session, sample_clubs):
        """Test querying matches by competition"""
        home_club, away_club = sample_clubs
        
        match1 = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        match2 = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="FA Cup"
        )
        
        test_db_session.add_all([match1, match2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Match).where(Match.competition == "Premier League")
        )
        pl_matches = result.scalars().all()
        
        assert len(pl_matches) == 1
        assert pl_matches[0].competition == "Premier League"
    
    @pytest.mark.asyncio
    async def test_match_query_by_status(self, test_db_session, sample_clubs):
        """Test querying matches by status"""
        home_club, away_club = sample_clubs
        
        match1 = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            status=MatchStatus.SCHEDULED
        )
        match2 = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            status=MatchStatus.COMPLETED
        )
        
        test_db_session.add_all([match1, match2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Match).where(Match.status == MatchStatus.COMPLETED)
        )
        completed_matches = result.scalars().all()
        
        assert len(completed_matches) == 1
        assert completed_matches[0].status == MatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_match_update(self, test_db_session, sample_clubs):
        """Test updating match attributes"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League",
            status=MatchStatus.SCHEDULED
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        # Update match
        match.home_score = 2
        match.away_score = 1
        match.status = MatchStatus.COMPLETED
        await test_db_session.commit()
        await test_db_session.refresh(match)
        
        assert match.home_score == 2
        assert match.away_score == 1
        assert match.status == MatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_match_delete(self, test_db_session, sample_clubs):
        """Test deleting a match"""
        home_club, away_club = sample_clubs
        
        match = Match(
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            match_date=datetime.now(timezone.utc),
            competition="Premier League"
        )
        
        test_db_session.add(match)
        await test_db_session.commit()
        match_id = match.id
        
        await test_db_session.delete(match)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Match).where(Match.id == match_id)
        )
        deleted_match = result.scalar_one_or_none()
        
        assert deleted_match is None
    
    @pytest.mark.asyncio
    async def test_match_with_all_weather_conditions(self, test_db_session, sample_clubs):
        """Test creating matches with all weather conditions"""
        home_club, away_club = sample_clubs
        
        for weather in WeatherCondition:
            match = Match(
                home_club_id=home_club.id,
                away_club_id=away_club.id,
                match_date=datetime.now(timezone.utc),
                competition="Premier League",
                weather=weather
            )
            test_db_session.add(match)
        
        await test_db_session.commit()
        
        result = await test_db_session.execute(select(Match))
        matches = result.scalars().all()
        
        assert len(matches) == len(WeatherCondition)
    
    @pytest.mark.asyncio
    async def test_match_with_all_pitch_conditions(self, test_db_session, sample_clubs):
        """Test creating matches with all pitch conditions"""
        home_club, away_club = sample_clubs
        
        for pitch in PitchCondition:
            match = Match(
                home_club_id=home_club.id,
                away_club_id=away_club.id,
                match_date=datetime.now(timezone.utc),
                competition="Premier League",
                pitch_condition=pitch
            )
            test_db_session.add(match)
        
        await test_db_session.commit()
        
        result = await test_db_session.execute(select(Match))
        matches = result.scalars().all()
        
        assert len(matches) == len(PitchCondition)
