"""
Tests for Finance Service - Negative Balance Restrictions (Task 11.3)

Tests the negative balance restriction methods:
- can_afford(club_id, amount) - checks if club can afford an expenditure
- is_in_deficit(club_id) - checks if club balance is negative
- get_financial_restrictions(club_id) - returns list of restricted actions
- validate_expenditure(club_id, amount, category) - validates if expenditure is allowed

Restriction rules:
1. Cannot make transfer bids (buying players) when in deficit
2. Cannot upgrade infrastructure when in deficit
3. Cannot hire new staff when in deficit
4. Wages still get paid (can go further negative)
5. Can still sell players (to recover balance)
"""

import pytest

from app.models.financial_transaction import (
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


class TestCanAfford:
    """Test can_afford method - checks if club can afford an expenditure."""

    @pytest.mark.asyncio
    async def test_can_afford_with_sufficient_balance(self, finance_service, fake_session):
        """Club with balance of 50M can afford 10M expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=50_000_000),
        ])

        result = await finance_service.can_afford(club_id=1, amount=10_000_000)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_afford_with_insufficient_balance(self, finance_service, fake_session):
        """Club with balance of 5M cannot afford 10M expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=5_000_000),
        ])

        result = await finance_service.can_afford(club_id=1, amount=10_000_000)
        assert result is False

    @pytest.mark.asyncio
    async def test_can_afford_exact_balance(self, finance_service, fake_session):
        """Club with balance exactly equal to amount can afford it."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=10_000_000),
        ])

        result = await finance_service.can_afford(club_id=1, amount=10_000_000)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_afford_with_negative_balance(self, finance_service, fake_session):
        """Club with negative balance cannot afford any expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-5_000_000),
        ])

        result = await finance_service.can_afford(club_id=1, amount=1_000_000)
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_afford_with_zero_balance(self, finance_service, fake_session):
        """Club with zero balance cannot afford any positive expenditure."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=0),
        ])

        result = await finance_service.can_afford(club_id=1, amount=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_can_afford_club_not_found(self, finance_service, fake_session):
        """Returns False when club is not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.can_afford(club_id=999, amount=1_000_000)
        assert result is False

    @pytest.mark.asyncio
    async def test_can_afford_rejects_zero_amount(self, finance_service):
        """Raises ValueError for zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await finance_service.can_afford(club_id=1, amount=0)

    @pytest.mark.asyncio
    async def test_can_afford_rejects_negative_amount(self, finance_service):
        """Raises ValueError for negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await finance_service.can_afford(club_id=1, amount=-100)


class TestIsInDeficit:
    """Test is_in_deficit method - checks if club balance is negative."""

    @pytest.mark.asyncio
    async def test_not_in_deficit_positive_balance(self, finance_service, fake_session):
        """Club with positive balance is not in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=50_000_000),
        ])

        result = await finance_service.is_in_deficit(club_id=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_not_in_deficit_zero_balance(self, finance_service, fake_session):
        """Club with zero balance is not in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=0),
        ])

        result = await finance_service.is_in_deficit(club_id=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_in_deficit_negative_balance(self, finance_service, fake_session):
        """Club with negative balance is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-1_000_000),
        ])

        result = await finance_service.is_in_deficit(club_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_in_deficit_large_negative_balance(self, finance_service, fake_session):
        """Club with large negative balance is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-100_000_000),
        ])

        result = await finance_service.is_in_deficit(club_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_in_deficit_minus_one(self, finance_service, fake_session):
        """Club with balance of -1 is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-1),
        ])

        result = await finance_service.is_in_deficit(club_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_in_deficit_club_not_found(self, finance_service, fake_session):
        """Returns False when club is not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.is_in_deficit(club_id=999)
        assert result is False


class TestGetFinancialRestrictions:
    """Test get_financial_restrictions method - returns list of restricted actions."""

    @pytest.mark.asyncio
    async def test_no_restrictions_positive_balance(self, finance_service, fake_session):
        """Club with positive balance has no restrictions."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=50_000_000),
        ])

        result = await finance_service.get_financial_restrictions(club_id=1)

        assert result["club_id"] == 1
        assert result["is_in_deficit"] is False
        assert result["current_balance"] == 50_000_000
        assert result["restricted_actions"] == []
        assert "transfer_bids" in result["allowed_actions"]
        assert "infrastructure_upgrades" in result["allowed_actions"]
        assert "staff_hiring" in result["allowed_actions"]
        assert "player_wages" in result["allowed_actions"]
        assert "player_sales" in result["allowed_actions"]

    @pytest.mark.asyncio
    async def test_restrictions_when_in_deficit(self, finance_service, fake_session):
        """Club in deficit has transfer, infrastructure, and staff restrictions."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-5_000_000),
        ])

        result = await finance_service.get_financial_restrictions(club_id=1)

        assert result["club_id"] == 1
        assert result["is_in_deficit"] is True
        assert result["current_balance"] == -5_000_000
        assert "transfer_bids" in result["restricted_actions"]
        assert "infrastructure_upgrades" in result["restricted_actions"]
        assert "staff_hiring" in result["restricted_actions"]
        # Wages and sales are still allowed
        assert "player_wages" in result["allowed_actions"]
        assert "staff_wages" in result["allowed_actions"]
        assert "player_sales" in result["allowed_actions"]

    @pytest.mark.asyncio
    async def test_no_restrictions_zero_balance(self, finance_service, fake_session):
        """Club with zero balance has no restrictions (not in deficit)."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=0),
        ])

        result = await finance_service.get_financial_restrictions(club_id=1)

        assert result["is_in_deficit"] is False
        assert result["restricted_actions"] == []

    @pytest.mark.asyncio
    async def test_restrictions_club_not_found(self, finance_service, fake_session):
        """Returns empty restrictions when club not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.get_financial_restrictions(club_id=999)

        assert result["club_id"] == 999
        assert result["is_in_deficit"] is False
        assert result["restricted_actions"] == []
        assert result["message"] == "Club not found"

    @pytest.mark.asyncio
    async def test_restrictions_message_in_deficit(self, finance_service, fake_session):
        """Message explains the deficit situation."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-2_000_000),
        ])

        result = await finance_service.get_financial_restrictions(club_id=1)

        assert "deficit" in result["message"].lower()
        assert "restricted" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_restrictions_message_healthy(self, finance_service, fake_session):
        """Message confirms healthy finances."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=10_000_000),
        ])

        result = await finance_service.get_financial_restrictions(club_id=1)

        assert "healthy" in result["message"].lower()
        assert "no restrictions" in result["message"].lower()


class TestValidateExpenditure:
    """Test validate_expenditure method - validates if expenditure is allowed."""

    @pytest.mark.asyncio
    async def test_transfer_allowed_positive_balance(self, finance_service, fake_session):
        """Transfer fee allowed when club has sufficient balance."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=50_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=10_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert result["allowed"] is True
        assert result["current_balance"] == 50_000_000
        assert result["balance_after"] == 40_000_000

    @pytest.mark.asyncio
    async def test_transfer_blocked_in_deficit(self, finance_service, fake_session):
        """Transfer fee blocked when club is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-5_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=10_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert result["allowed"] is False
        assert "deficit" in result["reason"].lower()
        assert result["balance_after"] is None

    @pytest.mark.asyncio
    async def test_infrastructure_blocked_in_deficit(self, finance_service, fake_session):
        """Infrastructure expenditure blocked when club is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-1_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=5_000_000,
            category=ExpenditureCategory.INFRASTRUCTURE,
        )

        assert result["allowed"] is False
        assert "deficit" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_staff_wages_blocked_in_deficit_for_new_hires(self, finance_service, fake_session):
        """Staff wages (new hiring) blocked when club is in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-500_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=50_000,
            category=ExpenditureCategory.STAFF_WAGES,
        )

        assert result["allowed"] is False
        assert "deficit" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_wages_always_allowed_in_deficit(self, finance_service, fake_session):
        """Player wages are always allowed even when in deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-10_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=500_000,
            category=ExpenditureCategory.WAGES,
        )

        assert result["allowed"] is True
        assert result["balance_after"] == -10_500_000
        assert "always allowed" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_wages_allowed_with_zero_balance(self, finance_service, fake_session):
        """Player wages are allowed even with zero balance (will go negative)."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=0),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=500_000,
            category=ExpenditureCategory.WAGES,
        )

        assert result["allowed"] is True
        assert result["balance_after"] == -500_000

    @pytest.mark.asyncio
    async def test_other_expenditure_always_allowed(self, finance_service, fake_session):
        """Other expenditure category is unrestricted."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=-3_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=100_000,
            category=ExpenditureCategory.OTHER_EXPENDITURE,
        )

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_transfer_blocked_would_exceed_balance(self, finance_service, fake_session):
        """Transfer blocked when it would push club into deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=5_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=10_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert result["allowed"] is False
        assert "exceed" in result["reason"].lower()
        assert result["balance_after"] is None

    @pytest.mark.asyncio
    async def test_infrastructure_blocked_would_exceed_balance(self, finance_service, fake_session):
        """Infrastructure blocked when it would push club into deficit."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=3_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=5_000_000,
            category=ExpenditureCategory.INFRASTRUCTURE,
        )

        assert result["allowed"] is False
        assert "exceed" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_expenditure_club_not_found(self, finance_service, fake_session):
        """Returns not allowed when club is not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),
        ])

        result = await finance_service.validate_expenditure(
            club_id=999,
            amount=1_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert result["allowed"] is False
        assert "not found" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_expenditure_rejects_zero_amount(self, finance_service):
        """Raises ValueError for zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await finance_service.validate_expenditure(
                club_id=1,
                amount=0,
                category=ExpenditureCategory.TRANSFER_FEES,
            )

    @pytest.mark.asyncio
    async def test_validate_expenditure_rejects_negative_amount(self, finance_service):
        """Raises ValueError for negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await finance_service.validate_expenditure(
                club_id=1,
                amount=-500,
                category=ExpenditureCategory.WAGES,
            )

    @pytest.mark.asyncio
    async def test_transfer_allowed_exact_balance(self, finance_service, fake_session):
        """Transfer allowed when amount exactly equals balance."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=10_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=10_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert result["allowed"] is True
        assert result["balance_after"] == 0

    @pytest.mark.asyncio
    async def test_result_contains_all_fields(self, finance_service, fake_session):
        """Validate that result dict contains all expected fields."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=20_000_000),
        ])

        result = await finance_service.validate_expenditure(
            club_id=1,
            amount=5_000_000,
            category=ExpenditureCategory.TRANSFER_FEES,
        )

        assert "allowed" in result
        assert "reason" in result
        assert "club_id" in result
        assert "amount" in result
        assert "category" in result
        assert "current_balance" in result
        assert "balance_after" in result
        assert result["club_id"] == 1
        assert result["amount"] == 5_000_000
        assert result["category"] == "transfer_fees"


class TestRestrictionCategories:
    """Test that the correct categories are restricted/unrestricted."""

    def test_restricted_categories_defined(self):
        """Verify restricted categories include transfer, infrastructure, staff."""
        assert ExpenditureCategory.TRANSFER_FEES in FinanceService.RESTRICTED_CATEGORIES
        assert ExpenditureCategory.INFRASTRUCTURE in FinanceService.RESTRICTED_CATEGORIES
        assert ExpenditureCategory.STAFF_WAGES in FinanceService.RESTRICTED_CATEGORIES

    def test_unrestricted_categories_defined(self):
        """Verify unrestricted categories include wages and other."""
        assert ExpenditureCategory.WAGES in FinanceService.UNRESTRICTED_CATEGORIES
        assert ExpenditureCategory.OTHER_EXPENDITURE in FinanceService.UNRESTRICTED_CATEGORIES

    def test_all_categories_classified(self):
        """Every expenditure category should be in either restricted or unrestricted."""
        all_classified = (
            set(FinanceService.RESTRICTED_CATEGORIES)
            | set(FinanceService.UNRESTRICTED_CATEGORIES)
        )
        for cat in ExpenditureCategory:
            assert cat in all_classified, f"Category {cat} is not classified"
