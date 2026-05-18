"""
Infrastructure Upgrade Model - Tracks in-progress and completed infrastructure upgrades

This model records infrastructure upgrade requests for clubs, tracking:
- Which category is being upgraded
- The target level
- Cost and duration
- Start time (season/week) and expected completion time
- Current status (in_progress, completed, cancelled)

Implements Requirement 9.3: "THE Career_Manager SHALL allow the player-manager to
request infrastructure upgrades from the board, subject to board approval and club
financial health."

Implements Requirement 9.9: "Infrastructure upgrades SHALL take between 4 and 26
in-game weeks to complete depending on upgrade level."
"""

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class UpgradeStatus(str, enum.Enum):
    """Status of an infrastructure upgrade."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InfrastructureUpgrade(Base):
    """
    Infrastructure upgrade model for tracking upgrade requests and progress.

    Each record represents a single upgrade request for one infrastructure category.
    Only one upgrade per category can be in progress at a time for a given club/career.

    Attributes:
        id: Primary key, auto-increment
        club_id: Club requesting the upgrade
        career_id: Career context for the upgrade
        category: Infrastructure category being upgraded (e.g., "stadium")
        from_level: Current level before upgrade
        to_level: Target level after upgrade
        cost: Total cost of the upgrade
        duration_weeks: Number of weeks to complete
        start_season: Season when upgrade was requested
        start_week: Week when upgrade was requested
        completion_season: Season when upgrade will complete
        completion_week: Week when upgrade will complete
        status: Current status (in_progress, completed, cancelled)
        created_at: Timestamp when record was created
        completed_at: Timestamp when upgrade was completed (if applicable)
    """

    __tablename__ = "infrastructure_upgrades"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    club_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Club requesting the upgrade"
    )

    career_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Career context for the upgrade"
    )

    # Upgrade details
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Infrastructure category (stadium, training_facilities, etc.)"
    )

    from_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Level before upgrade (1-4)"
    )

    to_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Target level after upgrade (2-5)"
    )

    cost: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Total cost of the upgrade"
    )

    duration_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of weeks to complete the upgrade"
    )

    # Timing
    start_season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Season when upgrade was started"
    )

    start_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Week when upgrade was started (1-52)"
    )

    completion_season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Season when upgrade will complete"
    )

    completion_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Week when upgrade will complete (1-52)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UpgradeStatus.IN_PROGRESS.value,
        server_default=UpgradeStatus.IN_PROGRESS.value,
        comment="Current status: in_progress, completed, cancelled"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when upgrade was requested"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when upgrade was completed"
    )

    __table_args__ = (
        # Level constraints
        CheckConstraint('from_level >= 1 AND from_level <= 4', name='check_upgrade_from_level_range'),
        CheckConstraint('to_level >= 2 AND to_level <= 5', name='check_upgrade_to_level_range'),
        CheckConstraint('to_level > from_level', name='check_upgrade_level_progression'),
        # Cost must be positive
        CheckConstraint('cost > 0', name='check_upgrade_cost_positive'),
        # Duration must be within valid range (4-26 weeks per Requirement 9.9)
        CheckConstraint('duration_weeks >= 4 AND duration_weeks <= 26', name='check_upgrade_duration_range'),
        # Week constraints
        CheckConstraint('start_week >= 1 AND start_week <= 52', name='check_upgrade_start_week_range'),
        CheckConstraint('completion_week >= 1 AND completion_week <= 52', name='check_upgrade_completion_week_range'),
        # Season constraints
        CheckConstraint('start_season >= 1', name='check_upgrade_start_season_positive'),
        CheckConstraint('completion_season >= 1', name='check_upgrade_completion_season_positive'),
        # Performance indexes
        Index('idx_infrastructure_upgrades_club_career', 'club_id', 'career_id'),
        Index('idx_infrastructure_upgrades_status', 'status'),
        Index('idx_infrastructure_upgrades_category', 'category'),
        Index('idx_infrastructure_upgrades_completion', 'completion_season', 'completion_week'),
    )

    def __repr__(self) -> str:
        return (
            f"<InfrastructureUpgrade(id={self.id}, "
            f"club_id={self.club_id}, "
            f"category={self.category}, "
            f"from_level={self.from_level}, "
            f"to_level={self.to_level}, "
            f"status={self.status})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "club_id": self.club_id,
            "career_id": self.career_id,
            "category": self.category,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "cost": self.cost,
            "duration_weeks": self.duration_weeks,
            "start_season": self.start_season,
            "start_week": self.start_week,
            "completion_season": self.completion_season,
            "completion_week": self.completion_week,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @property
    def is_in_progress(self) -> bool:
        """Check if upgrade is still in progress."""
        return self.status == UpgradeStatus.IN_PROGRESS.value

    @property
    def is_completed(self) -> bool:
        """Check if upgrade has been completed."""
        return self.status == UpgradeStatus.COMPLETED.value
