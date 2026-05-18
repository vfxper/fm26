"""
Season Deficit Record Model - Tracks whether a club ended a season in financial deficit.

Used by the Finance_Module to track consecutive deficit seasons and apply
escalating consequences per Requirement 8.9.

Consequences:
- 1 season in deficit: Warning to player-manager
- 2 consecutive seasons in deficit: Transfer embargo (cannot buy players)
- 3 consecutive seasons in deficit: Points deduction or forced player sales
"""

from datetime import datetime
from sqlalchemy import Integer, Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SeasonDeficitRecord(Base):
    """
    Records whether a club ended a specific season in financial deficit.

    One record per club per career per season. Used to determine consecutive
    deficit streaks and apply escalating consequences.

    Attributes:
        id: Primary key, auto-increment
        club_id: ID of the club
        career_id: ID of the career
        season: Season number this record covers
        ended_in_deficit: Whether the club's balance was negative at season end
        balance_at_season_end: The club's balance when the season ended
        consequence_applied: What consequence was applied (if any)
        created_at: Timestamp when record was created
    """

    __tablename__ = "season_deficit_records"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    club_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Club this record belongs to"
    )

    career_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Career this record belongs to"
    )

    # Season data
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Season number this record covers"
    )

    ended_in_deficit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the club ended this season in deficit"
    )

    balance_at_season_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Club balance at the end of the season"
    )

    consequence_applied: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="Consequence applied: warning, transfer_embargo, points_deduction, forced_sales"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when record was created"
    )

    __table_args__ = (
        # Unique constraint: one record per club per career per season
        Index(
            'idx_season_deficit_unique',
            'club_id', 'career_id', 'season',
            unique=True
        ),
        # Performance indexes
        Index('idx_season_deficit_club_career', 'club_id', 'career_id'),
        Index('idx_season_deficit_season', 'season'),
    )

    def __repr__(self) -> str:
        return (
            f"<SeasonDeficitRecord(id={self.id}, "
            f"club_id={self.club_id}, "
            f"career_id={self.career_id}, "
            f"season={self.season}, "
            f"ended_in_deficit={self.ended_in_deficit})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "club_id": self.club_id,
            "career_id": self.career_id,
            "season": self.season,
            "ended_in_deficit": self.ended_in_deficit,
            "balance_at_season_end": self.balance_at_season_end,
            "consequence_applied": self.consequence_applied,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
