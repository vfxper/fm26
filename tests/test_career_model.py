"""
Unit Tests for Career Model
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.career import Career
from app.models.user import User
from app.models.club import Club


class TestCareerModel:
    """Test suite for Career model"""
    
    @pytest.fixture
    async def test_user(self, test_db_session):
        """Create a test user"""
        user = User(
            telegram_user_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
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
            reputation=70,
            league="Test League",
            country="Test Country"
        )
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        return club
    
    @pytest.mark.asyncio
    async def test_create_career_basic(self, test_db_session, test_user, test_club):
        """Test creating a basic career with required fields"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        assert career.id is not None
        assert career.user_id == test_user.id
        assert career.club_id == test_club.id
        assert career.manager_name == "Test Manager"
        
        # Check default values
        assert career.current_season == 1
        assert career.current_week == 1
        assert career.board_confidence == 50
        assert career.board_objectives is None
        assert career.manager_reputation == 50
        
        # Check default manager attributes
        assert career.tactical_knowledge == 10
        assert career.man_management == 10
        assert career.motivating == 10
        assert career.attacking == 10
        assert career.defending == 10
        assert career.technical == 10
        assert career.mental == 10
        assert career.youth_development == 10
        assert career.board_relations == 10
        
        # Check default career statistics
        assert career.seasons_managed == 0
        assert career.trophies_won == 0
        assert career.matches_won == 0
        assert career.matches_drawn == 0
        assert career.matches_lost == 0
        assert career.total_transfer_spend == 0
        
        # Check timestamps
        assert career.save_timestamp is not None
        assert career.created_at is not None
        assert career.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_career_full(self, test_db_session, test_user, test_club):
        """Test creating a career with all fields specified"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Elite Manager",
            current_season=3,
            current_week=25,
            board_confidence=85,
            board_objectives='{"objectives": ["Win League", "Reach Cup Final"]}',
            manager_reputation=75,
            tactical_knowledge=18,
            man_management=16,
            motivating=17,
            attacking=19,
            defending=15,
            technical=16,
            mental=17,
            youth_development=14,
            board_relations=18,
            seasons_managed=2,
            trophies_won=3,
            matches_won=45,
            matches_drawn=12,
            matches_lost=8,
            total_transfer_spend=50000000
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        assert career.id is not None
        assert career.manager_name == "Elite Manager"
        assert career.current_season == 3
        assert career.current_week == 25
        assert career.board_confidence == 85
        assert career.board_objectives == '{"objectives": ["Win League", "Reach Cup Final"]}'
        assert career.manager_reputation == 75
        assert career.tactical_knowledge == 18
        assert career.man_management == 16
        assert career.motivating == 17
        assert career.attacking == 19
        assert career.defending == 15
        assert career.technical == 16
        assert career.mental == 17
        assert career.youth_development == 14
        assert career.board_relations == 18
        assert career.seasons_managed == 2
        assert career.trophies_won == 3
        assert career.matches_won == 45
        assert career.matches_drawn == 12
        assert career.matches_lost == 8
        assert career.total_transfer_spend == 50000000
    
    @pytest.mark.asyncio
    async def test_career_season_constraint_min(self, test_db_session, test_user, test_club):
        """Test that current_season cannot be less than 1"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_season=0  # Invalid: below minimum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_week_constraint_min(self, test_db_session, test_user, test_club):
        """Test that current_week cannot be less than 1"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_week=0  # Invalid: below minimum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_week_constraint_max(self, test_db_session, test_user, test_club):
        """Test that current_week cannot be greater than 52"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_week=53  # Invalid: above maximum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_board_confidence_constraint_min(self, test_db_session, test_user, test_club):
        """Test that board_confidence cannot be less than 1"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            board_confidence=0  # Invalid: below minimum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_board_confidence_constraint_max(self, test_db_session, test_user, test_club):
        """Test that board_confidence cannot be greater than 100"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            board_confidence=101  # Invalid: above maximum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_manager_reputation_constraint_min(self, test_db_session, test_user, test_club):
        """Test that manager_reputation cannot be less than 1"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            manager_reputation=0  # Invalid: below minimum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_manager_reputation_constraint_max(self, test_db_session, test_user, test_club):
        """Test that manager_reputation cannot be greater than 100"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            manager_reputation=101  # Invalid: above maximum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_manager_attribute_constraint_min(self, test_db_session, test_user, test_club):
        """Test that manager attributes cannot be less than 1"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            tactical_knowledge=0  # Invalid: below minimum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_manager_attribute_constraint_max(self, test_db_session, test_user, test_club):
        """Test that manager attributes cannot be greater than 20"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            man_management=21  # Invalid: above maximum
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_statistics_non_negative(self, test_db_session, test_user, test_club):
        """Test that career statistics cannot be negative"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            matches_won=-1  # Invalid: negative
        )
        
        test_db_session.add(career)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_career_to_dict(self, test_db_session, test_user, test_club):
        """Test converting career to dictionary"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_season=2,
            current_week=15,
            board_confidence=70,
            board_objectives='{"objectives": ["Top 6"]}',
            manager_reputation=65,
            tactical_knowledge=15,
            man_management=14,
            motivating=16,
            attacking=17,
            defending=13,
            technical=14,
            mental=15,
            youth_development=12,
            board_relations=16,
            seasons_managed=1,
            trophies_won=1,
            matches_won=20,
            matches_drawn=8,
            matches_lost=5,
            total_transfer_spend=25000000
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        career_dict = career.to_dict()
        
        assert career_dict["id"] == career.id
        assert career_dict["user_id"] == test_user.id
        assert career_dict["club_id"] == test_club.id
        assert career_dict["manager_name"] == "Test Manager"
        
        assert career_dict["progression"]["current_season"] == 2
        assert career_dict["progression"]["current_week"] == 15
        
        assert career_dict["board"]["confidence"] == 70
        assert career_dict["board"]["objectives"] == '{"objectives": ["Top 6"]}'
        
        assert career_dict["manager"]["reputation"] == 65
        assert career_dict["manager"]["attributes"]["tactical_knowledge"] == 15
        assert career_dict["manager"]["attributes"]["man_management"] == 14
        assert career_dict["manager"]["attributes"]["motivating"] == 16
        assert career_dict["manager"]["attributes"]["attacking"] == 17
        assert career_dict["manager"]["attributes"]["defending"] == 13
        assert career_dict["manager"]["attributes"]["technical"] == 14
        assert career_dict["manager"]["attributes"]["mental"] == 15
        assert career_dict["manager"]["attributes"]["youth_development"] == 12
        assert career_dict["manager"]["attributes"]["board_relations"] == 16
        
        assert career_dict["statistics"]["seasons_managed"] == 1
        assert career_dict["statistics"]["trophies_won"] == 1
        assert career_dict["statistics"]["matches_won"] == 20
        assert career_dict["statistics"]["matches_drawn"] == 8
        assert career_dict["statistics"]["matches_lost"] == 5
        assert career_dict["statistics"]["total_transfer_spend"] == 25000000
        
        assert career_dict["save_timestamp"] is not None
        assert career_dict["created_at"] is not None
        assert career_dict["updated_at"] is not None
    
    @pytest.mark.asyncio
    async def test_career_repr(self, test_db_session, test_user, test_club):
        """Test career string representation"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_season=2,
            current_week=15
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        repr_str = repr(career)
        assert "Career" in repr_str
        assert "Test Manager" in repr_str
        assert str(test_club.id) in repr_str
        assert "2" in repr_str  # season
        assert "15" in repr_str  # week
    
    @pytest.mark.asyncio
    async def test_get_total_matches(self, test_db_session, test_user, test_club):
        """Test calculating total matches played"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            matches_won=20,
            matches_drawn=8,
            matches_lost=5
        )
        
        assert career.get_total_matches() == 33
    
    @pytest.mark.asyncio
    async def test_get_win_percentage(self, test_db_session, test_user, test_club):
        """Test calculating win percentage"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            matches_won=20,
            matches_drawn=8,
            matches_lost=2
        )
        
        win_pct = career.get_win_percentage()
        assert abs(win_pct - 66.67) < 0.1  # 20/30 * 100 = 66.67%
    
    @pytest.mark.asyncio
    async def test_get_win_percentage_no_matches(self, test_db_session, test_user, test_club):
        """Test win percentage when no matches played"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        assert career.get_win_percentage() == 0.0
    
    @pytest.mark.asyncio
    async def test_get_average_manager_attribute(self, test_db_session, test_user, test_club):
        """Test calculating average manager attribute"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            tactical_knowledge=15,
            man_management=14,
            motivating=16,
            attacking=17,
            defending=13,
            technical=14,
            mental=15,
            youth_development=12,
            board_relations=16
        )
        
        avg = career.get_average_manager_attribute()
        expected = (15 + 14 + 16 + 17 + 13 + 14 + 15 + 12 + 16) / 9
        assert abs(avg - expected) < 0.01
    
    @pytest.mark.asyncio
    async def test_is_board_confident(self, test_db_session, test_user, test_club):
        """Test checking if board is confident"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            board_confidence=70
        )
        
        assert career.is_board_confident() is True
        
        career.board_confidence = 60
        assert career.is_board_confident() is True
        
        career.board_confidence = 59
        assert career.is_board_confident() is False
    
    @pytest.mark.asyncio
    async def test_is_under_pressure(self, test_db_session, test_user, test_club):
        """Test checking if manager is under pressure"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            board_confidence=30
        )
        
        assert career.is_under_pressure() is True
        
        career.board_confidence = 39
        assert career.is_under_pressure() is True
        
        career.board_confidence = 40
        assert career.is_under_pressure() is False
    
    @pytest.mark.asyncio
    async def test_update_match_statistics_win(self, test_db_session, test_user, test_club):
        """Test updating match statistics for a win"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        career.update_match_statistics('win')
        assert career.matches_won == 1
        assert career.matches_drawn == 0
        assert career.matches_lost == 0
    
    @pytest.mark.asyncio
    async def test_update_match_statistics_draw(self, test_db_session, test_user, test_club):
        """Test updating match statistics for a draw"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        career.update_match_statistics('draw')
        assert career.matches_won == 0
        assert career.matches_drawn == 1
        assert career.matches_lost == 0
    
    @pytest.mark.asyncio
    async def test_update_match_statistics_loss(self, test_db_session, test_user, test_club):
        """Test updating match statistics for a loss"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        career.update_match_statistics('loss')
        assert career.matches_won == 0
        assert career.matches_drawn == 0
        assert career.matches_lost == 1
    
    @pytest.mark.asyncio
    async def test_add_trophy(self, test_db_session, test_user, test_club):
        """Test adding a trophy"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            trophies_won=2
        )
        
        career.add_trophy()
        assert career.trophies_won == 3
    
    @pytest.mark.asyncio
    async def test_add_transfer_spend(self, test_db_session, test_user, test_club):
        """Test adding to transfer spend"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            total_transfer_spend=10000000
        )
        
        career.add_transfer_spend(5000000)
        assert career.total_transfer_spend == 15000000
    
    @pytest.mark.asyncio
    async def test_advance_week_normal(self, test_db_session, test_user, test_club):
        """Test advancing career by one week"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_season=1,
            current_week=15
        )
        
        career.advance_week()
        assert career.current_week == 16
        assert career.current_season == 1
        assert career.seasons_managed == 0
    
    @pytest.mark.asyncio
    async def test_advance_week_season_rollover(self, test_db_session, test_user, test_club):
        """Test advancing career with season rollover"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            current_season=1,
            current_week=52,
            seasons_managed=0
        )
        
        career.advance_week()
        assert career.current_week == 1
        assert career.current_season == 2
        assert career.seasons_managed == 1
    
    @pytest.mark.asyncio
    async def test_career_foreign_key_user_cascade(self, test_db_session, test_user, test_club):
        """Test that deleting user cascades to career"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        career_id = career.id
        
        # Delete user
        await test_db_session.delete(test_user)
        await test_db_session.commit()
        
        # Career should be deleted due to CASCADE
        result = await test_db_session.execute(
            select(Career).where(Career.id == career_id)
        )
        deleted_career = result.scalar_one_or_none()
        
        assert deleted_career is None
    
    @pytest.mark.asyncio
    async def test_career_query_by_user(self, test_db_session, test_user, test_club):
        """Test querying careers by user"""
        career1 = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Manager 1",
            current_season=1
        )
        career2 = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Manager 2",
            current_season=2
        )
        
        test_db_session.add_all([career1, career2])
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Career).where(Career.user_id == test_user.id)
        )
        user_careers = result.scalars().all()
        
        assert len(user_careers) == 2
        assert all(career.user_id == test_user.id for career in user_careers)
    
    @pytest.mark.asyncio
    async def test_career_query_by_club(self, test_db_session, test_user, test_club):
        """Test querying careers by club"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Career).where(Career.club_id == test_club.id)
        )
        club_careers = result.scalars().all()
        
        assert len(club_careers) == 1
        assert club_careers[0].club_id == test_club.id
    
    @pytest.mark.asyncio
    async def test_career_update(self, test_db_session, test_user, test_club):
        """Test updating career attributes"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager",
            board_confidence=50
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        # Update career
        career.board_confidence = 75
        career.manager_reputation = 80
        await test_db_session.commit()
        await test_db_session.refresh(career)
        
        assert career.board_confidence == 75
        assert career.manager_reputation == 80
    
    @pytest.mark.asyncio
    async def test_career_delete(self, test_db_session, test_user, test_club):
        """Test deleting a career"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="Test Manager"
        )
        
        test_db_session.add(career)
        await test_db_session.commit()
        career_id = career.id
        
        await test_db_session.delete(career)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(Career).where(Career.id == career_id)
        )
        deleted_career = result.scalar_one_or_none()
        
        assert deleted_career is None
