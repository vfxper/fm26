"""
Transfer Model - Represents player transfer history and transactions
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, CheckConstraint, Index,
    DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class TransferType(str, enum.Enum):
    """Transfer type enumeration"""
    PERMANENT = "permanent"
    LOAN = "loan"
    FREE_AGENT = "free_agent"
    EMERGENCY_LOAN = "emergency_loan"


class TransferStatus(str, enum.Enum):
    """Transfer status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"


class Transfer(Base):
    """
    Transfer model representing player transfer history and transactions.
    
    Tracks all player movements between clubs including permanent transfers,
    loans, and free agent signings. Stores complete transfer details including
    fees, wages, and status progression.
    
    Transfer Types:
        - PERMANENT: Permanent transfer with transfer fee
        - LOAN: Season-long loan deal
        - FREE_AGENT: Free agent signing (no transfer fee)
        - EMERGENCY_LOAN: Emergency loan outside transfer window
    
    Transfer Status:
        - PENDING: Transfer bid submitted, awaiting response
        - ACCEPTED: Transfer bid accepted by selling club
        - REJECTED: Transfer bid rejected by selling club
        - COMPLETED: Transfer finalized, player moved to new club
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (manager executing transfer)
        player_id: Foreign key to Player (player being transferred)
        from_club_id: Foreign key to Club (selling/loaning club, NULL for free agents)
        to_club_id: Foreign key to Club (buying/receiving club)
        
        Transfer Details:
            transfer_type: Type of transfer (permanent, loan, free_agent, emergency_loan)
            transfer_status: Current status (pending, accepted, rejected, completed)
            transfer_fee: Transfer fee amount (0 for loans and free agents)
            wage_offer: Weekly wage offered to player
            contract_length: Contract length in years (for permanent transfers)
            loan_duration: Loan duration in weeks (for loan deals)
            wage_contribution: Percentage of wage paid by loaning club (0.0-1.0)
        
        Timing:
            transfer_date: Date when transfer was initiated
            completion_date: Date when transfer was completed (NULL if not completed)
            season: Season number when transfer occurred
            week: Week number when transfer occurred (1-52)
        
        Timestamps:
            created_at: Timestamp when transfer record was created
            updated_at: Timestamp when transfer record was last updated
    """
    
    __tablename__ = "transfers"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Career (manager executing transfer)"
    )
    
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Player (player being transferred)"
    )
    
    from_club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Foreign key to Club (selling/loaning club, NULL for free agents)"
    )
    
    to_club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Club (buying/receiving club)"
    )
    
    # Transfer Details
    transfer_type: Mapped[TransferType] = mapped_column(
        SQLEnum(TransferType, name="transfer_type_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Type of transfer (permanent, loan, free_agent, emergency_loan)"
    )
    
    transfer_status: Mapped[TransferStatus] = mapped_column(
        SQLEnum(TransferStatus, name="transfer_status_enum", create_constraint=True),
        nullable=False,
        default=TransferStatus.PENDING,
        server_default="pending",
        index=True,
        comment="Current status (pending, accepted, rejected, completed)"
    )
    
    transfer_fee: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Transfer fee amount (0 for loans and free agents)"
    )
    
    wage_offer: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Weekly wage offered to player"
    )
    
    contract_length: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Contract length in years (for permanent transfers)"
    )
    
    loan_duration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Loan duration in weeks (for loan deals)"
    )
    
    wage_contribution: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Percentage of wage paid by loaning club (0.0-1.0)"
    )
    
    # Timing
    transfer_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Date when transfer was initiated"
    )
    
    completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when transfer was completed (NULL if not completed)"
    )
    
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Season number when transfer occurred"
    )
    
    week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Week number when transfer occurred (1-52)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when transfer record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when transfer record was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="transfers")
    # player: Mapped["Player"] = relationship("Player", back_populates="transfers")
    # from_club: Mapped[Optional["Club"]] = relationship("Club", foreign_keys=[from_club_id])
    # to_club: Mapped["Club"] = relationship("Club", foreign_keys=[to_club_id])
    
    # Check constraints and indexes
    __table_args__ = (
        # Transfer fee constraint (non-negative)
        CheckConstraint('transfer_fee >= 0', name='check_transfer_fee_non_negative'),
        
        # Wage offer constraint (positive)
        CheckConstraint('wage_offer > 0', name='check_wage_offer_positive'),
        
        # Contract length constraint (1-5 years for permanent transfers)
        CheckConstraint(
            'contract_length IS NULL OR (contract_length >= 1 AND contract_length <= 5)',
            name='check_contract_length_range'
        ),
        
        # Loan duration constraint (positive for loan deals)
        CheckConstraint(
            'loan_duration IS NULL OR loan_duration > 0',
            name='check_loan_duration_positive'
        ),
        
        # Wage contribution constraint (0.0-1.0 for loan deals)
        CheckConstraint(
            'wage_contribution IS NULL OR (wage_contribution >= 0.0 AND wage_contribution <= 1.0)',
            name='check_wage_contribution_range'
        ),
        
        # Week constraint (1-52)
        CheckConstraint('week >= 1 AND week <= 52', name='check_week_range'),
        
        # Season constraint (positive)
        CheckConstraint('season >= 1', name='check_season_positive'),
        
        # Performance indexes
        Index('idx_transfers_career_id', 'career_id'),
        Index('idx_transfers_player_id', 'player_id'),
        Index('idx_transfers_from_club_id', 'from_club_id'),
        Index('idx_transfers_to_club_id', 'to_club_id'),
        Index('idx_transfers_transfer_type', 'transfer_type'),
        Index('idx_transfers_transfer_status', 'transfer_status'),
        Index('idx_transfers_season', 'season'),
        # Composite indexes for common query patterns
        Index('idx_transfers_career_season', 'career_id', 'season'),
        Index('idx_transfers_player_season', 'player_id', 'season'),
        Index('idx_transfers_status_career', 'transfer_status', 'career_id'),
    )
    
    def __repr__(self) -> str:
        """String representation of Transfer"""
        return (
            f"<Transfer(id={self.id}, "
            f"player_id={self.player_id}, "
            f"from_club_id={self.from_club_id}, "
            f"to_club_id={self.to_club_id}, "
            f"type={self.transfer_type.value}, "
            f"status={self.transfer_status.value}, "
            f"fee={self.transfer_fee})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Transfer model to dictionary.
        
        Returns:
            dict: Dictionary representation of the transfer with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "player_id": self.player_id,
            "from_club_id": self.from_club_id,
            "to_club_id": self.to_club_id,
            # Transfer details
            "transfer_type": self.transfer_type.value,
            "transfer_status": self.transfer_status.value,
            "transfer_fee": self.transfer_fee,
            "wage_offer": self.wage_offer,
            "contract_length": self.contract_length,
            "loan_duration": self.loan_duration,
            "wage_contribution": self.wage_contribution,
            # Timing
            "transfer_date": self.transfer_date.isoformat() if self.transfer_date else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "season": self.season,
            "week": self.week,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_pending(self) -> bool:
        """
        Check if transfer is pending approval.
        
        Returns:
            bool: True if transfer status is PENDING, False otherwise
        """
        return self.transfer_status == TransferStatus.PENDING
    
    def is_completed(self) -> bool:
        """
        Check if transfer is completed.
        
        Returns:
            bool: True if transfer status is COMPLETED, False otherwise
        """
        return self.transfer_status == TransferStatus.COMPLETED
    
    def is_loan(self) -> bool:
        """
        Check if transfer is a loan deal.
        
        Returns:
            bool: True if transfer type is LOAN or EMERGENCY_LOAN, False otherwise
        """
        return self.transfer_type in (TransferType.LOAN, TransferType.EMERGENCY_LOAN)
    
    def is_permanent(self) -> bool:
        """
        Check if transfer is a permanent transfer.
        
        Returns:
            bool: True if transfer type is PERMANENT, False otherwise
        """
        return self.transfer_type == TransferType.PERMANENT
    
    def is_free_agent(self) -> bool:
        """
        Check if transfer is a free agent signing.
        
        Returns:
            bool: True if transfer type is FREE_AGENT, False otherwise
        """
        return self.transfer_type == TransferType.FREE_AGENT
    
    def get_total_cost(self) -> int:
        """
        Calculate total cost of transfer including fee and wages.
        
        For permanent transfers: transfer_fee + (wage_offer * 52 * contract_length)
        For loan deals: wage_contribution * wage_offer * loan_duration
        For free agents: wage_offer * 52 * contract_length
        
        Returns:
            int: Total cost of the transfer
        """
        if self.is_permanent():
            if self.contract_length:
                return self.transfer_fee + (self.wage_offer * 52 * self.contract_length)
            return self.transfer_fee
        elif self.is_loan():
            if self.loan_duration and self.wage_contribution is not None:
                return int(self.wage_contribution * self.wage_offer * self.loan_duration)
            return 0
        elif self.is_free_agent():
            if self.contract_length:
                return self.wage_offer * 52 * self.contract_length
            return 0
        return 0
    
    def accept(self) -> None:
        """Update transfer status to ACCEPTED."""
        self.transfer_status = TransferStatus.ACCEPTED
    
    def reject(self) -> None:
        """Update transfer status to REJECTED."""
        self.transfer_status = TransferStatus.REJECTED
    
    def complete(self) -> None:
        """
        Mark transfer as COMPLETED and set completion date.
        """
        self.transfer_status = TransferStatus.COMPLETED
        self.completion_date = func.now()
    
    def get_wage_cost_per_week(self) -> int:
        """
        Calculate weekly wage cost for the buying/receiving club.
        
        For permanent transfers and free agents: full wage_offer
        For loan deals: wage_contribution * wage_offer
        
        Returns:
            int: Weekly wage cost
        """
        if self.is_loan() and self.wage_contribution is not None:
            return int(self.wage_contribution * self.wage_offer)
        return self.wage_offer
