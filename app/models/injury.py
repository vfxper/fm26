"""
Injury Model - Represents player injuries and recovery tracking
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, CheckConstraint, Index,
    DateTime, ForeignKey, Enum as SQLEnum, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class InjurySeverity(str, enum.Enum):
    """Injury severity enumeration"""
    MINOR = "minor"  # 1-2 weeks
    MODERATE = "moderate"  # 3-8 weeks
    SEVERE = "severe"  # 9+ weeks


class InjuryStatus(str, enum.Enum):
    """Injury status enumeration"""
    ACTIVE = "active"  # Currently injured
    RECOVERING = "recovering"  # Returned but with sharpness penalty
    RECOVERED = "recovered"  # Fully recovered


class Injury(Base):
    """
    Injury model representing player injuries and recovery tracking.
    
    Tracks all player injuries including match injuries and training ground injuries.
    Stores complete injury details including severity, recovery timeline, and status
    progression. Supports injury history tracking for identifying injury-prone players.
    
    Injury Severity:
        - MINOR: 1-2 weeks recovery time
        - MODERATE: 3-8 weeks recovery time
        - SEVERE: 9+ weeks recovery time
    
    Injury Status:
        - ACTIVE: Player is currently injured and unavailable
        - RECOVERING: Player has returned but has match sharpness penalty (2 weeks)
        - RECOVERED: Player is fully recovered with no penalties
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (career context)
        player_id: Foreign key to Player (injured player)
        squad_player_id: Foreign key to SquadPlayer (player in squad context)
        
        Injury Details:
            injury_type: Type of injury (e.g., "Hamstring Strain", "Ankle Sprain")
            injury_description: Detailed description of the injury
            severity: Injury severity (minor, moderate, severe)
            status: Current injury status (active, recovering, recovered)
        
        Timing:
            injury_date: Date when injury occurred
            expected_recovery_date: Expected date of return to full fitness
            actual_recovery_date: Actual date when player returned (NULL if still injured)
            full_recovery_date: Date when sharpness penalty ends (NULL if not recovered)
            recovery_weeks: Number of weeks for recovery (1-2, 3-8, or 9+)
        
        Context:
            occurred_in_match_id: Foreign key to Match if injury occurred in match (NULL for training injuries)
            match_minute: Minute of match when injury occurred (NULL for training injuries)
            season: Season number when injury occurred
            week: Week number when injury occurred (1-52)
        
        Recovery Impact:
            sharpness_penalty: Match sharpness penalty percentage (0-100, typically 10%)
            is_injury_prone_flag: Flag set if player has 3+ injuries in a season
        
        Timestamps:
            created_at: Timestamp when injury record was created
            updated_at: Timestamp when injury record was last updated
    """
    
    __tablename__ = "injuries"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Career (career context)"
    )
    
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Player (injured player)"
    )
    
    squad_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("squad_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to SquadPlayer (player in squad context)"
    )
    
    # Injury Details
    injury_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of injury (e.g., 'Hamstring Strain', 'Ankle Sprain')"
    )
    
    injury_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the injury"
    )
    
    severity: Mapped[InjurySeverity] = mapped_column(
        SQLEnum(InjurySeverity, name="injury_severity_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Injury severity (minor, moderate, severe)"
    )
    
    status: Mapped[InjuryStatus] = mapped_column(
        SQLEnum(InjuryStatus, name="injury_status_enum", create_constraint=True),
        nullable=False,
        default=InjuryStatus.ACTIVE,
        server_default="active",
        index=True,
        comment="Current injury status (active, recovering, recovered)"
    )
    
    # Timing
    injury_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Date when injury occurred"
    )
    
    expected_recovery_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Expected date of return to full fitness"
    )
    
    actual_recovery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual date when player returned (NULL if still injured)"
    )
    
    full_recovery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when sharpness penalty ends (NULL if not recovered)"
    )
    
    recovery_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of weeks for recovery (1-2, 3-8, or 9+)"
    )
    
    # Context
    occurred_in_match_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign key to Match if injury occurred in match (NULL for training injuries)"
    )
    
    match_minute: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Minute of match when injury occurred (NULL for training injuries)"
    )
    
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Season number when injury occurred"
    )
    
    week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Week number when injury occurred (1-52)"
    )
    
    # Recovery Impact
    sharpness_penalty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Match sharpness penalty percentage (0-100, typically 10%)"
    )
    
    is_injury_prone_flag: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Flag set if player has 3+ injuries in a season"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when injury record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when injury record was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="injuries")
    # player: Mapped["Player"] = relationship("Player", back_populates="injuries")
    # squad_player: Mapped["SquadPlayer"] = relationship("SquadPlayer", back_populates="injuries")
    # match: Mapped[Optional["Match"]] = relationship("Match", back_populates="injuries")
    
    # Check constraints and indexes
    __table_args__ = (
        # Recovery weeks constraint (positive)
        CheckConstraint('recovery_weeks > 0', name='check_recovery_weeks_positive'),
        
        # Match minute constraint (0-120 for regular time + extra time)
        CheckConstraint(
            'match_minute IS NULL OR (match_minute >= 0 AND match_minute <= 120)',
            name='check_match_minute_range'
        ),
        
        # Week constraint (1-52)
        CheckConstraint('week >= 1 AND week <= 52', name='check_week_range'),
        
        # Season constraint (positive)
        CheckConstraint('season >= 1', name='check_season_positive'),
        
        # Sharpness penalty constraint (0-100)
        CheckConstraint(
            'sharpness_penalty >= 0 AND sharpness_penalty <= 100',
            name='check_sharpness_penalty_range'
        ),
        
        # Performance indexes
        Index('idx_injuries_career_id', 'career_id'),
        Index('idx_injuries_player_id', 'player_id'),
        Index('idx_injuries_squad_player_id', 'squad_player_id'),
        Index('idx_injuries_injury_type', 'injury_type'),
        Index('idx_injuries_severity', 'severity'),
        Index('idx_injuries_status', 'status'),
        Index('idx_injuries_injury_date', 'injury_date'),
        Index('idx_injuries_season', 'season'),
        Index('idx_injuries_occurred_in_match_id', 'occurred_in_match_id'),
        # Composite indexes for common query patterns
        Index('idx_injuries_career_season', 'career_id', 'season'),
        Index('idx_injuries_player_season', 'player_id', 'season'),
        Index('idx_injuries_status_career', 'status', 'career_id'),
        Index('idx_injuries_squad_player_status', 'squad_player_id', 'status'),
    )
    
    def __repr__(self) -> str:
        """String representation of Injury"""
        return (
            f"<Injury(id={self.id}, "
            f"player_id={self.player_id}, "
            f"type={self.injury_type}, "
            f"severity={self.severity.value}, "
            f"status={self.status.value}, "
            f"recovery_weeks={self.recovery_weeks})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Injury model to dictionary.
        
        Returns:
            dict: Dictionary representation of the injury with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "player_id": self.player_id,
            "squad_player_id": self.squad_player_id,
            # Injury details
            "injury_type": self.injury_type,
            "injury_description": self.injury_description,
            "severity": self.severity.value,
            "status": self.status.value,
            # Timing
            "injury_date": self.injury_date.isoformat() if self.injury_date else None,
            "expected_recovery_date": self.expected_recovery_date.isoformat() if self.expected_recovery_date else None,
            "actual_recovery_date": self.actual_recovery_date.isoformat() if self.actual_recovery_date else None,
            "full_recovery_date": self.full_recovery_date.isoformat() if self.full_recovery_date else None,
            "recovery_weeks": self.recovery_weeks,
            # Context
            "occurred_in_match_id": self.occurred_in_match_id,
            "match_minute": self.match_minute,
            "season": self.season,
            "week": self.week,
            # Recovery impact
            "sharpness_penalty": self.sharpness_penalty,
            "is_injury_prone_flag": self.is_injury_prone_flag,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_active(self) -> bool:
        """
        Check if injury is currently active.
        
        Returns:
            bool: True if injury status is ACTIVE, False otherwise
        """
        return self.status == InjuryStatus.ACTIVE
    
    def is_recovering(self) -> bool:
        """
        Check if player is in recovery phase with sharpness penalty.
        
        Returns:
            bool: True if injury status is RECOVERING, False otherwise
        """
        return self.status == InjuryStatus.RECOVERING
    
    def is_recovered(self) -> bool:
        """
        Check if player is fully recovered.
        
        Returns:
            bool: True if injury status is RECOVERED, False otherwise
        """
        return self.status == InjuryStatus.RECOVERED
    
    def is_minor(self) -> bool:
        """
        Check if injury is minor severity.
        
        Returns:
            bool: True if severity is MINOR, False otherwise
        """
        return self.severity == InjurySeverity.MINOR
    
    def is_moderate(self) -> bool:
        """
        Check if injury is moderate severity.
        
        Returns:
            bool: True if severity is MODERATE, False otherwise
        """
        return self.severity == InjurySeverity.MODERATE
    
    def is_severe(self) -> bool:
        """
        Check if injury is severe.
        
        Returns:
            bool: True if severity is SEVERE, False otherwise
        """
        return self.severity == InjurySeverity.SEVERE
    
    def is_match_injury(self) -> bool:
        """
        Check if injury occurred during a match.
        
        Returns:
            bool: True if occurred_in_match_id is not NULL, False otherwise
        """
        return self.occurred_in_match_id is not None
    
    def is_training_injury(self) -> bool:
        """
        Check if injury occurred during training.
        
        Returns:
            bool: True if occurred_in_match_id is NULL, False otherwise
        """
        return self.occurred_in_match_id is None
    
    def get_days_until_recovery(self) -> int:
        """
        Calculate days remaining until expected recovery.
        
        Returns:
            int: Days until expected recovery (0 if already recovered or past expected date)
        """
        if self.is_recovered() or self.actual_recovery_date:
            return 0
        
        now = datetime.now(self.expected_recovery_date.tzinfo)
        delta = self.expected_recovery_date - now
        return max(0, delta.days)
    
    def get_days_until_full_recovery(self) -> int:
        """
        Calculate days remaining until full recovery (sharpness penalty ends).
        
        Returns:
            int: Days until full recovery (0 if fully recovered or no full_recovery_date set)
        """
        if self.is_recovered() or not self.full_recovery_date:
            return 0
        
        now = datetime.now(self.full_recovery_date.tzinfo)
        delta = self.full_recovery_date - now
        return max(0, delta.days)
    
    def get_effective_ca_penalty(self) -> int:
        """
        Calculate effective CA penalty percentage based on injury status.
        
        Returns:
            int: CA penalty percentage (0-100)
                - ACTIVE: 100% (player unavailable)
                - RECOVERING: sharpness_penalty (typically 10%)
                - RECOVERED: 0%
        """
        if self.is_active():
            return 100  # Player completely unavailable
        elif self.is_recovering():
            return self.sharpness_penalty
        else:
            return 0
    
    def return_from_injury(self) -> None:
        """
        Mark player as returned from injury (enters RECOVERING status).
        Sets actual_recovery_date and calculates full_recovery_date (2 weeks later).
        """
        from datetime import timedelta
        
        self.status = InjuryStatus.RECOVERING
        self.actual_recovery_date = func.now()
        # Full recovery is 2 weeks (14 days) after return
        if isinstance(self.actual_recovery_date, datetime):
            self.full_recovery_date = self.actual_recovery_date + timedelta(days=14)
    
    def fully_recover(self) -> None:
        """
        Mark player as fully recovered (no more penalties).
        Sets status to RECOVERED and ensures full_recovery_date is set.
        """
        self.status = InjuryStatus.RECOVERED
        if not self.full_recovery_date:
            self.full_recovery_date = func.now()
    
    def set_injury_prone_flag(self) -> None:
        """
        Set the injury-prone flag for this player.
        Called when player has 3+ injuries in a season.
        """
        self.is_injury_prone_flag = True
    
    def get_recovery_progress_percentage(self) -> float:
        """
        Calculate recovery progress as a percentage.
        
        Returns:
            float: Recovery progress (0.0-100.0)
        """
        if self.is_recovered():
            return 100.0
        
        now = datetime.now(self.injury_date.tzinfo)
        total_duration = (self.expected_recovery_date - self.injury_date).total_seconds()
        elapsed = (now - self.injury_date).total_seconds()
        
        if total_duration <= 0:
            return 100.0
        
        progress = (elapsed / total_duration) * 100.0
        return min(100.0, max(0.0, progress))
