"""
TrainingSchedule Model - Represents player training assignments and schedules
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


class TrainingFocus(str, enum.Enum):
    """Training focus area enumeration"""
    GENERAL = "general"
    FITNESS = "fitness"
    TACTICS = "tactics"
    ATTACKING = "attacking"
    DEFENDING = "defending"
    SET_PIECES = "set_pieces"
    INDIVIDUAL_TECHNICAL = "individual_technical"
    INDIVIDUAL_MENTAL = "individual_mental"
    REHABILITATION = "rehabilitation"  # Automatic for injured players


class TrainingIntensity(str, enum.Enum):
    """Training intensity enumeration"""
    LIGHT = "light"
    NORMAL = "normal"
    HEAVY = "heavy"


class TrainingSchedule(Base):
    """
    TrainingSchedule model representing player training assignments and schedules.
    
    Tracks weekly training assignments for each player in a career, supporting the
    Training_Module functionality. Each record represents a player's training focus
    for a specific week, enabling attribute development tracking and training history.
    
    Training Focus Areas (8 + rehabilitation):
        - GENERAL: General training across all attributes
        - FITNESS: Physical attributes (stamina, pace, endurance, strength)
        - TACTICS: Tactical attributes (positioning, anticipation, decisions)
        - ATTACKING: Attacking attributes (finishing, dribbling, passing)
        - DEFENDING: Defensive attributes (tackling, marking, heading)
        - SET_PIECES: Set piece attributes (corners, free kicks, penalties)
        - INDIVIDUAL_TECHNICAL: Technical attributes (technique, first touch, dribbling)
        - INDIVIDUAL_MENTAL: Mental attributes (composure, concentration, determination)
        - REHABILITATION: Automatic assignment for injured players
    
    Training Intensity (team-wide setting):
        - LIGHT: Lower injury risk, slower attribute development
        - NORMAL: Balanced injury risk and attribute development
        - HEAVY: Higher injury risk, faster attribute development
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (career context)
        player_id: Foreign key to Player (player being trained)
        squad_player_id: Foreign key to SquadPlayer (player in squad context)
        
        Training Assignment:
            training_focus: Training focus area for this week
            training_intensity: Training intensity level (team-wide setting)
            season: Season number when training occurred
            week: Week number when training occurred (1-52)
        
        Progress Tracking:
            consecutive_weeks: Number of consecutive weeks in this focus area
            attribute_improvements: JSON text field storing attribute changes
            is_injured: Flag indicating if player is injured (auto-assigned to rehabilitation)
        
        Timestamps:
            created_at: Timestamp when training schedule was created
            updated_at: Timestamp when training schedule was last updated
    """
    
    __tablename__ = "training_schedules"
    
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
        comment="Foreign key to Player (player being trained)"
    )
    
    squad_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("squad_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to SquadPlayer (player in squad context)"
    )
    
    # Training Assignment
    training_focus: Mapped[TrainingFocus] = mapped_column(
        SQLEnum(TrainingFocus, name="training_focus_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Training focus area for this week"
    )
    
    training_intensity: Mapped[TrainingIntensity] = mapped_column(
        SQLEnum(TrainingIntensity, name="training_intensity_enum", create_constraint=True),
        nullable=False,
        default=TrainingIntensity.NORMAL,
        server_default="normal",
        comment="Training intensity level (team-wide setting)"
    )
    
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Season number when training occurred"
    )
    
    week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Week number when training occurred (1-52)"
    )
    
    # Progress Tracking
    consecutive_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of consecutive weeks in this focus area"
    )
    
    attribute_improvements: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing attribute changes"
    )
    
    is_injured: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Flag indicating if player is injured (auto-assigned to rehabilitation)"
    )
    
    previous_training_focus: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="Previous training focus before injury (restored on recovery)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when training schedule was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when training schedule was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="training_schedules")
    # player: Mapped["Player"] = relationship("Player", back_populates="training_schedules")
    # squad_player: Mapped["SquadPlayer"] = relationship("SquadPlayer", back_populates="training_schedules")
    
    # Check constraints and indexes
    __table_args__ = (
        # Unique constraint: one training schedule per player per week per season per career
        Index(
            'idx_training_schedules_career_player_season_week_unique',
            'career_id', 'squad_player_id', 'season', 'week',
            unique=True
        ),
        
        # Week constraint (1-52)
        CheckConstraint('week >= 1 AND week <= 52', name='check_week_range'),
        
        # Season constraint (positive)
        CheckConstraint('season >= 1', name='check_season_positive'),
        
        # Consecutive weeks constraint (positive)
        CheckConstraint('consecutive_weeks >= 1', name='check_consecutive_weeks_positive'),
        
        # Performance indexes
        Index('idx_training_schedules_career_id', 'career_id'),
        Index('idx_training_schedules_player_id', 'player_id'),
        Index('idx_training_schedules_squad_player_id', 'squad_player_id'),
        Index('idx_training_schedules_training_focus', 'training_focus'),
        Index('idx_training_schedules_season', 'season'),
        Index('idx_training_schedules_is_injured', 'is_injured'),
        # Composite indexes for common query patterns
        Index('idx_training_schedules_career_season', 'career_id', 'season'),
        Index('idx_training_schedules_career_season_week', 'career_id', 'season', 'week'),
        Index('idx_training_schedules_player_season', 'player_id', 'season'),
        Index('idx_training_schedules_squad_player_focus', 'squad_player_id', 'training_focus'),
    )
    
    def __repr__(self) -> str:
        """String representation of TrainingSchedule"""
        return (
            f"<TrainingSchedule(id={self.id}, "
            f"player_id={self.player_id}, "
            f"focus={self.training_focus.value}, "
            f"season={self.season}, "
            f"week={self.week}, "
            f"consecutive_weeks={self.consecutive_weeks})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert TrainingSchedule model to dictionary.
        
        Returns:
            dict: Dictionary representation of the training schedule with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "player_id": self.player_id,
            "squad_player_id": self.squad_player_id,
            # Training assignment
            "training_focus": self.training_focus.value,
            "training_intensity": self.training_intensity.value,
            "season": self.season,
            "week": self.week,
            # Progress tracking
            "consecutive_weeks": self.consecutive_weeks,
            "attribute_improvements": self.attribute_improvements,
            "is_injured": self.is_injured,
            "previous_training_focus": self.previous_training_focus,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_rehabilitation(self) -> bool:
        """
        Check if training focus is rehabilitation.
        
        Returns:
            bool: True if training_focus is REHABILITATION, False otherwise
        """
        return self.training_focus == TrainingFocus.REHABILITATION
    
    def is_fitness_training(self) -> bool:
        """
        Check if training focus is fitness.
        
        Returns:
            bool: True if training_focus is FITNESS, False otherwise
        """
        return self.training_focus == TrainingFocus.FITNESS
    
    def is_light_intensity(self) -> bool:
        """
        Check if training intensity is light.
        
        Returns:
            bool: True if training_intensity is LIGHT, False otherwise
        """
        return self.training_intensity == TrainingIntensity.LIGHT
    
    def is_heavy_intensity(self) -> bool:
        """
        Check if training intensity is heavy.
        
        Returns:
            bool: True if training_intensity is HEAVY, False otherwise
        """
        return self.training_intensity == TrainingIntensity.HEAVY
    
    def is_ready_for_improvement(self, player_age: int) -> bool:
        """
        Check if player is ready for attribute improvement.
        
        Players under 24 years old improve after 4 consecutive weeks in same focus.
        
        Args:
            player_age: Current age of the player
        
        Returns:
            bool: True if player is ready for improvement, False otherwise
        """
        return player_age < 24 and self.consecutive_weeks >= 4
    
    def should_decline_attributes(self, player_age: int) -> bool:
        """
        Check if player should have attributes decline.
        
        Players over 30 years old decline if not assigned to Fitness training
        for 8 consecutive weeks.
        
        Args:
            player_age: Current age of the player
        
        Returns:
            bool: True if player should decline, False otherwise
        """
        return (
            player_age > 30
            and not self.is_fitness_training()
            and self.consecutive_weeks >= 8
        )
    
    def get_injury_risk_multiplier(self) -> float:
        """
        Calculate injury risk multiplier based on training intensity.
        
        Returns:
            float: Injury risk multiplier
                - LIGHT: 0.7 (30% reduction)
                - NORMAL: 1.0 (baseline)
                - HEAVY: 1.5 (50% increase)
        """
        if self.is_light_intensity():
            return 0.7
        elif self.is_heavy_intensity():
            return 1.5
        else:
            return 1.0
    
    def get_development_rate_multiplier(self) -> float:
        """
        Calculate attribute development rate multiplier based on training intensity.
        
        Returns:
            float: Development rate multiplier
                - LIGHT: 0.8 (20% slower)
                - NORMAL: 1.0 (baseline)
                - HEAVY: 1.2 (20% faster)
        """
        if self.is_light_intensity():
            return 0.8
        elif self.is_heavy_intensity():
            return 1.2
        else:
            return 1.0
    
    def increment_consecutive_weeks(self) -> None:
        """Increment consecutive weeks counter."""
        self.consecutive_weeks += 1
    
    def reset_consecutive_weeks(self) -> None:
        """Reset consecutive weeks counter to 1 (when focus changes)."""
        self.consecutive_weeks = 1
    
    def set_injured(self) -> None:
        """
        Mark player as injured and auto-assign to rehabilitation.
        
        Saves the current training focus so it can be restored on recovery.
        """
        # Save current focus before switching to rehabilitation
        if self.training_focus != TrainingFocus.REHABILITATION:
            self.previous_training_focus = self.training_focus.value
        self.is_injured = True
        self.training_focus = TrainingFocus.REHABILITATION
        self.reset_consecutive_weeks()
    
    def clear_injured(self) -> None:
        """
        Clear injured flag when player recovers.
        
        Restores the previous training focus if one was saved,
        otherwise defaults to GENERAL training.
        """
        self.is_injured = False
        # Restore previous training focus or default to GENERAL
        if self.previous_training_focus:
            try:
                self.training_focus = TrainingFocus(self.previous_training_focus)
            except ValueError:
                self.training_focus = TrainingFocus.GENERAL
        else:
            self.training_focus = TrainingFocus.GENERAL
        self.previous_training_focus = None
        self.reset_consecutive_weeks()
    
    def get_affected_attributes(self) -> list[str]:
        """
        Get list of player attributes affected by current training focus.
        
        Returns:
            list[str]: List of attribute names affected by this training focus
        """
        focus_attribute_map = {
            TrainingFocus.GENERAL: [
                "technique", "passing", "stamina", "decisions", "positioning"
            ],
            TrainingFocus.FITNESS: [
                "stamina", "pace", "endurance", "strength", "acceleration", "agility"
            ],
            TrainingFocus.TACTICS: [
                "positioning", "anticipation", "decisions", "teamwork", "vision"
            ],
            TrainingFocus.ATTACKING: [
                "finishing", "dribbling", "passing", "off_the_ball", "composure"
            ],
            TrainingFocus.DEFENDING: [
                "tackling", "marking", "heading", "positioning", "concentration"
            ],
            TrainingFocus.SET_PIECES: [
                "corners", "free_kicks", "penalty", "long_throws"
            ],
            TrainingFocus.INDIVIDUAL_TECHNICAL: [
                "technique", "first_touch", "dribbling", "passing", "crossing"
            ],
            TrainingFocus.INDIVIDUAL_MENTAL: [
                "composure", "concentration", "determination", "bravery", "leadership"
            ],
            TrainingFocus.REHABILITATION: []  # No attribute improvements during rehab
        }
        
        return focus_attribute_map.get(self.training_focus, [])
