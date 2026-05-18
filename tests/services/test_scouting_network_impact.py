"""
Tests for Scouting Network Impact on Attribute Accuracy (Task 12.7)

Tests the InfrastructureService methods:
- get_scouting_network_accuracy(club_id) - returns attribute_accuracy_percent and scouting_speed_bonus
- calculate_revealed_attribute_accuracy(true_value, club_id) - applies noise based on accuracy level

Scouting Network accuracy per level:
    - Level 1 (Basic): attribute_accuracy_percent=60, scouting_speed_bonus=0
    - Level 2 (Standard): attribute_accuracy_percent=70, scouting_speed_bonus=10
    - Level 3 (Good): attribute_accuracy_percent=80, scouting_speed_bonus=20
    - Level 4 (Excellent): attribute_accuracy_percent=90, scouting_speed_bonus=30
    - Level 5 (World Class): attribute_accuracy_percent=95, scouting_speed_bonus=40

Accuracy formula:
    max_deviation = max(1, (100 - attribute_accuracy_percent) // 10)
    - 60% accuracy: ±4 deviation
    - 70% accuracy: ±3 deviation
    - 80% accuracy: ±2 deviation
    - 90% accuracy: ±1 deviation
    - 95% accuracy: ±1 deviation
"""

import pytest
from unittest.mock import patch

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
        scouting_network_level=2,
        stadium_level=2,
        training_facilities_level=2,
        youth_academy_level=2,
        medical_centre_level=2,
    ):
        self.id = id
        self.name = name
        self.scouting_network_level = scouting_network_level
        self.stadium_level = stadium_level
        self.training_facilities_level = training_facilities_level
        self.youth_academy_level = youth_academy_level
        self.medical_centre_level = medical_centre_level


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


# --- Tests for get_scouting_network_accuracy ---


class TestGetScoutingNetworkAccuracy:
    """Test InfrastructureService.get_scouting_network_accuracy method."""

    @pytest.mark.asyncio
    async def test_level_1_returns_60_percent_accuracy(self):
        """Level 1 (Basic) should return 60% attribute accuracy."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_scouting_network_accuracy(club_id=1)

        assert result["attribute_accuracy_percent"] == 60
        assert result["scouting_speed_bonus"] == 0
        assert result["level"] == 1
        assert result["level_name"] == "Basic"

    @pytest.mark.asyncio
    async def test_level_2_returns_70_percent_accuracy(self):
        """Level 2 (Standard) should return 70% attribute accuracy."""
        club = FakeClub(scouting_network_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_scouting_network_accuracy(club_id=1)

        assert result["attribute_accuracy_percent"] == 70
        assert result["scouting_speed_bonus"] == 10
        assert result["level"] == 2
        assert result["level_name"] == "Standard"

    @pytest.mark.asyncio
    async def test_level_3_returns_80_percent_accuracy(self):
        """Level 3 (Good) should return 80% attribute accuracy."""
        club = FakeClub(scouting_network_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_scouting_network_accuracy(club_id=1)

        assert result["attribute_accuracy_percent"] == 80
        assert result["scouting_speed_bonus"] == 20
        assert result["level"] == 3
        assert result["level_name"] == "Good"

    @pytest.mark.asyncio
    async def test_level_4_returns_90_percent_accuracy(self):
        """Level 4 (Excellent) should return 90% attribute accuracy."""
        club = FakeClub(scouting_network_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_scouting_network_accuracy(club_id=1)

        assert result["attribute_accuracy_percent"] == 90
        assert result["scouting_speed_bonus"] == 30
        assert result["level"] == 4
        assert result["level_name"] == "Excellent"

    @pytest.mark.asyncio
    async def test_level_5_returns_95_percent_accuracy(self):
        """Level 5 (World Class) should return 95% attribute accuracy."""
        club = FakeClub(scouting_network_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_scouting_network_accuracy(club_id=1)

        assert result["attribute_accuracy_percent"] == 95
        assert result["scouting_speed_bonus"] == 40
        assert result["level"] == 5
        assert result["level_name"] == "World Class"

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_scouting_network_accuracy(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definition."""
        for level in range(1, 6):
            club = FakeClub(scouting_network_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_scouting_network_accuracy(club_id=1)

            expected_effects = CATEGORY_EFFECTS[InfrastructureCategory.SCOUTING_NETWORK][level]
            assert result["attribute_accuracy_percent"] == expected_effects["attribute_accuracy_percent"], (
                f"Level {level}: accuracy mismatch"
            )
            assert result["scouting_speed_bonus"] == expected_effects["scouting_speed_bonus"], (
                f"Level {level}: speed bonus mismatch"
            )
            assert result["level"] == level
            assert result["level_name"] == LEVEL_NAMES[level]


# --- Tests for calculate_revealed_attribute_accuracy ---


class TestCalculateRevealedAttributeAccuracy:
    """Test InfrastructureService.calculate_revealed_attribute_accuracy method."""

    @pytest.mark.asyncio
    async def test_level_1_max_deviation_is_4(self):
        """Level 1 (60% accuracy): max deviation should be ±4."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        # Run multiple times to verify deviation range
        results = set()
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            # Test max positive deviation
            mock_randint.return_value = 4
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 14

            # Test max negative deviation
            mock_randint.return_value = -4
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 6

            # Verify randint was called with correct range
            mock_randint.assert_called_with(-4, 4)

    @pytest.mark.asyncio
    async def test_level_2_max_deviation_is_3(self):
        """Level 2 (70% accuracy): max deviation should be ±3."""
        club = FakeClub(scouting_network_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = 3
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 13
            mock_randint.assert_called_with(-3, 3)

    @pytest.mark.asyncio
    async def test_level_3_max_deviation_is_2(self):
        """Level 3 (80% accuracy): max deviation should be ±2."""
        club = FakeClub(scouting_network_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = -2
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 8
            mock_randint.assert_called_with(-2, 2)

    @pytest.mark.asyncio
    async def test_level_4_max_deviation_is_1(self):
        """Level 4 (90% accuracy): max deviation should be ±1."""
        club = FakeClub(scouting_network_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = 1
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 11
            mock_randint.assert_called_with(-1, 1)

    @pytest.mark.asyncio
    async def test_level_5_max_deviation_is_1(self):
        """Level 5 (95% accuracy): max deviation should be ±1."""
        club = FakeClub(scouting_network_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = -1
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 9
            mock_randint.assert_called_with(-1, 1)

    @pytest.mark.asyncio
    async def test_clamped_to_minimum_1(self):
        """Revealed value should never go below 1."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 1  # Minimum attribute value
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = -4  # Max negative deviation
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            # 1 + (-4) = -3, clamped to 1
            assert result == 1

    @pytest.mark.asyncio
    async def test_clamped_to_maximum_20(self):
        """Revealed value should never go above 20."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 20  # Maximum attribute value
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = 4  # Max positive deviation
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            # 20 + 4 = 24, clamped to 20
            assert result == 20

    @pytest.mark.asyncio
    async def test_zero_noise_returns_true_value(self):
        """When noise is 0, revealed value equals true value."""
        club = FakeClub(scouting_network_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 15
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = 0
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 15

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.calculate_revealed_attribute_accuracy(true_value=10, club_id=999)

    @pytest.mark.asyncio
    async def test_statistical_distribution_level_1(self):
        """Level 1: over many runs, revealed values should stay within ±4 of true value."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        results = []
        for _ in range(200):
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            results.append(result)

        # All results should be within ±4 of true value
        for r in results:
            assert 6 <= r <= 14, f"Result {r} outside expected range [6, 14]"

    @pytest.mark.asyncio
    async def test_statistical_distribution_level_5(self):
        """Level 5: over many runs, revealed values should stay within ±1 of true value."""
        club = FakeClub(scouting_network_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 10
        results = []
        for _ in range(200):
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            results.append(result)

        # All results should be within ±1 of true value
        for r in results:
            assert 9 <= r <= 11, f"Result {r} outside expected range [9, 11]"

    @pytest.mark.asyncio
    async def test_boundary_value_at_low_end(self):
        """Test with true_value=2 at level 1: should clamp to minimum 1."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 2
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = -4
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            # 2 + (-4) = -2, clamped to 1
            assert result == 1

    @pytest.mark.asyncio
    async def test_boundary_value_at_high_end(self):
        """Test with true_value=18 at level 1: should clamp to maximum 20."""
        club = FakeClub(scouting_network_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 18
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = 4
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            # 18 + 4 = 22, clamped to 20
            assert result == 20

    @pytest.mark.asyncio
    async def test_mid_range_value_no_clamping(self):
        """Test with mid-range value that doesn't need clamping."""
        club = FakeClub(scouting_network_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        true_value = 12
        with patch("app.services.infrastructure_service.random.randint") as mock_randint:
            mock_randint.return_value = -2
            result = await service.calculate_revealed_attribute_accuracy(true_value, club_id=1)
            assert result == 10
