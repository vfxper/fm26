"""
Match Model - Represents match results and match data
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, CheckConstraint, Index, 
    DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class MatchStatus(str, enum.Enum):
    """Match status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class WeatherCondition(str, enum.Enum):
    """Weather condition enumeration"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    FOG = "fog"


class PitchCondition(str, enum.Enum):
    """Pitch condition enumeration"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    WATERLOGGED = "waterlogged"


class Match(Base):
    """
    Match model representing match results and match data.
    
    This table stores the outcome of simulated matches including scores,
    statistics, and match metadata. Matches can be linked to a Career
    (for player-managed matches) and must reference home and away Clubs.
    
    Match Result Fields:
        - home_score: Goals scored by home team
        - away_score: Goals scored by away team
        - home_club_id: Foreign key to home Club
        - away_club_id: Foreign key to away Club
    
    Match Metadata:
        - match_date: Date and time of the match
        - competition: Competition name (e.g., "Premier League", "FA Cup")
        - venue: Stadium name
        - weather: Weather condition during match
        - pitch_condition: Pitch quality during match
        - attendance: Number of spectators
    
    Match Statistics:
        - home_possession: Home team possession percentage (0-100)
        - away_possession: Away team possession percentage (0-100)
        - home_shots: Home team total shots
        - away_shots: Away team total shots
        - home_shots_on_target: Home team shots on target
        - away_shots_on_target: Away team shots on target
        - home_passes: Home team completed passes
        - away_passes: Away team completed passes
        - home_pass_accuracy: Home team pass accuracy percentage (0-100)
        - away_pass_accuracy: Away team pass accuracy percentage (0-100)
        - home_tackles: Home team tackles
        - away_tackles: Away team tackles
        - home_fouls: Home team fouls committed
        - away_fouls: Away team fouls committed
        - home_yellow_cards: Home team yellow cards
        - away_yellow_cards: Away team yellow cards
        - home_red_cards: Home team red cards
        - away_red_cards: Away team red cards
    
    Match Duration:
        - match_duration: Total match duration in minutes (90 + extra time)
        - extra_time_played: Whether extra time was played
    
    Home Advantage:
        - home_advantage_applied: Whether home advantage was applied
    
    Player Ratings:
        - player_ratings: JSON text field storing player ratings (1-10 scale)
          Format: {"player_id": rating, ...}
    
    Career Link:
        - career_id: Optional foreign key to Career (for player-managed matches)
    
    Match Status:
        - status: Current match status (scheduled, in_progress, completed, abandoned)
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Optional foreign key to Career
        home_club_id: Foreign key to home Club
        away_club_id: Foreign key to away Club
        
        Match Result:
            home_score: Goals scored by home team
            away_score: Goals scored by away team
        
        Match Metadata:
            match_date: Date and time of the match
            competition: Competition name
            venue: Stadium name
            weather: Weather condition
            pitch_condition: Pitch quality
            attendance: Number of spectators
        
        Match Statistics:
            home_possession: Home team possession %
            away_possession: Away team possession %
            home_shots: Home team shots
            away_shots: Away team shots
            home_shots_on_target: Home team shots on target
            away_shots_on_target: Away team shots on target
            home_passes: Home team passes
            away_passes: Away team passes
            home_pass_accuracy: Home team pass accuracy %
            away_pass_accuracy: Away team pass accuracy %
            home_tackles: Home team tackles
            away_tackles: Away team tackles
            home_fouls: Home team fouls
            away_fouls: Away team fouls
            home_yellow_cards: Home team yellow cards
            away_yellow_cards: Away team yellow cards
            home_red_cards: Home team red cards
            away_red_cards: Away team red cards
        
        Match Duration:
            match_duration: Total duration in minutes
            extra_time_played: Whether extra time was played
        
        Home Advantage:
            home_advantage_applied: Whether home advantage was applied
        
        Player Ratings:
            player_ratings: JSON text field with player ratings
        
        Match Status:
            status: Current match status
        
        Timestamps:
            created_at: Timestamp when match was created
            updated_at: Timestamp when match was last updated
    """
    
    __tablename__ = "matches"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Keys
    career_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional foreign key to Career (for player-managed matches)"
    )
    
    home_club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to home Club"
    )
    
    away_club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to away Club"
    )
    
    # Match Result
    home_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Goals scored by home team"
    )
    
    away_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Goals scored by away team"
    )
    
    # Match Metadata
    match_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Date and time of the match"
    )
    
    competition: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Competition name (e.g., Premier League, FA Cup)"
    )
    
    venue: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Stadium name"
    )
    
    weather: Mapped[str] = mapped_column(
        SQLEnum(WeatherCondition),
        nullable=False,
        default=WeatherCondition.CLEAR,
        server_default=WeatherCondition.CLEAR.value,
        comment="Weather condition during match"
    )
    
    pitch_condition: Mapped[str] = mapped_column(
        SQLEnum(PitchCondition),
        nullable=False,
        default=PitchCondition.GOOD,
        server_default=PitchCondition.GOOD.value,
        comment="Pitch quality during match"
    )
    
    attendance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of spectators"
    )
    
    # Match Statistics
    home_possession: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        comment="Home team possession percentage (0-100)"
    )
    
    away_possession: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        comment="Away team possession percentage (0-100)"
    )
    
    home_shots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team total shots"
    )
    
    away_shots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team total shots"
    )
    
    home_shots_on_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team shots on target"
    )
    
    away_shots_on_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team shots on target"
    )
    
    home_passes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team completed passes"
    )
    
    away_passes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team completed passes"
    )
    
    home_pass_accuracy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team pass accuracy percentage (0-100)"
    )
    
    away_pass_accuracy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team pass accuracy percentage (0-100)"
    )
    
    home_tackles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team tackles"
    )
    
    away_tackles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team tackles"
    )
    
    home_fouls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team fouls committed"
    )
    
    away_fouls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team fouls committed"
    )
    
    home_yellow_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team yellow cards"
    )
    
    away_yellow_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team yellow cards"
    )
    
    home_red_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Home team red cards"
    )
    
    away_red_cards: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Away team red cards"
    )
    
    # Match Duration
    match_duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
        server_default="90",
        comment="Total match duration in minutes (90 + extra time)"
    )
    
    extra_time_played: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether extra time was played"
    )
    
    # Home Advantage
    home_advantage_applied: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether home advantage was applied"
    )
    
    # Player Ratings (JSON text field)
    player_ratings: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON text field storing player ratings (1-10 scale)"
    )
    
    # Match Status
    status: Mapped[str] = mapped_column(
        SQLEnum(MatchStatus),
        nullable=False,
        default=MatchStatus.SCHEDULED,
        server_default=MatchStatus.SCHEDULED.value,
        index=True,
        comment="Current match status"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when match was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when match was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped[Optional["Career"]] = relationship("Career", back_populates="matches")
    # home_club: Mapped["Club"] = relationship("Club", foreign_keys=[home_club_id], back_populates="home_matches")
    # away_club: Mapped["Club"] = relationship("Club", foreign_keys=[away_club_id], back_populates="away_matches")
    
    # Check constraints and indexes
    __table_args__ = (
        # Score constraints (non-negative)
        CheckConstraint('home_score >= 0', name='check_home_score_non_negative'),
        CheckConstraint('away_score >= 0', name='check_away_score_non_negative'),
        
        # Attendance constraint (non-negative)
        CheckConstraint('attendance >= 0', name='check_attendance_non_negative'),
        
        # Possession constraints (0-100)
        CheckConstraint('home_possession >= 0 AND home_possession <= 100', name='check_home_possession_range'),
        CheckConstraint('away_possession >= 0 AND away_possession <= 100', name='check_away_possession_range'),
        
        # Statistics constraints (non-negative)
        CheckConstraint('home_shots >= 0', name='check_home_shots_non_negative'),
        CheckConstraint('away_shots >= 0', name='check_away_shots_non_negative'),
        CheckConstraint('home_shots_on_target >= 0', name='check_home_shots_on_target_non_negative'),
        CheckConstraint('away_shots_on_target >= 0', name='check_away_shots_on_target_non_negative'),
        CheckConstraint('home_passes >= 0', name='check_home_passes_non_negative'),
        CheckConstraint('away_passes >= 0', name='check_away_passes_non_negative'),
        CheckConstraint('home_tackles >= 0', name='check_home_tackles_non_negative'),
        CheckConstraint('away_tackles >= 0', name='check_away_tackles_non_negative'),
        CheckConstraint('home_fouls >= 0', name='check_home_fouls_non_negative'),
        CheckConstraint('away_fouls >= 0', name='check_away_fouls_non_negative'),
        CheckConstraint('home_yellow_cards >= 0', name='check_home_yellow_cards_non_negative'),
        CheckConstraint('away_yellow_cards >= 0', name='check_away_yellow_cards_non_negative'),
        CheckConstraint('home_red_cards >= 0', name='check_home_red_cards_non_negative'),
        CheckConstraint('away_red_cards >= 0', name='check_away_red_cards_non_negative'),
        
        # Pass accuracy constraints (0-100)
        CheckConstraint('home_pass_accuracy >= 0 AND home_pass_accuracy <= 100', name='check_home_pass_accuracy_range'),
        CheckConstraint('away_pass_accuracy >= 0 AND away_pass_accuracy <= 100', name='check_away_pass_accuracy_range'),
        
        # Shots on target cannot exceed total shots
        CheckConstraint('home_shots_on_target <= home_shots', name='check_home_shots_on_target_valid'),
        CheckConstraint('away_shots_on_target <= away_shots', name='check_away_shots_on_target_valid'),
        
        # Match duration constraint (must be at least 90 minutes)
        CheckConstraint('match_duration >= 90', name='check_match_duration_minimum'),
        
        # Home and away clubs must be different
        CheckConstraint('home_club_id != away_club_id', name='check_different_clubs'),
        
        # Performance indexes
        Index('idx_matches_career_id', 'career_id'),
        Index('idx_matches_home_club_id', 'home_club_id'),
        Index('idx_matches_away_club_id', 'away_club_id'),
        Index('idx_matches_match_date', 'match_date'),
        Index('idx_matches_competition', 'competition'),
        Index('idx_matches_status', 'status'),
        # Composite indexes for common queries
        Index('idx_matches_career_date', 'career_id', 'match_date'),
        Index('idx_matches_competition_date', 'competition', 'match_date'),
        Index('idx_matches_club_date', 'home_club_id', 'away_club_id', 'match_date'),
    )
    
    def __repr__(self) -> str:
        """String representation of Match"""
        return (
            f"<Match(id={self.id}, "
            f"home_club_id={self.home_club_id}, "
            f"away_club_id={self.away_club_id}, "
            f"score={self.home_score}-{self.away_score}, "
            f"status={self.status})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Match model to dictionary.
        
        Returns:
            dict: Dictionary representation of the match with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "home_club_id": self.home_club_id,
            "away_club_id": self.away_club_id,
            # Match Result
            "result": {
                "home_score": self.home_score,
                "away_score": self.away_score,
            },
            # Match Metadata
            "metadata": {
                "match_date": self.match_date.isoformat() if self.match_date else None,
                "competition": self.competition,
                "venue": self.venue,
                "weather": self.weather,
                "pitch_condition": self.pitch_condition,
                "attendance": self.attendance,
            },
            # Match Statistics
            "statistics": {
                "possession": {
                    "home": self.home_possession,
                    "away": self.away_possession,
                },
                "shots": {
                    "home": self.home_shots,
                    "away": self.away_shots,
                    "home_on_target": self.home_shots_on_target,
                    "away_on_target": self.away_shots_on_target,
                },
                "passes": {
                    "home": self.home_passes,
                    "away": self.away_passes,
                    "home_accuracy": self.home_pass_accuracy,
                    "away_accuracy": self.away_pass_accuracy,
                },
                "tackles": {
                    "home": self.home_tackles,
                    "away": self.away_tackles,
                },
                "fouls": {
                    "home": self.home_fouls,
                    "away": self.away_fouls,
                },
                "cards": {
                    "home_yellow": self.home_yellow_cards,
                    "away_yellow": self.away_yellow_cards,
                    "home_red": self.home_red_cards,
                    "away_red": self.away_red_cards,
                },
            },
            # Match Duration
            "duration": {
                "match_duration": self.match_duration,
                "extra_time_played": self.extra_time_played,
            },
            # Home Advantage
            "home_advantage_applied": self.home_advantage_applied,
            # Player Ratings
            "player_ratings": self.player_ratings,
            # Match Status
            "status": self.status,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_result_string(self) -> str:
        """
        Get match result as a string.
        
        Returns:
            str: Match result string (e.g., "2-1")
        """
        return f"{self.home_score}-{self.away_score}"
    
    def get_winner(self) -> Optional[str]:
        """
        Determine the winner of the match.
        
        Returns:
            Optional[str]: "home", "away", or None for draw
        """
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        else:
            return None
    
    def is_draw(self) -> bool:
        """
        Check if the match ended in a draw.
        
        Returns:
            bool: True if draw, False otherwise
        """
        return self.home_score == self.away_score
    
    def is_completed(self) -> bool:
        """
        Check if the match is completed.
        
        Returns:
            bool: True if completed, False otherwise
        """
        return self.status == MatchStatus.COMPLETED
    
    def is_scheduled(self) -> bool:
        """
        Check if the match is scheduled.
        
        Returns:
            bool: True if scheduled, False otherwise
        """
        return self.status == MatchStatus.SCHEDULED
    
    def is_in_progress(self) -> bool:
        """
        Check if the match is in progress.
        
        Returns:
            bool: True if in progress, False otherwise
        """
        return self.status == MatchStatus.IN_PROGRESS
    
    def get_total_goals(self) -> int:
        """
        Get total goals scored in the match.
        
        Returns:
            int: Total goals (home + away)
        """
        return self.home_score + self.away_score
    
    def get_total_cards(self) -> int:
        """
        Get total cards shown in the match.
        
        Returns:
            int: Total cards (yellow + red for both teams)
        """
        return (
            self.home_yellow_cards + self.away_yellow_cards +
            self.home_red_cards + self.away_red_cards
        )
    
    def get_shot_accuracy(self, team: str) -> float:
        """
        Calculate shot accuracy for a team.
        
        Args:
            team: "home" or "away"
        
        Returns:
            float: Shot accuracy percentage (0-100), or 0 if no shots
        """
        if team == "home":
            if self.home_shots == 0:
                return 0.0
            return (self.home_shots_on_target / self.home_shots) * 100
        elif team == "away":
            if self.away_shots == 0:
                return 0.0
            return (self.away_shots_on_target / self.away_shots) * 100
        else:
            return 0.0
    
    def was_high_scoring(self) -> bool:
        """
        Check if the match was high-scoring (5+ goals).
        
        Returns:
            bool: True if 5 or more goals scored, False otherwise
        """
        return self.get_total_goals() >= 5
    
    def was_clean_sheet(self, team: str) -> bool:
        """
        Check if a team kept a clean sheet.
        
        Args:
            team: "home" or "away"
        
        Returns:
            bool: True if clean sheet, False otherwise
        """
        if team == "home":
            return self.away_score == 0
        elif team == "away":
            return self.home_score == 0
        else:
            return False
