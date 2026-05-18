"""
Tests for Finance Service - Matchday Revenue Calculation (Task 11.4)

Tests the calculate_matchday_revenue method including:
- Stadium capacity lookup based on level
- Attendance calculation with fill rate
- Ticket price calculation based on competition and opponent
- Revenue recording as MATCHDAY_REVENUE income transaction
- Different scenarios (competition types, stadium levels, opponent reputations)
- Input validation and edge cases
"""

import pytest
from unittest.mock import MagicMock

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


@pytest.fixture
def mock_club():
    """Create a fake club with default values (stadium_level=3, reputation=60)."""
    return FakeClub()


class TestStadiumCapacityLookup:
    """Test stadium capacity determination based on level."""

    def test_stadium_capacity_level_1(self, finance_service):
        """Level 1 stadium has 10,000 capacity."""
        assert finance_service.STADIUM_CAPACITY_BY_LEVEL[1] == 10_000

    def test_stadium_capacity_level_2(self, finance_service):
        """Level 2 stadium has 25,000 capacity."""
        assert finance_service.STADIUM_CAPACITY_BY_LEVEL[2] == 25_000

    def test_stadium_capacity_level_3(self, finance_service):
        """Level 3 stadium has 40,000 capacity."""
        assert finance_service.STADIUM_CAPACITY_BY_LEVEL[3] == 40_000

    def test_stadium_capacity_level_4(self, finance_service):
        """Level 4 stadium has 60,000 capacity."""
        assert finance_service.STADIUM_CAPACITY_BY_LEVEL[4] == 60_000

    def test_stadium_capacity_level_5(self, finance_service):
        """Level 5 stadium has 80,000 capacity."""
        assert finance_service.STADIUM_CAPACITY_BY_LEVEL[5] == 80_000

    def test_stadium_capacity_matches_infrastructure(self, finance_service):
        """Capacity values must match infrastructure_service Task 12.8 effects."""
        from app.services.infrastructure_service import (
            CATEGORY_EFFECTS,
            InfrastructureCategory,
        )
        for level in range(1, 6):
            expected = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level][
                "max_capacity"
            ]
            assert finance_service.STADIUM_CAPACITY_BY_LEVEL[level] == expected

    def test_stadium_revenue_multiplier_matches_infrastructure(self, finance_service):
        """Revenue multipliers must match infrastructure_service Task 12.8 effects."""
        from app.services.infrastructure_service import (
            CATEGORY_EFFECTS,
            InfrastructureCategory,
        )
        for level in range(1, 6):
            expected = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level][
                "matchday_revenue_multiplier"
            ]
            assert (
                finance_service.STADIUM_REVENUE_MULTIPLIER_BY_LEVEL[level] == expected
            )

    def test_stadium_revenue_multiplier_monotonically_increasing(self, finance_service):
        """Higher Stadium levels never reduce the revenue multiplier."""
        multipliers = [
            finance_service.STADIUM_REVENUE_MULTIPLIER_BY_LEVEL[level]
            for level in range(1, 6)
        ]
        for prev, curr in zip(multipliers, multipliers[1:]):
            assert curr > prev


class TestFillRateCalculation:
    """Test the fill rate calculation logic."""

    def test_fill_rate_low_reputation_league(self, finance_service):
        """Low reputation club in league match has lower fill rate."""
        fill_rate = finance_service._calculate_fill_rate(
            club_reputation=20,
            competition="league",
            opponent_reputation=50,
        )
        # base: 0.40 + (20/100)*0.45 = 0.49
        # competition: 0.0
        # opponent: (50/100)*0.10 = 0.05
        # total: 0.54
        assert 0.50 <= fill_rate <= 0.60

    def test_fill_rate_high_reputation_league(self, finance_service):
        """High reputation club in league match has higher fill rate."""
        fill_rate = finance_service._calculate_fill_rate(
            club_reputation=90,
            competition="league",
            opponent_reputation=80,
        )
        # base: 0.40 + (90/100)*0.45 = 0.805
        # competition: 0.0
        # opponent: (80/100)*0.10 = 0.08
        # total: 0.885
        assert 0.85 <= fill_rate <= 0.95

    def test_fill_rate_continental_cup_bonus(self, finance_service):
        """Continental cup gives +10% fill rate bonus."""
        league_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="league",
            opponent_reputation=50,
        )
        continental_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="continental_cup",
            opponent_reputation=50,
        )
        assert continental_rate - league_rate == pytest.approx(0.10, abs=0.001)

    def test_fill_rate_domestic_cup_bonus(self, finance_service):
        """Domestic cup gives +5% fill rate bonus."""
        league_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="league",
            opponent_reputation=50,
        )
        cup_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="domestic_cup",
            opponent_reputation=50,
        )
        assert cup_rate - league_rate == pytest.approx(0.05, abs=0.001)

    def test_fill_rate_friendly_penalty(self, finance_service):
        """Friendly gives -10% fill rate penalty."""
        league_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="league",
            opponent_reputation=50,
        )
        friendly_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="friendly",
            opponent_reputation=50,
        )
        assert league_rate - friendly_rate == pytest.approx(0.10, abs=0.001)

    def test_fill_rate_minimum_clamped(self, finance_service):
        """Fill rate never goes below 0.3 (30%)."""
        fill_rate = finance_service._calculate_fill_rate(
            club_reputation=1,
            competition="friendly",
            opponent_reputation=1,
        )
        assert fill_rate >= 0.3

    def test_fill_rate_maximum_clamped(self, finance_service):
        """Fill rate never exceeds 1.0 (100%)."""
        fill_rate = finance_service._calculate_fill_rate(
            club_reputation=100,
            competition="continental_cup",
            opponent_reputation=100,
        )
        assert fill_rate <= 1.0

    def test_fill_rate_top_opponent_draws_more(self, finance_service):
        """Higher opponent reputation draws bigger crowds."""
        low_opponent_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="league",
            opponent_reputation=20,
        )
        high_opponent_rate = finance_service._calculate_fill_rate(
            club_reputation=50,
            competition="league",
            opponent_reputation=90,
        )
        assert high_opponent_rate > low_opponent_rate


class TestTicketPriceCalculation:
    """Test ticket price calculation logic."""

    def test_league_base_price(self, finance_service):
        """League base ticket price is 30."""
        price = finance_service._calculate_ticket_price(
            competition="league",
            opponent_reputation=1,
        )
        # base: 30, premium: (1/100)*0.50 = 0.005 -> 30 * 1.005 = 30
        assert price == 30

    def test_continental_cup_base_price(self, finance_service):
        """Continental cup has higher base price (50)."""
        price = finance_service._calculate_ticket_price(
            competition="continental_cup",
            opponent_reputation=1,
        )
        # base: 50, premium: (1/100)*0.50 = 0.005 -> 50 * 1.005 = 50
        assert price == 50

    def test_domestic_cup_base_price(self, finance_service):
        """Domestic cup base price is 35."""
        price = finance_service._calculate_ticket_price(
            competition="domestic_cup",
            opponent_reputation=1,
        )
        assert price == 35

    def test_friendly_base_price(self, finance_service):
        """Friendly base price is 15."""
        price = finance_service._calculate_ticket_price(
            competition="friendly",
            opponent_reputation=1,
        )
        assert price == 15

    def test_high_reputation_opponent_premium(self, finance_service):
        """High reputation opponent increases ticket price."""
        low_rep_price = finance_service._calculate_ticket_price(
            competition="league",
            opponent_reputation=10,
        )
        high_rep_price = finance_service._calculate_ticket_price(
            competition="league",
            opponent_reputation=100,
        )
        assert high_rep_price > low_rep_price

    def test_max_opponent_premium(self, finance_service):
        """Max opponent reputation gives 50% premium."""
        price = finance_service._calculate_ticket_price(
            competition="league",
            opponent_reputation=100,
        )
        # base: 30, premium: (100/100)*0.50 = 0.50 -> 30 * 1.50 = 45
        assert price == 45

    def test_unknown_competition_uses_default(self, finance_service):
        """Unknown competition type uses default ticket price (25)."""
        price = finance_service._calculate_ticket_price(
            competition="unknown_competition",
            opponent_reputation=50,
        )
        # base: 25, premium: (50/100)*0.50 = 0.25 -> 25 * 1.25 = 31
        assert price == 31

    def test_minimum_ticket_price(self, finance_service):
        """Ticket price is always at least 1."""
        price = finance_service._calculate_ticket_price(
            competition="friendly",
            opponent_reputation=1,
        )
        assert price >= 1


class TestCalculateMatchdayRevenue:
    """Test the full matchday revenue calculation method."""

    @pytest.mark.asyncio
    async def test_basic_league_match_revenue(self, finance_service, fake_session):
        """Test basic league match revenue calculation."""
        club = FakeClub(stadium_level=3, reputation=60)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),   # get club for calculate_matchday_revenue
            FakeResult(scalar_value=club),   # _update_club_balance in record_income
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1,
            career_id=1,
            competition="league",
            opponent_reputation=50,
            season=1,
            week=10,
        )

        assert result["club_id"] == 1
        assert result["career_id"] == 1
        assert result["stadium_capacity"] == 40_000  # Level 3
        assert result["stadium_level"] == 3
        assert result["stadium_revenue_multiplier"] == 1.5
        assert result["competition"] == "league"
        assert result["opponent_reputation"] == 50
        assert result["revenue"] > 0
        assert result["attendance"] > 0
        assert result["ticket_price"] > 0
        assert result["fill_rate"] > 0
        # Revenue = int(attendance * ticket_price * stadium_revenue_multiplier)
        assert result["base_revenue"] == result["attendance"] * result["ticket_price"]
        assert result["revenue"] == int(
            result["base_revenue"] * result["stadium_revenue_multiplier"]
        )

    @pytest.mark.asyncio
    async def test_revenue_recorded_as_matchday_income(self, finance_service, fake_session):
        """Test that revenue is recorded as MATCHDAY_REVENUE income transaction."""
        club = FakeClub(stadium_level=2, reputation=50)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),   # get club
            FakeResult(scalar_value=club),   # _update_club_balance
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1,
            career_id=1,
            competition="league",
            opponent_reputation=40,
            season=1,
            week=5,
        )

        # Check that a transaction was added to the session
        assert len(fake_session.added) == 1
        transaction = fake_session.added[0]
        assert transaction.transaction_type == TransactionType.INCOME.value
        assert transaction.category == IncomeCategory.MATCHDAY_REVENUE.value
        assert transaction.amount == result["revenue"]
        assert transaction.season == 1
        assert transaction.week == 5

    @pytest.mark.asyncio
    async def test_higher_stadium_level_more_revenue(self, finance_service, fake_session):
        """Test that higher stadium level produces more revenue."""
        # Level 2 stadium (20k capacity)
        club_small = FakeClub(stadium_level=2, reputation=50)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club_small),
            FakeResult(scalar_value=club_small),
        ])
        result_small = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=5,
        )

        # Level 5 stadium (75k capacity)
        fake_session._execute_index = 0
        club_large = FakeClub(stadium_level=5, reputation=50)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club_large),
            FakeResult(scalar_value=club_large),
        ])
        result_large = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=5,
        )

        assert result_large["revenue"] > result_small["revenue"]
        assert result_large["stadium_capacity"] == 80_000
        assert result_small["stadium_capacity"] == 25_000

    @pytest.mark.asyncio
    async def test_continental_cup_higher_revenue(self, finance_service, fake_session):
        """Test that continental cup generates more revenue than league."""
        club = FakeClub(stadium_level=3, reputation=60)

        # League match
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])
        league_result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=5,
        )

        # Continental cup match
        fake_session._execute_index = 0
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])
        continental_result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="continental_cup",
            opponent_reputation=50, season=1, week=5,
        )

        assert continental_result["revenue"] > league_result["revenue"]

    @pytest.mark.asyncio
    async def test_high_reputation_opponent_more_revenue(self, finance_service, fake_session):
        """Test that playing against a high-reputation opponent generates more revenue."""
        club = FakeClub(stadium_level=3, reputation=50)

        # Low reputation opponent
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])
        low_rep_result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=20, season=1, week=5,
        )

        # High reputation opponent
        fake_session._execute_index = 0
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])
        high_rep_result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=90, season=1, week=5,
        )

        assert high_rep_result["revenue"] > low_rep_result["revenue"]

    @pytest.mark.asyncio
    async def test_level_1_stadium_revenue(self, finance_service, fake_session):
        """Test revenue for smallest stadium (level 1, 10k capacity)."""
        club = FakeClub(stadium_level=1, reputation=30)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=30, season=1, week=5,
        )

        assert result["stadium_capacity"] == 10_000
        assert result["attendance"] <= 10_000
        assert result["revenue"] > 0

    @pytest.mark.asyncio
    async def test_level_5_stadium_sold_out(self, finance_service, fake_session):
        """Test revenue for largest stadium with high demand (near sold out)."""
        club = FakeClub(stadium_level=5, reputation=95)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="continental_cup",
            opponent_reputation=95, season=1, week=5,
        )

        assert result["stadium_capacity"] == 80_000
        # With high reputation + continental cup + high opponent, should be near capacity
        assert result["fill_rate"] >= 0.9
        assert result["attendance"] >= 72_000  # At least 90% of 80k


class TestMatchdayRevenueValidation:
    """Test input validation for matchday revenue calculation."""

    @pytest.mark.asyncio
    async def test_rejects_opponent_reputation_zero(self, finance_service):
        """Test that opponent reputation of 0 is rejected."""
        with pytest.raises(ValueError, match="Opponent reputation must be between 1 and 100"):
            await finance_service.calculate_matchday_revenue(
                club_id=1, career_id=1, competition="league",
                opponent_reputation=0, season=1, week=5,
            )

    @pytest.mark.asyncio
    async def test_rejects_opponent_reputation_over_100(self, finance_service):
        """Test that opponent reputation over 100 is rejected."""
        with pytest.raises(ValueError, match="Opponent reputation must be between 1 and 100"):
            await finance_service.calculate_matchday_revenue(
                club_id=1, career_id=1, competition="league",
                opponent_reputation=101, season=1, week=5,
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_week(self, finance_service):
        """Test that invalid week is rejected."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.calculate_matchday_revenue(
                club_id=1, career_id=1, competition="league",
                opponent_reputation=50, season=1, week=0,
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_season(self, finance_service):
        """Test that invalid season is rejected."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.calculate_matchday_revenue(
                club_id=1, career_id=1, competition="league",
                opponent_reputation=50, season=0, week=5,
            )

    @pytest.mark.asyncio
    async def test_rejects_club_not_found(self, finance_service, fake_session):
        """Test that missing club raises ValueError."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),  # Club not found
        ])

        with pytest.raises(ValueError, match="Club with id 999 not found"):
            await finance_service.calculate_matchday_revenue(
                club_id=999, career_id=1, competition="league",
                opponent_reputation=50, season=1, week=5,
            )


class TestMatchdayRevenueFormula:
    """Test that the revenue formula is correctly applied."""

    @pytest.mark.asyncio
    async def test_revenue_equals_base_times_multiplier(self, finance_service, fake_session):
        """Verify revenue = int(base_revenue * stadium_revenue_multiplier)."""
        club = FakeClub(stadium_level=4, reputation=70)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=60, season=1, week=10,
        )

        expected_base = result["attendance"] * result["ticket_price"]
        expected_revenue = int(expected_base * result["stadium_revenue_multiplier"])
        assert result["base_revenue"] == expected_base
        assert result["revenue"] == expected_revenue

    @pytest.mark.asyncio
    async def test_attendance_equals_capacity_times_fill_rate(self, finance_service, fake_session):
        """Verify attendance = int(capacity * fill_rate)."""
        club = FakeClub(stadium_level=3, reputation=50)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=10,
        )

        expected_attendance = int(result["stadium_capacity"] * result["fill_rate"])
        assert result["attendance"] == expected_attendance

    @pytest.mark.asyncio
    async def test_balance_updated_after_revenue(self, finance_service, fake_session):
        """Test that club balance is updated after recording revenue."""
        club = FakeClub(stadium_level=3, reputation=60, balance=10_000_000)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),   # get club
            FakeResult(scalar_value=club),   # _update_club_balance
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=10,
        )

        # Balance should have increased by the revenue amount
        assert club.balance == 10_000_000 + result["revenue"]


class TestStadiumLevelImpactOnRevenue:
    """Verify the Stadium infrastructure level changes revenue (Tasks 11.4 + 12.8)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
    async def test_stadium_level_reported_in_result(self, finance_service, fake_session, level):
        """Result should expose the home club's stadium_level for transparency."""
        club = FakeClub(stadium_level=level, reputation=55)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="league",
            opponent_reputation=50, season=1, week=5,
        )

        assert result["stadium_level"] == level
        assert (
            result["stadium_revenue_multiplier"]
            == finance_service.STADIUM_REVENUE_MULTIPLIER_BY_LEVEL[level]
        )
        assert (
            result["stadium_capacity"]
            == finance_service.STADIUM_CAPACITY_BY_LEVEL[level]
        )

    @pytest.mark.asyncio
    async def test_revenue_is_monotonic_in_stadium_level(self, finance_service, fake_session):
        """For identical reputation/competition/opponent, revenue grows with level."""
        revenues = []
        for level in range(1, 6):
            fake_session._execute_index = 0
            club = FakeClub(stadium_level=level, reputation=55)
            fake_session.set_execute_results([
                FakeResult(scalar_value=club),
                FakeResult(scalar_value=club),
            ])
            result = await finance_service.calculate_matchday_revenue(
                club_id=1, career_id=1, competition="league",
                opponent_reputation=50, season=1, week=5,
            )
            revenues.append(result["revenue"])

        # Strictly increasing across all five levels.
        for prev, curr in zip(revenues, revenues[1:]):
            assert curr > prev, (
                f"Stadium upgrade reduced revenue: {revenues}"
            )

    @pytest.mark.asyncio
    async def test_stadium_multiplier_actually_scales_revenue(
        self, finance_service, fake_session
    ):
        """Level 5 vs level 1 with same fill rate inputs gives multiplier-scaled revenue."""
        # Use a high-reputation, sold-out scenario so both clubs fill to 1.0:
        # base = 0.40 + (95/100)*0.45 = 0.8275
        # opponent bonus = 0.10, continental bonus = 0.10 -> 1.0275 -> clamped to 1.0
        # so fill_rate = 1.0 for both.
        club_low = FakeClub(stadium_level=1, reputation=95)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club_low),
            FakeResult(scalar_value=club_low),
        ])
        low = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="continental_cup",
            opponent_reputation=95, season=1, week=5,
        )

        fake_session._execute_index = 0
        club_high = FakeClub(stadium_level=5, reputation=95)
        fake_session.set_execute_results([
            FakeResult(scalar_value=club_high),
            FakeResult(scalar_value=club_high),
        ])
        high = await finance_service.calculate_matchday_revenue(
            club_id=1, career_id=1, competition="continental_cup",
            opponent_reputation=95, season=1, week=5,
        )

        # Both at 100% fill, ticket prices identical (depend only on competition/opp)
        assert low["fill_rate"] == 1.0
        assert high["fill_rate"] == 1.0
        assert low["ticket_price"] == high["ticket_price"]
        # Capacity ratio: 80_000 / 10_000 = 8x
        # Multiplier ratio: 2.25 / 1.0 = 2.25x
        # So total revenue ratio should be ~18x
        assert high["revenue"] == int(
            low["base_revenue"]
            * (high["stadium_capacity"] / low["stadium_capacity"])
            * high["stadium_revenue_multiplier"]
        )
