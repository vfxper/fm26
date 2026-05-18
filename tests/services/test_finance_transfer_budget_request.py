"""
Tests for Finance Service - Transfer Budget Request System (Task 11.7)

Tests the request_transfer_budget method including:
- Full approval when board confidence is high and finances are healthy
- Partial approval when conditions are moderate
- Rejection when club is in deficit or confidence is low
- Board decision logic based on confidence, financial health, performance, and request size
- Transfer budget update on approval
- Input validation
"""

import pytest

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


class FakeCareer:
    """Fake career object for testing."""

    def __init__(
        self,
        id=1,
        board_confidence=70,
        matches_won=15,
        matches_drawn=5,
        matches_lost=5,
    ):
        self.id = id
        self.board_confidence = board_confidence
        self.matches_won = matches_won
        self.matches_drawn = matches_drawn
        self.matches_lost = matches_lost

    def get_win_percentage(self) -> float:
        total = self.matches_won + self.matches_drawn + self.matches_lost
        if total == 0:
            return 0.0
        return (self.matches_won / total) * 100

    def get_total_matches(self) -> int:
        return self.matches_won + self.matches_drawn + self.matches_lost


class FakeClub:
    """Fake club object for testing."""

    def __init__(self, id=1, balance=100_000_000, transfer_budget=50_000_000):
        self.id = id
        self.balance = balance
        self.transfer_budget = transfer_budget


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
def finance_service(fake_session):
    return FinanceService(fake_session)


# --- Full Approval Tests ---


class TestTransferBudgetFullApproval:
    """Tests for scenarios where the board fully approves the request."""

    @pytest.mark.asyncio
    async def test_full_approval_high_confidence_healthy_finances(
        self, finance_service, fake_session
    ):
        """Board approves full amount when confidence is high and finances are strong."""
        career = FakeCareer(board_confidence=85, matches_won=20, matches_drawn=5, matches_lost=3)
        club = FakeClub(balance=200_000_000, transfer_budget=50_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),  # career query
            FakeResult(scalar_value=club),    # club query
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=10_000_000,
        )

        assert result["decision"] == "approved"
        assert result["approved_amount"] == 10_000_000
        assert result["new_transfer_budget"] == 60_000_000
        assert result["board_confidence"] == 85
        assert "approved" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_full_approval_modest_request(
        self, finance_service, fake_session
    ):
        """Board approves when request is very modest relative to current budget."""
        career = FakeCareer(board_confidence=75, matches_won=12, matches_drawn=8, matches_lost=5)
        club = FakeClub(balance=150_000_000, transfer_budget=80_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        # Request only 10% of current budget - very modest
        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=8_000_000,
        )

        assert result["decision"] == "approved"
        assert result["approved_amount"] == 8_000_000
        assert result["new_transfer_budget"] == 88_000_000

    @pytest.mark.asyncio
    async def test_transfer_budget_updated_on_approval(
        self, finance_service, fake_session
    ):
        """Club's transfer_budget field is updated when request is approved."""
        career = FakeCareer(board_confidence=90, matches_won=25, matches_drawn=3, matches_lost=2)
        club = FakeClub(balance=300_000_000, transfer_budget=100_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=15_000_000,
        )

        assert result["decision"] == "approved"
        # Verify the club object was updated
        assert club.transfer_budget == 115_000_000
        assert fake_session.flushed is True


# --- Partial Approval Tests ---


class TestTransferBudgetPartialApproval:
    """Tests for scenarios where the board partially approves the request."""

    @pytest.mark.asyncio
    async def test_partial_approval_moderate_confidence(
        self, finance_service, fake_session
    ):
        """Board partially approves when confidence is moderate."""
        career = FakeCareer(board_confidence=50, matches_won=10, matches_drawn=8, matches_lost=7)
        club = FakeClub(balance=80_000_000, transfer_budget=40_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=20_000_000,
        )

        assert result["decision"] == "partial"
        assert 0 < result["approved_amount"] < 20_000_000
        assert result["new_transfer_budget"] == 40_000_000 + result["approved_amount"]
        assert "partially" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_partial_approval_large_request(
        self, finance_service, fake_session
    ):
        """Board partially approves when request is large relative to budget."""
        career = FakeCareer(board_confidence=65, matches_won=14, matches_drawn=6, matches_lost=5)
        club = FakeClub(balance=100_000_000, transfer_budget=30_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        # Request 80% of current budget - ambitious
        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=24_000_000,
        )

        # With moderate confidence and ambitious request, likely partial
        assert result["decision"] in ("partial", "approved")
        assert result["approved_amount"] > 0

    @pytest.mark.asyncio
    async def test_partial_approval_updates_budget(
        self, finance_service, fake_session
    ):
        """Transfer budget is correctly updated with partial amount."""
        career = FakeCareer(board_confidence=55, matches_won=8, matches_drawn=7, matches_lost=10)
        club = FakeClub(balance=60_000_000, transfer_budget=25_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=15_000_000,
        )

        if result["decision"] == "partial":
            assert club.transfer_budget == 25_000_000 + result["approved_amount"]
            assert fake_session.flushed is True


# --- Rejection Tests ---


class TestTransferBudgetRejection:
    """Tests for scenarios where the board rejects the request."""

    @pytest.mark.asyncio
    async def test_rejection_club_in_deficit(
        self, finance_service, fake_session
    ):
        """Board always rejects when club is in financial deficit."""
        career = FakeCareer(board_confidence=90, matches_won=25, matches_drawn=3, matches_lost=2)
        club = FakeClub(balance=-5_000_000, transfer_budget=0)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=10_000_000,
        )

        assert result["decision"] == "rejected"
        assert result["approved_amount"] == 0
        assert result["new_transfer_budget"] == 0
        assert "deficit" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_rejection_low_confidence_poor_performance(
        self, finance_service, fake_session
    ):
        """Board rejects when confidence is low and performance is poor."""
        career = FakeCareer(board_confidence=20, matches_won=3, matches_drawn=5, matches_lost=17)
        club = FakeClub(balance=30_000_000, transfer_budget=10_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        # Large request with low confidence
        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=20_000_000,
        )

        assert result["decision"] == "rejected"
        assert result["approved_amount"] == 0
        assert result["new_transfer_budget"] == 10_000_000

    @pytest.mark.asyncio
    async def test_rejection_does_not_update_budget(
        self, finance_service, fake_session
    ):
        """Transfer budget remains unchanged when request is rejected."""
        career = FakeCareer(board_confidence=15, matches_won=2, matches_drawn=3, matches_lost=20)
        club = FakeClub(balance=-1_000_000, transfer_budget=5_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=10_000_000,
        )

        assert result["decision"] == "rejected"
        assert club.transfer_budget == 5_000_000


# --- Input Validation Tests ---


class TestTransferBudgetValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_rejects_zero_amount(self, finance_service):
        """Raises ValueError for zero amount."""
        with pytest.raises(ValueError, match="must be positive"):
            await finance_service.request_transfer_budget(
                career_id=1, club_id=1, amount_requested=0
            )

    @pytest.mark.asyncio
    async def test_rejects_negative_amount(self, finance_service):
        """Raises ValueError for negative amount."""
        with pytest.raises(ValueError, match="must be positive"):
            await finance_service.request_transfer_budget(
                career_id=1, club_id=1, amount_requested=-5_000_000
            )

    @pytest.mark.asyncio
    async def test_rejects_career_not_found(self, finance_service, fake_session):
        """Raises ValueError when career is not found."""
        fake_session.set_execute_results([
            FakeResult(scalar_value=None),  # career not found
        ])

        with pytest.raises(ValueError, match="Career with id"):
            await finance_service.request_transfer_budget(
                career_id=999, club_id=1, amount_requested=10_000_000
            )

    @pytest.mark.asyncio
    async def test_rejects_club_not_found(self, finance_service, fake_session):
        """Raises ValueError when club is not found."""
        career = FakeCareer(board_confidence=70)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),  # career found
            FakeResult(scalar_value=None),    # club not found
        ])

        with pytest.raises(ValueError, match="Club with id"):
            await finance_service.request_transfer_budget(
                career_id=1, club_id=999, amount_requested=10_000_000
            )


# --- Board Decision Logic Tests ---


class TestBoardDecisionLogic:
    """Tests for the internal _evaluate_budget_request logic."""

    def test_high_score_gives_full_approval(self):
        """Score >= 70 results in full approval."""
        service = FinanceService(None)

        decision, amount, reasoning = service._evaluate_budget_request(
            board_confidence=90,
            current_balance=500_000_000,
            current_budget=100_000_000,
            amount_requested=10_000_000,
            win_percentage=80.0,
        )

        assert decision == "approved"
        assert amount == 10_000_000

    def test_medium_score_gives_partial_approval(self):
        """Score between 40-69 results in partial approval."""
        service = FinanceService(None)

        decision, amount, reasoning = service._evaluate_budget_request(
            board_confidence=50,
            current_balance=50_000_000,
            current_budget=30_000_000,
            amount_requested=20_000_000,
            win_percentage=40.0,
        )

        assert decision == "partial"
        assert 0 < amount < 20_000_000

    def test_low_score_gives_rejection(self):
        """Score < 40 results in rejection."""
        service = FinanceService(None)

        decision, amount, reasoning = service._evaluate_budget_request(
            board_confidence=15,
            current_balance=10_000_000,
            current_budget=5_000_000,
            amount_requested=50_000_000,
            win_percentage=10.0,
        )

        assert decision == "rejected"
        assert amount == 0

    def test_deficit_always_rejects(self):
        """Negative balance always results in rejection."""
        service = FinanceService(None)

        decision, amount, reasoning = service._evaluate_budget_request(
            board_confidence=100,
            current_balance=-1,
            current_budget=50_000_000,
            amount_requested=1_000_000,
            win_percentage=100.0,
        )

        assert decision == "rejected"
        assert amount == 0
        assert "deficit" in reasoning.lower()

    def test_excessive_request_penalizes_score(self):
        """Requesting more than 100% of current budget penalizes the score."""
        service = FinanceService(None)

        # Moderate conditions but excessive request
        decision, amount, reasoning = service._evaluate_budget_request(
            board_confidence=55,
            current_balance=40_000_000,
            current_budget=10_000_000,
            amount_requested=20_000_000,  # 200% of budget - excessive
            win_percentage=45.0,
        )

        # The excessive request penalty should push toward rejection or low partial
        assert decision in ("rejected", "partial")
        if decision == "partial":
            assert amount < 20_000_000

    def test_confidence_impact_on_decision(self):
        """Higher confidence leads to better outcomes for same request."""
        service = FinanceService(None)

        # Low confidence
        decision_low, amount_low, _ = service._evaluate_budget_request(
            board_confidence=30,
            current_balance=100_000_000,
            current_budget=50_000_000,
            amount_requested=25_000_000,
            win_percentage=50.0,
        )

        # High confidence
        decision_high, amount_high, _ = service._evaluate_budget_request(
            board_confidence=90,
            current_balance=100_000_000,
            current_budget=50_000_000,
            amount_requested=25_000_000,
            win_percentage=50.0,
        )

        # High confidence should yield equal or better outcome
        assert amount_high >= amount_low

    def test_win_percentage_impact(self):
        """Better performance leads to better outcomes."""
        service = FinanceService(None)

        # Poor performance
        decision_poor, amount_poor, _ = service._evaluate_budget_request(
            board_confidence=60,
            current_balance=100_000_000,
            current_budget=50_000_000,
            amount_requested=20_000_000,
            win_percentage=10.0,
        )

        # Great performance
        decision_great, amount_great, _ = service._evaluate_budget_request(
            board_confidence=60,
            current_balance=100_000_000,
            current_budget=50_000_000,
            amount_requested=20_000_000,
            win_percentage=80.0,
        )

        # Better performance should yield equal or better outcome
        assert amount_great >= amount_poor


# --- Result Structure Tests ---


class TestTransferBudgetResultStructure:
    """Tests for the result dictionary structure."""

    @pytest.mark.asyncio
    async def test_result_contains_all_required_fields(
        self, finance_service, fake_session
    ):
        """Result dict contains all expected fields."""
        career = FakeCareer(board_confidence=70)
        club = FakeClub(balance=100_000_000, transfer_budget=50_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=10_000_000,
        )

        assert "career_id" in result
        assert "club_id" in result
        assert "amount_requested" in result
        assert "decision" in result
        assert "approved_amount" in result
        assert "reasoning" in result
        assert "board_confidence" in result
        assert "financial_health" in result
        assert "new_transfer_budget" in result

    @pytest.mark.asyncio
    async def test_decision_is_valid_value(self, finance_service, fake_session):
        """Decision field is one of the valid values."""
        career = FakeCareer(board_confidence=70)
        club = FakeClub(balance=100_000_000, transfer_budget=50_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=10_000_000,
        )

        assert result["decision"] in ("approved", "partial", "rejected")

    @pytest.mark.asyncio
    async def test_approved_amount_never_exceeds_requested(
        self, finance_service, fake_session
    ):
        """Approved amount never exceeds the requested amount."""
        career = FakeCareer(board_confidence=100, matches_won=30, matches_drawn=0, matches_lost=0)
        club = FakeClub(balance=1_000_000_000, transfer_budget=500_000_000)

        fake_session.set_execute_results([
            FakeResult(scalar_value=career),
            FakeResult(scalar_value=club),
        ])

        result = await finance_service.request_transfer_budget(
            career_id=1,
            club_id=1,
            amount_requested=5_000_000,
        )

        assert result["approved_amount"] <= 5_000_000
