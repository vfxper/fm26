"""
Finance Service - Manages club financial operations and balance sheet tracking

This module implements the Finance_Module functionality for managing club finances,
including income/expenditure tracking, balance sheet generation, transaction history,
and negative balance restrictions.

Key Features:
- Record income transactions (transfer sales, matchday revenue, prize money, sponsorship)
- Record expenditure transactions (wages, transfer fees, infrastructure, staff wages)
- Generate balance sheet with categorized income and expenditure
- Track transactions with timestamps, amounts, categories, and descriptions
- Update club balance on each transaction
- Negative balance restrictions (no transfers, infrastructure, or staff hiring when in deficit)
- Expenditure validation based on financial health

Implements Requirement 8: Финансы клуба
"""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sql_func

from app.models.financial_transaction import (
    FinancialTransaction,
    TransactionType,
    IncomeCategory,
    ExpenditureCategory,
)
from app.models.club import Club
from app.models.squad_player import SquadPlayer
from app.models.staff import Staff
from app.core.logging import get_logger

logger = get_logger(__name__)


class FinanceService:
    """
    Service for managing club finances and balance sheet tracking.

    Implements Requirement 8.1: "THE Finance_Module SHALL maintain a club balance
    sheet with income (matchday revenue, TV rights, prize money, player sales,
    sponsorships) and expenditure (wages, transfer fees, infrastructure, staff salaries)."

    The service provides methods to:
    - Record income and expenditure transactions
    - Retrieve the current balance sheet
    - Query transaction history with filters
    """

    # Valid income categories
    INCOME_CATEGORIES = [
        IncomeCategory.TRANSFER_SALES,
        IncomeCategory.MATCHDAY_REVENUE,
        IncomeCategory.PRIZE_MONEY,
        IncomeCategory.SPONSORSHIP,
        IncomeCategory.OTHER_INCOME,
    ]

    # Valid expenditure categories
    EXPENDITURE_CATEGORIES = [
        ExpenditureCategory.WAGES,
        ExpenditureCategory.TRANSFER_FEES,
        ExpenditureCategory.INFRASTRUCTURE,
        ExpenditureCategory.STAFF_WAGES,
        ExpenditureCategory.OTHER_EXPENDITURE,
    ]

    def __init__(self, db_session: AsyncSession):
        """
        Initialize FinanceService.

        Args:
            db_session: Async database session for persistence operations
        """
        self.db = db_session

    async def record_income(
        self,
        club_id: int,
        career_id: int,
        category: IncomeCategory,
        amount: int,
        description: str,
        season: int,
        week: int,
    ) -> FinancialTransaction:
        """
        Record an income transaction and update the club balance.

        Args:
            club_id: ID of the club receiving income
            career_id: ID of the career
            category: Income category (transfer_sales, matchday_revenue, etc.)
            amount: Income amount (must be positive)
            description: Human-readable description of the income
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            The created FinancialTransaction record

        Raises:
            ValueError: If amount is not positive or category is invalid
        """
        if amount <= 0:
            raise ValueError(f"Income amount must be positive, got {amount}")

        if category not in self.INCOME_CATEGORIES:
            raise ValueError(
                f"Invalid income category: {category}. "
                f"Valid categories: {[c.value for c in self.INCOME_CATEGORIES]}"
            )

        if not (1 <= week <= 52):
            raise ValueError(f"Week must be between 1 and 52, got {week}")

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Create transaction record
        transaction = FinancialTransaction(
            club_id=club_id,
            career_id=career_id,
            transaction_type=TransactionType.INCOME.value,
            category=category.value,
            amount=amount,
            description=description,
            season=season,
            week=week,
        )

        self.db.add(transaction)

        # Update club balance
        await self._update_club_balance(club_id, amount)

        await self.db.flush()

        logger.info(
            f"Recorded income: club={club_id}, category={category.value}, "
            f"amount={amount}, season={season}, week={week}"
        )

        return transaction

    async def record_expenditure(
        self,
        club_id: int,
        career_id: int,
        category: ExpenditureCategory,
        amount: int,
        description: str,
        season: int,
        week: int,
    ) -> FinancialTransaction:
        """
        Record an expenditure transaction and update the club balance.

        Args:
            club_id: ID of the club making the expenditure
            career_id: ID of the career
            category: Expenditure category (wages, transfer_fees, etc.)
            amount: Expenditure amount (must be positive)
            description: Human-readable description of the expenditure
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            The created FinancialTransaction record

        Raises:
            ValueError: If amount is not positive or category is invalid
        """
        if amount <= 0:
            raise ValueError(f"Expenditure amount must be positive, got {amount}")

        if category not in self.EXPENDITURE_CATEGORIES:
            raise ValueError(
                f"Invalid expenditure category: {category}. "
                f"Valid categories: {[c.value for c in self.EXPENDITURE_CATEGORIES]}"
            )

        if not (1 <= week <= 52):
            raise ValueError(f"Week must be between 1 and 52, got {week}")

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Create transaction record
        transaction = FinancialTransaction(
            club_id=club_id,
            career_id=career_id,
            transaction_type=TransactionType.EXPENDITURE.value,
            category=category.value,
            amount=amount,
            description=description,
            season=season,
            week=week,
        )

        self.db.add(transaction)

        # Update club balance (subtract expenditure)
        await self._update_club_balance(club_id, -amount)

        await self.db.flush()

        logger.info(
            f"Recorded expenditure: club={club_id}, category={category.value}, "
            f"amount={amount}, season={season}, week={week}"
        )

        return transaction

    async def get_balance_sheet(
        self,
        club_id: int,
        career_id: int,
        season: Optional[int] = None,
    ) -> Dict:
        """
        Get the current balance sheet showing all income and expenditure categories.

        The balance sheet provides a summary of all financial activity, grouped by
        category, with totals for income, expenditure, and net balance.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Optional season filter (None = all seasons)

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - season: Season filter applied (or "all")
                - income: Dict of income categories with totals
                - expenditure: Dict of expenditure categories with totals
                - total_income: Sum of all income
                - total_expenditure: Sum of all expenditure
                - net_balance: total_income - total_expenditure
                - current_balance: Current club balance from Club model
                - transaction_count: Total number of transactions
        """
        # Build base conditions
        conditions = [
            FinancialTransaction.club_id == club_id,
            FinancialTransaction.career_id == career_id,
        ]

        if season is not None:
            conditions.append(FinancialTransaction.season == season)

        # Query income by category
        income_stmt = (
            select(
                FinancialTransaction.category,
                sql_func.sum(FinancialTransaction.amount).label("total"),
                sql_func.count(FinancialTransaction.id).label("count"),
            )
            .where(
                and_(
                    *conditions,
                    FinancialTransaction.transaction_type == TransactionType.INCOME.value,
                )
            )
            .group_by(FinancialTransaction.category)
        )

        income_result = await self.db.execute(income_stmt)
        income_rows = income_result.all()

        # Query expenditure by category
        expenditure_stmt = (
            select(
                FinancialTransaction.category,
                sql_func.sum(FinancialTransaction.amount).label("total"),
                sql_func.count(FinancialTransaction.id).label("count"),
            )
            .where(
                and_(
                    *conditions,
                    FinancialTransaction.transaction_type == TransactionType.EXPENDITURE.value,
                )
            )
            .group_by(FinancialTransaction.category)
        )

        expenditure_result = await self.db.execute(expenditure_stmt)
        expenditure_rows = expenditure_result.all()

        # Build income summary
        income_summary = {}
        total_income = 0
        for row in income_rows:
            income_summary[row.category] = {
                "total": int(row.total),
                "count": int(row.count),
            }
            total_income += int(row.total)

        # Ensure all income categories are present (even if zero)
        for cat in self.INCOME_CATEGORIES:
            if cat.value not in income_summary:
                income_summary[cat.value] = {"total": 0, "count": 0}

        # Build expenditure summary
        expenditure_summary = {}
        total_expenditure = 0
        for row in expenditure_rows:
            expenditure_summary[row.category] = {
                "total": int(row.total),
                "count": int(row.count),
            }
            total_expenditure += int(row.total)

        # Ensure all expenditure categories are present (even if zero)
        for cat in self.EXPENDITURE_CATEGORIES:
            if cat.value not in expenditure_summary:
                expenditure_summary[cat.value] = {"total": 0, "count": 0}

        # Get current club balance
        club_stmt = select(Club.balance).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        current_balance = club_result.scalar_one_or_none() or 0

        # Count total transactions
        count_stmt = (
            select(sql_func.count(FinancialTransaction.id))
            .where(and_(*conditions))
        )
        count_result = await self.db.execute(count_stmt)
        transaction_count = count_result.scalar() or 0

        return {
            "club_id": club_id,
            "career_id": career_id,
            "season": season if season is not None else "all",
            "income": income_summary,
            "expenditure": expenditure_summary,
            "total_income": total_income,
            "total_expenditure": total_expenditure,
            "net_balance": total_income - total_expenditure,
            "current_balance": current_balance,
            "transaction_count": transaction_count,
        }

    async def get_transactions(
        self,
        club_id: int,
        career_id: int,
        transaction_type: Optional[TransactionType] = None,
        category: Optional[str] = None,
        season: Optional[int] = None,
        week: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FinancialTransaction]:
        """
        Get transaction history with optional filters.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            transaction_type: Optional filter by INCOME or EXPENDITURE
            category: Optional filter by specific category
            season: Optional filter by season
            week: Optional filter by week
            limit: Maximum number of results (default 50)
            offset: Offset for pagination (default 0)

        Returns:
            List of FinancialTransaction records matching the filters
        """
        conditions = [
            FinancialTransaction.club_id == club_id,
            FinancialTransaction.career_id == career_id,
        ]

        if transaction_type is not None:
            conditions.append(
                FinancialTransaction.transaction_type == transaction_type.value
            )

        if category is not None:
            conditions.append(FinancialTransaction.category == category)

        if season is not None:
            conditions.append(FinancialTransaction.season == season)

        if week is not None:
            conditions.append(FinancialTransaction.week == week)

        stmt = (
            select(FinancialTransaction)
            .where(and_(*conditions))
            .order_by(
                FinancialTransaction.season.desc(),
                FinancialTransaction.week.desc(),
                FinancialTransaction.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        scalars_result = result.scalars()
        return list(scalars_result.all())

    async def process_weekly_finances(
        self,
        career_id: int,
        club_id: int,
        season: int,
        week: int,
    ) -> Dict:
        """
        Process all weekly financial obligations for a club.

        This method is called during the advance_week career progression to handle
        recurring weekly costs including player wages and staff wages.

        For each category of wages, a single aggregated transaction is recorded
        rather than individual per-player/per-staff transactions, keeping the
        transaction log manageable.

        Args:
            career_id: ID of the career
            club_id: ID of the club
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            Dict containing:
                - career_id: Career ID
                - club_id: Club ID
                - season: Season number
                - week: Week number
                - player_wages_total: Total player wages paid
                - player_count: Number of players on wages
                - staff_wages_total: Total staff wages paid
                - staff_count: Number of staff on wages
                - total_deductions: Combined total of all wage deductions
                - previous_balance: Club balance before deductions
                - new_balance: Club balance after deductions
                - transactions: List of transaction IDs created

        Raises:
            ValueError: If season or week values are invalid
        """
        if not (1 <= week <= 52):
            raise ValueError(f"Week must be between 1 and 52, got {week}")

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Get current club balance before deductions
        club_stmt = select(Club.balance).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        previous_balance = club_result.scalar_one_or_none() or 0

        transactions = []

        # 1. Query all squad players and sum their wages
        player_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(SquadPlayer.wage), 0).label("total_wages"),
                sql_func.count(SquadPlayer.id).label("player_count"),
            )
            .where(SquadPlayer.career_id == career_id)
        )
        player_result = await self.db.execute(player_wages_stmt)
        player_row = player_result.one()
        player_wages_total = int(player_row.total_wages)
        player_count = int(player_row.player_count)

        # Record player wages expenditure (only if there are wages to pay)
        if player_wages_total > 0:
            player_wage_tx = await self.record_expenditure(
                club_id=club_id,
                career_id=career_id,
                category=ExpenditureCategory.WAGES,
                amount=player_wages_total,
                description=f"Weekly player wages ({player_count} players)",
                season=season,
                week=week,
            )
            transactions.append(player_wage_tx.id)

        # 2. Query all staff and sum their wages
        staff_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(Staff.wage), 0).label("total_wages"),
                sql_func.count(Staff.id).label("staff_count"),
            )
            .where(
                and_(
                    Staff.career_id == career_id,
                    Staff.club_id == club_id,
                )
            )
        )
        staff_result = await self.db.execute(staff_wages_stmt)
        staff_row = staff_result.one()
        staff_wages_total = int(staff_row.total_wages)
        staff_count = int(staff_row.staff_count)

        # Record staff wages expenditure (only if there are wages to pay)
        if staff_wages_total > 0:
            staff_wage_tx = await self.record_expenditure(
                club_id=club_id,
                career_id=career_id,
                category=ExpenditureCategory.STAFF_WAGES,
                amount=staff_wages_total,
                description=f"Weekly staff wages ({staff_count} staff)",
                season=season,
                week=week,
            )
            transactions.append(staff_wage_tx.id)

        # 3. Process sponsorship payment if a deal is active for this season.
        # Implements Requirement 8.8 (Task 11.8): sponsorship deals contribute
        # weekly income to the balance during the advance_week update.
        sponsorship_payment_total = 0
        sponsorship_tier = None
        active_deal = await self.get_active_sponsorship_deal(
            club_id=club_id, career_id=career_id, season=season
        )
        if active_deal is not None:
            sponsorship_tx = await self.process_sponsorship_payment(
                club_id=club_id,
                career_id=career_id,
                season=season,
                week=week,
                sponsorship_deal=active_deal.to_dict(),
            )
            if sponsorship_tx is not None:
                transactions.append(sponsorship_tx.id)
                sponsorship_payment_total = sponsorship_tx.amount
                sponsorship_tier = active_deal.tier

        # Calculate totals
        total_deductions = player_wages_total + staff_wages_total
        new_balance = previous_balance - total_deductions + sponsorship_payment_total

        logger.info(
            f"Processed weekly finances: career={career_id}, club={club_id}, "
            f"season={season}, week={week}, "
            f"player_wages={player_wages_total} ({player_count} players), "
            f"staff_wages={staff_wages_total} ({staff_count} staff), "
            f"sponsorship_income={sponsorship_payment_total} "
            f"(tier={sponsorship_tier}), "
            f"total_deductions={total_deductions}, "
            f"balance: {previous_balance} -> {new_balance}"
        )

        return {
            "career_id": career_id,
            "club_id": club_id,
            "season": season,
            "week": week,
            "player_wages_total": player_wages_total,
            "player_count": player_count,
            "staff_wages_total": staff_wages_total,
            "staff_count": staff_count,
            "sponsorship_payment_total": sponsorship_payment_total,
            "sponsorship_tier": sponsorship_tier,
            "total_deductions": total_deductions,
            "previous_balance": previous_balance,
            "new_balance": new_balance,
            "transactions": transactions,
        }

    # --- Negative Balance Restrictions (Task 11.3) ---

    # Categories of expenditure that are restricted when in deficit
    RESTRICTED_CATEGORIES = [
        ExpenditureCategory.TRANSFER_FEES,
        ExpenditureCategory.INFRASTRUCTURE,
        ExpenditureCategory.STAFF_WAGES,
    ]

    # Categories that are always allowed (even when in deficit)
    UNRESTRICTED_CATEGORIES = [
        ExpenditureCategory.WAGES,
        ExpenditureCategory.OTHER_EXPENDITURE,
    ]

    async def can_afford(self, club_id: int, amount: int) -> bool:
        """
        Check if a club can afford a specific expenditure.

        A club can afford an expenditure if its current balance minus the amount
        would remain non-negative, OR if the expenditure is in an unrestricted
        category (like wages which are always paid).

        This is a simple balance check - it does not consider category restrictions.
        Use validate_expenditure() for full validation including deficit restrictions.

        Args:
            club_id: ID of the club
            amount: Amount to check (must be positive)

        Returns:
            True if the club's current balance >= amount, False otherwise

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        club_stmt = select(Club.balance).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            logger.warning(f"Club {club_id} not found in can_afford check")
            return False

        return balance >= amount

    async def is_in_deficit(self, club_id: int) -> bool:
        """
        Check if a club's balance is negative (in financial deficit).

        Implements Requirement 8.3: "WHEN the club balance falls below zero,
        THE Finance_Module SHALL notify the player-manager and restrict transfer
        spending to zero until the balance is positive."

        Args:
            club_id: ID of the club

        Returns:
            True if the club's balance is negative, False otherwise
        """
        club_stmt = select(Club.balance).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            logger.warning(f"Club {club_id} not found in is_in_deficit check")
            return False

        return balance < 0

    async def get_financial_restrictions(self, club_id: int) -> Dict:
        """
        Get the list of financial restrictions currently active for a club.

        When a club is in deficit (negative balance), the following are restricted:
        - Cannot make transfer bids (buying players)
        - Cannot upgrade infrastructure
        - Cannot hire new staff

        The following are always allowed:
        - Wages still get paid (can go further negative)
        - Can still sell players (to recover balance)

        Args:
            club_id: ID of the club

        Returns:
            Dict containing:
                - club_id: Club ID
                - is_in_deficit: Whether the club is in deficit
                - current_balance: Current club balance
                - restricted_actions: List of restricted action names
                - allowed_actions: List of actions still allowed
                - message: Human-readable summary of financial status
        """
        club_stmt = select(Club.balance).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            logger.warning(f"Club {club_id} not found in get_financial_restrictions")
            return {
                "club_id": club_id,
                "is_in_deficit": False,
                "current_balance": 0,
                "restricted_actions": [],
                "allowed_actions": [],
                "message": "Club not found",
            }

        in_deficit = balance < 0

        if in_deficit:
            restricted_actions = [
                "transfer_bids",
                "infrastructure_upgrades",
                "staff_hiring",
            ]
            allowed_actions = [
                "player_wages",
                "staff_wages",
                "player_sales",
            ]
            message = (
                f"Club is in financial deficit (balance: {balance}). "
                f"Transfer bids, infrastructure upgrades, and staff hiring are restricted. "
                f"Sell players to recover balance."
            )
        else:
            restricted_actions = []
            allowed_actions = [
                "transfer_bids",
                "infrastructure_upgrades",
                "staff_hiring",
                "player_wages",
                "staff_wages",
                "player_sales",
            ]
            message = f"Club finances are healthy (balance: {balance}). No restrictions."

        return {
            "club_id": club_id,
            "is_in_deficit": in_deficit,
            "current_balance": balance,
            "restricted_actions": restricted_actions,
            "allowed_actions": allowed_actions,
            "message": message,
        }

    async def validate_expenditure(
        self,
        club_id: int,
        amount: int,
        category: ExpenditureCategory,
    ) -> Dict:
        """
        Validate whether an expenditure is allowed given the club's current balance.

        This method combines deficit checking with category-based restrictions:
        - If the club is in deficit, only unrestricted categories (wages) are allowed
        - If the club is not in deficit, all expenditures are allowed
        - Wages are always allowed regardless of balance (can go further negative)

        Args:
            club_id: ID of the club
            amount: Expenditure amount (must be positive)
            category: Expenditure category

        Returns:
            Dict containing:
                - allowed: Whether the expenditure is permitted
                - reason: Explanation of why it's allowed or denied
                - club_id: Club ID
                - amount: Requested amount
                - category: Expenditure category
                - current_balance: Current club balance
                - balance_after: Projected balance after expenditure (if allowed)

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        club_stmt = select(Club.balance).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            return {
                "allowed": False,
                "reason": "Club not found",
                "club_id": club_id,
                "amount": amount,
                "category": category.value,
                "current_balance": 0,
                "balance_after": None,
            }

        in_deficit = balance < 0

        # Wages are always allowed (unrestricted categories)
        if category in self.UNRESTRICTED_CATEGORIES:
            return {
                "allowed": True,
                "reason": f"Category '{category.value}' is always allowed regardless of balance",
                "club_id": club_id,
                "amount": amount,
                "category": category.value,
                "current_balance": balance,
                "balance_after": balance - amount,
            }

        # If in deficit, restricted categories are blocked
        if in_deficit:
            return {
                "allowed": False,
                "reason": (
                    f"Club is in financial deficit (balance: {balance}). "
                    f"Category '{category.value}' is restricted until balance is positive."
                ),
                "club_id": club_id,
                "amount": amount,
                "category": category.value,
                "current_balance": balance,
                "balance_after": None,
            }

        # Not in deficit - check if club can afford it
        can_afford = balance >= amount
        if can_afford:
            return {
                "allowed": True,
                "reason": "Club can afford this expenditure",
                "club_id": club_id,
                "amount": amount,
                "category": category.value,
                "current_balance": balance,
                "balance_after": balance - amount,
            }
        else:
            # Club is not in deficit but can't afford the full amount
            # This would push them into deficit - block it for restricted categories
            return {
                "allowed": False,
                "reason": (
                    f"Expenditure of {amount} would exceed current balance of {balance}. "
                    f"Category '{category.value}' cannot push the club into deficit."
                ),
                "club_id": club_id,
                "amount": amount,
                "category": category.value,
                "current_balance": balance,
                "balance_after": None,
            }

    # --- Matchday Revenue Calculation (Task 11.4) ---

    # --- Prize Money Distribution (Task 11.5) ---

    # League position prize money (positions 1-20, amounts in currency units)
    LEAGUE_PRIZE_MONEY = {
        1: 50_000_000,
        2: 40_000_000,
        3: 35_000_000,
        4: 30_000_000,
        5: 27_000_000,
        6: 24_000_000,
        7: 21_000_000,
        8: 19_000_000,
        9: 17_000_000,
        10: 15_000_000,
        11: 13_500_000,
        12: 12_000_000,
        13: 11_000_000,
        14: 10_000_000,
        15: 9_000_000,
        16: 8_000_000,
        17: 7_000_000,
        18: 6_500_000,
        19: 6_000_000,
        20: 5_000_000,
    }

    # Domestic cup prize money by finishing position/stage
    DOMESTIC_CUP_PRIZE_MONEY = {
        "winner": 10_000_000,
        "runner_up": 5_000_000,
        "semi_finalist": 2_000_000,
        "quarter_finalist": 1_000_000,
    }

    # Continental cup prize money by finishing position/stage
    CONTINENTAL_CUP_PRIZE_MONEY = {
        "winner": 30_000_000,
        "runner_up": 20_000_000,
        "semi_finalist": 10_000_000,
        "group_stage": 5_000_000,
    }

    # Mapping of competition types to their prize tables
    PRIZE_MONEY_TABLES = {
        "league": LEAGUE_PRIZE_MONEY,
        "domestic_cup": DOMESTIC_CUP_PRIZE_MONEY,
        "continental_cup": CONTINENTAL_CUP_PRIZE_MONEY,
    }

    def get_prize_money_table(self, competition: str) -> Dict:
        """
        Get the prize money table for a given competition type.

        Args:
            competition: Competition type ("league", "domestic_cup", "continental_cup")

        Returns:
            Dict mapping positions/stages to prize money amounts.
            For league: {1: 50_000_000, 2: 40_000_000, ...}
            For cups: {"winner": amount, "runner_up": amount, ...}

        Raises:
            ValueError: If competition type is not recognized
        """
        if competition not in self.PRIZE_MONEY_TABLES:
            raise ValueError(
                f"Unknown competition type: '{competition}'. "
                f"Valid types: {list(self.PRIZE_MONEY_TABLES.keys())}"
            )

        return dict(self.PRIZE_MONEY_TABLES[competition])

    async def distribute_prize_money(
        self,
        club_id: int,
        career_id: int,
        competition: str,
        position: object,
        season: int,
        week: int,
    ) -> FinancialTransaction:
        """
        Distribute prize money to a club based on competition results.

        Prize money is awarded based on the competition type and the club's
        finishing position or stage reached:
        - League: Position 1-20 gets decreasing amounts (1st: 50M, 20th: 5M)
        - Domestic Cup: Winner, runner-up, semi-finalists, quarter-finalists
        - Continental Cup: Winner, runner-up, semi-finalists, group stage

        The prize money is recorded as a PRIZE_MONEY income transaction.

        Args:
            club_id: ID of the club receiving prize money
            career_id: ID of the career
            competition: Competition type ("league", "domestic_cup", "continental_cup")
            position: Finishing position (int for league 1-20, str for cups e.g. "winner")
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            The created FinancialTransaction record

        Raises:
            ValueError: If competition type is invalid, position is invalid,
                       or no prize money is defined for the given position
        """
        if competition not in self.PRIZE_MONEY_TABLES:
            raise ValueError(
                f"Unknown competition type: '{competition}'. "
                f"Valid types: {list(self.PRIZE_MONEY_TABLES.keys())}"
            )

        prize_table = self.PRIZE_MONEY_TABLES[competition]

        # Validate position and look up prize amount
        if competition == "league":
            if not isinstance(position, int) or position < 1 or position > 20:
                raise ValueError(
                    f"League position must be an integer between 1 and 20, got {position}"
                )
            amount = prize_table.get(position)
        else:
            # Cup competitions use string positions
            if not isinstance(position, str):
                raise ValueError(
                    f"Cup position must be a string (e.g. 'winner', 'runner_up'), "
                    f"got {type(position).__name__}: {position}"
                )
            valid_positions = list(prize_table.keys())
            if position not in prize_table:
                raise ValueError(
                    f"Invalid position '{position}' for {competition}. "
                    f"Valid positions: {valid_positions}"
                )
            amount = prize_table[position]

        if amount is None or amount <= 0:
            raise ValueError(
                f"No prize money defined for position {position} in {competition}"
            )

        # Build description
        if competition == "league":
            description = f"League prize money - Position {position}"
        elif competition == "domestic_cup":
            description = f"Domestic Cup prize money - {position.replace('_', ' ').title()}"
        else:
            description = f"Continental Cup prize money - {position.replace('_', ' ').title()}"

        # Record as PRIZE_MONEY income
        transaction = await self.record_income(
            club_id=club_id,
            career_id=career_id,
            category=IncomeCategory.PRIZE_MONEY,
            amount=amount,
            description=description,
            season=season,
            week=week,
        )

        logger.info(
            f"Distributed prize money: club={club_id}, competition={competition}, "
            f"position={position}, amount={amount}, season={season}, week={week}"
        )

        return transaction

    # --- Matchday Revenue Calculation (Task 11.4) ---

    # Stadium capacity lookup based on stadium infrastructure level (1-5).
    # These values mirror infrastructure_service.CATEGORY_EFFECTS[STADIUM][level]
    # ["max_capacity"] (Task 12.8) so that 11.4 and 12.8 stay in sync.
    STADIUM_CAPACITY_BY_LEVEL = {
        1: 10_000,
        2: 25_000,
        3: 40_000,
        4: 60_000,
        5: 80_000,
    }

    # Stadium revenue multiplier applied after computing base matchday revenue.
    # Mirrors infrastructure_service.CATEGORY_EFFECTS[STADIUM][level]
    # ["matchday_revenue_multiplier"] (Task 12.8): higher Stadium levels not
    # only increase capacity but also command premium hospitality, retail, and
    # corporate-box income beyond raw ticket sales.
    STADIUM_REVENUE_MULTIPLIER_BY_LEVEL = {
        1: 1.0,
        2: 1.25,
        3: 1.5,
        4: 1.85,
        5: 2.25,
    }

    # Base ticket prices by competition type (in currency units)
    BASE_TICKET_PRICE_BY_COMPETITION = {
        "league": 30,
        "domestic_cup": 35,
        "continental_cup": 50,
        "friendly": 15,
    }

    # Default ticket price for unknown competition types
    DEFAULT_TICKET_PRICE = 25

    async def calculate_matchday_revenue(
        self,
        club_id: int,
        career_id: int,
        competition: str,
        opponent_reputation: int,
        season: int,
        week: int,
    ) -> Dict:
        """
        Calculate and record matchday revenue for a home match.

        Revenue is calculated as:
            base_revenue = attendance * ticket_price
            revenue      = int(base_revenue * stadium_revenue_multiplier)

        Where:
        - attendance = stadium_capacity * fill_rate
        - fill_rate is affected by club reputation, competition type, and opponent reputation
        - ticket_price is based on competition type and opponent reputation
        - stadium_capacity is determined by the club's stadium infrastructure level
        - stadium_revenue_multiplier reflects hospitality, retail, and corporate
          income that scales with Stadium level (Task 12.8)

        Only home matches generate matchday revenue.

        Implements Requirement 8.4: "THE Finance_Module SHALL calculate matchday revenue
        based on stadium capacity, average attendance, and ticket price."

        Implements Requirement 9.8 / Task 12.8: stadium upgrades increase the
        maximum matchday revenue capacity by raising both attendance ceiling
        and the stadium revenue multiplier.

        Args:
            club_id: ID of the home club
            career_id: ID of the career
            competition: Competition type (league, domestic_cup, continental_cup, friendly)
            opponent_reputation: Opponent club reputation (1-100)
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - stadium_level: The home club's Stadium infrastructure level (1-5)
                - stadium_capacity: Stadium capacity based on level
                - stadium_revenue_multiplier: Multiplier applied for Stadium level
                - fill_rate: Calculated fill rate (0.0-1.0)
                - attendance: Actual attendance (integer)
                - ticket_price: Ticket price per seat
                - base_revenue: attendance * ticket_price (before Stadium multiplier)
                - revenue: Total matchday revenue (after Stadium multiplier)
                - competition: Competition type
                - opponent_reputation: Opponent reputation
                - transaction_id: ID of the recorded income transaction (or None)

        Raises:
            ValueError: If opponent_reputation is out of range or club not found
        """
        if not (1 <= opponent_reputation <= 100):
            raise ValueError(
                f"Opponent reputation must be between 1 and 100, got {opponent_reputation}"
            )

        if not (1 <= week <= 52):
            raise ValueError(f"Week must be between 1 and 52, got {week}")

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Get club data (stadium_level and reputation)
        club_stmt = select(Club).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        club = result.scalar_one_or_none()

        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        # 1. Determine stadium capacity from level (default to level 1 if unknown)
        stadium_level = club.stadium_level
        stadium_capacity = self.STADIUM_CAPACITY_BY_LEVEL.get(
            stadium_level, self.STADIUM_CAPACITY_BY_LEVEL[1]
        )

        # 2. Determine stadium revenue multiplier from level
        stadium_revenue_multiplier = self.STADIUM_REVENUE_MULTIPLIER_BY_LEVEL.get(
            stadium_level, self.STADIUM_REVENUE_MULTIPLIER_BY_LEVEL[1]
        )

        # 3. Calculate fill rate
        fill_rate = self._calculate_fill_rate(
            club_reputation=club.reputation,
            competition=competition,
            opponent_reputation=opponent_reputation,
        )

        # 4. Calculate attendance
        attendance = int(stadium_capacity * fill_rate)

        # 5. Calculate ticket price
        ticket_price = self._calculate_ticket_price(
            competition=competition,
            opponent_reputation=opponent_reputation,
        )

        # 6. Calculate revenue (apply Stadium-level revenue multiplier on top
        #    of raw ticket sales to account for hospitality / retail income).
        base_revenue = attendance * ticket_price
        revenue = int(base_revenue * stadium_revenue_multiplier)

        # 7. Record as income transaction (only if revenue > 0)
        transaction_id = None
        if revenue > 0:
            transaction = await self.record_income(
                club_id=club_id,
                career_id=career_id,
                category=IncomeCategory.MATCHDAY_REVENUE,
                amount=revenue,
                description=(
                    f"Matchday revenue - {competition} (Week {week}): "
                    f"{attendance:,} attendance @ {ticket_price} per ticket "
                    f"(Stadium L{stadium_level} x{stadium_revenue_multiplier:g})"
                ),
                season=season,
                week=week,
            )
            transaction_id = transaction.id

        logger.info(
            f"Matchday revenue calculated: club={club_id}, competition={competition}, "
            f"stadium_level={stadium_level}, capacity={stadium_capacity}, "
            f"fill_rate={fill_rate:.2f}, attendance={attendance}, "
            f"ticket_price={ticket_price}, multiplier={stadium_revenue_multiplier}, "
            f"base_revenue={base_revenue}, revenue={revenue}"
        )

        return {
            "club_id": club_id,
            "career_id": career_id,
            "stadium_level": stadium_level,
            "stadium_capacity": stadium_capacity,
            "stadium_revenue_multiplier": stadium_revenue_multiplier,
            "fill_rate": fill_rate,
            "attendance": attendance,
            "ticket_price": ticket_price,
            "base_revenue": base_revenue,
            "revenue": revenue,
            "competition": competition,
            "opponent_reputation": opponent_reputation,
            "transaction_id": transaction_id,
        }

    def _calculate_fill_rate(
        self,
        club_reputation: int,
        competition: str,
        opponent_reputation: int,
    ) -> float:
        """
        Calculate the stadium fill rate based on various factors.

        The fill rate is composed of:
        - Base fill rate from club reputation (higher reputation = more fans)
        - Competition bonus (bigger competitions attract more fans)
        - Opponent attractiveness bonus (famous opponents draw bigger crowds)

        The final fill rate is clamped between 0.3 (minimum 30% attendance)
        and 1.0 (sold out).

        Args:
            club_reputation: Home club reputation (1-100)
            competition: Competition type
            opponent_reputation: Opponent reputation (1-100)

        Returns:
            Fill rate as a float between 0.3 and 1.0
        """
        # Base fill rate from club reputation (40%-85% based on reputation)
        # reputation 1 -> 0.40, reputation 100 -> 0.85
        base_rate = 0.40 + (club_reputation / 100.0) * 0.45

        # Competition bonus
        competition_bonus = {
            "league": 0.0,
            "domestic_cup": 0.05,
            "continental_cup": 0.10,
            "friendly": -0.10,
        }.get(competition, 0.0)

        # Opponent attractiveness bonus (big teams draw bigger crowds)
        # opponent_reputation 1 -> 0.0, opponent_reputation 100 -> 0.10
        opponent_bonus = (opponent_reputation / 100.0) * 0.10

        # Calculate total fill rate
        fill_rate = base_rate + competition_bonus + opponent_bonus

        # Clamp between 0.3 and 1.0
        return max(0.3, min(1.0, fill_rate))

    def _calculate_ticket_price(
        self,
        competition: str,
        opponent_reputation: int,
    ) -> int:
        """
        Calculate the ticket price based on competition and opponent.

        Ticket price is determined by:
        - Base price from competition type
        - Premium for high-reputation opponents (up to +50% for top opponents)

        Args:
            competition: Competition type
            opponent_reputation: Opponent reputation (1-100)

        Returns:
            Ticket price as an integer (currency units)
        """
        # Get base price for competition type
        base_price = self.BASE_TICKET_PRICE_BY_COMPETITION.get(
            competition, self.DEFAULT_TICKET_PRICE
        )

        # Opponent reputation premium (0% to 50% increase for top opponents)
        # reputation 1 -> 0% premium, reputation 100 -> 50% premium
        opponent_premium = (opponent_reputation / 100.0) * 0.50

        # Calculate final price
        final_price = int(base_price * (1 + opponent_premium))

        return max(1, final_price)  # Minimum ticket price of 1

    # --- Financial Summary Screen (Task 11.6) ---

    # Financial health thresholds
    HEALTH_DEFICIT_THRESHOLD = 0  # Below 0 = deficit
    HEALTH_WARNING_THRESHOLD_WEEKS = 8  # If balance covers fewer than 8 weeks of wages

    async def get_financial_summary(
        self,
        club_id: int,
        career_id: int,
        season: int,
    ) -> Dict:
        """
        Generate a comprehensive financial summary for display to the player-manager.

        Combines balance sheet data with additional context including weekly wage bill,
        transfer budget remaining, financial health status, and comparison with the
        previous season (if available).

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Current in-game season number

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - season: Current season
                - current_balance: Current club balance
                - income_breakdown: Dict of income categories with totals for this season
                - expenditure_breakdown: Dict of expenditure categories with totals for this season
                - total_income: Sum of all income this season
                - total_expenditure: Sum of all expenditure this season
                - net_profit_loss: total_income - total_expenditure for this season
                - weekly_wage_bill: Combined weekly wages (players + staff)
                - player_wages_weekly: Weekly player wages total
                - staff_wages_weekly: Weekly staff wages total
                - transfer_budget_remaining: Remaining transfer budget
                - financial_health: "healthy", "warning", or "deficit"
                - health_message: Human-readable explanation of financial health
                - previous_season_comparison: Comparison with previous season (or None)

        Raises:
            ValueError: If season is not positive
        """
        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # 1. Get balance sheet for current season
        balance_sheet = await self.get_balance_sheet(
            club_id=club_id,
            career_id=career_id,
            season=season,
        )

        current_balance = balance_sheet["current_balance"]

        # 2. Calculate weekly wage bill (players + staff)
        player_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(SquadPlayer.wage), 0).label("total_wages"),
            )
            .where(SquadPlayer.career_id == career_id)
        )
        player_result = await self.db.execute(player_wages_stmt)
        player_wages_weekly = int(player_result.scalar() or 0)

        staff_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(Staff.wage), 0).label("total_wages"),
            )
            .where(
                and_(
                    Staff.career_id == career_id,
                    Staff.club_id == club_id,
                )
            )
        )
        staff_result = await self.db.execute(staff_wages_stmt)
        staff_wages_weekly = int(staff_result.scalar() or 0)

        weekly_wage_bill = player_wages_weekly + staff_wages_weekly

        # 3. Get transfer budget remaining
        club_stmt = select(Club.transfer_budget).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        transfer_budget_remaining = club_result.scalar_one_or_none() or 0

        # 4. Calculate financial health status
        financial_health, health_message = self._calculate_financial_health(
            current_balance=current_balance,
            weekly_wage_bill=weekly_wage_bill,
        )

        # 5. Get previous season comparison (if season > 1)
        previous_season_comparison = None
        if season > 1:
            previous_balance_sheet = await self.get_balance_sheet(
                club_id=club_id,
                career_id=career_id,
                season=season - 1,
            )
            # Only include comparison if previous season had transactions
            if previous_balance_sheet["transaction_count"] > 0:
                prev_income = previous_balance_sheet["total_income"]
                prev_expenditure = previous_balance_sheet["total_expenditure"]
                prev_net = previous_balance_sheet["net_balance"]
                curr_income = balance_sheet["total_income"]
                curr_expenditure = balance_sheet["total_expenditure"]
                curr_net = balance_sheet["net_balance"]

                previous_season_comparison = {
                    "previous_season": season - 1,
                    "previous_total_income": prev_income,
                    "previous_total_expenditure": prev_expenditure,
                    "previous_net_profit_loss": prev_net,
                    "income_change": curr_income - prev_income,
                    "expenditure_change": curr_expenditure - prev_expenditure,
                    "net_change": curr_net - prev_net,
                    "income_change_percent": (
                        round(((curr_income - prev_income) / prev_income) * 100, 1)
                        if prev_income > 0 else None
                    ),
                    "expenditure_change_percent": (
                        round(((curr_expenditure - prev_expenditure) / prev_expenditure) * 100, 1)
                        if prev_expenditure > 0 else None
                    ),
                }

        return {
            "club_id": club_id,
            "career_id": career_id,
            "season": season,
            "current_balance": current_balance,
            "income_breakdown": balance_sheet["income"],
            "expenditure_breakdown": balance_sheet["expenditure"],
            "total_income": balance_sheet["total_income"],
            "total_expenditure": balance_sheet["total_expenditure"],
            "net_profit_loss": balance_sheet["net_balance"],
            "weekly_wage_bill": weekly_wage_bill,
            "player_wages_weekly": player_wages_weekly,
            "staff_wages_weekly": staff_wages_weekly,
            "transfer_budget_remaining": transfer_budget_remaining,
            "financial_health": financial_health,
            "health_message": health_message,
            "previous_season_comparison": previous_season_comparison,
        }

    def _calculate_financial_health(
        self,
        current_balance: int,
        weekly_wage_bill: int,
    ) -> tuple:
        """
        Calculate the financial health status based on balance and wage obligations.

        Health statuses:
        - "deficit": Balance is negative
        - "warning": Balance is positive but covers fewer than 8 weeks of wages
        - "healthy": Balance comfortably covers ongoing obligations

        Args:
            current_balance: Current club balance
            weekly_wage_bill: Combined weekly wages (players + staff)

        Returns:
            Tuple of (status_string, human_readable_message)
        """
        if current_balance < self.HEALTH_DEFICIT_THRESHOLD:
            return (
                "deficit",
                f"Club is in financial deficit (balance: {current_balance:,}). "
                f"Transfer spending and new hires are restricted."
            )

        # Check if balance covers at least 8 weeks of wages
        if weekly_wage_bill > 0:
            weeks_covered = current_balance // weekly_wage_bill
            if weeks_covered < self.HEALTH_WARNING_THRESHOLD_WEEKS:
                return (
                    "warning",
                    f"Financial caution: balance ({current_balance:,}) covers only "
                    f"{weeks_covered} weeks of wages ({weekly_wage_bill:,}/week). "
                    f"Consider increasing revenue or reducing costs."
                )

        return (
            "healthy",
            f"Club finances are healthy (balance: {current_balance:,}). "
            f"No financial concerns."
        )

    # --- Transfer Budget Request System (Task 11.7) ---

    # Board decision thresholds
    # Confidence thresholds for approval likelihood
    CONFIDENCE_HIGH = 70  # High confidence - board is generous
    CONFIDENCE_MEDIUM = 45  # Medium confidence - board is cautious
    # Below CONFIDENCE_MEDIUM - board is reluctant

    # Maximum request as a percentage of current transfer budget
    # Requests above this are considered unreasonable
    MAX_REASONABLE_REQUEST_RATIO = 1.0  # 100% of current budget

    async def request_transfer_budget(
        self,
        career_id: int,
        club_id: int,
        amount_requested: int,
    ) -> Dict:
        """
        Request additional transfer budget from the board.

        The board's decision depends on:
        1. Board confidence level (higher confidence = more likely to approve)
        2. Club's current financial health (healthy clubs can afford more)
        3. Current season performance (winning teams get more budget)
        4. Amount requested relative to current budget (reasonable requests more likely approved)

        The board can:
        - Approve the full amount requested
        - Approve a partial amount (reduced based on factors)
        - Reject the request entirely

        Implements Requirement 8.7: "THE Finance_Module SHALL allow the player-manager
        to request a transfer budget increase from the board, subject to board approval
        based on club financial health."

        Args:
            career_id: ID of the career
            club_id: ID of the club requesting budget
            amount_requested: Amount of additional transfer budget requested (must be positive)

        Returns:
            Dict containing:
                - career_id: Career ID
                - club_id: Club ID
                - amount_requested: Original amount requested
                - decision: "approved", "partial", or "rejected"
                - approved_amount: Amount approved (0 if rejected)
                - reasoning: Human-readable explanation of the board's decision
                - board_confidence: Current board confidence level
                - financial_health: Current financial health status
                - new_transfer_budget: Updated transfer budget after approval

        Raises:
            ValueError: If amount_requested is not positive, or career/club not found
        """
        if amount_requested <= 0:
            raise ValueError(
                f"Amount requested must be positive, got {amount_requested}"
            )

        # 1. Load career data (board confidence, performance)
        from app.models.career import Career

        career_stmt = select(Career).where(Career.id == career_id)
        career_result = await self.db.execute(career_stmt)
        career = career_result.scalar_one_or_none()

        if career is None:
            raise ValueError(f"Career with id {career_id} not found")

        # 2. Load club data (financial health, current budget)
        club_stmt = select(Club).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        club = club_result.scalar_one_or_none()

        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        # 3. Calculate approval factors
        board_confidence = career.board_confidence
        current_balance = club.balance
        current_budget = club.transfer_budget
        win_percentage = career.get_win_percentage()

        # 4. Determine board decision
        decision, approved_amount, reasoning = self._evaluate_budget_request(
            board_confidence=board_confidence,
            current_balance=current_balance,
            current_budget=current_budget,
            amount_requested=amount_requested,
            win_percentage=win_percentage,
        )

        # 5. Apply approved amount to club's transfer budget
        if approved_amount > 0:
            club.transfer_budget += approved_amount
            await self.db.flush()

        new_transfer_budget = club.transfer_budget

        # Determine financial health status
        weekly_wage_bill = 0  # Simplified - just use balance for health check
        financial_health, _ = self._calculate_financial_health(
            current_balance=current_balance,
            weekly_wage_bill=weekly_wage_bill,
        )

        logger.info(
            f"Transfer budget request: career={career_id}, club={club_id}, "
            f"requested={amount_requested}, decision={decision}, "
            f"approved={approved_amount}, confidence={board_confidence}, "
            f"balance={current_balance}"
        )

        return {
            "career_id": career_id,
            "club_id": club_id,
            "amount_requested": amount_requested,
            "decision": decision,
            "approved_amount": approved_amount,
            "reasoning": reasoning,
            "board_confidence": board_confidence,
            "financial_health": financial_health,
            "new_transfer_budget": new_transfer_budget,
        }

    def _evaluate_budget_request(
        self,
        board_confidence: int,
        current_balance: int,
        current_budget: int,
        amount_requested: int,
        win_percentage: float,
    ) -> tuple:
        """
        Evaluate a transfer budget request and determine the board's decision.

        Decision logic:
        1. If club is in deficit (negative balance) -> always reject
        2. Calculate an approval score based on:
           - Board confidence (0-40 points)
           - Financial health (0-30 points)
           - Season performance (0-20 points)
           - Request reasonableness (0-10 points, or penalty)
        3. Based on total score:
           - Score >= 70: Full approval
           - Score >= 40: Partial approval (proportional to score)
           - Score < 40: Rejection

        Args:
            board_confidence: Board confidence level (1-100)
            current_balance: Club's current balance
            current_budget: Club's current transfer budget
            amount_requested: Amount requested
            win_percentage: Manager's win percentage this career

        Returns:
            Tuple of (decision, approved_amount, reasoning)
        """
        reasons = []

        # Immediate rejection: club in deficit
        if current_balance < 0:
            return (
                "rejected",
                0,
                "The board has rejected your request. The club is currently "
                "in financial deficit and cannot allocate additional transfer funds.",
            )

        # Calculate approval score (0-100)
        score = 0

        # Factor 1: Board confidence (0-40 points)
        # confidence 1-100 maps to 0-40 points
        confidence_score = (board_confidence / 100.0) * 40
        score += confidence_score
        if board_confidence >= self.CONFIDENCE_HIGH:
            reasons.append("The board has high confidence in your management")
        elif board_confidence >= self.CONFIDENCE_MEDIUM:
            reasons.append("The board has moderate confidence in your management")
        else:
            reasons.append("The board has concerns about your management")

        # Factor 2: Financial health (0-30 points)
        # Based on how much balance exceeds the request
        if current_balance > 0:
            # How many times the balance covers the request
            coverage_ratio = current_balance / max(amount_requested, 1)
            if coverage_ratio >= 5.0:
                health_score = 30
                reasons.append("The club's finances are very strong")
            elif coverage_ratio >= 2.0:
                health_score = 20
                reasons.append("The club's finances are healthy")
            elif coverage_ratio >= 1.0:
                health_score = 10
                reasons.append("The club can afford this but it would be a stretch")
            else:
                health_score = 5
                reasons.append(
                    "The requested amount exceeds what the club can comfortably afford"
                )
            score += health_score

        # Factor 3: Season performance (0-20 points)
        # win_percentage 0-100 maps to 0-20 points
        performance_score = (win_percentage / 100.0) * 20
        score += performance_score
        if win_percentage >= 60:
            reasons.append("Your strong results this season support the request")
        elif win_percentage >= 40:
            reasons.append("Your results have been acceptable")
        elif win_percentage > 0:
            reasons.append("Your results have been disappointing")

        # Factor 4: Request reasonableness (0-10 points or penalty)
        if current_budget > 0:
            request_ratio = amount_requested / current_budget
            if request_ratio <= 0.25:
                reasonableness_score = 10
                reasons.append("The request is very modest")
            elif request_ratio <= 0.5:
                reasonableness_score = 7
                reasons.append("The request is reasonable")
            elif request_ratio <= self.MAX_REASONABLE_REQUEST_RATIO:
                reasonableness_score = 3
                reasons.append("The request is ambitious")
            else:
                reasonableness_score = -10
                reasons.append("The request is considered excessive by the board")
        else:
            # No existing budget - any request is ambitious
            if amount_requested <= current_balance * 0.1:
                reasonableness_score = 5
                reasons.append("The request is modest given the club's situation")
            else:
                reasonableness_score = 0
                reasons.append("The board notes there is no existing transfer budget")

        score += reasonableness_score

        # Clamp score to 0-100
        score = max(0, min(100, score))

        # Make decision based on score
        if score >= 70:
            decision = "approved"
            approved_amount = amount_requested
            reasoning = (
                "The board has approved your full budget request. "
                + " ".join(reasons)
            )
        elif score >= 40:
            # Partial approval - scale between 30% and 90% based on score
            # score 40 -> 30%, score 69 -> 90%
            approval_ratio = 0.30 + ((score - 40) / 30.0) * 0.60
            approved_amount = int(amount_requested * approval_ratio)
            # Round to nearest reasonable amount (nearest 100,000)
            if approved_amount >= 100_000:
                approved_amount = (approved_amount // 100_000) * 100_000
            decision = "partial"
            reasoning = (
                f"The board has partially approved your request, "
                f"granting {approved_amount:,} of the {amount_requested:,} requested. "
                + " ".join(reasons)
            )
        else:
            decision = "rejected"
            approved_amount = 0
            reasoning = (
                "The board has rejected your budget request. "
                + " ".join(reasons)
            )

        return decision, approved_amount, reasoning

    async def _update_club_balance(self, club_id: int, amount: int) -> None:
        """
        Update the club's balance by the given amount.

        Args:
            club_id: ID of the club
            amount: Amount to add (positive) or subtract (negative)
        """
        stmt = select(Club).where(Club.id == club_id)
        result = await self.db.execute(stmt)
        club = result.scalar_one_or_none()

        if club is not None:
            club.balance += amount
            logger.debug(
                f"Updated club {club_id} balance by {amount}, "
                f"new balance: {club.balance}"
            )
        else:
            logger.warning(f"Club {club_id} not found, balance not updated")

    # --- Sponsorship Deal Simulation (Task 11.8) ---

    # Sponsorship tiers with annual value ranges (in currency units per season)
    SPONSORSHIP_TIERS = {
        "small": {"min": 1_000_000, "max": 3_000_000, "label": "Small Sponsor"},
        "medium": {"min": 3_000_000, "max": 8_000_000, "label": "Medium Sponsor"},
        "large": {"min": 8_000_000, "max": 15_000_000, "label": "Large Sponsor"},
        "premium": {"min": 15_000_000, "max": 30_000_000, "label": "Premium Sponsor"},
    }

    # Sponsorship deal duration range (in seasons)
    SPONSORSHIP_MIN_DURATION = 1
    SPONSORSHIP_MAX_DURATION = 3

    # Reputation thresholds for tier eligibility
    # Club must meet reputation threshold to attract that tier
    SPONSORSHIP_REPUTATION_THRESHOLDS = {
        "small": 1,       # Any club can get a small sponsor
        "medium": 30,     # Reputation 30+ for medium sponsors
        "large": 60,      # Reputation 60+ for large sponsors
        "premium": 80,    # Reputation 80+ for premium sponsors
    }

    def _determine_sponsorship_tier(
        self,
        club_reputation: int,
        league_position: int,
        stadium_level: int,
        in_continental_cup: bool,
    ) -> str:
        """
        Determine the sponsorship tier a club qualifies for based on multiple factors.

        Factors:
        - Club reputation (1-100): Primary factor for tier selection
        - League position (1-20): Better position boosts tier
        - Stadium level (1-5): Higher stadium = more exposure
        - Continental cup participation: Premium sponsors want continental exposure

        The method calculates a composite score and maps it to a tier.

        Args:
            club_reputation: Club reputation (1-100)
            league_position: Current league position (1-20, lower is better)
            stadium_level: Stadium infrastructure level (1-5)
            in_continental_cup: Whether the club is in a continental competition

        Returns:
            Sponsorship tier string: "small", "medium", "large", or "premium"
        """
        # Calculate composite score (0-100 scale)
        # Reputation contributes 50% of the score
        reputation_score = club_reputation * 0.50

        # League position contributes 25% (position 1 = 25 points, position 20 = ~1 point)
        position_score = max(0, (21 - league_position) / 20.0) * 25.0

        # Stadium level contributes 15% (level 1 = 3, level 5 = 15)
        stadium_score = (stadium_level / 5.0) * 15.0

        # Continental cup contributes 10%
        continental_score = 10.0 if in_continental_cup else 0.0

        composite_score = reputation_score + position_score + stadium_score + continental_score

        # Map composite score to tier
        if composite_score >= 75:
            return "premium"
        elif composite_score >= 55:
            return "large"
        elif composite_score >= 35:
            return "medium"
        else:
            return "small"

    def _calculate_sponsorship_value(
        self,
        tier: str,
        club_reputation: int,
        league_position: int,
        stadium_level: int,
        in_continental_cup: bool,
    ) -> int:
        """
        Calculate the annual sponsorship value within the tier's range.

        The value is interpolated within the tier's min-max range based on
        the club's attractiveness factors.

        Args:
            tier: Sponsorship tier ("small", "medium", "large", "premium")
            club_reputation: Club reputation (1-100)
            league_position: Current league position (1-20)
            stadium_level: Stadium infrastructure level (1-5)
            in_continental_cup: Whether the club is in a continental competition

        Returns:
            Annual sponsorship value in currency units
        """
        tier_data = self.SPONSORSHIP_TIERS[tier]
        min_value = tier_data["min"]
        max_value = tier_data["max"]

        # Calculate a factor (0.0 to 1.0) to interpolate within the tier range
        # Reputation factor (0-0.4)
        rep_factor = (club_reputation / 100.0) * 0.4

        # Position factor (0-0.3) - position 1 = 0.3, position 20 = 0.0
        pos_factor = max(0, (21 - league_position) / 20.0) * 0.3

        # Stadium factor (0-0.15)
        stadium_factor = (stadium_level / 5.0) * 0.15

        # Continental factor (0 or 0.15)
        continental_factor = 0.15 if in_continental_cup else 0.0

        # Total interpolation factor (clamped 0-1)
        interpolation = min(1.0, rep_factor + pos_factor + stadium_factor + continental_factor)

        # Calculate value within range
        value = int(min_value + (max_value - min_value) * interpolation)

        return value

    def _calculate_sponsorship_duration(
        self,
        tier: str,
        club_reputation: int,
    ) -> int:
        """
        Calculate the duration of a sponsorship deal in seasons.

        Higher-tier sponsors and more reputable clubs tend to get longer deals.

        Args:
            tier: Sponsorship tier
            club_reputation: Club reputation (1-100)

        Returns:
            Duration in seasons (1-3)
        """
        # Base duration depends on tier
        if tier == "premium":
            base_duration = 2  # Premium sponsors commit for longer
        elif tier == "large":
            base_duration = 2
        elif tier == "medium":
            base_duration = 1
        else:
            base_duration = 1

        # High reputation clubs get longer deals
        if club_reputation >= 80:
            base_duration = min(self.SPONSORSHIP_MAX_DURATION, base_duration + 1)
        elif club_reputation >= 60:
            base_duration = min(self.SPONSORSHIP_MAX_DURATION, base_duration)

        return max(self.SPONSORSHIP_MIN_DURATION, min(self.SPONSORSHIP_MAX_DURATION, base_duration))

    async def generate_sponsorship_deal(
        self,
        club_id: int,
        career_id: int,
        season: int,
        league_position: int = 10,
        in_continental_cup: bool = False,
    ) -> Dict:
        """
        Generate a new sponsorship deal for a club at the start of a season.

        The sponsorship deal is determined by the club's reputation, league position,
        stadium level, and continental cup participation. The deal provides regular
        income over its duration (1-3 seasons).

        This method should be called at the start of each season when the club's
        current sponsorship deal has expired.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Current season number (deal starts this season)
            league_position: Club's current/previous league position (1-20, default 10)
            in_continental_cup: Whether the club participates in continental competition

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - tier: Sponsorship tier (small/medium/large/premium)
                - tier_label: Human-readable tier name
                - annual_value: Total value per season
                - weekly_payment: Value divided into weekly payments
                - duration_seasons: How many seasons the deal lasts
                - start_season: Season the deal starts
                - end_season: Last season of the deal (inclusive)
                - sponsor_name: Generated sponsor name
                - factors: Dict of factors that influenced the deal

        Raises:
            ValueError: If club not found or invalid parameters
        """
        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        if not (1 <= league_position <= 20):
            raise ValueError(f"League position must be between 1 and 20, got {league_position}")

        # Get club data
        club_stmt = select(Club).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        club = result.scalar_one_or_none()

        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        # Determine sponsorship tier
        tier = self._determine_sponsorship_tier(
            club_reputation=club.reputation,
            league_position=league_position,
            stadium_level=club.stadium_level,
            in_continental_cup=in_continental_cup,
        )

        # Calculate annual value
        annual_value = self._calculate_sponsorship_value(
            tier=tier,
            club_reputation=club.reputation,
            league_position=league_position,
            stadium_level=club.stadium_level,
            in_continental_cup=in_continental_cup,
        )

        # Calculate duration
        duration = self._calculate_sponsorship_duration(
            tier=tier,
            club_reputation=club.reputation,
        )

        # Calculate weekly payment (52 weeks per season)
        weekly_payment = annual_value // 52

        # Generate sponsor name based on tier
        tier_label = self.SPONSORSHIP_TIERS[tier]["label"]
        sponsor_name = f"{tier_label} Deal (Season {season})"

        logger.info(
            f"Generated sponsorship deal: club={club_id}, tier={tier}, "
            f"annual_value={annual_value}, duration={duration} seasons, "
            f"weekly_payment={weekly_payment}"
        )

        return {
            "club_id": club_id,
            "career_id": career_id,
            "tier": tier,
            "tier_label": tier_label,
            "annual_value": annual_value,
            "weekly_payment": weekly_payment,
            "duration_seasons": duration,
            "start_season": season,
            "end_season": season + duration - 1,
            "sponsor_name": sponsor_name,
            "factors": {
                "club_reputation": club.reputation,
                "league_position": league_position,
                "stadium_level": club.stadium_level,
                "in_continental_cup": in_continental_cup,
            },
        }

    async def process_sponsorship_payment(
        self,
        club_id: int,
        career_id: int,
        season: int,
        week: int,
        sponsorship_deal: Optional[Dict] = None,
    ) -> Optional[FinancialTransaction]:
        """
        Process a weekly/monthly sponsorship payment for a club.

        This method records the sponsorship income as a SPONSORSHIP transaction.
        It should be called each week during the advance_week process.

        If no sponsorship_deal is provided, the method will attempt to calculate
        a default payment based on the club's current attributes.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Current in-game season
            week: Current in-game week (1-52)
            sponsorship_deal: Optional dict with deal details (from generate_sponsorship_deal).
                             If provided, uses the weekly_payment from the deal.
                             If None, calculates a basic payment from club attributes.

        Returns:
            The created FinancialTransaction record, or None if no payment is due

        Raises:
            ValueError: If season/week are invalid or club not found
        """
        if not (1 <= week <= 52):
            raise ValueError(f"Week must be between 1 and 52, got {week}")

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Determine payment amount
        if sponsorship_deal is not None:
            # Check if the deal is still active for this season
            if season < sponsorship_deal.get("start_season", 1):
                return None
            if season > sponsorship_deal.get("end_season", season):
                return None

            weekly_payment = sponsorship_deal.get("weekly_payment", 0)
            sponsor_name = sponsorship_deal.get("sponsor_name", "Sponsorship")
        else:
            # Calculate a basic payment from club attributes
            club_stmt = select(Club).where(Club.id == club_id)
            result = await self.db.execute(club_stmt)
            club = result.scalar_one_or_none()

            if club is None:
                raise ValueError(f"Club with id {club_id} not found")

            # Basic calculation: reputation-based annual value / 52 weeks
            # Small clubs get ~1M/season, top clubs get ~15M/season
            base_annual = 1_000_000 + (club.reputation / 100.0) * 14_000_000
            weekly_payment = int(base_annual // 52)
            sponsor_name = "Sponsorship"

        if weekly_payment <= 0:
            return None

        # Record as SPONSORSHIP income
        description = f"{sponsor_name} - Week {week} payment"

        transaction = await self.record_income(
            club_id=club_id,
            career_id=career_id,
            category=IncomeCategory.SPONSORSHIP,
            amount=weekly_payment,
            description=description,
            season=season,
            week=week,
        )

        logger.info(
            f"Processed sponsorship payment: club={club_id}, amount={weekly_payment}, "
            f"season={season}, week={week}"
        )

        return transaction

    async def get_current_sponsorship(
        self,
        club_id: int,
        career_id: int,
        season: Optional[int] = None,
    ) -> Dict:
        """
        Get the current sponsorship details for a club.

        Returns a summary of sponsorship income received, including total payments
        this season and estimated annual value based on recent payments.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Optional season to query (defaults to latest season with payments)

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - season: Season queried
                - total_sponsorship_income: Total sponsorship income this season
                - payment_count: Number of sponsorship payments this season
                - average_weekly_payment: Average weekly payment amount
                - estimated_annual_value: Projected annual value (average * 52)
                - has_active_sponsorship: Whether any sponsorship payments exist
        """
        # Build query conditions
        conditions = [
            FinancialTransaction.club_id == club_id,
            FinancialTransaction.career_id == career_id,
            FinancialTransaction.transaction_type == TransactionType.INCOME.value,
            FinancialTransaction.category == IncomeCategory.SPONSORSHIP.value,
        ]

        if season is not None:
            conditions.append(FinancialTransaction.season == season)

        # Query sponsorship transactions
        stmt = (
            select(
                sql_func.coalesce(sql_func.sum(FinancialTransaction.amount), 0).label("total"),
                sql_func.count(FinancialTransaction.id).label("count"),
            )
            .where(and_(*conditions))
        )

        result = await self.db.execute(stmt)
        row = result.one()

        total_income = int(row.total)
        payment_count = int(row.count)

        # Calculate averages
        average_weekly = total_income // payment_count if payment_count > 0 else 0
        estimated_annual = average_weekly * 52 if average_weekly > 0 else 0

        return {
            "club_id": club_id,
            "career_id": career_id,
            "season": season if season is not None else "all",
            "total_sponsorship_income": total_income,
            "payment_count": payment_count,
            "average_weekly_payment": average_weekly,
            "estimated_annual_value": estimated_annual,
            "has_active_sponsorship": payment_count > 0,
        }

    # --- Persistent Sponsorship Deal Management (Task 11.8) ---
    # The methods below persist active sponsorship deals to the database so
    # that weekly payouts and end-of-season renewals work consistently across
    # the advance_week career progression.

    async def get_active_sponsorship_deal(
        self,
        club_id: int,
        career_id: int,
        season: int,
    ):
        """
        Return the currently active sponsorship deal covering the given season.

        A deal is considered active if `is_active` is True and the season
        falls within the deal's start_season..end_season range. If multiple
        rows match (which should not occur under normal operation), the most
        recently created one is returned.

        Args:
            club_id: ID of the club.
            career_id: ID of the career.
            season: Season to check coverage for.

        Returns:
            The matching SponsorshipDeal ORM object or None if no active deal
            covers the given season.
        """
        from app.models.sponsorship_deal import SponsorshipDeal

        stmt = (
            select(SponsorshipDeal)
            .where(
                and_(
                    SponsorshipDeal.club_id == club_id,
                    SponsorshipDeal.career_id == career_id,
                    SponsorshipDeal.is_active == True,  # noqa: E712
                    SponsorshipDeal.start_season <= season,
                    SponsorshipDeal.end_season >= season,
                )
            )
            .order_by(SponsorshipDeal.created_at.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_sponsorship_deal(
        self,
        club_id: int,
        career_id: int,
        season: int,
        league_position: int = 10,
        in_continental_cup: bool = False,
    ):
        """
        Generate a new sponsorship deal and persist it to the database.

        Any other active deals for the same club/career are deactivated first
        so that exactly one active deal exists at a time.

        Args:
            club_id: ID of the club.
            career_id: ID of the career.
            season: The season the new deal starts in.
            league_position: Club's previous-season league position (1-20).
            in_continental_cup: Whether the club is in a continental cup.

        Returns:
            The persisted SponsorshipDeal ORM object.

        Raises:
            ValueError: If parameters are invalid or the club is not found.
        """
        from app.models.sponsorship_deal import SponsorshipDeal

        # Generate the deal terms using the existing pure-logic helper.
        deal_dict = await self.generate_sponsorship_deal(
            club_id=club_id,
            career_id=career_id,
            season=season,
            league_position=league_position,
            in_continental_cup=in_continental_cup,
        )

        # Deactivate any currently-active deals for this club/career so we
        # never have overlapping active deals.
        existing_stmt = select(SponsorshipDeal).where(
            and_(
                SponsorshipDeal.club_id == club_id,
                SponsorshipDeal.career_id == career_id,
                SponsorshipDeal.is_active == True,  # noqa: E712
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        for existing in existing_result.scalars().all():
            existing.is_active = False

        deal = SponsorshipDeal(
            club_id=club_id,
            career_id=career_id,
            tier=deal_dict["tier"],
            sponsor_name=deal_dict["sponsor_name"],
            annual_value=deal_dict["annual_value"],
            weekly_payment=deal_dict["weekly_payment"],
            duration_seasons=deal_dict["duration_seasons"],
            start_season=deal_dict["start_season"],
            end_season=deal_dict["end_season"],
            is_active=True,
        )
        self.db.add(deal)
        await self.db.flush()

        logger.info(
            f"Created sponsorship deal: club={club_id}, career={career_id}, "
            f"tier={deal.tier}, annual_value={deal.annual_value}, "
            f"seasons={deal.start_season}-{deal.end_season}"
        )

        return deal

    async def renew_sponsorship_if_expired(
        self,
        club_id: int,
        career_id: int,
        season: int,
        league_position: int = 10,
        in_continental_cup: bool = False,
    ) -> Dict:
        """
        Ensure the club has an active sponsorship deal covering `season`.

        If the existing deal has expired (end_season < season) or no deal
        exists, a fresh deal is generated and persisted. This implements the
        annual renewal cycle described in Requirement 8.8.

        Args:
            club_id: ID of the club.
            career_id: ID of the career.
            season: Current season.
            league_position: Previous-season league position used to value the deal.
            in_continental_cup: Whether the club participates in a continental cup.

        Returns:
            Dict with:
                - renewed: Whether a new deal was created.
                - deal: dict representation of the active deal (existing or new).
                - reason: Human-readable explanation.
        """
        active = await self.get_active_sponsorship_deal(
            club_id=club_id, career_id=career_id, season=season
        )

        if active is not None:
            return {
                "renewed": False,
                "deal": active.to_dict(),
                "reason": (
                    f"Existing deal still active "
                    f"(seasons {active.start_season}-{active.end_season})."
                ),
            }

        new_deal = await self.create_sponsorship_deal(
            club_id=club_id,
            career_id=career_id,
            season=season,
            league_position=league_position,
            in_continental_cup=in_continental_cup,
        )

        return {
            "renewed": True,
            "deal": new_deal.to_dict(),
            "reason": (
                f"No active deal covered season {season}; "
                f"signed new {new_deal.tier} deal "
                f"running until season {new_deal.end_season}."
            ),
        }

    # --- 5-Season Financial History Tracking (Task 11.10) ---
    # Implements Requirement 8.10: "THE Finance_Module SHALL track and display
    # a 5-season financial history chart."

    # Trend analysis thresholds
    TREND_IMPROVING_THRESHOLD = 0.05  # 5% improvement considered "improving"
    TREND_DECLINING_THRESHOLD = -0.05  # 5% decline considered "declining"

    async def get_financial_history(
        self,
        club_id: int,
        career_id: int,
        num_seasons: int = 5,
    ) -> Dict:
        """
        Get financial history over the last N seasons for trend analysis and display.

        Provides per-season financial data including income/expenditure totals,
        net profit/loss, end-of-season balance, category breakdowns, and trend
        analysis. Used for the financial summary screen and board evaluation.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            num_seasons: Number of seasons to include (default 5, max 10)

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - num_seasons_requested: Number of seasons requested
                - num_seasons_available: Number of seasons with data
                - seasons: List of per-season financial data (most recent first)
                - trend_analysis: Overall trend assessment
                - summary: Aggregate summary across all included seasons

        Raises:
            ValueError: If num_seasons is not between 1 and 10
        """
        from app.models.season_deficit_record import SeasonDeficitRecord

        if not (1 <= num_seasons <= 10):
            raise ValueError(f"num_seasons must be between 1 and 10, got {num_seasons}")

        # 1. Determine which seasons have data by finding distinct seasons
        distinct_seasons_stmt = (
            select(FinancialTransaction.season)
            .where(
                and_(
                    FinancialTransaction.club_id == club_id,
                    FinancialTransaction.career_id == career_id,
                )
            )
            .distinct()
            .order_by(FinancialTransaction.season.desc())
            .limit(num_seasons)
        )
        seasons_result = await self.db.execute(distinct_seasons_stmt)
        available_seasons = [row[0] for row in seasons_result.all()]

        if not available_seasons:
            return {
                "club_id": club_id,
                "career_id": career_id,
                "num_seasons_requested": num_seasons,
                "num_seasons_available": 0,
                "seasons": [],
                "trend_analysis": {
                    "overall_trend": "stable",
                    "income_trend": "stable",
                    "expenditure_trend": "stable",
                    "net_profit_trend": "stable",
                    "description": "No financial history available.",
                },
                "summary": {
                    "total_income_all_seasons": 0,
                    "total_expenditure_all_seasons": 0,
                    "total_net_profit_loss": 0,
                    "average_season_income": 0,
                    "average_season_expenditure": 0,
                    "average_season_net": 0,
                },
            }

        # 2. Get balance sheet data for each season
        season_data_list = []
        for season_num in sorted(available_seasons):
            # Get balance sheet for this season
            balance_sheet = await self.get_balance_sheet(
                club_id=club_id,
                career_id=career_id,
                season=season_num,
            )

            # Get end-of-season balance from SeasonDeficitRecord if available
            deficit_stmt = select(SeasonDeficitRecord).where(
                and_(
                    SeasonDeficitRecord.club_id == club_id,
                    SeasonDeficitRecord.career_id == career_id,
                    SeasonDeficitRecord.season == season_num,
                )
            )
            deficit_result = await self.db.execute(deficit_stmt)
            deficit_record = deficit_result.scalar_one_or_none()

            balance_at_end = (
                deficit_record.balance_at_season_end
                if deficit_record is not None
                else None
            )

            season_entry = {
                "season": season_num,
                "total_income": balance_sheet["total_income"],
                "total_expenditure": balance_sheet["total_expenditure"],
                "net_profit_loss": balance_sheet["net_balance"],
                "balance_at_season_end": balance_at_end,
                "transaction_count": balance_sheet["transaction_count"],
                "income_breakdown": balance_sheet["income"],
                "expenditure_breakdown": balance_sheet["expenditure"],
            }
            season_data_list.append(season_entry)

        # Sort by season descending (most recent first) for the response
        season_data_list_desc = sorted(
            season_data_list, key=lambda x: x["season"], reverse=True
        )

        # 3. Calculate trend analysis (using chronological order)
        trend_analysis = self._calculate_trend_analysis(season_data_list)

        # 4. Calculate aggregate summary
        total_income_all = sum(s["total_income"] for s in season_data_list)
        total_expenditure_all = sum(s["total_expenditure"] for s in season_data_list)
        total_net = total_income_all - total_expenditure_all
        num_available = len(season_data_list)

        summary = {
            "total_income_all_seasons": total_income_all,
            "total_expenditure_all_seasons": total_expenditure_all,
            "total_net_profit_loss": total_net,
            "average_season_income": (
                total_income_all // num_available if num_available > 0 else 0
            ),
            "average_season_expenditure": (
                total_expenditure_all // num_available if num_available > 0 else 0
            ),
            "average_season_net": (
                total_net // num_available if num_available > 0 else 0
            ),
        }

        return {
            "club_id": club_id,
            "career_id": career_id,
            "num_seasons_requested": num_seasons,
            "num_seasons_available": num_available,
            "seasons": season_data_list_desc,
            "trend_analysis": trend_analysis,
            "summary": summary,
        }

    def _calculate_trend_analysis(self, season_data: List[Dict]) -> Dict:
        """
        Calculate trend analysis from chronologically ordered season data.

        Compares the most recent season(s) against earlier seasons to determine
        if finances are improving, declining, or stable.

        Args:
            season_data: List of season data dicts, ordered chronologically
                         (oldest first)

        Returns:
            Dict containing:
                - overall_trend: "improving", "declining", or "stable"
                - income_trend: "improving", "declining", or "stable"
                - expenditure_trend: "improving", "declining", or "stable"
                - net_profit_trend: "improving", "declining", or "stable"
                - description: Human-readable trend description
        """
        if len(season_data) < 2:
            return {
                "overall_trend": "stable",
                "income_trend": "stable",
                "expenditure_trend": "stable",
                "net_profit_trend": "stable",
                "description": (
                    "Insufficient data for trend analysis (need at least 2 seasons)."
                ),
            }

        # Compare the last two seasons for trend direction
        recent = season_data[-1]
        previous = season_data[-2]

        # Income trend
        income_trend = self._determine_trend(
            previous["total_income"], recent["total_income"]
        )

        # Expenditure trend (lower is better, so invert the logic)
        expenditure_trend = self._determine_trend(
            previous["total_expenditure"],
            recent["total_expenditure"],
            invert=True,
        )

        # Net profit trend
        net_profit_trend = self._determine_trend(
            previous["net_profit_loss"], recent["net_profit_loss"]
        )

        # Overall trend is based on net profit trend primarily
        overall_trend = net_profit_trend

        # Generate description
        description = self._generate_trend_description(
            overall_trend=overall_trend,
            income_trend=income_trend,
            expenditure_trend=expenditure_trend,
            net_profit_trend=net_profit_trend,
            recent=recent,
            previous=previous,
        )

        return {
            "overall_trend": overall_trend,
            "income_trend": income_trend,
            "expenditure_trend": expenditure_trend,
            "net_profit_trend": net_profit_trend,
            "description": description,
        }

    def _determine_trend(
        self,
        previous_value: int,
        current_value: int,
        invert: bool = False,
    ) -> str:
        """
        Determine if a metric is improving, declining, or stable.

        Args:
            previous_value: Value from the previous season
            current_value: Value from the current/recent season
            invert: If True, a decrease is considered "improving" (used for expenditure)

        Returns:
            "improving", "declining", or "stable"
        """
        if previous_value == 0 and current_value == 0:
            return "stable"

        if previous_value == 0:
            # Can't calculate percentage change from zero
            if current_value > 0:
                return "declining" if invert else "improving"
            elif current_value < 0:
                return "improving" if invert else "declining"
            return "stable"

        change_ratio = (current_value - previous_value) / abs(previous_value)

        if change_ratio > self.TREND_IMPROVING_THRESHOLD:
            return "declining" if invert else "improving"
        elif change_ratio < self.TREND_DECLINING_THRESHOLD:
            return "improving" if invert else "declining"
        else:
            return "stable"

    def _generate_trend_description(
        self,
        overall_trend: str,
        income_trend: str,
        expenditure_trend: str,
        net_profit_trend: str,
        recent: Dict,
        previous: Dict,
    ) -> str:
        """
        Generate a human-readable description of the financial trend.

        Args:
            overall_trend: Overall trend direction
            income_trend: Income trend direction
            expenditure_trend: Expenditure trend direction
            net_profit_trend: Net profit trend direction
            recent: Most recent season data
            previous: Previous season data

        Returns:
            Human-readable trend description string
        """
        recent_net = recent["net_profit_loss"]
        previous_net = previous["net_profit_loss"]
        net_change = recent_net - previous_net

        if overall_trend == "improving":
            base = "Club finances are improving."
            if income_trend == "improving":
                base += " Income has increased."
            if expenditure_trend == "improving":
                base += " Spending has been reduced."
            if net_change > 0:
                base += f" Net profit improved by {net_change:,}."
        elif overall_trend == "declining":
            base = "Club finances are declining."
            if income_trend == "declining":
                base += " Income has decreased."
            if expenditure_trend == "declining":
                base += " Spending has increased."
            if net_change < 0:
                base += f" Net profit worsened by {abs(net_change):,}."
        else:
            base = "Club finances are stable with no significant changes."

        return base

    # --- Financial Deficit Consequences (Task 11.9) ---
    # Implements Requirement 8.9: "IF the club is in financial deficit for 3
    # consecutive in-game seasons, THEN THE Finance_Module SHALL trigger a board
    # takeover event with consequences for the player-manager's job security."

    # Consequence levels based on consecutive deficit seasons
    DEFICIT_CONSEQUENCE_WARNING = "warning"
    DEFICIT_CONSEQUENCE_TRANSFER_EMBARGO = "transfer_embargo"
    DEFICIT_CONSEQUENCE_POINTS_DEDUCTION = "points_deduction"
    DEFICIT_CONSEQUENCE_FORCED_SALES = "forced_sales"

    async def record_season_end_financial_status(
        self,
        club_id: int,
        career_id: int,
        season: int,
    ) -> Dict:
        """
        Record whether a season ended in financial deficit for a club.

        This method should be called at the end of each season to record the
        club's financial status. It checks the current balance and creates a
        SeasonDeficitRecord.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Season number that just ended

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - season: Season recorded
                - ended_in_deficit: Whether the season ended in deficit
                - balance_at_season_end: Balance at end of season
                - record_id: ID of the created record

        Raises:
            ValueError: If season is not positive or club not found
        """
        from app.models.season_deficit_record import SeasonDeficitRecord

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Get current club balance
        club_stmt = select(Club.balance).where(Club.id == club_id)
        result = await self.db.execute(club_stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            raise ValueError(f"Club with id {club_id} not found")

        ended_in_deficit = balance < 0

        # Check if a record already exists for this season
        existing_stmt = select(SeasonDeficitRecord).where(
            and_(
                SeasonDeficitRecord.club_id == club_id,
                SeasonDeficitRecord.career_id == career_id,
                SeasonDeficitRecord.season == season,
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record is not None:
            # Update existing record
            existing_record.ended_in_deficit = ended_in_deficit
            existing_record.balance_at_season_end = balance
            await self.db.flush()
            record_id = existing_record.id
        else:
            # Create new record
            record = SeasonDeficitRecord(
                club_id=club_id,
                career_id=career_id,
                season=season,
                ended_in_deficit=ended_in_deficit,
                balance_at_season_end=balance,
            )
            self.db.add(record)
            await self.db.flush()
            record_id = record.id

        logger.info(
            f"Recorded season-end financial status: club={club_id}, career={career_id}, "
            f"season={season}, in_deficit={ended_in_deficit}, balance={balance}"
        )

        return {
            "club_id": club_id,
            "career_id": career_id,
            "season": season,
            "ended_in_deficit": ended_in_deficit,
            "balance_at_season_end": balance,
            "record_id": record_id,
        }

    async def get_deficit_status(
        self,
        club_id: int,
        career_id: int,
    ) -> Dict:
        """
        Get the current deficit streak and active consequences for a club.

        Examines the SeasonDeficitRecord history to determine how many consecutive
        seasons the club has ended in deficit (counting backwards from the most
        recent recorded season).

        Args:
            club_id: ID of the club
            career_id: ID of the career

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - consecutive_deficit_seasons: Number of consecutive seasons in deficit
                - current_consequence: Active consequence level (or None)
                - consequence_description: Human-readable description
                - deficit_history: List of recent season records
                - is_currently_in_deficit: Whether the club is currently in deficit
        """
        from app.models.season_deficit_record import SeasonDeficitRecord

        # Get all deficit records ordered by season descending
        stmt = (
            select(SeasonDeficitRecord)
            .where(
                and_(
                    SeasonDeficitRecord.club_id == club_id,
                    SeasonDeficitRecord.career_id == career_id,
                )
            )
            .order_by(SeasonDeficitRecord.season.desc())
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        # Count consecutive deficit seasons from most recent
        consecutive_deficit_seasons = 0
        for record in records:
            if record.ended_in_deficit:
                consecutive_deficit_seasons += 1
            else:
                break

        # Determine current consequence level
        current_consequence = self._get_consequence_for_streak(consecutive_deficit_seasons)
        consequence_description = self._get_consequence_description(
            consecutive_deficit_seasons, current_consequence
        )

        # Build deficit history (last 5 seasons)
        deficit_history = [
            {
                "season": r.season,
                "ended_in_deficit": r.ended_in_deficit,
                "balance_at_season_end": r.balance_at_season_end,
                "consequence_applied": r.consequence_applied,
            }
            for r in records[:5]
        ]

        # Check if currently in deficit
        club_stmt = select(Club.balance).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        current_balance = club_result.scalar_one_or_none()
        is_currently_in_deficit = (current_balance is not None and current_balance < 0)

        return {
            "club_id": club_id,
            "career_id": career_id,
            "consecutive_deficit_seasons": consecutive_deficit_seasons,
            "current_consequence": current_consequence,
            "consequence_description": consequence_description,
            "deficit_history": deficit_history,
            "is_currently_in_deficit": is_currently_in_deficit,
        }

    async def check_deficit_consequences(
        self,
        club_id: int,
        career_id: int,
        season: int,
    ) -> Dict:
        """
        Check and apply deficit consequences based on consecutive deficit seasons.

        This method should be called after record_season_end_financial_status to
        determine and apply the appropriate consequence.

        Consequence escalation:
        - 0 seasons in deficit: No consequences
        - 1 season in deficit: Warning to player-manager
        - 2 consecutive seasons: Transfer embargo (cannot buy players)
        - 3+ consecutive seasons: Points deduction or forced player sales

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: The season that just ended (used to update the record)

        Returns:
            Dict containing:
                - club_id: Club ID
                - career_id: Career ID
                - season: Season checked
                - consecutive_deficit_seasons: Current streak count
                - consequence_applied: Consequence applied (or None)
                - consequence_description: Human-readable description
                - actions_taken: List of actions taken as a result
                - requires_attention: Whether the player-manager needs to act

        Raises:
            ValueError: If season is not positive
        """
        from app.models.season_deficit_record import SeasonDeficitRecord

        if season < 1:
            raise ValueError(f"Season must be positive, got {season}")

        # Get current deficit status
        status = await self.get_deficit_status(club_id, career_id)
        consecutive = status["consecutive_deficit_seasons"]

        # Determine consequence
        consequence = self._get_consequence_for_streak(consecutive)
        description = self._get_consequence_description(consecutive, consequence)
        actions_taken = []
        requires_attention = False

        if consequence == self.DEFICIT_CONSEQUENCE_WARNING:
            actions_taken.append("Warning issued to player-manager about financial deficit")
            requires_attention = True

        elif consequence == self.DEFICIT_CONSEQUENCE_TRANSFER_EMBARGO:
            actions_taken.append(
                "Transfer embargo imposed: club cannot purchase new players"
            )
            actions_taken.append(
                "Club must sell players or increase revenue to lift embargo"
            )
            requires_attention = True

        elif consequence in (
            self.DEFICIT_CONSEQUENCE_POINTS_DEDUCTION,
            self.DEFICIT_CONSEQUENCE_FORCED_SALES,
        ):
            actions_taken.append(
                "Severe financial penalty: points deduction applied"
            )
            actions_taken.append(
                "Board may force sale of highest-value players to recover finances"
            )
            actions_taken.append(
                "Manager's job security is at risk due to prolonged financial mismanagement"
            )
            requires_attention = True

        # Update the season record with the consequence applied
        if consequence is not None:
            update_stmt = select(SeasonDeficitRecord).where(
                and_(
                    SeasonDeficitRecord.club_id == club_id,
                    SeasonDeficitRecord.career_id == career_id,
                    SeasonDeficitRecord.season == season,
                )
            )
            update_result = await self.db.execute(update_stmt)
            record = update_result.scalar_one_or_none()
            if record is not None:
                record.consequence_applied = consequence
                await self.db.flush()

        logger.info(
            f"Deficit consequences checked: club={club_id}, career={career_id}, "
            f"season={season}, consecutive={consecutive}, consequence={consequence}"
        )

        return {
            "club_id": club_id,
            "career_id": career_id,
            "season": season,
            "consecutive_deficit_seasons": consecutive,
            "consequence_applied": consequence,
            "consequence_description": description,
            "actions_taken": actions_taken,
            "requires_attention": requires_attention,
        }

    def _get_consequence_for_streak(self, consecutive_deficit_seasons: int) -> str:
        """
        Determine the consequence level for a given deficit streak.

        Args:
            consecutive_deficit_seasons: Number of consecutive seasons in deficit

        Returns:
            Consequence string or None if no consequence
        """
        if consecutive_deficit_seasons >= 3:
            return self.DEFICIT_CONSEQUENCE_POINTS_DEDUCTION
        elif consecutive_deficit_seasons == 2:
            return self.DEFICIT_CONSEQUENCE_TRANSFER_EMBARGO
        elif consecutive_deficit_seasons == 1:
            return self.DEFICIT_CONSEQUENCE_WARNING
        else:
            return None

    def _get_consequence_description(
        self,
        consecutive_deficit_seasons: int,
        consequence: str,
    ) -> str:
        """
        Get a human-readable description of the current consequence.

        Args:
            consecutive_deficit_seasons: Number of consecutive seasons in deficit
            consequence: The consequence level

        Returns:
            Human-readable description string
        """
        if consequence is None:
            return "Club finances are in order. No deficit consequences."

        if consequence == self.DEFICIT_CONSEQUENCE_WARNING:
            return (
                f"WARNING: The club has been in financial deficit for "
                f"{consecutive_deficit_seasons} season. The board urges immediate "
                f"action to restore financial stability. Continued deficit will "
                f"result in a transfer embargo next season."
            )

        if consequence == self.DEFICIT_CONSEQUENCE_TRANSFER_EMBARGO:
            return (
                f"TRANSFER EMBARGO: The club has been in deficit for "
                f"{consecutive_deficit_seasons} consecutive seasons. The club is "
                f"banned from purchasing new players until finances are restored. "
                f"If the deficit continues next season, severe penalties will follow."
            )

        if consequence in (
            self.DEFICIT_CONSEQUENCE_POINTS_DEDUCTION,
            self.DEFICIT_CONSEQUENCE_FORCED_SALES,
        ):
            return (
                f"SEVERE PENALTY: The club has been in deficit for "
                f"{consecutive_deficit_seasons} consecutive seasons. A points "
                f"deduction has been applied and the board may force the sale of "
                f"players. The manager's position is under serious threat."
            )

        return "Unknown consequence status."
