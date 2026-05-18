"""
Tests for Medical Centre Impact on Injury Recovery (Task 12.6)

Tests the InfrastructureService methods:
- get_medical_centre_recovery_reduction(club_id) - returns recovery time reduction %
- calculate_adjusted_recovery_weeks(base_weeks, club_id) - applies reduction to base time

Medical Centre recovery time reduction per level:
    - Level 1 (Basic): 0% reduction
    - Level 2 (Standard): 0% reduction (baseline)
    - Level 3 (Good): 10% reduction (1 level above Standard)
    - Level 4 (Excellent): 20% reduction (2 levels above Standard)
    - Level 5 (World Class): 30% reduction (3 levels above Standard)

Formula: adjusted_weeks = max(1, round(base_weeks * (1 - reduction_percent/100)))
"""

import pytest

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    CATEGORY_EFFECTS,
)


class FakeClub:
    """A fake Club object for testing."""

    def __init__(
        self,
        id=1,
        name="Test FC",
        medical_centre_level=2,
        stadium_level=2,
        training_facilities_level=2,
        youth_academy_level=2,
        scouting_network_level=2,
    ):
        self.id = id
        self.name = name
        self.medical_centre_level = medical_centre_level
        self.stadium_level = stadium_level
        self.training_facilities_level = training_facilities_level
        self.youth_academy_level = youth_academy_level
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


# --- Tests for get_medical_centre_recovery_reduction ---


class TestGetMedicalCentreRecoveryReduction:
    """Test InfrastructureService.get_medical_centre_recovery_reduction method."""

    @pytest.mark.asyncio
    async def test_level_1_returns_0_percent(self):
        """Level 1 (Basic) should return 0% reduction."""
        club = FakeClub(medical_centre_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

        assert reduction == 0

    @pytest.mark.asyncio
    async def test_level_2_returns_0_percent(self):
        """Level 2 (Standard/baseline) should return 0% reduction."""
        club = FakeClub(medical_centre_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

        assert reduction == 0

    @pytest.mark.asyncio
    async def test_level_3_returns_10_percent(self):
        """Level 3 (Good) should return 10% reduction."""
        club = FakeClub(medical_centre_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

        assert reduction == 10

    @pytest.mark.asyncio
    async def test_level_4_returns_20_percent(self):
        """Level 4 (Excellent) should return 20% reduction."""
        club = FakeClub(medical_centre_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

        assert reduction == 20

    @pytest.mark.asyncio
    async def test_level_5_returns_30_percent(self):
        """Level 5 (World Class) should return 30% reduction."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

        assert reduction == 30

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_medical_centre_recovery_reduction(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definition."""
        for level in range(1, 6):
            club = FakeClub(medical_centre_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            reduction = await service.get_medical_centre_recovery_reduction(club_id=1)

            expected = CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][level][
                "recovery_time_reduction_percent"
            ]
            assert reduction == expected, (
                f"Level {level}: expected {expected}, got {reduction}"
            )


# --- Tests for calculate_adjusted_recovery_weeks ---


class TestCalculateAdjustedRecoveryWeeks:
    """Test InfrastructureService.calculate_adjusted_recovery_weeks method."""

    @pytest.mark.asyncio
    async def test_no_reduction_at_level_1(self):
        """Level 1 (0% reduction): 10 weeks stays 10 weeks."""
        club = FakeClub(medical_centre_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=10, club_id=1)

        assert result == 10

    @pytest.mark.asyncio
    async def test_no_reduction_at_level_2(self):
        """Level 2 (0% reduction): 8 weeks stays 8 weeks."""
        club = FakeClub(medical_centre_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=8, club_id=1)

        assert result == 8

    @pytest.mark.asyncio
    async def test_10_percent_reduction_at_level_3(self):
        """Level 3 (10% reduction): 10 weeks becomes 9 weeks."""
        club = FakeClub(medical_centre_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=10, club_id=1)

        # 10 * (1 - 0.10) = 10 * 0.9 = 9.0 -> round(9.0) = 9
        assert result == 9

    @pytest.mark.asyncio
    async def test_20_percent_reduction_at_level_4(self):
        """Level 4 (20% reduction): 10 weeks becomes 8 weeks."""
        club = FakeClub(medical_centre_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=10, club_id=1)

        # 10 * (1 - 0.20) = 10 * 0.8 = 8.0 -> round(8.0) = 8
        assert result == 8

    @pytest.mark.asyncio
    async def test_30_percent_reduction_at_level_5(self):
        """Level 5 (30% reduction): 10 weeks becomes 7 weeks."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=10, club_id=1)

        # 10 * (1 - 0.30) = 10 * 0.7 = 7.0 -> round(7.0) = 7
        assert result == 7

    @pytest.mark.asyncio
    async def test_minimum_1_week_recovery(self):
        """Recovery should never go below 1 week, even with high reduction."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        # 1 * (1 - 0.30) = 0.7 -> round(0.7) = 1 -> max(1, 1) = 1
        result = await service.calculate_adjusted_recovery_weeks(base_weeks=1, club_id=1)

        assert result == 1

    @pytest.mark.asyncio
    async def test_minimum_1_week_with_very_short_base(self):
        """Even with 0 base weeks (edge case), result should be at least 1."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        # 0 * (1 - 0.30) = 0 -> round(0) = 0 -> max(1, 0) = 1
        result = await service.calculate_adjusted_recovery_weeks(base_weeks=0, club_id=1)

        assert result == 1

    @pytest.mark.asyncio
    async def test_rounding_behavior(self):
        """Test rounding: 7 weeks at level 3 = 7 * 0.9 = 6.3 -> rounds to 6."""
        club = FakeClub(medical_centre_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=7, club_id=1)

        # 7 * 0.9 = 6.3 -> round(6.3) = 6
        assert result == 6

    @pytest.mark.asyncio
    async def test_rounding_up_behavior(self):
        """Test rounding up: 5 weeks at level 3 = 5 * 0.9 = 4.5 -> rounds to 4 (banker's rounding)."""
        club = FakeClub(medical_centre_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=5, club_id=1)

        # 5 * 0.9 = 4.5 -> round(4.5) = 4 (Python banker's rounding)
        assert result == 4

    @pytest.mark.asyncio
    async def test_large_base_weeks_at_level_5(self):
        """Large base recovery: 20 weeks at level 5 = 20 * 0.7 = 14 weeks."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=20, club_id=1)

        # 20 * 0.7 = 14.0 -> round(14.0) = 14
        assert result == 14

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.calculate_adjusted_recovery_weeks(base_weeks=10, club_id=999)

    @pytest.mark.asyncio
    async def test_level_4_with_3_weeks(self):
        """3 weeks at level 4 (20% reduction): 3 * 0.8 = 2.4 -> rounds to 2."""
        club = FakeClub(medical_centre_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=3, club_id=1)

        # 3 * 0.8 = 2.4 -> round(2.4) = 2
        assert result == 2

    @pytest.mark.asyncio
    async def test_level_5_with_2_weeks(self):
        """2 weeks at level 5 (30% reduction): 2 * 0.7 = 1.4 -> rounds to 1."""
        club = FakeClub(medical_centre_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.calculate_adjusted_recovery_weeks(base_weeks=2, club_id=1)

        # 2 * 0.7 = 1.4 -> round(1.4) = 1
        assert result == 1
