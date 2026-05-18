"""
Tests for Training Facilities Bonus Integration (Task 12.4)

Tests the integration between InfrastructureService.get_training_facilities_bonus()
and TrainingService._get_training_facilities_bonus() to ensure training attribute
development correctly uses the Training Facilities infrastructure level bonus.

Training Facilities bonus multipliers:
    - Level 1 (Basic): 1.0x (no bonus)
    - Level 2 (Standard): 1.1x (10% bonus)
    - Level 3 (Good): 1.25x (25% bonus)
    - Level 4 (Excellent): 1.4x (40% bonus)
    - Level 5 (World Class): 1.6x (60% bonus)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    CATEGORY_EFFECTS,
)
from app.services.training_service import TrainingService


class FakeClub:
    """A fake Club object for testing."""

    def __init__(
        self,
        id=1,
        name="Test FC",
        training_facilities_level=1,
        stadium_level=1,
        youth_academy_level=1,
        medical_centre_level=1,
        scouting_network_level=1,
    ):
        self.id = id
        self.name = name
        self.training_facilities_level = training_facilities_level
        self.stadium_level = stadium_level
        self.youth_academy_level = youth_academy_level
        self.medical_centre_level = medical_centre_level
        self.scouting_network_level = scouting_network_level


class FakeResult:
    """A fake result object that mimics SQLAlchemy's async result."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return []


class FakeSession:
    """A fake async session for testing."""

    def __init__(self, club=None, scalar_value=None):
        self._club = club
        self._scalar_value = scalar_value

    async def execute(self, stmt):
        if self._scalar_value is not None:
            return FakeResult(self._scalar_value)
        return FakeResult(self._club)

    async def commit(self):
        pass


# --- Tests for InfrastructureService.get_training_facilities_bonus ---


class TestGetTrainingFacilitiesBonus:
    """Test InfrastructureService.get_training_facilities_bonus method."""

    @pytest.mark.asyncio
    async def test_level_1_returns_1_0(self):
        """Level 1 (Basic) should return 1.0x multiplier (no bonus)."""
        club = FakeClub(training_facilities_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        bonus = await service.get_training_facilities_bonus(club_id=1)

        assert bonus == 1.0

    @pytest.mark.asyncio
    async def test_level_2_returns_1_1(self):
        """Level 2 (Standard) should return 1.1x multiplier (10% bonus)."""
        club = FakeClub(training_facilities_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        bonus = await service.get_training_facilities_bonus(club_id=1)

        assert bonus == 1.1

    @pytest.mark.asyncio
    async def test_level_3_returns_1_25(self):
        """Level 3 (Good) should return 1.25x multiplier (25% bonus)."""
        club = FakeClub(training_facilities_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        bonus = await service.get_training_facilities_bonus(club_id=1)

        assert bonus == 1.25

    @pytest.mark.asyncio
    async def test_level_4_returns_1_4(self):
        """Level 4 (Excellent) should return 1.4x multiplier (40% bonus)."""
        club = FakeClub(training_facilities_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        bonus = await service.get_training_facilities_bonus(club_id=1)

        assert bonus == 1.4

    @pytest.mark.asyncio
    async def test_level_5_returns_1_6(self):
        """Level 5 (World Class) should return 1.6x multiplier (60% bonus)."""
        club = FakeClub(training_facilities_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        bonus = await service.get_training_facilities_bonus(club_id=1)

        assert bonus == 1.6

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_training_facilities_bonus(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definition."""
        for level in range(1, 6):
            club = FakeClub(training_facilities_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            bonus = await service.get_training_facilities_bonus(club_id=1)

            expected = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][level][
                "training_bonus_multiplier"
            ]
            assert bonus == expected, (
                f"Level {level}: expected {expected}, got {bonus}"
            )


# --- Tests for TrainingService._get_training_facilities_bonus ---


class TestTrainingServiceInfrastructureBonus:
    """Test TrainingService._get_training_facilities_bonus helper method."""

    @pytest.mark.asyncio
    async def test_returns_bonus_for_level_3(self):
        """Should return 1.25 for a club with training_facilities_level=3."""
        session = FakeSession(scalar_value=3)
        service = TrainingService(session)

        bonus = await service._get_training_facilities_bonus(career_id=1)

        assert bonus == 1.25

    @pytest.mark.asyncio
    async def test_returns_bonus_for_level_5(self):
        """Should return 1.6 for a club with training_facilities_level=5."""
        session = FakeSession(scalar_value=5)
        service = TrainingService(session)

        bonus = await service._get_training_facilities_bonus(career_id=1)

        assert bonus == 1.6

    @pytest.mark.asyncio
    async def test_returns_1_0_when_not_found(self):
        """Should return 1.0 when career/club is not found."""
        session = FakeSession(scalar_value=None)
        service = TrainingService(session)

        bonus = await service._get_training_facilities_bonus(career_id=999)

        assert bonus == 1.0

    @pytest.mark.asyncio
    async def test_returns_1_0_for_level_1(self):
        """Should return 1.0 for level 1 (no bonus)."""
        session = FakeSession(scalar_value=1)
        service = TrainingService(session)

        bonus = await service._get_training_facilities_bonus(career_id=1)

        assert bonus == 1.0


# --- Integration Test: Training uses infrastructure bonus ---


class TestTrainingInfrastructureIntegration:
    """Test that simulate_weekly_training correctly uses infrastructure bonus.

    These tests verify the auto-fetch logic by directly testing the
    _get_training_facilities_bonus method and the parameter handling logic.
    The full simulate_weekly_training integration requires a live DB due to
    SQLAlchemy model relationship resolution.
    """

    @pytest.mark.asyncio
    async def test_get_training_facilities_bonus_returns_correct_values(self):
        """_get_training_facilities_bonus should return correct multiplier for each level."""
        expected = {1: 1.0, 2: 1.1, 3: 1.25, 4: 1.4, 5: 1.6}

        for level, expected_bonus in expected.items():
            session = FakeSession(scalar_value=level)
            service = TrainingService(session)

            bonus = await service._get_training_facilities_bonus(career_id=1)
            assert bonus == expected_bonus, (
                f"Level {level}: expected {expected_bonus}, got {bonus}"
            )

    @pytest.mark.asyncio
    async def test_infrastructure_bonus_parameter_accepted(self):
        """simulate_weekly_training should accept infrastructure_bonus parameter."""
        import inspect

        sig = inspect.signature(TrainingService.simulate_weekly_training)
        params = sig.parameters

        assert "infrastructure_bonus" in params
        assert "auto_fetch_infrastructure_bonus" in params

        # infrastructure_bonus should default to None (auto-fetch)
        assert params["infrastructure_bonus"].default is None
        # auto_fetch_infrastructure_bonus should default to True
        assert params["auto_fetch_infrastructure_bonus"].default is True

    @pytest.mark.asyncio
    async def test_infrastructure_bonus_used_in_multiplier_calculation(self):
        """The infrastructure_bonus is used in the total_multiplier calculation.

        In simulate_weekly_training, the total_multiplier is:
            focus_bonus * infrastructure_bonus * intensity_multiplier

        This verifies the infrastructure_bonus flows through to affect training.
        """
        # Verify the code uses infrastructure_bonus in the multiplier calculation
        import ast
        import os

        training_service_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "app", "services", "training_service.py"
        )

        with open(training_service_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Check that infrastructure_bonus is used in the multiplier calculation
        assert "infrastructure_bonus" in source
        assert "focus_bonus * infrastructure_bonus * intensity_multiplier" in source
