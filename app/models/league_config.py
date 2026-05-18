"""
LeagueConfig Model - Stores league-specific scheduling configuration
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class LeagueConfig(Base):
    """
    LeagueConfig model storing league-specific scheduling rules.

    Each league has unique scheduling constraints including winter breaks,
    mandatory fixture dates (e.g. Boxing Day), blackout dates (e.g. Christmas),
    and custom milestones. This data drives the CalendarEngine's season generation.

    JSON fields:
        mandatory_fixture_dates: ["12-26", "01-01"] - dates that must have fixtures
        blackout_dates: ["12-25"] - dates where no matches allowed
        custom_milestones: [{"date": "12-26", "name": "Boxing Day fixtures"}]
    """

    __tablename__ = "league_configs"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # League identification
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Country name (unique identifier for league config)"
    )

    league_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full league name (e.g. Premier League, Bundesliga)"
    )

    # Winter break configuration
    has_winter_break: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this league has a winter break"
    )

    winter_break_start: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Winter break start in MM-DD format (e.g. 01-01)"
    )

    winter_break_end: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Winter break end in MM-DD format (e.g. 01-31)"
    )

    # Scheduling rules (JSON)
    mandatory_fixture_dates: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of MM-DD dates that must have fixtures"
    )

    blackout_dates: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of MM-DD dates where no matches allowed"
    )

    custom_milestones: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of {date, name} milestone objects"
    )

    # Season dates
    season_start_date: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Season start in MM-DD format (e.g. 08-10)"
    )

    season_end_date: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
        comment="Season end in MM-DD format (e.g. 05-15)"
    )

    # European competition
    european_competition: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="European competition: champions_league, europa_league, conference_league, or null"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="Timestamp when config was created"
    )

    def __repr__(self) -> str:
        """String representation of LeagueConfig"""
        return (
            f"<LeagueConfig(id={self.id}, "
            f"country={self.country}, "
            f"league={self.league_name})>"
        )
