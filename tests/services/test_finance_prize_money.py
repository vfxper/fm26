"""
Tests for Finance Service - Prize Money Distribution System (Task 11.5)

Tests the prize money distribution functionality including:
- League position prize money (positions 1-20)
- Domestic cup prize money (winner, runner-up, semi-finalists, quarter-finalists)
- Continental cup prize money (winner, runner-up, semi-finalists, group stage)
- get_prize_money_table() method
- distribute_prize_money() method
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
    """A simple fake club object for testing balance updates."""

    def __init__(self, id=1, name="Test FC", balance=50_000_000):
        self.id = id
        self.name = name
        self.balance = balance


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
    """Create a fake club with initial balance."""
    return FakeClub()


class TestGetPrizeMoneyTable:
    """Test get_prize_money_table() method."""

    def test_get_league_prize_table(self, finance_service):
        """Test retrieving the league prize money table."""
        table = finance_service.get_prize_money_table("league")

        assert len(table) == 20
        assert table[1] == 50_000_000
        assert table[2] == 40_000_000
        assert table[3] == 35_000_000
        assert table[20] == 5_000_000

    def test_league_prizes_decrease_by_position(self, finance_service):
        """Test that league prizes decrease as position increases."""
        table = finance_service.get_prize_money_table("league")

        for pos in range(1, 20):
            assert table[pos] > table[pos + 1], (
                f"Position {pos} ({table[pos]}) should have more prize money "
                f"than position {pos + 1} ({table[pos + 1]})"
            )

    def test_get_domestic_cup_prize_table(self, finance_service):
        """Test retrieving the domestic cup prize money table."""
        table = finance_service.get_prize_money_table("domestic_cup")

        assert table["winner"] == 10_000_000
        assert table["runner_up"] == 5_000_000
        assert table["semi_finalist"] == 2_000_000
        assert table["quarter_finalist"] == 1_000_000

    def test_domestic_cup_prizes_decrease_by_stage(self, finance_service):
        """Test that domestic cup prizes decrease by stage."""
        table = finance_service.get_prize_money_table("domestic_cup")

        assert table["winner"] > table["runner_up"]
        assert table["runner_up"] > table["semi_finalist"]
        assert table["semi_finalist"] > table["quarter_finalist"]

    def test_get_continental_cup_prize_table(self, finance_service):
        """Test retrieving the continental cup prize money table."""
        table = finance_service.get_prize_money_table("continental_cup")

        assert table["winner"] == 30_000_000
        assert table["runner_up"] == 20_000_000
        assert table["semi_finalist"] == 10_000_000
        assert table["group_stage"] == 5_000_000

    def test_continental_cup_prizes_decrease_by_stage(self, finance_service):
        """Test that continental cup prizes decrease by stage."""
        table = finance_service.get_prize_money_table("continental_cup")

        assert table["winner"] > table["runner_up"]
        assert table["runner_up"] > table["semi_finalist"]
        assert table["semi_finalist"] > table["group_stage"]

    def test_continental_cup_prizes_higher_than_domestic(self, finance_service):
        """Test that continental cup prizes are higher than domestic cup."""
        continental = finance_service.get_prize_money_table("continental_cup")
        domestic = finance_service.get_prize_money_table("domestic_cup")

        assert continental["winner"] > domestic["winner"]
        assert continental["runner_up"] > domestic["runner_up"]
        assert continental["semi_finalist"] > domestic["semi_finalist"]

    def test_invalid_competition_type_raises_error(self, finance_service):
        """Test that an invalid competition type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown competition type"):
            finance_service.get_prize_money_table("invalid_competition")

    def test_returns_copy_not_reference(self, finance_service):
        """Test that get_prize_money_table returns a copy, not a reference."""
        table1 = finance_service.get_prize_money_table("league")
        table1[1] = 0  # Modify the returned copy

        table2 = finance_service.get_prize_money_table("league")
        assert table2[1] == 50_000_000  # Original should be unchanged


class TestDistributePrizeMoneyLeague:
    """Test distribute_prize_money() for league competitions."""

    @pytest.mark.asyncio
    async def test_league_first_place(self, finance_service, fake_session, mock_club):
        """Test prize money for league 1st place."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="league", position=1,
            season=1, week=38,
        )

        assert transaction.amount == 50_000_000
        assert transaction.category == IncomeCategory.PRIZE_MONEY.value
        assert transaction.transaction_type == TransactionType.INCOME.value
        assert "Position 1" in transaction.description

    @pytest.mark.asyncio
    async def test_league_last_place(self, finance_service, fake_session, mock_club):
        """Test prize money for league 20th place."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="league", position=20,
            season=1, week=38,
        )

        assert transaction.amount == 5_000_000
        assert "Position 20" in transaction.description

    @pytest.mark.asyncio
    async def test_league_mid_table(self, finance_service, fake_session, mock_club):
        """Test prize money for league 10th place."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="league", position=10,
            season=2, week=38,
        )

        assert transaction.amount == 15_000_000
        assert transaction.season == 2
        assert transaction.week == 38

    @pytest.mark.asyncio
    async def test_league_updates_club_balance(self, finance_service, fake_session, mock_club):
        """Test that league prize money updates the club balance."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        initial_balance = mock_club.balance
        await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="league", position=1,
            season=1, week=38,
        )

        assert mock_club.balance == initial_balance + 50_000_000

    @pytest.mark.asyncio
    async def test_league_invalid_position_zero(self, finance_service):
        """Test that position 0 is rejected for league."""
        with pytest.raises(ValueError, match="League position must be an integer between 1 and 20"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position=0,
                season=1, week=38,
            )

    @pytest.mark.asyncio
    async def test_league_invalid_position_21(self, finance_service):
        """Test that position 21 is rejected for league."""
        with pytest.raises(ValueError, match="League position must be an integer between 1 and 20"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position=21,
                season=1, week=38,
            )

    @pytest.mark.asyncio
    async def test_league_invalid_position_string(self, finance_service):
        """Test that a string position is rejected for league."""
        with pytest.raises(ValueError, match="League position must be an integer between 1 and 20"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position="winner",
                season=1, week=38,
            )

    @pytest.mark.asyncio
    async def test_league_invalid_position_negative(self, finance_service):
        """Test that a negative position is rejected for league."""
        with pytest.raises(ValueError, match="League position must be an integer between 1 and 20"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position=-1,
                season=1, week=38,
            )


class TestDistributePrizeMoneyDomesticCup:
    """Test distribute_prize_money() for domestic cup competitions."""

    @pytest.mark.asyncio
    async def test_domestic_cup_winner(self, finance_service, fake_session, mock_club):
        """Test prize money for domestic cup winner."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="domestic_cup", position="winner",
            season=1, week=40,
        )

        assert transaction.amount == 10_000_000
        assert transaction.category == IncomeCategory.PRIZE_MONEY.value
        assert "Winner" in transaction.description

    @pytest.mark.asyncio
    async def test_domestic_cup_runner_up(self, finance_service, fake_session, mock_club):
        """Test prize money for domestic cup runner-up."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="domestic_cup", position="runner_up",
            season=1, week=40,
        )

        assert transaction.amount == 5_000_000
        assert "Runner Up" in transaction.description

    @pytest.mark.asyncio
    async def test_domestic_cup_semi_finalist(self, finance_service, fake_session, mock_club):
        """Test prize money for domestic cup semi-finalist."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="domestic_cup", position="semi_finalist",
            season=1, week=35,
        )

        assert transaction.amount == 2_000_000
        assert "Semi Finalist" in transaction.description

    @pytest.mark.asyncio
    async def test_domestic_cup_quarter_finalist(self, finance_service, fake_session, mock_club):
        """Test prize money for domestic cup quarter-finalist."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="domestic_cup", position="quarter_finalist",
            season=1, week=30,
        )

        assert transaction.amount == 1_000_000
        assert "Quarter Finalist" in transaction.description

    @pytest.mark.asyncio
    async def test_domestic_cup_invalid_position(self, finance_service):
        """Test that an invalid cup position is rejected."""
        with pytest.raises(ValueError, match="Invalid position"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="domestic_cup", position="round_of_16",
                season=1, week=30,
            )

    @pytest.mark.asyncio
    async def test_domestic_cup_integer_position_rejected(self, finance_service):
        """Test that an integer position is rejected for cup competitions."""
        with pytest.raises(ValueError, match="Cup position must be a string"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="domestic_cup", position=1,
                season=1, week=40,
            )


class TestDistributePrizeMoneyContinentalCup:
    """Test distribute_prize_money() for continental cup competitions."""

    @pytest.mark.asyncio
    async def test_continental_cup_winner(self, finance_service, fake_session, mock_club):
        """Test prize money for continental cup winner."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="continental_cup", position="winner",
            season=1, week=45,
        )

        assert transaction.amount == 30_000_000
        assert transaction.category == IncomeCategory.PRIZE_MONEY.value
        assert "Continental Cup" in transaction.description
        assert "Winner" in transaction.description

    @pytest.mark.asyncio
    async def test_continental_cup_runner_up(self, finance_service, fake_session, mock_club):
        """Test prize money for continental cup runner-up."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="continental_cup", position="runner_up",
            season=1, week=45,
        )

        assert transaction.amount == 20_000_000

    @pytest.mark.asyncio
    async def test_continental_cup_semi_finalist(self, finance_service, fake_session, mock_club):
        """Test prize money for continental cup semi-finalist."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="continental_cup", position="semi_finalist",
            season=1, week=42,
        )

        assert transaction.amount == 10_000_000

    @pytest.mark.asyncio
    async def test_continental_cup_group_stage(self, finance_service, fake_session, mock_club):
        """Test prize money for continental cup group stage exit."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="continental_cup", position="group_stage",
            season=1, week=20,
        )

        assert transaction.amount == 5_000_000
        assert "Group Stage" in transaction.description

    @pytest.mark.asyncio
    async def test_continental_cup_invalid_position(self, finance_service):
        """Test that an invalid continental cup position is rejected."""
        with pytest.raises(ValueError, match="Invalid position"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="continental_cup", position="quarter_finalist",
                season=1, week=30,
            )


class TestDistributePrizeMoneyValidation:
    """Test input validation for distribute_prize_money()."""

    @pytest.mark.asyncio
    async def test_invalid_competition_type(self, finance_service):
        """Test that an invalid competition type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown competition type"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="super_league", position=1,
                season=1, week=38,
            )

    @pytest.mark.asyncio
    async def test_invalid_week_zero(self, finance_service, fake_session, mock_club):
        """Test that week 0 is rejected (validation happens in record_income)."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position=1,
                season=1, week=0,
            )

    @pytest.mark.asyncio
    async def test_invalid_season_zero(self, finance_service, fake_session, mock_club):
        """Test that season 0 is rejected (validation happens in record_income)."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.distribute_prize_money(
                club_id=1, career_id=1,
                competition="league", position=1,
                season=0, week=38,
            )

    @pytest.mark.asyncio
    async def test_transaction_recorded_as_prize_money_category(
        self, finance_service, fake_session, mock_club
    ):
        """Test that all prize money is recorded under PRIZE_MONEY income category."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.distribute_prize_money(
            club_id=1, career_id=1,
            competition="league", position=5,
            season=1, week=38,
        )

        assert transaction.category == IncomeCategory.PRIZE_MONEY.value
        assert transaction.transaction_type == TransactionType.INCOME.value


class TestPrizeMoneyConstants:
    """Test the prize money constant tables directly."""

    def test_league_has_20_positions(self):
        """Test that league prize table has exactly 20 positions."""
        assert len(FinanceService.LEAGUE_PRIZE_MONEY) == 20

    def test_league_all_positions_positive(self):
        """Test that all league prize amounts are positive."""
        for pos, amount in FinanceService.LEAGUE_PRIZE_MONEY.items():
            assert amount > 0, f"Position {pos} has non-positive amount: {amount}"

    def test_domestic_cup_has_4_stages(self):
        """Test that domestic cup prize table has 4 stages."""
        assert len(FinanceService.DOMESTIC_CUP_PRIZE_MONEY) == 4

    def test_domestic_cup_all_amounts_positive(self):
        """Test that all domestic cup prize amounts are positive."""
        for stage, amount in FinanceService.DOMESTIC_CUP_PRIZE_MONEY.items():
            assert amount > 0, f"Stage '{stage}' has non-positive amount: {amount}"

    def test_continental_cup_has_4_stages(self):
        """Test that continental cup prize table has 4 stages."""
        assert len(FinanceService.CONTINENTAL_CUP_PRIZE_MONEY) == 4

    def test_continental_cup_all_amounts_positive(self):
        """Test that all continental cup prize amounts are positive."""
        for stage, amount in FinanceService.CONTINENTAL_CUP_PRIZE_MONEY.items():
            assert amount > 0, f"Stage '{stage}' has non-positive amount: {amount}"

    def test_prize_money_tables_mapping(self):
        """Test that PRIZE_MONEY_TABLES maps all three competition types."""
        assert "league" in FinanceService.PRIZE_MONEY_TABLES
        assert "domestic_cup" in FinanceService.PRIZE_MONEY_TABLES
        assert "continental_cup" in FinanceService.PRIZE_MONEY_TABLES
        assert len(FinanceService.PRIZE_MONEY_TABLES) == 3
