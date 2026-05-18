"""
Financial Transaction Model - Tracks all income and expenditure for clubs

This model provides a complete transaction history for club finances,
supporting the Finance_Module's balance sheet functionality.

Each transaction records:
- The club and career it belongs to
- Whether it's income or expenditure
- The category (e.g., Transfer Sales, Wages, Sponsorship)
- Amount, description, and timestamp
"""

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Enum, Text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class TransactionType(str, enum.Enum):
    """Type of financial transaction"""
    INCOME = "income"
    EXPENDITURE = "expenditure"


class IncomeCategory(str, enum.Enum):
    """Categories of income"""
    TRANSFER_SALES = "transfer_sales"
    MATCHDAY_REVENUE = "matchday_revenue"
    PRIZE_MONEY = "prize_money"
    SPONSORSHIP = "sponsorship"
    OTHER_INCOME = "other_income"


class ExpenditureCategory(str, enum.Enum):
    """Categories of expenditure"""
    WAGES = "wages"
    TRANSFER_FEES = "transfer_fees"
    INFRASTRUCTURE = "infrastructure"
    STAFF_WAGES = "staff_wages"
    OTHER_EXPENDITURE = "other_expenditure"


class FinancialTransaction(Base):
    """
    Financial transaction model for tracking all club income and expenditure.

    Implements Requirement 8.1: "THE Finance_Module SHALL maintain a club balance
    sheet with income (matchday revenue, TV rights, prize money, player sales,
    sponsorships) and expenditure (wages, transfer fees, infrastructure, staff salaries)."

    Attributes:
        id: Primary key, auto-increment
        club_id: Foreign key to clubs table
        career_id: Foreign key to careers table
        transaction_type: INCOME or EXPENDITURE
        category: Specific category within the transaction type
        amount: Transaction amount (always positive, type determines direction)
        description: Human-readable description of the transaction
        season: In-game season number
        week: In-game week number (1-52)
        created_at: Timestamp when transaction was recorded
    """

    __tablename__ = "financial_transactions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    club_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Club this transaction belongs to"
    )

    career_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Career this transaction belongs to"
    )

    # Transaction details
    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type: income or expenditure"
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Category of the transaction"
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Transaction amount (always positive)"
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="Human-readable description"
    )

    # Game time context
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="In-game season number"
    )

    week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="In-game week number (1-52)"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when transaction was recorded"
    )

    __table_args__ = (
        # Amount must be positive
        CheckConstraint('amount > 0', name='check_transaction_amount_positive'),
        # Week must be valid
        CheckConstraint('week >= 1 AND week <= 52', name='check_transaction_week_range'),
        # Season must be positive
        CheckConstraint('season >= 1', name='check_transaction_season_positive'),
        # Performance indexes
        Index('idx_financial_transactions_club_career', 'club_id', 'career_id'),
        Index('idx_financial_transactions_type', 'transaction_type'),
        Index('idx_financial_transactions_category', 'category'),
        Index('idx_financial_transactions_season_week', 'season', 'week'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialTransaction(id={self.id}, "
            f"type={self.transaction_type}, "
            f"category={self.category}, "
            f"amount={self.amount})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "club_id": self.club_id,
            "career_id": self.career_id,
            "transaction_type": self.transaction_type,
            "category": self.category,
            "amount": self.amount,
            "description": self.description,
            "season": self.season,
            "week": self.week,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
