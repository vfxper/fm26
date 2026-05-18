"""
Tests for Finance Service - 5-Season Financial History Tracking (Task 11.10)

Tests the get_financial_history method including:
- Retrieving per-season financial data for the last N seasons
- Trend analysis (improving/declining/stable)
- Category breakdowns per season
- Edge cases (1 season, no data, max seasons)
- Input validation
"""

import pytest
from unittest.mock import MagicMock

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


def make_season_balance_sheet_results(
    income_rows, expenditure_rows, club_balance, transaction_count
):
    """Helper to create the sequence of FakeResults for a get_balance_sheet call."""
    return [
        FakeResult(data=income_rows),
        FakeResult(data=expenditure_rows),
        FakeResult(scalar_value=club_balance),
        FakeResult(scalar_value=transaction_count),
    ]


class FakeDeficitRecord:
    """Fake SeasonDeficitRecord for testing."""

    def __init__(self, season, balance_at_season_end):
        self.season = season
        self.balance_at_season_end = balance_at_season_end
        self.ended_in_deficit = balance_at_season_end < 0


class TestGetFinancialHistoryValidation:
    """Test input validation for get_financial_history."""

    @pytest.mark.asyncio
    async def test_rejects_zero_num_seasons(self, finance_service):
        """Test that num_seasons=0 is rejected."""
        with pytest.raises(ValueError, match="num_seasons must be between 1 and 10"):
            await finance_service.get_financial_history(
                club_id=1, career_id=1, num_seasons=0
            )

    @pytest.mark.asyncio
    async def test_rejects_negative_num_seasons(self, finance_service):
        """Test that negative num_seasons is rejected."""
        with pytest.raises(ValueError, match="num_seasons must be between 1 and 10"):
            await finance_service.get_financial_history(
                club_id=1, career_id=1, num_seasons=-1
            )

    @pytest.mark.asyncio
    async def test_rejects_num_seasons_over_10(self, finance_service):
        """Test that num_seasons > 10 is rejected."""
        with pytest.raises(ValueError, match="num_seasons must be between 1 and 10"):
            await finance_service.get_financial_history(
                club_id=1, career_id=1, num_seasons=11
            )


class TestGetFinancialHistoryNoData:
    """Test get_financial_history when no data is available."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_transactions(self, finance_service, fake_session):
        """Test that empty history is returned when no transactions exist."""
        # distinct seasons query returns empty
        fake_session.set_execute_results([
            FakeResult(data=[]),
        ])

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1, num_seasons=5
        )

        assert result["club_id"] == 1
        assert result["career_id"] == 1
        assert result["num_seasons_requested"] == 5
        assert result["num_seasons_available"] == 0
        assert result["seasons"] == []
        assert result["trend_analysis"]["overall_trend"] == "stable"
        assert result["trend_analysis"]["description"] == "No financial history available."
        assert result["summary"]["total_income_all_seasons"] == 0
        assert result["summary"]["total_expenditure_all_seasons"] == 0


class TestGetFinancialHistoryOneSeason:
    """Test get_financial_history with 1 season of data."""

    @pytest.mark.asyncio
    async def test_single_season_data(self, finance_service, fake_session):
        """Test financial history with only 1 season of data."""
        income_rows = [
            MagicMock(category="matchday_revenue", total=5_000_000, count=20),
            MagicMock(category="sponsorship", total=10_000_000, count=1),
        ]
        expenditure_rows = [
            MagicMock(category="wages", total=12_000_000, count=40),
            MagicMock(category="staff_wages", total=2_000_000, count=40),
        ]

        fake_session.set_execute_results([
            # distinct seasons query
            FakeResult(data=[(1,)]),
            # get_balance_sheet for season 1
            FakeResult(data=income_rows),
            FakeResult(data=expenditure_rows),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=101),
            # deficit record query for season 1
            FakeResult(scalar_value=FakeDeficitRecord(season=1, balance_at_season_end=45_000_000)),
        ])

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1, num_seasons=5
        )

        assert result["num_seasons_available"] == 1
        assert len(result["seasons"]) == 1

        season_1 = result["seasons"][0]
        assert season_1["season"] == 1
        assert season_1["total_income"] == 15_000_000
        assert season_1["total_expenditure"] == 14_000_000
        assert season_1["net_profit_loss"] == 1_000_000
        assert season_1["balance_at_season_end"] == 45_000_000
        assert season_1["transaction_count"] == 101

        # Trend should be stable with only 1 season
        assert result["trend_analysis"]["overall_trend"] == "stable"
        assert "Insufficient data" in result["trend_analysis"]["description"]

        # Summary
        assert result["summary"]["total_income_all_seasons"] == 15_000_000
        assert result["summary"]["total_expenditure_all_seasons"] == 14_000_000
        assert result["summary"]["average_season_income"] == 15_000_000


class TestGetFinancialHistoryMultipleSeasons:
    """Test get_financial_history with multiple seasons of data."""

    @pytest.mark.asyncio
    async def test_three_seasons_improving_trend(self, finance_service, fake_session):
        """Test financial history with 3 seasons showing improving trend."""
        # Season 1: income 10M, expenditure 12M (loss)
        s1_income = [MagicMock(category="matchday_revenue", total=10_000_000, count=20)]
        s1_expenditure = [MagicMock(category="wages", total=12_000_000, count=40)]

        # Season 2: income 15M, expenditure 12M (profit)
        s2_income = [MagicMock(category="matchday_revenue", total=15_000_000, count=20)]
        s2_expenditure = [MagicMock(category="wages", total=12_000_000, count=40)]

        # Season 3: income 20M, expenditure 12M (bigger profit)
        s3_income = [MagicMock(category="matchday_revenue", total=20_000_000, count=20)]
        s3_expenditure = [MagicMock(category="wages", total=12_000_000, count=40)]

        fake_session.set_execute_results([
            # distinct seasons query
            FakeResult(data=[(3,), (2,), (1,)]),
            # get_balance_sheet for season 1
            FakeResult(data=s1_income),
            FakeResult(data=s1_expenditure),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=60),
            # deficit record for season 1
            FakeResult(scalar_value=FakeDeficitRecord(season=1, balance_at_season_end=38_000_000)),
            # get_balance_sheet for season 2
            FakeResult(data=s2_income),
            FakeResult(data=s2_expenditure),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=60),
            # deficit record for season 2
            FakeResult(scalar_value=FakeDeficitRecord(season=2, balance_at_season_end=41_000_000)),
            # get_balance_sheet for season 3
            FakeResult(data=s3_income),
            FakeResult(data=s3_expenditure),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=60),
            # deficit record for season 3
            FakeResult(scalar_value=FakeDeficitRecord(season=3, balance_at_season_end=49_000_000)),
        ])

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1, num_seasons=5
        )

        assert result["num_seasons_available"] == 3
        assert len(result["seasons"]) == 3

        # Seasons should be in descending order (most recent first)
        assert result["seasons"][0]["season"] == 3
        assert result["seasons"][1]["season"] == 2
        assert result["seasons"][2]["season"] == 1

        # Season 3 data
        assert result["seasons"][0]["total_income"] == 20_000_000
        assert result["seasons"][0]["net_profit_loss"] == 8_000_000

        # Trend should be improving (net profit went from 3M to 8M)
        assert result["trend_analysis"]["overall_trend"] == "improving"
        assert result["trend_analysis"]["income_trend"] == "improving"

        # Summary
        assert result["summary"]["total_income_all_seasons"] == 45_000_000
        assert result["summary"]["total_expenditure_all_seasons"] == 36_000_000
        assert result["summary"]["total_net_profit_loss"] == 9_000_000

    @pytest.mark.asyncio
    async def test_five_seasons_declining_trend(self, finance_service, fake_session):
        """Test financial history with 5 seasons showing declining trend."""
        # Build results for 5 seasons with declining income
        execute_results = [
            # distinct seasons query
            FakeResult(data=[(5,), (4,), (3,), (2,), (1,)]),
        ]

        incomes = [20_000_000, 18_000_000, 15_000_000, 12_000_000, 8_000_000]
        expenditure = 14_000_000  # constant expenditure

        for i, season_num in enumerate([1, 2, 3, 4, 5]):
            income_amount = incomes[i]
            s_income = [MagicMock(category="matchday_revenue", total=income_amount, count=20)]
            s_expenditure = [MagicMock(category="wages", total=expenditure, count=40)]
            balance_end = 50_000_000 + (income_amount - expenditure) * (i + 1)

            execute_results.extend([
                FakeResult(data=s_income),
                FakeResult(data=s_expenditure),
                FakeResult(scalar_value=50_000_000),
                FakeResult(scalar_value=60),
                FakeResult(scalar_value=FakeDeficitRecord(
                    season=season_num, balance_at_season_end=balance_end
                )),
            ])

        fake_session.set_execute_results(execute_results)

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1, num_seasons=5
        )

        assert result["num_seasons_available"] == 5
        assert len(result["seasons"]) == 5

        # Most recent season (5) has lowest income
        assert result["seasons"][0]["season"] == 5
        assert result["seasons"][0]["total_income"] == 8_000_000

        # Trend should be declining (income dropped from 12M to 8M between seasons 4 and 5)
        assert result["trend_analysis"]["overall_trend"] == "declining"
        assert result["trend_analysis"]["income_trend"] == "declining"


class TestGetFinancialHistoryNoDeficitRecord:
    """Test get_financial_history when no deficit record exists for a season."""

    @pytest.mark.asyncio
    async def test_balance_at_season_end_is_none_without_deficit_record(
        self, finance_service, fake_session
    ):
        """Test that balance_at_season_end is None when no deficit record exists."""
        income_rows = [MagicMock(category="matchday_revenue", total=5_000_000, count=10)]
        expenditure_rows = [MagicMock(category="wages", total=3_000_000, count=20)]

        fake_session.set_execute_results([
            # distinct seasons query
            FakeResult(data=[(1,)]),
            # get_balance_sheet for season 1
            FakeResult(data=income_rows),
            FakeResult(data=expenditure_rows),
            FakeResult(scalar_value=50_000_000),
            FakeResult(scalar_value=30),
            # deficit record query returns None
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1, num_seasons=5
        )

        assert result["num_seasons_available"] == 1
        assert result["seasons"][0]["balance_at_season_end"] is None


class TestTrendAnalysisHelpers:
    """Test the trend analysis helper methods directly."""

    def test_determine_trend_improving(self, finance_service):
        """Test that a significant increase is detected as improving."""
        result = finance_service._determine_trend(10_000_000, 12_000_000)
        assert result == "improving"

    def test_determine_trend_declining(self, finance_service):
        """Test that a significant decrease is detected as declining."""
        result = finance_service._determine_trend(10_000_000, 8_000_000)
        assert result == "declining"

    def test_determine_trend_stable(self, finance_service):
        """Test that a small change is detected as stable."""
        result = finance_service._determine_trend(10_000_000, 10_200_000)
        assert result == "stable"

    def test_determine_trend_inverted_for_expenditure(self, finance_service):
        """Test that inverted trend works for expenditure (decrease = improving)."""
        # Expenditure decreased - that's improving
        result = finance_service._determine_trend(10_000_000, 8_000_000, invert=True)
        assert result == "improving"

        # Expenditure increased - that's declining
        result = finance_service._determine_trend(10_000_000, 12_000_000, invert=True)
        assert result == "declining"

    def test_determine_trend_both_zero(self, finance_service):
        """Test that both values being zero returns stable."""
        result = finance_service._determine_trend(0, 0)
        assert result == "stable"

    def test_determine_trend_from_zero_to_positive(self, finance_service):
        """Test trend from zero to positive value."""
        result = finance_service._determine_trend(0, 5_000_000)
        assert result == "improving"

    def test_determine_trend_from_zero_to_negative(self, finance_service):
        """Test trend from zero to negative value."""
        result = finance_service._determine_trend(0, -5_000_000)
        assert result == "declining"

    def test_calculate_trend_analysis_insufficient_data(self, finance_service):
        """Test trend analysis with only 1 season (insufficient)."""
        season_data = [
            {"total_income": 10_000_000, "total_expenditure": 8_000_000, "net_profit_loss": 2_000_000}
        ]
        result = finance_service._calculate_trend_analysis(season_data)
        assert result["overall_trend"] == "stable"
        assert "Insufficient data" in result["description"]

    def test_calculate_trend_analysis_improving(self, finance_service):
        """Test trend analysis detecting improvement."""
        season_data = [
            {"total_income": 10_000_000, "total_expenditure": 12_000_000, "net_profit_loss": -2_000_000},
            {"total_income": 15_000_000, "total_expenditure": 10_000_000, "net_profit_loss": 5_000_000},
        ]
        result = finance_service._calculate_trend_analysis(season_data)
        assert result["overall_trend"] == "improving"
        assert result["income_trend"] == "improving"
        assert "improving" in result["description"]

    def test_calculate_trend_analysis_declining(self, finance_service):
        """Test trend analysis detecting decline."""
        season_data = [
            {"total_income": 15_000_000, "total_expenditure": 10_000_000, "net_profit_loss": 5_000_000},
            {"total_income": 10_000_000, "total_expenditure": 12_000_000, "net_profit_loss": -2_000_000},
        ]
        result = finance_service._calculate_trend_analysis(season_data)
        assert result["overall_trend"] == "declining"
        assert result["income_trend"] == "declining"
        assert "declining" in result["description"]


class TestGetFinancialHistoryDefaultNumSeasons:
    """Test that the default num_seasons parameter works correctly."""

    @pytest.mark.asyncio
    async def test_default_num_seasons_is_5(self, finance_service, fake_session):
        """Test that default num_seasons is 5."""
        fake_session.set_execute_results([
            FakeResult(data=[]),
        ])

        result = await finance_service.get_financial_history(
            club_id=1, career_id=1
        )

        assert result["num_seasons_requested"] == 5
