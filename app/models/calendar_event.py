"""
CalendarEvent Model - Represents a single event in the club's season calendar
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CalendarEvent(Base):
    """
    CalendarEvent model representing a single event in the club's season calendar.

    Events include matches, training sessions, meetings, deadlines, international
    breaks, medical appointments, days off, travel, and milestones. Each event has
    a priority (0-10) used for conflict resolution during scheduling.

    Event types: match, training, meeting, deadline, international, medical,
                 day_off, travel, milestone

    Priority scale:
        10 = International windows
        9  = Mandatory holiday fixtures (locked)
        8  = European competition
        6  = Domestic league
        4  = Domestic cup
        2  = Friendlies
        0  = Lowest priority
    """

    __tablename__ = "calendar_events"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to Career"
    )

    # Event core fields
    event_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of the event"
    )

    event_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type: match, training, meeting, deadline, international, medical, day_off, travel, milestone"
    )

    # Competition and club references
    competition_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Reference to competition (if match event)"
    )

    home_club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clubs.id"),
        nullable=True,
        comment="Home club for match events"
    )

    away_club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clubs.id"),
        nullable=True,
        comment="Away club for match events"
    )

    # Scheduling fields
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this event cannot be rescheduled"
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Priority 0-10, higher = more important for conflict resolution"
    )

    kick_off_time: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Kick-off time in HH:MM format (e.g. 15:00, 20:00)"
    )

    # JSON data fields
    weather_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON: {precipitation, temperature_celsius, pitch_condition}"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the event"
    )

    travel_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON: {transport_mode, departure, destination, distance_km}"
    )

    # Rescheduling audit trail
    original_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Original date before rescheduling (null if never rescheduled)"
    )

    reschedule_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for rescheduling (null if never rescheduled)"
    )

    # Soft deletion
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag - cancelled events excluded from queries"
    )

    # Template reference
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Reference to recurring template that generated this event"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="Timestamp when event was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when event was last updated"
    )

    # Indexes and constraints
    __table_args__ = (
        Index('idx_calendar_career_date', 'career_id', 'event_date'),
        Index('idx_calendar_career_type', 'career_id', 'event_type'),
        Index('idx_calendar_career_priority', 'career_id', 'priority'),
        CheckConstraint('priority >= 0 AND priority <= 10', name='check_priority_range'),
    )

    def __repr__(self) -> str:
        """String representation of CalendarEvent"""
        return (
            f"<CalendarEvent(id={self.id}, "
            f"career_id={self.career_id}, "
            f"date={self.event_date}, "
            f"type={self.event_type}, "
            f"priority={self.priority})>"
        )
