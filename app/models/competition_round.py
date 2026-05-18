"""
CompetitionRound Model - Represents a single round within a competition (e.g. league phase, round of 16, final)
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Date,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CompetitionRound(Base):
    """
    CompetitionRound model representing a single round within a competition.

    Used by the UEFA Champions League module to track the lifecycle of each
    round: league_phase, knockout_playoff, round_of_16, quarter_final,
    semi_final, final. The round_order column gives a deterministic ordering
    so the generator can advance from one round to the next.

    round_type values:
        league_phase, knockout_playoff, round_of_16,
        quarter_final, semi_final, final
    """

    __tablename__ = "competition_rounds"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign Keys
    competition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to the parent competition"
    )

    # Round identity
    round_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type of round: league_phase, knockout_playoff, round_of_16, quarter_final, semi_final, final"
    )

    round_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ordinal position of the round within the competition (1-based)"
    )

    # Scheduling window
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Earliest date on which a match in this round may be played"
    )

    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Latest date on which a match in this round may be played"
    )

    # Lifecycle flag
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether all ties / matches in this round have been resolved"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="Timestamp when the round was created"
    )

    # Indexes
    __table_args__ = (
        Index('idx_comp_rounds_comp', 'competition_id'),
        Index('idx_comp_rounds_comp_order', 'competition_id', 'round_order', unique=True),
    )

    def __repr__(self) -> str:
        """String representation of CompetitionRound"""
        return (
            f"<CompetitionRound(id={self.id}, "
            f"competition_id={self.competition_id}, "
            f"round_type={self.round_type}, "
            f"round_order={self.round_order})>"
        )
