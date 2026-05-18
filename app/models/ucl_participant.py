"""
UCLParticipant Model - Represents a club taking part in a UEFA Champions League season
"""

from typing import Optional
from sqlalchemy import (
    String, Integer,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UCLParticipant(Base):
    """
    UCLParticipant model representing one of the 36 clubs participating in a
    UEFA Champions League season for a given career.

    The ``club_id`` column references the 1-based index of the club in
    ``app.data.club_budgets.CLUBS`` and is nullable for teams that are not
    present in the CLUBS list (e.g. Bodø/Glimt, Kairat). For those clubs
    only the ``club_name`` and ``country`` strings are stored.

    The ``seed`` column (1-36) is used by the Swiss-system pot draw and by
    the knockout bracket pairing.

    The ``final_rank`` column (1-36) is populated once the league phase
    finishes and drives the knockout playoff / round-of-16 draws.
    """

    __tablename__ = "ucl_participants"

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

    # Club identity
    club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="1-based index in app.data.club_budgets.CLUBS, or NULL for clubs not in CLUBS"
    )

    club_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name of the club"
    )

    country: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Country of the club (e.g. England, Spain, Germany)"
    )

    # Seeding and final classification
    seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Seed 1-36; drives Swiss-system pot draw and bracket pairing"
    )

    final_rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Final rank 1-36 after the league phase ends"
    )

    # Indexes
    __table_args__ = (
        Index('idx_ucl_part_comp', 'competition_id'),
        Index('idx_ucl_part_comp_seed', 'competition_id', 'seed', unique=True),
    )

    def __repr__(self) -> str:
        """String representation of UCLParticipant"""
        return (
            f"<UCLParticipant(id={self.id}, "
            f"competition_id={self.competition_id}, "
            f"club_name={self.club_name}, "
            f"seed={self.seed})>"
        )
