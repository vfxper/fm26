"""
Tests for Youth Academy Quality Impact on Prospects (Task 12.5)

Tests the InfrastructureService.get_youth_academy_quality() method which returns
the youth academy effects for a club's current Youth Academy level.

The Youth Academy level affects the quality of youth prospects generated:
    - Level 1 (Basic): youth_quality_bonus=0, max_youth_pa=120, youth_intake_size=3
    - Level 2 (Standard): youth_quality_bonus=5, max_youth_pa=140, youth_intake_size=4
    - Level 3 (Good): youth_quality_bonus=10, max_youth_pa=160, youth_intake_size=5
    - Level 4 (Excellent): youth_quality_bonus=15, max_youth_pa=180, youth_intake_size=6
    - Level 5 (World Class): youth_quality_bonus=20, max_youth_pa=200, youth_intake_size=8

Implements Requirement 9.5: "WHEN a Youth Academy upgrade is completed,
THE Youth_Academy SHALL generate higher-quality youth prospects."
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
        training_facilities_level=3,
        youth_academy_level=1,
        medical_centre_level=4,
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


# --- Tests for InfrastructureService.get_youth_academy_quality ---


class TestGetYouthAcademyQuality:
    """Test InfrastructureService.get_youth_academy_quality method."""

    @pytest.mark.asyncio
    async def test_level_1_basic(self):
        """Level 1 (Basic) should return no bonus, max PA 120, intake size 3."""
        club = FakeClub(youth_academy_level=1)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        assert result["youth_quality_bonus"] == 0
        assert result["max_youth_pa"] == 120
        assert result["youth_intake_size"] == 3
        assert result["level"] == 1
        assert result["level_name"] == "Basic"

    @pytest.mark.asyncio
    async def test_level_2_standard(self):
        """Level 2 (Standard) should return bonus 5, max PA 140, intake size 4."""
        club = FakeClub(youth_academy_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        assert result["youth_quality_bonus"] == 5
        assert result["max_youth_pa"] == 140
        assert result["youth_intake_size"] == 4
        assert result["level"] == 2
        assert result["level_name"] == "Standard"

    @pytest.mark.asyncio
    async def test_level_3_good(self):
        """Level 3 (Good) should return bonus 10, max PA 160, intake size 5."""
        club = FakeClub(youth_academy_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        assert result["youth_quality_bonus"] == 10
        assert result["max_youth_pa"] == 160
        assert result["youth_intake_size"] == 5
        assert result["level"] == 3
        assert result["level_name"] == "Good"

    @pytest.mark.asyncio
    async def test_level_4_excellent(self):
        """Level 4 (Excellent) should return bonus 15, max PA 180, intake size 6."""
        club = FakeClub(youth_academy_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        assert result["youth_quality_bonus"] == 15
        assert result["max_youth_pa"] == 180
        assert result["youth_intake_size"] == 6
        assert result["level"] == 4
        assert result["level_name"] == "Excellent"

    @pytest.mark.asyncio
    async def test_level_5_world_class(self):
        """Level 5 (World Class) should return bonus 20, max PA 200, intake size 8."""
        club = FakeClub(youth_academy_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        assert result["youth_quality_bonus"] == 20
        assert result["max_youth_pa"] == 200
        assert result["youth_intake_size"] == 8
        assert result["level"] == 5
        assert result["level_name"] == "World Class"

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_youth_academy_quality(club_id=999)

    @pytest.mark.asyncio
    async def test_all_levels_match_category_effects(self):
        """All levels should return values matching CATEGORY_EFFECTS definitions."""
        for level in range(1, 6):
            club = FakeClub(youth_academy_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_youth_academy_quality(club_id=1)

            expected = CATEGORY_EFFECTS[InfrastructureCategory.YOUTH_ACADEMY][level]
            assert result["youth_quality_bonus"] == expected["youth_quality_bonus"], (
                f"Level {level}: expected youth_quality_bonus={expected['youth_quality_bonus']}, "
                f"got {result['youth_quality_bonus']}"
            )
            assert result["max_youth_pa"] == expected["max_youth_pa"], (
                f"Level {level}: expected max_youth_pa={expected['max_youth_pa']}, "
                f"got {result['max_youth_pa']}"
            )
            assert result["youth_intake_size"] == expected["youth_intake_size"], (
                f"Level {level}: expected youth_intake_size={expected['youth_intake_size']}, "
                f"got {result['youth_intake_size']}"
            )

    @pytest.mark.asyncio
    async def test_quality_bonus_increases_with_level(self):
        """Youth quality bonus should increase with each level."""
        prev_bonus = -1
        for level in range(1, 6):
            club = FakeClub(youth_academy_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_youth_academy_quality(club_id=1)

            assert result["youth_quality_bonus"] > prev_bonus or (
                level == 1 and result["youth_quality_bonus"] == 0
            )
            prev_bonus = result["youth_quality_bonus"]

    @pytest.mark.asyncio
    async def test_max_pa_increases_with_level(self):
        """Max youth PA should increase with each level."""
        prev_pa = 0
        for level in range(1, 6):
            club = FakeClub(youth_academy_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_youth_academy_quality(club_id=1)

            assert result["max_youth_pa"] > prev_pa
            prev_pa = result["max_youth_pa"]

    @pytest.mark.asyncio
    async def test_intake_size_increases_with_level(self):
        """Youth intake size should increase with each level."""
        prev_size = 0
        for level in range(1, 6):
            club = FakeClub(youth_academy_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_youth_academy_quality(club_id=1)

            assert result["youth_intake_size"] > prev_size
            prev_size = result["youth_intake_size"]

    @pytest.mark.asyncio
    async def test_result_contains_all_expected_keys(self):
        """Result dict should contain all expected keys."""
        club = FakeClub(youth_academy_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_youth_academy_quality(club_id=1)

        expected_keys = {"youth_quality_bonus", "max_youth_pa", "youth_intake_size", "level", "level_name"}
        assert set(result.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_level_name_matches_level_names_constant(self):
        """Level name in result should match the LEVEL_NAMES constant."""
        for level in range(1, 6):
            club = FakeClub(youth_academy_level=level)
            session = FakeSession(club=club)
            service = InfrastructureService(session)

            result = await service.get_youth_academy_quality(club_id=1)

            assert result["level_name"] == LEVEL_NAMES[level]
