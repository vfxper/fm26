"""
Match Event Model - Represents individual events during a match
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, CheckConstraint, Index, 
    DateTime, ForeignKey, Text, Enum as SQLEnum, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class EventType(str, enum.Enum):
    """Event type enumeration"""
    PASS = "pass"
    SHOT = "shot"
    TACKLE = "tackle"
    FOUL = "foul"
    GOAL = "goal"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    SUBSTITUTION = "substitution"
    CORNER = "corner"
    FREE_KICK = "free_kick"
    PENALTY = "penalty"
    OFFSIDE = "offside"
    SAVE = "save"
    BLOCK = "block"
    INTERCEPTION = "interception"
    CLEARANCE = "clearance"
    CROSS = "cross"
    DRIBBLE = "dribble"
    HEADER = "header"
    THROW_IN = "throw_in"
    GOAL_KICK = "goal_kick"
    INJURY = "injury"


class TeamSide(str, enum.Enum):
    """Team side enumeration"""
    HOME = "home"
    AWAY = "away"


class MatchEvent(Base):
    """
    Match Event model representing individual events during a match.
    
    This table stores the event stream for match simulation, capturing
    every significant action that occurs during a match with precise
    timing, player involvement, and spatial information.
    
    Event Identification:
        - match_id: Foreign key to Match
        - event_type: Type of event (pass, shot, goal, etc.)
        - team: Which team performed the event (home/away)
    
    Timing:
        - minute: Match minute (0-90+)
        - second: Second within the minute (0-59)
    
    Player Involvement:
        - player_id: Primary player involved in the event
        - target_player_id: Secondary player (pass recipient, tackled player, etc.)
    
    Spatial Information:
        - position_x: X coordinate on pitch (0-100, 0=own goal, 100=opponent goal)
        - position_y: Y coordinate on pitch (0-100, 0=left touchline, 100=right touchline)
    
    Event Outcome:
        - success: Whether the event was successful (completed pass, scored shot, etc.)
    
    Event Metadata:
        - metadata: JSON text field for event-specific data
          Examples:
            - Shot: {"shot_power": 85, "shot_type": "header", "goalkeeper_id": 123}
            - Pass: {"pass_distance": 25, "pass_type": "through_ball"}
            - Card: {"reason": "dangerous_tackle", "minute_shown": 45}
            - Substitution: {"player_off_id": 10, "player_on_id": 15}
    
    Attributes:
        id: Primary key, auto-increment
        match_id: Foreign key to Match
        event_type: Type of event
        team: Team that performed the event
        minute: Match minute
        second: Second within minute
        player_id: Primary player involved
        target_player_id: Secondary player (optional)
        position_x: X coordinate on pitch
        position_y: Y coordinate on pitch
        success: Event success flag
        metadata: JSON text field for event-specific data
        created_at: Timestamp when event was created
    """
    
    __tablename__ = "match_events"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    match_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Match"
    )
    
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Primary player involved in the event"
    )
    
    target_player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Secondary player involved (pass recipient, tackled player, etc.)"
    )
    
    # Event Identification
    event_type: Mapped[str] = mapped_column(
        SQLEnum(EventType),
        nullable=False,
        index=True,
        comment="Type of event (pass, shot, goal, etc.)"
    )
    
    team: Mapped[str] = mapped_column(
        SQLEnum(TeamSide),
        nullable=False,
        index=True,
        comment="Team that performed the event (home/away)"
    )
    
    # Timing
    minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Match minute (0-90+)"
    )
    
    second: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Second within the minute (0-59)"
    )
    
    # Spatial Information
    position_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="X coordinate on pitch (0-100, 0=own goal, 100=opponent goal)"
    )
    
    position_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Y coordinate on pitch (0-100, 0=left touchline, 100=right touchline)"
    )
    
    # Event Outcome
    success: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether the event was successful"
    )
    
    # Event Metadata (JSON text field)
    event_metadata: Mapped[Optional[str]] = mapped_column(
        "metadata",  # Column name in database
        Text,
        nullable=True,
        comment="JSON text field for event-specific data"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when event was created"
    )
    
    # Relationships (will be populated when related models are available)
    # match: Mapped["Match"] = relationship("Match", back_populates="events")
    # player: Mapped["Player"] = relationship("Player", foreign_keys=[player_id], back_populates="events")
    # target_player: Mapped[Optional["Player"]] = relationship("Player", foreign_keys=[target_player_id])
    
    # Check constraints and indexes
    __table_args__ = (
        # Minute constraint (non-negative)
        CheckConstraint('minute >= 0', name='check_minute_non_negative'),
        
        # Second constraint (0-59)
        CheckConstraint('second >= 0 AND second <= 59', name='check_second_range'),
        
        # Position constraints (0-100)
        CheckConstraint('position_x >= 0 AND position_x <= 100', name='check_position_x_range'),
        CheckConstraint('position_y >= 0 AND position_y <= 100', name='check_position_y_range'),
        
        # Performance indexes
        Index('idx_match_events_match_id', 'match_id'),
        Index('idx_match_events_player_id', 'player_id'),
        Index('idx_match_events_target_player_id', 'target_player_id'),
        Index('idx_match_events_event_type', 'event_type'),
        Index('idx_match_events_team', 'team'),
        Index('idx_match_events_minute', 'minute'),
        # Composite indexes for common queries
        Index('idx_match_events_match_time', 'match_id', 'minute', 'second'),
        Index('idx_match_events_match_type', 'match_id', 'event_type'),
        Index('idx_match_events_player_type', 'player_id', 'event_type'),
        Index('idx_match_events_match_team', 'match_id', 'team'),
    )
    
    def __repr__(self) -> str:
        """String representation of MatchEvent"""
        return (
            f"<MatchEvent(id={self.id}, "
            f"match_id={self.match_id}, "
            f"event_type={self.event_type}, "
            f"team={self.team}, "
            f"minute={self.minute}, "
            f"player_id={self.player_id})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert MatchEvent model to dictionary.
        
        Returns:
            dict: Dictionary representation of the match event with all attributes
        """
        return {
            "id": self.id,
            "match_id": self.match_id,
            "event_type": self.event_type,
            "team": self.team,
            "timing": {
                "minute": self.minute,
                "second": self.second,
            },
            "players": {
                "player_id": self.player_id,
                "target_player_id": self.target_player_id,
            },
            "position": {
                "x": self.position_x,
                "y": self.position_y,
            },
            "success": self.success,
            "metadata": self.event_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_time_string(self) -> str:
        """
        Get event time as a string.
        
        Returns:
            str: Event time string (e.g., "45:30")
        """
        return f"{self.minute}:{self.second:02d}"
    
    def is_goal_event(self) -> bool:
        """
        Check if the event is a goal.
        
        Returns:
            bool: True if goal, False otherwise
        """
        return self.event_type == EventType.GOAL
    
    def is_card_event(self) -> bool:
        """
        Check if the event is a card (yellow or red).
        
        Returns:
            bool: True if card event, False otherwise
        """
        return self.event_type in (EventType.YELLOW_CARD, EventType.RED_CARD)
    
    def is_substitution_event(self) -> bool:
        """
        Check if the event is a substitution.
        
        Returns:
            bool: True if substitution, False otherwise
        """
        return self.event_type == EventType.SUBSTITUTION
    
    def is_set_piece_event(self) -> bool:
        """
        Check if the event is a set piece.
        
        Returns:
            bool: True if set piece event, False otherwise
        """
        return self.event_type in (
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.THROW_IN,
            EventType.GOAL_KICK
        )
    
    def is_attacking_event(self) -> bool:
        """
        Check if the event is an attacking action.
        
        Returns:
            bool: True if attacking event, False otherwise
        """
        return self.event_type in (
            EventType.SHOT,
            EventType.GOAL,
            EventType.CROSS,
            EventType.DRIBBLE,
            EventType.HEADER
        )
    
    def is_defensive_event(self) -> bool:
        """
        Check if the event is a defensive action.
        
        Returns:
            bool: True if defensive event, False otherwise
        """
        return self.event_type in (
            EventType.TACKLE,
            EventType.SAVE,
            EventType.BLOCK,
            EventType.INTERCEPTION,
            EventType.CLEARANCE
        )
    
    def is_in_first_half(self) -> bool:
        """
        Check if the event occurred in the first half.
        
        Returns:
            bool: True if first half (0-45 minutes), False otherwise
        """
        return self.minute <= 45
    
    def is_in_second_half(self) -> bool:
        """
        Check if the event occurred in the second half.
        
        Returns:
            bool: True if second half (46-90+ minutes), False otherwise
        """
        return self.minute > 45
    
    def is_in_extra_time(self) -> bool:
        """
        Check if the event occurred in extra time.
        
        Returns:
            bool: True if extra time (90+ minutes), False otherwise
        """
        return self.minute > 90
    
    def get_position_zone(self) -> str:
        """
        Get the zone of the pitch where the event occurred.
        
        Returns:
            str: Zone description (e.g., "defensive_third", "midfield", "attacking_third")
        """
        if self.position_x < 33.33:
            return "defensive_third"
        elif self.position_x < 66.67:
            return "midfield"
        else:
            return "attacking_third"
    
    def get_position_side(self) -> str:
        """
        Get the side of the pitch where the event occurred.
        
        Returns:
            str: Side description (e.g., "left", "center", "right")
        """
        if self.position_y < 33.33:
            return "left"
        elif self.position_y < 66.67:
            return "center"
        else:
            return "right"
