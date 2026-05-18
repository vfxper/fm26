"""
Career Model - Represents a single-club career mode save
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, CheckConstraint, Index, 
    DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.training_schedule import TrainingIntensity


class Career(Base):
    """
    Career model representing a single-club career mode save.
    
    The Career tracks the manager's profile, club assignment, season/week progression,
    board confidence, objectives, manager reputation, manager attributes, and career
    statistics. This is the core entity for the single-club career mode where the
    player manages one club throughout the career.
    
    Manager Attributes (1-20 each):
        - tactical_knowledge: Manager's tactical understanding
        - man_management: Ability to manage player relationships
        - motivating: Ability to motivate players
        - attacking: Attacking tactical knowledge
        - defending: Defensive tactical knowledge
        - technical: Technical coaching ability
        - mental: Mental coaching ability
        - youth_development: Youth player development ability
        - board_relations: Relationship management with board
    
    Career Statistics:
        - seasons_managed: Total seasons managed in this career
        - trophies_won: Total trophies won
        - matches_won: Total matches won
        - matches_drawn: Total matches drawn
        - matches_lost: Total matches lost
        - total_transfer_spend: Total money spent on transfers
    
    Attributes:
        id: Primary key, auto-increment
        user_id: Foreign key to User (Telegram user)
        club_id: Foreign key to Club (managed club)
        manager_name: Name of the manager
        
        Season/Week Progression:
            current_season: Current season number (1-based)
            current_week: Current week in season (1-52)
        
        Board System:
            board_confidence: Board confidence level (1-100)
            board_objectives: JSON text field storing board objectives
        
        Manager Profile:
            manager_reputation: Manager reputation (1-100)
            
        Manager Attributes (1-20 each):
            tactical_knowledge
            man_management
            motivating
            attacking
            defending
            technical
            mental
            youth_development
            board_relations
        
        Career Statistics:
            seasons_managed
            trophies_won
            matches_won
            matches_drawn
            matches_lost
            total_transfer_spend
        
        Timestamps:
            save_timestamp: Last save timestamp (for auto-save system)
            created_at: Timestamp when career was created
            updated_at: Timestamp when career was last updated
    """
    
    __tablename__ = "careers"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to User (Telegram user)"
    )
    
    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Club (managed club)"
    )
    
    # Manager Profile
    manager_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of the manager"
    )
    
    # Season/Week Progression
    current_season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Current season number (1-based)"
    )
    
    current_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Current week in season (1-52)"
    )
    
    # Board System
    board_confidence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        comment="Board confidence level (1-100)"
    )
    
    board_objectives: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing board objectives"
    )
    
    # Training Settings
    training_intensity: Mapped[TrainingIntensity] = mapped_column(
        SQLEnum(TrainingIntensity, name="career_training_intensity_enum", create_constraint=True),
        nullable=False,
        default=TrainingIntensity.NORMAL,
        server_default="normal",
        comment="Team-wide training intensity setting (light, normal, heavy)"
    )
    
    # Manager Profile
    manager_reputation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        comment="Manager reputation (1-100)"
    )
    
    # Manager Attributes (1-20 each)
    tactical_knowledge: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Manager's tactical understanding (1-20)"
    )
    
    man_management: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Ability to manage player relationships (1-20)"
    )
    
    motivating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Ability to motivate players (1-20)"
    )
    
    attacking: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Attacking tactical knowledge (1-20)"
    )
    
    defending: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Defensive tactical knowledge (1-20)"
    )
    
    technical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Technical coaching ability (1-20)"
    )
    
    mental: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Mental coaching ability (1-20)"
    )
    
    youth_development: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Youth player development ability (1-20)"
    )
    
    board_relations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Relationship management with board (1-20)"
    )
    
    # Career Statistics
    seasons_managed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total seasons managed in this career"
    )
    
    trophies_won: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total trophies won"
    )
    
    matches_won: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total matches won"
    )
    
    matches_drawn: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total matches drawn"
    )
    
    matches_lost: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total matches lost"
    )
    
    total_transfer_spend: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total money spent on transfers"
    )
    
    # Timestamps
    save_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last save timestamp (for auto-save system)"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when career was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when career was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # user: Mapped["User"] = relationship("User", back_populates="careers")
    # club: Mapped["Club"] = relationship("Club", back_populates="careers")
    
    # Check constraints and indexes
    __table_args__ = (
        # Season/Week constraints
        CheckConstraint('current_season >= 1', name='check_current_season_positive'),
        CheckConstraint('current_week >= 1 AND current_week <= 52', name='check_current_week_range'),
        
        # Board confidence constraint (1-100)
        CheckConstraint('board_confidence >= 1 AND board_confidence <= 100', name='check_board_confidence_range'),
        
        # Manager reputation constraint (1-100)
        CheckConstraint('manager_reputation >= 1 AND manager_reputation <= 100', name='check_manager_reputation_range'),
        
        # Manager attribute constraints (1-20 each)
        CheckConstraint('tactical_knowledge >= 1 AND tactical_knowledge <= 20', name='check_tactical_knowledge_range'),
        CheckConstraint('man_management >= 1 AND man_management <= 20', name='check_man_management_range'),
        CheckConstraint('motivating >= 1 AND motivating <= 20', name='check_motivating_range'),
        CheckConstraint('attacking >= 1 AND attacking <= 20', name='check_attacking_range'),
        CheckConstraint('defending >= 1 AND defending <= 20', name='check_defending_range'),
        CheckConstraint('technical >= 1 AND technical <= 20', name='check_technical_range'),
        CheckConstraint('mental >= 1 AND mental <= 20', name='check_mental_range'),
        CheckConstraint('youth_development >= 1 AND youth_development <= 20', name='check_youth_development_range'),
        CheckConstraint('board_relations >= 1 AND board_relations <= 20', name='check_board_relations_range'),
        
        # Career statistics constraints (non-negative)
        CheckConstraint('seasons_managed >= 0', name='check_seasons_managed_non_negative'),
        CheckConstraint('trophies_won >= 0', name='check_trophies_won_non_negative'),
        CheckConstraint('matches_won >= 0', name='check_matches_won_non_negative'),
        CheckConstraint('matches_drawn >= 0', name='check_matches_drawn_non_negative'),
        CheckConstraint('matches_lost >= 0', name='check_matches_lost_non_negative'),
        CheckConstraint('total_transfer_spend >= 0', name='check_total_transfer_spend_non_negative'),
        
        # Performance indexes
        Index('idx_careers_user_id', 'user_id'),
        Index('idx_careers_club_id', 'club_id'),
        Index('idx_careers_save_timestamp', 'save_timestamp'),
        # Composite index for user's active careers
        Index('idx_careers_user_season', 'user_id', 'current_season'),
    )
    
    def __repr__(self) -> str:
        """String representation of Career"""
        return (
            f"<Career(id={self.id}, "
            f"manager_name={self.manager_name}, "
            f"club_id={self.club_id}, "
            f"season={self.current_season}, "
            f"week={self.current_week})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Career model to dictionary.
        
        Returns:
            dict: Dictionary representation of the career with all attributes
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "club_id": self.club_id,
            "manager_name": self.manager_name,
            # Season/Week
            "progression": {
                "current_season": self.current_season,
                "current_week": self.current_week,
            },
            # Board System
            "board": {
                "confidence": self.board_confidence,
                "objectives": self.board_objectives,
            },
            # Training Settings
            "training_intensity": self.training_intensity.value,
            # Manager Profile
            "manager": {
                "reputation": self.manager_reputation,
                "attributes": {
                    "tactical_knowledge": self.tactical_knowledge,
                    "man_management": self.man_management,
                    "motivating": self.motivating,
                    "attacking": self.attacking,
                    "defending": self.defending,
                    "technical": self.technical,
                    "mental": self.mental,
                    "youth_development": self.youth_development,
                    "board_relations": self.board_relations,
                },
            },
            # Career Statistics
            "statistics": {
                "seasons_managed": self.seasons_managed,
                "trophies_won": self.trophies_won,
                "matches_won": self.matches_won,
                "matches_drawn": self.matches_drawn,
                "matches_lost": self.matches_lost,
                "total_transfer_spend": self.total_transfer_spend,
            },
            # Timestamps
            "save_timestamp": self.save_timestamp.isoformat() if self.save_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_total_matches(self) -> int:
        """
        Calculate total matches played.
        
        Returns:
            int: Total matches (won + drawn + lost)
        """
        return self.matches_won + self.matches_drawn + self.matches_lost
    
    def get_win_percentage(self) -> float:
        """
        Calculate win percentage.
        
        Returns:
            float: Win percentage (0-100), or 0 if no matches played
        """
        total_matches = self.get_total_matches()
        if total_matches == 0:
            return 0.0
        return (self.matches_won / total_matches) * 100
    
    def get_average_manager_attribute(self) -> float:
        """
        Calculate average manager attribute across all 9 attributes.
        
        Returns:
            float: Average manager attribute (1-20)
        """
        attributes = [
            self.tactical_knowledge,
            self.man_management,
            self.motivating,
            self.attacking,
            self.defending,
            self.technical,
            self.mental,
            self.youth_development,
            self.board_relations,
        ]
        return sum(attributes) / len(attributes)
    
    def is_board_confident(self) -> bool:
        """
        Check if the board has high confidence in the manager.
        
        Returns:
            bool: True if board confidence >= 60, False otherwise
        """
        return self.board_confidence >= 60
    
    def is_under_pressure(self) -> bool:
        """
        Check if the manager is under pressure from the board.
        
        Returns:
            bool: True if board confidence < 40, False otherwise
        """
        return self.board_confidence < 40
    
    def update_match_statistics(self, result: str) -> None:
        """
        Update career match statistics based on match result.
        
        Args:
            result: Match result ('win', 'draw', 'loss')
        """
        if result == 'win':
            self.matches_won += 1
        elif result == 'draw':
            self.matches_drawn += 1
        elif result == 'loss':
            self.matches_lost += 1
    
    def add_trophy(self) -> None:
        """Increment trophies won counter."""
        self.trophies_won += 1
    
    def add_transfer_spend(self, amount: int) -> None:
        """
        Add to total transfer spend.
        
        Args:
            amount: Transfer fee amount to add
        """
        self.total_transfer_spend += amount
    
    def advance_week(self) -> None:
        """
        Advance career by one week.
        Handles season rollover when week exceeds 52.
        """
        self.current_week += 1
        if self.current_week > 52:
            self.current_week = 1
            self.current_season += 1
            self.seasons_managed += 1
