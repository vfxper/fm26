"""
Scouting Shortlist Model - Represents players added to a career's scouting shortlist
"""

from datetime import datetime
from sqlalchemy import (
    Integer, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ScoutingShortlist(Base):
    """
    Scouting Shortlist model representing players on a career's scouting shortlist.
    
    Each career can have up to 50 players on their shortlist. Players are added
    after scouting reports are generated or manually by the manager.
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career
        player_id: Foreign key to Player
        added_date: Timestamp when player was added to shortlist
    """
    
    __tablename__ = "scouting_shortlists"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Career"
    )
    
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Player"
    )
    
    # Timestamp
    added_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when player was added to shortlist"
    )
    
    __table_args__ = (
        # Ensure a player can only be on a career's shortlist once
        UniqueConstraint('career_id', 'player_id', name='uq_shortlist_career_player'),
        # Performance indexes
        Index('idx_shortlist_career_id', 'career_id'),
        Index('idx_shortlist_player_id', 'player_id'),
        Index('idx_shortlist_added_date', 'added_date'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ScoutingShortlist(id={self.id}, "
            f"career_id={self.career_id}, "
            f"player_id={self.player_id})>"
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "career_id": self.career_id,
            "player_id": self.player_id,
            "added_date": self.added_date.isoformat() if self.added_date else None,
        }
