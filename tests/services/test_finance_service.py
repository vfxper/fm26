"""
Tests for Finance Service - Club Balance Sheet with Income/Expenditure Tracking (Task 11.1)

Tests the FinanceService class including:
- Recording income transactions (transfer sales, matchday revenue, prize money, sponsorship)
- Recording expenditure transactions (wages, transfer fees, infrastructure, staff wages)
- Generating balance sheets with categorized income and expenditure
- Transaction history with filtering
- Club balance updates on each transaction
- Input validation and edge cases
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.financial_transaction import (
    FinancialTransaction,
    TransactionType,
    IncomeCategory,
    ExpenditureCategory,
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
        """Return the first row from data (mimics SQLAlchemy Result.one())."""
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
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

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


@pytest.fixture
def fake_session():
    """Create a fake async database session."""
    return FakeSession()


@pytest.fixture
def finance_service(fake_session):
    """Create a FinanceService instance with fake session."""
    return FinanceService(fake_session)


class FakeClub:
    """A simple fake club object for testing balance updates."""

    def __init__(self, id=1, name="Test FC", balance=50_000_000):
        self.id = id
        self.name = name
        self.balance = balance
        self.transfer_budget = 20_000_000
        self.wage_budget = 500_000


@pytest.fixture
def mock_club():
    """Create a fake club with initial balance."""
    return FakeClub()


class TestRecordIncome:
    """Test recording income transactions."""

    @pytest.mark.asyncio
    async def test_record_transfer_sale_income(self, finance_service, fake_session, mock_club):
        """Test recording income from a transfer sale."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),  # _update_club_balance query
        ])

        transaction = await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.TRANSFER_SALES,
            amount=15_000_000,
            description="Sale of Player X to Club Y",
            season=1,
            week=5,
        )

        assert transaction.club_id == 1
        assert transaction.career_id == 1
        assert transaction.transaction_type == TransactionType.INCOME.value
        assert transaction.category == IncomeCategory.TRANSFER_SALES.value
        assert transaction.amount == 15_000_000
        assert transaction.description == "Sale of Player X to Club Y"
        assert transaction.season == 1
        assert transaction.week == 5
        assert transaction in fake_session.added
        assert fake_session.flushed

    @pytest.mark.asyncio
    async def test_record_matchday_revenue(self, finance_service, fake_session, mock_club):
        """Test recording matchday revenue income."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.MATCHDAY_REVENUE,
            amount=500_000,
            description="Matchday revenue - Week 10",
            season=1,
            week=10,
        )

        assert transaction.category == IncomeCategory.MATCHDAY_REVENUE.value
        assert transaction.amount == 500_000

    @pytest.mark.asyncio
    async def test_record_prize_money(self, finance_service, fake_session, mock_club):
        """Test recording prize money income."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.PRIZE_MONEY,
            amount=5_000_000,
            description="League 3rd place prize money",
            season=1,
            week=38,
        )

        assert transaction.category == IncomeCategory.PRIZE_MONEY.value
        assert transaction.amount == 5_000_000

    @pytest.mark.asyncio
    async def test_record_sponsorship_income(self, finance_service, fake_session, mock_club):
        """Test recording sponsorship income."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.SPONSORSHIP,
            amount=10_000_000,
            description="Annual sponsorship deal - Nike",
            season=1,
            week=1,
        )

        assert transaction.category == IncomeCategory.SPONSORSHIP.value
        assert transaction.amount == 10_000_000

    @pytest.mark.asyncio
    async def test_record_other_income(self, finance_service, fake_session, mock_club):
        """Test recording other income."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.OTHER_INCOME,
            amount=100_000,
            description="Merchandise sales",
            season=2,
            week=20,
        )

        assert transaction.category == IncomeCategory.OTHER_INCOME.value
        assert transaction.amount == 100_000

    @pytest.mark.asyncio
    async def test_income_updates_club_balance(self, finance_service, fake_session, mock_club):
        """Test that recording income updates the club balance."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        initial_balance = mock_club.balance
        await finance_service.record_income(
            club_id=1,
            career_id=1,
            category=IncomeCategory.TRANSFER_SALES,
            amount=5_000_000,
            description="Player sale",
            season=1,
            week=3,
        )

        assert mock_club.balance == initial_balance + 5_000_000


class TestRecordExpenditure:
    """Test recording expenditure transactions."""

    @pytest.mark.asyncio
    async def test_record_wages_expenditure(self, finance_service, fake_session, mock_club):
        """Test recording wages expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.WAGES,
            amount=500_000,
            description="Weekly player wages",
            season=1,
            week=5,
        )

        assert transaction.club_id == 1
        assert transaction.career_id == 1
        assert transaction.transaction_type == TransactionType.EXPENDITURE.value
        assert transaction.category == ExpenditureCategory.WAGES.value
        assert transaction.amount == 500_000
        assert transaction.description == "Weekly player wages"
        assert transaction in fake_session.added

    @pytest.mark.asyncio
    async def test_record_transfer_fee_expenditure(self, finance_service, fake_session, mock_club):
        """Test recording transfer fee expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.TRANSFER_FEES,
            amount=25_000_000,
            description="Transfer fee for Player Z",
            season=1,
            week=3,
        )

        assert transaction.category == ExpenditureCategory.TRANSFER_FEES.value
        assert transaction.amount == 25_000_000

    @pytest.mark.asyncio
    async def test_record_infrastructure_expenditure(self, finance_service, fake_session, mock_club):
        """Test recording infrastructure expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.INFRASTRUCTURE,
            amount=8_000_000,
            description="Stadium upgrade to level 3",
            season=2,
            week=15,
        )

        assert transaction.category == ExpenditureCategory.INFRASTRUCTURE.value
        assert transaction.amount == 8_000_000

    @pytest.mark.asyncio
    async def test_record_staff_wages_expenditure(self, finance_service, fake_session, mock_club):
        """Test recording staff wages expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.STAFF_WAGES,
            amount=100_000,
            description="Weekly staff wages",
            season=1,
            week=10,
        )

        assert transaction.category == ExpenditureCategory.STAFF_WAGES.value
        assert transaction.amount == 100_000

    @pytest.mark.asyncio
    async def test_record_other_expenditure(self, finance_service, fake_session, mock_club):
        """Test recording other expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        transaction = await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.OTHER_EXPENDITURE,
            amount=50_000,
            description="Miscellaneous expenses",
            season=1,
            week=8,
        )

        assert transaction.category == ExpenditureCategory.OTHER_EXPENDITURE.value
        assert transaction.amount == 50_000

    @pytest.mark.asyncio
    async def test_expenditure_decreases_club_balance(self, finance_service, fake_session, mock_club):
        """Test that recording expenditure decreases the club balance."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=mock_club),
        ])

        initial_balance = mock_club.balance
        await finance_service.record_expenditure(
            club_id=1,
            career_id=1,
            category=ExpenditureCategory.WAGES,
            amount=500_000,
            description="Weekly wages",
            season=1,
            week=5,
        )

        assert mock_club.balance == initial_balance - 500_000


class TestInputValidation:
    """Test input validation for income and expenditure recording."""

    @pytest.mark.asyncio
    async def test_income_rejects_zero_amount(self, finance_service):
        """Test that zero amount is rejected for income."""
        with pytest.raises(ValueError, match="Income amount must be positive"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=IncomeCategory.TRANSFER_SALES,
                amount=0, description="Invalid", season=1, week=1,
            )

    @pytest.mark.asyncio
    async def test_income_rejects_negative_amount(self, finance_service):
        """Test that negative amount is rejected for income."""
        with pytest.raises(ValueError, match="Income amount must be positive"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=IncomeCategory.TRANSFER_SALES,
                amount=-100, description="Invalid", season=1, week=1,
            )

    @pytest.mark.asyncio
    async def test_expenditure_rejects_zero_amount(self, finance_service):
        """Test that zero amount is rejected for expenditure."""
        with pytest.raises(ValueError, match="Expenditure amount must be positive"):
            await finance_service.record_expenditure(
                club_id=1, career_id=1,
                category=ExpenditureCategory.WAGES,
                amount=0, description="Invalid", season=1, week=1,
            )

    @pytest.mark.asyncio
    async def test_expenditure_rejects_negative_amount(self, finance_service):
        """Test that negative amount is rejected for expenditure."""
        with pytest.raises(ValueError, match="Expenditure amount must be positive"):
            await finance_service.record_expenditure(
                club_id=1, career_id=1,
                category=ExpenditureCategory.WAGES,
                amount=-500, description="Invalid", season=1, week=1,
            )

    @pytest.mark.asyncio
    async def test_income_rejects_invalid_week_zero(self, finance_service):
        """Test that week 0 is rejected."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=IncomeCategory.MATCHDAY_REVENUE,
                amount=100_000, description="Invalid week", season=1, week=0,
            )

    @pytest.mark.asyncio
    async def test_income_rejects_invalid_week_53(self, finance_service):
        """Test that week 53 is rejected."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=IncomeCategory.MATCHDAY_REVENUE,
                amount=100_000, description="Invalid week", season=1, week=53,
            )

    @pytest.mark.asyncio
    async def test_income_rejects_invalid_season(self, finance_service):
        """Test that season 0 is rejected."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=IncomeCategory.MATCHDAY_REVENUE,
                amount=100_000, description="Invalid season", season=0, week=1,
            )

    @pytest.mark.asyncio
    async def test_expenditure_rejects_invalid_week(self, finance_service):
        """Test that invalid week is rejected for expenditure."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.record_expenditure(
                club_id=1, career_id=1,
                category=ExpenditureCategory.WAGES,
                amount=100_000, description="Invalid week", season=1, week=53,
            )

    @pytest.mark.asyncio
    async def test_expenditure_rejects_invalid_season(self, finance_service):
        """Test that invalid season is rejected for expenditure."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.record_expenditure(
                club_id=1, career_id=1,
                category=ExpenditureCategory.WAGES,
                amount=100_000, description="Invalid season", season=-1, week=1,
            )

    @pytest.mark.asyncio
    async def test_income_rejects_invalid_category(self, finance_service):
        """Test that an invalid income category is rejected."""
        with pytest.raises(ValueError, match="Invalid income category"):
            await finance_service.record_income(
                club_id=1, career_id=1,
                category=ExpenditureCategory.WAGES,  # Wrong type
                amount=100_000, description="Invalid category", season=1, week=1,
            )

    @pytest.mark.asyncio
    async def test_expenditure_rejects_invalid_category(self, finance_service):
        """Test that an invalid expenditure category is rejected."""
        with pytest.raises(ValueError, match="Invalid expenditure category"):
            await finance_service.record_expenditure(
                club_id=1, career_id=1,
                category=IncomeCategory.TRANSFER_SALES,  # Wrong type
                amount=100_000, description="Invalid category", season=1, week=1,
            )


class TestGetBalanceSheet:
    """Test balance sheet generation."""

    @pytest.mark.asyncio
    async def test_balance_sheet_empty(self, finance_service, fake_session):
        """Test balance sheet with no transactions."""
        fake_session.set_execute_results([
            FakeResult(data=[]),                    # income query
            FakeResult(data=[]),                    # expenditure query
            FakeResult(scalar_value=50_000_000),   # club balance
            FakeResult(scalar_value=0),            # transaction count
        ])

        balance_sheet = await finance_service.get_balance_sheet(
            club_id=1, career_id=1
        )

        assert balance_sheet["club_id"] == 1
        assert balance_sheet["career_id"] == 1
        assert balance_sheet["season"] == "all"
        assert balance_sheet["total_income"] == 0
        assert balance_sheet["total_expenditure"] == 0
        assert balance_sheet["net_balance"] == 0
        assert balance_sheet["current_balance"] == 50_000_000
        assert balance_sheet["transaction_count"] == 0

        # All categories should be present with zero values
        for cat in IncomeCategory:
            assert cat.value in balance_sheet["income"]
            assert balance_sheet["income"][cat.value]["total"] == 0
            assert balance_sheet["income"][cat.value]["count"] == 0

        for cat in ExpenditureCategory:
            assert cat.value in balance_sheet["expenditure"]
            assert balance_sheet["expenditure"][cat.value]["total"] == 0
            assert balance_sheet["expenditure"][cat.value]["count"] == 0

    @pytest.mark.asyncio
    async def test_balance_sheet_with_transactions(self, finance_service, fake_session):
        """Test balance sheet with income and expenditure transactions."""
        # Create row-like objects for the grouped query results
        income_rows = [
            MagicMock(category="transfer_sales", total=15_000_000, count=2),
            MagicMock(category="matchday_revenue", total=3_000_000, count=6),
            MagicMock(category="sponsorship", total=10_000_000, count=1),
        ]
        expenditure_rows = [
            MagicMock(category="wages", total=12_000_000, count=24),
            MagicMock(category="transfer_fees", total=8_000_000, count=1),
        ]

        fake_session.set_execute_results([
            FakeResult(data=income_rows),
            FakeResult(data=expenditure_rows),
            FakeResult(scalar_value=58_000_000),
            FakeResult(scalar_value=34),
        ])

        balance_sheet = await finance_service.get_balance_sheet(
            club_id=1, career_id=1
        )

        assert balance_sheet["total_income"] == 28_000_000
        assert balance_sheet["total_expenditure"] == 20_000_000
        assert balance_sheet["net_balance"] == 8_000_000
        assert balance_sheet["current_balance"] == 58_000_000
        assert balance_sheet["transaction_count"] == 34

        # Check specific income categories
        assert balance_sheet["income"]["transfer_sales"]["total"] == 15_000_000
        assert balance_sheet["income"]["transfer_sales"]["count"] == 2
        assert balance_sheet["income"]["matchday_revenue"]["total"] == 3_000_000
        assert balance_sheet["income"]["sponsorship"]["total"] == 10_000_000

        # Check specific expenditure categories
        assert balance_sheet["expenditure"]["wages"]["total"] == 12_000_000
        assert balance_sheet["expenditure"]["wages"]["count"] == 24
        assert balance_sheet["expenditure"]["transfer_fees"]["total"] == 8_000_000

    @pytest.mark.asyncio
    async def test_balance_sheet_with_season_filter(self, finance_service, fake_session):
        """Test balance sheet filtered by season."""
        fake_session.set_execute_results([
            FakeResult(data=[
                MagicMock(category="matchday_revenue", total=2_000_000, count=4),
            ]),
            FakeResult(data=[
                MagicMock(category="wages", total=6_000_000, count=12),
            ]),
            FakeResult(scalar_value=45_000_000),
            FakeResult(scalar_value=16),
        ])

        balance_sheet = await finance_service.get_balance_sheet(
            club_id=1, career_id=1, season=2
        )

        assert balance_sheet["season"] == 2
        assert balance_sheet["total_income"] == 2_000_000
        assert balance_sheet["total_expenditure"] == 6_000_000
        assert balance_sheet["net_balance"] == -4_000_000


class TestGetTransactions:
    """Test transaction history retrieval with filters."""

    @pytest.mark.asyncio
    async def test_get_all_transactions(self, finance_service, fake_session):
        """Test getting all transactions without filters."""
        txn1 = FinancialTransaction(
            id=1, club_id=1, career_id=1,
            transaction_type="income", category="transfer_sales",
            amount=5_000_000, description="Sale", season=1, week=3,
        )
        txn2 = FinancialTransaction(
            id=2, club_id=1, career_id=1,
            transaction_type="expenditure", category="wages",
            amount=500_000, description="Wages", season=1, week=5,
        )

        fake_session.set_execute_results([
            FakeResult(data=[txn1, txn2]),
        ])

        transactions = await finance_service.get_transactions(
            club_id=1, career_id=1
        )

        assert len(transactions) == 2

    @pytest.mark.asyncio
    async def test_get_transactions_empty_result(self, finance_service, fake_session):
        """Test getting transactions when none exist."""
        fake_session.set_execute_results([
            FakeResult(data=[]),
        ])

        transactions = await finance_service.get_transactions(
            club_id=1, career_id=1
        )

        assert len(transactions) == 0


class TestFinancialTransactionModel:
    """Test the FinancialTransaction model."""

    def test_transaction_type_enum_values(self):
        """Test TransactionType enum has correct values."""
        assert TransactionType.INCOME.value == "income"
        assert TransactionType.EXPENDITURE.value == "expenditure"

    def test_income_category_enum_values(self):
        """Test IncomeCategory enum has all expected values."""
        assert IncomeCategory.TRANSFER_SALES.value == "transfer_sales"
        assert IncomeCategory.MATCHDAY_REVENUE.value == "matchday_revenue"
        assert IncomeCategory.PRIZE_MONEY.value == "prize_money"
        assert IncomeCategory.SPONSORSHIP.value == "sponsorship"
        assert IncomeCategory.OTHER_INCOME.value == "other_income"

    def test_expenditure_category_enum_values(self):
        """Test ExpenditureCategory enum has all expected values."""
        assert ExpenditureCategory.WAGES.value == "wages"
        assert ExpenditureCategory.TRANSFER_FEES.value == "transfer_fees"
        assert ExpenditureCategory.INFRASTRUCTURE.value == "infrastructure"
        assert ExpenditureCategory.STAFF_WAGES.value == "staff_wages"
        assert ExpenditureCategory.OTHER_EXPENDITURE.value == "other_expenditure"

    def test_transaction_to_dict(self):
        """Test FinancialTransaction to_dict method."""
        transaction = FinancialTransaction(
            id=1, club_id=1, career_id=1,
            transaction_type=TransactionType.INCOME.value,
            category=IncomeCategory.TRANSFER_SALES.value,
            amount=5_000_000, description="Player sale",
            season=1, week=5,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
        )

        result = transaction.to_dict()

        assert result["id"] == 1
        assert result["club_id"] == 1
        assert result["career_id"] == 1
        assert result["transaction_type"] == "income"
        assert result["category"] == "transfer_sales"
        assert result["amount"] == 5_000_000
        assert result["description"] == "Player sale"
        assert result["season"] == 1
        assert result["week"] == 5
        assert result["created_at"] == "2025-01-15T10:30:00"

    def test_transaction_repr(self):
        """Test FinancialTransaction __repr__ method."""
        transaction = FinancialTransaction(
            id=1,
            transaction_type=TransactionType.INCOME.value,
            category=IncomeCategory.TRANSFER_SALES.value,
            amount=5_000_000,
        )

        repr_str = repr(transaction)
        assert "FinancialTransaction" in repr_str
        assert "income" in repr_str
        assert "transfer_sales" in repr_str
        assert "5000000" in repr_str


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_income_week_1_boundary(self, finance_service, fake_session, mock_club):
        """Test recording income at week 1 boundary."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.record_income(
            club_id=1, career_id=1,
            category=IncomeCategory.MATCHDAY_REVENUE,
            amount=100_000, description="First week revenue",
            season=1, week=1,
        )

        assert transaction.week == 1

    @pytest.mark.asyncio
    async def test_income_week_52_boundary(self, finance_service, fake_session, mock_club):
        """Test recording income at week 52 boundary."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.record_income(
            club_id=1, career_id=1,
            category=IncomeCategory.MATCHDAY_REVENUE,
            amount=100_000, description="Last week revenue",
            season=1, week=52,
        )

        assert transaction.week == 52

    @pytest.mark.asyncio
    async def test_very_large_amount(self, finance_service, fake_session, mock_club):
        """Test recording a very large transaction amount."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.record_income(
            club_id=1, career_id=1,
            category=IncomeCategory.TRANSFER_SALES,
            amount=500_000_000, description="Record-breaking transfer sale",
            season=1, week=5,
        )

        assert transaction.amount == 500_000_000

    @pytest.mark.asyncio
    async def test_amount_of_one(self, finance_service, fake_session, mock_club):
        """Test recording minimum valid amount (1)."""
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])

        transaction = await finance_service.record_income(
            club_id=1, career_id=1,
            category=IncomeCategory.OTHER_INCOME,
            amount=1, description="Minimal income",
            season=1, week=1,
        )

        assert transaction.amount == 1

    @pytest.mark.asyncio
    async def test_club_not_found_for_balance_update(self, finance_service, fake_session):
        """Test behavior when club is not found during balance update."""
        fake_session.set_execute_results([FakeResult(scalar_value=None)])

        # Should not raise, just log a warning
        transaction = await finance_service.record_income(
            club_id=999, career_id=1,
            category=IncomeCategory.TRANSFER_SALES,
            amount=1_000_000, description="Sale with missing club",
            season=1, week=5,
        )

        assert transaction.amount == 1_000_000

    @pytest.mark.asyncio
    async def test_multiple_transactions_accumulate(self, finance_service, fake_session, mock_club):
        """Test that multiple transactions correctly accumulate on balance."""
        # First transaction
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])
        await finance_service.record_income(
            club_id=1, career_id=1,
            category=IncomeCategory.TRANSFER_SALES,
            amount=10_000_000, description="Sale 1",
            season=1, week=1,
        )

        # Second transaction
        fake_session.set_execute_results([FakeResult(scalar_value=mock_club)])
        await finance_service.record_expenditure(
            club_id=1, career_id=1,
            category=ExpenditureCategory.WAGES,
            amount=3_000_000, description="Wages",
            season=1, week=1,
        )

        # Balance should be: 50M + 10M - 3M = 57M
        assert mock_club.balance == 57_000_000


class TestProcessWeeklyFinances:
    """Test weekly balance updates (Task 11.2)."""

    @pytest.mark.asyncio
    async def test_process_weekly_finances_with_players_and_staff(
        self, finance_service, fake_session, mock_club
    ):
        """Test processing weekly finances deducts player and staff wages."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=50_000_000),  # club balance query
            FakeResult(data=[MagicMock(total_wages=500_000, player_count=25)]),  # player wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for player wages
            FakeResult(data=[MagicMock(total_wages=80_000, staff_count=5)]),  # staff wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for staff wages
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=5
        )

        assert result["career_id"] == 1
        assert result["club_id"] == 1
        assert result["season"] == 1
        assert result["week"] == 5
        assert result["player_wages_total"] == 500_000
        assert result["player_count"] == 25
        assert result["staff_wages_total"] == 80_000
        assert result["staff_count"] == 5
        assert result["total_deductions"] == 580_000
        assert result["previous_balance"] == 50_000_000
        assert result["new_balance"] == 50_000_000 - 580_000
        assert len(result["transactions"]) == 2

    @pytest.mark.asyncio
    async def test_process_weekly_finances_no_players_no_staff(
        self, finance_service, fake_session
    ):
        """Test processing weekly finances when there are no players or staff."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=10_000_000),  # club balance query
            FakeResult(data=[MagicMock(total_wages=0, player_count=0)]),  # player wages
            FakeResult(data=[MagicMock(total_wages=0, staff_count=0)]),  # staff wages
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=10
        )

        assert result["player_wages_total"] == 0
        assert result["player_count"] == 0
        assert result["staff_wages_total"] == 0
        assert result["staff_count"] == 0
        assert result["total_deductions"] == 0
        assert result["previous_balance"] == 10_000_000
        assert result["new_balance"] == 10_000_000
        assert len(result["transactions"]) == 0

    @pytest.mark.asyncio
    async def test_process_weekly_finances_only_players(
        self, finance_service, fake_session, mock_club
    ):
        """Test processing weekly finances with only player wages (no staff)."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=30_000_000),  # club balance query
            FakeResult(data=[MagicMock(total_wages=750_000, player_count=30)]),  # player wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for player wages
            FakeResult(data=[MagicMock(total_wages=0, staff_count=0)]),  # staff wages
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=2, week=20
        )

        assert result["player_wages_total"] == 750_000
        assert result["player_count"] == 30
        assert result["staff_wages_total"] == 0
        assert result["staff_count"] == 0
        assert result["total_deductions"] == 750_000
        assert len(result["transactions"]) == 1

    @pytest.mark.asyncio
    async def test_process_weekly_finances_only_staff(
        self, finance_service, fake_session, mock_club
    ):
        """Test processing weekly finances with only staff wages (no players)."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=20_000_000),  # club balance query
            FakeResult(data=[MagicMock(total_wages=0, player_count=0)]),  # player wages
            FakeResult(data=[MagicMock(total_wages=120_000, staff_count=8)]),  # staff wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for staff wages
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=15
        )

        assert result["player_wages_total"] == 0
        assert result["player_count"] == 0
        assert result["staff_wages_total"] == 120_000
        assert result["staff_count"] == 8
        assert result["total_deductions"] == 120_000
        assert len(result["transactions"]) == 1

    @pytest.mark.asyncio
    async def test_process_weekly_finances_invalid_week(self, finance_service):
        """Test that invalid week raises ValueError."""
        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.process_weekly_finances(
                career_id=1, club_id=1, season=1, week=0
            )

        with pytest.raises(ValueError, match="Week must be between 1 and 52"):
            await finance_service.process_weekly_finances(
                career_id=1, club_id=1, season=1, week=53
            )

    @pytest.mark.asyncio
    async def test_process_weekly_finances_invalid_season(self, finance_service):
        """Test that invalid season raises ValueError."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.process_weekly_finances(
                career_id=1, club_id=1, season=0, week=1
            )

    @pytest.mark.asyncio
    async def test_process_weekly_finances_balance_can_go_negative(
        self, finance_service, fake_session, mock_club
    ):
        """Test that weekly finances can push balance into negative territory."""
        mock_club.balance = 100_000  # Small balance
        fake_session.set_execute_results([
            FakeResult(scalar_value=100_000),  # club balance query (small)
            FakeResult(data=[MagicMock(total_wages=500_000, player_count=20)]),  # player wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for player wages
            FakeResult(data=[MagicMock(total_wages=80_000, staff_count=5)]),  # staff wages
            FakeResult(scalar_value=mock_club),  # _update_club_balance for staff wages
        ])

        result = await finance_service.process_weekly_finances(
            career_id=1, club_id=1, season=1, week=5
        )

        assert result["previous_balance"] == 100_000
        assert result["new_balance"] == 100_000 - 580_000  # -480_000
        assert result["new_balance"] < 0
