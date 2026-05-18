"""
Tests for Career Service

This module contains unit tests for the career initialization and management service.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.models.user import User
from app.models.club import Club
from app.models.career import Career
# Import all models to ensure they're registered with SQLAlchemy
from app.models import (
    Player, SquadPlayer, Match, MatchEvent, Transfer,
    Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
    Competition, Fixture
)
from app.services.career_service import (
    CareerService,
    UserNotFoundError,
    ClubNotFoundError,
    CareerAlreadyExistsError,
    InvalidManagerNameError,
    CareerServiceError,
    WeekSummary,
    TrainingUpdate,
    FinanceUpdate,
    WeekEvent,
)


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine"""
    # Import all models to ensure they're registered with Base.metadata
    # This must happen before create_all()
    from app.models import (
        User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
        Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
        Competition, Fixture
    )
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session"""
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(session):
    """Create a test user"""
    user = User(
        telegram_user_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en"
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def test_club(session):
    """Create a test club"""
    club = Club(
        name="Test FC",
        reputation=50,
        league="Test League",
        country="Test Country",
        stadium_level=2,
        training_facilities_level=2,
        youth_academy_level=2,
        medical_centre_level=2,
        scouting_network_level=2,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=50000,
        matchday_revenue=100000,
        stadium_capacity=30000,
        stadium_name="Test Stadium"
    )
    session.add(club)
    await session.flush()
    return club


@pytest.fixture
def career_service(session):
    """Create career service instance"""
    return CareerService(session)


class TestCareerInitialization:
    """Tests for career initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_career_success(self, career_service, test_user, test_club, session):
        """Test successful career initialization"""
        # Initialize career
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Verify career was created
        assert career is not None
        assert career.id is not None
        assert career.user_id == test_user.id
        assert career.club_id == test_club.id
        assert career.manager_name == "John Smith"
        
        # Verify initial state
        assert career.current_season == 1
        assert career.current_week == 1
        assert career.board_confidence == 50
        assert career.manager_reputation == 50
        
        # Verify manager attributes (all should be 10)
        assert career.tactical_knowledge == 10
        assert career.man_management == 10
        assert career.motivating == 10
        assert career.attacking == 10
        assert career.defending == 10
        assert career.technical == 10
        assert career.mental == 10
        assert career.youth_development == 10
        assert career.board_relations == 10
        
        # Verify statistics (all should be 0)
        assert career.seasons_managed == 0
        assert career.trophies_won == 0
        assert career.matches_won == 0
        assert career.matches_drawn == 0
        assert career.matches_lost == 0
        assert career.total_transfer_spend == 0
        
        # Verify timestamps
        assert career.created_at is not None
        assert career.updated_at is not None
        assert career.save_timestamp is not None
    
    @pytest.mark.asyncio
    async def test_initialize_career_strips_whitespace(self, career_service, test_user, test_club):
        """Test that manager name whitespace is stripped"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="  John Smith  ",
            club_id=test_club.id
        )
        
        assert career.manager_name == "John Smith"
    
    @pytest.mark.asyncio
    async def test_initialize_career_user_not_found(self, career_service, test_club):
        """Test error when user doesn't exist"""
        with pytest.raises(UserNotFoundError) as exc_info:
            await career_service.initialize_career(
                user_id=99999,  # Non-existent user
                manager_name="John Smith",
                club_id=test_club.id
            )
        
        assert "User with id 99999 not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_club_not_found(self, career_service, test_user):
        """Test error when club doesn't exist"""
        with pytest.raises(ClubNotFoundError) as exc_info:
            await career_service.initialize_career(
                user_id=test_user.id,
                manager_name="John Smith",
                club_id=99999  # Non-existent club
            )
        
        assert "Club with id 99999 not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_empty_manager_name(self, career_service, test_user, test_club):
        """Test error when manager name is empty"""
        with pytest.raises(InvalidManagerNameError) as exc_info:
            await career_service.initialize_career(
                user_id=test_user.id,
                manager_name="",
                club_id=test_club.id
            )
        
        assert "Manager name cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_whitespace_only_manager_name(self, career_service, test_user, test_club):
        """Test error when manager name is only whitespace"""
        with pytest.raises(InvalidManagerNameError) as exc_info:
            await career_service.initialize_career(
                user_id=test_user.id,
                manager_name="   ",
                club_id=test_club.id
            )
        
        assert "Manager name cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_manager_name_too_long(self, career_service, test_user, test_club):
        """Test error when manager name exceeds 255 characters"""
        long_name = "A" * 256
        
        with pytest.raises(InvalidManagerNameError) as exc_info:
            await career_service.initialize_career(
                user_id=test_user.id,
                manager_name=long_name,
                club_id=test_club.id
            )
        
        assert "cannot exceed 255 characters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_already_exists(self, career_service, test_user, test_club):
        """Test error when user already has a career"""
        # Create first career
        await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Try to create second career
        with pytest.raises(CareerAlreadyExistsError) as exc_info:
            await career_service.initialize_career(
                user_id=test_user.id,
                manager_name="Jane Doe",
                club_id=test_club.id
            )
        
        assert "already has an active career" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_career_skip_existing_check(self, career_service, test_user, test_club, session):
        """Test that check_existing=False allows multiple careers"""
        # Create first career
        career1 = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Create second career with check_existing=False
        career2 = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="Jane Doe",
            club_id=test_club.id,
            check_existing=False
        )
        
        # Both careers should exist
        assert career1.id != career2.id
        assert career1.manager_name == "John Smith"
        assert career2.manager_name == "Jane Doe"


class TestCareerRetrieval:
    """Tests for career retrieval methods"""
    
    @pytest.mark.asyncio
    async def test_get_career_by_id_success(self, career_service, test_user, test_club):
        """Test retrieving career by ID"""
        # Create career
        created_career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Retrieve career
        retrieved_career = await career_service.get_career_by_id(created_career.id)
        
        assert retrieved_career is not None
        assert retrieved_career.id == created_career.id
        assert retrieved_career.manager_name == "John Smith"
    
    @pytest.mark.asyncio
    async def test_get_career_by_id_not_found(self, career_service):
        """Test retrieving non-existent career"""
        career = await career_service.get_career_by_id(99999)
        assert career is None
    
    @pytest.mark.asyncio
    async def test_get_user_career_success(self, career_service, test_user, test_club):
        """Test retrieving user's career"""
        # Create career
        created_career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Retrieve user's career
        user_career = await career_service.get_user_career(test_user.id)
        
        assert user_career is not None
        assert user_career.id == created_career.id
        assert user_career.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_user_career_not_found(self, career_service):
        """Test retrieving career for user with no career"""
        career = await career_service.get_user_career(99999)
        assert career is None
    
    @pytest.mark.asyncio
    async def test_get_user_career_returns_latest(self, career_service, test_user, test_club):
        """Test that get_user_career returns the most recent career"""
        # Create two careers (with check_existing=False)
        career1 = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="First Manager",
            club_id=test_club.id,
            check_existing=False
        )
        
        career2 = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="Second Manager",
            club_id=test_club.id,
            check_existing=False
        )
        
        # Get user's career (should be the latest one)
        user_career = await career_service.get_user_career(test_user.id)
        
        assert user_career is not None
        assert user_career.id == career2.id
        assert user_career.manager_name == "Second Manager"


class TestCareerSummary:
    """Tests for career summary generation"""
    
    @pytest.mark.asyncio
    async def test_get_career_summary_success(self, career_service, test_user, test_club):
        """Test generating career summary"""
        # Create career
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Get summary
        summary = await career_service.get_career_summary(career.id)
        
        # Verify summary structure
        assert summary['career_id'] == career.id
        assert summary['manager_name'] == "John Smith"
        assert summary['club_id'] == test_club.id
        assert summary['club_name'] == "Test FC"
        assert summary['club_reputation'] == 50
        assert summary['user_id'] == test_user.id
        assert summary['telegram_user_id'] == 123456789
        assert summary['current_season'] == 1
        assert summary['current_week'] == 1
        assert summary['board_confidence'] == 50
        assert summary['manager_reputation'] == 50
        
        # Verify manager attributes
        assert 'manager_attributes' in summary
        assert summary['manager_attributes']['tactical_knowledge'] == 10
        assert summary['manager_attributes']['average'] == 10.0
        
        # Verify statistics
        assert 'statistics' in summary
        assert summary['statistics']['seasons_managed'] == 0
        assert summary['statistics']['total_matches'] == 0
        assert summary['statistics']['win_percentage'] == 0.0
        
        # Verify board status
        assert 'board_status' in summary
        assert summary['board_status']['is_confident'] == False
        assert summary['board_status']['is_under_pressure'] == False
        
        # Verify timestamps
        assert summary['created_at'] is not None
        assert summary['updated_at'] is not None
        assert summary['save_timestamp'] is not None
    
    @pytest.mark.asyncio
    async def test_get_career_summary_not_found(self, career_service):
        """Test error when career doesn't exist"""
        with pytest.raises(CareerServiceError) as exc_info:
            await career_service.get_career_summary(99999)
        
        assert "Career 99999 not found" in str(exc_info.value)


class TestCareerModelMethods:
    """Tests for Career model helper methods"""
    
    @pytest.mark.asyncio
    async def test_career_get_total_matches(self, career_service, test_user, test_club):
        """Test get_total_matches method"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Initially 0
        assert career.get_total_matches() == 0
        
        # Update statistics
        career.matches_won = 10
        career.matches_drawn = 5
        career.matches_lost = 3
        
        assert career.get_total_matches() == 18
    
    @pytest.mark.asyncio
    async def test_career_get_win_percentage(self, career_service, test_user, test_club):
        """Test get_win_percentage method"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Initially 0 (no matches)
        assert career.get_win_percentage() == 0.0
        
        # Update statistics
        career.matches_won = 10
        career.matches_drawn = 5
        career.matches_lost = 5
        
        # 10 wins out of 20 matches = 50%
        assert career.get_win_percentage() == 50.0
    
    @pytest.mark.asyncio
    async def test_career_get_average_manager_attribute(self, career_service, test_user, test_club):
        """Test get_average_manager_attribute method"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Initially all 10
        assert career.get_average_manager_attribute() == 10.0
        
        # Update some attributes
        career.tactical_knowledge = 15
        career.attacking = 12
        career.defending = 8
        
        # Average of (15, 10, 10, 12, 8, 10, 10, 10, 10) = 10.555...
        avg = career.get_average_manager_attribute()
        assert 10.5 < avg < 10.6
    
    @pytest.mark.asyncio
    async def test_career_is_board_confident(self, career_service, test_user, test_club):
        """Test is_board_confident method"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Initially 50 (not confident)
        assert career.is_board_confident() == False
        
        # Set to 60 (confident)
        career.board_confidence = 60
        assert career.is_board_confident() == True
        
        # Set to 59 (not confident)
        career.board_confidence = 59
        assert career.is_board_confident() == False
    
    @pytest.mark.asyncio
    async def test_career_is_under_pressure(self, career_service, test_user, test_club):
        """Test is_under_pressure method"""
        career = await career_service.initialize_career(
            user_id=test_user.id,
            manager_name="John Smith",
            club_id=test_club.id
        )
        
        # Initially 50 (not under pressure)
        assert career.is_under_pressure() == False
        
        # Set to 39 (under pressure)
        career.board_confidence = 39
        assert career.is_under_pressure() == True
        
        # Set to 40 (not under pressure)
        career.board_confidence = 40
        assert career.is_under_pressure() == False


class TestAdvanceWeek:
    """Tests for the advance_week method using mocked sessions"""

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 1
        career.current_week = 1
        career.board_confidence = 50
        career.manager_reputation = 50
        career.save_timestamp = None

        # Make advance_week actually modify the mock
        def advance_week_side_effect():
            career.current_week += 1
            if career.current_week > 52:
                career.current_week = 1
                career.current_season += 1
                career.seasons_managed += 1

        career.advance_week = MagicMock(side_effect=advance_week_side_effect)
        return career

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock, MagicMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_advance_week_increments_week(self, mock_session, mock_career):
        """Test that advance_week increments the week counter"""
        from unittest.mock import AsyncMock, patch

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.season == 1
        assert summary.week == 2
        assert summary.previous_season == 1
        assert summary.previous_week == 1
        assert summary.season_changed is False
        mock_career.advance_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_advance_week_season_rollover(self, mock_session, mock_career):
        """Test that advancing past week 52 rolls over to next season"""
        from unittest.mock import AsyncMock

        mock_career.current_week = 52
        mock_career.current_season = 1

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.season == 2
        assert summary.week == 1
        assert summary.previous_season == 1
        assert summary.previous_week == 52
        assert summary.season_changed is True

    @pytest.mark.asyncio
    async def test_advance_week_returns_week_summary(self, mock_session, mock_career):
        """Test that advance_week returns a properly structured WeekSummary"""
        from unittest.mock import AsyncMock

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert isinstance(summary, WeekSummary)
        assert isinstance(summary.matches, list)
        assert isinstance(summary.training, TrainingUpdate)
        assert isinstance(summary.aged_players, list)
        assert isinstance(summary.finances, FinanceUpdate)
        assert isinstance(summary.contract_notifications, list)
        assert isinstance(summary.events, list)
        assert isinstance(summary.board_confidence_change, int)
        assert isinstance(summary.new_board_confidence, int)

    @pytest.mark.asyncio
    async def test_advance_week_career_not_found(self, mock_session):
        """Test that advance_week raises error for non-existent career"""
        from unittest.mock import AsyncMock

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=None)

        with pytest.raises(CareerServiceError) as exc_info:
            await service.advance_week(99999)

        assert "Career 99999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_advance_week_stubs_return_defaults(self, mock_session, mock_career):
        """Test that stub subsystems return sensible defaults"""
        from unittest.mock import AsyncMock

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        # Matches stub returns empty list
        assert summary.matches == []

        # Training stub returns default values
        assert summary.training.players_trained == 0
        assert summary.training.focus_area == "General"
        assert summary.training.improvement_points == 0

        # Aging stub returns empty list
        assert summary.aged_players == []

        # Finance stub returns zero changes
        assert summary.finances.income == 0
        assert summary.finances.expenditure == 0
        assert summary.finances.balance_change == 0

        # Contract notifications stub returns empty list
        assert summary.contract_notifications == []

    @pytest.mark.asyncio
    async def test_advance_week_board_confidence_stays_in_bounds(self, mock_session, mock_career):
        """Test that board confidence stays within 1-100 bounds after advance"""
        from unittest.mock import AsyncMock

        mock_career.board_confidence = 1

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.new_board_confidence >= 1
        assert summary.new_board_confidence <= 100

    @pytest.mark.asyncio
    async def test_advance_week_board_confidence_upper_bound(self, mock_session, mock_career):
        """Test that board confidence doesn't exceed 100"""
        from unittest.mock import AsyncMock

        mock_career.board_confidence = 100

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.new_board_confidence <= 100
        assert summary.new_board_confidence >= 1

    @pytest.mark.asyncio
    async def test_advance_week_multiple_weeks(self, mock_session, mock_career):
        """Test advancing multiple weeks in sequence"""
        from unittest.mock import AsyncMock

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        # Advance 5 weeks
        for i in range(5):
            summary = await service.advance_week(mock_career.id)

        assert summary.week == 6
        assert summary.season == 1

    @pytest.mark.asyncio
    async def test_advance_week_events_are_valid(self, mock_session, mock_career):
        """Test that generated events have valid structure"""
        from unittest.mock import AsyncMock
        import random

        # Seed random for deterministic event generation
        random.seed(42)

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        # Run many weeks to get some events
        all_events = []
        for _ in range(50):
            summary = await service.advance_week(mock_career.id)
            all_events.extend(summary.events)

        # With seed 42 and 50 weeks, we should get some events
        assert len(all_events) > 0

        for event in all_events:
            assert isinstance(event, WeekEvent)
            assert event.event_type in ("injury", "media", "board_message")
            assert isinstance(event.description, str)
            assert len(event.description) > 0
            assert isinstance(event.impact, dict)

    @pytest.mark.asyncio
    async def test_advance_week_updates_save_timestamp(self, mock_session, mock_career):
        """Test that advance_week updates the save timestamp"""
        from unittest.mock import AsyncMock

        mock_career.save_timestamp = None

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        await service.advance_week(mock_career.id)

        # save_timestamp should have been set
        assert mock_career.save_timestamp is not None

    @pytest.mark.asyncio
    async def test_advance_week_flush_failure_raises_error(self, mock_session, mock_career):
        """Test that a flush failure raises CareerServiceError"""
        from unittest.mock import AsyncMock

        mock_session.flush = AsyncMock(side_effect=Exception("DB connection lost"))

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        with pytest.raises(CareerServiceError) as exc_info:
            await service.advance_week(mock_career.id)

        assert "Failed to advance week" in str(exc_info.value)


class TestBoardObjectives:
    """Tests for the board objectives system"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 1
        career.current_week = 1
        career.board_confidence = 50
        career.board_objectives = None
        return career

    @pytest.mark.asyncio
    async def test_generate_objectives_top_club(self, mock_session):
        """Test that top clubs (rep 70+) get hard objectives"""
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)
        objectives = service.generate_board_objectives(
            club_reputation=80,
            current_league_position=3,
            season_number=1,
        )

        assert len(objectives) >= 2
        # Top clubs should have "Win the league" as primary
        league_obj = [o for o in objectives if o.objective_type == "league_position"]
        assert len(league_obj) == 1
        assert league_obj[0].target_value == 1
        assert league_obj[0].priority == "primary"
        assert "Win the league" in league_obj[0].description

        # Should have cup objectives
        cup_objs = [o for o in objectives if o.objective_type == "cup_progress"]
        assert len(cup_objs) >= 1

    @pytest.mark.asyncio
    async def test_generate_objectives_mid_club(self, mock_session):
        """Test that mid clubs (rep 40-69) get moderate objectives"""
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)
        objectives = service.generate_board_objectives(
            club_reputation=55,
            current_league_position=10,
            season_number=1,
        )

        assert len(objectives) >= 2
        # Mid clubs should have "Finish in the top half"
        league_obj = [o for o in objectives if o.objective_type == "league_position"]
        assert len(league_obj) == 1
        assert league_obj[0].target_value == 10
        assert "top half" in league_obj[0].description

        # Should have youth development objective
        youth_objs = [o for o in objectives if o.objective_type == "youth_development"]
        assert len(youth_objs) == 1

    @pytest.mark.asyncio
    async def test_generate_objectives_low_club(self, mock_session):
        """Test that low clubs (rep <40) get survival objectives"""
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)
        objectives = service.generate_board_objectives(
            club_reputation=25,
            current_league_position=18,
            season_number=1,
        )

        assert len(objectives) >= 2
        # Low clubs should have "Avoid relegation"
        league_obj = [o for o in objectives if o.objective_type == "league_position"]
        assert len(league_obj) == 1
        assert league_obj[0].target_value == 17
        assert "relegation" in league_obj[0].description.lower()

        # Should have financial objective
        fin_objs = [o for o in objectives if o.objective_type == "financial"]
        assert len(fin_objs) >= 1

    @pytest.mark.asyncio
    async def test_generate_objectives_extra_objective_later_seasons(self, mock_session):
        """Test that later seasons add extra objectives for mid+ clubs"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)

        # Season 1 - no extra objective
        objectives_s1 = service.generate_board_objectives(
            club_reputation=55,
            current_league_position=10,
            season_number=1,
        )

        # Season 3 - should have extra objective
        objectives_s3 = service.generate_board_objectives(
            club_reputation=55,
            current_league_position=10,
            season_number=3,
        )

        assert len(objectives_s3) > len(objectives_s1)

    @pytest.mark.asyncio
    async def test_evaluate_objectives_league_position_met(self, mock_session, mock_career):
        """Test evaluating objectives when league position target is met"""
        import json
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)

        # Set up objectives in career
        objectives = [
            BoardObjective(
                objective_type="league_position",
                description="Finish in the top half",
                target_value=10,
                priority="primary",
            )
        ]
        mock_career.board_objectives = json.dumps([o.to_dict() for o in objectives])

        # Evaluate with position 5 (better than target 10)
        result = service.evaluate_objectives(
            career=mock_career,
            current_league_position=5,
        )

        assert len(result) == 1
        assert result[0].is_met is True
        assert result[0].current_value == 5

    @pytest.mark.asyncio
    async def test_evaluate_objectives_league_position_not_met(self, mock_session, mock_career):
        """Test evaluating objectives when league position target is not met"""
        import json
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)

        objectives = [
            BoardObjective(
                objective_type="league_position",
                description="Finish in the top half",
                target_value=10,
                priority="primary",
            )
        ]
        mock_career.board_objectives = json.dumps([o.to_dict() for o in objectives])

        # Evaluate with position 15 (worse than target 10)
        result = service.evaluate_objectives(
            career=mock_career,
            current_league_position=15,
        )

        assert len(result) == 1
        assert result[0].is_met is False
        assert result[0].current_value == 15

    @pytest.mark.asyncio
    async def test_evaluate_objectives_cup_progress(self, mock_session, mock_career):
        """Test evaluating cup progress objectives"""
        import json
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)

        objectives = [
            BoardObjective(
                objective_type="cup_progress",
                description="Reach the cup quarter-final",
                target_value=3,
                priority="secondary",
            )
        ]
        mock_career.board_objectives = json.dumps([o.to_dict() for o in objectives])

        # Reached round 4 (semi-final) - exceeds target
        result = service.evaluate_objectives(
            career=mock_career,
            current_league_position=10,
            cup_round_reached=4,
        )

        assert result[0].is_met is True
        assert result[0].current_value == 4

    @pytest.mark.asyncio
    async def test_evaluate_objectives_empty(self, mock_session, mock_career):
        """Test evaluating when no objectives are set"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = None

        result = service.evaluate_objectives(
            career=mock_career,
            current_league_position=10,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_set_season_objectives_stores_json(self, mock_session, mock_career):
        """Test that set_season_objectives stores objectives as JSON"""
        import json
        from app.services.career_service import CareerService, BoardObjective

        service = CareerService(mock_session)

        objectives = service.set_season_objectives(
            career=mock_career,
            club_reputation=55,
            current_league_position=10,
        )

        # Verify objectives were returned
        assert len(objectives) >= 2

        # Verify JSON was stored in career.board_objectives
        assert mock_career.board_objectives is not None
        stored_data = json.loads(mock_career.board_objectives)
        assert isinstance(stored_data, list)
        assert len(stored_data) == len(objectives)

        # Verify stored data can be deserialized back
        for item in stored_data:
            obj = BoardObjective.from_dict(item)
            assert obj.objective_type in ("league_position", "cup_progress", "youth_development", "financial")
            assert obj.description != ""

    @pytest.mark.asyncio
    async def test_board_objective_serialization_roundtrip(self, mock_session):
        """Test that BoardObjective can be serialized and deserialized"""
        from app.services.career_service import BoardObjective

        original = BoardObjective(
            objective_type="league_position",
            description="Win the league",
            target_value=1,
            current_value=3,
            is_met=False,
            priority="primary",
        )

        # Serialize to dict and back
        data = original.to_dict()
        restored = BoardObjective.from_dict(data)

        assert restored.objective_type == original.objective_type
        assert restored.description == original.description
        assert restored.target_value == original.target_value
        assert restored.current_value == original.current_value
        assert restored.is_met == original.is_met
        assert restored.priority == original.priority


class TestManagerReputation:
    """Tests for the manager reputation system"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing reputation"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 1
        career.current_week = 1
        career.board_confidence = 50
        career.manager_reputation = 50
        career.save_timestamp = None

        # Make advance_week actually modify the mock
        def advance_week_side_effect():
            career.current_week += 1
            if career.current_week > 52:
                career.current_week = 1
                career.current_season += 1
                career.seasons_managed += 1

        career.advance_week = MagicMock(side_effect=advance_week_side_effect)
        return career

    # --- Tests for calculate_reputation_change ---

    def test_calculate_reputation_change_match_win(self, mock_session):
        """Test that match_win gives +1 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("match_win") == 1

    def test_calculate_reputation_change_match_draw(self, mock_session):
        """Test that match_draw gives 0 reputation change"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("match_draw") == 0

    def test_calculate_reputation_change_match_loss(self, mock_session):
        """Test that match_loss gives -1 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("match_loss") == -1

    def test_calculate_reputation_change_trophy_won_minor(self, mock_session):
        """Test that minor trophy gives +5 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("trophy_won", trophy_importance=1) == 5

    def test_calculate_reputation_change_trophy_won_major(self, mock_session):
        """Test that major trophy gives +7 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("trophy_won", trophy_importance=2) == 7

    def test_calculate_reputation_change_trophy_won_top(self, mock_session):
        """Test that top trophy gives +10 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("trophy_won", trophy_importance=3) == 10

    def test_calculate_reputation_change_trophy_won_default(self, mock_session):
        """Test that trophy_won without importance defaults to +5"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("trophy_won") == 5

    def test_calculate_reputation_change_objectives_met(self, mock_session):
        """Test that objectives_met gives +3 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("objectives_met") == 3

    def test_calculate_reputation_change_objectives_failed(self, mock_session):
        """Test that objectives_failed gives -3 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("objectives_failed") == -3

    def test_calculate_reputation_change_season_end_overperform(self, mock_session):
        """Test that season_end_overperform gives +5 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("season_end_overperform") == 5

    def test_calculate_reputation_change_season_end_underperform(self, mock_session):
        """Test that season_end_underperform gives -5 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("season_end_underperform") == -5

    def test_calculate_reputation_change_promoted(self, mock_session):
        """Test that promoted gives +8 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("promoted") == 8

    def test_calculate_reputation_change_relegated(self, mock_session):
        """Test that relegated gives -10 reputation"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("relegated") == -10

    def test_calculate_reputation_change_unknown_event(self, mock_session):
        """Test that unknown event type gives 0 reputation change"""
        service = CareerService(mock_session)
        assert service.calculate_reputation_change("unknown_event") == 0

    # --- Tests for update_manager_reputation ---

    @pytest.mark.asyncio
    async def test_reputation_increases_on_win(self, mock_session, mock_career):
        """Test that reputation increases when a match is won"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        change = await service.update_manager_reputation(mock_career, "match_win")

        assert change == 1
        assert mock_career.manager_reputation == 51

    @pytest.mark.asyncio
    async def test_reputation_decreases_on_loss(self, mock_session, mock_career):
        """Test that reputation decreases when a match is lost"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        change = await service.update_manager_reputation(mock_career, "match_loss")

        assert change == -1
        assert mock_career.manager_reputation == 49

    @pytest.mark.asyncio
    async def test_reputation_stays_at_minimum_1(self, mock_session, mock_career):
        """Test that reputation never goes below 1"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 1

        change = await service.update_manager_reputation(mock_career, "match_loss")

        assert change == 0
        assert mock_career.manager_reputation == 1

    @pytest.mark.asyncio
    async def test_reputation_stays_at_maximum_100(self, mock_session, mock_career):
        """Test that reputation never exceeds 100"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 100

        change = await service.update_manager_reputation(mock_career, "match_win")

        assert change == 0
        assert mock_career.manager_reputation == 100

    @pytest.mark.asyncio
    async def test_reputation_clamped_at_lower_bound_with_big_loss(self, mock_session, mock_career):
        """Test that a large negative change is clamped to keep reputation >= 1"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 5

        change = await service.update_manager_reputation(mock_career, "relegated")

        # relegated = -10, but 5 - 10 = -5 which clamps to 1
        assert mock_career.manager_reputation == 1
        assert change == -4  # actual change is only -4 (from 5 to 1)

    @pytest.mark.asyncio
    async def test_reputation_clamped_at_upper_bound_with_big_gain(self, mock_session, mock_career):
        """Test that a large positive change is clamped to keep reputation <= 100"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 95

        change = await service.update_manager_reputation(mock_career, "trophy_won", trophy_importance=3)

        # trophy_won importance 3 = +10, but 95 + 10 = 105 which clamps to 100
        assert mock_career.manager_reputation == 100
        assert change == 5  # actual change is only +5 (from 95 to 100)

    @pytest.mark.asyncio
    async def test_trophy_gives_big_reputation_boost(self, mock_session, mock_career):
        """Test that winning a trophy gives a significant reputation boost"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        change = await service.update_manager_reputation(mock_career, "trophy_won", trophy_importance=3)

        assert change == 10
        assert mock_career.manager_reputation == 60

    # --- Tests for _update_manager_reputation (weekly integration) ---

    @pytest.mark.asyncio
    async def test_weekly_reputation_update_with_wins(self, mock_session, mock_career):
        """Test that weekly reputation update processes wins correctly"""
        from app.services.career_service import MatchResult

        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        matches = [
            MatchResult(match_id=1, opponent="Team A", score_home=2, score_away=1, result="win"),
            MatchResult(match_id=2, opponent="Team B", score_home=3, score_away=0, result="win"),
        ]

        total_change = await service._update_manager_reputation(mock_career, matches)

        assert total_change == 2
        assert mock_career.manager_reputation == 52

    @pytest.mark.asyncio
    async def test_weekly_reputation_update_with_losses(self, mock_session, mock_career):
        """Test that weekly reputation update processes losses correctly"""
        from app.services.career_service import MatchResult

        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        matches = [
            MatchResult(match_id=1, opponent="Team A", score_home=0, score_away=2, result="loss"),
            MatchResult(match_id=2, opponent="Team B", score_home=1, score_away=3, result="loss"),
        ]

        total_change = await service._update_manager_reputation(mock_career, matches)

        assert total_change == -2
        assert mock_career.manager_reputation == 48

    @pytest.mark.asyncio
    async def test_weekly_reputation_update_no_matches(self, mock_session, mock_career):
        """Test that no matches means no reputation change"""
        service = CareerService(mock_session)
        mock_career.manager_reputation = 50

        total_change = await service._update_manager_reputation(mock_career, [])

        assert total_change == 0
        assert mock_career.manager_reputation == 50

    @pytest.mark.asyncio
    async def test_advance_week_calls_reputation_update(self, mock_session, mock_career):
        """Test that advance_week integrates reputation update"""
        from unittest.mock import AsyncMock

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        # With no matches (stub returns []), reputation should stay the same
        mock_career.manager_reputation = 50
        await service.advance_week(mock_career.id)

        # Reputation should remain 50 since no matches were played
        assert mock_career.manager_reputation == 50


class TestManagerAttributeProgression:
    """Tests for the manager attribute progression system"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing attribute progression"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        # Set all attributes to 10 (default)
        career.tactical_knowledge = 10
        career.man_management = 10
        career.motivating = 10
        career.attacking = 10
        career.defending = 10
        career.technical = 10
        career.mental = 10
        career.youth_development = 10
        career.board_relations = 10
        return career

    # --- Tests for progress_manager_attribute ---

    def test_progress_attribute_increases(self, mock_session, mock_career):
        """Test that an attribute increases correctly"""
        service = CareerService(mock_session)
        change = service.progress_manager_attribute(mock_career, "tactical_knowledge", 1)
        assert change == 1
        assert mock_career.tactical_knowledge == 11

    def test_progress_attribute_decreases(self, mock_session, mock_career):
        """Test that an attribute decreases correctly"""
        service = CareerService(mock_session)
        change = service.progress_manager_attribute(mock_career, "attacking", -2)
        assert change == -2
        assert mock_career.attacking == 8

    def test_progress_attribute_clamped_at_max_20(self, mock_session, mock_career):
        """Test that attribute is clamped at maximum 20"""
        service = CareerService(mock_session)
        mock_career.tactical_knowledge = 19
        change = service.progress_manager_attribute(mock_career, "tactical_knowledge", 3)
        assert change == 1  # Only +1 applied (19 -> 20)
        assert mock_career.tactical_knowledge == 20

    def test_progress_attribute_clamped_at_min_1(self, mock_session, mock_career):
        """Test that attribute is clamped at minimum 1"""
        service = CareerService(mock_session)
        mock_career.defending = 2
        change = service.progress_manager_attribute(mock_career, "defending", -5)
        assert change == -1  # Only -1 applied (2 -> 1)
        assert mock_career.defending == 1

    def test_progress_attribute_already_at_max(self, mock_session, mock_career):
        """Test that no change when attribute is already at 20"""
        service = CareerService(mock_session)
        mock_career.mental = 20
        change = service.progress_manager_attribute(mock_career, "mental", 1)
        assert change == 0
        assert mock_career.mental == 20

    def test_progress_attribute_already_at_min(self, mock_session, mock_career):
        """Test that no change when attribute is already at 1"""
        service = CareerService(mock_session)
        mock_career.technical = 1
        change = service.progress_manager_attribute(mock_career, "technical", -1)
        assert change == 0
        assert mock_career.technical == 1

    def test_progress_attribute_invalid_name_raises_error(self, mock_session, mock_career):
        """Test that invalid attribute name raises ValueError"""
        service = CareerService(mock_session)
        with pytest.raises(ValueError) as exc_info:
            service.progress_manager_attribute(mock_career, "invalid_attribute", 1)
        assert "Invalid attribute name" in str(exc_info.value)

    def test_progress_attribute_zero_change(self, mock_session, mock_career):
        """Test that zero change returns 0 and doesn't modify attribute"""
        service = CareerService(mock_session)
        change = service.progress_manager_attribute(mock_career, "motivating", 0)
        assert change == 0
        assert mock_career.motivating == 10

    # --- Tests for process_achievement_progression ---

    def test_achievement_league_win(self, mock_session, mock_career):
        """Test league_win increases tactical_knowledge and motivating"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "league_win")
        assert changes == {"tactical_knowledge": 1, "motivating": 1}
        assert mock_career.tactical_knowledge == 11
        assert mock_career.motivating == 11

    def test_achievement_cup_win(self, mock_session, mock_career):
        """Test cup_win increases man_management and mental"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "cup_win")
        assert changes == {"man_management": 1, "mental": 1}
        assert mock_career.man_management == 11
        assert mock_career.mental == 11

    def test_achievement_continental_win(self, mock_session, mock_career):
        """Test continental_win increases tactical_knowledge, attacking, defending"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "continental_win")
        assert changes == {"tactical_knowledge": 1, "attacking": 1, "defending": 1}
        assert mock_career.tactical_knowledge == 11
        assert mock_career.attacking == 11
        assert mock_career.defending == 11

    def test_achievement_season_top_scorer(self, mock_session, mock_career):
        """Test season_top_scorer increases attacking"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "season_top_scorer")
        assert changes == {"attacking": 1}
        assert mock_career.attacking == 11

    def test_achievement_season_best_defense(self, mock_session, mock_career):
        """Test season_best_defense increases defending"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "season_best_defense")
        assert changes == {"defending": 1}
        assert mock_career.defending == 11

    def test_achievement_youth_player_promoted(self, mock_session, mock_career):
        """Test youth_player_promoted increases youth_development"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "youth_player_promoted")
        assert changes == {"youth_development": 1}
        assert mock_career.youth_development == 11

    def test_achievement_board_objectives_met(self, mock_session, mock_career):
        """Test board_objectives_met increases board_relations"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "board_objectives_met")
        assert changes == {"board_relations": 1}
        assert mock_career.board_relations == 11

    def test_achievement_unbeaten_run_10(self, mock_session, mock_career):
        """Test unbeaten_run_10 increases motivating and mental"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "unbeaten_run_10")
        assert changes == {"motivating": 1, "mental": 1}
        assert mock_career.motivating == 11
        assert mock_career.mental == 11

    def test_achievement_transfer_profit(self, mock_session, mock_career):
        """Test transfer_profit increases technical"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "transfer_profit")
        assert changes == {"technical": 1}
        assert mock_career.technical == 11

    def test_achievement_unknown_returns_empty(self, mock_session, mock_career):
        """Test that unknown achievement returns empty dict"""
        service = CareerService(mock_session)
        changes = service.process_achievement_progression(mock_career, "unknown_achievement")
        assert changes == {}

    def test_achievement_clamped_at_max(self, mock_session, mock_career):
        """Test that achievement progression is clamped at 20"""
        service = CareerService(mock_session)
        mock_career.tactical_knowledge = 20
        mock_career.motivating = 20
        changes = service.process_achievement_progression(mock_career, "league_win")
        # Both are already at 20, so no changes applied
        assert changes == {}

    def test_multiple_achievements_stack(self, mock_session, mock_career):
        """Test that multiple achievements stack correctly"""
        service = CareerService(mock_session)
        # league_win: tactical_knowledge +1, motivating +1
        changes1 = service.process_achievement_progression(mock_career, "league_win")
        # cup_win: man_management +1, mental +1
        changes2 = service.process_achievement_progression(mock_career, "cup_win")
        # continental_win: tactical_knowledge +1, attacking +1, defending +1
        changes3 = service.process_achievement_progression(mock_career, "continental_win")

        assert mock_career.tactical_knowledge == 12  # +1 +1
        assert mock_career.motivating == 11  # +1
        assert mock_career.man_management == 11  # +1
        assert mock_career.mental == 11  # +1
        assert mock_career.attacking == 11  # +1
        assert mock_career.defending == 11  # +1

    # --- Tests for process_season_end_progression ---

    def test_season_end_with_achievements(self, mock_session, mock_career):
        """Test season-end progression with multiple achievements"""
        import random
        random.seed(999)  # Seed to avoid random progression in this test

        service = CareerService(mock_session)
        achievements = ["league_win", "season_top_scorer"]
        changes = service.process_season_end_progression(mock_career, achievements)

        # league_win: tactical_knowledge +1, motivating +1
        # season_top_scorer: attacking +1
        assert "tactical_knowledge" in changes
        assert "motivating" in changes
        assert "attacking" in changes
        assert mock_career.tactical_knowledge == 11
        assert mock_career.motivating == 11
        assert mock_career.attacking == 11

    def test_season_end_empty_achievements(self, mock_session, mock_career):
        """Test season-end progression with no achievements"""
        import random
        random.seed(999)  # Seed to avoid random progression

        service = CareerService(mock_session)
        changes = service.process_season_end_progression(mock_career, [])

        # With seed 999, random.random() should not trigger 20% chance
        # (depends on seed, but we verify no achievement-based changes)
        # All attributes should remain at 10 unless random triggers
        for attr in CareerService.VALID_MANAGER_ATTRIBUTES:
            val = getattr(mock_career, attr)
            assert val >= 10  # Could be 11 if random triggered

    def test_season_end_random_progression_triggers(self, mock_session, mock_career):
        """Test that random progression can trigger (20% chance)"""
        import random
        # Find a seed where random.random() < 0.20
        # We'll try a few seeds to find one that triggers
        triggered = False
        for seed in range(100):
            random.seed(seed)
            if random.random() < 0.20:
                # This seed triggers random progression
                random.seed(seed)  # Reset seed
                service = CareerService(mock_session)
                # Reset attributes
                for attr in CareerService.VALID_MANAGER_ATTRIBUTES:
                    setattr(mock_career, attr, 10)
                changes = service.process_season_end_progression(mock_career, [])
                # Should have exactly one random attribute increased
                assert len(changes) == 1
                attr_changed = list(changes.keys())[0]
                assert attr_changed in CareerService.VALID_MANAGER_ATTRIBUTES
                assert changes[attr_changed] == 1
                triggered = True
                break

        assert triggered, "Could not find a seed that triggers random progression"

    def test_season_end_random_progression_does_not_trigger(self, mock_session, mock_career):
        """Test that random progression doesn't always trigger"""
        import random
        # Find a seed where random.random() >= 0.20
        not_triggered = False
        for seed in range(100):
            random.seed(seed)
            if random.random() >= 0.20:
                # This seed does NOT trigger random progression
                random.seed(seed)  # Reset seed
                service = CareerService(mock_session)
                changes = service.process_season_end_progression(mock_career, [])
                assert changes == {}
                not_triggered = True
                break

        assert not_triggered, "Could not find a seed that doesn't trigger random progression"

    def test_season_end_duplicate_achievements(self, mock_session, mock_career):
        """Test that duplicate achievements stack"""
        import random
        random.seed(999)

        service = CareerService(mock_session)
        # Two league wins in same season (unlikely but valid)
        achievements = ["league_win", "league_win"]
        changes = service.process_season_end_progression(mock_career, achievements)

        # Each league_win: tactical_knowledge +1, motivating +1
        assert mock_career.tactical_knowledge == 12
        assert mock_career.motivating == 12


class TestSackingEvent:
    """Tests for the sacking event logic"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for sacking tests"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 3
        career.current_week = 20
        career.board_confidence = 50
        career.manager_reputation = 50
        career.board_objectives = None
        career.seasons_managed = 2
        career.trophies_won = 0
        career.matches_won = 30
        career.matches_drawn = 10
        career.matches_lost = 20
        career.total_transfer_spend = 5000000
        return career

    def test_check_sacking_no_conditions_met(self, mock_session, mock_career):
        """Test no sacking when conditions aren't met"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 50
        mock_career.board_objectives = None

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=0
        )

        assert result["should_sack"] is False
        assert result["reason"] == ""
        assert result["severity"] == "none"

    def test_check_sacking_low_confidence_not_enough_weeks(self, mock_session, mock_career):
        """Test no sacking when confidence is low but not for long enough"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 15

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=3
        )

        assert result["should_sack"] is False

    def test_check_sacking_low_confidence_triggers(self, mock_session, mock_career):
        """Test sacking triggers when board confidence < 20 for 4+ weeks"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 15

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=4
        )

        assert result["should_sack"] is True
        assert "critically low" in result["reason"]
        assert "15%" in result["reason"]
        assert "4 consecutive weeks" in result["reason"]
        assert result["severity"] == "critical"

    def test_check_sacking_low_confidence_extended_period(self, mock_session, mock_career):
        """Test sacking triggers with extended low confidence period"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 5

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=8
        )

        assert result["should_sack"] is True
        assert result["severity"] == "critical"

    def test_check_sacking_confidence_at_threshold_no_sack(self, mock_session, mock_career):
        """Test no sacking when confidence is exactly at threshold"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 20  # At threshold, not below

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=10
        )

        assert result["should_sack"] is False

    def test_check_sacking_failed_objectives_two_seasons(self, mock_session, mock_career):
        """Test sacking triggers when objectives failed 2 consecutive seasons"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 50  # Not low enough for confidence sacking

        # Two seasons of failed primary objectives
        objectives_history = [
            [
                {"objective_type": "league_position", "description": "Win the league",
                 "target_value": 1, "current_value": 8, "is_met": False, "priority": "primary"},
                {"objective_type": "cup_progress", "description": "Win cup",
                 "target_value": 1, "current_value": 2, "is_met": False, "priority": "primary"},
            ],
            [
                {"objective_type": "league_position", "description": "Win the league",
                 "target_value": 1, "current_value": 12, "is_met": False, "priority": "primary"},
                {"objective_type": "cup_progress", "description": "Win cup",
                 "target_value": 1, "current_value": 0, "is_met": False, "priority": "primary"},
            ],
        ]
        mock_career.board_objectives = json.dumps(objectives_history)

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=0
        )

        assert result["should_sack"] is True
        assert "Failed board objectives" in result["reason"]
        assert "2 consecutive seasons" in result["reason"]
        assert result["severity"] == "critical"

    def test_check_sacking_one_failed_season_no_sack(self, mock_session, mock_career):
        """Test no sacking with only 1 failed season"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 50

        # One season passed, one failed
        objectives_history = [
            [
                {"objective_type": "league_position", "description": "Win the league",
                 "target_value": 1, "current_value": 1, "is_met": True, "priority": "primary"},
            ],
            [
                {"objective_type": "league_position", "description": "Win the league",
                 "target_value": 1, "current_value": 8, "is_met": False, "priority": "primary"},
            ],
        ]
        mock_career.board_objectives = json.dumps(objectives_history)

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=0
        )

        assert result["should_sack"] is False

    def test_check_sacking_single_season_format_failed(self, mock_session, mock_career):
        """Test sacking check with single-season objectives format (only 1 failure)"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 50

        # Single season format - all primary failed
        objectives = [
            {"objective_type": "league_position", "description": "Win the league",
             "target_value": 1, "current_value": 15, "is_met": False, "priority": "primary"},
        ]
        mock_career.board_objectives = json.dumps(objectives)

        result = service.check_sacking_conditions(
            mock_career, consecutive_low_confidence_weeks=0
        )

        # Only 1 failed season, need 2 consecutive
        assert result["should_sack"] is False

    def test_trigger_sacking_event_returns_correct_data(self, mock_session, mock_career):
        """Test that trigger_sacking_event returns correct SackingEvent"""
        from app.services.career_service import CareerService, SackingEvent

        service = CareerService(mock_session)
        mock_career.board_confidence = 10
        mock_career.current_season = 3
        mock_career.current_week = 20

        event = service.trigger_sacking_event(
            mock_career, "Board confidence critically low"
        )

        assert isinstance(event, SackingEvent)
        assert event.reason == "Board confidence critically low"
        assert event.season == 3
        assert event.week == 20
        assert event.board_confidence_at_sacking == 10
        assert event.career_summary["seasons_managed"] == 2
        assert event.career_summary["trophies_won"] == 0
        assert event.career_summary["matches_won"] == 30
        assert event.career_summary["matches_drawn"] == 10
        assert event.career_summary["matches_lost"] == 20
        assert event.career_summary["total_transfer_spend"] == 5000000
        assert event.career_summary["final_reputation"] == 50

    def test_trigger_sacking_marks_career_ended(self, mock_session, mock_career):
        """Test that trigger_sacking_event marks the career as ended"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)

        service.trigger_sacking_event(mock_career, "Failed objectives")

        # board_objectives should be set to ended marker
        # Since mock_career is a MagicMock, check the assignment
        assert mock_career.board_objectives is not None
        ended_data = json.loads(mock_career.board_objectives)
        assert ended_data["career_ended"] is True
        assert ended_data["sacking_reason"] == "Failed objectives"

    def test_is_career_active_true_when_no_objectives(self, mock_session, mock_career):
        """Test career is active when no board_objectives set"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = None

        assert service.is_career_active(mock_career) is True

    def test_is_career_active_true_with_normal_objectives(self, mock_session, mock_career):
        """Test career is active with normal objectives"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = json.dumps([
            {"objective_type": "league_position", "description": "Win",
             "target_value": 1, "is_met": False, "priority": "primary"}
        ])

        assert service.is_career_active(mock_career) is True

    def test_is_career_active_false_after_sacking(self, mock_session, mock_career):
        """Test career is inactive after sacking"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = json.dumps({
            "career_ended": True,
            "sacking_reason": "Failed objectives",
            "sacking_season": 3,
            "sacking_week": 20,
        })

        assert service.is_career_active(mock_career) is False

    def test_get_consecutive_failed_seasons_empty_objectives(self, mock_session, mock_career):
        """Test returns 0 when no objectives set"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = None

        assert service.get_consecutive_failed_seasons(mock_career) == 0

    def test_get_consecutive_failed_seasons_invalid_json(self, mock_session, mock_career):
        """Test returns 0 when objectives JSON is invalid"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_objectives = "not valid json {"

        assert service.get_consecutive_failed_seasons(mock_career) == 0

    def test_get_consecutive_failed_seasons_three_failures(self, mock_session, mock_career):
        """Test correctly counts 3 consecutive failed seasons"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)

        objectives_history = [
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": False, "priority": "primary", "description": "Win"}],
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": False, "priority": "primary", "description": "Win"}],
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": False, "priority": "primary", "description": "Win"}],
        ]
        mock_career.board_objectives = json.dumps(objectives_history)

        assert service.get_consecutive_failed_seasons(mock_career) == 3

    def test_get_consecutive_failed_seasons_mixed_results(self, mock_session, mock_career):
        """Test correctly counts only consecutive failures from most recent"""
        import json
        from app.services.career_service import CareerService

        service = CareerService(mock_session)

        # Season 1: passed, Season 2: failed, Season 3: failed
        objectives_history = [
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": True, "priority": "primary", "description": "Win"}],
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": False, "priority": "primary", "description": "Win"}],
            [{"objective_type": "league_position", "target_value": 1,
              "is_met": False, "priority": "primary", "description": "Win"}],
        ]
        mock_career.board_objectives = json.dumps(objectives_history)

        # Only 2 consecutive from the end
        assert service.get_consecutive_failed_seasons(mock_career) == 2

    @pytest.mark.asyncio
    async def test_advance_week_triggers_sacking_on_low_confidence(self, mock_session, mock_career):
        """Test that advance_week triggers sacking when confidence is critically low"""
        from unittest.mock import AsyncMock
        from app.services.career_service import CareerService, SackingEvent

        # Set up career with very low confidence (will trigger heuristic)
        mock_career.board_confidence = 1  # Very low - heuristic estimates ~5 weeks

        def advance_week_side_effect():
            mock_career.current_week += 1

        mock_career.advance_week = lambda: advance_week_side_effect()

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        # With confidence at 1, the heuristic estimates enough weeks for sacking
        assert summary.sacking is not None
        assert isinstance(summary.sacking, SackingEvent)
        assert "critically low" in summary.sacking.reason

    @pytest.mark.asyncio
    async def test_advance_week_no_sacking_normal_confidence(self, mock_session, mock_career):
        """Test that advance_week does not trigger sacking with normal confidence"""
        from unittest.mock import AsyncMock
        from app.services.career_service import CareerService

        mock_career.board_confidence = 50
        mock_career.board_objectives = None

        def advance_week_side_effect():
            mock_career.current_week += 1

        mock_career.advance_week = lambda: advance_week_side_effect()

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.sacking is None

    def test_estimate_consecutive_low_confidence_weeks_above_threshold(self, mock_session, mock_career):
        """Test estimation returns 0 when confidence is at or above threshold"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 20

        result = service._estimate_consecutive_low_confidence_weeks(mock_career)
        assert result == 0

    def test_estimate_consecutive_low_confidence_weeks_below_threshold(self, mock_session, mock_career):
        """Test estimation returns positive value when confidence is below threshold"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 5

        result = service._estimate_consecutive_low_confidence_weeks(mock_career)
        # deficit = 20 - 5 = 15, estimated_weeks = 15 // 4 = 3
        assert result == 3

    def test_estimate_consecutive_low_confidence_weeks_very_low(self, mock_session, mock_career):
        """Test estimation with confidence at 1 (minimum)"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        mock_career.board_confidence = 1

        result = service._estimate_consecutive_low_confidence_weeks(mock_career)
        # deficit = 20 - 1 = 19, estimated_weeks = 19 // 4 = 4
        assert result == 4


class TestHallOfFame:
    """Tests for the Hall of Fame system"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 3
        career.current_week = 15
        career.board_confidence = 50
        career.board_objectives = None
        career.seasons_managed = 2
        career.trophies_won = 0
        career.matches_won = 20
        career.matches_drawn = 10
        career.matches_lost = 10
        career.get_total_matches = MagicMock(return_value=40)
        career.get_win_percentage = MagicMock(return_value=50.0)
        return career

    def test_hall_of_fame_entry_dataclass_creation(self):
        """Test that HallOfFameEntry is created correctly"""
        from app.services.career_service import HallOfFameEntry

        entry = HallOfFameEntry(
            achievement_type="trophy",
            title="League Champion 2024",
            description="Won the league title in season 2",
            season=2,
            week=38,
            value=87,
        )

        assert entry.achievement_type == "trophy"
        assert entry.title == "League Champion 2024"
        assert entry.description == "Won the league title in season 2"
        assert entry.season == 2
        assert entry.week == 38
        assert entry.value == 87

    def test_hall_of_fame_entry_to_dict(self):
        """Test HallOfFameEntry serialization to dict"""
        from app.services.career_service import HallOfFameEntry

        entry = HallOfFameEntry(
            achievement_type="milestone",
            title="Century of Matches",
            description="Managed 100 matches",
            season=5,
            week=20,
            value=100,
        )

        result = entry.to_dict()

        assert result == {
            "achievement_type": "milestone",
            "title": "Century of Matches",
            "description": "Managed 100 matches",
            "season": 5,
            "week": 20,
            "value": 100,
        }

    def test_hall_of_fame_entry_from_dict(self):
        """Test HallOfFameEntry deserialization from dict"""
        from app.services.career_service import HallOfFameEntry

        data = {
            "achievement_type": "record",
            "title": "Elite Win Rate",
            "description": "Achieved a win percentage above 60%",
            "season": 4,
            "week": 52,
            "value": 65,
        }

        entry = HallOfFameEntry.from_dict(data)

        assert entry.achievement_type == "record"
        assert entry.title == "Elite Win Rate"
        assert entry.description == "Achieved a win percentage above 60%"
        assert entry.season == 4
        assert entry.week == 52
        assert entry.value == 65

    def test_hall_of_fame_entry_optional_value(self):
        """Test HallOfFameEntry with no value"""
        from app.services.career_service import HallOfFameEntry

        entry = HallOfFameEntry(
            achievement_type="trophy",
            title="First Trophy",
            description="Won the first trophy",
            season=1,
            week=40,
        )

        assert entry.value is None
        assert entry.to_dict()["value"] is None

    def test_get_hall_of_fame_empty_career(self, mock_session, mock_career):
        """Test get_hall_of_fame with no achievements"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        # Career with no milestones reached
        mock_career.get_total_matches = MagicMock(return_value=5)
        mock_career.get_win_percentage = MagicMock(return_value=40.0)
        mock_career.matches_won = 3
        mock_career.trophies_won = 0
        mock_career.seasons_managed = 0

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        assert entries == []

    def test_get_hall_of_fame_detects_100_matches(self, mock_session, mock_career):
        """Test that 100 matches milestone is detected"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=105)
        mock_career.get_win_percentage = MagicMock(return_value=50.0)
        mock_career.matches_won = 50
        mock_career.trophies_won = 0
        mock_career.seasons_managed = 3

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "Century of Matches" in titles
        assert "50 Victories" in titles

    def test_get_hall_of_fame_detects_50_wins(self, mock_session, mock_career):
        """Test that 50 wins milestone is detected"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=80)
        mock_career.get_win_percentage = MagicMock(return_value=62.5)
        mock_career.matches_won = 50
        mock_career.trophies_won = 0
        mock_career.seasons_managed = 2

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "50 Victories" in titles

    def test_get_hall_of_fame_detects_first_trophy(self, mock_session, mock_career):
        """Test that first trophy milestone is detected"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=40)
        mock_career.get_win_percentage = MagicMock(return_value=50.0)
        mock_career.matches_won = 20
        mock_career.trophies_won = 1
        mock_career.seasons_managed = 1

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "First Trophy" in titles

    def test_get_hall_of_fame_detects_5_trophies(self, mock_session, mock_career):
        """Test that 5 trophies milestone is detected"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=200)
        mock_career.get_win_percentage = MagicMock(return_value=55.0)
        mock_career.matches_won = 110
        mock_career.trophies_won = 5
        mock_career.seasons_managed = 6

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "First Trophy" in titles
        assert "Trophy Collector" in titles

    def test_get_hall_of_fame_detects_10_seasons(self, mock_session, mock_career):
        """Test that 10 seasons milestone is detected"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=400)
        mock_career.get_win_percentage = MagicMock(return_value=55.0)
        mock_career.matches_won = 220
        mock_career.trophies_won = 3
        mock_career.seasons_managed = 10

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "Decade of Management" in titles

    def test_get_hall_of_fame_detects_win_percentage(self, mock_session, mock_career):
        """Test that win percentage > 60% milestone is detected (requires 20+ matches)"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        mock_career.get_total_matches = MagicMock(return_value=50)
        mock_career.get_win_percentage = MagicMock(return_value=65.0)
        mock_career.matches_won = 32
        mock_career.trophies_won = 0
        mock_career.seasons_managed = 1

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "Elite Win Rate" in titles

    def test_get_hall_of_fame_win_percentage_not_detected_few_matches(self, mock_session, mock_career):
        """Test that win percentage milestone requires at least 20 matches"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService

        # Only 10 matches but high win rate - should NOT trigger
        mock_career.get_total_matches = MagicMock(return_value=10)
        mock_career.get_win_percentage = MagicMock(return_value=80.0)
        mock_career.matches_won = 8
        mock_career.trophies_won = 0
        mock_career.seasons_managed = 0

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        titles = [e.title for e in entries]
        assert "Elite Win Rate" not in titles

    def test_add_hall_of_fame_entry(self, mock_session, mock_career):
        """Test adding a Hall of Fame entry"""
        from app.services.career_service import CareerService, HallOfFameEntry
        import json

        service = CareerService(mock_session)

        entry = HallOfFameEntry(
            achievement_type="trophy",
            title="League Champion 2024",
            description="Won the league in season 2",
            season=2,
            week=38,
            value=87,
        )

        service.add_hall_of_fame_entry(mock_career, entry)

        # Verify the entry was stored in board_objectives
        stored_data = json.loads(mock_career.board_objectives)
        assert "hall_of_fame" in stored_data
        assert len(stored_data["hall_of_fame"]) == 1
        assert stored_data["hall_of_fame"][0]["title"] == "League Champion 2024"
        assert stored_data["hall_of_fame"][0]["achievement_type"] == "trophy"
        assert stored_data["hall_of_fame"][0]["value"] == 87

    def test_add_multiple_hall_of_fame_entries(self, mock_session, mock_career):
        """Test adding multiple Hall of Fame entries"""
        from app.services.career_service import CareerService, HallOfFameEntry
        import json

        service = CareerService(mock_session)

        entry1 = HallOfFameEntry(
            achievement_type="trophy",
            title="League Champion",
            description="Won the league",
            season=1,
            week=38,
        )
        entry2 = HallOfFameEntry(
            achievement_type="record",
            title="Unbeaten Run",
            description="20 matches unbeaten",
            season=2,
            week=10,
            value=20,
        )

        service.add_hall_of_fame_entry(mock_career, entry1)
        service.add_hall_of_fame_entry(mock_career, entry2)

        stored_data = json.loads(mock_career.board_objectives)
        assert len(stored_data["hall_of_fame"]) == 2
        assert stored_data["hall_of_fame"][0]["title"] == "League Champion"
        assert stored_data["hall_of_fame"][1]["title"] == "Unbeaten Run"

    def test_get_hall_of_fame_includes_stored_entries(self, mock_session, mock_career):
        """Test that get_hall_of_fame returns stored entries"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService, HallOfFameEntry
        import json

        # Pre-store an entry
        stored = {
            "hall_of_fame": [
                {
                    "achievement_type": "trophy",
                    "title": "Cup Winner",
                    "description": "Won the domestic cup",
                    "season": 1,
                    "week": 40,
                    "value": None,
                }
            ]
        }
        mock_career.board_objectives = json.dumps(stored)

        # Career has no milestones reached
        mock_career.get_total_matches = MagicMock(return_value=10)
        mock_career.get_win_percentage = MagicMock(return_value=40.0)
        mock_career.matches_won = 4
        mock_career.trophies_won = 1
        mock_career.seasons_managed = 0

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        # Should include the stored entry plus auto-detected "First Trophy"
        titles = [e.title for e in entries]
        assert "Cup Winner" in titles
        assert "First Trophy" in titles

    def test_get_hall_of_fame_no_duplicate_entries(self, mock_session, mock_career):
        """Test that auto-detected milestones don't duplicate stored entries"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService, HallOfFameEntry
        import json

        # Pre-store the "First Trophy" entry
        stored = {
            "hall_of_fame": [
                {
                    "achievement_type": "trophy",
                    "title": "First Trophy",
                    "description": "Won the first trophy of the career",
                    "season": 1,
                    "week": 40,
                    "value": 1,
                }
            ]
        }
        mock_career.board_objectives = json.dumps(stored)

        # Career stats would also trigger "First Trophy" detection
        mock_career.get_total_matches = MagicMock(return_value=30)
        mock_career.get_win_percentage = MagicMock(return_value=50.0)
        mock_career.matches_won = 15
        mock_career.trophies_won = 1
        mock_career.seasons_managed = 1

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        # "First Trophy" should appear only once
        first_trophy_entries = [e for e in entries if e.title == "First Trophy"]
        assert len(first_trophy_entries) == 1

    def test_hall_of_fame_entry_has_correct_structure(self, mock_session, mock_career):
        """Test that all entries have the required fields"""
        from unittest.mock import MagicMock
        from app.services.career_service import CareerService, HallOfFameEntry

        mock_career.get_total_matches = MagicMock(return_value=150)
        mock_career.get_win_percentage = MagicMock(return_value=65.0)
        mock_career.matches_won = 97
        mock_career.trophies_won = 2
        mock_career.seasons_managed = 4

        service = CareerService(mock_session)
        entries = service.get_hall_of_fame(mock_career)

        assert len(entries) > 0
        for entry in entries:
            assert isinstance(entry, HallOfFameEntry)
            assert entry.achievement_type in ("trophy", "record", "milestone")
            assert isinstance(entry.title, str) and len(entry.title) > 0
            assert isinstance(entry.description, str) and len(entry.description) > 0
            assert isinstance(entry.season, int) and entry.season >= 1
            assert isinstance(entry.week, int) and entry.week >= 1


class TestManagerFatigue:
    """Tests for the manager fatigue system"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        from unittest.mock import AsyncMock
        session = AsyncMock(spec=AsyncSession)
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_career(self):
        """Create a mock career object for testing"""
        from unittest.mock import MagicMock
        career = MagicMock(spec=Career)
        career.id = 1
        career.user_id = 1
        career.club_id = 1
        career.manager_name = "John Smith"
        career.current_season = 1
        career.current_week = 10
        career.board_confidence = 50
        career.manager_reputation = 50
        career.matches_won = 5
        career.matches_drawn = 3
        career.matches_lost = 2
        return career

    def test_no_fatigue_with_zero_losses(self, mock_session, mock_career):
        """Test no fatigue when there are no consecutive losses"""
        from app.services.career_service import CareerService, ManagerFatigueStatus

        service = CareerService(mock_session)
        results = ["W", "W", "D", "W", "W"]

        status = service.check_manager_fatigue(mock_career, results)

        assert isinstance(status, ManagerFatigueStatus)
        assert status.consecutive_losses == 0
        assert status.is_fatigued is False
        assert status.morale_penalty == 0
        assert "not fatigued" in status.description

    def test_no_fatigue_with_less_than_5_losses(self, mock_session, mock_career):
        """Test no fatigue with fewer than 5 consecutive losses"""
        from app.services.career_service import CareerService, ManagerFatigueStatus

        service = CareerService(mock_session)
        results = ["W", "D", "L", "L", "L", "L"]  # 4 consecutive losses

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 4
        assert status.is_fatigued is False
        assert status.morale_penalty == 0

    def test_fatigue_triggers_at_exactly_5_losses(self, mock_session, mock_career):
        """Test fatigue triggers at exactly 5 consecutive losses"""
        from app.services.career_service import CareerService, ManagerFatigueStatus

        service = CareerService(mock_session)
        results = ["W", "L", "L", "L", "L", "L"]  # 5 consecutive losses

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 5
        assert status.is_fatigued is True
        assert status.morale_penalty == -5
        assert "fatigued" in status.description
        assert "5 consecutive losses" in status.description

    def test_fatigue_penalty_scales_with_6_losses(self, mock_session, mock_career):
        """Test morale penalty scales to -8 at 6 consecutive losses"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        results = ["L", "L", "L", "L", "L", "L"]  # 6 consecutive losses

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 6
        assert status.is_fatigued is True
        assert status.morale_penalty == -8

    def test_fatigue_penalty_scales_with_7_plus_losses(self, mock_session, mock_career):
        """Test morale penalty caps at -10 for 7+ consecutive losses"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        results = ["L", "L", "L", "L", "L", "L", "L", "L"]  # 8 consecutive losses

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 8
        assert status.is_fatigued is True
        assert status.morale_penalty == -10

    def test_mixed_results_counts_from_end(self, mock_session, mock_career):
        """Test that mixed results (W, L, L, L, L, L) correctly counts from end"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        # Win followed by 5 losses - should count 5 consecutive from end
        results = ["W", "L", "L", "L", "L", "L"]

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 5
        assert status.is_fatigued is True
        assert status.morale_penalty == -5

    def test_fatigue_resets_after_win(self, mock_session, mock_career):
        """Test that fatigue resets after a win breaks the losing streak"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        # 5 losses then a win - no consecutive losses from end
        results = ["L", "L", "L", "L", "L", "W"]

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 0
        assert status.is_fatigued is False
        assert status.morale_penalty == 0

    def test_fatigue_resets_after_draw(self, mock_session, mock_career):
        """Test that fatigue resets after a draw breaks the losing streak"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        # 5 losses then a draw - no consecutive losses from end
        results = ["L", "L", "L", "L", "L", "D"]

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 0
        assert status.is_fatigued is False
        assert status.morale_penalty == 0

    def test_empty_results_no_fatigue(self, mock_session, mock_career):
        """Test no fatigue with empty results list"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        results = []

        status = service.check_manager_fatigue(mock_career, results)

        assert status.consecutive_losses == 0
        assert status.is_fatigued is False
        assert status.morale_penalty == 0

    def test_calculate_fatigue_morale_penalty_below_5(self, mock_session):
        """Test penalty calculation for 0-4 losses returns 0"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)

        assert service.calculate_fatigue_morale_penalty(0) == 0
        assert service.calculate_fatigue_morale_penalty(1) == 0
        assert service.calculate_fatigue_morale_penalty(2) == 0
        assert service.calculate_fatigue_morale_penalty(3) == 0
        assert service.calculate_fatigue_morale_penalty(4) == 0

    def test_calculate_fatigue_morale_penalty_at_5(self, mock_session):
        """Test penalty calculation at exactly 5 losses returns -5"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        assert service.calculate_fatigue_morale_penalty(5) == -5

    def test_calculate_fatigue_morale_penalty_at_6(self, mock_session):
        """Test penalty calculation at 6 losses returns -8"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        assert service.calculate_fatigue_morale_penalty(6) == -8

    def test_calculate_fatigue_morale_penalty_at_7_plus(self, mock_session):
        """Test penalty calculation at 7+ losses returns -10"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        assert service.calculate_fatigue_morale_penalty(7) == -10
        assert service.calculate_fatigue_morale_penalty(10) == -10
        assert service.calculate_fatigue_morale_penalty(20) == -10

    def test_get_recent_results_returns_list(self, mock_session, mock_career):
        """Test that get_recent_results returns a list"""
        from app.services.career_service import CareerService

        service = CareerService(mock_session)
        results = service.get_recent_results(mock_career)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_advance_week_includes_fatigue_status(self, mock_session, mock_career):
        """Test that advance_week includes manager_fatigue in WeekSummary"""
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.career_service import CareerService, ManagerFatigueStatus

        # Setup mock career advance_week
        def advance_week_side_effect():
            mock_career.current_week += 1

        mock_career.advance_week = MagicMock(side_effect=advance_week_side_effect)
        mock_career.board_objectives = None

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)

        summary = await service.advance_week(mock_career.id)

        assert summary.manager_fatigue is not None
        assert isinstance(summary.manager_fatigue, ManagerFatigueStatus)

    @pytest.mark.asyncio
    async def test_advance_week_fatigue_with_losses(self, mock_session, mock_career):
        """Test that advance_week correctly reports fatigue when losses are present"""
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.career_service import CareerService, ManagerFatigueStatus

        def advance_week_side_effect():
            mock_career.current_week += 1

        mock_career.advance_week = MagicMock(side_effect=advance_week_side_effect)
        mock_career.board_objectives = None

        service = CareerService(mock_session)
        service.get_career_by_id = AsyncMock(return_value=mock_career)
        # Mock get_recent_results to return 5 consecutive losses
        service.get_recent_results = MagicMock(return_value=["W", "L", "L", "L", "L", "L"])

        summary = await service.advance_week(mock_career.id)

        assert summary.manager_fatigue is not None
        assert summary.manager_fatigue.is_fatigued is True
        assert summary.manager_fatigue.consecutive_losses == 5
        assert summary.manager_fatigue.morale_penalty == -5
