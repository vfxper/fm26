"""
Tests for Finance Service - Financial Deficit Consequences (Task 11.9)

Tests the deficit tracking and consequence methods:
- record_season_end_financial_status(club_id, career_id, season) - records season-end status
- get_deficit_status(club_id, career_id) - returns current deficit streak and consequences
- check_deficit_consequences(club_id, career_id, season) - checks and applies consequences

Consequence escalation:
- 0 seasons in deficit: No consequences
- 1 season in deficit: Warning to player-manager
- 2 consecutive seasons: Transfer embargo (cannot buy players)
- 3+ consecutive seasons: Points deduction or forced player sales
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.models.season_deficit_record import SeasonDeficitRecord
from app.services.finance_service import FinanceService


class FakeResult:
    """A fake result object that mimics SQLAlchemy's async result."""

    def __init__(self, data=None, scalar_value=None):
        self._data = data
        self._scalar_value = scalar_value

    def all(self):
        return self._data if self._data is not None else []

    def one(self):
        if self._data and len(self._data) > 0:
            return self._data[0]
        return None

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self


class FakeSession:
    """A fake async session that tracks added objects and simulates execute."""

    def __init__(self):
        self.added = []
        self._execute_results = []
        self._execute_index = 0
        self.flushed = False
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    def set_execute_results(self, results):
        """Set a list of FakeResult objects to return in sequence."""
        self._execute_results = results
        self._execute_index = 0

    async def execute(self, stmt):
        if self._execute_index < len(self._execute_results):
            result = self._execute_results[self._execute_index]
            self._execute_index += 1
            return result
        return FakeResult()


@pytest.fixture
def fake_session():
    """Create a fake async database session."""
    return FakeSession()


@pytest.fixture
def finance_service(fake_session):
    """Create a FinanceService instance with fake session."""
    return FinanceService(fake_session)


def _make_deficit_record(season, ended_in_deficit, balance=0, consequence=None):
    """Helper to create a mock SeasonDeficitRecord."""
    record = MagicMock(spec=SeasonDeficitRecord)
    record.id = season  # Use season as ID for simplicity
    record.club_id = 1
    record.career_id = 1
    record.season = season
    record.ended_in_deficit = ended_in_deficit
    record.balance_at_season_end = balance
    record.consequence_applied = consequence
    return record


class TestRecordSeasonEndFinancialStatus:
    """Test record_season_end_financial_status method."""

    @pytest.mark.asyncio
    async def test_records_deficit_when_balance_negative(self, finance_service, fake_session):
        """Records deficit when club balance is negative at season end."""
        fake_session.set_execute_results([
            # Club balance query
            FakeResult(scalar_value=-5_000_000),
            # Check existing record query
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.record_season_end_financial_status(
            club_id=1, career_id=1, season=3
        )

        assert result["club_id"] == 1
        assert result["career_id"] == 1
        assert result["season"] == 3
        assert result["ended_in_deficit"] is True
        assert result["balance_at_season_end"] == -5_000_000
        # Should have added a new record
        assert len(fake_session.added) == 1
        added_record = fake_session.added[0]
        assert added_record.ended_in_deficit is True
        assert added_record.balance_at_season_end == -5_000_000

    @pytest.mark.asyncio
    async def test_records_no_deficit_when_balance_positive(self, finance_service, fake_session):
        """Records no deficit when club balance is positive at season end."""
        fake_session.set_execute_results([
            # Club balance query
            FakeResult(scalar_value=10_000_000),
            # Check existing record query
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.record_season_end_financial_status(
            club_id=1, career_id=1, season=2
        )

        assert result["ended_in_deficit"] is False
        assert result["balance_at_season_end"] == 10_000_000
        added_record = fake_session.added[0]
        assert added_record.ended_in_deficit is False

    @pytest.mark.asyncio
    async def test_records_no_deficit_when_balance_zero(self, finance_service, fake_session):
        """Records no deficit when club balance is exactly zero."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=0),
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.record_season_end_financial_status(
            club_id=1, career_id=1, season=1
        )

        assert result["ended_in_deficit"] is False
        assert result["balance_at_season_end"] == 0

    @pytest.mark.asyncio
    async def test_updates_existing_record(self, finance_service, fake_session):
        """Updates existing record if one already exists for the season."""
        existing_record = MagicMock()
        existing_record.id = 42

        fake_session.set_execute_results([
            # Club balance query
            FakeResult(scalar_value=-2_000_000),
            # Check existing record query - found one
            FakeResult(scalar_value=existing_record),
        ])

        result = await finance_service.record_season_end_financial_status(
            club_id=1, career_id=1, season=2
        )

        assert result["record_id"] == 42
        assert existing_record.ended_in_deficit is True
        assert existing_record.balance_at_season_end == -2_000_000
        # Should NOT have added a new record
        assert len(fake_session.added) == 0

    @pytest.mark.asyncio
    async def test_raises_for_invalid_season(self, finance_service):
        """Raises ValueError for season < 1."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.record_season_end_financial_status(
                club_id=1, career_id=1, season=0
            )

    @pytest.mark.asyncio
    async def test_raises_for_club_not_found(self, finance_service, fake_session):
        """Raises ValueError when club is not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),
        ])

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await finance_service.record_season_end_financial_status(
                club_id=999, career_id=1, season=1
            )


class TestGetDeficitStatus:
    """Test get_deficit_status method."""

    @pytest.mark.asyncio
    async def test_zero_consecutive_deficit_seasons(self, finance_service, fake_session):
        """Returns 0 consecutive deficit seasons when no records exist."""
        fake_session.set_execute_results([
            # Deficit records query - empty
            FakeResult(data=[]),
            # Current balance query
            FakeResult(scalar_value=10_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 0
        assert result["current_consequence"] is None
        assert result["is_currently_in_deficit"] is False
        assert result["deficit_history"] == []

    @pytest.mark.asyncio
    async def test_one_consecutive_deficit_season(self, finance_service, fake_session):
        """Returns 1 consecutive deficit season with warning consequence."""
        records = [
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-1_000_000),
            _make_deficit_record(season=2, ended_in_deficit=False, balance=5_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-1_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 1
        assert result["current_consequence"] == "warning"
        assert result["is_currently_in_deficit"] is True
        assert "WARNING" in result["consequence_description"]

    @pytest.mark.asyncio
    async def test_two_consecutive_deficit_seasons(self, finance_service, fake_session):
        """Returns 2 consecutive deficit seasons with transfer embargo."""
        records = [
            _make_deficit_record(season=4, ended_in_deficit=True, balance=-3_000_000),
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-1_000_000),
            _make_deficit_record(season=2, ended_in_deficit=False, balance=2_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-3_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 2
        assert result["current_consequence"] == "transfer_embargo"
        assert "TRANSFER EMBARGO" in result["consequence_description"]

    @pytest.mark.asyncio
    async def test_three_consecutive_deficit_seasons(self, finance_service, fake_session):
        """Returns 3 consecutive deficit seasons with points deduction."""
        records = [
            _make_deficit_record(season=5, ended_in_deficit=True, balance=-8_000_000),
            _make_deficit_record(season=4, ended_in_deficit=True, balance=-5_000_000),
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-2_000_000),
            _make_deficit_record(season=2, ended_in_deficit=False, balance=1_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-8_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 3
        assert result["current_consequence"] == "points_deduction"
        assert "SEVERE PENALTY" in result["consequence_description"]

    @pytest.mark.asyncio
    async def test_more_than_three_consecutive_deficit_seasons(self, finance_service, fake_session):
        """Returns 4+ consecutive deficit seasons still with points deduction."""
        records = [
            _make_deficit_record(season=6, ended_in_deficit=True, balance=-10_000_000),
            _make_deficit_record(season=5, ended_in_deficit=True, balance=-8_000_000),
            _make_deficit_record(season=4, ended_in_deficit=True, balance=-5_000_000),
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-2_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-10_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 4
        assert result["current_consequence"] == "points_deduction"

    @pytest.mark.asyncio
    async def test_streak_broken_by_positive_season(self, finance_service, fake_session):
        """Streak resets when a non-deficit season is encountered."""
        records = [
            _make_deficit_record(season=5, ended_in_deficit=True, balance=-1_000_000),
            _make_deficit_record(season=4, ended_in_deficit=False, balance=500_000),
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-3_000_000),
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-2_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-1_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        # Only 1 consecutive (season 5), because season 4 broke the streak
        assert result["consecutive_deficit_seasons"] == 1
        assert result["current_consequence"] == "warning"

    @pytest.mark.asyncio
    async def test_deficit_history_limited_to_5(self, finance_service, fake_session):
        """Deficit history returns at most 5 recent seasons."""
        records = [
            _make_deficit_record(season=i, ended_in_deficit=True, balance=-i * 1_000_000)
            for i in range(7, 0, -1)
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-7_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert len(result["deficit_history"]) == 5

    @pytest.mark.asyncio
    async def test_not_currently_in_deficit(self, finance_service, fake_session):
        """is_currently_in_deficit is False when current balance is positive."""
        records = [
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-1_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            # Current balance is now positive (recovered)
            FakeResult(scalar_value=5_000_000),
        ])

        result = await finance_service.get_deficit_status(club_id=1, career_id=1)

        assert result["consecutive_deficit_seasons"] == 1
        assert result["is_currently_in_deficit"] is False


class TestCheckDeficitConsequences:
    """Test check_deficit_consequences method."""

    @pytest.mark.asyncio
    async def test_no_consequences_zero_deficit(self, finance_service, fake_session):
        """No consequences when club has no deficit history."""
        fake_session.set_execute_results([
            # get_deficit_status: deficit records query
            FakeResult(data=[]),
            # get_deficit_status: current balance query
            FakeResult(scalar_value=10_000_000),
        ])

        result = await finance_service.check_deficit_consequences(
            club_id=1, career_id=1, season=1
        )

        assert result["consecutive_deficit_seasons"] == 0
        assert result["consequence_applied"] is None
        assert result["requires_attention"] is False
        assert result["actions_taken"] == []

    @pytest.mark.asyncio
    async def test_warning_after_one_deficit_season(self, finance_service, fake_session):
        """Warning issued after 1 season in deficit."""
        records = [
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-2_000_000),
        ]

        fake_session.set_execute_results([
            # get_deficit_status: deficit records query
            FakeResult(data=records),
            # get_deficit_status: current balance query
            FakeResult(scalar_value=-2_000_000),
            # Update record query
            FakeResult(scalar_value=records[0]),
        ])

        result = await finance_service.check_deficit_consequences(
            club_id=1, career_id=1, season=2
        )

        assert result["consecutive_deficit_seasons"] == 1
        assert result["consequence_applied"] == "warning"
        assert result["requires_attention"] is True
        assert any("Warning" in a for a in result["actions_taken"])

    @pytest.mark.asyncio
    async def test_transfer_embargo_after_two_deficit_seasons(self, finance_service, fake_session):
        """Transfer embargo after 2 consecutive deficit seasons."""
        records = [
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-4_000_000),
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-2_000_000),
        ]

        fake_session.set_execute_results([
            # get_deficit_status: deficit records query
            FakeResult(data=records),
            # get_deficit_status: current balance query
            FakeResult(scalar_value=-4_000_000),
            # Update record query
            FakeResult(scalar_value=records[0]),
        ])

        result = await finance_service.check_deficit_consequences(
            club_id=1, career_id=1, season=3
        )

        assert result["consecutive_deficit_seasons"] == 2
        assert result["consequence_applied"] == "transfer_embargo"
        assert result["requires_attention"] is True
        assert any("embargo" in a.lower() for a in result["actions_taken"])

    @pytest.mark.asyncio
    async def test_points_deduction_after_three_deficit_seasons(self, finance_service, fake_session):
        """Points deduction after 3 consecutive deficit seasons."""
        records = [
            _make_deficit_record(season=4, ended_in_deficit=True, balance=-6_000_000),
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-4_000_000),
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-2_000_000),
        ]

        fake_session.set_execute_results([
            # get_deficit_status: deficit records query
            FakeResult(data=records),
            # get_deficit_status: current balance query
            FakeResult(scalar_value=-6_000_000),
            # Update record query
            FakeResult(scalar_value=records[0]),
        ])

        result = await finance_service.check_deficit_consequences(
            club_id=1, career_id=1, season=4
        )

        assert result["consecutive_deficit_seasons"] == 3
        assert result["consequence_applied"] == "points_deduction"
        assert result["requires_attention"] is True
        assert any("points deduction" in a.lower() for a in result["actions_taken"])
        assert any("force" in a.lower() for a in result["actions_taken"])
        assert any("job security" in a.lower() for a in result["actions_taken"])

    @pytest.mark.asyncio
    async def test_raises_for_invalid_season(self, finance_service):
        """Raises ValueError for season < 1."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.check_deficit_consequences(
                club_id=1, career_id=1, season=0
            )

    @pytest.mark.asyncio
    async def test_consequence_description_contains_season_count(
        self, finance_service, fake_session
    ):
        """Consequence description mentions the number of deficit seasons."""
        records = [
            _make_deficit_record(season=3, ended_in_deficit=True, balance=-3_000_000),
            _make_deficit_record(season=2, ended_in_deficit=True, balance=-1_000_000),
        ]

        fake_session.set_execute_results([
            FakeResult(data=records),
            FakeResult(scalar_value=-3_000_000),
            FakeResult(scalar_value=records[0]),
        ])

        result = await finance_service.check_deficit_consequences(
            club_id=1, career_id=1, season=3
        )

        assert "2" in result["consequence_description"]


class TestGetConsequenceForStreak:
    """Test the _get_consequence_for_streak helper method."""

    def test_zero_streak_no_consequence(self, finance_service):
        """No consequence for 0 deficit seasons."""
        assert finance_service._get_consequence_for_streak(0) is None

    def test_one_streak_warning(self, finance_service):
        """Warning for 1 deficit season."""
        assert finance_service._get_consequence_for_streak(1) == "warning"

    def test_two_streak_transfer_embargo(self, finance_service):
        """Transfer embargo for 2 deficit seasons."""
        assert finance_service._get_consequence_for_streak(2) == "transfer_embargo"

    def test_three_streak_points_deduction(self, finance_service):
        """Points deduction for 3 deficit seasons."""
        assert finance_service._get_consequence_for_streak(3) == "points_deduction"

    def test_four_streak_still_points_deduction(self, finance_service):
        """Points deduction for 4+ deficit seasons (max severity)."""
        assert finance_service._get_consequence_for_streak(4) == "points_deduction"

    def test_ten_streak_still_points_deduction(self, finance_service):
        """Points deduction for very long streaks."""
        assert finance_service._get_consequence_for_streak(10) == "points_deduction"


class TestGetConsequenceDescription:
    """Test the _get_consequence_description helper method."""

    def test_no_consequence_description(self, finance_service):
        """Description for no consequence."""
        desc = finance_service._get_consequence_description(0, None)
        assert "in order" in desc.lower()

    def test_warning_description(self, finance_service):
        """Description for warning consequence."""
        desc = finance_service._get_consequence_description(1, "warning")
        assert "WARNING" in desc
        assert "1" in desc

    def test_embargo_description(self, finance_service):
        """Description for transfer embargo consequence."""
        desc = finance_service._get_consequence_description(2, "transfer_embargo")
        assert "TRANSFER EMBARGO" in desc
        assert "2" in desc

    def test_points_deduction_description(self, finance_service):
        """Description for points deduction consequence."""
        desc = finance_service._get_consequence_description(3, "points_deduction")
        assert "SEVERE PENALTY" in desc
        assert "3" in desc


class TestSeasonDeficitRecordModel:
    """Test the SeasonDeficitRecord model."""

    def test_model_creation(self):
        """Can create a SeasonDeficitRecord instance."""
        record = SeasonDeficitRecord(
            club_id=1,
            career_id=1,
            season=3,
            ended_in_deficit=True,
            balance_at_season_end=-5_000_000,
            consequence_applied="warning",
        )

        assert record.club_id == 1
        assert record.career_id == 1
        assert record.season == 3
        assert record.ended_in_deficit is True
        assert record.balance_at_season_end == -5_000_000
        assert record.consequence_applied == "warning"

    def test_model_to_dict(self):
        """to_dict returns expected fields."""
        record = SeasonDeficitRecord(
            club_id=2,
            career_id=3,
            season=5,
            ended_in_deficit=False,
            balance_at_season_end=10_000_000,
            consequence_applied=None,
        )
        record.id = 42
        record.created_at = None

        d = record.to_dict()
        assert d["id"] == 42
        assert d["club_id"] == 2
        assert d["career_id"] == 3
        assert d["season"] == 5
        assert d["ended_in_deficit"] is False
        assert d["balance_at_season_end"] == 10_000_000
        assert d["consequence_applied"] is None

    def test_model_repr(self):
        """__repr__ returns readable string."""
        record = SeasonDeficitRecord(
            club_id=1,
            career_id=1,
            season=2,
            ended_in_deficit=True,
            balance_at_season_end=-1_000_000,
        )
        record.id = 7

        repr_str = repr(record)
        assert "SeasonDeficitRecord" in repr_str
        assert "club_id=1" in repr_str
        assert "season=2" in repr_str
        assert "ended_in_deficit=True" in repr_str

    def test_model_defaults(self):
        """Model has correct defaults when explicitly set."""
        record = SeasonDeficitRecord(
            club_id=1,
            career_id=1,
            season=1,
            ended_in_deficit=False,
            balance_at_season_end=0,
        )

        assert record.ended_in_deficit is False
        assert record.balance_at_season_end == 0
        assert record.consequence_applied is None
