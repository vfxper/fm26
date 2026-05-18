"""
UCLStanding Model - Represents a participant's running standings in the UCL league phase
"""

from typing import Optional
from sqlalchemy import (
    Integer,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UCLStanding(Base):
    """
    UCLStanding model representing a single participant's running standings
    during the UEFA Champions League league phase.

    One row per (competition_id, participant_id). All counters default to
    zero when the row is initialised by the generator and are updated as
    league phase matches are simulated.

    Tie-breakers (used to compute ``rank``):
        1. points DESC
        2. goal_difference DESC
        3. goals_for DESC
        4. participant.club_name ASC
    """

    __tablename__ = "ucl_standings"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign Keys
    competition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to the parent UCL competition"
    )

    participant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ucl_participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to the participant whose standings these are"
    )

    # Counters
    played: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of league phase matches played"
    )

    won: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of league phase matches won"
    )

    drawn: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of league phase matches drawn"
    )

    lost: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of league phase matches lost"
    )

    goals_for: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total goals scored in the league phase"
    )

    goals_against: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total goals conceded in the league phase"
    )

    goal_difference: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="goals_for minus goals_against"
    )

    points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total league phase points (3 per win, 1 per draw)"
    )

    rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Current rank 1-36 across all 36 league phase standings"
    )

    # Indexes
    __table_args__ = (
        Index('idx_ucl_stand_comp', 'competition_id'),
        Index('idx_ucl_stand_comp_part', 'competition_id', 'participant_id', unique=True),
    )

    def __repr__(self) -> str:
        """String representation of UCLStanding"""
        return (
            f"<UCLStanding(id={self.id}, "
            f"competition_id={self.competition_id}, "
            f"participant_id={self.participant_id}, "
            f"played={self.played}, "
            f"points={self.points}, "
            f"rank={self.rank})>"
        )
