"""
SquadPlayer Model - Junction table linking careers to players (squad composition)
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, CheckConstraint, Index, 
    DateTime, ForeignKey, Date, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class SquadStatus(str, enum.Enum):
    """Squad status enumeration"""
    KEY_PLAYER = "KEY_PLAYER"
    FIRST_TEAM = "FIRST_TEAM"
    ROTATION = "ROTATION"
    BACKUP = "BACKUP"
    NOT_NEEDED = "NOT_NEEDED"


class SquadPlayer(Base):
    """
    SquadPlayer junction table linking Career and Player models.
    
    Represents the squad composition for each career save, implementing the
    many-to-many relationship between careers and players. This table tracks
    all squad management data including contracts, morale, playing time, and
    squad status.
    
    Key Features:
        - Junction table for Career <-> Player many-to-many relationship
        - Squad size validation (18-40 players per club)
        - Matchday squad limit (18 players: 11 starters + 7 substitutes)
        - Player contract tracking (expiry date, wage, release clause)
        - Squad status (Key Player, First Team, Rotation, Backup, Not Needed)
        - Player morale (1-100)
        - Playing time tracking
        - Contract months remaining
        - Squad number (shirt number)
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career
        player_id: Foreign key to Player
        
        Contract Information:
            contract_start_date: Date when contract started
            contract_end_date: Date when contract expires
            wage: Weekly wage amount
            release_clause: Optional release clause amount
            contract_months_remaining: Calculated months until contract expires
        
        Squad Management:
            squad_status: Player's squad status (KEY_PLAYER, FIRST_TEAM, etc.)
            squad_number: Shirt number (1-99)
            morale: Player morale (1-100)
        
        Playing Time:
            appearances: Total appearances for the club
            goals: Total goals scored
            assists: Total assists
            minutes_played: Total minutes played
            yellow_cards: Total yellow cards received
            red_cards: Total red cards received
        
        Timestamps:
            joined_date: Date when player joined the squad
            created_at: Timestamp when record was created
            updated_at: Timestamp when record was last updated
    """
    
    __tablename__ = "squad_players"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Career"
    )
    
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Player"
    )
    
    # Contract Information
    contract_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date when contract started"
    )
    
    contract_end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date when contract expires"
    )
    
    wage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Weekly wage amount"
    )
    
    release_clause: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Optional release clause amount"
    )
    
    contract_months_remaining: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Calculated months until contract expires"
    )
    
    # Squad Management
    squad_status: Mapped[SquadStatus] = mapped_column(
        SQLEnum(SquadStatus, name="squad_status_enum", create_constraint=True),
        nullable=False,
        default=SquadStatus.FIRST_TEAM,
        server_default=SquadStatus.FIRST_TEAM.value,
        comment="Player's squad status"
    )
    
    squad_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Shirt number (1-99)"
    )
    
    morale: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default="70",
        comment="Player morale (1-100)"
    )
    
    # Transfer Listing
    is_listed_for_sale: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether player is listed for sale"
    )
    
    asking_price: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Asking price when listed for sale (NULL if not listed)"
    )
    
    # Playing Time Statistics
    appearances: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total appearances for the club"
    )
    
    goals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total goals scored"
    )
    
    assists: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total assists"
    )
    
    minutes_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total minutes played"
    )
    
    yellow_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total yellow cards received"
    )
    
    red_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total red cards received"
    )
    
    # Timestamps
    joined_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=func.current_date(),
        comment="Date when player joined the squad"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when record was last updated"
    )
    
    # Relationships (will be populated when related models are updated)
    # career: Mapped["Career"] = relationship("Career", back_populates="squad_players")
    # player: Mapped["Player"] = relationship("Player", back_populates="squad_players")
    
    # Check constraints and indexes
    __table_args__ = (
        # Unique constraint: one player can only be in one career's squad once
        Index('idx_squad_players_career_player_unique', 'career_id', 'player_id', unique=True),
        
        # Unique constraint: squad number must be unique within a career
        Index('idx_squad_players_career_squad_number_unique', 'career_id', 'squad_number', unique=True),
        
        # Wage constraint (non-negative)
        CheckConstraint('wage >= 0', name='check_wage_non_negative'),
        
        # Release clause constraint (non-negative if set)
        CheckConstraint('release_clause IS NULL OR release_clause >= 0', name='check_release_clause_non_negative'),
        
        # Contract months remaining constraint (non-negative if set)
        CheckConstraint('contract_months_remaining IS NULL OR contract_months_remaining >= 0', name='check_contract_months_non_negative'),
        
        # Squad number constraint (1-99)
        CheckConstraint('squad_number >= 1 AND squad_number <= 99', name='check_squad_number_range'),
        
        # Morale constraint (1-100)
        CheckConstraint('morale >= 1 AND morale <= 100', name='check_morale_range'),
        
        # Asking price constraint (non-negative if set)
        CheckConstraint('asking_price IS NULL OR asking_price >= 0', name='check_asking_price_non_negative'),
        
        # Playing time statistics constraints (non-negative)
        CheckConstraint('appearances >= 0', name='check_appearances_non_negative'),
        CheckConstraint('goals >= 0', name='check_goals_non_negative'),
        CheckConstraint('assists >= 0', name='check_assists_non_negative'),
        CheckConstraint('minutes_played >= 0', name='check_minutes_played_non_negative'),
        CheckConstraint('yellow_cards >= 0', name='check_yellow_cards_non_negative'),
        CheckConstraint('red_cards >= 0', name='check_red_cards_non_negative'),
        
        # Contract date constraint (end date must be after start date)
        CheckConstraint('contract_end_date > contract_start_date', name='check_contract_dates_valid'),
        
        # Performance indexes
        Index('idx_squad_players_career_id', 'career_id'),
        Index('idx_squad_players_player_id', 'player_id'),
        Index('idx_squad_players_squad_status', 'squad_status'),
        Index('idx_squad_players_morale', 'morale'),
        Index('idx_squad_players_contract_end_date', 'contract_end_date'),
        # Composite index for squad queries
        Index('idx_squad_players_career_status', 'career_id', 'squad_status'),
    )
    
    def __repr__(self) -> str:
        """String representation of SquadPlayer"""
        return (
            f"<SquadPlayer(id={self.id}, "
            f"career_id={self.career_id}, "
            f"player_id={self.player_id}, "
            f"squad_number={self.squad_number}, "
            f"squad_status={self.squad_status.value})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert SquadPlayer model to dictionary.
        
        Returns:
            dict: Dictionary representation of the squad player with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "player_id": self.player_id,
            # Contract information
            "contract": {
                "start_date": self.contract_start_date.isoformat() if self.contract_start_date else None,
                "end_date": self.contract_end_date.isoformat() if self.contract_end_date else None,
                "wage": self.wage,
                "release_clause": self.release_clause,
                "months_remaining": self.contract_months_remaining,
            },
            # Squad management
            "squad": {
                "status": self.squad_status.value,
                "number": self.squad_number,
                "morale": self.morale,
            },
            # Transfer listing
            "transfer_listing": {
                "is_listed_for_sale": self.is_listed_for_sale,
                "asking_price": self.asking_price,
            },
            # Playing time statistics
            "statistics": {
                "appearances": self.appearances,
                "goals": self.goals,
                "assists": self.assists,
                "minutes_played": self.minutes_played,
                "yellow_cards": self.yellow_cards,
                "red_cards": self.red_cards,
            },
            # Timestamps
            "joined_date": self.joined_date.isoformat() if self.joined_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_contract_expiring_soon(self, months_threshold: int = 6) -> bool:
        """
        Check if player's contract is expiring soon.
        
        Args:
            months_threshold: Number of months to consider as "soon" (default: 6)
        
        Returns:
            bool: True if contract expires within threshold months, False otherwise
        """
        if self.contract_months_remaining is None:
            return False
        return self.contract_months_remaining <= months_threshold
    
    def is_low_morale(self) -> bool:
        """
        Check if player has low morale.
        
        Returns:
            bool: True if morale < 40, False otherwise
        """
        return self.morale < 40
    
    def is_very_low_morale(self) -> bool:
        """
        Check if player has very low morale (transfer request threshold).
        
        Returns:
            bool: True if morale < 20, False otherwise
        """
        return self.morale < 20
    
    def is_key_player(self) -> bool:
        """
        Check if player is a key player.
        
        Returns:
            bool: True if squad_status is KEY_PLAYER, False otherwise
        """
        return self.squad_status == SquadStatus.KEY_PLAYER
    
    def is_not_needed(self) -> bool:
        """
        Check if player is not needed in the squad.
        
        Returns:
            bool: True if squad_status is NOT_NEEDED, False otherwise
        """
        return self.squad_status == SquadStatus.NOT_NEEDED
    
    def get_goals_per_appearance(self) -> float:
        """
        Calculate goals per appearance ratio.
        
        Returns:
            float: Goals per appearance, or 0.0 if no appearances
        """
        if self.appearances == 0:
            return 0.0
        return self.goals / self.appearances
    
    def get_assists_per_appearance(self) -> float:
        """
        Calculate assists per appearance ratio.
        
        Returns:
            float: Assists per appearance, or 0.0 if no appearances
        """
        if self.appearances == 0:
            return 0.0
        return self.assists / self.appearances
    
    def get_minutes_per_appearance(self) -> float:
        """
        Calculate average minutes per appearance.
        
        Returns:
            float: Average minutes per appearance, or 0.0 if no appearances
        """
        if self.appearances == 0:
            return 0.0
        return self.minutes_played / self.appearances
    
    def get_goal_contributions(self) -> int:
        """
        Calculate total goal contributions (goals + assists).
        
        Returns:
            int: Total goals and assists
        """
        return self.goals + self.assists
    
    def update_morale(self, change: int) -> None:
        """
        Update player morale by a given amount.
        Ensures morale stays within valid range (1-100).
        
        Args:
            change: Amount to change morale by (positive or negative)
        """
        self.morale = max(1, min(100, self.morale + change))
    
    def record_appearance(
        self,
        minutes: int,
        goals: int = 0,
        assists: int = 0,
        yellow_card: bool = False,
        red_card: bool = False
    ) -> None:
        """
        Record a match appearance and update statistics.
        
        Args:
            minutes: Minutes played in the match
            goals: Goals scored in the match (default: 0)
            assists: Assists in the match (default: 0)
            yellow_card: Whether player received a yellow card (default: False)
            red_card: Whether player received a red card (default: False)
        """
        self.appearances += 1
        self.minutes_played += minutes
        self.goals += goals
        self.assists += assists
        if yellow_card:
            self.yellow_cards += 1
        if red_card:
            self.red_cards += 1
    
    def calculate_contract_months_remaining(self, current_date: date) -> int:
        """
        Calculate months remaining on contract from a given date.
        Updates the contract_months_remaining field.
        
        Args:
            current_date: Current date to calculate from
        
        Returns:
            int: Months remaining on contract
        """
        if current_date >= self.contract_end_date:
            self.contract_months_remaining = 0
            return 0
        
        # Calculate months difference
        months = (
            (self.contract_end_date.year - current_date.year) * 12
            + (self.contract_end_date.month - current_date.month)
        )
        
        self.contract_months_remaining = max(0, months)
        return self.contract_months_remaining
    
    def extend_contract(self, years: int, new_wage: Optional[int] = None) -> None:
        """
        Extend player contract by a number of years.
        
        Args:
            years: Number of years to extend contract
            new_wage: Optional new weekly wage (if None, keeps current wage)
        """
        from dateutil.relativedelta import relativedelta
        
        self.contract_end_date = self.contract_end_date + relativedelta(years=years)
        
        if new_wage is not None:
            self.wage = new_wage
    
    def list_for_sale(self, asking_price: int) -> None:
        """
        List player for sale with an asking price.
        
        Args:
            asking_price: The asking price for the player
        
        Raises:
            ValueError: If asking_price is negative
        """
        if asking_price < 0:
            raise ValueError("Asking price cannot be negative")
        
        self.is_listed_for_sale = True
        self.asking_price = asking_price
    
    def unlist_from_sale(self) -> None:
        """
        Remove player from sale listing.
        """
        self.is_listed_for_sale = False
        self.asking_price = None
    
    def is_listed(self) -> bool:
        """
        Check if player is currently listed for sale.
        
        Returns:
            bool: True if player is listed for sale, False otherwise
        """
        return self.is_listed_for_sale
