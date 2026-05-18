"""
Staff Model - Represents club staff members (coaches, scouts, medical staff, etc.)
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


class StaffRole(str, enum.Enum):
    """Staff role enumeration"""
    ASSISTANT_MANAGER = "assistant_manager"
    FITNESS_COACH = "fitness_coach"
    GOALKEEPING_COACH = "goalkeeping_coach"
    DEFENSIVE_COACH = "defensive_coach"
    ATTACKING_COACH = "attacking_coach"
    CHIEF_SCOUT = "chief_scout"
    PHYSIO = "physio"
    SPORTS_SCIENTIST = "sports_scientist"


class Staff(Base):
    """
    Staff model representing club staff members including coaches, scouts, and medical staff.
    
    Staff members provide bonuses to various aspects of club management based on their
    role and attributes. Each staff member has a contract with wage and expiry date,
    and their morale affects their effectiveness.
    
    Staff Roles (8 total):
        - ASSISTANT_MANAGER: Assists with tactical decisions and team management
        - FITNESS_COACH: Improves fitness training effectiveness
        - GOALKEEPING_COACH: Improves goalkeeper training and development
        - DEFENSIVE_COACH: Improves defensive training and tactics
        - ATTACKING_COACH: Improves attacking training and tactics
        - CHIEF_SCOUT: Reduces scouting report generation time and improves accuracy
        - PHYSIO: Reduces injury recovery time
        - SPORTS_SCIENTIST: Improves overall player performance analysis
    
    Staff Attributes (1-20 each):
        - coaching: General coaching ability (relevant for all coach roles)
        - tactical_knowledge: Understanding of tactics and formations
        - man_management: Ability to manage and motivate players
        - scouting: Scouting ability (relevant for Chief Scout)
        - medical: Medical knowledge (relevant for Physio)
        - fitness: Fitness training expertise (relevant for Fitness Coach)
        - technical: Technical coaching ability
        - mental: Mental coaching ability
    
    Bonuses:
        - Fitness Coach with coaching > 15: +10% fitness training effectiveness
        - Chief Scout with scouting > 15: -20% scouting report generation time
        - Physio with medical > 15: -10% injury recovery time per level
        - Other roles provide similar bonuses based on their attributes
    
    Attributes:
        id: Primary key, auto-increment
        career_id: Foreign key to Career (career context)
        club_id: Foreign key to Club (employing club)
        
        Basic Information:
            name: Staff member's full name
            role: Staff role (one of 8 roles)
            age: Staff member's age
            nationality: Staff member's nationality
        
        Staff Attributes (1-20 each):
            coaching: General coaching ability
            tactical_knowledge: Tactical understanding
            man_management: Player management ability
            scouting: Scouting ability
            medical: Medical knowledge
            fitness: Fitness training expertise
            technical: Technical coaching ability
            mental: Mental coaching ability
        
        Contract Details:
            wage: Weekly wage
            contract_start_date: Date when contract started
            contract_expiry_date: Date when contract expires
            contract_years: Contract duration in years (1-5)
        
        Performance:
            morale: Staff morale (1-100)
            performance_rating: Performance rating (1-20)
        
        Timestamps:
            created_at: Timestamp when staff record was created
            updated_at: Timestamp when staff record was last updated
    """
    
    __tablename__ = "staff"
    
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
    
    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to Club (employing club)"
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Staff member's full name"
    )
    
    role: Mapped[StaffRole] = mapped_column(
        SQLEnum(StaffRole, name="staff_role_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Staff role (assistant_manager, fitness_coach, etc.)"
    )
    
    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Staff member's age"
    )
    
    nationality: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Staff member's nationality"
    )
    
    # Staff Attributes (1-20 each)
    coaching: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="General coaching ability (1-20)"
    )
    
    tactical_knowledge: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Tactical understanding (1-20)"
    )
    
    man_management: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Player management ability (1-20)"
    )
    
    scouting: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Scouting ability (1-20)"
    )
    
    medical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Medical knowledge (1-20)"
    )
    
    fitness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Fitness training expertise (1-20)"
    )
    
    technical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Technical coaching ability (1-20)"
    )
    
    mental: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Mental coaching ability (1-20)"
    )
    
    # Contract Details
    wage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Weekly wage"
    )
    
    contract_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Date when contract started"
    )
    
    contract_expiry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Date when contract expires"
    )
    
    contract_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Contract duration in years (1-5)"
    )
    
    # Performance
    morale: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default="70",
        comment="Staff morale (1-100)"
    )
    
    performance_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        comment="Performance rating (1-20)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when staff record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when staff record was last updated"
    )
    
    # Relationships (will be populated when related models are created)
    # career: Mapped["Career"] = relationship("Career", back_populates="staff")
    # club: Mapped["Club"] = relationship("Club", back_populates="staff")
    
    # Check constraints and indexes
    __table_args__ = (
        # Age constraint (18-80)
        CheckConstraint('age >= 18 AND age <= 80', name='check_staff_age_range'),
        
        # Staff attribute constraints (1-20 each)
        CheckConstraint('coaching >= 1 AND coaching <= 20', name='check_coaching_range'),
        CheckConstraint('tactical_knowledge >= 1 AND tactical_knowledge <= 20', name='check_tactical_knowledge_range'),
        CheckConstraint('man_management >= 1 AND man_management <= 20', name='check_man_management_range'),
        CheckConstraint('scouting >= 1 AND scouting <= 20', name='check_scouting_range'),
        CheckConstraint('medical >= 1 AND medical <= 20', name='check_medical_range'),
        CheckConstraint('fitness >= 1 AND fitness <= 20', name='check_fitness_range'),
        CheckConstraint('technical >= 1 AND technical <= 20', name='check_technical_range'),
        CheckConstraint('mental >= 1 AND mental <= 20', name='check_mental_range'),
        
        # Wage constraint (positive)
        CheckConstraint('wage > 0', name='check_wage_positive'),
        
        # Contract years constraint (1-5)
        CheckConstraint('contract_years >= 1 AND contract_years <= 5', name='check_contract_years_range'),
        
        # Morale constraint (1-100)
        CheckConstraint('morale >= 1 AND morale <= 100', name='check_morale_range'),
        
        # Performance rating constraint (1-20)
        CheckConstraint('performance_rating >= 1 AND performance_rating <= 20', name='check_performance_rating_range'),
        
        # Contract date constraint (expiry must be after start)
        CheckConstraint('contract_expiry_date > contract_start_date', name='check_contract_dates_valid'),
        
        # Performance indexes
        Index('idx_staff_career_id', 'career_id'),
        Index('idx_staff_club_id', 'club_id'),
        Index('idx_staff_name', 'name'),
        Index('idx_staff_role', 'role'),
        Index('idx_staff_contract_expiry_date', 'contract_expiry_date'),
        # Composite indexes for common query patterns
        Index('idx_staff_career_role', 'career_id', 'role'),
        Index('idx_staff_club_role', 'club_id', 'role'),
        Index('idx_staff_career_expiry', 'career_id', 'contract_expiry_date'),
    )
    
    def __repr__(self) -> str:
        """String representation of Staff"""
        return (
            f"<Staff(id={self.id}, "
            f"name={self.name}, "
            f"role={self.role.value}, "
            f"club_id={self.club_id})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Staff model to dictionary.
        
        Returns:
            dict: Dictionary representation of the staff member with all attributes
        """
        return {
            "id": self.id,
            "career_id": self.career_id,
            "club_id": self.club_id,
            # Basic information
            "name": self.name,
            "role": self.role.value,
            "age": self.age,
            "nationality": self.nationality,
            # Staff attributes
            "attributes": {
                "coaching": self.coaching,
                "tactical_knowledge": self.tactical_knowledge,
                "man_management": self.man_management,
                "scouting": self.scouting,
                "medical": self.medical,
                "fitness": self.fitness,
                "technical": self.technical,
                "mental": self.mental,
            },
            # Contract details
            "contract": {
                "wage": self.wage,
                "contract_start_date": self.contract_start_date.isoformat() if self.contract_start_date else None,
                "contract_expiry_date": self.contract_expiry_date.isoformat() if self.contract_expiry_date else None,
                "contract_years": self.contract_years,
            },
            # Performance
            "morale": self.morale,
            "performance_rating": self.performance_rating,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_role_display_name(self) -> str:
        """
        Get human-readable display name for staff role.
        
        Returns:
            str: Display name for the role
        """
        role_names = {
            StaffRole.ASSISTANT_MANAGER: "Assistant Manager",
            StaffRole.FITNESS_COACH: "Fitness Coach",
            StaffRole.GOALKEEPING_COACH: "Goalkeeping Coach",
            StaffRole.DEFENSIVE_COACH: "Defensive Coach",
            StaffRole.ATTACKING_COACH: "Attacking Coach",
            StaffRole.CHIEF_SCOUT: "Chief Scout",
            StaffRole.PHYSIO: "Physio",
            StaffRole.SPORTS_SCIENTIST: "Sports Scientist",
        }
        return role_names.get(self.role, "Unknown")
    
    def get_primary_attribute(self) -> int:
        """
        Get the primary attribute value for this staff member's role.
        
        Returns:
            int: Primary attribute value (1-20)
        """
        primary_attributes = {
            StaffRole.ASSISTANT_MANAGER: self.tactical_knowledge,
            StaffRole.FITNESS_COACH: self.fitness,
            StaffRole.GOALKEEPING_COACH: self.coaching,
            StaffRole.DEFENSIVE_COACH: self.coaching,
            StaffRole.ATTACKING_COACH: self.coaching,
            StaffRole.CHIEF_SCOUT: self.scouting,
            StaffRole.PHYSIO: self.medical,
            StaffRole.SPORTS_SCIENTIST: self.technical,
        }
        return primary_attributes.get(self.role, self.coaching)
    
    def get_average_attribute(self) -> float:
        """
        Calculate average attribute across all 8 attributes.
        
        Returns:
            float: Average attribute (1-20)
        """
        attributes = [
            self.coaching,
            self.tactical_knowledge,
            self.man_management,
            self.scouting,
            self.medical,
            self.fitness,
            self.technical,
            self.mental,
        ]
        return sum(attributes) / len(attributes)
    
    def is_high_morale(self) -> bool:
        """
        Check if staff member has high morale.
        
        Returns:
            bool: True if morale >= 70, False otherwise
        """
        return self.morale >= 70
    
    def is_low_morale(self) -> bool:
        """
        Check if staff member has low morale.
        
        Returns:
            bool: True if morale < 40, False otherwise
        """
        return self.morale < 40
    
    def is_contract_expiring_soon(self, weeks_threshold: int = 26) -> bool:
        """
        Check if contract is expiring soon (within specified weeks).
        
        Args:
            weeks_threshold: Number of weeks to consider as "soon" (default: 26 weeks = 6 months)
        
        Returns:
            bool: True if contract expires within threshold, False otherwise
        """
        from datetime import timedelta
        
        now = datetime.now(self.contract_expiry_date.tzinfo)
        threshold_date = now + timedelta(weeks=weeks_threshold)
        return self.contract_expiry_date <= threshold_date
    
    def get_contract_months_remaining(self) -> int:
        """
        Calculate months remaining on contract.
        
        Returns:
            int: Months remaining (0 if contract expired)
        """
        now = datetime.now(self.contract_expiry_date.tzinfo)
        if self.contract_expiry_date <= now:
            return 0
        
        delta = self.contract_expiry_date - now
        return max(0, delta.days // 30)
    
    def provides_fitness_bonus(self) -> bool:
        """
        Check if this staff member provides fitness training bonus.
        Fitness Coach with fitness attribute > 15 provides +10% bonus.
        
        Returns:
            bool: True if provides fitness bonus, False otherwise
        """
        return self.role == StaffRole.FITNESS_COACH and self.fitness > 15
    
    def provides_scouting_bonus(self) -> bool:
        """
        Check if this staff member provides scouting bonus.
        Chief Scout with scouting > 15 provides -20% scouting time.
        
        Returns:
            bool: True if provides scouting bonus, False otherwise
        """
        return self.role == StaffRole.CHIEF_SCOUT and self.scouting > 15
    
    def provides_medical_bonus(self) -> bool:
        """
        Check if this staff member provides medical bonus.
        Physio with medical > 15 provides -10% injury recovery time.
        
        Returns:
            bool: True if provides medical bonus, False otherwise
        """
        return self.role == StaffRole.PHYSIO and self.medical > 15
    
    def get_fitness_bonus_percentage(self) -> float:
        """
        Get fitness training bonus percentage.
        
        Returns:
            float: Bonus percentage (0.0-10.0)
        """
        if self.provides_fitness_bonus():
            return 10.0
        return 0.0
    
    def get_scouting_time_reduction_percentage(self) -> float:
        """
        Get scouting time reduction percentage.
        
        Returns:
            float: Time reduction percentage (0.0-20.0)
        """
        if self.provides_scouting_bonus():
            return 20.0
        return 0.0
    
    def get_injury_recovery_reduction_percentage(self) -> float:
        """
        Get injury recovery time reduction percentage.
        
        Returns:
            float: Recovery time reduction percentage (0.0-10.0)
        """
        if self.provides_medical_bonus():
            return 10.0
        return 0.0
    
    def is_elite_staff(self) -> bool:
        """
        Check if staff member is elite (primary attribute >= 18).
        
        Returns:
            bool: True if primary attribute >= 18, False otherwise
        """
        return self.get_primary_attribute() >= 18
    
    def is_good_staff(self) -> bool:
        """
        Check if staff member is good (primary attribute >= 15).
        
        Returns:
            bool: True if primary attribute >= 15, False otherwise
        """
        return self.get_primary_attribute() >= 15
    
    def update_morale(self, change: int) -> None:
        """
        Update staff morale by specified amount.
        
        Args:
            change: Morale change amount (positive or negative)
        """
        self.morale = max(1, min(100, self.morale + change))
    
    def update_performance_rating(self, new_rating: int) -> None:
        """
        Update staff performance rating.
        
        Args:
            new_rating: New performance rating (1-20)
        """
        self.performance_rating = max(1, min(20, new_rating))
    
    def renew_contract(self, years: int, new_wage: int) -> None:
        """
        Renew staff contract with new duration and wage.
        
        Args:
            years: Contract duration in years (1-5)
            new_wage: New weekly wage
        """
        from datetime import timedelta
        
        tz = getattr(self.contract_expiry_date, 'tzinfo', None) if self.contract_expiry_date else None
        now = datetime.now(tz)
        self.contract_start_date = now
        self.contract_expiry_date = now + timedelta(days=365 * years)
        self.contract_years = years
        self.wage = new_wage
