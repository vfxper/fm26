"""
Sponsorship Deal Model - Persistent storage for active sponsorship deals.

Implements Requirement 8.8: "THE Finance_Module SHALL simulate sponsorship deals
that renew annually with value based on club reputation and league position."

A sponsorship deal lasts 1-3 seasons, pays a weekly amount, and is automatically
renewed at the start of a season once its current term expires.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SponsorshipDeal(Base):
    """
    A sponsorship deal owned by a club for a given career.

    Each row represents a single deal that runs from `start_season` through
    `end_season` (inclusive) and contributes `weekly_payment` of SPONSORSHIP
    income each week the deal is active.

    A career may accumulate historical (expired) deals over time. Active deals
    are those whose season range covers the current season and whose
    `is_active` flag is True.

    Attributes:
        id: Primary key.
        club_id: Club the deal belongs to.
        career_id: Career the deal belongs to.
        tier: Sponsorship tier ("small", "medium", "large", "premium").
        sponsor_name: Generated human-readable sponsor name.
        annual_value: Total annual value of the deal.
        weekly_payment: Per-week payment amount (annual_value // 52).
        duration_seasons: Length of the deal in seasons (1-3).
        start_season: First season of the deal.
        end_season: Final season of the deal (inclusive).
        is_active: Whether the deal is currently active. Set to False when
                   superseded by a renewal.
        created_at: Creation timestamp.
    """

    __tablename__ = "sponsorship_deals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    club_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Club the deal belongs to",
    )

    career_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Career the deal belongs to",
    )

    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Sponsorship tier (small, medium, large, premium)",
    )

    sponsor_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
        comment="Human-readable sponsor name",
    )

    annual_value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Total annual value of the deal",
    )

    weekly_payment: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Weekly payment amount (annual_value // 52)",
    )

    duration_seasons: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Duration in seasons (1-3)",
    )

    start_season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="First season the deal is active",
    )

    end_season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Last season the deal is active (inclusive)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether the deal is currently active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the deal was created",
    )

    __table_args__ = (
        CheckConstraint("annual_value >= 0", name="check_sponsorship_annual_value_nonneg"),
        CheckConstraint(
            "weekly_payment >= 0", name="check_sponsorship_weekly_payment_nonneg"
        ),
        CheckConstraint(
            "duration_seasons >= 1 AND duration_seasons <= 3",
            name="check_sponsorship_duration_range",
        ),
        CheckConstraint(
            "start_season >= 1", name="check_sponsorship_start_season_positive"
        ),
        CheckConstraint(
            "end_season >= start_season", name="check_sponsorship_season_range"
        ),
        Index("idx_sponsorship_deals_club_career", "club_id", "career_id"),
        Index(
            "idx_sponsorship_deals_active", "club_id", "career_id", "is_active"
        ),
        Index("idx_sponsorship_deals_seasons", "start_season", "end_season"),
    )

    def __repr__(self) -> str:
        return (
            f"<SponsorshipDeal(id={self.id}, "
            f"club_id={self.club_id}, "
            f"career_id={self.career_id}, "
            f"tier={self.tier}, "
            f"annual_value={self.annual_value}, "
            f"seasons={self.start_season}-{self.end_season}, "
            f"active={self.is_active})>"
        )

    def covers_season(self, season: int) -> bool:
        """Return True if this deal covers the given season."""
        return self.start_season <= season <= self.end_season

    def to_dict(self) -> dict:
        """Convert to a dictionary mirroring the format of generate_sponsorship_deal."""
        return {
            "id": self.id,
            "club_id": self.club_id,
            "career_id": self.career_id,
            "tier": self.tier,
            "sponsor_name": self.sponsor_name,
            "annual_value": self.annual_value,
            "weekly_payment": self.weekly_payment,
            "duration_seasons": self.duration_seasons,
            "start_season": self.start_season,
            "end_season": self.end_season,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
