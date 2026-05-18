"""
Transfer Service - Transfer engine implementation for player transfers, loans, and market operations.

This module provides functionality for managing the transfer market including:
- Transfer window system (summer: weeks 1-8, winter: weeks 26-30)
- Transfer bid submission and AI acceptance probability
- Loan deal system (season-long and emergency)
- Player listing with asking price
- AI bid generation for listed players
- Squad size validation for transfers (max 40)
- Free agent signing outside windows
- Transfer history logging
- Wage calculation in negotiations
- Transfer budget management
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.transfer import Transfer, TransferType, TransferStatus
from app.models.career import Career
from app.models.club import Club
from app.models.player import Player
from app.models.squad_player import SquadPlayer, SquadStatus
from app.services.transfer_window import TransferWindowService

logger = logging.getLogger(__name__)


# --- Constants ---

SUMMER_WINDOW_START = 1
SUMMER_WINDOW_END = 8
WINTER_WINDOW_START = 26
WINTER_WINDOW_END = 30

MAX_SQUAD_SIZE = 40
MAX_CONTRACT_YEARS = 5
MIN_CONTRACT_YEARS = 1

# Wage budget safety threshold (percentage of total budget)
WAGE_BUDGET_WARNING_THRESHOLD = 0.75  # 75% of budget on wages = warning
WAGE_BUDGET_CRITICAL_THRESHOLD = 0.90  # 90% = critical


# --- Data Classes ---

@dataclass
class BidResult:
    """Result of a transfer bid submission."""
    success: bool
    accepted: bool
    message: str
    bid_amount: int = 0
    acceptance_probability: float = 0.0
    rejection_reason: Optional[str] = None


@dataclass
class LoanResult:
    """Result of a loan offer submission."""
    success: bool
    accepted: bool
    message: str
    loan_type: str = ""  # "season_long" or "emergency"
    wage_contribution: float = 0.0
    rejection_reason: Optional[str] = None


@dataclass
class AIBid:
    """An AI-generated bid for a listed player."""
    club_id: int
    club_name: str
    player_id: int
    bid_amount: int
    wage_offer: int
    contract_years: int


@dataclass
class TransferRecord:
    """A record of a completed transfer."""
    player_id: int
    player_name: str
    from_club: str
    to_club: str
    transfer_type: str  # "permanent", "loan", "free_agent", "emergency_loan"
    fee: int
    wage: int
    season: int
    week: int


@dataclass
class WageImpact:
    """Impact of a new player's wage on the club's wage bill."""
    current_wage_bill: int
    new_player_wage: int
    projected_wage_bill: int
    wage_budget_ratio: float  # projected / total budget
    is_warning: bool
    is_critical: bool
    message: str


@dataclass
class BudgetStatus:
    """Current transfer budget status."""
    transfer_budget: int
    wage_budget: int
    current_wage_bill: int
    available_transfer_funds: int
    available_wage_room: int
    can_make_transfers: bool
    message: str


# --- TransferService Class ---

class TransferService:
    """
    Service for managing the transfer market.

    Provides synchronous validation and calculation methods for transfer operations.
    No database access is performed directly; callers pass in data as needed.

    Example:
        >>> service = TransferService()
        >>> service.is_transfer_window_open(5)
        True
        >>> service.get_window_type(27)
        'winter'
    """

    # ---------------------------------------------------------------
    # 8.1 Transfer window system (summer: weeks 1-8, winter: 26-30)
    # ---------------------------------------------------------------

    def is_transfer_window_open(self, week: int) -> bool:
        """
        Check if the transfer window is open for the given week.

        Summer window: weeks 1-8 (inclusive)
        Winter window: weeks 26-30 (inclusive)

        Args:
            week: Current week number (1-52).

        Returns:
            True if a transfer window is open.
        """
        return (
            SUMMER_WINDOW_START <= week <= SUMMER_WINDOW_END
            or WINTER_WINDOW_START <= week <= WINTER_WINDOW_END
        )

    def get_window_type(self, week: int) -> Optional[str]:
        """
        Get the type of transfer window for the given week.

        Args:
            week: Current week number (1-52).

        Returns:
            "summer" if in summer window, "winter" if in winter window,
            None if no window is open.
        """
        if SUMMER_WINDOW_START <= week <= SUMMER_WINDOW_END:
            return "summer"
        if WINTER_WINDOW_START <= week <= WINTER_WINDOW_END:
            return "winter"
        return None

    # ---------------------------------------------------------------
    # 8.2 Transfer bid submission
    # ---------------------------------------------------------------

    def submit_transfer_bid(
        self,
        career_week: int,
        career_transfer_budget: int,
        current_squad_size: int,
        player_club_id: int,
        career_club_id: int,
        player_market_value: int,
        selling_club_balance: int,
        player_contract_months: int,
        player_squad_status: str,
        bid_amount: int,
        wage_offer: int,
    ) -> BidResult:
        """
        Submit a transfer bid for a player.

        Validates:
        - Transfer window is open
        - Player is not in the buyer's club
        - Squad size allows addition
        - Budget can afford the bid
        Then calculates AI acceptance probability.

        Args:
            career_week: Current week in the career.
            career_transfer_budget: Available transfer budget.
            current_squad_size: Current number of players in squad.
            player_club_id: Club ID of the player being bid on.
            career_club_id: Club ID of the buying career.
            player_market_value: Player's market value.
            selling_club_balance: Selling club's financial balance.
            player_contract_months: Months remaining on player's contract.
            player_squad_status: Player's squad status at selling club.
            bid_amount: The bid amount offered.
            wage_offer: Weekly wage offered to the player.

        Returns:
            BidResult with success/accepted status and details.
        """
        # Validate transfer window
        if not self.is_transfer_window_open(career_week):
            return BidResult(
                success=False,
                accepted=False,
                message="Transfer window is closed.",
                bid_amount=bid_amount,
                rejection_reason="window_closed",
            )

        # Validate not bidding for own player
        if player_club_id == career_club_id:
            return BidResult(
                success=False,
                accepted=False,
                message="Cannot bid for a player already in your club.",
                bid_amount=bid_amount,
                rejection_reason="own_player",
            )

        # Validate squad size
        if not self.validate_transfer_squad_size(current_squad_size):
            return BidResult(
                success=False,
                accepted=False,
                message="Squad is full (max 40 players).",
                bid_amount=bid_amount,
                rejection_reason="squad_full",
            )

        # Validate budget
        if bid_amount > career_transfer_budget:
            return BidResult(
                success=False,
                accepted=False,
                message="Insufficient transfer budget.",
                bid_amount=bid_amount,
                rejection_reason="insufficient_budget",
            )

        # Calculate acceptance probability
        probability = self.calculate_acceptance_probability(
            bid_amount=bid_amount,
            market_value=player_market_value,
            selling_club_balance=selling_club_balance,
            contract_months=player_contract_months,
            player_status=player_squad_status,
        )

        # Determine acceptance (probability-based)
        import random
        accepted = random.random() < probability

        if accepted:
            return BidResult(
                success=True,
                accepted=True,
                message="Transfer bid accepted!",
                bid_amount=bid_amount,
                acceptance_probability=probability,
            )
        else:
            return BidResult(
                success=True,
                accepted=False,
                message="Transfer bid rejected by the selling club.",
                bid_amount=bid_amount,
                acceptance_probability=probability,
                rejection_reason="club_rejected",
            )

    # ---------------------------------------------------------------
    # 8.3 AI acceptance probability calculation
    # ---------------------------------------------------------------

    def calculate_acceptance_probability(
        self,
        bid_amount: int,
        market_value: int,
        selling_club_balance: int,
        contract_months: int,
        player_status: str,
    ) -> float:
        """
        Calculate the probability that the AI selling club accepts a bid.

        Factors:
        - Bid vs market value ratio
        - Selling club financial situation
        - Player contract length remaining
        - Player squad status

        Args:
            bid_amount: The bid amount offered.
            market_value: Player's market value.
            selling_club_balance: Selling club's current balance.
            contract_months: Months remaining on player's contract.
            player_status: Player's squad status (KEY_PLAYER, FIRST_TEAM, etc.).

        Returns:
            Float between 0.0 and 1.0 representing acceptance probability.
        """
        if market_value <= 0:
            # Free agent or invalid value - auto accept
            return 1.0

        base_probability = 0.0

        # 1. Bid vs Market Value ratio
        value_ratio = bid_amount / market_value
        if value_ratio >= 1.5:
            base_probability += 0.6
        elif value_ratio >= 1.2:
            base_probability += 0.4
        elif value_ratio >= 1.0:
            base_probability += 0.2
        elif value_ratio >= 0.8:
            base_probability += 0.1
        else:
            # Lowball offer - reject
            return 0.0

        # 2. Selling club financial situation
        if selling_club_balance < 0:
            base_probability += 0.2  # Desperate to sell
        elif selling_club_balance < 1_000_000:
            base_probability += 0.1  # Needs cash

        # 3. Player contract length
        if contract_months <= 6:
            base_probability += 0.3  # Avoid losing on free
        elif contract_months <= 12:
            base_probability += 0.15
        elif contract_months <= 24:
            base_probability += 0.05

        # 4. Player squad status
        status_upper = player_status.upper() if player_status else ""
        if status_upper == "NOT_NEEDED":
            base_probability += 0.2
        elif status_upper == "BACKUP":
            base_probability += 0.1
        elif status_upper == "ROTATION":
            base_probability += 0.05
        elif status_upper == "KEY_PLAYER":
            base_probability -= 0.2

        return min(1.0, max(0.0, base_probability))

    # ---------------------------------------------------------------
    # 8.4 Transfer fee deduction from budget
    # ---------------------------------------------------------------

    def process_accepted_bid(
        self, career_transfer_budget: int, bid_amount: int
    ) -> tuple:
        """
        Process an accepted transfer bid by deducting the fee from the budget.

        Args:
            career_transfer_budget: Current transfer budget.
            bid_amount: The accepted bid amount to deduct.

        Returns:
            Tuple of (new_budget: int, success: bool, message: str).
        """
        if bid_amount < 0:
            return (career_transfer_budget, False, "Invalid bid amount.")

        if bid_amount > career_transfer_budget:
            return (
                career_transfer_budget,
                False,
                "Insufficient budget to complete transfer.",
            )

        new_budget = career_transfer_budget - bid_amount
        return (new_budget, True, f"Transfer fee of {bid_amount} deducted. New budget: {new_budget}.")

    # ---------------------------------------------------------------
    # 8.5 Loan deal system (season-long and emergency)
    # ---------------------------------------------------------------

    def submit_loan_offer(
        self,
        career_week: int,
        current_squad_size: int,
        player_club_id: int,
        career_club_id: int,
        player_contract_months: int,
        loan_type: str,
        wage_contribution: float,
    ) -> LoanResult:
        """
        Submit a loan offer for a player.

        Loan types:
        - "season_long": Standard season-long loan (requires open window)
        - "emergency": Emergency loan (can be done outside normal windows
          but only during weeks 9-25 or 31-52 with restrictions)

        Args:
            career_week: Current week in the career.
            current_squad_size: Current squad size.
            player_club_id: Club ID of the player.
            career_club_id: Club ID of the career (borrowing club).
            player_contract_months: Months remaining on player's contract.
            loan_type: "season_long" or "emergency".
            wage_contribution: Fraction of wage the borrowing club pays (0.0-1.0).

        Returns:
            LoanResult with success/accepted status.
        """
        # Validate loan type
        if loan_type not in ("season_long", "emergency"):
            return LoanResult(
                success=False,
                accepted=False,
                message="Invalid loan type. Must be 'season_long' or 'emergency'.",
                loan_type=loan_type,
                rejection_reason="invalid_loan_type",
            )

        # Validate wage contribution
        if not (0.0 <= wage_contribution <= 1.0):
            return LoanResult(
                success=False,
                accepted=False,
                message="Wage contribution must be between 0.0 and 1.0.",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="invalid_wage_contribution",
            )

        # Validate not loaning own player
        if player_club_id == career_club_id:
            return LoanResult(
                success=False,
                accepted=False,
                message="Cannot loan a player from your own club.",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="own_player",
            )

        # Validate squad size
        if not self.validate_transfer_squad_size(current_squad_size):
            return LoanResult(
                success=False,
                accepted=False,
                message="Squad is full (max 40 players).",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="squad_full",
            )

        # Validate transfer window for season-long loans
        if loan_type == "season_long" and not self.is_transfer_window_open(career_week):
            return LoanResult(
                success=False,
                accepted=False,
                message="Transfer window is closed for season-long loans.",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="window_closed",
            )

        # Validate contract length (player must have > 6 months on contract for loan)
        if player_contract_months <= 6:
            return LoanResult(
                success=False,
                accepted=False,
                message="Player's contract is too short for a loan deal.",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="short_contract",
            )

        # Loan acceptance is generally easier than permanent transfers
        # Higher wage contribution = more likely to be accepted
        acceptance_base = 0.4
        acceptance_base += wage_contribution * 0.4  # Up to +0.4 for full wage coverage
        if loan_type == "emergency":
            acceptance_base += 0.1  # Emergency loans slightly easier

        import random
        accepted = random.random() < min(1.0, acceptance_base)

        if accepted:
            return LoanResult(
                success=True,
                accepted=True,
                message=f"Loan offer accepted ({loan_type.replace('_', ' ')}).",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
            )
        else:
            return LoanResult(
                success=True,
                accepted=False,
                message="Loan offer rejected by the parent club.",
                loan_type=loan_type,
                wage_contribution=wage_contribution,
                rejection_reason="club_rejected",
            )

    # ---------------------------------------------------------------
    # 8.6 Player listing system with asking price
    # ---------------------------------------------------------------

    def validate_player_listing(
        self, squad_player: Any, asking_price: int
    ) -> tuple[bool, str]:
        """
        Validate that a player can be listed for sale.
        
        Args:
            squad_player: A SquadPlayer instance
            asking_price: The asking price to validate
        
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Validate asking price is non-negative
        if asking_price < 0:
            return (False, "Asking price cannot be negative.")
        
        # Validate player is not already listed
        if hasattr(squad_player, 'is_listed_for_sale') and squad_player.is_listed_for_sale:
            return (False, "Player is already listed for sale.")
        
        # All validations passed
        return (True, "")

    def list_player_for_sale(
        self, squad_player: Any, asking_price: int
    ) -> dict:
        """
        List a player for sale with an asking price.
        
        This method validates the listing and returns the listing details.
        The caller is responsible for persisting changes to the database.

        Args:
            squad_player: A SquadPlayer instance (must have player_id, wage).
            asking_price: The asking price set by the manager.

        Returns:
            Dictionary with listing details.

        Raises:
            ValueError: If asking_price is negative or player is already listed.
        """
        # Validate listing
        is_valid, error_msg = self.validate_player_listing(squad_player, asking_price)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Update squad player listing status
        if hasattr(squad_player, 'list_for_sale'):
            squad_player.list_for_sale(asking_price)
        else:
            # Fallback for objects without the method
            squad_player.is_listed_for_sale = True
            squad_player.asking_price = asking_price

        return {
            "player_id": squad_player.player_id,
            "asking_price": asking_price,
            "wage": squad_player.wage,
            "listed": True,
        }
    
    def unlist_player_from_sale(self, squad_player: Any) -> dict:
        """
        Remove a player from sale listing.
        
        The caller is responsible for persisting changes to the database.
        
        Args:
            squad_player: A SquadPlayer instance
        
        Returns:
            Dictionary with unlisting confirmation
        """
        # Update squad player listing status
        if hasattr(squad_player, 'unlist_from_sale'):
            squad_player.unlist_from_sale()
        else:
            # Fallback for objects without the method
            squad_player.is_listed_for_sale = False
            squad_player.asking_price = None
        
        return {
            "player_id": squad_player.player_id,
            "listed": False,
            "message": "Player removed from sale listing."
        }

    def get_listed_players(
        self, squad_players: List[Any]
    ) -> List[Any]:
        """
        Get all players currently listed for sale.

        Args:
            squad_players: List of SquadPlayer instances.

        Returns:
            List of squad players that are listed for sale.
        """
        return [
            sp for sp in squad_players 
            if hasattr(sp, 'is_listed_for_sale') and sp.is_listed_for_sale
        ]
    
    def get_listing_details(self, squad_player: Any) -> Optional[dict]:
        """
        Get listing details for a player.
        
        Args:
            squad_player: A SquadPlayer instance
        
        Returns:
            Dictionary with listing details if listed, None otherwise
        """
        if not hasattr(squad_player, 'is_listed_for_sale') or not squad_player.is_listed_for_sale:
            return None
        
        return {
            "player_id": squad_player.player_id,
            "asking_price": squad_player.asking_price,
            "wage": squad_player.wage,
            "listed": True,
        }

    # ---------------------------------------------------------------
    # 8.7 AI bid generation for listed players
    # ---------------------------------------------------------------

    def generate_ai_bids_for_listed(
        self,
        listed_players: List[dict],
        ai_clubs: List[dict],
    ) -> List[AIBid]:
        """
        Generate AI bids for players listed for sale.

        Each AI club has a chance to bid based on their budget and needs.
        Bids are typically 80-120% of the asking price.

        Args:
            listed_players: List of dicts with keys:
                - player_id (int)
                - asking_price (int)
                - player_name (str)
                - position (str)
                - ca (int)
            ai_clubs: List of dicts with keys:
                - club_id (int)
                - club_name (str)
                - transfer_budget (int)
                - needs (List[str]) - positions needed

        Returns:
            List of AIBid objects generated by AI clubs.
        """
        import random

        bids: List[AIBid] = []

        for player in listed_players:
            asking_price = player.get("asking_price", 0)
            player_position = player.get("position", "")
            player_id = player.get("player_id", 0)

            for club in ai_clubs:
                # Check if club can afford the player
                if club.get("transfer_budget", 0) < asking_price * 0.8:
                    continue

                # Check if club needs this position
                needs = club.get("needs", [])
                position_match = any(
                    need.upper() in player_position.upper() for need in needs
                )

                # Base chance to bid: 10% if no position match, 30% if match
                bid_chance = 0.30 if position_match else 0.10

                if random.random() < bid_chance:
                    # Generate bid amount (80-120% of asking price)
                    bid_multiplier = random.uniform(0.8, 1.2)
                    bid_amount = int(asking_price * bid_multiplier)

                    # Generate wage offer (reasonable range)
                    wage_offer = int(bid_amount * 0.001)  # ~0.1% of fee as weekly wage
                    wage_offer = max(wage_offer, 1000)  # Minimum wage

                    # Contract years (1-5)
                    contract_years = random.randint(2, 4)

                    bids.append(
                        AIBid(
                            club_id=club["club_id"],
                            club_name=club["club_name"],
                            player_id=player_id,
                            bid_amount=bid_amount,
                            wage_offer=wage_offer,
                            contract_years=contract_years,
                        )
                    )

        return bids

    # ---------------------------------------------------------------
    # 8.8 Squad size validation (max 40 players)
    # ---------------------------------------------------------------

    def validate_transfer_squad_size(self, current_size: int) -> bool:
        """
        Validate that the squad can accept another player via transfer.

        Args:
            current_size: Current number of players in the squad.

        Returns:
            True if squad has room (current_size < MAX_SQUAD_SIZE).
        """
        return current_size < MAX_SQUAD_SIZE

    # ---------------------------------------------------------------
    # 8.9 Free agent signing system
    # ---------------------------------------------------------------

    def sign_free_agent(
        self,
        career_week: int,
        current_squad_size: int,
        career_transfer_budget: int,
        wage_offer: int,
        contract_years: int,
        wage_budget: int,
        current_wage_bill: int,
    ) -> BidResult:
        """
        Sign a free agent player (available outside transfer windows).

        Free agents can be signed at any time during the season.
        No transfer fee is required, only wage agreement.

        Args:
            career_week: Current week (free agents available any week).
            current_squad_size: Current squad size.
            career_transfer_budget: Transfer budget (not used for fee but checked).
            wage_offer: Weekly wage offered to the free agent.
            contract_years: Contract length offered (1-5 years).
            wage_budget: Total wage budget available.
            current_wage_bill: Current weekly wage bill.

        Returns:
            BidResult indicating success or failure.
        """
        # Validate squad size
        if not self.validate_transfer_squad_size(current_squad_size):
            return BidResult(
                success=False,
                accepted=False,
                message="Squad is full (max 40 players).",
                rejection_reason="squad_full",
            )

        # Validate contract years
        if not (MIN_CONTRACT_YEARS <= contract_years <= MAX_CONTRACT_YEARS):
            return BidResult(
                success=False,
                accepted=False,
                message=f"Contract must be {MIN_CONTRACT_YEARS}-{MAX_CONTRACT_YEARS} years.",
                rejection_reason="invalid_contract",
            )

        # Validate wage offer is positive
        if wage_offer <= 0:
            return BidResult(
                success=False,
                accepted=False,
                message="Wage offer must be positive.",
                rejection_reason="invalid_wage",
            )

        # Validate wage budget
        if current_wage_bill + wage_offer > wage_budget:
            return BidResult(
                success=False,
                accepted=False,
                message="Insufficient wage budget for this signing.",
                rejection_reason="wage_budget_exceeded",
            )

        # Free agents are always accepted (no selling club to negotiate with)
        return BidResult(
            success=True,
            accepted=True,
            message="Free agent signed successfully.",
            bid_amount=0,
            acceptance_probability=1.0,
        )

    # ---------------------------------------------------------------
    # 8.10 Transfer history logging
    # ---------------------------------------------------------------

    def log_transfer(
        self,
        player_id: int,
        player_name: str,
        from_club: str,
        to_club: str,
        transfer_type: str,
        fee: int,
        wage: int,
        season: int,
        week: int,
        history: List[TransferRecord],
    ) -> TransferRecord:
        """
        Log a completed transfer to the transfer history.

        Args:
            player_id: ID of the transferred player.
            player_name: Name of the player.
            from_club: Name of the selling club (or "Free Agent").
            to_club: Name of the buying club.
            transfer_type: Type of transfer ("permanent", "loan", "free_agent", "emergency_loan").
            fee: Transfer fee paid.
            wage: Weekly wage agreed.
            season: Season number.
            week: Week number.
            history: Existing transfer history list to append to.

        Returns:
            The newly created TransferRecord.
        """
        record = TransferRecord(
            player_id=player_id,
            player_name=player_name,
            from_club=from_club,
            to_club=to_club,
            transfer_type=transfer_type,
            fee=fee,
            wage=wage,
            season=season,
            week=week,
        )
        history.append(record)
        return record

    def get_transfer_history(
        self,
        history: List[TransferRecord],
        season: Optional[int] = None,
        transfer_type: Optional[str] = None,
    ) -> List[TransferRecord]:
        """
        Get transfer history with optional filtering.

        Args:
            history: Full transfer history list.
            season: Optional season filter.
            transfer_type: Optional transfer type filter.

        Returns:
            Filtered list of TransferRecord objects.
        """
        result = history

        if season is not None:
            result = [r for r in result if r.season == season]

        if transfer_type is not None:
            result = [r for r in result if r.transfer_type == transfer_type]

        return result

    # ---------------------------------------------------------------
    # 8.11 Wage calculation in transfer negotiations
    # ---------------------------------------------------------------

    def calculate_wage_impact(
        self, current_wage_bill: int, new_player_wage: int, wage_budget: int
    ) -> WageImpact:
        """
        Calculate the impact of a new player's wage on the club's finances.

        Args:
            current_wage_bill: Current total weekly wage bill.
            new_player_wage: Proposed weekly wage for the new player.
            wage_budget: Total weekly wage budget available.

        Returns:
            WageImpact with projected figures and warning flags.
        """
        projected = current_wage_bill + new_player_wage

        if wage_budget > 0:
            ratio = projected / wage_budget
        else:
            ratio = 1.0 if projected > 0 else 0.0

        is_warning = ratio >= WAGE_BUDGET_WARNING_THRESHOLD
        is_critical = ratio >= WAGE_BUDGET_CRITICAL_THRESHOLD

        if is_critical:
            message = "CRITICAL: Wage bill will exceed 90% of budget!"
        elif is_warning:
            message = "WARNING: Wage bill will exceed 75% of budget."
        else:
            message = "Wage impact is within acceptable limits."

        return WageImpact(
            current_wage_bill=current_wage_bill,
            new_player_wage=new_player_wage,
            projected_wage_bill=projected,
            wage_budget_ratio=ratio,
            is_warning=is_warning,
            is_critical=is_critical,
            message=message,
        )

    # ---------------------------------------------------------------
    # 8.12 Transfer budget management
    # ---------------------------------------------------------------

    def get_budget_status(
        self,
        transfer_budget: int,
        wage_budget: int,
        current_wage_bill: int,
    ) -> BudgetStatus:
        """
        Get the current transfer budget status.

        Args:
            transfer_budget: Total transfer budget available.
            wage_budget: Total weekly wage budget.
            current_wage_bill: Current weekly wage expenditure.

        Returns:
            BudgetStatus with all financial details.
        """
        available_wage_room = max(0, wage_budget - current_wage_bill)
        can_make_transfers = transfer_budget > 0 and available_wage_room > 0

        if not can_make_transfers:
            if transfer_budget <= 0:
                message = "No transfer funds available."
            else:
                message = "No wage budget room available."
        else:
            message = f"Budget available: {transfer_budget} transfer, {available_wage_room} wage room."

        return BudgetStatus(
            transfer_budget=transfer_budget,
            wage_budget=wage_budget,
            current_wage_bill=current_wage_bill,
            available_transfer_funds=transfer_budget,
            available_wage_room=available_wage_room,
            can_make_transfers=can_make_transfers,
            message=message,
        )

    def can_afford_transfer(
        self,
        transfer_budget: int,
        wage_budget: int,
        current_wage_bill: int,
        fee: int,
        wage: int,
    ) -> bool:
        """
        Check if the club can afford a transfer (fee + wage).

        Args:
            transfer_budget: Available transfer budget.
            wage_budget: Total weekly wage budget.
            current_wage_bill: Current weekly wage bill.
            fee: Transfer fee required.
            wage: Weekly wage for the player.

        Returns:
            True if the club can afford both the fee and the wage.
        """
        can_afford_fee = fee <= transfer_budget
        can_afford_wage = (current_wage_bill + wage) <= wage_budget
        return can_afford_fee and can_afford_wage


    # ---------------------------------------------------------------
    # Async Database Methods for Transfer Bid Submission (Task 8.2)
    # ---------------------------------------------------------------

    async def submit_transfer_bid_async(
        self,
        db: AsyncSession,
        career_id: int,
        player_id: int,
        bid_amount: int,
        wage_offer: int,
        contract_length: int,
    ) -> dict:
        """
        Submit a transfer bid for a player (async with database integration).
        
        This method:
        1. Validates transfer window status using TransferWindowService
        2. Validates squad size constraints (max 40 players)
        3. Validates budget availability
        4. Checks player is not already in the squad
        5. Creates a pending transfer bid record
        6. Calculates AI acceptance probability
        7. Determines if bid is accepted or rejected
        8. Updates transfer status accordingly
        
        Args:
            db: Database session
            career_id: ID of the career making the bid
            player_id: ID of the player being bid on
            bid_amount: Transfer fee offered
            wage_offer: Weekly wage offered
            contract_length: Contract length in years (1-5)
            
        Returns:
            dict: Result containing success status, message, and transfer details
            
        Raises:
            ValueError: If career, player, or clubs not found
        """
        # Load career
        career_result = await db.execute(
            select(Career).where(Career.id == career_id)
        )
        career = career_result.scalar_one_or_none()
        if not career:
            raise ValueError(f"Career {career_id} not found")
        
        # Load career's club
        club_result = await db.execute(
            select(Club).where(Club.id == career.club_id)
        )
        club = club_result.scalar_one_or_none()
        if not club:
            raise ValueError(f"Club {career.club_id} not found")
        
        # Load player
        player_result = await db.execute(
            select(Player).where(Player.id == player_id)
        )
        player = player_result.scalar_one_or_none()
        if not player:
            raise ValueError(f"Player {player_id} not found")
        
        # Get player's current club (from Player model's club field)
        # Note: Player model has a 'club' field (string) that we need to look up
        player_club_result = await db.execute(
            select(Club).where(Club.name == player.club)
        )
        player_club = player_club_result.scalar_one_or_none()
        if not player_club:
            # Player might be a free agent or club not in database
            player_club_id = None
            player_club_balance = 0
        else:
            player_club_id = player_club.id
            player_club_balance = player_club.balance
        
        # Check if player is already in the squad
        existing_squad_player = await db.execute(
            select(SquadPlayer).where(
                SquadPlayer.career_id == career_id,
                SquadPlayer.player_id == player_id
            )
        )
        if existing_squad_player.scalar_one_or_none():
            return {
                "success": False,
                "accepted": False,
                "message": "Player is already in your squad",
                "rejection_reason": "already_in_squad"
            }
        
        # Get current squad size
        squad_size_result = await db.execute(
            select(func.count(SquadPlayer.id)).where(
                SquadPlayer.career_id == career_id
            )
        )
        current_squad_size = squad_size_result.scalar() or 0
        
        # Get current wage bill
        wage_bill_result = await db.execute(
            select(func.sum(SquadPlayer.wage)).where(
                SquadPlayer.career_id == career_id
            )
        )
        current_wage_bill = wage_bill_result.scalar() or 0
        
        # Validate transfer window using TransferWindowService
        transfer_window_service = TransferWindowService()
        window_status = transfer_window_service.get_window_status(career.current_week)
        
        if not window_status.can_make_permanent_transfers:
            return {
                "success": False,
                "accepted": False,
                "message": f"Transfer window is closed. Opens in {window_status.weeks_until_opens} weeks.",
                "rejection_reason": "window_closed",
                "window_status": window_status.to_dict()
            }
        
        # Calculate player's market value (use price from Player model)
        # Price is stored as string like "£2.5M", need to parse it
        market_value = self._parse_price_to_int(player.price)
        
        # Get player's squad status at current club (default to FIRST_TEAM if not in a squad)
        player_squad_status = "FIRST_TEAM"
        if player_club_id:
            # Try to find player in their current club's squad
            player_squad_result = await db.execute(
                select(SquadPlayer).where(
                    SquadPlayer.player_id == player_id
                ).order_by(SquadPlayer.updated_at.desc()).limit(1)
            )
            player_squad = player_squad_result.scalar_one_or_none()
            if player_squad:
                player_squad_status = player_squad.squad_status.value
        
        # Estimate contract months remaining (default to 24 months)
        contract_months = 24
        if player_club_id:
            player_squad_result = await db.execute(
                select(SquadPlayer).where(
                    SquadPlayer.player_id == player_id
                ).order_by(SquadPlayer.updated_at.desc()).limit(1)
            )
            player_squad = player_squad_result.scalar_one_or_none()
            if player_squad and player_squad.contract_months_remaining:
                contract_months = player_squad.contract_months_remaining
        
        # Validate using synchronous methods
        bid_result = self.submit_transfer_bid(
            career_week=career.current_week,
            career_transfer_budget=club.transfer_budget,
            current_squad_size=current_squad_size,
            player_club_id=player_club_id if player_club_id else -1,  # Use -1 for free agents
            career_club_id=club.id,
            player_market_value=market_value,
            selling_club_balance=player_club_balance,
            player_contract_months=contract_months,
            player_squad_status=player_squad_status,
            bid_amount=bid_amount,
            wage_offer=wage_offer,
        )
        
        if not bid_result.success:
            return {
                "success": False,
                "accepted": False,
                "message": bid_result.message,
                "rejection_reason": bid_result.rejection_reason,
                "bid_amount": bid_amount,
                "acceptance_probability": bid_result.acceptance_probability
            }
        
        # Create transfer record
        transfer = Transfer(
            career_id=career_id,
            player_id=player_id,
            from_club_id=player_club_id,
            to_club_id=club.id,
            transfer_type=TransferType.PERMANENT,
            transfer_status=TransferStatus.ACCEPTED if bid_result.accepted else TransferStatus.REJECTED,
            transfer_fee=bid_amount,
            wage_offer=wage_offer,
            contract_length=contract_length,
            season=career.current_season,
            week=career.current_week,
        )
        
        db.add(transfer)
        
        # If accepted, process the transfer
        if bid_result.accepted:
            # Deduct transfer fee from club budget
            club.transfer_budget -= bid_amount
            career.add_transfer_spend(bid_amount)
            
            # Add player to squad
            # Find next available squad number
            used_numbers_result = await db.execute(
                select(SquadPlayer.squad_number).where(
                    SquadPlayer.career_id == career_id
                )
            )
            used_numbers = {row[0] for row in used_numbers_result.all()}
            next_squad_number = 1
            while next_squad_number in used_numbers and next_squad_number <= 99:
                next_squad_number += 1
            
            # Create squad player record
            contract_start = date.today()
            contract_end = contract_start + relativedelta(years=contract_length)
            
            squad_player = SquadPlayer(
                career_id=career_id,
                player_id=player_id,
                contract_start_date=contract_start,
                contract_end_date=contract_end,
                wage=wage_offer,
                squad_status=SquadStatus.FIRST_TEAM,
                squad_number=next_squad_number,
                morale=70,  # Default morale
                joined_date=contract_start,
            )
            
            db.add(squad_player)
            
            # Mark transfer as completed
            transfer.transfer_status = TransferStatus.COMPLETED
            transfer.completion_date = func.now()
            
            await db.commit()
            await db.refresh(transfer)
            await db.refresh(squad_player)
            
            return {
                "success": True,
                "accepted": True,
                "message": f"Transfer completed! {player.name} has joined {club.name} for £{bid_amount:,}",
                "transfer_id": transfer.id,
                "squad_player_id": squad_player.id,
                "bid_amount": bid_amount,
                "wage_offer": wage_offer,
                "contract_length": contract_length,
                "squad_number": next_squad_number,
                "acceptance_probability": bid_result.acceptance_probability,
                "new_transfer_budget": club.transfer_budget,
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "ca": player.ca,
                    "pa": player.pa,
                }
            }
        else:
            # Bid rejected
            await db.commit()
            await db.refresh(transfer)
            
            return {
                "success": True,
                "accepted": False,
                "message": f"Transfer bid rejected. {player_club.name if player_club else 'The club'} wants more money.",
                "transfer_id": transfer.id,
                "bid_amount": bid_amount,
                "acceptance_probability": bid_result.acceptance_probability,
                "rejection_reason": bid_result.rejection_reason,
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "ca": player.ca,
                    "pa": player.pa,
                }
            }
    
    def _parse_price_to_int(self, price_str: str) -> int:
        """
        Parse price string (e.g., "£2.5M", "£500K") to integer.
        
        Args:
            price_str: Price string from Player model
            
        Returns:
            int: Price as integer (in base currency units)
        """
        if not price_str:
            return 0
        
        # Remove currency symbols and whitespace
        price_str = price_str.replace('£', '').replace('$', '').replace('€', '').strip()
        
        # Handle M (millions) and K (thousands)
        if 'M' in price_str or 'm' in price_str:
            value = float(price_str.replace('M', '').replace('m', '').strip())
            return int(value * 1_000_000)
        elif 'K' in price_str or 'k' in price_str:
            value = float(price_str.replace('K', '').replace('k', '').strip())
            return int(value * 1_000)
        else:
            try:
                return int(float(price_str))
            except ValueError:
                return 0
    
    async def get_transfer_bid_history(
        self,
        db: AsyncSession,
        career_id: int,
        season: Optional[int] = None,
        status: Optional[TransferStatus] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Get transfer bid history for a career.
        
        Args:
            db: Database session
            career_id: ID of the career
            season: Optional season filter
            status: Optional status filter
            limit: Maximum number of records to return
            
        Returns:
            List of transfer bid records with player details
        """
        query = select(Transfer).where(Transfer.career_id == career_id)
        
        if season is not None:
            query = query.where(Transfer.season == season)
        
        if status is not None:
            query = query.where(Transfer.transfer_status == status)
        
        query = query.order_by(Transfer.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        transfers = result.scalars().all()
        
        # Load player details for each transfer
        transfer_list = []
        for transfer in transfers:
            player_result = await db.execute(
                select(Player).where(Player.id == transfer.player_id)
            )
            player = player_result.scalar_one_or_none()
            
            from_club_result = await db.execute(
                select(Club).where(Club.id == transfer.from_club_id)
            ) if transfer.from_club_id else None
            from_club = from_club_result.scalar_one_or_none() if from_club_result else None
            
            to_club_result = await db.execute(
                select(Club).where(Club.id == transfer.to_club_id)
            )
            to_club = to_club_result.scalar_one_or_none()
            
            transfer_dict = transfer.to_dict()
            transfer_dict["player"] = {
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "age": player.age,
                "ca": player.ca,
            } if player else None
            transfer_dict["from_club_name"] = from_club.name if from_club else "Free Agent"
            transfer_dict["to_club_name"] = to_club.name if to_club else "Unknown"
            
            transfer_list.append(transfer_dict)
        
        return transfer_list

    # ---------------------------------------------------------------
    # Async Database Methods for Loan Deal System (Task 8.5)
    # ---------------------------------------------------------------

    async def submit_loan_offer_async(
        self,
        db: AsyncSession,
        career_id: int,
        player_id: int,
        loan_type: str,
        wage_contribution: float,
        loan_duration_weeks: Optional[int] = None,
    ) -> dict:
        """
        Submit a loan offer for a player (async with database integration).
        
        This method:
        1. Validates loan type (season_long or emergency)
        2. Validates transfer window status (season_long requires open window)
        3. Validates squad size constraints (max 40 players)
        4. Validates wage contribution (0.0-1.0)
        5. Checks player is not already in the squad
        6. Creates a pending loan transfer record
        7. Calculates AI acceptance probability
        8. Determines if loan is accepted or rejected
        9. Updates transfer status and creates squad player if accepted
        
        Loan Types:
        - season_long: Standard season-long loan (requires open transfer window)
          Duration: Until end of season (calculated automatically)
        - emergency: Emergency loan (available outside transfer windows)
          Duration: Specified by loan_duration_weeks parameter (max 12 weeks)
        
        Args:
            db: Database session
            career_id: ID of the career making the loan offer
            player_id: ID of the player being loaned
            loan_type: Type of loan ("season_long" or "emergency")
            wage_contribution: Fraction of wage paid by borrowing club (0.0-1.0)
            loan_duration_weeks: Duration in weeks (required for emergency loans)
            
        Returns:
            dict: Result containing success status, message, and loan details
            
        Raises:
            ValueError: If career, player, or clubs not found
        """
        # Load career
        career_result = await db.execute(
            select(Career).where(Career.id == career_id)
        )
        career = career_result.scalar_one_or_none()
        if not career:
            raise ValueError(f"Career {career_id} not found")
        
        # Load career's club
        club_result = await db.execute(
            select(Club).where(Club.id == career.club_id)
        )
        club = club_result.scalar_one_or_none()
        if not club:
            raise ValueError(f"Club {career.club_id} not found")
        
        # Load player
        player_result = await db.execute(
            select(Player).where(Player.id == player_id)
        )
        player = player_result.scalar_one_or_none()
        if not player:
            raise ValueError(f"Player {player_id} not found")
        
        # Get player's current club
        player_club_result = await db.execute(
            select(Club).where(Club.name == player.club)
        )
        player_club = player_club_result.scalar_one_or_none()
        if not player_club:
            return {
                "success": False,
                "accepted": False,
                "message": "Cannot loan a free agent player",
                "rejection_reason": "free_agent"
            }
        
        player_club_id = player_club.id
        
        # Check if player is already in the squad
        existing_squad_player = await db.execute(
            select(SquadPlayer).where(
                SquadPlayer.career_id == career_id,
                SquadPlayer.player_id == player_id
            )
        )
        if existing_squad_player.scalar_one_or_none():
            return {
                "success": False,
                "accepted": False,
                "message": "Player is already in your squad",
                "rejection_reason": "already_in_squad"
            }
        
        # Get current squad size
        squad_size_result = await db.execute(
            select(func.count(SquadPlayer.id)).where(
                SquadPlayer.career_id == career_id
            )
        )
        current_squad_size = squad_size_result.scalar() or 0
        
        # Get player's contract months remaining
        contract_months = 24  # Default
        player_squad_result = await db.execute(
            select(SquadPlayer).where(
                SquadPlayer.player_id == player_id
            ).order_by(SquadPlayer.updated_at.desc()).limit(1)
        )
        player_squad = player_squad_result.scalar_one_or_none()
        if player_squad and player_squad.contract_months_remaining:
            contract_months = player_squad.contract_months_remaining
        
        # Validate using synchronous method
        loan_result = self.submit_loan_offer(
            career_week=career.current_week,
            current_squad_size=current_squad_size,
            player_club_id=player_club_id,
            career_club_id=club.id,
            player_contract_months=contract_months,
            loan_type=loan_type,
            wage_contribution=wage_contribution,
        )
        
        if not loan_result.success:
            return {
                "success": False,
                "accepted": False,
                "message": loan_result.message,
                "rejection_reason": loan_result.rejection_reason,
                "loan_type": loan_type,
                "wage_contribution": wage_contribution
            }
        
        # Calculate loan duration
        if loan_type == "season_long":
            # Season-long loan: until end of season (week 52)
            loan_duration = 52 - career.current_week
        elif loan_type == "emergency":
            # Emergency loan: specified duration (max 12 weeks)
            if loan_duration_weeks is None:
                return {
                    "success": False,
                    "accepted": False,
                    "message": "Emergency loans require loan_duration_weeks parameter",
                    "rejection_reason": "missing_duration"
                }
            if loan_duration_weeks > 12:
                return {
                    "success": False,
                    "accepted": False,
                    "message": "Emergency loans cannot exceed 12 weeks",
                    "rejection_reason": "duration_too_long"
                }
            loan_duration = loan_duration_weeks
        else:
            return {
                "success": False,
                "accepted": False,
                "message": f"Invalid loan type: {loan_type}",
                "rejection_reason": "invalid_loan_type"
            }
        
        # Calculate loan return date
        loan_return_date = date.today() + relativedelta(weeks=loan_duration)
        
        # Calculate wage cost for borrowing club
        player_wage = player.wage
        wage_cost = int(player_wage * wage_contribution)
        
        # Create transfer record
        transfer_type_enum = TransferType.LOAN if loan_type == "season_long" else TransferType.EMERGENCY_LOAN
        
        transfer = Transfer(
            career_id=career_id,
            player_id=player_id,
            from_club_id=player_club_id,
            to_club_id=club.id,
            transfer_type=transfer_type_enum,
            transfer_status=TransferStatus.ACCEPTED if loan_result.accepted else TransferStatus.REJECTED,
            transfer_fee=0,  # No fee for loans
            wage_offer=player_wage,
            loan_duration=loan_duration,
            wage_contribution=wage_contribution,
            season=career.current_season,
            week=career.current_week,
        )
        
        db.add(transfer)
        
        # If accepted, process the loan
        if loan_result.accepted:
            # Add player to squad
            # Find next available squad number
            used_numbers_result = await db.execute(
                select(SquadPlayer.squad_number).where(
                    SquadPlayer.career_id == career_id
                )
            )
            used_numbers = {row[0] for row in used_numbers_result.all()}
            next_squad_number = 1
            while next_squad_number in used_numbers and next_squad_number <= 99:
                next_squad_number += 1
            
            # Create squad player record for loan
            contract_start = date.today()
            contract_end = loan_return_date
            
            squad_player = SquadPlayer(
                career_id=career_id,
                player_id=player_id,
                contract_start_date=contract_start,
                contract_end_date=contract_end,  # Loan return date
                wage=wage_cost,  # Only pay the contribution
                squad_status=SquadStatus.FIRST_TEAM,
                squad_number=next_squad_number,
                morale=70,  # Default morale
                joined_date=contract_start,
            )
            
            db.add(squad_player)
            
            # Mark transfer as completed
            transfer.transfer_status = TransferStatus.COMPLETED
            transfer.completion_date = func.now()
            
            await db.commit()
            await db.refresh(transfer)
            await db.refresh(squad_player)
            
            return {
                "success": True,
                "accepted": True,
                "message": f"Loan completed! {player.name} has joined {club.name} on loan ({loan_type.replace('_', ' ')})",
                "transfer_id": transfer.id,
                "squad_player_id": squad_player.id,
                "loan_type": loan_type,
                "loan_duration_weeks": loan_duration,
                "loan_return_date": loan_return_date.isoformat(),
                "wage_contribution": wage_contribution,
                "wage_cost_per_week": wage_cost,
                "total_wage_cost": wage_cost * loan_duration,
                "squad_number": next_squad_number,
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "ca": player.ca,
                    "pa": player.pa,
                }
            }
        else:
            # Loan rejected
            await db.commit()
            await db.refresh(transfer)
            
            return {
                "success": True,
                "accepted": False,
                "message": f"Loan offer rejected. {player_club.name} does not want to loan out {player.name}.",
                "transfer_id": transfer.id,
                "loan_type": loan_type,
                "wage_contribution": wage_contribution,
                "rejection_reason": loan_result.rejection_reason,
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "ca": player.ca,
                    "pa": player.pa,
                }
            }
    
    async def get_active_loans(
        self,
        db: AsyncSession,
        career_id: int,
    ) -> List[dict]:
        """
        Get all active loan players in the squad.
        
        Args:
            db: Database session
            career_id: ID of the career
            
        Returns:
            List of active loan players with return dates
        """
        # Get all completed loan transfers for this career
        query = select(Transfer).where(
            Transfer.career_id == career_id,
            Transfer.transfer_status == TransferStatus.COMPLETED,
            Transfer.transfer_type.in_([TransferType.LOAN, TransferType.EMERGENCY_LOAN])
        ).order_by(Transfer.created_at.desc())
        
        result = await db.execute(query)
        loan_transfers = result.scalars().all()
        
        active_loans = []
        for transfer in loan_transfers:
            # Check if player is still in squad (loan not yet returned)
            squad_player_result = await db.execute(
                select(SquadPlayer).where(
                    SquadPlayer.career_id == career_id,
                    SquadPlayer.player_id == transfer.player_id
                )
            )
            squad_player = squad_player_result.scalar_one_or_none()
            
            if squad_player:
                # Player is still on loan
                player_result = await db.execute(
                    select(Player).where(Player.id == transfer.player_id)
                )
                player = player_result.scalar_one_or_none()
                
                from_club_result = await db.execute(
                    select(Club).where(Club.id == transfer.from_club_id)
                )
                from_club = from_club_result.scalar_one_or_none()
                
                active_loans.append({
                    "transfer_id": transfer.id,
                    "squad_player_id": squad_player.id,
                    "player": {
                        "id": player.id,
                        "name": player.name,
                        "position": player.position,
                        "age": player.age,
                        "ca": player.ca,
                        "pa": player.pa,
                    } if player else None,
                    "parent_club": from_club.name if from_club else "Unknown",
                    "loan_type": transfer.transfer_type.value,
                    "loan_return_date": squad_player.contract_end_date.isoformat(),
                    "weeks_remaining": transfer.loan_duration,
                    "wage_contribution": transfer.wage_contribution,
                    "wage_cost_per_week": squad_player.wage,
                    "squad_number": squad_player.squad_number,
                    "morale": squad_player.morale,
                })
        
        return active_loans
