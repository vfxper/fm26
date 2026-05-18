"""
Unit Tests for Injury Model
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.injury import Injury, InjurySeverity, InjuryStatus


class TestInjuryModel:
    """Test suite for Injury model"""
    
    @pytest.mark.asyncio
    async def test_create_injury_with_all_attributes(self, test_db_session):
        """Test creating an injury with all required attributes"""
        now = datetime.now()
        expected_recovery = now + timedelta(weeks=2)
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Hamstring Strain",
            injury_description="Grade 2 hamstring strain during sprint",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=expected_recovery,
            recovery_weeks=2,
            season=1,
            week=10,
            sharpness_penalty=10,
            is_injury_prone_flag=False
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        assert injury.id is not None
        assert injury.career_id == 1
        assert injury.player_id == 1
        assert injury.squad_player_id == 1
        assert injury.injury_type == "Hamstring Strain"
        assert injury.severity == InjurySeverity.MINOR
        assert injury.status == InjuryStatus.ACTIVE
        assert injury.recovery_weeks == 2
        assert injury.season == 1
        assert injury.week == 10
        assert injury.sharpness_penalty == 10
        assert injury.is_injury_prone_flag is False
    
    @pytest.mark.asyncio
    async def test_injury_severity_enum(self, test_db_session):
        """Test injury severity enumeration values"""
        now = datetime.now()
        
        # Test MINOR severity
        minor_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Ankle Sprain",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=5
        )
        
        test_db_session.add(minor_injury)
        await test_db_session.commit()
        await test_db_session.refresh(minor_injury)
        
        assert minor_injury.severity == InjurySeverity.MINOR
        assert minor_injury.is_minor() is True
        assert minor_injury.is_moderate() is False
        assert minor_injury.is_severe() is False
    
    @pytest.mark.asyncio
    async def test_injury_status_enum(self, test_db_session):
        """Test injury status enumeration values"""
        now = datetime.now()
        
        # Test ACTIVE status
        active_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Knee Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=1,
            week=15
        )
        
        test_db_session.add(active_injury)
        await test_db_session.commit()
        await test_db_session.refresh(active_injury)
        
        assert active_injury.status == InjuryStatus.ACTIVE
        assert active_injury.is_active() is True
        assert active_injury.is_recovering() is False
        assert active_injury.is_recovered() is False
    
    @pytest.mark.asyncio
    async def test_injury_recovery_weeks_constraint(self, test_db_session):
        """Test that recovery_weeks must be positive"""
        now = datetime.now()
        
        # Test invalid recovery_weeks (0)
        invalid_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=0,  # Invalid: must be > 0
            season=1,
            week=1
        )
        
        test_db_session.add(invalid_injury)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_injury_week_constraint(self, test_db_session):
        """Test that week must be between 1 and 52"""
        now = datetime.now()
        
        # Test invalid week (0)
        invalid_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=0  # Invalid: must be >= 1
        )
        
        test_db_session.add(invalid_injury)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
        
        await test_db_session.rollback()
        
        # Test invalid week (53)
        invalid_injury2 = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=53  # Invalid: must be <= 52
        )
        
        test_db_session.add(invalid_injury2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_injury_season_constraint(self, test_db_session):
        """Test that season must be positive"""
        now = datetime.now()
        
        # Test invalid season (0)
        invalid_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=0,  # Invalid: must be >= 1
            week=1
        )
        
        test_db_session.add(invalid_injury)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_injury_sharpness_penalty_constraint(self, test_db_session):
        """Test that sharpness_penalty must be between 0 and 100"""
        now = datetime.now()
        
        # Test invalid sharpness_penalty (101)
        invalid_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Test Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=1,
            sharpness_penalty=101  # Invalid: must be <= 100
        )
        
        test_db_session.add(invalid_injury)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_injury_match_minute_constraint(self, test_db_session):
        """Test that match_minute must be between 0 and 120"""
        now = datetime.now()
        
        # Test invalid match_minute (121)
        invalid_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Match Injury",
            severity=InjurySeverity.MODERATE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            occurred_in_match_id=1,
            match_minute=121,  # Invalid: must be <= 120
            season=1,
            week=10
        )
        
        test_db_session.add(invalid_injury)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_injury_to_dict(self, test_db_session):
        """Test converting injury to dictionary"""
        now = datetime.now()
        expected_recovery = now + timedelta(weeks=3)
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Muscle Strain",
            injury_description="Calf muscle strain",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=expected_recovery,
            recovery_weeks=3,
            season=1,
            week=20,
            sharpness_penalty=10,
            is_injury_prone_flag=False
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        injury_dict = injury.to_dict()
        
        assert injury_dict["career_id"] == 1
        assert injury_dict["player_id"] == 1
        assert injury_dict["squad_player_id"] == 1
        assert injury_dict["injury_type"] == "Muscle Strain"
        assert injury_dict["injury_description"] == "Calf muscle strain"
        assert injury_dict["severity"] == "moderate"
        assert injury_dict["status"] == "active"
        assert injury_dict["recovery_weeks"] == 3
        assert injury_dict["season"] == 1
        assert injury_dict["week"] == 20
        assert injury_dict["sharpness_penalty"] == 10
        assert injury_dict["is_injury_prone_flag"] is False
    
    @pytest.mark.asyncio
    async def test_injury_repr(self, test_db_session):
        """Test injury string representation"""
        now = datetime.now()
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Hamstring Strain",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=2),
            recovery_weeks=2,
            season=1,
            week=10
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        repr_str = repr(injury)
        
        assert "Injury" in repr_str
        assert "player_id=1" in repr_str
        assert "Hamstring Strain" in repr_str
        assert "minor" in repr_str
        assert "active" in repr_str
        assert "recovery_weeks=2" in repr_str
    
    @pytest.mark.asyncio
    async def test_is_match_injury(self, test_db_session):
        """Test checking if injury occurred during a match"""
        now = datetime.now()
        
        # Match injury
        match_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Collision Injury",
            severity=InjurySeverity.MODERATE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            occurred_in_match_id=1,
            match_minute=45,
            season=1,
            week=10
        )
        
        test_db_session.add(match_injury)
        await test_db_session.commit()
        await test_db_session.refresh(match_injury)
        
        assert match_injury.is_match_injury() is True
        assert match_injury.is_training_injury() is False
    
    @pytest.mark.asyncio
    async def test_is_training_injury(self, test_db_session):
        """Test checking if injury occurred during training"""
        now = datetime.now()
        
        # Training injury
        training_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Training Ground Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=5
        )
        
        test_db_session.add(training_injury)
        await test_db_session.commit()
        await test_db_session.refresh(training_injury)
        
        assert training_injury.is_training_injury() is True
        assert training_injury.is_match_injury() is False
    
    @pytest.mark.asyncio
    async def test_get_effective_ca_penalty(self, test_db_session):
        """Test calculating effective CA penalty based on injury status"""
        now = datetime.now()
        
        # Active injury (100% penalty)
        active_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Active Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=1,
            week=10
        )
        
        test_db_session.add(active_injury)
        await test_db_session.commit()
        await test_db_session.refresh(active_injury)
        
        assert active_injury.get_effective_ca_penalty() == 100
        
        # Recovering injury (sharpness penalty)
        active_injury.status = InjuryStatus.RECOVERING
        await test_db_session.commit()
        await test_db_session.refresh(active_injury)
        
        assert active_injury.get_effective_ca_penalty() == 10
        
        # Recovered injury (0% penalty)
        active_injury.status = InjuryStatus.RECOVERED
        await test_db_session.commit()
        await test_db_session.refresh(active_injury)
        
        assert active_injury.get_effective_ca_penalty() == 0
    
    @pytest.mark.asyncio
    async def test_return_from_injury(self, test_db_session):
        """Test marking player as returned from injury"""
        now = datetime.now()
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Recovered Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=1,
            week=10
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        # Return from injury
        injury.return_from_injury()
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        assert injury.status == InjuryStatus.RECOVERING
        assert injury.actual_recovery_date is not None
        # Note: full_recovery_date calculation uses func.now() which is server-side
    
    @pytest.mark.asyncio
    async def test_fully_recover(self, test_db_session):
        """Test marking player as fully recovered"""
        now = datetime.now()
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Fully Recovered Injury",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=2),
            recovery_weeks=2,
            season=1,
            week=10
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        # Fully recover
        injury.fully_recover()
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        assert injury.status == InjuryStatus.RECOVERED
        assert injury.full_recovery_date is not None
    
    @pytest.mark.asyncio
    async def test_set_injury_prone_flag(self, test_db_session):
        """Test setting injury-prone flag"""
        now = datetime.now()
        
        injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Recurring Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=10,
            is_injury_prone_flag=False
        )
        
        test_db_session.add(injury)
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        assert injury.is_injury_prone_flag is False
        
        # Set injury-prone flag
        injury.set_injury_prone_flag()
        await test_db_session.commit()
        await test_db_session.refresh(injury)
        
        assert injury.is_injury_prone_flag is True
    
    @pytest.mark.asyncio
    async def test_query_injuries_by_severity(self, test_db_session):
        """Test querying injuries by severity"""
        now = datetime.now()
        
        # Create injuries with different severities
        minor_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Minor Injury",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=5
        )
        
        moderate_injury = Injury(
            career_id=1,
            player_id=2,
            squad_player_id=2,
            injury_type="Moderate Injury",
            severity=InjurySeverity.MODERATE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=5),
            recovery_weeks=5,
            season=1,
            week=5
        )
        
        severe_injury = Injury(
            career_id=1,
            player_id=3,
            squad_player_id=3,
            injury_type="Severe Injury",
            severity=InjurySeverity.SEVERE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=12),
            recovery_weeks=12,
            season=1,
            week=5
        )
        
        test_db_session.add(minor_injury)
        test_db_session.add(moderate_injury)
        test_db_session.add(severe_injury)
        await test_db_session.commit()
        
        # Query severe injuries
        result = await test_db_session.execute(
            select(Injury).where(Injury.severity == InjurySeverity.SEVERE)
        )
        severe_injuries = result.scalars().all()
        
        assert len(severe_injuries) == 1
        assert severe_injuries[0].injury_type == "Severe Injury"
        assert severe_injuries[0].recovery_weeks == 12
    
    @pytest.mark.asyncio
    async def test_query_injuries_by_status(self, test_db_session):
        """Test querying injuries by status"""
        now = datetime.now()
        
        # Create injuries with different statuses
        active_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Active Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=1,
            week=10
        )
        
        recovering_injury = Injury(
            career_id=1,
            player_id=2,
            squad_player_id=2,
            injury_type="Recovering Injury",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERING,
            injury_date=now - timedelta(weeks=2),
            expected_recovery_date=now,
            recovery_weeks=2,
            season=1,
            week=8
        )
        
        test_db_session.add(active_injury)
        test_db_session.add(recovering_injury)
        await test_db_session.commit()
        
        # Query active injuries
        result = await test_db_session.execute(
            select(Injury).where(Injury.status == InjuryStatus.ACTIVE)
        )
        active_injuries = result.scalars().all()
        
        assert len(active_injuries) == 1
        assert active_injuries[0].injury_type == "Active Injury"
        assert active_injuries[0].is_active() is True
    
    @pytest.mark.asyncio
    async def test_query_injuries_by_career_and_season(self, test_db_session):
        """Test querying injuries by career and season"""
        now = datetime.now()
        
        # Create injuries for different careers and seasons
        career1_season1_injury = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Career 1 Season 1",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=1),
            recovery_weeks=1,
            season=1,
            week=10
        )
        
        career1_season2_injury = Injury(
            career_id=1,
            player_id=2,
            squad_player_id=2,
            injury_type="Career 1 Season 2",
            severity=InjurySeverity.MODERATE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=2,
            week=15
        )
        
        career2_season1_injury = Injury(
            career_id=2,
            player_id=3,
            squad_player_id=3,
            injury_type="Career 2 Season 1",
            severity=InjurySeverity.MINOR,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=2),
            recovery_weeks=2,
            season=1,
            week=20
        )
        
        test_db_session.add(career1_season1_injury)
        test_db_session.add(career1_season2_injury)
        test_db_session.add(career2_season1_injury)
        await test_db_session.commit()
        
        # Query injuries for career 1, season 1
        result = await test_db_session.execute(
            select(Injury).where(
                Injury.career_id == 1,
                Injury.season == 1
            )
        )
        career1_season1_injuries = result.scalars().all()
        
        assert len(career1_season1_injuries) == 1
        assert career1_season1_injuries[0].injury_type == "Career 1 Season 1"
    
    @pytest.mark.asyncio
    async def test_multiple_injuries_same_player(self, test_db_session):
        """Test tracking multiple injuries for the same player"""
        now = datetime.now()
        
        # First injury
        injury1 = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="First Injury",
            severity=InjurySeverity.MINOR,
            status=InjuryStatus.RECOVERED,
            injury_date=now - timedelta(weeks=10),
            expected_recovery_date=now - timedelta(weeks=8),
            recovery_weeks=2,
            season=1,
            week=5
        )
        
        # Second injury
        injury2 = Injury(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            injury_type="Second Injury",
            severity=InjurySeverity.MODERATE,
            status=InjuryStatus.ACTIVE,
            injury_date=now,
            expected_recovery_date=now + timedelta(weeks=4),
            recovery_weeks=4,
            season=1,
            week=15
        )
        
        test_db_session.add(injury1)
        test_db_session.add(injury2)
        await test_db_session.commit()
        
        # Query all injuries for player 1
        result = await test_db_session.execute(
            select(Injury).where(Injury.player_id == 1).order_by(Injury.injury_date)
        )
        player_injuries = result.scalars().all()
        
        assert len(player_injuries) == 2
        assert player_injuries[0].injury_type == "First Injury"
        assert player_injuries[0].status == InjuryStatus.RECOVERED
        assert player_injuries[1].injury_type == "Second Injury"
        assert player_injuries[1].status == InjuryStatus.ACTIVE
