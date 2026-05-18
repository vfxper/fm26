"""
Player Model - Represents football players from the 2600球员属性.csv database
"""

from typing import Optional
from sqlalchemy import String, Integer, CheckConstraint, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.core.database import Base


class Player(Base):
    """
    Player model representing football players from the Player_DB (2600球员属性.csv).
    
    Contains 50+ attributes including technical, mental, and physical attributes.
    All players are loaded from the CSV file and stored in the database for
    efficient querying, filtering, and full-text search.
    
    Attributes:
        id: Primary key, auto-increment
        uid: Unique identifier from CSV (unique and indexed)
        name: Player name (indexed for search)
        position: Player position(s) (e.g., "AM/ST RL")
        age: Player age in years
        ca: Current Ability (1-200)
        pa: Potential Ability (1-200)
        nationality: Player nationality
        club: Current club name
        
        Technical attributes (1-20 each):
            corners, crossing, dribbling, finishing, first_touch, free_kicks,
            heading, long_shots, long_throws, marking, passing, penalty,
            tackling, technique
        
        Mental attributes (1-20 each):
            aggression, anticipation, bravery, composure, concentration,
            decisions, determination, flair, leadership, off_the_ball,
            positioning, teamwork, vision, work_rate
        
        Physical attributes (1-20 each):
            acceleration, agility, balance, jumping, stamina, pace,
            endurance, strength
        
        Financial:
            price: Market value (string with currency symbols)
            wage: Weekly wage
        
        Physical stats:
            height: Height in cm
            weight: Weight in kg
            left_foot: Left foot ability (1-20)
            right_foot: Right foot ability (1-20)
    """
    
    __tablename__ = "players"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Unique identifier from CSV
    uid: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique identifier from CSV"
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Player name"
    )
    
    position: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Player position(s), e.g., 'AM/ST RL'"
    )
    
    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Player age in years"
    )
    
    # Core Attributes
    ca: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Current Ability (1-200)"
    )
    
    pa: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Potential Ability (1-200)"
    )
    
    nationality: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Player nationality"
    )
    
    club: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Current club name"
    )
    
    # Technical Attributes (1-20 each)
    corners: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Corners attribute (1-20)"
    )
    
    crossing: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Crossing attribute (1-20)"
    )
    
    dribbling: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Dribbling attribute (1-20)"
    )
    
    finishing: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Finishing attribute (1-20)"
    )
    
    first_touch: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="First touch attribute (1-20)"
    )
    
    free_kicks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Free kicks attribute (1-20)"
    )
    
    heading: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Heading attribute (1-20)"
    )
    
    long_shots: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Long shots attribute (1-20)"
    )
    
    long_throws: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Long throws attribute (1-20)"
    )
    
    marking: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Marking attribute (1-20)"
    )
    
    passing: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Passing attribute (1-20)"
    )
    
    penalty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Penalty attribute (1-20)"
    )
    
    tackling: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tackling attribute (1-20)"
    )
    
    technique: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Technique attribute (1-20)"
    )
    
    # Mental Attributes (1-20 each)
    aggression: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Aggression attribute (1-20)"
    )
    
    anticipation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Anticipation attribute (1-20)"
    )
    
    bravery: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Bravery attribute (1-20)"
    )
    
    composure: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Composure attribute (1-20)"
    )
    
    concentration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Concentration attribute (1-20)"
    )
    
    decisions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Decisions attribute (1-20)"
    )
    
    determination: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Determination attribute (1-20)"
    )
    
    flair: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Flair attribute (1-20)"
    )
    
    leadership: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Leadership attribute (1-20)"
    )
    
    off_the_ball: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Off the ball attribute (1-20)"
    )
    
    positioning: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Positioning attribute (1-20)"
    )
    
    teamwork: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Teamwork attribute (1-20)"
    )
    
    vision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Vision attribute (1-20)"
    )
    
    work_rate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Work rate attribute (1-20)"
    )
    
    # Physical Attributes (1-20 each)
    acceleration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Acceleration attribute (1-20)"
    )
    
    agility: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Agility attribute (1-20)"
    )
    
    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Balance attribute (1-20)"
    )
    
    jumping: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Jumping attribute (1-20)"
    )
    
    stamina: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Stamina attribute (1-20)"
    )
    
    pace: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Pace attribute (1-20)"
    )
    
    endurance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Endurance attribute (1-20)"
    )
    
    strength: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Strength attribute (1-20)"
    )
    
    # Financial
    price: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Market value (string with currency symbols)"
    )
    
    wage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Weekly wage"
    )
    
    # Physical Stats
    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Height in cm"
    )
    
    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Weight in kg"
    )
    
    left_foot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Left foot ability (1-20)"
    )
    
    right_foot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Right foot ability (1-20)"
    )
    
    # Player traits and playing style characteristics
    traits: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Player traits and playing style characteristics (e.g., 'tries tricks', 'cuts inside from right')"
    )
    
    # Check constraints for attribute ranges
    __table_args__ = (
        # CA and PA constraints
        # CA: 1-200
        # PA: -200 to 200 (negative values indicate random potential ranges in FM)
        CheckConstraint('ca >= 1 AND ca <= 200', name='check_ca_range'),
        CheckConstraint('pa >= -200 AND pa <= 200 AND pa != 0', name='check_pa_range'),
        
        # Technical attributes constraints (1-20)
        CheckConstraint('corners >= 1 AND corners <= 20', name='check_corners_range'),
        CheckConstraint('crossing >= 1 AND crossing <= 20', name='check_crossing_range'),
        CheckConstraint('dribbling >= 1 AND dribbling <= 20', name='check_dribbling_range'),
        CheckConstraint('finishing >= 1 AND finishing <= 20', name='check_finishing_range'),
        CheckConstraint('first_touch >= 1 AND first_touch <= 20', name='check_first_touch_range'),
        CheckConstraint('free_kicks >= 1 AND free_kicks <= 20', name='check_free_kicks_range'),
        CheckConstraint('heading >= 1 AND heading <= 20', name='check_heading_range'),
        CheckConstraint('long_shots >= 1 AND long_shots <= 20', name='check_long_shots_range'),
        CheckConstraint('long_throws >= 1 AND long_throws <= 20', name='check_long_throws_range'),
        CheckConstraint('marking >= 1 AND marking <= 20', name='check_marking_range'),
        CheckConstraint('passing >= 1 AND passing <= 20', name='check_passing_range'),
        CheckConstraint('penalty >= 1 AND penalty <= 20', name='check_penalty_range'),
        CheckConstraint('tackling >= 1 AND tackling <= 20', name='check_tackling_range'),
        CheckConstraint('technique >= 1 AND technique <= 20', name='check_technique_range'),
        
        # Mental attributes constraints (1-20)
        CheckConstraint('aggression >= 1 AND aggression <= 20', name='check_aggression_range'),
        CheckConstraint('anticipation >= 1 AND anticipation <= 20', name='check_anticipation_range'),
        CheckConstraint('bravery >= 1 AND bravery <= 20', name='check_bravery_range'),
        CheckConstraint('composure >= 1 AND composure <= 20', name='check_composure_range'),
        CheckConstraint('concentration >= 1 AND concentration <= 20', name='check_concentration_range'),
        CheckConstraint('decisions >= 1 AND decisions <= 20', name='check_decisions_range'),
        CheckConstraint('determination >= 1 AND determination <= 20', name='check_determination_range'),
        CheckConstraint('flair >= 1 AND flair <= 20', name='check_flair_range'),
        CheckConstraint('leadership >= 1 AND leadership <= 20', name='check_leadership_range'),
        CheckConstraint('off_the_ball >= 1 AND off_the_ball <= 20', name='check_off_the_ball_range'),
        CheckConstraint('positioning >= 1 AND positioning <= 20', name='check_positioning_range'),
        CheckConstraint('teamwork >= 1 AND teamwork <= 20', name='check_teamwork_range'),
        CheckConstraint('vision >= 1 AND vision <= 20', name='check_vision_range'),
        CheckConstraint('work_rate >= 1 AND work_rate <= 20', name='check_work_rate_range'),
        
        # Physical attributes constraints (1-20)
        CheckConstraint('acceleration >= 1 AND acceleration <= 20', name='check_acceleration_range'),
        CheckConstraint('agility >= 1 AND agility <= 20', name='check_agility_range'),
        CheckConstraint('balance >= 1 AND balance <= 20', name='check_balance_range'),
        CheckConstraint('jumping >= 1 AND jumping <= 20', name='check_jumping_range'),
        CheckConstraint('stamina >= 1 AND stamina <= 20', name='check_stamina_range'),
        CheckConstraint('pace >= 1 AND pace <= 20', name='check_pace_range'),
        CheckConstraint('endurance >= 1 AND endurance <= 20', name='check_endurance_range'),
        CheckConstraint('strength >= 1 AND strength <= 20', name='check_strength_range'),
        
        # Foot ability constraints (1-20)
        CheckConstraint('left_foot >= 1 AND left_foot <= 20', name='check_left_foot_range'),
        CheckConstraint('right_foot >= 1 AND right_foot <= 20', name='check_right_foot_range'),
        
        # Performance indexes
        Index('idx_players_uid', 'uid'),
        Index('idx_players_name', 'name'),
        Index('idx_players_position', 'position'),
        Index('idx_players_club', 'club'),
        Index('idx_players_ca', 'ca'),
        Index('idx_players_pa', 'pa'),
        Index('idx_players_nationality', 'nationality'),
        Index('idx_players_age', 'age'),
        # Composite index for common search patterns
        Index('idx_players_position_ca', 'position', 'ca'),
        Index('idx_players_club_position', 'club', 'position'),
        
        # Full-text search GIN index
        # Creates a GIN index on the tsvector expression combining searchable fields
        # Uses 'simple' configuration for language-agnostic search (supports multiple languages)
        # NOTE: This index is PostgreSQL-specific and will be skipped for SQLite
        Index(
            'idx_players_fts',
            text("to_tsvector('simple', COALESCE(name, '') || ' ' || COALESCE(position, '') || ' ' || COALESCE(club, '') || ' ' || COALESCE(nationality, ''))"),
            postgresql_using='gin'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of Player"""
        return (
            f"<Player(id={self.id}, "
            f"uid={self.uid}, "
            f"name={self.name}, "
            f"position={self.position}, "
            f"ca={self.ca}, "
            f"pa={self.pa}, "
            f"club={self.club})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Player model to dictionary.
        
        Returns:
            dict: Dictionary representation of the player with all attributes
        """
        return {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "position": self.position,
            "age": self.age,
            "ca": self.ca,
            "pa": self.pa,
            "nationality": self.nationality,
            "club": self.club,
            # Technical attributes
            "technical": {
                "corners": self.corners,
                "crossing": self.crossing,
                "dribbling": self.dribbling,
                "finishing": self.finishing,
                "first_touch": self.first_touch,
                "free_kicks": self.free_kicks,
                "heading": self.heading,
                "long_shots": self.long_shots,
                "long_throws": self.long_throws,
                "marking": self.marking,
                "passing": self.passing,
                "penalty": self.penalty,
                "tackling": self.tackling,
                "technique": self.technique,
            },
            # Mental attributes
            "mental": {
                "aggression": self.aggression,
                "anticipation": self.anticipation,
                "bravery": self.bravery,
                "composure": self.composure,
                "concentration": self.concentration,
                "decisions": self.decisions,
                "determination": self.determination,
                "flair": self.flair,
                "leadership": self.leadership,
                "off_the_ball": self.off_the_ball,
                "positioning": self.positioning,
                "teamwork": self.teamwork,
                "vision": self.vision,
                "work_rate": self.work_rate,
            },
            # Physical attributes
            "physical": {
                "acceleration": self.acceleration,
                "agility": self.agility,
                "balance": self.balance,
                "jumping": self.jumping,
                "stamina": self.stamina,
                "pace": self.pace,
                "endurance": self.endurance,
                "strength": self.strength,
            },
            # Financial
            "financial": {
                "price": self.price,
                "wage": self.wage,
            },
            # Physical stats
            "physical_stats": {
                "height": self.height,
                "weight": self.weight,
                "left_foot": self.left_foot,
                "right_foot": self.right_foot,
            },
            # Player traits
            "traits": self.traits,
        }
    
    def get_technical_average(self) -> float:
        """
        Calculate average of all technical attributes.
        
        Returns:
            float: Average technical attribute value
        """
        technical_attrs = [
            self.corners, self.crossing, self.dribbling, self.finishing,
            self.first_touch, self.free_kicks, self.heading, self.long_shots,
            self.long_throws, self.marking, self.passing, self.penalty,
            self.tackling, self.technique
        ]
        return sum(technical_attrs) / len(technical_attrs)
    
    def get_mental_average(self) -> float:
        """
        Calculate average of all mental attributes.
        
        Returns:
            float: Average mental attribute value
        """
        mental_attrs = [
            self.aggression, self.anticipation, self.bravery, self.composure,
            self.concentration, self.decisions, self.determination, self.flair,
            self.leadership, self.off_the_ball, self.positioning, self.teamwork,
            self.vision, self.work_rate
        ]
        return sum(mental_attrs) / len(mental_attrs)
    
    def get_physical_average(self) -> float:
        """
        Calculate average of all physical attributes.
        
        Returns:
            float: Average physical attribute value
        """
        physical_attrs = [
            self.acceleration, self.agility, self.balance, self.jumping,
            self.stamina, self.pace, self.endurance, self.strength
        ]
        return sum(physical_attrs) / len(physical_attrs)
    
    @staticmethod
    def build_search_vector(name: str, position: str, club: str, nationality: str):
        """
        Build a tsvector for full-text search from player fields.
        
        This is a helper method for constructing search vectors programmatically.
        The actual GIN index uses a similar expression defined in __table_args__.
        
        Args:
            name: Player name
            position: Player position(s)
            club: Club name
            nationality: Player nationality
            
        Returns:
            SQLAlchemy expression for tsvector
        """
        from sqlalchemy import func
        return func.to_tsvector(
            'simple',
            func.coalesce(name, '') + ' ' +
            func.coalesce(position, '') + ' ' +
            func.coalesce(club, '') + ' ' +
            func.coalesce(nationality, '')
        )
    
    @staticmethod
    def search_query_expression(search_text: str):
        """
        Build a tsquery expression for full-text search.
        
        This helper method creates the query expression that matches against
        the GIN index. Use with SQLAlchemy filter to perform full-text search.
        
        Args:
            search_text: Search query text (e.g., "Messi Barcelona")
            
        Returns:
            SQLAlchemy boolean expression for filtering
            
        Example:
            from sqlalchemy import select
            from app.models.player import Player
            
            # Search for players
            stmt = select(Player).where(
                Player.search_query_expression("Ronaldo Portugal")
            ).limit(50)
        """
        from sqlalchemy import func, cast, String
        
        # Build the tsvector expression (same as in the GIN index)
        search_vector = func.to_tsvector(
            'simple',
            func.coalesce(cast(Player.name, String), '') + ' ' +
            func.coalesce(cast(Player.position, String), '') + ' ' +
            func.coalesce(cast(Player.club, String), '') + ' ' +
            func.coalesce(cast(Player.nationality, String), '')
        )
        
        # Build the tsquery from search text
        search_query = func.plainto_tsquery('simple', search_text)
        
        # Return the match expression
        return search_vector.op('@@')(search_query)
    
    @staticmethod
    def search_rank_expression(search_text: str):
        """
        Build a ts_rank expression for relevance scoring.
        
        This helper method creates a relevance score expression that can be used
        for ordering search results by relevance.
        
        Args:
            search_text: Search query text
            
        Returns:
            SQLAlchemy expression for relevance ranking
            
        Example:
            from sqlalchemy import select
            from app.models.player import Player
            
            # Search and order by relevance
            rank = Player.search_rank_expression("Messi")
            stmt = select(Player, rank.label('rank')).where(
                Player.search_query_expression("Messi")
            ).order_by(rank.desc()).limit(50)
        """
        from sqlalchemy import func, cast, String
        
        # Build the tsvector expression (same as in the GIN index)
        search_vector = func.to_tsvector(
            'simple',
            func.coalesce(cast(Player.name, String), '') + ' ' +
            func.coalesce(cast(Player.position, String), '') + ' ' +
            func.coalesce(cast(Player.club, String), '') + ' ' +
            func.coalesce(cast(Player.nationality, String), '')
        )
        
        # Build the tsquery from search text
        search_query = func.plainto_tsquery('simple', search_text)
        
        # Return the rank expression
        return func.ts_rank(search_vector, search_query)
