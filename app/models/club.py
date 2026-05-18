"""
Club Model - Represents football clubs with infrastructure and financial data
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, CheckConstraint, Index, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Club(Base):
    """
    Club model representing football clubs in the game.
    
    Clubs have infrastructure across 5 categories (Stadium, Training Facilities,
    Youth Academy, Medical Centre, Scouting Network), each with 5 upgrade levels.
    Clubs also track financial data including balance, budgets, and revenue streams.
    
    Infrastructure Levels (1-5):
        1 = Basic
        2 = Standard
        3 = Good
        4 = Excellent
        5 = World Class
    
    Attributes:
        id: Primary key, auto-increment
        name: Club name (indexed for search)
        reputation: Club reputation (1-100)
        league: League name (indexed)
        country: Country name
        
        Infrastructure levels (1-5 each):
            stadium_level: Stadium quality level
            training_facilities_level: Training facilities quality level
            youth_academy_level: Youth academy quality level
            medical_centre_level: Medical centre quality level
            scouting_network_level: Scouting network quality level
        
        Financial fields:
            balance: Current club balance (can be negative)
            transfer_budget: Available transfer budget
            wage_budget: Weekly wage bill
            matchday_revenue: Revenue per match
        
        Stadium:
            stadium_capacity: Maximum stadium capacity
            stadium_name: Name of the stadium
        
        Timestamps:
            created_at: Timestamp when club was created
            updated_at: Timestamp when club was last updated
    """
    
    __tablename__ = "clubs"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Club name"
    )
    
    reputation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Club reputation (1-100)"
    )
    
    league: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="League name"
    )
    
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Country name"
    )
    
    # Infrastructure Levels (1-5 each)
    # 1 = Basic, 2 = Standard, 3 = Good, 4 = Excellent, 5 = World Class
    stadium_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Stadium quality level (1-5)"
    )
    
    training_facilities_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Training facilities quality level (1-5)"
    )
    
    youth_academy_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Youth academy quality level (1-5)"
    )
    
    medical_centre_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Medical centre quality level (1-5)"
    )
    
    scouting_network_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Scouting network quality level (1-5)"
    )
    
    # Financial Fields
    balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Current club balance (can be negative)"
    )
    
    transfer_budget: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Available transfer budget"
    )
    
    wage_budget: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Weekly wage bill"
    )
    
    matchday_revenue: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Revenue per match"
    )
    
    # Stadium Information
    stadium_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10000,
        server_default="10000",
        comment="Maximum stadium capacity"
    )
    
    stadium_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of the stadium"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when club was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when club was last updated"
    )
    
    # Check constraints and indexes
    __table_args__ = (
        # Reputation constraint (1-100)
        CheckConstraint('reputation >= 1 AND reputation <= 100', name='check_reputation_range'),
        
        # Infrastructure level constraints (1-5)
        CheckConstraint('stadium_level >= 1 AND stadium_level <= 5', name='check_stadium_level_range'),
        CheckConstraint('training_facilities_level >= 1 AND training_facilities_level <= 5', name='check_training_facilities_level_range'),
        CheckConstraint('youth_academy_level >= 1 AND youth_academy_level <= 5', name='check_youth_academy_level_range'),
        CheckConstraint('medical_centre_level >= 1 AND medical_centre_level <= 5', name='check_medical_centre_level_range'),
        CheckConstraint('scouting_network_level >= 1 AND scouting_network_level <= 5', name='check_scouting_network_level_range'),
        
        # Stadium capacity constraint (> 0)
        CheckConstraint('stadium_capacity > 0', name='check_stadium_capacity_positive'),
        
        # Performance indexes
        Index('idx_clubs_name', 'name'),
        Index('idx_clubs_league', 'league'),
        Index('idx_clubs_reputation', 'reputation'),
        Index('idx_clubs_country', 'country'),
        # Composite index for common search patterns
        Index('idx_clubs_league_reputation', 'league', 'reputation'),
    )
    
    def __repr__(self) -> str:
        """String representation of Club"""
        return (
            f"<Club(id={self.id}, "
            f"name={self.name}, "
            f"league={self.league}, "
            f"reputation={self.reputation})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Club model to dictionary.
        
        Returns:
            dict: Dictionary representation of the club with all attributes
        """
        return {
            "id": self.id,
            "name": self.name,
            "reputation": self.reputation,
            "league": self.league,
            "country": self.country,
            # Infrastructure
            "infrastructure": {
                "stadium_level": self.stadium_level,
                "training_facilities_level": self.training_facilities_level,
                "youth_academy_level": self.youth_academy_level,
                "medical_centre_level": self.medical_centre_level,
                "scouting_network_level": self.scouting_network_level,
            },
            # Financial
            "financial": {
                "balance": self.balance,
                "transfer_budget": self.transfer_budget,
                "wage_budget": self.wage_budget,
                "matchday_revenue": self.matchday_revenue,
            },
            # Stadium
            "stadium": {
                "capacity": self.stadium_capacity,
                "name": self.stadium_name,
            },
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_infrastructure_level_name(self, level: int) -> str:
        """
        Get the name of an infrastructure level.
        
        Args:
            level: Infrastructure level (1-5)
        
        Returns:
            str: Name of the infrastructure level
        """
        level_names = {
            1: "Basic",
            2: "Standard",
            3: "Good",
            4: "Excellent",
            5: "World Class"
        }
        return level_names.get(level, "Unknown")
    
    def get_average_infrastructure_level(self) -> float:
        """
        Calculate average infrastructure level across all categories.
        
        Returns:
            float: Average infrastructure level (1-5)
        """
        infrastructure_levels = [
            self.stadium_level,
            self.training_facilities_level,
            self.youth_academy_level,
            self.medical_centre_level,
            self.scouting_network_level
        ]
        return sum(infrastructure_levels) / len(infrastructure_levels)
    
    def can_afford_transfer(self, transfer_fee: int) -> bool:
        """
        Check if the club can afford a transfer fee.
        
        Args:
            transfer_fee: Transfer fee amount
        
        Returns:
            bool: True if club can afford the transfer, False otherwise
        """
        return self.transfer_budget >= transfer_fee
    
    def can_afford_wage(self, weekly_wage: int) -> bool:
        """
        Check if the club can afford additional weekly wage.
        
        Args:
            weekly_wage: Additional weekly wage amount
        
        Returns:
            bool: True if club can afford the wage, False otherwise
        """
        # Simple check - in reality this would be more complex
        # considering total wage budget limits
        return self.balance > 0 or weekly_wage <= (self.transfer_budget // 52)
    
    def is_financially_healthy(self) -> bool:
        """
        Check if the club is financially healthy.
        
        Returns:
            bool: True if club balance is positive, False otherwise
        """
        return self.balance >= 0
