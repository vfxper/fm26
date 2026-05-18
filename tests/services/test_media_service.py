"""
Tests for MediaService - Comprehensive media system tests.

Tests cover:
- 16.1: Pre-match and post-match press conferences
- 16.2: Multiple-choice response system (3+ options)
- 16.3: Morale and reputation impact calculation
- 16.4: Media pressure event simulation
- 16.5: Media reputation score (1-100)
- 16.6: Player interview event generation
- 16.7: Board scrutiny triggers (reputation < 30)
- 16.8: News feed display
- 16.9: Press conference localization
- 16.10: Rival manager comment system
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.career import Career
from app.models.club import Club
from app.models.user import User
from app.models.media_event import MediaEvent, MediaEventType, MediaEventStatus
from app.services.media_service import (
    MediaService,
    MediaServiceError,
    CareerNotFoundError,
    ConferenceNotFoundError,
    InvalidResponseError,
    PRESS_CONFERENCE_TEMPLATES,
    PLAYER_INTERVIEW_TEMPLATES,
    RIVAL_COMMENT_TEMPLATES,
    MEDIA_PRESSURE_TEMPLATES,
    BOARD_SCRUTINY_MESSAGES,
)


# Use SQLite for testing (no PostgreSQL dependency)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def engine():
    """Create test database engine using SQLite."""
    eng = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            # Remove PostgreSQL-specific indexes (GIN/tsvector)
            pg_indexes = [
                idx for idx in table.indexes
                if 'fts' in idx.name or 'tsvector' in str(idx.expressions)
            ]
            for idx in pg_indexes:
                table.indexes.discard(idx)

            # Remove check constraints that use enum string values
            # (SQLite stores enum names differently than PostgreSQL)
            original_constraints = list(table.constraints)
            constraints_to_remove = []
            for constraint in table.constraints:
                if hasattr(constraint, 'name') and constraint.name and (
                    'check_status_response_consistency' in (constraint.name or '')
                ):
                    constraints_to_remove.append(constraint)
            for c in constraints_to_remove:
                table.constraints.discard(c)

            await conn.run_sync(
                lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True)
            )

            # Restore removed items
            for idx in pg_indexes:
                table.indexes.add(idx)
            for c in constraints_to_remove:
                table.constraints.add(c)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture(scope="function")
async def session(engine):
    """Create test database session."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as sess:
        yield sess


@pytest.fixture
async def sample_career(session: AsyncSession) -> Career:
    """Create a sample career for testing."""
    user = User(telegram_user_id=123456, username="testuser", first_name="Test")
    session.add(user)
    await session.flush()

    club = Club(
        name="Test FC",
        reputation=60,
        league="Premier League",
        country="England",
        balance=10_000_000,
        wage_budget=500_000,
        stadium_capacity=30000,
        youth_academy_level=5,
        training_facilities_level=5,
        medical_centre_level=5,
        scouting_network_level=5,
    )
    session.add(club)
    await session.flush()

    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Test Manager",
        current_season=1,
        current_week=10,
        board_confidence=50,
        manager_reputation=50,
        tactical_knowledge=10,
        man_management=10,
        motivating=10,
        attacking=10,
        defending=10,
        technical=10,
        mental=10,
        youth_development=10,
        board_relations=10,
    )
    session.add(career)
    await session.flush()
    return career


@pytest.fixture
async def low_reputation_career(session: AsyncSession) -> Career:
    """Create a career with low reputation for board scrutiny tests."""
    user = User(telegram_user_id=789012, username="lowrep", first_name="Low")
    session.add(user)
    await session.flush()

    club = Club(
        name="Struggling FC",
        reputation=30,
        league="Championship",
        country="England",
        balance=5_000_000,
        wage_budget=200_000,
        stadium_capacity=15000,
        youth_academy_level=3,
        training_facilities_level=3,
        medical_centre_level=3,
        scouting_network_level=3,
    )
    session.add(club)
    await session.flush()

    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Struggling Manager",
        current_season=2,
        current_week=20,
        board_confidence=40,
        manager_reputation=20,  # Below scrutiny threshold of 30
        tactical_knowledge=8,
        man_management=8,
        motivating=8,
        attacking=8,
        defending=8,
        technical=8,
        mental=8,
        youth_development=8,
        board_relations=8,
        matches_won=5,
        matches_lost=15,
        matches_drawn=5,
    )
    session.add(career)
    await session.flush()
    return career


# --- 16.1: Pre-match and Post-match Press Conferences ---


class TestPressConferences:
    """Tests for press conference generation (16.1)."""

    @pytest.mark.asyncio
    async def test_generate_pre_match_conference(self, session, sample_career):
        """Pre-match conference generates valid event with question and options."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        assert result["type"] == "pre_match"
        assert result["event_type"] == "pre_match_conference"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["pre_match"]["questions"]["en"]
        assert len(result["response_options"]) >= 3
        assert result["id"] is not None

    @pytest.mark.asyncio
    async def test_generate_post_match_win_conference(self, session, sample_career):
        """Post-match win conference uses correct template."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            match_id=1,
            conference_type="post_match",
            match_result="win",
        )

        assert result["type"] == "post_match"
        assert result["event_type"] == "post_match_conference"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["post_match_win"]["questions"]["en"]
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_generate_post_match_loss_conference(self, session, sample_career):
        """Post-match loss conference uses loss template."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="post_match",
            match_result="loss",
        )

        assert result["type"] == "post_match"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["post_match_loss"]["questions"]["en"]
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_generate_post_match_draw_conference(self, session, sample_career):
        """Post-match draw conference uses draw template."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="post_match",
            match_result="draw",
        )

        assert result["type"] == "post_match"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["post_match_draw"]["questions"]["en"]

    @pytest.mark.asyncio
    async def test_conference_creates_media_event(self, session, sample_career):
        """Conference generation creates a MediaEvent in the database."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        event = await session.get(MediaEvent, result["id"])
        assert event is not None
        assert event.career_id == sample_career.id
        assert event.event_type == MediaEventType.PRE_MATCH_CONFERENCE
        assert event.event_status == MediaEventStatus.PENDING

    @pytest.mark.asyncio
    async def test_conference_invalid_career_raises(self, session):
        """Conference generation with invalid career raises error."""
        service = MediaService(session)
        with pytest.raises(CareerNotFoundError):
            await service.generate_press_conference(career_id=99999)

    @pytest.mark.asyncio
    async def test_conference_invalid_type_raises(self, session, sample_career):
        """Conference generation with invalid type raises error."""
        service = MediaService(session)
        with pytest.raises(MediaServiceError):
            await service.generate_press_conference(
                career_id=sample_career.id,
                conference_type="invalid_type",
            )


# --- 16.2: Multiple-choice Response System ---


class TestResponseSystem:
    """Tests for the multiple-choice response system (16.2)."""

    @pytest.mark.asyncio
    async def test_respond_to_conference_valid_choice(self, session, sample_career):
        """Responding with a valid choice updates the event."""
        service = MediaService(session)
        conf = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        result = await service.respond_to_press_conference(
            career_id=sample_career.id,
            conference_id=conf["id"],
            choice_index=0,
        )

        assert result["conference_id"] == conf["id"]
        assert result["chosen_response"] is not None
        assert "impact" in result

        # Verify event is updated
        event = await session.get(MediaEvent, conf["id"])
        assert event.event_status == MediaEventStatus.RESPONDED
        assert event.selected_response == 0
        assert event.response_date is not None

    @pytest.mark.asyncio
    async def test_respond_all_options_valid(self, session, sample_career):
        """All response options (0 to N-1) are valid choices."""
        service = MediaService(session)
        conf = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )
        num_options = len(conf["response_options"])

        # Test last valid option
        result = await service.respond_to_press_conference(
            career_id=sample_career.id,
            conference_id=conf["id"],
            choice_index=num_options - 1,
        )
        assert result["chosen_response"]["key"] == conf["response_options"][num_options - 1]["key"]

    @pytest.mark.asyncio
    async def test_respond_invalid_choice_raises(self, session, sample_career):
        """Responding with out-of-range choice raises error."""
        service = MediaService(session)
        conf = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        with pytest.raises(InvalidResponseError):
            await service.respond_to_press_conference(
                career_id=sample_career.id,
                conference_id=conf["id"],
                choice_index=99,
            )

    @pytest.mark.asyncio
    async def test_respond_negative_choice_raises(self, session, sample_career):
        """Responding with negative choice raises error."""
        service = MediaService(session)
        conf = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        with pytest.raises(InvalidResponseError):
            await service.respond_to_press_conference(
                career_id=sample_career.id,
                conference_id=conf["id"],
                choice_index=-1,
            )

    @pytest.mark.asyncio
    async def test_respond_already_responded_raises(self, session, sample_career):
        """Responding to already-responded conference raises error."""
        service = MediaService(session)
        conf = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
        )

        # First response
        await service.respond_to_press_conference(
            career_id=sample_career.id,
            conference_id=conf["id"],
            choice_index=0,
        )

        # Second response should fail
        with pytest.raises(MediaServiceError, match="already responded"):
            await service.respond_to_press_conference(
                career_id=sample_career.id,
                conference_id=conf["id"],
                choice_index=1,
            )

    @pytest.mark.asyncio
    async def test_respond_nonexistent_conference_raises(self, session, sample_career):
        """Responding to non-existent conference raises error."""
        service = MediaService(session)
        with pytest.raises(ConferenceNotFoundError):
            await service.respond_to_press_conference(
                career_id=sample_career.id,
                conference_id=99999,
                choice_index=0,
            )

    @pytest.mark.asyncio
    async def test_all_templates_have_3_plus_options(self):
        """All press conference templates have at least 3 response options."""
        for key, template in PRESS_CONFERENCE_TEMPLATES.items():
            responses = template["responses"]
            assert len(responses) >= 3, (
                f"Template '{key}' has only {len(responses)} options, needs 3+"
            )


# --- 16.3: Morale and Reputation Impact Calculation ---


class TestImpactCalculation:
    """Tests for morale and reputation impact calculation (16.3)."""

    def test_calculate_basic_impact(self):
        """Basic impact calculation returns expected values."""
        service = MediaService.__new__(MediaService)
        result = service.calculate_response_impact(
            response_type="confident",
            context={
                "event_type": "pre_match_conference",
                "morale_impact": 3,
                "reputation_impact": 1,
            },
        )

        assert result["morale_change"] == 3
        assert result["reputation_change"] == 1
        assert "board_confidence_change" in result

    def test_blaming_response_amplified_in_post_match(self):
        """Blaming responses have amplified negative effects in post-match."""
        service = MediaService.__new__(MediaService)
        result = service.calculate_response_impact(
            response_type="blaming",
            context={
                "event_type": "post_match_conference",
                "morale_impact": 0,
                "reputation_impact": -3,
            },
        )

        # Modifier of 1.5 applied
        assert result["reputation_change"] == int(-3 * 1.5)
        assert result["modifier"] == 1.5

    def test_media_pressure_amplified(self):
        """Media pressure events have amplified effects."""
        service = MediaService.__new__(MediaService)
        result = service.calculate_response_impact(
            response_type="defiant",
            context={
                "event_type": "media_pressure",
                "morale_impact": 2,
                "reputation_impact": 1,
            },
        )

        assert result["modifier"] == 1.3
        assert result["morale_change"] == int(2 * 1.3)

    def test_board_confidence_positive_threshold(self):
        """Board confidence increases when reputation change >= 2."""
        service = MediaService.__new__(MediaService)
        result = service.calculate_response_impact(
            response_type="humble",
            context={
                "event_type": "post_match_conference",
                "morale_impact": 3,
                "reputation_impact": 2,
            },
        )

        assert result["board_confidence_change"] == 1

    def test_board_confidence_negative_threshold(self):
        """Board confidence decreases when reputation change <= -2."""
        service = MediaService.__new__(MediaService)
        result = service.calculate_response_impact(
            response_type="blaming",
            context={
                "event_type": "pre_match_conference",
                "morale_impact": 0,
                "reputation_impact": -3,
            },
        )

        assert result["board_confidence_change"] == -1


# --- 16.4: Media Pressure Event Simulation ---


class TestMediaPressure:
    """Tests for media pressure event simulation (16.4)."""

    @pytest.mark.asyncio
    async def test_pressure_generated_for_losing_career(
        self, session, low_reputation_career
    ):
        """Pressure event generated for career with many losses."""
        service = MediaService(session)
        result = await service.simulate_media_pressure(
            career_id=low_reputation_career.id,
            season=2,
            week=20,
        )

        # Should generate pressure due to low reputation or high loss ratio
        assert result is not None
        assert "question" in result
        assert len(result["response_options"]) >= 3
        assert result["id"] is not None

    @pytest.mark.asyncio
    async def test_pressure_not_always_generated(self, session, sample_career):
        """Pressure events are not always generated for healthy careers."""
        service = MediaService(session)

        # Run multiple times - with 50 reputation and no losses,
        # only random 10% chance should trigger
        generated_count = 0
        for _ in range(20):
            with patch("app.services.media_service.random.random", return_value=0.5):
                result = await service.simulate_media_pressure(
                    career_id=sample_career.id,
                    season=1,
                    week=10,
                )
                if result is not None:
                    generated_count += 1

        # With random returning 0.5 (> 0.10), no random pressure should trigger
        # and with 0 matches, no loss-based pressure either
        assert generated_count == 0

    @pytest.mark.asyncio
    async def test_pressure_creates_media_event(self, session, low_reputation_career):
        """Pressure event creates a MediaEvent in the database."""
        service = MediaService(session)
        result = await service.simulate_media_pressure(
            career_id=low_reputation_career.id,
            season=2,
            week=20,
        )

        assert result is not None
        event = await session.get(MediaEvent, result["id"])
        assert event is not None
        assert event.event_type == MediaEventType.MEDIA_PRESSURE
        assert event.event_status == MediaEventStatus.PENDING

    @pytest.mark.asyncio
    async def test_pressure_invalid_career_raises(self, session):
        """Pressure simulation with invalid career raises error."""
        service = MediaService(session)
        with pytest.raises(CareerNotFoundError):
            await service.simulate_media_pressure(
                career_id=99999, season=1, week=1
            )


# --- 16.5: Media Reputation Score (1-100) ---


class TestMediaReputation:
    """Tests for media reputation score management (16.5)."""

    @pytest.mark.asyncio
    async def test_get_reputation(self, session, sample_career):
        """Get reputation returns current value."""
        service = MediaService(session)
        rep = await service.get_media_reputation(sample_career.id)
        assert rep == 50

    @pytest.mark.asyncio
    async def test_update_reputation_positive(self, session, sample_career):
        """Positive reputation change increases score."""
        service = MediaService(session)
        result = await service.update_media_reputation(sample_career.id, 10)

        assert result["old_reputation"] == 50
        assert result["new_reputation"] == 60
        assert result["change_applied"] == 10

    @pytest.mark.asyncio
    async def test_update_reputation_negative(self, session, sample_career):
        """Negative reputation change decreases score."""
        service = MediaService(session)
        result = await service.update_media_reputation(sample_career.id, -20)

        assert result["old_reputation"] == 50
        assert result["new_reputation"] == 30
        assert result["change_applied"] == -20

    @pytest.mark.asyncio
    async def test_reputation_clamped_at_100(self, session, sample_career):
        """Reputation cannot exceed 100."""
        service = MediaService(session)
        result = await service.update_media_reputation(sample_career.id, 60)

        assert result["new_reputation"] == 100
        assert result["change_applied"] == 50  # 50 + 50 = 100, not 110

    @pytest.mark.asyncio
    async def test_reputation_clamped_at_1(self, session, sample_career):
        """Reputation cannot go below 1."""
        service = MediaService(session)
        result = await service.update_media_reputation(sample_career.id, -100)

        assert result["new_reputation"] == 1
        assert result["change_applied"] == -49  # 50 - 49 = 1

    @pytest.mark.asyncio
    async def test_reputation_invalid_career_raises(self, session):
        """Getting reputation for invalid career raises error."""
        service = MediaService(session)
        with pytest.raises(CareerNotFoundError):
            await service.get_media_reputation(99999)


# --- 16.6: Player Interview Event Generation ---


class TestPlayerInterviews:
    """Tests for player interview event generation (16.6)."""

    @pytest.mark.asyncio
    async def test_generate_happy_player_interview(self, session, sample_career):
        """Happy player interview generates valid event."""
        service = MediaService(session)
        result = await service.generate_player_interview(
            career_id=sample_career.id,
            player_id=1,
            interview_type="happy_player",
        )

        assert result["interview_type"] == "happy_player"
        assert result["player_id"] == 1
        assert len(result["response_options"]) >= 3
        assert result["question"] in PLAYER_INTERVIEW_TEMPLATES["happy_player"]["questions"]["en"]

    @pytest.mark.asyncio
    async def test_generate_unhappy_player_interview(self, session, sample_career):
        """Unhappy player interview generates valid event."""
        service = MediaService(session)
        result = await service.generate_player_interview(
            career_id=sample_career.id,
            player_id=2,
            interview_type="unhappy_player",
        )

        assert result["interview_type"] == "unhappy_player"
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_generate_transfer_rumour_interview(self, session, sample_career):
        """Transfer rumour interview generates valid event."""
        service = MediaService(session)
        result = await service.generate_player_interview(
            career_id=sample_career.id,
            player_id=3,
            interview_type="transfer_rumour",
        )

        assert result["interview_type"] == "transfer_rumour"
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_interview_creates_media_event(self, session, sample_career):
        """Interview generation creates a MediaEvent with player reference."""
        service = MediaService(session)
        result = await service.generate_player_interview(
            career_id=sample_career.id,
            player_id=42,
            interview_type="happy_player",
        )

        event = await session.get(MediaEvent, result["id"])
        assert event is not None
        assert event.event_type == MediaEventType.PLAYER_INTERVIEW
        assert event.related_player_id == 42

    @pytest.mark.asyncio
    async def test_interview_random_type_when_none(self, session, sample_career):
        """Interview type is randomly selected when not specified."""
        service = MediaService(session)
        result = await service.generate_player_interview(
            career_id=sample_career.id,
            player_id=1,
        )

        assert result["interview_type"] in PLAYER_INTERVIEW_TEMPLATES

    @pytest.mark.asyncio
    async def test_interview_invalid_type_raises(self, session, sample_career):
        """Invalid interview type raises error."""
        service = MediaService(session)
        with pytest.raises(MediaServiceError):
            await service.generate_player_interview(
                career_id=sample_career.id,
                player_id=1,
                interview_type="nonexistent",
            )


# --- 16.7: Board Scrutiny Triggers ---


class TestBoardScrutiny:
    """Tests for board scrutiny triggers (16.7)."""

    @pytest.mark.asyncio
    async def test_scrutiny_triggered_below_30(self, session, low_reputation_career):
        """Board scrutiny triggered when reputation < 30."""
        service = MediaService(session)
        result = await service.check_board_scrutiny(low_reputation_career.id)

        assert result is not None
        assert result["triggered"] is True
        assert result["reputation"] == 20
        assert result["severity"] in ("warning", "severe", "critical")
        assert result["board_confidence_change"] < 0

    @pytest.mark.asyncio
    async def test_scrutiny_not_triggered_above_30(self, session, sample_career):
        """Board scrutiny not triggered when reputation >= 30."""
        service = MediaService(session)
        result = await service.check_board_scrutiny(sample_career.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_scrutiny_severity_critical(self, session, low_reputation_career):
        """Critical severity when reputation < 10."""
        # Set reputation to 5
        low_reputation_career.manager_reputation = 5
        await session.flush()

        service = MediaService(session)
        result = await service.check_board_scrutiny(low_reputation_career.id)

        assert result["severity"] == "critical"
        assert result["board_confidence_change"] == -3

    @pytest.mark.asyncio
    async def test_scrutiny_severity_severe(self, session, low_reputation_career):
        """Severe severity when reputation 10-19."""
        low_reputation_career.manager_reputation = 15
        await session.flush()

        service = MediaService(session)
        result = await service.check_board_scrutiny(low_reputation_career.id)

        assert result["severity"] == "severe"
        assert result["board_confidence_change"] == -2

    @pytest.mark.asyncio
    async def test_scrutiny_severity_warning(self, session, low_reputation_career):
        """Warning severity when reputation 20-29."""
        low_reputation_career.manager_reputation = 25
        await session.flush()

        service = MediaService(session)
        result = await service.check_board_scrutiny(low_reputation_career.id)

        assert result["severity"] == "warning"
        assert result["board_confidence_change"] == -1

    @pytest.mark.asyncio
    async def test_scrutiny_reduces_board_confidence(self, session, low_reputation_career):
        """Board scrutiny reduces board confidence."""
        old_confidence = low_reputation_career.board_confidence
        service = MediaService(session)
        result = await service.check_board_scrutiny(low_reputation_career.id)

        assert result["new_board_confidence"] < old_confidence

    @pytest.mark.asyncio
    async def test_scrutiny_invalid_career_raises(self, session):
        """Board scrutiny check with invalid career raises error."""
        service = MediaService(session)
        with pytest.raises(CareerNotFoundError):
            await service.check_board_scrutiny(99999)


# --- 16.8: News Feed Display ---


class TestNewsFeed:
    """Tests for news feed display (16.8)."""

    @pytest.mark.asyncio
    async def test_empty_news_feed(self, session, sample_career):
        """Empty news feed returns empty list."""
        service = MediaService(session)
        feed = await service.get_news_feed(sample_career.id)
        assert feed == []

    @pytest.mark.asyncio
    async def test_news_feed_returns_events(self, session, sample_career):
        """News feed returns generated events."""
        service = MediaService(session)

        # Generate some events
        await service.generate_press_conference(
            career_id=sample_career.id, conference_type="pre_match"
        )
        await service.generate_player_interview(
            career_id=sample_career.id, player_id=1, interview_type="happy_player"
        )

        feed = await service.get_news_feed(sample_career.id)
        assert len(feed) == 2

    @pytest.mark.asyncio
    async def test_news_feed_ordered_by_date(self, session, sample_career):
        """News feed is ordered by date (newest first)."""
        service = MediaService(session)

        await service.generate_press_conference(
            career_id=sample_career.id, conference_type="pre_match"
        )
        await service.generate_player_interview(
            career_id=sample_career.id, player_id=1, interview_type="happy_player"
        )

        feed = await service.get_news_feed(sample_career.id)
        assert len(feed) == 2
        # Both created at roughly the same time, but order should be consistent
        dates = [item["event_date"] for item in feed]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_news_feed_respects_limit(self, session, sample_career):
        """News feed respects the limit parameter."""
        service = MediaService(session)

        # Generate 5 events
        for _ in range(5):
            await service.generate_press_conference(
                career_id=sample_career.id, conference_type="pre_match"
            )

        feed = await service.get_news_feed(sample_career.id, limit=3)
        assert len(feed) == 3

    @pytest.mark.asyncio
    async def test_news_feed_filter_by_type(self, session, sample_career):
        """News feed can be filtered by event type."""
        service = MediaService(session)

        await service.generate_press_conference(
            career_id=sample_career.id, conference_type="pre_match"
        )
        await service.generate_player_interview(
            career_id=sample_career.id, player_id=1, interview_type="happy_player"
        )

        feed = await service.get_news_feed(
            sample_career.id, event_type="player_interview"
        )
        assert len(feed) == 1
        assert feed[0]["event_type"] == "player_interview"

    @pytest.mark.asyncio
    async def test_news_feed_contains_expected_fields(self, session, sample_career):
        """News feed items contain all expected fields."""
        service = MediaService(session)
        await service.generate_press_conference(
            career_id=sample_career.id, conference_type="pre_match"
        )

        feed = await service.get_news_feed(sample_career.id)
        item = feed[0]

        assert "id" in item
        assert "event_type" in item
        assert "question" in item
        assert "status" in item
        assert "response_options" in item
        assert "event_date" in item


# --- 16.9: Press Conference Localization ---


class TestLocalization:
    """Tests for press conference localization (16.9)."""

    @pytest.mark.asyncio
    async def test_english_locale(self, session, sample_career):
        """English locale returns English text."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
            locale="en",
        )

        assert result["locale"] == "en"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["pre_match"]["questions"]["en"]

    @pytest.mark.asyncio
    async def test_russian_locale(self, session, sample_career):
        """Russian locale returns Russian text."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
            locale="ru",
        )

        assert result["locale"] == "ru"
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["pre_match"]["questions"]["ru"]

    @pytest.mark.asyncio
    async def test_russian_response_options(self, session, sample_career):
        """Russian locale provides Russian response text."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
            locale="ru",
        )

        # Check that response texts are in Russian
        for option in result["response_options"]:
            # Russian text should contain Cyrillic characters
            assert any(
                '\u0400' <= c <= '\u04FF' for c in option["text"]
            ), f"Expected Russian text, got: {option['text']}"

    @pytest.mark.asyncio
    async def test_unsupported_locale_falls_back_to_english(self, session, sample_career):
        """Unsupported locale falls back to English."""
        service = MediaService(session)
        result = await service.generate_press_conference(
            career_id=sample_career.id,
            conference_type="pre_match",
            locale="fr",  # French not supported
        )

        # Should fall back to English
        assert result["question"] in PRESS_CONFERENCE_TEMPLATES["pre_match"]["questions"]["en"]

    def test_all_templates_have_russian_translations(self):
        """All press conference templates have Russian translations."""
        for key, template in PRESS_CONFERENCE_TEMPLATES.items():
            assert "ru" in template["questions"], (
                f"Template '{key}' missing Russian questions"
            )
            for resp_key, resp_data in template["responses"].items():
                assert "ru" in resp_data, (
                    f"Template '{key}' response '{resp_key}' missing Russian text"
                )

    def test_player_interview_templates_have_russian(self):
        """All player interview templates have Russian translations."""
        for key, template in PLAYER_INTERVIEW_TEMPLATES.items():
            assert "ru" in template["questions"], (
                f"Interview template '{key}' missing Russian questions"
            )
            for resp_key, resp_data in template["responses"].items():
                assert "ru" in resp_data, (
                    f"Interview '{key}' response '{resp_key}' missing Russian text"
                )

    def test_rival_comment_templates_have_russian(self):
        """All rival comment templates have Russian translations."""
        for key, template in RIVAL_COMMENT_TEMPLATES.items():
            assert "ru" in template["comments"], (
                f"Rival template '{key}' missing Russian comments"
            )
            for resp_key, resp_data in template["responses"].items():
                assert "ru" in resp_data, (
                    f"Rival '{key}' response '{resp_key}' missing Russian text"
                )

    def test_board_scrutiny_messages_have_russian(self):
        """Board scrutiny messages have Russian translations."""
        assert "ru" in BOARD_SCRUTINY_MESSAGES
        assert len(BOARD_SCRUTINY_MESSAGES["ru"]) >= 1


# --- 16.10: Rival Manager Comment System ---


class TestRivalComments:
    """Tests for rival manager comment system (16.10)."""

    @pytest.mark.asyncio
    async def test_generate_pre_match_taunt(self, session, sample_career):
        """Pre-match taunt generates valid event."""
        service = MediaService(session)
        result = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
            comment_type="pre_match_taunt",
        )

        assert result["comment_type"] == "pre_match_taunt"
        assert result["rival_comment"] in RIVAL_COMMENT_TEMPLATES["pre_match_taunt"]["comments"]["en"]
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_generate_post_match_gloat(self, session, sample_career):
        """Post-match gloat generates valid event."""
        service = MediaService(session)
        result = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
            match_id=5,
            comment_type="post_match_gloat",
        )

        assert result["comment_type"] == "post_match_gloat"
        assert len(result["response_options"]) >= 3

    @pytest.mark.asyncio
    async def test_rival_comment_creates_media_event(self, session, sample_career):
        """Rival comment creates a MediaEvent in the database."""
        service = MediaService(session)
        result = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
            comment_type="pre_match_taunt",
            rival_club_id=99,
        )

        event = await session.get(MediaEvent, result["id"])
        assert event is not None
        assert event.event_type == MediaEventType.RIVAL_COMMENT
        assert event.related_club_id == 99

    @pytest.mark.asyncio
    async def test_rival_comment_random_type(self, session, sample_career):
        """Rival comment type is random when not specified."""
        service = MediaService(session)
        result = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
        )

        assert result["comment_type"] in RIVAL_COMMENT_TEMPLATES

    @pytest.mark.asyncio
    async def test_rival_comment_invalid_type_raises(self, session, sample_career):
        """Invalid rival comment type raises error."""
        service = MediaService(session)
        with pytest.raises(MediaServiceError):
            await service.generate_rival_manager_comment(
                career_id=sample_career.id,
                comment_type="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_rival_comment_russian_locale(self, session, sample_career):
        """Rival comment in Russian locale uses Russian text."""
        service = MediaService(session)
        result = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
            comment_type="pre_match_taunt",
            locale="ru",
        )

        assert result["rival_comment"] in RIVAL_COMMENT_TEMPLATES["pre_match_taunt"]["comments"]["ru"]
        # Response options should be in Russian
        for option in result["response_options"]:
            assert any(
                '\u0400' <= c <= '\u04FF' for c in option["text"]
            ), f"Expected Russian text, got: {option['text']}"

    @pytest.mark.asyncio
    async def test_rival_comment_can_be_responded_to(self, session, sample_career):
        """Rival comments can be responded to via the response system."""
        service = MediaService(session)
        comment = await service.generate_rival_manager_comment(
            career_id=sample_career.id,
            comment_type="pre_match_taunt",
        )

        result = await service.respond_to_press_conference(
            career_id=sample_career.id,
            conference_id=comment["id"],
            choice_index=0,
        )

        assert result["conference_id"] == comment["id"]
        assert "impact" in result
