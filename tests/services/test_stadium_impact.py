"""
Tests for Stadium Impact on Matchday Revenue (Task 12.8)

Tests the InfrastructureService methods:
- get_stadium_revenue_multiplier(club_id) - returns the matchday_revenue_multiplier
- get_stadium_capacity(club_id) - returns the max_capacity

Stadium effects per level:
    - Level 1 (Basic): matchday_revenue_multiplier=1.0, max_capacity=10,000
    - Level 2 (Standard): matchday_revenue_multiplier=1.25, max_capacity=25,000
    - Level 3 (Good): matchday_revenue_multiplier=1.5, max_capacity=40,000
    - Level 4 (Excellent): matchday_revenue_multiplier=1.85, max_capacity=60,000
    - Level 5 (World Class): matchday_revenue_multiplier=2.25, max_capacity=80,000
"""

import pytest

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    CATEGORY_EFFECTS,
    LEVEL_NAMES,
)


class FakeClub:
    """A fake Club object for testing."""

    def __init__(
        self,
        id=1,
        name="Test FC",
        stadium_level=2,
        training_facilities_level=2,
        youth_academy_level=2,
        medical_centre_level=2,
        scouting_network_level=2,
    ):
        self.id = id
        self.name = name
        self.stadium_level = stadium_level
        self.training_facilities_level = training_facilities_level
        self.youth_academy_level = youth_academy_level
        self.medical_centre_level = medical_centre_level
        self.scouting_network_level = scouting_network_level


class FakeResult:
    """A fake result object that mimics SQLAlchemy's async result."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    """A fake async session for testing."""

    def __init__(self, club=None):
        self._club = club

    async def execute(self, stmt):
        return FakeResult(self._club)

    async def commit(self):
        pass


# --- Tests for get_stadium_revenue_multiplier ---


class TestGetStadiumRevenueMultiplier:
    """Test InfrastructureService.get_stadium_revenue_multiplier method."""

    @pytest.mark.asyncio
    async def test_level_1_returns_1_0_multiplier(self):
        """Level 1 (Basic) should return 1.0x revenue multiplier."""
        club = FakeClub(stadium_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_revenue_multiplier(club_id=1)

        assert result == 1.0

    @pytest.mark.asyncio
    async def test_level_2_returns_1_25_multiplier(self):
        """Level 2 (Standard) should return 1.25x revenue multiplier."""
        club = FakeClub(stadium_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_revenue_multiplier(club_id=1)

        assert result == 1.25

    @pytest.mark.asyncio
    async def test_level_3_returns_1_5_multiplier(self):
        """Level 3 (Good) should return 1.5x revenue multiplier."""
        club = FakeClub(stadium_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_revenue_multiplier(club_id=1)

        assert result == 1.5

    @pytest.mark.asyncio
    async def test_level_4_returns_1_85_multiplier(self):
        """Level 4 (Excellent) should return 1.85x revenue multiplier."""
        club = FakeClub(stadium_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_revenue_multiplier(club_id=1)

        assert result == 1.85

    @pytest.mark.asyncio
    async def test_level_5_returns_2_25_multiplier(self):
        """Level 5 (World Class) should return 2.25x revenue multiplier."""
        club = FakeClub(stadium_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_revenue_multiplier(club_id=1)

        assert result == 2.25

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_stadium_revenue_multiplier(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definition."""
        for level in range(1, 6):
            club = FakeClub(stadium_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_stadium_revenue_multiplier(club_id=1)

            expected = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]["matchday_revenue_multiplier"]
            assert result == expected, (
                f"Level {level}: expected multiplier {expected}, got {result}"
            )

    @pytest.mark.asyncio
    async def test_multiplier_increases_with_level(self):
        """Revenue multiplier should strictly increase with each level."""
        multipliers = []
        for level in range(1, 6):
            club = FakeClub(stadium_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_stadium_revenue_multiplier(club_id=1)
            multipliers.append(result)

        for i in range(1, len(multipliers)):
            assert multipliers[i] > multipliers[i - 1], (
                f"Multiplier at level {i + 1} ({multipliers[i]}) should be greater "
                f"than level {i} ({multipliers[i - 1]})"
            )


# --- Tests for get_stadium_capacity ---


class TestGetStadiumCapacity:
    """Test InfrastructureService.get_stadium_capacity method."""

    @pytest.mark.asyncio
    async def test_level_1_returns_10000_capacity(self):
        """Level 1 (Basic) should return 10,000 capacity."""
        club = FakeClub(stadium_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_capacity(club_id=1)

        assert result == 10_000

    @pytest.mark.asyncio
    async def test_level_2_returns_25000_capacity(self):
        """Level 2 (Standard) should return 25,000 capacity."""
        club = FakeClub(stadium_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_capacity(club_id=1)

        assert result == 25_000

    @pytest.mark.asyncio
    async def test_level_3_returns_40000_capacity(self):
        """Level 3 (Good) should return 40,000 capacity."""
        club = FakeClub(stadium_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_capacity(club_id=1)

        assert result == 40_000

    @pytest.mark.asyncio
    async def test_level_4_returns_60000_capacity(self):
        """Level 4 (Excellent) should return 60,000 capacity."""
        club = FakeClub(stadium_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_capacity(club_id=1)

        assert result == 60_000

    @pytest.mark.asyncio
    async def test_level_5_returns_80000_capacity(self):
        """Level 5 (World Class) should return 80,000 capacity."""
        club = FakeClub(stadium_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_stadium_capacity(club_id=1)

        assert result == 80_000

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_stadium_capacity(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definition."""
        for level in range(1, 6):
            club = FakeClub(stadium_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_stadium_capacity(club_id=1)

            expected = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]["max_capacity"]
            assert result == expected, (
                f"Level {level}: expected capacity {expected}, got {result}"
            )

    @pytest.mark.asyncio
    async def test_capacity_increases_with_level(self):
        """Stadium capacity should strictly increase with each level."""
        capacities = []
        for level in range(1, 6):
            club = FakeClub(stadium_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_stadium_capacity(club_id=1)
            capacities.append(result)

        for i in range(1, len(capacities)):
            assert capacities[i] > capacities[i - 1], (
                f"Capacity at level {i + 1} ({capacities[i]}) should be greater "
                f"than level {i} ({capacities[i - 1]})"
            )

    @pytest.mark.asyncio
    async def test_capacity_returns_integer(self):
        """Stadium capacity should always be an integer."""
        for level in range(1, 6):
            club = FakeClub(stadium_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_stadium_capacity(club_id=1)

            assert isinstance(result, int), (
                f"Level {level}: capacity should be int, got {type(result)}"
            )
