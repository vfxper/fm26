"""
Tests for Infrastructure Service - Club Infrastructure Categories (Task 12.1)

Tests the InfrastructureService class including:
- 5 infrastructure categories (Stadium, Training, Academy, Medical, Scouting)
- Level definitions (1-5) with names
- Effects/bonuses per level for each category
- Upgrade costs per level for each category
- Upgrade durations per level for each category
- get_infrastructure_overview returns all categories with current levels
- get_category_details returns detailed info for one category
- Validation and error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    LEVEL_NAMES,
    CATEGORY_DEFINITIONS,
    CATEGORY_EFFECTS,
    UPGRADE_COSTS,
    UPGRADE_DURATIONS,
)
from app.models.club import Club


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


# --- Test Constants and Category Definitions ---


class TestInfrastructureCategoryEnum:
    """Test the InfrastructureCategory enum."""

    def test_has_five_categories(self):
        """There should be exactly 5 infrastructure categories."""
        assert len(InfrastructureCategory) == 5

    def test_category_values(self):
        """Each category should have the expected string value."""
        assert InfrastructureCategory.STADIUM.value == "stadium"
        assert InfrastructureCategory.TRAINING_FACILITIES.value == "training_facilities"
        assert InfrastructureCategory.YOUTH_ACADEMY.value == "youth_academy"
        assert InfrastructureCategory.MEDICAL_CENTRE.value == "medical_centre"
        assert InfrastructureCategory.SCOUTING_NETWORK.value == "scouting_network"


class TestLevelNames:
    """Test level name definitions."""

    def test_five_levels_defined(self):
        """There should be exactly 5 level names."""
        assert len(LEVEL_NAMES) == 5

    def test_level_names_correct(self):
        """Level names should match the expected values."""
        assert LEVEL_NAMES[1] == "Basic"
        assert LEVEL_NAMES[2] == "Standard"
        assert LEVEL_NAMES[3] == "Good"
        assert LEVEL_NAMES[4] == "Excellent"
        assert LEVEL_NAMES[5] == "World Class"


class TestCategoryDefinitions:
    """Test category definition constants."""

    def test_all_categories_have_definitions(self):
        """Every category enum value should have a definition."""
        for category in InfrastructureCategory:
            assert category in CATEGORY_DEFINITIONS

    def test_definitions_have_required_fields(self):
        """Each definition should have name, description, and model_field."""
        for category in InfrastructureCategory:
            defn = CATEGORY_DEFINITIONS[category]
            assert "name" in defn
            assert "description" in defn
            assert "model_field" in defn
            assert len(defn["name"]) > 0
            assert len(defn["description"]) > 0

    def test_model_fields_match_club_model(self):
        """Model field names should correspond to actual Club model attributes."""
        expected_fields = {
            InfrastructureCategory.STADIUM: "stadium_level",
            InfrastructureCategory.TRAINING_FACILITIES: "training_facilities_level",
            InfrastructureCategory.YOUTH_ACADEMY: "youth_academy_level",
            InfrastructureCategory.MEDICAL_CENTRE: "medical_centre_level",
            InfrastructureCategory.SCOUTING_NETWORK: "scouting_network_level",
        }
        for category, expected_field in expected_fields.items():
            assert CATEGORY_DEFINITIONS[category]["model_field"] == expected_field


class TestCategoryEffects:
    """Test effects/bonuses per level for each category."""

    def test_all_categories_have_effects(self):
        """Every category should have effects defined."""
        for category in InfrastructureCategory:
            assert category in CATEGORY_EFFECTS

    def test_all_levels_have_effects(self):
        """Each category should have effects for all 5 levels."""
        for category in InfrastructureCategory:
            for level in range(1, 6):
                assert level in CATEGORY_EFFECTS[category], (
                    f"Missing effects for {category.value} level {level}"
                )

    def test_effects_have_description(self):
        """Each level's effects should include a description."""
        for category in InfrastructureCategory:
            for level in range(1, 6):
                effects = CATEGORY_EFFECTS[category][level]
                assert "description" in effects

    def test_stadium_effects_have_revenue_multiplier(self):
        """Stadium effects should include matchday_revenue_multiplier."""
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]
            assert "matchday_revenue_multiplier" in effects
            assert effects["matchday_revenue_multiplier"] >= 1.0

    def test_stadium_revenue_increases_with_level(self):
        """Stadium revenue multiplier should increase with each level."""
        prev_multiplier = 0
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]
            assert effects["matchday_revenue_multiplier"] > prev_multiplier
            prev_multiplier = effects["matchday_revenue_multiplier"]

    def test_training_effects_have_bonus_multiplier(self):
        """Training facilities effects should include training_bonus_multiplier."""
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][level]
            assert "training_bonus_multiplier" in effects
            assert effects["training_bonus_multiplier"] >= 1.0

    def test_training_bonus_increases_with_level(self):
        """Training bonus multiplier should increase with each level."""
        prev_multiplier = 0
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][level]
            assert effects["training_bonus_multiplier"] > prev_multiplier
            prev_multiplier = effects["training_bonus_multiplier"]

    def test_youth_academy_effects_have_quality_bonus(self):
        """Youth academy effects should include youth_quality_bonus."""
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.YOUTH_ACADEMY][level]
            assert "youth_quality_bonus" in effects
            assert "max_youth_pa" in effects

    def test_medical_centre_recovery_reduction(self):
        """Medical centre should reduce recovery time per level above Standard.

        Requirement 9.6: reduce average player injury recovery time by 10% per
        upgrade level above Standard.
        """
        # Level 1 (Basic) - no reduction
        assert CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][1][
            "recovery_time_reduction_percent"
        ] == 0
        # Level 2 (Standard) - baseline, no reduction
        assert CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][2][
            "recovery_time_reduction_percent"
        ] == 0
        # Level 3 (Good) - 10% reduction (1 level above Standard)
        assert CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][3][
            "recovery_time_reduction_percent"
        ] == 10
        # Level 4 (Excellent) - 20% reduction (2 levels above Standard)
        assert CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][4][
            "recovery_time_reduction_percent"
        ] == 20
        # Level 5 (World Class) - 30% reduction (3 levels above Standard)
        assert CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][5][
            "recovery_time_reduction_percent"
        ] == 30

    def test_scouting_effects_have_accuracy(self):
        """Scouting network effects should include attribute_accuracy_percent."""
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.SCOUTING_NETWORK][level]
            assert "attribute_accuracy_percent" in effects
            assert 0 <= effects["attribute_accuracy_percent"] <= 100

    def test_scouting_accuracy_increases_with_level(self):
        """Scouting accuracy should increase with each level."""
        prev_accuracy = 0
        for level in range(1, 6):
            effects = CATEGORY_EFFECTS[InfrastructureCategory.SCOUTING_NETWORK][level]
            assert effects["attribute_accuracy_percent"] > prev_accuracy
            prev_accuracy = effects["attribute_accuracy_percent"]


class TestUpgradeCosts:
    """Test upgrade cost definitions."""

    def test_all_categories_have_costs(self):
        """Every category should have upgrade costs defined."""
        for category in InfrastructureCategory:
            assert category in UPGRADE_COSTS

    def test_costs_for_levels_2_through_5(self):
        """Each category should have costs for levels 2-5 (upgrading from 1-4)."""
        for category in InfrastructureCategory:
            for level in range(2, 6):
                assert level in UPGRADE_COSTS[category], (
                    f"Missing cost for {category.value} level {level}"
                )

    def test_costs_are_positive(self):
        """All upgrade costs should be positive integers."""
        for category in InfrastructureCategory:
            for level in range(2, 6):
                cost = UPGRADE_COSTS[category][level]
                assert cost > 0
                assert isinstance(cost, int)

    def test_costs_increase_with_level(self):
        """Upgrade costs should increase with each level."""
        for category in InfrastructureCategory:
            prev_cost = 0
            for level in range(2, 6):
                cost = UPGRADE_COSTS[category][level]
                assert cost > prev_cost, (
                    f"Cost for {category.value} level {level} ({cost}) "
                    f"should be greater than level {level-1} ({prev_cost})"
                )
                prev_cost = cost

    def test_stadium_is_most_expensive(self):
        """Stadium upgrades should be the most expensive category."""
        for level in range(2, 6):
            stadium_cost = UPGRADE_COSTS[InfrastructureCategory.STADIUM][level]
            for category in InfrastructureCategory:
                if category != InfrastructureCategory.STADIUM:
                    assert stadium_cost >= UPGRADE_COSTS[category][level]


class TestUpgradeDurations:
    """Test upgrade duration definitions."""

    def test_all_categories_have_durations(self):
        """Every category should have upgrade durations defined."""
        for category in InfrastructureCategory:
            assert category in UPGRADE_DURATIONS

    def test_durations_for_levels_2_through_5(self):
        """Each category should have durations for levels 2-5."""
        for category in InfrastructureCategory:
            for level in range(2, 6):
                assert level in UPGRADE_DURATIONS[category], (
                    f"Missing duration for {category.value} level {level}"
                )

    def test_durations_within_required_range(self):
        """All durations should be between 4 and 26 weeks (Requirement 9.9)."""
        for category in InfrastructureCategory:
            for level in range(2, 6):
                duration = UPGRADE_DURATIONS[category][level]
                assert 4 <= duration <= 26, (
                    f"Duration for {category.value} level {level} is {duration}, "
                    f"should be between 4 and 26 weeks"
                )

    def test_durations_increase_with_level(self):
        """Upgrade durations should increase with each level."""
        for category in InfrastructureCategory:
            prev_duration = 0
            for level in range(2, 6):
                duration = UPGRADE_DURATIONS[category][level]
                assert duration > prev_duration, (
                    f"Duration for {category.value} level {level} ({duration}) "
                    f"should be greater than level {level-1} ({prev_duration})"
                )
                prev_duration = duration


# --- Test InfrastructureService Methods ---


class TestGetInfrastructureOverview:
    """Test get_infrastructure_overview method."""

    @pytest.mark.asyncio
    async def test_returns_all_five_categories(self):
        """Overview should return info for all 5 categories."""
        club = FakeClub()
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        assert len(result["categories"]) == 5

    @pytest.mark.asyncio
    async def test_returns_club_info(self):
        """Overview should include club_id and club_name."""
        club = FakeClub(id=42, name="Arsenal FC")
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=42)

        assert result["club_id"] == 42
        assert result["club_name"] == "Arsenal FC"

    @pytest.mark.asyncio
    async def test_returns_correct_current_levels(self):
        """Overview should reflect the club's actual infrastructure levels."""
        club = FakeClub(
            stadium_level=3,
            training_facilities_level=4,
            youth_academy_level=2,
            medical_centre_level=5,
            scouting_network_level=1,
        )
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        assert categories["stadium"]["current_level"] == 3
        assert categories["training_facilities"]["current_level"] == 4
        assert categories["youth_academy"]["current_level"] == 2
        assert categories["medical_centre"]["current_level"] == 5
        assert categories["scouting_network"]["current_level"] == 1

    @pytest.mark.asyncio
    async def test_returns_level_names(self):
        """Overview should include level names for each category."""
        club = FakeClub(stadium_level=1, training_facilities_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        assert categories["stadium"]["level_name"] == "Basic"
        assert categories["training_facilities"]["level_name"] == "World Class"

    @pytest.mark.asyncio
    async def test_returns_effects_for_current_level(self):
        """Overview should include effects for the current level."""
        club = FakeClub(stadium_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        stadium = categories["stadium"]
        assert "effects" in stadium
        assert stadium["effects"]["matchday_revenue_multiplier"] == 1.5

    @pytest.mark.asyncio
    async def test_can_upgrade_flag(self):
        """Categories at level 5 should have can_upgrade=False."""
        club = FakeClub(stadium_level=5, training_facilities_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        assert categories["stadium"]["can_upgrade"] is False
        assert categories["training_facilities"]["can_upgrade"] is True

    @pytest.mark.asyncio
    async def test_next_upgrade_info_included(self):
        """Categories below level 5 should include next upgrade info."""
        club = FakeClub(training_facilities_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        training = categories["training_facilities"]
        assert "next_upgrade" in training
        assert training["next_upgrade"]["target_level"] == 3
        assert training["next_upgrade"]["target_level_name"] == "Good"
        assert training["next_upgrade"]["cost"] == UPGRADE_COSTS[InfrastructureCategory.TRAINING_FACILITIES][3]
        assert training["next_upgrade"]["duration_weeks"] == UPGRADE_DURATIONS[InfrastructureCategory.TRAINING_FACILITIES][3]

    @pytest.mark.asyncio
    async def test_max_level_no_next_upgrade(self):
        """Categories at level 5 should not include next_upgrade."""
        club = FakeClub(stadium_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        categories = {c["category"]: c for c in result["categories"]}
        assert "next_upgrade" not in categories["stadium"]

    @pytest.mark.asyncio
    async def test_average_level_calculation(self):
        """Average level should be correctly calculated."""
        club = FakeClub(
            stadium_level=2,
            training_facilities_level=3,
            youth_academy_level=1,
            medical_centre_level=4,
            scouting_network_level=5,
        )
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_infrastructure_overview(club_id=1)

        # (2 + 3 + 1 + 4 + 5) / 5 = 3.0
        assert result["average_level"] == 3.0

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_infrastructure_overview(club_id=999)


class TestGetCategoryDetails:
    """Test get_category_details method."""

    @pytest.mark.asyncio
    async def test_returns_category_info(self):
        """Should return name, description, and category value."""
        club = FakeClub(stadium_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.STADIUM
        )

        assert result["category"] == "stadium"
        assert result["name"] == "Stadium"
        assert len(result["description"]) > 0

    @pytest.mark.asyncio
    async def test_returns_current_level_info(self):
        """Should return current level and level name."""
        club = FakeClub(medical_centre_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.MEDICAL_CENTRE
        )

        assert result["current_level"] == 4
        assert result["level_name"] == "Excellent"

    @pytest.mark.asyncio
    async def test_returns_current_effects(self):
        """Should return effects for the current level."""
        club = FakeClub(scouting_network_level=3)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.SCOUTING_NETWORK
        )

        assert result["current_effects"]["attribute_accuracy_percent"] == 80

    @pytest.mark.asyncio
    async def test_returns_all_five_levels(self):
        """Should return info for all 5 levels."""
        club = FakeClub(training_facilities_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.TRAINING_FACILITIES
        )

        assert len(result["all_levels"]) == 5
        # Check is_current flag
        for level_info in result["all_levels"]:
            if level_info["level"] == 2:
                assert level_info["is_current"] is True
            else:
                assert level_info["is_current"] is False

    @pytest.mark.asyncio
    async def test_all_levels_have_costs_for_2_through_5(self):
        """Levels 2-5 should include upgrade_cost and upgrade_duration_weeks."""
        club = FakeClub()
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.STADIUM
        )

        for level_info in result["all_levels"]:
            if level_info["level"] >= 2:
                assert "upgrade_cost" in level_info
                assert "upgrade_duration_weeks" in level_info
            else:
                assert "upgrade_cost" not in level_info

    @pytest.mark.asyncio
    async def test_upgrade_path_from_level_2(self):
        """Upgrade path from level 2 should show levels 3, 4, 5."""
        club = FakeClub(youth_academy_level=2)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.YOUTH_ACADEMY
        )

        assert len(result["upgrade_path"]) == 3
        assert result["upgrade_path"][0]["target_level"] == 3
        assert result["upgrade_path"][1]["target_level"] == 4
        assert result["upgrade_path"][2]["target_level"] == 5

    @pytest.mark.asyncio
    async def test_upgrade_path_empty_at_max_level(self):
        """Upgrade path should be empty at level 5."""
        club = FakeClub(stadium_level=5)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.STADIUM
        )

        assert result["upgrade_path"] == []
        assert result["is_max_level"] is True

    @pytest.mark.asyncio
    async def test_is_max_level_false_below_5(self):
        """is_max_level should be False for levels below 5."""
        club = FakeClub(stadium_level=4)
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        result = await service.get_category_details(
            club_id=1, category=InfrastructureCategory.STADIUM
        )

        assert result["is_max_level"] is False

    @pytest.mark.asyncio
    async def test_raises_for_invalid_club(self):
        """Should raise ValueError if club is not found."""
        session = FakeSession(club=None)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_category_details(
                club_id=999, category=InfrastructureCategory.STADIUM
            )

    @pytest.mark.asyncio
    async def test_raises_for_invalid_category(self):
        """Should raise ValueError for invalid category."""
        club = FakeClub()
        session = FakeSession(club=club)
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Invalid category"):
            await service.get_category_details(club_id=1, category="invalid")


class TestGetUpgradeCost:
    """Test get_upgrade_cost method."""

    def test_returns_correct_cost(self):
        """Should return the correct cost for a given category and level."""
        session = FakeSession()
        service = InfrastructureService(session)

        cost = service.get_upgrade_cost(InfrastructureCategory.STADIUM, 3)
        assert cost == 15_000_000

    def test_raises_for_level_below_2(self):
        """Should raise ValueError for target_level < 2."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Target level must be between 2 and 5"):
            service.get_upgrade_cost(InfrastructureCategory.STADIUM, 1)

    def test_raises_for_level_above_5(self):
        """Should raise ValueError for target_level > 5."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Target level must be between 2 and 5"):
            service.get_upgrade_cost(InfrastructureCategory.STADIUM, 6)


class TestGetUpgradeDuration:
    """Test get_upgrade_duration method."""

    def test_returns_correct_duration(self):
        """Should return the correct duration for a given category and level."""
        session = FakeSession()
        service = InfrastructureService(session)

        duration = service.get_upgrade_duration(InfrastructureCategory.STADIUM, 5)
        assert duration == 26

    def test_raises_for_level_below_2(self):
        """Should raise ValueError for target_level < 2."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Target level must be between 2 and 5"):
            service.get_upgrade_duration(InfrastructureCategory.STADIUM, 1)

    def test_raises_for_level_above_5(self):
        """Should raise ValueError for target_level > 5."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Target level must be between 2 and 5"):
            service.get_upgrade_duration(InfrastructureCategory.STADIUM, 6)


class TestGetLevelEffects:
    """Test get_level_effects method."""

    def test_returns_effects_dict(self):
        """Should return a dict of effects for the given level."""
        session = FakeSession()
        service = InfrastructureService(session)

        effects = service.get_level_effects(InfrastructureCategory.STADIUM, 4)
        assert isinstance(effects, dict)
        assert "matchday_revenue_multiplier" in effects

    def test_raises_for_level_below_1(self):
        """Should raise ValueError for level < 1."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Level must be between 1 and 5"):
            service.get_level_effects(InfrastructureCategory.STADIUM, 0)

    def test_raises_for_level_above_5(self):
        """Should raise ValueError for level > 5."""
        session = FakeSession()
        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Level must be between 1 and 5"):
            service.get_level_effects(InfrastructureCategory.STADIUM, 6)


class TestGetAllCategories:
    """Test get_all_categories method."""

    def test_returns_five_categories(self):
        """Should return a list of 5 category definitions."""
        session = FakeSession()
        service = InfrastructureService(session)

        categories = service.get_all_categories()
        assert len(categories) == 5

    def test_each_category_has_required_fields(self):
        """Each category should have category, name, and description."""
        session = FakeSession()
        service = InfrastructureService(session)

        categories = service.get_all_categories()
        for cat in categories:
            assert "category" in cat
            assert "name" in cat
            assert "description" in cat
