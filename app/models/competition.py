"""
Competition Model - Represents football competitions (leagues and cups)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, CheckConstraint, Index, 
    DateTime, Text, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class CompetitionType(str, enum.Enum):
    """Competition type enumeration"""
    DOMESTIC_LEAGUE = "domestic_league"
    DOMESTIC_CUP = "domestic_cup"
    CONTINENTAL_CUP = "continental_cup"


class Competition(Base):
    """
    Competition model representing football competitions (leagues and cups).
    
    Competitions include domestic leagues (e.g., Premier League with 20 clubs, 38 matchdays),
    domestic cups (knockout format), and continental cups (group stage + knockout).
    
    The Competition_Engine generates fixture lists, maintains league tables, enforces
    promotion/relegation, awards prize money, and manages European qualification.
    
    Competition Types:
        - DOMESTIC_LEAGUE: League competition with round-robin format (20 clubs, 38 matchdays)
        - DOMESTIC_CUP: Knockout cup competition with randomized seeded draws
        - CONTINENTAL_CUP: Continental competition with group stage + knockout format
    
    Attributes:
        id: Primary key, auto-increment
        name: Competition name (e.g., "Premier League", "FA Cup", "Champions League")
        competition_type: Type of competition (domestic_league, domestic_cup, continental_cup)
        season: Season year (e.g., 2024 for 2024/25 season)
        country: Country where competition is held
        
        Competition Structure:
            num_teams: Number of teams participating
            num_matchdays: Number of matchdays (38 for 20-team league, varies for cups)
            current_matchday: Current matchday number (1-based)
        
        Prize Money Structure (JSON):
            prize_money: JSON text field storing prize money by position
                Format: {"1": 50000000, "2": 40000000, ...} for leagues
                Format: {"winner": 10000000, "runner_up": 5000000, ...} for cups
        
        Reputation Awards:
            reputation_winner: Reputation points awarded to winner
            reputation_runner_up: Reputation points awarded to runner-up
        
        Promotion/Relegation (for leagues):
            promotion_places: Number of automatic promotion places
            relegation_places: Number of automatic relegation places
            playoff_places: Number of playoff places
        
        European Qualification (for domestic leagues):
            champions_league_places: Number of Champions League qualification places
            europa_league_places: Number of Europa League qualification places
        
        Competition Status:
            is_active: Whether competition is currently active
            is_completed: Whether competition has been completed
        
        Timestamps:
            created_at: Timestamp when competition was created
            updated_at: Timestamp when competition was last updated
    """
    
    __tablename__ = "competitions"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Competition name (e.g., Premier League, FA Cup)"
    )
    
    competition_type: Mapped[str] = mapped_column(
        SQLEnum(CompetitionType),
        nullable=False,
        index=True,
        comment="Type of competition (domestic_league, domestic_cup, continental_cup)"
    )
    
    season: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Season year (e.g., 2024 for 2024/25 season)"
    )
    
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Country where competition is held"
    )
    
    # Competition Structure
    num_teams: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of teams participating"
    )
    
    num_matchdays: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of matchdays (38 for 20-team league, varies for cups)"
    )
    
    current_matchday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Current matchday number (1-based)"
    )
    
    # Prize Money Structure (JSON)
    prize_money: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing prize money by position"
    )
    
    # Reputation Awards
    reputation_winner: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Reputation points awarded to winner"
    )
    
    reputation_runner_up: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        comment="Reputation points awarded to runner-up"
    )
    
    # Promotion/Relegation (for leagues)
    promotion_places: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of automatic promotion places"
    )
    
    relegation_places: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of automatic relegation places"
    )
    
    playoff_places: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of playoff places"
    )
    
    # European Qualification (for domestic leagues)
    champions_league_places: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of Champions League qualification places"
    )
    
    europa_league_places: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of Europa League qualification places"
    )
    
    # Competition Status
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Whether competition is currently active"
    )
    
    is_completed: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="Whether competition has been completed"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when competition was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when competition was last updated"
    )
    
    # Check constraints and indexes
    __table_args__ = (
        # Season constraint (reasonable year range)
        CheckConstraint('season >= 2020 AND season <= 2100', name='check_season_range'),
        
        # Team count constraint (> 0)
        CheckConstraint('num_teams > 0', name='check_num_teams_positive'),
        
        # Matchday constraints
        CheckConstraint('num_matchdays > 0', name='check_num_matchdays_positive'),
        CheckConstraint('current_matchday > 0', name='check_current_matchday_positive'),
        CheckConstraint('current_matchday <= num_matchdays', name='check_current_matchday_valid'),
        
        # Reputation constraints (non-negative)
        CheckConstraint('reputation_winner >= 0', name='check_reputation_winner_non_negative'),
        CheckConstraint('reputation_runner_up >= 0', name='check_reputation_runner_up_non_negative'),
        
        # Promotion/Relegation constraints (non-negative)
        CheckConstraint('promotion_places >= 0', name='check_promotion_places_non_negative'),
        CheckConstraint('relegation_places >= 0', name='check_relegation_places_non_negative'),
        CheckConstraint('playoff_places >= 0', name='check_playoff_places_non_negative'),
        
        # European qualification constraints (non-negative)
        CheckConstraint('champions_league_places >= 0', name='check_champions_league_places_non_negative'),
        CheckConstraint('europa_league_places >= 0', name='check_europa_league_places_non_negative'),
        
        # Performance indexes
        Index('idx_competitions_name', 'name'),
        Index('idx_competitions_type', 'competition_type'),
        Index('idx_competitions_season', 'season'),
        Index('idx_competitions_country', 'country'),
        Index('idx_competitions_active', 'is_active'),
        Index('idx_competitions_completed', 'is_completed'),
        Index('idx_competitions_current_matchday', 'current_matchday'),
        # Composite indexes for common queries
        Index('idx_competitions_season_type', 'season', 'competition_type'),
        Index('idx_competitions_country_season', 'country', 'season'),
        Index('idx_competitions_active_season', 'is_active', 'season'),
    )
    
    def __repr__(self) -> str:
        """String representation of Competition"""
        return (
            f"<Competition(id={self.id}, "
            f"name={self.name}, "
            f"type={self.competition_type}, "
            f"season={self.season})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Competition model to dictionary.
        
        Returns:
            dict: Dictionary representation of the competition with all attributes
        """
        return {
            "id": self.id,
            "name": self.name,
            "competition_type": self.competition_type,
            "season": self.season,
            "country": self.country,
            # Competition Structure
            "structure": {
                "num_teams": self.num_teams,
                "num_matchdays": self.num_matchdays,
                "current_matchday": self.current_matchday,
            },
            # Prize Money
            "prize_money": self.prize_money,
            # Reputation Awards
            "reputation": {
                "winner": self.reputation_winner,
                "runner_up": self.reputation_runner_up,
            },
            # Promotion/Relegation
            "promotion_relegation": {
                "promotion_places": self.promotion_places,
                "relegation_places": self.relegation_places,
                "playoff_places": self.playoff_places,
            },
            # European Qualification
            "european_qualification": {
                "champions_league_places": self.champions_league_places,
                "europa_league_places": self.europa_league_places,
            },
            # Status
            "status": {
                "is_active": self.is_active,
                "is_completed": self.is_completed,
            },
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_league(self) -> bool:
        """
        Check if competition is a league.
        
        Returns:
            bool: True if domestic league, False otherwise
        """
        return self.competition_type == CompetitionType.DOMESTIC_LEAGUE
    
    def is_cup(self) -> bool:
        """
        Check if competition is a cup.
        
        Returns:
            bool: True if domestic or continental cup, False otherwise
        """
        return self.competition_type in (
            CompetitionType.DOMESTIC_CUP,
            CompetitionType.CONTINENTAL_CUP
        )
    
    def has_promotion_relegation(self) -> bool:
        """
        Check if competition has promotion/relegation.
        
        Returns:
            bool: True if promotion or relegation places exist, False otherwise
        """
        return (self.promotion_places > 0 or 
                self.relegation_places > 0 or 
                self.playoff_places > 0)
    
    def has_european_qualification(self) -> bool:
        """
        Check if competition offers European qualification.
        
        Returns:
            bool: True if Champions League or Europa League places exist, False otherwise
        """
        return (self.champions_league_places > 0 or 
                self.europa_league_places > 0)
    
    def get_progress_percentage(self) -> float:
        """
        Calculate competition progress percentage.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if self.num_matchdays == 0:
            return 0.0
        return (self.current_matchday / self.num_matchdays) * 100
    
    def is_final_matchday(self) -> bool:
        """
        Check if current matchday is the final matchday.
        
        Returns:
            bool: True if on final matchday, False otherwise
        """
        return self.current_matchday == self.num_matchdays
    
    def advance_matchday(self) -> bool:
        """
        Advance to next matchday.
        
        Returns:
            bool: True if advanced successfully, False if already on final matchday
        """
        if self.current_matchday < self.num_matchdays:
            self.current_matchday += 1
            return True
        return False
    
    def complete_competition(self) -> None:
        """Mark competition as completed."""
        self.is_completed = True
        self.is_active = False
