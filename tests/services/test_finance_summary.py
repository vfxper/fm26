"""
Tests for Finance Service - Financial Summary Screen (Task 11.6)

Tests the get_financial_summary() method including:
- Current balance display
- Income breakdown by category (this season)
- Expenditure breakdown by category (this season)
- Net profit/loss for the current season
- Weekly wage bill (players + staff)
- Transfer budget remaining
- Financial health status (healthy, warning, deficit)
- Comparison with previous season (if available)
"""

import pytest
from unittest.mock import MagicMock

from app.models.financial_transaction import (
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


@pytest.fixture
def fake_session():
    """Create a fake async database session."""
    return FakeSession()


@pytest.fixture
def finance_service(fake_session):
    """Create a FinanceService instance with fake session."""
    return FinanceService(fake_session)


def _make_balance_sheet_results(
    income_rows=None,
    expenditure_rows=None,
    club_balance=50_000_000,
    transaction_count=10,
):
    """Helper to create the sequence of FakeResults for get_balance_sheet."""
    return [
        FakeResult(data=income_rows or []),       # income query
        FakeResult(data=expenditure_rows or []),   # expenditure query
        FakeResult(scalar_value=club_balance),     # club balance
        FakeResult(scalar_value=transaction_count),  # transaction count
    ]


class TestGetFinancialSummary:
    """Test the get_financial_summary method."""

    @pytest.mark.asyncio
    async def test_basic_summary_season_1(self, finance_service, fake_session):
        """Test basic financial summary for season 1 (no previous season comparison)."""
        income_rows = [
            MagicMock(category="matchday_revenue", total=5_000_000, count=10),
            MagicMock(category="sponsorship", total=8_000_000, count=1),
        ]
        expenditure_rows = [
            MagicMock(category="wages", total=12_000_000, count=20),
            MagicMock(category="staff_wages", total=2_000_000, count=20),
        ]

        fake_session.set_execute_results([
            # get_balance_sheet for current season
            FakeResult(data=income_rows),           # income query
            FakeResult(data=expenditure_rows),       # expenditure query
            FakeResult(scalar_value=40_000_000),     # club balance
            FakeResult(scalar_value=30),             # transaction count
            # player wages weekly
            FakeResult(scalar_value=600_000),
            # staff wages weekly
            FakeResult(scalar_value=100_000),
            # transfer budget
            FakeResult(scalar_value=15_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        assert summary["club_id"] == 1
        assert summary["career_id"] == 1
        assert summary["season"] == 1
        assert summary["current_balance"] == 40_000_000
        assert summary["total_income"] == 13_000_000
        assert summary["total_expenditure"] == 14_000_000
        assert summary["net_profit_loss"] == -1_000_000
        assert summary["weekly_wage_bill"] == 700_000
        assert summary["player_wages_weekly"] == 600_000
        assert summary["staff_wages_weekly"] == 100_000
        assert summary["transfer_budget_remaining"] == 15_000_000
        assert summary["financial_health"] == "healthy"
        assert summary["previous_season_comparison"] is None

    @pytest.mark.asyncio
    async def test_summary_with_previous_season_comparison(self, finance_service, fake_session):
        """Test financial summary with previous season comparison (season > 1)."""
        # Current season (season 2) balance sheet results
        current_income_rows = [
            MagicMock(category="matchday_revenue", total=6_000_000, count=12),
            MagicMock(category="transfer_sales", total=20_000_000, count=2),
        ]
        current_expenditure_rows = [
            MagicMock(category="wages", total=15_000_000, count=24),
        ]

        # Previous season (season 1) balance sheet results
        prev_income_rows = [
            MagicMock(category="matchday_revenue", total=4_000_000, count=10),
            MagicMock(category="transfer_sales", total=10_000_000, count=1),
        ]
        prev_expenditure_rows = [
            MagicMock(category="wages", total=12_000_000, count=20),
        ]

        fake_session.set_execute_results([
            # get_balance_sheet for current season (season 2)
            FakeResult(data=current_income_rows),
            FakeResult(data=current_expenditure_rows),
            FakeResult(scalar_value=60_000_000),
            FakeResult(scalar_value=38),
            # player wages weekly
            FakeResult(scalar_value=700_000),
            # staff wages weekly
            FakeResult(scalar_value=150_000),
            # transfer budget
            FakeResult(scalar_value=20_000_000),
            # get_balance_sheet for previous season (season 1)
            FakeResult(data=prev_income_rows),
            FakeResult(data=prev_expenditure_rows),
            FakeResult(scalar_value=60_000_000),
            FakeResult(scalar_value=31),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=2
        )

        assert summary["season"] == 2
        assert summary["total_income"] == 26_000_000
        assert summary["total_expenditure"] == 15_000_000
        assert summary["net_profit_loss"] == 11_000_000

        # Check previous season comparison
        comparison = summary["previous_season_comparison"]
        assert comparison is not None
        assert comparison["previous_season"] == 1
        assert comparison["previous_total_income"] == 14_000_000
        assert comparison["previous_total_expenditure"] == 12_000_000
        assert comparison["previous_net_profit_loss"] == 2_000_000
        assert comparison["income_change"] == 12_000_000  # 26M - 14M
        assert comparison["expenditure_change"] == 3_000_000  # 15M - 12M
        assert comparison["net_change"] == 9_000_000  # 11M - 2M
        # Income change percent: (26M - 14M) / 14M * 100 = 85.7%
        assert comparison["income_change_percent"] == pytest.approx(85.7, abs=0.1)
        # Expenditure change percent: (15M - 12M) / 12M * 100 = 25.0%
        assert comparison["expenditure_change_percent"] == 25.0

    @pytest.mark.asyncio
    async def test_summary_no_previous_season_transactions(self, finance_service, fake_session):
        """Test that comparison is None when previous season has no transactions."""
        income_rows = [
            MagicMock(category="sponsorship", total=5_000_000, count=1),
        ]

        fake_session.set_execute_results([
            # get_balance_sheet for current season (season 2)
            FakeResult(data=income_rows),
            FakeResult(data=[]),
            FakeResult(scalar_value=30_000_000),
            FakeResult(scalar_value=1),
            # player wages weekly
            FakeResult(scalar_value=400_000),
            # staff wages weekly
            FakeResult(scalar_value=50_000),
            # transfer budget
            FakeResult(scalar_value=10_000_000),
            # get_balance_sheet for previous season (season 1) - no transactions
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=30_000_000),
            FakeResult(scalar_value=0),  # 0 transactions = no comparison
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=2
        )

        assert summary["previous_season_comparison"] is None

    @pytest.mark.asyncio
    async def test_financial_health_deficit(self, finance_service, fake_session):
        """Test financial health status is 'deficit' when balance is negative."""
        fake_session.set_execute_results([
            # get_balance_sheet for current season
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=-5_000_000),  # Negative balance
            FakeResult(scalar_value=5),
            # player wages weekly
            FakeResult(scalar_value=500_000),
            # staff wages weekly
            FakeResult(scalar_value=100_000),
            # transfer budget
            FakeResult(scalar_value=0),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        assert summary["financial_health"] == "deficit"
        assert "deficit" in summary["health_message"].lower()
        assert summary["current_balance"] == -5_000_000

    @pytest.mark.asyncio
    async def test_financial_health_warning(self, finance_service, fake_session):
        """Test financial health status is 'warning' when balance covers < 8 weeks of wages."""
        # Balance of 3_000_000 with weekly wages of 500_000 = 6 weeks coverage
        fake_session.set_execute_results([
            # get_balance_sheet for current season
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=3_000_000),
            FakeResult(scalar_value=5),
            # player wages weekly
            FakeResult(scalar_value=400_000),
            # staff wages weekly
            FakeResult(scalar_value=100_000),
            # transfer budget
            FakeResult(scalar_value=1_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        assert summary["financial_health"] == "warning"
        assert "caution" in summary["health_message"].lower()

    @pytest.mark.asyncio
    async def test_financial_health_healthy(self, finance_service, fake_session):
        """Test financial health status is 'healthy' when balance is comfortable."""
        # Balance of 50_000_000 with weekly wages of 500_000 = 100 weeks coverage
        fake_session.set_execute_results([
            # get_balance_sheet for current season
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=5),
            # player wages weekly
            FakeResult(scalar_value=400_000),
            # staff wages weekly
            FakeResult(scalar_value=100_000),
            # transfer budget
            FakeResult(scalar_value=20_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        assert summary["financial_health"] == "healthy"
        assert "healthy" in summary["health_message"].lower()

    @pytest.mark.asyncio
    async def test_financial_health_healthy_zero_wages(self, finance_service, fake_session):
        """Test financial health is 'healthy' when there are no wages (no division by zero)."""
        fake_session.set_execute_results([
            # get_balance_sheet for current season
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=10_000_000),
            FakeResult(scalar_value=0),
            # player wages weekly = 0
            FakeResult(scalar_value=0),
            # staff wages weekly = 0
            FakeResult(scalar_value=0),
            # transfer budget
            FakeResult(scalar_value=5_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        assert summary["financial_health"] == "healthy"
        assert summary["weekly_wage_bill"] == 0

    @pytest.mark.asyncio
    async def test_income_breakdown_all_categories(self, finance_service, fake_session):
        """Test that income breakdown includes all categories even if zero."""
        income_rows = [
            MagicMock(category="transfer_sales", total=10_000_000, count=1),
        ]

        fake_session.set_execute_results([
            FakeResult(data=income_rows),
            FakeResult(data=[]),
            FakeResult(scalar_value=30_000_000),
            FakeResult(scalar_value=1),
            FakeResult(scalar_value=300_000),
            FakeResult(scalar_value=50_000),
            FakeResult(scalar_value=10_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        # All income categories should be present
        for cat in IncomeCategory:
            assert cat.value in summary["income_breakdown"]

        # transfer_sales should have data
        assert summary["income_breakdown"]["transfer_sales"]["total"] == 10_000_000
        # Others should be zero
        assert summary["income_breakdown"]["matchday_revenue"]["total"] == 0

    @pytest.mark.asyncio
    async def test_expenditure_breakdown_all_categories(self, finance_service, fake_session):
        """Test that expenditure breakdown includes all categories even if zero."""
        expenditure_rows = [
            MagicMock(category="wages", total=8_000_000, count=16),
            MagicMock(category="transfer_fees", total=25_000_000, count=3),
        ]

        fake_session.set_execute_results([
            FakeResult(data=[]),
            FakeResult(data=expenditure_rows),
            FakeResult(scalar_value=20_000_000),
            FakeResult(scalar_value=19),
            FakeResult(scalar_value=500_000),
            FakeResult(scalar_value=80_000),
            FakeResult(scalar_value=5_000_000),
        ])

        summary = await finance_service.get_financial_summary(
            club_id=1, career_id=1, season=1
        )

        # All expenditure categories should be present
        for cat in ExpenditureCategory:
            assert cat.value in summary["expenditure_breakdown"]

        assert summary["expenditure_breakdown"]["wages"]["total"] == 8_000_000
        assert summary["expenditure_breakdown"]["transfer_fees"]["total"] == 25_000_000
        assert summary["expenditure_breakdown"]["infrastructure"]["total"] == 0

    @pytest.mark.asyncio
    async def test_invalid_season_raises_error(self, finance_service):
        """Test that season 0 or negative raises ValueError."""
        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.get_financial_summary(
                club_id=1, career_id=1, season=0
            )

        with pytest.raises(ValueError, match="Season must be positive"):
            await finance_service.get_financial_summary(
                club_id=1, career_id=1, season=-1
            )

    @pytest.mark.asyncio
    async def test_transfer_budget_zero_when_club_not_found(self, finance_service, fake_session):
        """Test transfer budget defaults to 0 when club not found."""
        fake_session.set_execute_results([
            FakeResult(data=[]),
            FakeResult(data=[]),
            FakeResult(scalar_value=None),  # club balance not found
            FakeResult(scalar_value=0),
            FakeResult(scalar_value=0),
            FakeResult(scalar_value=0),
            FakeResult(scalar_value=None),  # transfer budget not found
        ])

        summary = await finance_service.get_financial_summary(
            club_id=999, career_id=1, season=1
        )

        assert summary["transfer_budget_remaining"] == 0
        assert summary["current_balance"] == 0


class TestCalculateFinancialHealth:
    """Test the _calculate_financial_health helper method."""

    def test_deficit_status(self):
        """Test deficit status when balance is negative."""
        service = FinanceService.__new__(FinanceService)
        status, message = service._calculate_financial_health(
            current_balance=-1_000_000,
            weekly_wage_bill=500_000,
        )
        assert status == "deficit"
        assert "deficit" in message.lower()

    def test_warning_status(self):
        """Test warning status when balance covers fewer than 8 weeks of wages."""
        service = FinanceService.__new__(FinanceService)
        # 3_500_000 / 500_000 = 7 weeks (< 8 threshold)
        status, message = service._calculate_financial_health(
            current_balance=3_500_000,
            weekly_wage_bill=500_000,
        )
        assert status == "warning"
        assert "caution" in message.lower()

    def test_healthy_status(self):
        """Test healthy status when balance comfortably covers wages."""
        service = FinanceService.__new__(FinanceService)
        # 10_000_000 / 500_000 = 20 weeks (>= 8 threshold)
        status, message = service._calculate_financial_health(
            current_balance=10_000_000,
            weekly_wage_bill=500_000,
        )
        assert status == "healthy"
        assert "healthy" in message.lower()

    def test_healthy_status_zero_wages(self):
        """Test healthy status when there are no wages (avoids division by zero)."""
        service = FinanceService.__new__(FinanceService)
        status, message = service._calculate_financial_health(
            current_balance=1_000_000,
            weekly_wage_bill=0,
        )
        assert status == "healthy"

    def test_warning_boundary_exactly_8_weeks(self):
        """Test that exactly 8 weeks of coverage is healthy (not warning)."""
        service = FinanceService.__new__(FinanceService)
        # 4_000_000 / 500_000 = 8 weeks (>= 8 threshold, so healthy)
        status, message = service._calculate_financial_health(
            current_balance=4_000_000,
            weekly_wage_bill=500_000,
        )
        assert status == "healthy"

    def test_warning_boundary_7_weeks(self):
        """Test that 7 weeks of coverage triggers warning."""
        service = FinanceService.__new__(FinanceService)
        # 3_499_999 / 500_000 = 6 weeks (integer division), < 8
        status, message = service._calculate_financial_health(
            current_balance=3_499_999,
            weekly_wage_bill=500_000,
        )
        assert status == "warning"

    def test_deficit_at_exactly_zero(self):
        """Test that balance of exactly 0 is not deficit (threshold is < 0)."""
        service = FinanceService.__new__(FinanceService)
        status, message = service._calculate_financial_health(
            current_balance=0,
            weekly_wage_bill=500_000,
        )
        # Balance is 0, wages are 500k, so 0 weeks coverage < 8 = warning
        assert status == "warning"
