"""
UCLTie Model - Represents a single tie (one-leg or two-legged) in the UCL knockout bracket
"""

from typing import Optional
from sqlalchemy import (
    String, Integer,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UCLTie(Base):
    """
    UCLTie model representing a single tie in the UEFA Champions League
    knockout bracket.

    Most rounds (knockout_playoff, round_of_16, quarter_final, semi_final)
    are two-legged. The ``home_participant_id`` is the higher-seeded club
    and plays the SECOND leg at home, so:

        aggregate_home = leg1_home_score + leg2_away_score
        aggregate_away = leg1_away_score + leg2_home_score

    The final is a single match — only ``leg1_home_score`` and
    ``leg1_away_score`` are populated and ``winner_decided_by`` is
    ``single_match`` (or ``extra_time`` / ``penalties``).

    ``winner_decided_by`` is a free-form ``String(20)`` column rather than
    a CHECK constraint because SQLite has limited support for CHECK
    constraints. Allowed values:
        - ``aggregate``     — winner decided by aggregate score
        - ``extra_time``    — winner decided in extra time of leg 2 / final
        - ``penalties``     — winner decided in a penalty shootout
        - ``single_match``  — final won in regulation 90 minutes

    The ``bracket_position`` column uniquely identifies a slot within a
    round so ``advance_bracket()`` can pair winners deterministically.
    """

    __tablename__ = "ucl_ties"

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

    round_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("competition_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to the competition_rounds row this tie belongs to"
    )

    # Participants — nullable because the round may be a placeholder before
    # the previous round has finished and seeded its winners.
    home_participant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ucl_participants.id"),
        nullable=True,
        comment="Higher-seeded participant; plays first leg away and second leg at home"
    )

    away_participant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ucl_participants.id"),
        nullable=True,
        comment="Lower-seeded participant; plays first leg at home and second leg away"
    )

    # Leg scores — nullable until each leg has been played.
    leg1_home_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Goals scored by the home team of leg 1 (the away_participant's stadium)"
    )

    leg1_away_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Goals scored by the away team of leg 1"
    )

    leg2_home_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Goals scored by the home team of leg 2 (the home_participant's stadium)"
    )

    leg2_away_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Goals scored by the away team of leg 2"
    )

    # Aggregate — populated when both legs are decided.
    aggregate_home: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="leg1_home_score + leg2_away_score (home_participant's total)"
    )

    aggregate_away: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="leg1_away_score + leg2_home_score (away_participant's total)"
    )

    # Outcome
    winner_participant_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ucl_participants.id"),
        nullable=True,
        comment="Participant who advances; NULL until the tie is resolved"
    )

    # Note: SQLite has limited CHECK constraint support, so this column is
    # an unconstrained String(20). Allowed values are documented in the
    # class docstring: aggregate, extra_time, penalties, single_match.
    winner_decided_by: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="How the winner was decided: aggregate, extra_time, penalties, single_match"
    )

    # Bracket slot
    bracket_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Slot within the round (1-based); used to pair winners into the next round"
    )

    # Indexes
    __table_args__ = (
        Index('idx_ucl_tie_comp', 'competition_id'),
        Index('idx_ucl_tie_round', 'round_id'),
        Index('idx_ucl_tie_round_pos', 'round_id', 'bracket_position', unique=True),
    )

    def __repr__(self) -> str:
        """String representation of UCLTie"""
        return (
            f"<UCLTie(id={self.id}, "
            f"competition_id={self.competition_id}, "
            f"round_id={self.round_id}, "
            f"bracket_position={self.bracket_position}, "
            f"winner_participant_id={self.winner_participant_id})>"
        )
