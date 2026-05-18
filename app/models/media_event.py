"""
Media Event Model - Represents media interactions like press conferences and interviews
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


class MediaEventType(str, enum.Enum):
    """Media event type enumeration"""
    PRE_MATCH_CONFERENCE = "pre_match_conference"
    POST_MATCH_CONFERENCE = "post_match_conference"
    PLAYER_INTERVIEW = "player_interview"
    MEDIA_PRESSURE = "media_pressure"
    RIVAL_COMMENT = "rival_comment"


class MediaEventStatus(str, enum.Enum):
    """Media event status enumeration"""
    PENDING = "pending"
    RESPONDED = "responded"
    EXPIRED = "expired"


class MediaEvent(Base):
    """
    Media Event model representing media interactions like press conferences and interviews.
    
    Based on Requirement 13 (Медиа и пресс-конференции), the media system includes:
    - Pre-match and post-match press conferences
    - Multiple-choice response system (3+ options)
    - Morale and reputation impact calculation
    - Media pressure event simulation
    - Media reputation score (1-100)
    - Player interview event generation
    - Board scrutiny triggers (reputation < 30)
    - News feed display
    - Press conference localization
    - Rival manager comment system
    
    Event Types:
        - PRE_MATCH_CONFERENCE: Press conference before a match
        - POST_MATCH_CONFERENCE: Press conference after a match
        - PLAYER_INTERVIEW: Player makes public statement requiring manager response
        - MEDIA_PRESSURE: Media pressure event (e.g., "Manager under pressure after 3 losses")
        - RIVAL_COMMENT: Rival manager comment requiring response
    
    Event Status:
        - PENDING: Event is waiting for manager response
        - RESPONDED: Manager has responded to the event
        - EXPIRED: Event has expired without response
    
    Response Options (JSON field):
        - Array of 3+ response options with text and impact data
        - Format: [{"text": "...", "morale_impact": {...}, "reputation_impact": ...}, ...]
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (career context)
        match_id: Optional foreign key to Match (for match-related events)
        
        Event Details:
            event_type: Type of media event
            event_question: Question or prompt text
            response_options: JSON text field storing response options
            selected_response: Index of selected response (0-based)
            event_status: Current status (pending, responded, expired)
        
        Impact Tracking:
            morale_impact: JSON text field storing morale impact per player
            reputation_impact: Manager reputation impact (-10 to +10)
            board_confidence_impact: Board confidence impact (-10 to +10)
        
        Context:
            related_player_id: Optional player ID (for player interviews)
            related_club_id: Optional club ID (for rival comments)
            event_context: JSON text field storing additional context
        
        Timestamps:
            event_date: Date when event occurred
            response_date: Date when manager responded (null if pending)
            expiry_date: Date when event expires
            created_at: Timestamp when event was created
            updated_at: Timestamp when event was last updated
    """
    
    __tablename__ = "media_events"
    
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
    
    match_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional foreign key to Match (for match-related events)"
    )
    
    # Event Details
    event_type: Mapped[MediaEventType] = mapped_column(
        SQLEnum(MediaEventType, name="media_event_type_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Type of media event"
    )
    
    event_question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Question or prompt text"
    )
    
    response_options: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON text field storing response options (array of 3+ options)"
    )
    
    selected_response: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Index of selected response (0-based, null if not responded)"
    )
    
    event_status: Mapped[MediaEventStatus] = mapped_column(
        SQLEnum(MediaEventStatus, name="media_event_status_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Current status (pending, responded, expired)"
    )
    
    # Impact Tracking
    morale_impact: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing morale impact per player"
    )
    
    reputation_impact: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Manager reputation impact (-10 to +10)"
    )
    
    board_confidence_impact: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Board confidence impact (-10 to +10)"
    )
    
    # Context
    related_player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional player ID (for player interviews)"
    )
    
    related_club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional club ID (for rival comments)"
    )
    
    event_context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing additional context"
    )
    
    # Timestamps
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Date when event occurred"
    )
    
    response_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when manager responded (null if pending)"
    )
    
    expiry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Date when event expires"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when event was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when event was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="media_events")
    # match: Mapped[Optional["Match"]] = relationship("Match", back_populates="media_events")
    # related_player: Mapped[Optional["Player"]] = relationship("Player", back_populates="media_events")
    # related_club: Mapped[Optional["Club"]] = relationship("Club", back_populates="media_events")
    
    # Check constraints and indexes
    __table_args__ = (
        # Reputation impact constraint (-10 to +10)
        CheckConstraint(
            'reputation_impact >= -10 AND reputation_impact <= 10',
            name='check_reputation_impact_range'
        ),
        
        # Board confidence impact constraint (-10 to +10)
        CheckConstraint(
            'board_confidence_impact >= -10 AND board_confidence_impact <= 10',
            name='check_board_confidence_impact_range'
        ),
        
        # Selected response constraint (non-negative if set)
        CheckConstraint(
            'selected_response IS NULL OR selected_response >= 0',
            name='check_selected_response_non_negative'
        ),
        
        # Response date constraint (must be after event date if set)
        CheckConstraint(
            'response_date IS NULL OR response_date >= event_date',
            name='check_response_date_after_event'
        ),
        
        # Expiry date constraint (must be after event date)
        CheckConstraint(
            'expiry_date >= event_date',
            name='check_expiry_date_after_event'
        ),
        
        # Status consistency constraints
        CheckConstraint(
            "(event_status = 'pending' AND selected_response IS NULL AND response_date IS NULL) OR "
            "(event_status = 'responded' AND selected_response IS NOT NULL AND response_date IS NOT NULL) OR "
            "(event_status = 'expired' AND selected_response IS NULL AND response_date IS NULL)",
            name='check_status_response_consistency'
        ),
        
        # Performance indexes
        Index('idx_media_events_career_id', 'career_id'),
        Index('idx_media_events_match_id', 'match_id'),
        Index('idx_media_events_event_type', 'event_type'),
        Index('idx_media_events_event_status', 'event_status'),
        Index('idx_media_events_related_player_id', 'related_player_id'),
        Index('idx_media_events_related_club_id', 'related_club_id'),
        Index('idx_media_events_event_date', 'event_date'),
        Index('idx_media_events_expiry_date', 'expiry_date'),
        # Composite indexes for common query patterns
        Index('idx_media_events_career_status', 'career_id', 'event_status'),
        Index('idx_media_events_career_type', 'career_id', 'event_type'),
        Index('idx_media_events_career_date', 'career_id', 'event_date'),
        Index('idx_media_events_status_expiry', 'event_status', 'expiry_date'),
    )
    
    def __repr__(self) -> str:
        """String representation of MediaEvent"""
        return (
            f"<MediaEvent(id={self.id}, "
            f"career_id={self.career_id}, "
            f"event_type={self.event_type.value}, "
            f"status={self.event_status.value})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert MediaEvent model to dictionary.
        
        Returns:
            dict: Dictionary representation of the media event with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "match_id": self.match_id,
            # Event details
            "event": {
                "type": self.event_type.value,
                "question": self.event_question,
                "response_options": self.response_options,
                "selected_response": self.selected_response,
                "status": self.event_status.value,
            },
            # Impact tracking
            "impact": {
                "morale_impact": self.morale_impact,
                "reputation_impact": self.reputation_impact,
                "board_confidence_impact": self.board_confidence_impact,
            },
            # Context
            "context": {
                "related_player_id": self.related_player_id,
                "related_club_id": self.related_club_id,
                "event_context": self.event_context,
            },
            # Timestamps
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "response_date": self.response_date.isoformat() if self.response_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_pending(self) -> bool:
        """
        Check if the event is pending response.
        
        Returns:
            bool: True if status is PENDING, False otherwise
        """
        return self.event_status == MediaEventStatus.PENDING
    
    def is_responded(self) -> bool:
        """
        Check if the event has been responded to.
        
        Returns:
            bool: True if status is RESPONDED, False otherwise
        """
        return self.event_status == MediaEventStatus.RESPONDED
    
    def is_expired(self) -> bool:
        """
        Check if the event has expired.
        
        Returns:
            bool: True if status is EXPIRED, False otherwise
        """
        return self.event_status == MediaEventStatus.EXPIRED
    
    def is_match_related(self) -> bool:
        """
        Check if the event is related to a match.
        
        Returns:
            bool: True if match_id is set, False otherwise
        """
        return self.match_id is not None
    
    def is_pre_match_conference(self) -> bool:
        """
        Check if the event is a pre-match press conference.
        
        Returns:
            bool: True if event type is PRE_MATCH_CONFERENCE, False otherwise
        """
        return self.event_type == MediaEventType.PRE_MATCH_CONFERENCE
    
    def is_post_match_conference(self) -> bool:
        """
        Check if the event is a post-match press conference.
        
        Returns:
            bool: True if event type is POST_MATCH_CONFERENCE, False otherwise
        """
        return self.event_type == MediaEventType.POST_MATCH_CONFERENCE
    
    def is_player_interview(self) -> bool:
        """
        Check if the event is a player interview.
        
        Returns:
            bool: True if event type is PLAYER_INTERVIEW, False otherwise
        """
        return self.event_type == MediaEventType.PLAYER_INTERVIEW
    
    def is_media_pressure(self) -> bool:
        """
        Check if the event is a media pressure event.
        
        Returns:
            bool: True if event type is MEDIA_PRESSURE, False otherwise
        """
        return self.event_type == MediaEventType.MEDIA_PRESSURE
    
    def is_rival_comment(self) -> bool:
        """
        Check if the event is a rival manager comment.
        
        Returns:
            bool: True if event type is RIVAL_COMMENT, False otherwise
        """
        return self.event_type == MediaEventType.RIVAL_COMMENT
    
    def has_positive_reputation_impact(self) -> bool:
        """
        Check if the event has positive reputation impact.
        
        Returns:
            bool: True if reputation_impact > 0, False otherwise
        """
        return self.reputation_impact > 0
    
    def has_negative_reputation_impact(self) -> bool:
        """
        Check if the event has negative reputation impact.
        
        Returns:
            bool: True if reputation_impact < 0, False otherwise
        """
        return self.reputation_impact < 0
    
    def has_positive_board_impact(self) -> bool:
        """
        Check if the event has positive board confidence impact.
        
        Returns:
            bool: True if board_confidence_impact > 0, False otherwise
        """
        return self.board_confidence_impact > 0
    
    def has_negative_board_impact(self) -> bool:
        """
        Check if the event has negative board confidence impact.
        
        Returns:
            bool: True if board_confidence_impact < 0, False otherwise
        """
        return self.board_confidence_impact < 0
    
    def is_overdue(self) -> bool:
        """
        Check if the event is overdue (past expiry date and still pending).
        
        Returns:
            bool: True if pending and past expiry date, False otherwise
        """
        if not self.is_pending():
            return False
        
        now = datetime.now(self.expiry_date.tzinfo)
        return now > self.expiry_date
    
    def get_time_until_expiry(self) -> int:
        """
        Calculate hours until event expires.
        
        Returns:
            int: Hours until expiry (0 if expired or already responded)
        """
        if not self.is_pending():
            return 0
        
        now = datetime.now(self.expiry_date.tzinfo)
        if now >= self.expiry_date:
            return 0
        
        delta = self.expiry_date - now
        return max(0, int(delta.total_seconds() / 3600))
    
    def respond(self, response_index: int, morale_impact: Optional[str] = None) -> None:
        """
        Record manager's response to the event.
        
        Args:
            response_index: Index of selected response (0-based)
            morale_impact: Optional JSON string with morale impact data
        """
        self.selected_response = response_index
        self.response_date = func.now()
        self.event_status = MediaEventStatus.RESPONDED
        if morale_impact:
            self.morale_impact = morale_impact
    
    def expire(self) -> None:
        """
        Mark the event as expired (no response given before expiry date).
        """
        if self.is_pending():
            self.event_status = MediaEventStatus.EXPIRED
    
    def set_reputation_impact(self, impact: int) -> None:
        """
        Set reputation impact value.
        
        Args:
            impact: Reputation impact (-10 to +10)
        """
        self.reputation_impact = max(-10, min(10, impact))
    
    def set_board_confidence_impact(self, impact: int) -> None:
        """
        Set board confidence impact value.
        
        Args:
            impact: Board confidence impact (-10 to +10)
        """
        self.board_confidence_impact = max(-10, min(10, impact))
    
    def get_event_type_display_name(self) -> str:
        """
        Get human-readable display name for the event type.
        
        Returns:
            str: Display name for the event type
        """
        display_names = {
            MediaEventType.PRE_MATCH_CONFERENCE: "Pre-Match Press Conference",
            MediaEventType.POST_MATCH_CONFERENCE: "Post-Match Press Conference",
            MediaEventType.PLAYER_INTERVIEW: "Player Interview",
            MediaEventType.MEDIA_PRESSURE: "Media Pressure",
            MediaEventType.RIVAL_COMMENT: "Rival Manager Comment",
        }
        return display_names.get(self.event_type, "Unknown Event")
    
    def get_status_display_name(self) -> str:
        """
        Get human-readable display name for the event status.
        
        Returns:
            str: Display name for the event status
        """
        display_names = {
            MediaEventStatus.PENDING: "Pending Response",
            MediaEventStatus.RESPONDED: "Responded",
            MediaEventStatus.EXPIRED: "Expired",
        }
        return display_names.get(self.event_status, "Unknown Status")
