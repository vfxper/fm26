"""
RecurringTemplate Model - Defines weekly recurring event patterns
"""

from datetime import datetime
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RecurringTemplate(Base):
    """
    RecurringTemplate model defining weekly recurring event patterns.

    Templates allow managers to set up a default weekly schedule (e.g. training
    types per day) that can be applied to any month. When applied, the template
    generates individual CalendarEvent records, skipping days that already have
    matches, international breaks, or locked events.

    day_assignments JSON format:
        {"monday": "tactical_theory", "tuesday": "practice_match",
         "wednesday": "rest", "thursday": "set_pieces", "friday": "light_warmup",
         "saturday": null, "sunday": null}
    """

    __tablename__ = "recurring_templates"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to Career"
    )

    # Template definition
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Template name (e.g. 'Match Week', 'Recovery Week')"
    )

    day_assignments: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON object mapping day names to activity types"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this template is currently active"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="Timestamp when template was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when template was last updated"
    )

    # Indexes
    __table_args__ = (
        Index('idx_template_career', 'career_id'),
    )

    def __repr__(self) -> str:
        """String representation of RecurringTemplate"""
        return (
            f"<RecurringTemplate(id={self.id}, "
            f"career_id={self.career_id}, "
            f"name={self.name}, "
            f"active={self.is_active})>"
        )
