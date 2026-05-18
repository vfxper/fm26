"""
Tests for Finance Service - Sponsorship Deal Simulation (Task 11.8)

Tests the sponsorship deal simulation including:
- generate_sponsorship_deal: Generates sponsorship deals based on club attributes
- process_sponsorship_payment: Processes weekly sponsorship payments
- get_current_sponsorship: Returns current sponsorship details
- Tier determination based on reputation, position, stadium, continental cup
- Value calculation within tier ranges
- Duration calculation (1-3 seasons)
- Payment recording as SPONSORSHIP income transactions
"""

import pytest

from app.models.financial_transaction import (
    FinancialTransaction,
    TransactionType,
    IncomeCategory,
)
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
        return self._data[0] if self._data else FakeRow(0, 0)

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self


class FakeRow:
    """A fake row for aggregate query results."""

    def __init__(self, total=0, count=0):
        self.total = total
        self.count = count


class FakeSession:
    """A fake async session that tracks added objects and simulates execute."""

    def __init__(self):
        self.added = []
        self._execute_results = []
        self._execute_index = 0
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

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


class FakeClub:
    """A simple fake club object for testing."""

    def __init__(self, id=1, name="Test FC", balance=50_000_000,
                 stadium_level=3, reputation=60):
        self.id = id
        self.name = name
        self.balance = balance
        self.stadium_level = stadium_level
        self.reputation = reputation


@pytest.fixture
def fake_session():
    """Create a fake async database session."""
    return FakeSession()


@pytest.fixture
def finance_service(fake_session):
    """Create a FinanceService instance with fake session."""
    return FinanceService(fake_session)


# --- Tests for _determine_sponsorship_tier ---

class TestDetermineSponsorshipTier:
    """Tests for the tier determination logic."""

    def test_low_reputation_gets_small_tier(self, finance_service):
        """Low reputation club with poor position gets small sponsor."""
        tier = finance_service._determine_sponsorship_tier(
            club_reputation=20,
            league_position=18,
            stadium_level=1,
            in_continental_cup=False,
        )
        assert tier == "small"

    def test_medium_reputation_gets_medium_tier(self, finance_service):
        """Medium reputation club gets medium sponsor."""
        tier = finance_service._determine_sponsorship_tier(
            club_reputation=50,
            league_position=10,
            stadium_level=3,
            in_continental_cup=False,
        )
        assert tier == "medium"

    def test_high_reputation_gets_large_tier(self, finance_service):
        """High reputation club gets large sponsor."""
        tier = finance_service._determine_sponsorship_tier(
            club_reputation=75,
            league_position=4,
            stadium_level=4,
            in_continental_cup=False,
        )
        assert tier == "large"

    def test_top_club_gets_premium_tier(self, finance_service):
        """Top club with all factors maxed gets premium sponsor."""
        tier = finance_service._determine_sponsorship_tier(
            club_reputation=95,
            league_position=1,
            stadium_level=5,
            in_continental_cup=True,
        )
        assert tier == "premium"

    def test_continental_cup_boosts_tier(self, finance_service):
        """Continental cup participation can push a club to a higher tier."""
        # Without continental cup
        tier_without = finance_service._determine_sponsorship_tier(
            club_reputation=70,
            league_position=5,
            stadium_level=4,
            in_continental_cup=False,
        )
        # With continental cup
        tier_with = finance_service._determine_sponsorship_tier(
            club_reputation=70,
            league_position=5,
            stadium_level=4,
            in_continental_cup=True,
        )
        # Continental cup should give same or higher tier
        tier_order = ["small", "medium", "large", "premium"]
        assert tier_order.index(tier_with) >= tier_order.index(tier_without)

    def test_league_position_affects_tier(self, finance_service):
        """Better league position should give same or higher tier."""
        tier_bottom = finance_service._determine_sponsorship_tier(
            club_reputation=50,
            league_position=20,
            stadium_level=3,
            in_continental_cup=False,
        )
        tier_top = finance_service._determine_sponsorship_tier(
            club_reputation=50,
            league_position=1,
            stadium_level=3,
            in_continental_cup=False,
        )
        tier_order = ["small", "medium", "large", "premium"]
        assert tier_order.index(tier_top) >= tier_order.index(tier_bottom)

    def test_stadium_level_affects_tier(self, finance_service):
        """Higher stadium level should give same or higher tier."""
        tier_low_stadium = finance_service._determine_sponsorship_tier(
            club_reputation=50,
            league_position=10,
            stadium_level=1,
            in_continental_cup=False,
        )
        tier_high_stadium = finance_service._determine_sponsorship_tier(
            club_reputation=50,
            league_position=10,
            stadium_level=5,
            in_continental_cup=False,
        )
        tier_order = ["small", "medium", "large", "premium"]
        assert tier_order.index(tier_high_stadium) >= tier_order.index(tier_low_stadium)


# --- Tests for _calculate_sponsorship_value ---

class TestCalculateSponsorshipValue:
    """Tests for sponsorship value calculation."""

    def test_small_tier_value_in_range(self, finance_service):
        """Small tier value should be between 1M and 3M."""
        value = finance_service._calculate_sponsorship_value(
            tier="small",
            club_reputation=20,
            league_position=15,
            stadium_level=2,
            in_continental_cup=False,
        )
        assert 1_000_000 <= value <= 3_000_000

    def test_medium_tier_value_in_range(self, finance_service):
        """Medium tier value should be between 3M and 8M."""
        value = finance_service._calculate_sponsorship_value(
            tier="medium",
            club_reputation=50,
            league_position=10,
            stadium_level=3,
            in_continental_cup=False,
        )
        assert 3_000_000 <= value <= 8_000_000

    def test_large_tier_value_in_range(self, finance_service):
        """Large tier value should be between 8M and 15M."""
        value = finance_service._calculate_sponsorship_value(
            tier="large",
            club_reputation=75,
            league_position=4,
            stadium_level=4,
            in_continental_cup=False,
        )
        assert 8_000_000 <= value <= 15_000_000

    def test_premium_tier_value_in_range(self, finance_service):
        """Premium tier value should be between 15M and 30M."""
        value = finance_service._calculate_sponsorship_value(
            tier="premium",
            club_reputation=95,
            league_position=1,
            stadium_level=5,
            in_continental_cup=True,
        )
        assert 15_000_000 <= value <= 30_000_000

    def test_higher_reputation_gives_higher_value(self, finance_service):
        """Higher reputation should give higher value within same tier."""
        value_low = finance_service._calculate_sponsorship_value(
            tier="medium",
            club_reputation=30,
            league_position=10,
            stadium_level=3,
            in_continental_cup=False,
        )
        value_high = finance_service._calculate_sponsorship_value(
            tier="medium",
            club_reputation=80,
            league_position=10,
            stadium_level=3,
            in_continental_cup=False,
        )
        assert value_high > value_low

    def test_better_position_gives_higher_value(self, finance_service):
        """Better league position should give higher value within same tier."""
        value_bottom = finance_service._calculate_sponsorship_value(
            tier="medium",
            club_reputation=50,
            league_position=20,
            stadium_level=3,
            in_continental_cup=False,
        )
        value_top = finance_service._calculate_sponsorship_value(
            tier="medium",
            club_reputation=50,
            league_position=1,
            stadium_level=3,
            in_continental_cup=False,
        )
        assert value_top > value_bottom


# --- Tests for _calculate_sponsorship_duration ---

class TestCalculateSponsorshipDuration:
    """Tests for sponsorship duration calculation."""

    def test_duration_within_valid_range(self, finance_service):
        """Duration should always be between 1 and 3 seasons."""
        for tier in ["small", "medium", "large", "premium"]:
            for rep in [10, 50, 80, 100]:
                duration = finance_service._calculate_sponsorship_duration(
                    tier=tier,
                    club_reputation=rep,
                )
                assert 1 <= duration <= 3

    def test_premium_tier_gets_longer_deals(self, finance_service):
        """Premium tier should get longer deals than small tier."""
        duration_small = finance_service._calculate_sponsorship_duration(
            tier="small",
            club_reputation=50,
        )
        duration_premium = finance_service._calculate_sponsorship_duration(
            tier="premium",
            club_reputation=50,
        )
        assert duration_premium >= duration_small

    def test_high_reputation_extends_duration(self, finance_service):
        """High reputation clubs should get same or longer deals."""
        duration_low_rep = finance_service._calculate_sponsorship_duration(
            tier="large",
            club_reputation=30,
        )
        duration_high_rep = finance_service._calculate_sponsorship_duration(
            tier="large",
            club_reputation=90,
        )
        assert duration_high_rep >= duration_low_rep


# --- Tests for generate_sponsorship_deal ---

class TestGenerateSponsorshipDeal:
    """Tests for the full sponsorship deal generation."""

    @pytest.mark.asyncio
    async def test_generates_deal_for_average_club(self, finance_service, fake_session):
        """Should generate a valid deal for an average club."""
        club = FakeClub(id=1, reputation=50, stadium_level=3, balance=20_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club lookup
        ])

        deal = await finance_service.generate_sponsorship_deal(
            club_id=1,
            career_id=1,
            season=1,
            league_position=10,
            in_continental_cup=False,
        )

        assert deal["club_id"] == 1
        assert deal["career_id"] == 1
        assert deal["tier"] in ["small", "medium", "large", "premium"]
        assert deal["annual_value"] > 0
        assert deal["weekly_payment"] > 0
        assert deal["weekly_payment"] == deal["annual_value"] // 52
        assert 1 <= deal["duration_seasons"] <= 3
        assert deal["start_season"] == 1
        assert deal["end_season"] == deal["start_season"] + deal["duration_seasons"] - 1

    @pytest.mark.asyncio
    async def test_generates_deal_for_top_club(self, finance_service, fake_session):
        """Top club should get premium/large tier with high value."""
        club = FakeClub(id=2, reputation=95, stadium_level=5, balance=100_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club lookup
        ])

        deal = await finance_service.generate_sponsorship_deal(
            club_id=2,
            career_id=1,
            season=2,
            league_position=1,
            in_continental_cup=True,
        )

        assert deal["tier"] in ["large", "premium"]
        assert deal["annual_value"] >= 8_000_000  # At least large tier minimum

    @pytest.mark.asyncio
    async def test_generates_deal_for_small_club(self, finance_service, fake_session):
        """Small club should get small/medium tier."""
        club = FakeClub(id=3, reputation=15, stadium_level=1, balance=5_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club lookup
        ])

        deal = await finance_service.generate_sponsorship_deal(
            club_id=3,
            career_id=1,
            season=1,
            league_position=18,
            in_continental_cup=False,
        )

        assert deal["tier"] in ["small", "medium"]
        assert deal["annual_value"] <= 8_000_000  # At most medium tier max

    @pytest.mark.asyncio
    async def test_invalid_season_raises_error(self, finance_service, fake_session):
        """Season must be positive."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.generate_sponsorship_deal(
                club_id=1, career_id=1, season=0,
            )

    @pytest.mark.asyncio
    async def test_invalid_league_position_raises_error(self, finance_service, fake_session):
        """League position must be between 1 and 20."""
        with pytest.raises(ValueError, match="League position must be between 1 and 20"):
            await finance_service.generate_sponsorship_deal(
                club_id=1, career_id=1, season=1, league_position=21,
            )

    @pytest.mark.asyncio
    async def test_club_not_found_raises_error(self, finance_service, fake_session):
        """Should raise ValueError if club not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),  # Club not found
        ])

        with pytest.raises(ValueError, match="Club with id 99 not found"):
            await finance_service.generate_sponsorship_deal(
                club_id=99, career_id=1, season=1,
            )

    @pytest.mark.asyncio
    async def test_deal_contains_factors(self, finance_service, fake_session):
        """Deal should include the factors that influenced it."""
        club = FakeClub(id=1, reputation=60, stadium_level=3, balance=30_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
        ])

        deal = await finance_service.generate_sponsorship_deal(
            club_id=1, career_id=1, season=1,
            league_position=5, in_continental_cup=True,
        )

        assert "factors" in deal
        assert deal["factors"]["club_reputation"] == 60
        assert deal["factors"]["league_position"] == 5
        assert deal["factors"]["stadium_level"] == 3
        assert deal["factors"]["in_continental_cup"] is True


# --- Tests for process_sponsorship_payment ---

class TestProcessSponsorshipPayment:
    """Tests for processing weekly sponsorship payments."""

    @pytest.mark.asyncio
    async def test_processes_payment_with_deal(self, finance_service, fake_session):
        """Should record a sponsorship payment when deal is provided."""
        deal = {
            "weekly_payment": 200_000,
            "start_season": 1,
            "end_season": 2,
            "sponsor_name": "Premium Sponsor Deal (Season 1)",
        }

        # _update_club_balance does select(Club).where(...) and expects a Club object
        club = FakeClub(id=1, balance=50_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club object for _update_club_balance
        ])

        transaction = await finance_service.process_sponsorship_payment(
            club_id=1,
            career_id=1,
            season=1,
            week=5,
            sponsorship_deal=deal,
        )

        assert transaction is not None
        assert transaction.amount == 200_000
        assert transaction.category == IncomeCategory.SPONSORSHIP.value
        assert transaction.transaction_type == TransactionType.INCOME.value

    @pytest.mark.asyncio
    async def test_no_payment_if_deal_expired(self, finance_service, fake_session):
        """Should return None if the deal has expired."""
        deal = {
            "weekly_payment": 200_000,
            "start_season": 1,
            "end_season": 2,
            "sponsor_name": "Old Deal",
        }

        result = await finance_service.process_sponsorship_payment(
            club_id=1,
            career_id=1,
            season=3,  # After deal end
            week=5,
            sponsorship_deal=deal,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_payment_before_deal_starts(self, finance_service, fake_session):
        """Should return None if the deal hasn't started yet."""
        deal = {
            "weekly_payment": 200_000,
            "start_season": 3,
            "end_season": 5,
            "sponsor_name": "Future Deal",
        }

        result = await finance_service.process_sponsorship_payment(
            club_id=1,
            career_id=1,
            season=2,  # Before deal start
            week=5,
            sponsorship_deal=deal,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_processes_payment_without_deal(self, finance_service, fake_session):
        """Should calculate basic payment from club attributes when no deal provided."""
        club = FakeClub(id=1, reputation=50, stadium_level=3, balance=30_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club lookup for basic calculation
            FakeResult(scalar_value=club),  # Club object for _update_club_balance
        ])

        transaction = await finance_service.process_sponsorship_payment(
            club_id=1,
            career_id=1,
            season=1,
            week=10,
            sponsorship_deal=None,
        )

        assert transaction is not None
        assert transaction.amount > 0
        assert transaction.category == IncomeCategory.SPONSORSHIP.value

    @pytest.mark.asyncio
    async def test_invalid_week_raises_error(self, finance_service, fake_session):
        """Week must be between 1 and 52."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.process_sponsorship_payment(
                club_id=1, career_id=1, season=1, week=53,
            )

    @pytest.mark.asyncio
    async def test_invalid_season_raises_error(self, finance_service, fake_session):
        """Season must be positive."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.process_sponsorship_payment(
                club_id=1, career_id=1, season=0, week=1,
            )


# --- Tests for get_current_sponsorship ---

class TestGetCurrentSponsorship:
    """Tests for retrieving current sponsorship details."""

    @pytest.mark.asyncio
    async def test_returns_sponsorship_summary(self, finance_service, fake_session):
        """Should return a summary of sponsorship income."""
        # Simulate 10 payments of 200,000 each
        fake_session.set_execute_results([
            FakeResult(data=[FakeRow(total=2_000_000, count=10)]),
        ])

        result = await finance_service.get_current_sponsorship(
            club_id=1,
            career_id=1,
            season=1,
        )

        assert result["club_id"] == 1
        assert result["career_id"] == 1
        assert result["season"] == 1
        assert result["total_sponsorship_income"] == 2_000_000
        assert result["payment_count"] == 10
        assert result["average_weekly_payment"] == 200_000
        assert result["estimated_annual_value"] == 200_000 * 52
        assert result["has_active_sponsorship"] is True

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_sponsorship(self, finance_service, fake_session):
        """Should indicate no active sponsorship when no payments exist."""
        fake_session.set_execute_results([
            FakeResult(data=[FakeRow(total=0, count=0)]),
        ])

        result = await finance_service.get_current_sponsorship(
            club_id=1,
            career_id=1,
            season=1,
        )

        assert result["total_sponsorship_income"] == 0
        assert result["payment_count"] == 0
        assert result["average_weekly_payment"] == 0
        assert result["estimated_annual_value"] == 0
        assert result["has_active_sponsorship"] is False

    @pytest.mark.asyncio
    async def test_queries_all_seasons_when_no_season_specified(self, finance_service, fake_session):
        """Should query all seasons when season is None."""
        fake_session.set_execute_results([
            FakeResult(data=[FakeRow(total=5_000_000, count=25)]),
        ])

        result = await finance_service.get_current_sponsorship(
            club_id=1,
            career_id=1,
            season=None,
        )

        assert result["season"] == "all"
        assert result["total_sponsorship_income"] == 5_000_000
        assert result["payment_count"] == 25


# --- Integration-style tests for tier/value consistency ---

class TestSponsorshipTierValueConsistency:
    """Tests ensuring tier and value calculations are consistent."""

    def test_all_tiers_have_valid_ranges(self, finance_service):
        """All tier ranges should be non-overlapping and increasing."""
        tiers = finance_service.SPONSORSHIP_TIERS
        tier_order = ["small", "medium", "large", "premium"]

        for i in range(len(tier_order) - 1):
            current = tiers[tier_order[i]]
            next_tier = tiers[tier_order[i + 1]]
            # Current max should equal next min (continuous ranges)
            assert current["max"] == next_tier["min"], (
                f"Gap between {tier_order[i]} max ({current['max']}) "
                f"and {tier_order[i+1]} min ({next_tier['min']})"
            )

    def test_tier_min_less_than_max(self, finance_service):
        """Each tier's min should be less than its max."""
        for tier_name, tier_data in finance_service.SPONSORSHIP_TIERS.items():
            assert tier_data["min"] < tier_data["max"], (
                f"Tier {tier_name}: min ({tier_data['min']}) >= max ({tier_data['max']})"
            )

    def test_duration_bounds(self, finance_service):
        """Duration should respect min/max bounds."""
        assert finance_service.SPONSORSHIP_MIN_DURATION == 1
        assert finance_service.SPONSORSHIP_MAX_DURATION == 3


# --- Tests for persistent sponsorship deal management & weekly integration ---

class TestPersistentSponsorshipDealManagement:
    """Tests for create_sponsorship_deal, get_active_sponsorship_deal, and renew_sponsorship_if_expired."""

    @pytest.mark.asyncio
    async def test_create_sponsorship_deal_persists_record(
        self, finance_service, fake_session
    ):
        """create_sponsorship_deal should generate a deal and add it to the session."""
        from app.models.sponsorship_deal import SponsorshipDeal

        club = FakeClub(id=1, reputation=60, stadium_level=3)
        # generate_sponsorship_deal -> select(Club) returns the club
        # Then we deactivate any existing deals (empty result set)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),  # Club lookup in generate_sponsorship_deal
            FakeResult(data=[]),  # Empty existing-active-deals query
        ])

        deal = await finance_service.create_sponsorship_deal(
            club_id=1,
            career_id=1,
            season=1,
            league_position=8,
            in_continental_cup=False,
        )

        # Should have added a SponsorshipDeal to the session
        added_deals = [obj for obj in fake_session.added if isinstance(obj, SponsorshipDeal)]
        assert len(added_deals) == 1
        persisted = added_deals[0]
        assert persisted is deal
        assert persisted.club_id == 1
        assert persisted.career_id == 1
        assert persisted.start_season == 1
        assert persisted.end_season == 1 + persisted.duration_seasons - 1
        assert persisted.is_active is True
        assert persisted.weekly_payment > 0
        assert persisted.annual_value > 0
        assert persisted.tier in ("small", "medium", "large", "premium")

    @pytest.mark.asyncio
    async def test_create_sponsorship_deal_deactivates_previous_active_deals(
        self, finance_service, fake_session
    ):
        """A new deal should deactivate any other active deals to enforce one-at-a-time."""
        from app.models.sponsorship_deal import SponsorshipDeal

        club = FakeClub(id=1, reputation=70, stadium_level=4)
        existing_active = SponsorshipDeal(
            club_id=1,
            career_id=1,
            tier="medium",
            sponsor_name="Old Deal",
            annual_value=5_000_000,
            weekly_payment=96_153,
            duration_seasons=2,
            start_season=1,
            end_season=2,
            is_active=True,
        )

        # First execute: club lookup; second execute: existing-active-deals query
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(data=[existing_active]),
        ])

        await finance_service.create_sponsorship_deal(
            club_id=1, career_id=1, season=3,
        )

        assert existing_active.is_active is False

    @pytest.mark.asyncio
    async def test_get_active_sponsorship_deal_returns_persisted_deal(
        self, finance_service, fake_session
    ):
        """get_active_sponsorship_deal should return the row stored in the database."""
        from app.models.sponsorship_deal import SponsorshipDeal

        deal = SponsorshipDeal(
            club_id=1,
            career_id=1,
            tier="large",
            sponsor_name="Large Sponsor Deal (Season 2)",
            annual_value=10_000_000,
            weekly_payment=192_307,
            duration_seasons=2,
            start_season=2,
            end_season=3,
            is_active=True,
        )
        fake_session.set_execute_results([FakeResult(scalar_value=deal)])

        active = await finance_service.get_active_sponsorship_deal(
            club_id=1, career_id=1, season=2,
        )

        assert active is deal

    @pytest.mark.asyncio
    async def test_get_active_sponsorship_deal_returns_none_when_no_match(
        self, finance_service, fake_session
    ):
        """When there is no active deal covering the season, return None."""
        fake_session.set_execute_results([FakeResult(scalar_value=None)])

        active = await finance_service.get_active_sponsorship_deal(
            club_id=1, career_id=1, season=5,
        )

        assert active is None

    @pytest.mark.asyncio
    async def test_renew_sponsorship_keeps_existing_active_deal(
        self, finance_service, fake_session
    ):
        """If an active deal already covers the season, no renewal is performed."""
        from app.models.sponsorship_deal import SponsorshipDeal

        existing = SponsorshipDeal(
            id=42,
            club_id=1,
            career_id=1,
            tier="medium",
            sponsor_name="Existing",
            annual_value=5_000_000,
            weekly_payment=96_153,
            duration_seasons=2,
            start_season=1,
            end_season=2,
            is_active=True,
        )
        fake_session.set_execute_results([FakeResult(scalar_value=existing)])

        result = await finance_service.renew_sponsorship_if_expired(
            club_id=1, career_id=1, season=2,
        )

        assert result["renewed"] is False
        assert result["deal"]["start_season"] == 1
        assert result["deal"]["end_season"] == 2

    @pytest.mark.asyncio
    async def test_renew_sponsorship_creates_new_deal_when_none_active(
        self, finance_service, fake_session
    ):
        """If no active deal exists, a new one is generated and persisted."""
        from app.models.sponsorship_deal import SponsorshipDeal

        club = FakeClub(id=1, reputation=55, stadium_level=3)
        # Sequence of execute() calls expected:
        # 1. get_active_sponsorship_deal -> None
        # 2. generate_sponsorship_deal: select(Club) -> club
        # 3. create_sponsorship_deal: existing active deals -> empty
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),  # No active deal
            FakeResult(scalar_value=club),  # Club lookup for generate
            FakeResult(data=[]),            # No existing active deals to deactivate
        ])

        result = await finance_service.renew_sponsorship_if_expired(
            club_id=1, career_id=1, season=4, league_position=7,
        )

        assert result["renewed"] is True
        assert result["deal"]["start_season"] == 4
        assert result["deal"]["end_season"] >= 4
        # A SponsorshipDeal should have been added to the session
        added_deals = [obj for obj in fake_session.added if isinstance(obj, SponsorshipDeal)]
        assert len(added_deals) == 1


class TestProcessWeeklyFinancesWithSponsorship:
    """Tests verifying that process_weekly_finances includes sponsorship income."""

    @pytest.mark.asyncio
    async def test_weekly_finances_credits_sponsorship_income(
        self, finance_service, fake_session
    ):
        """Active sponsorship deal should add weekly payment to balance."""
        from unittest.mock import MagicMock
        from app.models.sponsorship_deal import SponsorshipDeal

        club = FakeClub(id=1, balance=10_000_000)
        active_deal = SponsorshipDeal(
            club_id=1,
            career_id=1,
            tier="medium",
            sponsor_name="Medium Sponsor Deal (Season 1)",
            annual_value=5_200_000,
            weekly_payment=100_000,
            duration_seasons=1,
            start_season=1,
            end_season=1,
            is_active=True,
        )

        # Sequence of execute() calls inside process_weekly_finances:
        # 1. SELECT Club.balance for previous_balance
        # 2. SELECT player wages aggregate
        # 3. _update_club_balance for player wages: SELECT Club
        # 4. SELECT staff wages aggregate
        # 5. _update_club_balance for staff wages: SELECT Club
        # 6. get_active_sponsorship_deal: SELECT SponsorshipDeal -> active_deal
        # 7. process_sponsorship_payment -> record_income -> _update_club_balance: SELECT Club
        fake_session.set_execute_results([
            FakeResult(scalar_value=10_000_000),
            FakeResult(data=[MagicMock(total_wages=200_000, player_count=20)]),
            FakeResult(scalar_value=club),
            FakeResult(data=[MagicMock(total_wages=50_000, staff_count=5)]),
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=active_deal),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=10,
        )

        assert result["player_wages_total"] == 200_000
        assert result["staff_wages_total"] == 50_000
        assert result["sponsorship_payment_total"] == 100_000
        assert result["sponsorship_tier"] == "medium"
        # 3 transactions: player wages, staff wages, sponsorship
        assert len(result["transactions"]) == 3
        # New balance = previous - wages + sponsorship
        assert result["new_balance"] == 10_000_000 - 250_000 + 100_000

    @pytest.mark.asyncio
    async def test_weekly_finances_skips_sponsorship_when_none_active(
        self, finance_service, fake_session
    ):
        """When no active deal exists, sponsorship_payment_total is 0."""
        from unittest.mock import MagicMock

        club = FakeClub(id=1, balance=5_000_000)

        # Sequence: balance, player wages, _update for players, staff wages,
        # _update for staff, get_active_sponsorship_deal -> None
        fake_session.set_execute_results([
            FakeResult(scalar_value=5_000_000),
            FakeResult(data=[MagicMock(total_wages=100_000, player_count=10)]),
            FakeResult(scalar_value=club),
            FakeResult(data=[MagicMock(total_wages=20_000, staff_count=2)]),
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=15,
        )

        assert result["sponsorship_payment_total"] == 0
        assert result["sponsorship_tier"] is None
        # Only 2 transactions: player wages, staff wages
        assert len(result["transactions"]) == 2
        assert result["new_balance"] == 5_000_000 - 120_000
