"""
Tests for Club Overview Screen with Infrastructure Display (Task 12.10)

Tests the get_club_overview() method in InfrastructureService which generates
a comprehensive club overview including:
1. Club basic info (name, reputation, balance)
2. All 5 infrastructure categories with current levels and effects
3. Any active upgrades in progress
4. Financial summary (balance, transfer budget, wage bill)
5. Squad summary (total players, average age, average CA)
6. Staff summary (total staff, key roles filled)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.infrastructure_service import (
    InfrastructureService,
    InfrastructureCategory,
    LEVEL_NAMES,
    CATEGORY_EFFECTS,
)


class FakeClub:
    """A fake Club object for testing."""

    def __init__(
        self,
        id=1,
        name="Test FC",
        reputation=75,
        league="Premier League",
        country="England",
        balance=50_000_000,
        transfer_budget=20_000_000,
        wage_budget=500_000,
        matchday_revenue=1_000_000,
        stadium_level=3,
        training_facilities_level=2,
        youth_academy_level=4,
        medical_centre_level=2,
        scouting_network_level=3,
    ):
        self.id = id
        self.name = name
        self.reputation = reputation
        self.league = league
        self.country = country
        self.balance = balance
        self.transfer_budget = transfer_budget
        self.wage_budget = wage_budget
        self.matchday_revenue = matchday_revenue
        self.stadium_level = stadium_level
        self.training_facilities_level = training_facilities_level
        self.youth_academy_level = youth_academy_level
        self.medical_centre_level = medical_centre_level
        self.scouting_network_level = scouting_network_level


class FakeScalarResult:
    """Fake result for scalar queries."""

    def __init__(self, value=None):
        self._value = value

    def scalar(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class FakeRowResult:
    """Fake result for row queries (e.g., avg queries)."""

    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class FakeRow:
    """Fake row for aggregate queries."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeAllResult:
    """Fake result for .all() queries."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows

    def scalars(self):
        return self

    def scalar(self):
        if self._rows:
            return self._rows[0]
        return None


class FakeStaffRole:
    """Fake staff role enum value."""

    def __init__(self, value):
        self.value = value


def create_mock_session(club, squad_count=25, avg_age=26.5, avg_ca=130.0,
                        player_wages=300_000, staff_wages=50_000,
                        total_staff=5, filled_roles=None, active_upgrades=None):
    """
    Create a mock async session that returns appropriate results for
    the get_club_overview method's various queries.
    """
    if filled_roles is None:
        filled_roles = ["assistant_manager", "fitness_coach", "chief_scout"]
    if active_upgrades is None:
        active_upgrades = []

    session = AsyncMock(spec=AsyncSession)

    # Track call count to return different results for different queries
    call_results = []

    # 1. _get_club query (select Club where id = club_id)
    club_result = MagicMock()
    club_result.scalar_one_or_none.return_value = club
    call_results.append(club_result)

    # 2. get_active_upgrades query (select InfrastructureUpgrade)
    upgrades_result = MagicMock()
    upgrades_scalars = MagicMock()
    upgrades_scalars.all.return_value = active_upgrades
    upgrades_result.scalars.return_value = upgrades_scalars
    call_results.append(upgrades_result)

    # 3. Player wages query (sum of SquadPlayer.wage)
    player_wages_result = MagicMock()
    player_wages_result.scalar.return_value = player_wages
    call_results.append(player_wages_result)

    # 4. Staff wages query (sum of Staff.wage)
    staff_wages_result = MagicMock()
    staff_wages_result.scalar.return_value = staff_wages
    call_results.append(staff_wages_result)

    # 5. Squad count query (count of SquadPlayer)
    squad_count_result = MagicMock()
    squad_count_result.scalar.return_value = squad_count
    call_results.append(squad_count_result)

    # 6. Average age/CA query (join Player + SquadPlayer)
    if squad_count > 0:
        avg_row = FakeRow(avg_age=avg_age, avg_ca=avg_ca)
        avg_result = MagicMock()
        avg_result.one.return_value = avg_row
        call_results.append(avg_result)

    # 7. Staff count query
    staff_count_result = MagicMock()
    staff_count_result.scalar.return_value = total_staff
    call_results.append(staff_count_result)

    # 8. Roles filled query (distinct roles)
    roles_rows = [(FakeStaffRole(role),) for role in filled_roles]
    roles_result = MagicMock()
    roles_result.all.return_value = roles_rows
    call_results.append(roles_result)

    session.execute = AsyncMock(side_effect=call_results)

    return session


class TestGetClubOverview:
    """Tests for the get_club_overview method."""

    @pytest.mark.asyncio
    async def test_returns_club_basic_info(self):
        """Club overview should include basic club information."""
        club = FakeClub(
            id=1,
            name="Manchester United",
            reputation=90,
            league="Premier League",
            country="England",
            balance=100_000_000,
        )
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "club_info" in result
        assert result["club_info"]["id"] == 1
        assert result["club_info"]["name"] == "Manchester United"
        assert result["club_info"]["reputation"] == 90
        assert result["club_info"]["league"] == "Premier League"
        assert result["club_info"]["country"] == "England"
        assert result["club_info"]["balance"] == 100_000_000

    @pytest.mark.asyncio
    async def test_returns_all_five_infrastructure_categories(self):
        """Club overview should include all 5 infrastructure categories."""
        club = FakeClub()
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "infrastructure" in result
        assert len(result["infrastructure"]) == 5

        category_names = [cat["category"] for cat in result["infrastructure"]]
        assert "stadium" in category_names
        assert "training_facilities" in category_names
        assert "youth_academy" in category_names
        assert "medical_centre" in category_names
        assert "scouting_network" in category_names

    @pytest.mark.asyncio
    async def test_infrastructure_includes_levels_and_effects(self):
        """Each infrastructure category should include current level and effects."""
        club = FakeClub(stadium_level=3)
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        stadium = next(
            cat for cat in result["infrastructure"]
            if cat["category"] == "stadium"
        )
        assert stadium["current_level"] == 3
        assert stadium["level_name"] == "Good"
        assert "effects" in stadium
        assert stadium["effects"]["matchday_revenue_multiplier"] == 1.5
        assert stadium["can_upgrade"] is True

    @pytest.mark.asyncio
    async def test_infrastructure_max_level_cannot_upgrade(self):
        """Category at max level should show can_upgrade as False."""
        club = FakeClub(youth_academy_level=5)
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        youth_academy = next(
            cat for cat in result["infrastructure"]
            if cat["category"] == "youth_academy"
        )
        assert youth_academy["current_level"] == 5
        assert youth_academy["level_name"] == "World Class"
        assert youth_academy["can_upgrade"] is False

    @pytest.mark.asyncio
    async def test_returns_active_upgrades(self):
        """Club overview should include active upgrades in progress."""
        club = FakeClub()

        # Create a fake upgrade
        fake_upgrade = MagicMock()
        fake_upgrade.to_dict.return_value = {
            "id": 1,
            "category": "stadium",
            "from_level": 3,
            "to_level": 4,
            "duration_weeks": 20,
            "status": "in_progress",
        }

        session = create_mock_session(club, active_upgrades=[fake_upgrade])
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "active_upgrades" in result
        assert len(result["active_upgrades"]) == 1
        assert result["active_upgrades"][0]["category"] == "stadium"
        assert result["active_upgrades"][0]["to_level"] == 4

    @pytest.mark.asyncio
    async def test_returns_empty_active_upgrades_when_none(self):
        """Club overview should return empty list when no upgrades in progress."""
        club = FakeClub()
        session = create_mock_session(club, active_upgrades=[])
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "active_upgrades" in result
        assert result["active_upgrades"] == []

    @pytest.mark.asyncio
    async def test_returns_financial_summary(self):
        """Club overview should include financial summary."""
        club = FakeClub(
            balance=50_000_000,
            transfer_budget=20_000_000,
            wage_budget=500_000,
            matchday_revenue=1_000_000,
        )
        session = create_mock_session(
            club, player_wages=300_000, staff_wages=50_000
        )
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "financial_summary" in result
        fs = result["financial_summary"]
        assert fs["balance"] == 50_000_000
        assert fs["transfer_budget"] == 20_000_000
        assert fs["wage_budget"] == 500_000
        assert fs["matchday_revenue"] == 1_000_000
        assert fs["is_in_deficit"] is False
        assert fs["weekly_wage_bill"] == 350_000
        assert fs["player_wages_weekly"] == 300_000
        assert fs["staff_wages_weekly"] == 50_000

    @pytest.mark.asyncio
    async def test_financial_summary_deficit_detection(self):
        """Financial summary should detect when club is in deficit."""
        club = FakeClub(balance=-5_000_000)
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert result["financial_summary"]["is_in_deficit"] is True

    @pytest.mark.asyncio
    async def test_returns_squad_summary(self):
        """Club overview should include squad summary with player stats."""
        club = FakeClub()
        session = create_mock_session(
            club, squad_count=30, avg_age=25.8, avg_ca=145.3
        )
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "squad_summary" in result
        ss = result["squad_summary"]
        assert ss["total_players"] == 30
        assert ss["average_age"] == 25.8
        assert ss["average_ca"] == 145.3

    @pytest.mark.asyncio
    async def test_squad_summary_empty_squad(self):
        """Squad summary should handle empty squad gracefully."""
        club = FakeClub()
        session = create_mock_session(club, squad_count=0)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        ss = result["squad_summary"]
        assert ss["total_players"] == 0
        assert ss["average_age"] == 0.0
        assert ss["average_ca"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_staff_summary(self):
        """Club overview should include staff summary with roles filled."""
        club = FakeClub()
        filled = ["assistant_manager", "fitness_coach", "chief_scout", "physio"]
        session = create_mock_session(club, total_staff=6, filled_roles=filled)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        assert "staff_summary" in result
        staff = result["staff_summary"]
        assert staff["total_staff"] == 6
        assert staff["total_roles_available"] == 8
        assert staff["roles_vacant"] == 4
        assert "assistant_manager" in staff["roles_filled"]
        assert "fitness_coach" in staff["roles_filled"]
        assert "chief_scout" in staff["roles_filled"]
        assert "physio" in staff["roles_filled"]

    @pytest.mark.asyncio
    async def test_staff_summary_no_staff(self):
        """Staff summary should handle no staff gracefully."""
        club = FakeClub()
        session = create_mock_session(club, total_staff=0, filled_roles=[])
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        staff = result["staff_summary"]
        assert staff["total_staff"] == 0
        assert staff["roles_filled"] == []
        assert staff["roles_vacant"] == 8

    @pytest.mark.asyncio
    async def test_raises_value_error_for_invalid_club(self):
        """Should raise ValueError when club_id is not found."""
        session = AsyncMock(spec=AsyncSession)
        club_result = MagicMock()
        club_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=club_result)

        service = InfrastructureService(session)

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await service.get_club_overview(club_id=999, career_id=1)

    @pytest.mark.asyncio
    async def test_overview_structure_completeness(self):
        """Club overview should contain all required top-level keys."""
        club = FakeClub()
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        required_keys = [
            "club_info",
            "infrastructure",
            "active_upgrades",
            "financial_summary",
            "squad_summary",
            "staff_summary",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    @pytest.mark.asyncio
    async def test_infrastructure_effects_match_category_definitions(self):
        """Infrastructure effects should match the CATEGORY_EFFECTS definitions."""
        club = FakeClub(
            stadium_level=2,
            training_facilities_level=4,
            youth_academy_level=1,
            medical_centre_level=5,
            scouting_network_level=3,
        )
        session = create_mock_session(club)
        service = InfrastructureService(session)

        result = await service.get_club_overview(club_id=1, career_id=1)

        # Verify stadium level 2 effects
        stadium = next(
            cat for cat in result["infrastructure"]
            if cat["category"] == "stadium"
        )
        expected_effects = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][2]
        assert stadium["effects"] == expected_effects

        # Verify training facilities level 4 effects
        training = next(
            cat for cat in result["infrastructure"]
            if cat["category"] == "training_facilities"
        )
        expected_effects = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][4]
        assert training["effects"] == expected_effects
