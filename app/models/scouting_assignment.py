"""
Scouting Assignment Model - Represents scout assignments to players, regions, or competitions
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, CheckConstraint, Index,
    DateTime, ForeignKey, Enum as SQLEnum, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AssignmentType(str, enum.Enum):
    """Scouting assignment type enumeration"""
    PLAYER = "player"
    REGION = "region"
    COMPETITION = "competition"


class AssignmentStatus(str, enum.Enum):
    """Scouting assignment status enumeration"""
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ScoutingAssignment(Base):
    """
    Scouting Assignment model representing scout assignments to players, regions, or competitions.
    
    Based on Requirement 12 (Скаутинг), the scouting system includes:
    - Scout assignment to specific players, regions, or competitions
    - Scouting report generation (2-4 weeks depending on scout quality)
    - Progressive attribute revelation based on scout quality
    - Scouting shortlist (up to 50 players)
    - Youth scouting for 15-18 year olds
    - Scout idle warning notifications
    - World map view for scouting assignments
    
    Assignment Types:
        - PLAYER: Scout assigned to observe a specific player
        - REGION: Scout assigned to observe a geographical region
        - COMPETITION: Scout assigned to observe a specific competition
    
    Assignment Status:
        - ASSIGNED: Scout has been assigned but not yet started
        - IN_PROGRESS: Scout is actively working on the assignment
        - COMPLETED: Scouting report has been generated
    
    Report Data (JSON field):
        - Progressive attribute revelation based on scout quality
        - Basic attributes revealed immediately
        - Detailed attributes revealed after report completion
        - Youth scouting data for 15-18 year olds
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (career context)
        staff_id: Foreign key to Staff (scout assigned)
        
        Assignment Details:
            assignment_type: Type of assignment (player, region, competition)
            target_player_id: Target player ID (for player assignments)
            target_region: Target region name (for region assignments)
            target_competition: Target competition name (for competition assignments)
            assignment_status: Current status (assigned, in_progress, completed)
        
        Timeline:
            start_date: Date when assignment started
            completion_date: Date when assignment completed (null if in progress)
            estimated_weeks: Estimated weeks to complete (2-4 weeks)
        
        Report Data:
            report_data: JSON text field storing progressive revelation data
        
        Timestamps:
            created_at: Timestamp when assignment was created
            updated_at: Timestamp when assignment was last updated
    """
    
    __tablename__ = "scouting_assignments"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Career (career context)"
    )
    
    staff_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Staff (scout assigned)"
    )
    
    # Assignment Details
    assignment_type: Mapped[AssignmentType] = mapped_column(
        SQLEnum(AssignmentType, name="assignment_type_enum", create_constraint=True,
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        comment="Type of assignment (player, region, competition)"
    )
    
    target_player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Target player ID (for player assignments)"
    )
    
    target_region: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Target region name (for region assignments)"
    )
    
    target_competition: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Target competition name (for competition assignments)"
    )
    
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status_enum", create_constraint=True,
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AssignmentStatus.ASSIGNED,
        server_default="assigned",
        index=True,
        comment="Current status (assigned, in_progress, completed)"
    )
    
    # Timeline
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Date when assignment started"
    )
    
    completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when assignment completed (null if in progress)"
    )
    
    estimated_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        comment="Estimated weeks to complete (2-4 weeks)"
    )
    
    # Report Data
    report_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing progressive revelation data"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when assignment was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when assignment was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="scouting_assignments")
    # staff: Mapped["Staff"] = relationship("Staff", back_populates="scouting_assignments")
    # target_player: Mapped[Optional["Player"]] = relationship("Player", back_populates="scouting_assignments")
    
    # Check constraints and indexes
    __table_args__ = (
        # Estimated weeks constraint (2-4 weeks)
        CheckConstraint('estimated_weeks >= 2 AND estimated_weeks <= 4', name='check_estimated_weeks_range'),
        
        # Assignment type validation constraints
        CheckConstraint(
            "(assignment_type = 'player' AND target_player_id IS NOT NULL AND target_region IS NULL AND target_competition IS NULL) OR "
            "(assignment_type = 'region' AND target_player_id IS NULL AND target_region IS NOT NULL AND target_competition IS NULL) OR "
            "(assignment_type = 'competition' AND target_player_id IS NULL AND target_region IS NULL AND target_competition IS NOT NULL)",
            name='check_assignment_type_target_consistency'
        ),
        
        # Completion date constraint (must be after start date if set)
        CheckConstraint(
            'completion_date IS NULL OR completion_date >= start_date',
            name='check_completion_date_after_start'
        ),
        
        # Performance indexes
        Index('idx_scouting_assignments_career_id', 'career_id'),
        Index('idx_scouting_assignments_staff_id', 'staff_id'),
        Index('idx_scouting_assignments_target_player_id', 'target_player_id'),
        Index('idx_scouting_assignments_assignment_type', 'assignment_type'),
        Index('idx_scouting_assignments_assignment_status', 'assignment_status'),
        Index('idx_scouting_assignments_target_region', 'target_region'),
        Index('idx_scouting_assignments_target_competition', 'target_competition'),
        Index('idx_scouting_assignments_start_date', 'start_date'),
        Index('idx_scouting_assignments_completion_date', 'completion_date'),
        # Composite indexes for common query patterns
        Index('idx_scouting_assignments_career_status', 'career_id', 'assignment_status'),
        Index('idx_scouting_assignments_staff_status', 'staff_id', 'assignment_status'),
        Index('idx_scouting_assignments_career_type', 'career_id', 'assignment_type'),
    )
    
    def __repr__(self) -> str:
        """String representation of ScoutingAssignment"""
        return (
            f"<ScoutingAssignment(id={self.id}, "
            f"career_id={self.career_id}, "
            f"staff_id={self.staff_id}, "
            f"assignment_type={self.assignment_type.value}, "
            f"status={self.assignment_status.value})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert ScoutingAssignment model to dictionary.
        
        Returns:
            dict: Dictionary representation of the scouting assignment with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "staff_id": self.staff_id,
            # Assignment details
            "assignment": {
                "type": self.assignment_type.value,
                "target_player_id": self.target_player_id,
                "target_region": self.target_region,
                "target_competition": self.target_competition,
                "status": self.assignment_status.value,
            },
            # Timeline
            "timeline": {
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "completion_date": self.completion_date.isoformat() if self.completion_date else None,
                "estimated_weeks": self.estimated_weeks,
            },
            # Report data
            "report_data": self.report_data,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_target_display_name(self) -> str:
        """
        Get human-readable display name for the assignment target.
        
        Returns:
            str: Display name for the target
        """
        if self.assignment_type == AssignmentType.PLAYER:
            return f"Player ID: {self.target_player_id}"
        elif self.assignment_type == AssignmentType.REGION:
            return f"Region: {self.target_region}"
        elif self.assignment_type == AssignmentType.COMPETITION:
            return f"Competition: {self.target_competition}"
        return "Unknown"
    
    def is_completed(self) -> bool:
        """
        Check if the assignment is completed.
        
        Returns:
            bool: True if status is COMPLETED, False otherwise
        """
        return self.assignment_status == AssignmentStatus.COMPLETED
    
    def is_in_progress(self) -> bool:
        """
        Check if the assignment is in progress.
        
        Returns:
            bool: True if status is IN_PROGRESS, False otherwise
        """
        return self.assignment_status == AssignmentStatus.IN_PROGRESS
    
    def is_assigned(self) -> bool:
        """
        Check if the assignment is newly assigned.
        
        Returns:
            bool: True if status is ASSIGNED, False otherwise
        """
        return self.assignment_status == AssignmentStatus.ASSIGNED
    
    def get_weeks_elapsed(self) -> int:
        """
        Calculate weeks elapsed since assignment start.
        
        Returns:
            int: Weeks elapsed (0 if just started)
        """
        now = datetime.now(self.start_date.tzinfo)
        delta = now - self.start_date
        return max(0, delta.days // 7)
    
    def get_weeks_remaining(self) -> int:
        """
        Calculate estimated weeks remaining until completion.
        
        Returns:
            int: Weeks remaining (0 if completed or overdue)
        """
        if self.is_completed():
            return 0
        
        weeks_elapsed = self.get_weeks_elapsed()
        weeks_remaining = self.estimated_weeks - weeks_elapsed
        return max(0, weeks_remaining)
    
    def is_overdue(self) -> bool:
        """
        Check if the assignment is overdue (elapsed time exceeds estimated time).
        
        Returns:
            bool: True if overdue and not completed, False otherwise
        """
        if self.is_completed():
            return False
        
        return self.get_weeks_elapsed() > self.estimated_weeks
    
    def start_assignment(self) -> None:
        """
        Start the assignment by changing status to IN_PROGRESS.
        """
        if self.assignment_status == AssignmentStatus.ASSIGNED:
            self.assignment_status = AssignmentStatus.IN_PROGRESS
    
    def complete_assignment(self, report_data: str) -> None:
        """
        Complete the assignment by changing status to COMPLETED and setting report data.
        
        Args:
            report_data: JSON string containing scouting report data
        """
        self.assignment_status = AssignmentStatus.COMPLETED
        self.completion_date = func.now()
        self.report_data = report_data
    
    def get_progress_percentage(self) -> float:
        """
        Calculate progress percentage based on weeks elapsed.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if self.is_completed():
            return 100.0
        
        weeks_elapsed = self.get_weeks_elapsed()
        progress = (weeks_elapsed / self.estimated_weeks) * 100
        return min(100.0, progress)
    
    def is_player_assignment(self) -> bool:
        """
        Check if this is a player assignment.
        
        Returns:
            bool: True if assignment type is PLAYER, False otherwise
        """
        return self.assignment_type == AssignmentType.PLAYER
    
    def is_region_assignment(self) -> bool:
        """
        Check if this is a region assignment.
        
        Returns:
            bool: True if assignment type is REGION, False otherwise
        """
        return self.assignment_type == AssignmentType.REGION
    
    def is_competition_assignment(self) -> bool:
        """
        Check if this is a competition assignment.
        
        Returns:
            bool: True if assignment type is COMPETITION, False otherwise
        """
        return self.assignment_type == AssignmentType.COMPETITION
