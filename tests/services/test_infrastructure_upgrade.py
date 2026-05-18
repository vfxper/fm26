"""
Tests for Infrastructure Upgrade Request System (Task 12.3)

Tests the upgrade request methods in InfrastructureService:
- request_upgrade: validates, checks affordability, creates upgrade
- check_upgrade_progress: detects completed upgrades
- get_active_upgrades: returns in-progress upgrades
- complete_upgrade: completes upgrade and increases level
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    LEVEL_NAMES,
    UPGRADE_COSTS,
    UPGRADE_DURATIONS,
)
from app.models.infrastructure_upgrade import InfrastructureUpgrade, UpgradeStatus


class FakeClub:
    """A fake Club object for testing."""

    def __init__(
        self,
        id=1,
        name="Test FC",
        balance=50_000_000,
        stadium_level=2,
        training_facilities_level=3,
        youth_academy_level=1,
        medical_centre_level=4,
        scouting_network_level=2,
    ):
        self.id = id
        self.name = name
        self.balance = balance
        self.stadium_level = stadium_level
        self.training_facilities_level = training_facilities_level
        self.youth_academy_level = youth_academy_level
        self.medical_centre_level = medical_centre_level
        self.scouting_network_level = scouting_network_level


class FakeUpgrade:
    """A fake InfrastructureUpgrade object for testing."""

    def __init__(
        self,
        id=1,
        club_id=1,
        career_id=1,
        category="stadium",
        from_level=2,
        to_level=3,
        cost=15_000_000,
        duration_weeks=14,
        start_season=1,
        start_week=5,
        completion_season=1,
        completion_week=19,
        status=UpgradeStatus.IN_PROGRESS.value,
        created_at=None,
        completed_at=None,
    ):
        self.id = id
        self.club_id = club_id
        self.career_id = career_id
        self.category = category
        self.from_level = from_level
        self.to_level = to_level
        self.cost = cost
        self.duration_weeks = duration_weeks
        self.start_season = start_season
        self.start_week = start_week
        self.completion_season = completion_season
        self.completion_week = completion_week
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.completed_at = completed_at

    def to_dict(self):
        return {
            "id": self.id,
            "club_id": self.club_id,
            "career_id": self.career_id,
            "category": self.category,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "cost": self.cost,
            "duration_weeks": self.duration_weeks,
            "start_season": self.start_season,
            "start_week": self.start_week,
            "completion_season": self.completion_season,
            "completion_week": self.completion_week,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class FakeScalarResult:
    """Mimics SQLAlchemy scalar result."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeScalarsResult:
    """Mimics SQLAlchemy scalars() result."""

    def __init__(self, items=None):
        self._items = items or []

    def all(self):
        return self._items


class FakeExecuteResult:
    """Mimics SQLAlchemy execute result with scalars()."""

    def __init__(self, value=None, items=None):
        self._value = value
        self._items = items

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return FakeScalarsResult(self._items or [])

    def scalar(self):
        return self._value


class FakeSession:
    """A fake async session for testing upgrade methods.

    Uses a call-order based approach to return different results
    for sequential queries.
    """

    def __init__(self, club=None, upgrades=None, balance=None, responses=None):
        self._club = club
        self._upgrades = upgrades or []
        self._balance = balance
        self._added = []
        self._responses = responses or []
        self._call_index = 0

    async def execute(self, stmt):
        """Return responses in order if provided, otherwise use defaults."""
        if self._responses:
            if self._call_index < len(self._responses):
                resp = self._responses[self._call_index]
                self._call_index += 1
                return resp
            # Fallback to last response
            return self._responses[-1]

        # Default behavior: return club
        return FakeExecuteResult(value=self._club)

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        pass


# --- Test request_upgrade ---


class TestRequestUpgrade:
    """Test the request_upgrade method."""

    @pytest.mark.asyncio
    async def test_successful_upgrade_request(self):
        """Should approve upgrade when all conditions are met."""
        club = FakeClub(stadium_level=2, balance=50_000_000)
        # Calls: 1) _get_club, 2) _get_active_upgrade_for_category (scalar_one_or_none),
        # 3) validate_expenditure (select Club.balance -> scalar_one_or_none returns int),
        # 4) record_expenditure -> _update_club_balance (select Club -> scalar_one_or_none returns Club)
        responses = [
            FakeExecuteResult(value=club),  # _get_club
            FakeExecuteResult(value=None),  # _get_active_upgrade_for_category
            FakeScalarResult(value=50_000_000),  # validate_expenditure -> Club.balance
            FakeExecuteResult(value=club),  # _update_club_balance -> select(Club)
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.request_upgrade(
            club_id=1,
            career_id=1,
            category=InfrastructureCategory.STADIUM,
            season=1,
            week=5,
        )

        assert result["success"] is True
        assert "approved" in result["message"].lower() or "Approved" in result["message"]
        assert result["upgrade"] is not None

    @pytest.mark.asyncio
    async def test_rejects_at_max_level(self):
        """Should reject upgrade when category is already at level 5."""
        club = FakeClub(stadium_level=5)
        responses = [
            FakeExecuteResult(value=club),  # _get_club
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.request_upgrade(
            club_id=1,
            career_id=1,
            category=InfrastructureCategory.STADIUM,
            season=1,
            week=5,
        )

        assert result["success"] is False
        assert "maximum level" in result["message"].lower()
        assert result["upgrade"] is None

    @pytest.mark.asyncio
    async def test_rejects_when_upgrade_in_progress(self):
        """Should reject when there's already an upgrade in progress for the category."""
        club = FakeClub(stadium_level=2, balance=50_000_000)
        existing_upgrade = FakeUpgrade(
            category="stadium",
            status=UpgradeStatus.IN_PROGRESS.value,
        )
        responses = [
            FakeExecuteResult(value=club),  # _get_club
            FakeExecuteResult(value=existing_upgrade),  # _get_active_upgrade_for_category
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.request_upgrade(
            club_id=1,
            career_id=1,
            category=InfrastructureCategory.STADIUM,
            season=1,
            week=10,
        )

        assert result["success"] is False
        assert "already has an upgrade in progress" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_rejects_when_cannot_afford(self):
        """Should reject when club cannot afford the upgrade."""
        club = FakeClub(stadium_level=2, balance=1_000)
        responses = [
            FakeExecuteResult(value=club),  # _get_club
            FakeExecuteResult(value=None),  # _get_active_upgrade_for_category (none)
            FakeScalarResult(value=1_000),  # validate_expenditure -> balance
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.request_upgrade(
            club_id=1,
            career_id=1,
            category=InfrastructureCategory.STADIUM,
            season=1,
            week=5,
        )

        assert result["success"] is False
        assert result["upgrade"] is None

    @pytest.mark.asyncio
    async def test_rejects_invalid_category(self):
        """Should raise ValueError for invalid category."""
        session = FakeSession(responses=[])
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Invalid category"):
            await service.request_upgrade(
                club_id=1,
                career_id=1,
                category="invalid",
                season=1,
                week=5,
            )

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        responses = [
            FakeExecuteResult(value=None),  # _get_club returns None
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.request_upgrade(
                club_id=999,
                career_id=1,
                category=InfrastructureCategory.STADIUM,
                season=1,
                week=5,
            )


# --- Test _calculate_completion_date ---


class TestCalculateCompletionDate:
    """Test the _calculate_completion_date helper method."""

    def test_same_season_completion(self):
        """Upgrade within same season should stay in same season."""
        session = FakeSession()
        service = InfrastructureService(session)

        season, week = service._calculate_completion_date(
            start_season=1, start_week=5, duration_weeks=10
        )

        assert season == 1
        assert week == 15

    def test_crosses_season_boundary(self):
        """Upgrade crossing season boundary should increment season."""
        session = FakeSession()
        service = InfrastructureService(session)

        # Start at week 45, duration 14 weeks -> week 45+14=59 -> season 2, week 7
        season, week = service._calculate_completion_date(
            start_season=1, start_week=45, duration_weeks=14
        )

        assert season == 2
        assert week == 7

    def test_exact_season_end(self):
        """Upgrade ending exactly at week 52 should stay in same season."""
        session = FakeSession()
        service = InfrastructureService(session)

        season, week = service._calculate_completion_date(
            start_season=1, start_week=48, duration_weeks=4
        )

        assert season == 1
        assert week == 52

    def test_multiple_season_crossings(self):
        """Very long upgrade crossing multiple seasons."""
        session = FakeSession()
        service = InfrastructureService(session)

        # Start at week 50, duration 26 weeks -> 50+26=76 -> season 2, week 24
        season, week = service._calculate_completion_date(
            start_season=1, start_week=50, duration_weeks=26
        )

        assert season == 2
        assert week == 24

    def test_start_at_week_1(self):
        """Upgrade starting at week 1."""
        session = FakeSession()
        service = InfrastructureService(session)

        season, week = service._calculate_completion_date(
            start_season=1, start_week=1, duration_weeks=4
        )

        assert season == 1
        assert week == 5


# --- Test _is_upgrade_due ---


class TestIsUpgradeDue:
    """Test the _is_upgrade_due helper method."""

    def test_not_due_before_completion(self):
        """Upgrade should not be due before completion date."""
        session = FakeSession()
        service = InfrastructureService(session)

        upgrade = FakeUpgrade(completion_season=1, completion_week=20)

        assert service._is_upgrade_due(upgrade, current_season=1, current_week=15) is False

    def test_due_at_completion_week(self):
        """Upgrade should be due at exact completion date."""
        session = FakeSession()
        service = InfrastructureService(session)

        upgrade = FakeUpgrade(completion_season=1, completion_week=20)

        assert service._is_upgrade_due(upgrade, current_season=1, current_week=20) is True

    def test_due_after_completion_week(self):
        """Upgrade should be due after completion date."""
        session = FakeSession()
        service = InfrastructureService(session)

        upgrade = FakeUpgrade(completion_season=1, completion_week=20)

        assert service._is_upgrade_due(upgrade, current_season=1, current_week=25) is True

    def test_due_in_later_season(self):
        """Upgrade should be due if current season is past completion season."""
        session = FakeSession()
        service = InfrastructureService(session)

        upgrade = FakeUpgrade(completion_season=1, completion_week=50)

        assert service._is_upgrade_due(upgrade, current_season=2, current_week=1) is True

    def test_not_due_earlier_week_same_season(self):
        """Upgrade should not be due if same season but earlier week."""
        session = FakeSession()
        service = InfrastructureService(session)

        upgrade = FakeUpgrade(completion_season=2, completion_week=10)

        assert service._is_upgrade_due(upgrade, current_season=2, current_week=5) is False


# --- Test complete_upgrade ---


class TestCompleteUpgrade:
    """Test the complete_upgrade method."""

    @pytest.mark.asyncio
    async def test_completes_upgrade_and_updates_level(self):
        """Should mark upgrade as completed and update club level."""
        club = FakeClub(stadium_level=2)
        upgrade = FakeUpgrade(
            id=1,
            club_id=1,
            category="stadium",
            from_level=2,
            to_level=3,
            status=UpgradeStatus.IN_PROGRESS.value,
        )

        responses = [
            FakeExecuteResult(value=upgrade),  # get upgrade by id
            FakeExecuteResult(value=club),  # _get_club
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.complete_upgrade(upgrade_id=1)

        assert result is not None
        assert result["upgrade_id"] == 1
        assert result["category"] == "stadium"
        assert result["to_level"] == 3
        assert result["new_level_name"] == "Good"
        # Club level should be updated
        assert club.stadium_level == 3
        # Upgrade status should be completed
        assert upgrade.status == UpgradeStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_upgrade(self):
        """Should return None if upgrade ID doesn't exist."""
        responses = [
            FakeExecuteResult(value=None),  # get upgrade by id -> not found
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.complete_upgrade(upgrade_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_already_completed(self):
        """Should return None if upgrade is already completed."""
        upgrade = FakeUpgrade(
            id=1,
            status=UpgradeStatus.COMPLETED.value,
        )

        responses = [
            FakeExecuteResult(value=upgrade),  # get upgrade by id
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.complete_upgrade(upgrade_id=1)

        assert result is None


# --- Test get_active_upgrades ---


class TestGetActiveUpgrades:
    """Test the get_active_upgrades method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_upgrades(self):
        """Should return empty list when no upgrades are in progress."""
        responses = [
            FakeExecuteResult(items=[]),  # query for active upgrades
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.get_active_upgrades(club_id=1, career_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_active_upgrades(self):
        """Should return list of in-progress upgrades."""
        upgrade1 = FakeUpgrade(id=1, category="stadium")
        upgrade2 = FakeUpgrade(id=2, category="training_facilities")

        responses = [
            FakeExecuteResult(items=[upgrade1, upgrade2]),  # query for active upgrades
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.get_active_upgrades(club_id=1, career_id=1)

        assert len(result) == 2
        assert result[0]["category"] == "stadium"
        assert result[1]["category"] == "training_facilities"


# --- Test check_upgrade_progress ---


class TestCheckUpgradeProgress:
    """Test the check_upgrade_progress method."""

    @pytest.mark.asyncio
    async def test_no_upgrades_returns_empty(self):
        """Should return empty lists when no upgrades exist."""
        responses = [
            FakeExecuteResult(items=[]),  # query for active upgrades
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.check_upgrade_progress(
            club_id=1, career_id=1, season=1, week=10
        )

        assert result["completed_upgrades"] == []
        assert result["still_in_progress"] == []

    @pytest.mark.asyncio
    async def test_detects_due_upgrade(self):
        """Should detect and complete upgrades that are due."""
        club = FakeClub(stadium_level=2)
        upgrade = FakeUpgrade(
            id=1,
            club_id=1,
            category="stadium",
            from_level=2,
            to_level=3,
            completion_season=1,
            completion_week=10,
            status=UpgradeStatus.IN_PROGRESS.value,
        )

        responses = [
            FakeExecuteResult(items=[upgrade]),  # check_upgrade_progress: get active upgrades
            FakeExecuteResult(value=upgrade),  # complete_upgrade: get upgrade by id
            FakeExecuteResult(value=club),  # complete_upgrade: _get_club
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.check_upgrade_progress(
            club_id=1, career_id=1, season=1, week=10
        )

        assert len(result["completed_upgrades"]) == 1
        assert result["completed_upgrades"][0]["category"] == "stadium"
        assert result["completed_upgrades"][0]["to_level"] == 3

    @pytest.mark.asyncio
    async def test_keeps_not_due_upgrades_in_progress(self):
        """Should keep upgrades that aren't due yet in the in-progress list."""
        upgrade = FakeUpgrade(
            id=1,
            category="stadium",
            completion_season=1,
            completion_week=30,
            status=UpgradeStatus.IN_PROGRESS.value,
        )

        responses = [
            FakeExecuteResult(items=[upgrade]),  # get active upgrades
        ]
        session = FakeSession(responses=responses)
        service = InfrastructureService(session)

        result = await service.check_upgrade_progress(
            club_id=1, career_id=1, season=1, week=10
        )

        assert result["completed_upgrades"] == []
        assert len(result["still_in_progress"]) == 1
