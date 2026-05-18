"""
Player Schemas - Request/Response models for player-related API endpoints
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class PlayerSearchRequest(BaseModel):
    """
    Request model for player search endpoint.
    
    All fields are optional and can be combined. When multiple filters are
    provided, they are combined with AND logic (all must match).
    """
    
    # Full-text search
    search_text: Optional[str] = Field(
        None,
        description="Full-text search query (searches name, position, club, nationality)",
        examples=["Messi", "Barcelona", "Argentina"]
    )
    
    # Position filter
    position: Optional[str] = Field(
        None,
        description="Filter by position (supports partial match, e.g., 'ST' matches 'AM/ST RL')",
        examples=["ST", "AM", "DC"]
    )
    
    # Age filters
    min_age: Optional[int] = Field(
        None,
        ge=15,
        le=50,
        description="Minimum age (inclusive, 15-50)",
        examples=[18]
    )
    max_age: Optional[int] = Field(
        None,
        ge=15,
        le=50,
        description="Maximum age (inclusive, 15-50)",
        examples=[30]
    )
    
    # Current Ability (CA) filters
    min_ca: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description="Minimum Current Ability (inclusive, 1-200)",
        examples=[150]
    )
    max_ca: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description="Maximum Current Ability (inclusive, 1-200)",
        examples=[200]
    )
    
    # Potential Ability (PA) filters
    min_pa: Optional[int] = Field(
        None,
        ge=-200,
        le=200,
        description="Minimum Potential Ability (inclusive, -200 to 200)",
        examples=[160]
    )
    max_pa: Optional[int] = Field(
        None,
        ge=-200,
        le=200,
        description="Maximum Potential Ability (inclusive, -200 to 200)",
        examples=[200]
    )
    
    # Nationality filter
    nationality: Optional[str] = Field(
        None,
        description="Filter by nationality (exact match)",
        examples=["Argentina", "Brazil", "Spain"]
    )
    
    # Club filter
    club: Optional[str] = Field(
        None,
        description="Filter by club (exact match)",
        examples=["Barcelona", "Real Madrid", "Manchester United"]
    )
    
    # Pagination
    limit: int = Field(
        50,
        ge=1,
        le=200,
        description="Maximum number of results to return (1-200)",
        examples=[50]
    )
    offset: int = Field(
        0,
        ge=0,
        description="Number of results to skip for pagination",
        examples=[0]
    )
    
    # Sorting
    order_by: str = Field(
        "relevance",
        description="Sort order: 'relevance' (requires search_text), 'ca', 'pa', 'age', or 'name'",
        examples=["ca", "relevance"]
    )
    
    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, v: str) -> str:
        """Validate order_by field"""
        valid_orders = ["relevance", "ca", "pa", "age", "name"]
        if v not in valid_orders:
            raise ValueError(f"order_by must be one of: {', '.join(valid_orders)}")
        return v
    
    @field_validator("min_age", "max_age")
    @classmethod
    def validate_age_range(cls, v: Optional[int], info) -> Optional[int]:
        """Validate age range"""
        if v is not None:
            if info.field_name == "min_age" and v < 15:
                raise ValueError("min_age must be at least 15")
            if info.field_name == "max_age" and v > 50:
                raise ValueError("max_age must be at most 50")
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "search_text": "Messi",
                    "min_ca": 150,
                    "position": "ST",
                    "nationality": "Argentina",
                    "limit": 20,
                    "offset": 0,
                    "order_by": "ca"
                }
            ]
        }
    }


class PlayerResponse(BaseModel):
    """
    Response model for a single player.
    
    Contains all player attributes from the database.
    """
    
    # Identity
    uid: str = Field(description="Unique player identifier (database id as string)")
    id: Optional[int] = Field(default=None, description="Numeric database id")
    name: str = Field(description="Player name")
    position: str = Field(description="Player position(s), e.g., 'AM/ST RL'")
    age: int = Field(description="Player age")
    nationality: str = Field(description="Player nationality")
    club: str = Field(description="Current club")
    
    # Core Attributes
    ca: int = Field(description="Current Ability (1-200)")
    pa: int = Field(description="Potential Ability (-200 to 200)")
    
    # Technical Attributes (1-20 each)
    corners: int = Field(description="Corners attribute")
    crossing: int = Field(description="Crossing attribute")
    dribbling: int = Field(description="Dribbling attribute")
    finishing: int = Field(description="Finishing attribute")
    first_touch: int = Field(description="First Touch attribute")
    free_kicks: int = Field(description="Free Kicks attribute")
    heading: int = Field(description="Heading attribute")
    long_shots: int = Field(description="Long Shots attribute")
    long_throws: int = Field(description="Long Throws attribute")
    marking: int = Field(description="Marking attribute")
    passing: int = Field(description="Passing attribute")
    penalty: int = Field(description="Penalty Taking attribute")
    tackling: int = Field(description="Tackling attribute")
    technique: int = Field(description="Technique attribute")
    
    # Mental Attributes (1-20 each)
    aggression: int = Field(description="Aggression attribute")
    anticipation: int = Field(description="Anticipation attribute")
    bravery: int = Field(description="Bravery attribute")
    composure: int = Field(description="Composure attribute")
    concentration: int = Field(description="Concentration attribute")
    decisions: int = Field(description="Decisions attribute")
    determination: int = Field(description="Determination attribute")
    flair: int = Field(description="Flair attribute")
    leadership: int = Field(description="Leadership attribute")
    off_the_ball: int = Field(description="Off The Ball attribute")
    positioning: int = Field(description="Positioning attribute")
    teamwork: int = Field(description="Teamwork attribute")
    vision: int = Field(description="Vision attribute")
    work_rate: int = Field(description="Work Rate attribute")
    
    # Physical Attributes (1-20 each)
    acceleration: int = Field(description="Acceleration attribute")
    agility: int = Field(description="Agility attribute")
    balance: int = Field(description="Balance attribute")
    jumping: int = Field(description="Jumping Reach attribute")
    stamina: int = Field(description="Stamina attribute")
    pace: int = Field(description="Pace attribute")
    endurance: int = Field(description="Natural Fitness attribute")
    strength: int = Field(description="Strength attribute")
    
    # Financial
    price: str = Field(description="Market value")
    wage: int = Field(description="Weekly wage")
    
    # Physical Stats
    height: int = Field(description="Height in cm")
    weight: int = Field(description="Weight in kg")
    left_foot: int = Field(description="Left Foot ability (1-20)")
    right_foot: int = Field(description="Right Foot ability (1-20)")
    
    # Metadata
    traits: Optional[str] = Field(None, description="Playing style traits (comma-separated)")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "uid": "player_001",
                    "name": "Lionel Messi",
                    "position": "AM/ST RL",
                    "age": 36,
                    "nationality": "Argentina",
                    "club": "Inter Miami",
                    "ca": 180,
                    "pa": 200,
                    "corners": 18,
                    "crossing": 17,
                    "dribbling": 20,
                    "finishing": 19,
                    "first_touch": 20,
                    "free_kicks": 19,
                    "heading": 10,
                    "long_shots": 18,
                    "long_throws": 8,
                    "marking": 8,
                    "passing": 19,
                    "penalty": 18,
                    "tackling": 7,
                    "technique": 20,
                    "aggression": 12,
                    "anticipation": 19,
                    "bravery": 14,
                    "composure": 20,
                    "concentration": 18,
                    "decisions": 19,
                    "determination": 18,
                    "flair": 20,
                    "leadership": 16,
                    "off_the_ball": 19,
                    "positioning": 18,
                    "teamwork": 17,
                    "vision": 20,
                    "work_rate": 15,
                    "acceleration": 16,
                    "agility": 18,
                    "balance": 19,
                    "jumping": 10,
                    "stamina": 15,
                    "pace": 16,
                    "endurance": 16,
                    "strength": 11,
                    "price": "50M",
                    "wage": 500000,
                    "height": 170,
                    "weight": 67,
                    "left_foot": 20,
                    "right_foot": 12,
                    "traits": "Dribbles Often, Finesse Shot, Playmaker"
                }
            ]
        }
    }


class PlayerSearchResponse(BaseModel):
    """
    Response model for player search endpoint.
    
    Contains paginated search results with metadata.
    """
    
    players: List[PlayerResponse] = Field(
        description="List of matching players"
    )
    total: int = Field(
        description="Total number of matching players (before pagination)"
    )
    limit: int = Field(
        description="Applied limit (max results per page)"
    )
    offset: int = Field(
        description="Applied offset (number of results skipped)"
    )
    has_more: bool = Field(
        description="Whether more results exist beyond this page"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "players": [
                        {
                            "uid": "player_001",
                            "name": "Lionel Messi",
                            "position": "AM/ST RL",
                            "age": 36,
                            "nationality": "Argentina",
                            "club": "Inter Miami",
                            "ca": 180,
                            "pa": 200
                        }
                    ],
                    "total": 1,
                    "limit": 50,
                    "offset": 0,
                    "has_more": False
                }
            ]
        }
    }


class FilterOptionsResponse(BaseModel):
    """
    Response model for filter options endpoint.
    
    Provides available filter values to help build search UIs.
    """
    
    positions: List[str] = Field(
        description="List of unique positions available in the database"
    )
    nationalities: List[str] = Field(
        description="List of unique nationalities (sorted alphabetically)"
    )
    clubs: List[str] = Field(
        description="List of unique clubs (sorted alphabetically)"
    )
    age_range: dict = Field(
        description="Age range with 'min' and 'max' keys"
    )
    ca_range: dict = Field(
        description="Current Ability range with 'min' and 'max' keys"
    )
    pa_range: dict = Field(
        description="Potential Ability range with 'min' and 'max' keys"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "positions": ["GK", "DC", "DL", "DR", "DM", "MC", "ML", "MR", "AM", "ST"],
                    "nationalities": ["Argentina", "Brazil", "England", "France", "Germany", "Italy", "Spain"],
                    "clubs": ["Barcelona", "Real Madrid", "Manchester United", "Bayern Munich"],
                    "age_range": {"min": 16, "max": 42},
                    "ca_range": {"min": 50, "max": 200},
                    "pa_range": {"min": -200, "max": 200}
                }
            ]
        }
    }
