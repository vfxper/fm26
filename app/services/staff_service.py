"""
Staff Service - Handles staff hiring, firing, and management

This module implements staff management functionality for hiring and managing
up to 5 specialist coaches and other staff members.

Key Features:
- Hire up to 5 specialist coaches
- Calculate coach bonuses for training
- Manage staff contracts and wages
- Track staff morale and performance
- Negotiate staff contracts (1-5 years)
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.staff import Staff, StaffRole
from app.models.scouting_assignment import ScoutingAssignment, AssignmentType, AssignmentStatus
from app.models.training_schedule import TrainingFocus
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NegotiationResult:
    """Result of a staff contract negotiation."""
    outcome: str  # "accepted", "counter_offer", "rejected"
    offered_years: int
    offered_wage: int
    counter_years: Optional[int] = None
    counter_wage: Optional[int] = None
    reason: str = ""


class StaffService:
    """
    Service for managing club staff including coaches, scouts, and medical staff.
    
    Implements Requirement 10.5: "THE Training_Module SHALL allow the player-manager
    to hire up to 5 specialist coaches, each providing a bonus to a specific training area."
    """
    
    # Maximum number of specialist coaches allowed
    MAX_SPECIALIST_COACHES = 5
    
    # Coach roles that count towards the specialist coach limit
    SPECIALIST_COACH_ROLES = [
        StaffRole.FITNESS_COACH,
        StaffRole.GOALKEEPING_COACH,
        StaffRole.DEFENSIVE_COACH,
        StaffRole.ATTACKING_COACH,
    ]
    
    # All roles that can provide training bonuses (includes non-specialist staff)
    BONUS_ELIGIBLE_ROLES = [
        StaffRole.FITNESS_COACH,
        StaffRole.GOALKEEPING_COACH,
        StaffRole.DEFENSIVE_COACH,
        StaffRole.ATTACKING_COACH,
        StaffRole.ASSISTANT_MANAGER,
        StaffRole.SPORTS_SCIENTIST,
    ]
    
    # Bonus thresholds
    GOOD_COACH_THRESHOLD = 15  # Coaching attribute > 15 provides bonus
    BONUS_PERCENTAGE = 10.0    # 10% bonus for good coaches
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize StaffService.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session
    
    async def hire_staff(
        self,
        career_id: int,
        club_id: int,
        name: str,
        role: StaffRole,
        age: int,
        nationality: str,
        attributes: Dict[str, int],
        wage: int,
        contract_years: int
    ) -> Staff:
        """
        Hire a new staff member.
        
        Implements Requirement 10.2: "THE Career_Manager SHALL allow the player-manager
        to hire and fire staff within the constraints of the staff wage budget."
        
        Args:
            career_id: Career ID
            club_id: Club ID
            name: Staff member's name
            role: Staff role
            age: Staff member's age
            nationality: Staff member's nationality
            attributes: Dict of staff attributes (coaching, tactical_knowledge, etc.)
            wage: Weekly wage
            contract_years: Contract duration in years (1-5)
        
        Returns:
            Staff: Newly hired staff member
        
        Raises:
            ValueError: If specialist coach limit exceeded or invalid parameters
        """
        # Check specialist coach limit
        if role in self.SPECIALIST_COACH_ROLES:
            current_count = await self.count_specialist_coaches(career_id)
            if current_count >= self.MAX_SPECIALIST_COACHES:
                raise ValueError(
                    f"Cannot hire more than {self.MAX_SPECIALIST_COACHES} specialist coaches. "
                    f"Current count: {current_count}"
                )
        
        # Validate contract years
        if contract_years < 1 or contract_years > 5:
            raise ValueError("Contract years must be between 1 and 5")
        
        # Validate age
        if age < 18 or age > 80:
            raise ValueError("Staff age must be between 18 and 80")
        
        # Validate wage
        if wage <= 0:
            raise ValueError("Wage must be positive")
        
        # Check staff wage budget (only if club exists in DB)
        budget_check_passed = await self._check_staff_wage_budget(career_id, club_id, wage)
        if not budget_check_passed:
            status = await self.get_staff_wage_budget_status(career_id, club_id)
            raise ValueError(
                f"Cannot afford staff wage of {wage}/week. "
                f"Staff wage budget remaining: {status['remaining_budget']}/week "
                f"(allocation: {status['staff_wage_allocation']}/week, "
                f"current spending: {status['current_staff_wages']}/week)"
            )
        
        # Calculate contract dates
        contract_start_date = datetime.now()
        contract_expiry_date = contract_start_date + timedelta(days=365 * contract_years)
        
        # Create staff member
        staff = Staff(
            career_id=career_id,
            club_id=club_id,
            name=name,
            role=role,
            age=age,
            nationality=nationality,
            coaching=attributes.get("coaching", 10),
            tactical_knowledge=attributes.get("tactical_knowledge", 10),
            man_management=attributes.get("man_management", 10),
            scouting=attributes.get("scouting", 10),
            medical=attributes.get("medical", 10),
            fitness=attributes.get("fitness", 10),
            technical=attributes.get("technical", 10),
            mental=attributes.get("mental", 10),
            wage=wage,
            contract_start_date=contract_start_date,
            contract_expiry_date=contract_expiry_date,
            contract_years=contract_years,
            morale=70,  # Default starting morale
            performance_rating=10  # Default starting performance
        )
        
        self.db.add(staff)
        await self.db.commit()
        await self.db.refresh(staff)
        
        logger.info(
            f"Hired {role.value} {name} for career {career_id}, "
            f"wage: {wage}, contract: {contract_years} years"
        )
        
        return staff
    
    async def fire_staff(
        self,
        staff_id: int,
        career_id: int
    ) -> bool:
        """
        Fire a staff member.
        
        Args:
            staff_id: Staff ID
            career_id: Career ID (for validation)
        
        Returns:
            bool: True if staff was fired, False if not found
        """
        stmt = select(Staff).where(
            and_(
                Staff.id == staff_id,
                Staff.career_id == career_id
            )
        )
        
        result = await self.db.execute(stmt)
        staff = result.scalar_one_or_none()
        
        if not staff:
            logger.warning(f"Staff {staff_id} not found for career {career_id}")
            return False
        
        await self.db.delete(staff)
        await self.db.commit()
        
        logger.info(f"Fired {staff.role.value} {staff.name} from career {career_id}")
        
        return True
    
    async def count_specialist_coaches(self, career_id: int) -> int:
        """
        Count the number of specialist coaches currently employed.
        
        Args:
            career_id: Career ID
        
        Returns:
            int: Number of specialist coaches
        """
        stmt = select(func.count(Staff.id)).where(
            and_(
                Staff.career_id == career_id,
                Staff.role.in_(self.SPECIALIST_COACH_ROLES)
            )
        )
        
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        
        return count
    
    async def get_all_staff(self, career_id: int) -> List[Staff]:
        """
        Get all staff members for a career.
        
        Args:
            career_id: Career ID
        
        Returns:
            List[Staff]: List of all staff members
        """
        stmt = select(Staff).where(Staff.career_id == career_id)
        
        result = await self.db.execute(stmt)
        staff_list = result.scalars().all()
        
        return list(staff_list)
    
    async def get_staff_by_role(
        self,
        career_id: int,
        role: StaffRole
    ) -> Optional[Staff]:
        """
        Get staff member by role.
        
        Args:
            career_id: Career ID
            role: Staff role
        
        Returns:
            Optional[Staff]: Staff member or None if not found
        """
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.role == role
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_coach_bonuses(
        self,
        career_id: int
    ) -> Dict[TrainingFocus, float]:
        """
        Calculate coach bonuses for each training focus area.
        
        Implements Requirement 10.6: "THE Training_Module SHALL apply coach bonuses
        to training effectiveness."
        
        Coaches provide bonuses based on their role and attributes:
        - Fitness Coach (fitness > 15): +10% to FITNESS training
        - Defensive Coach (coaching > 15): +10% to DEFENDING training
        - Attacking Coach (coaching > 15): +10% to ATTACKING training
        - Goalkeeping Coach (coaching > 15): +10% to INDIVIDUAL_TECHNICAL training
        - Assistant Manager (tactical_knowledge > 15): +10% to TACTICS training
        - Sports Scientist (technical > 15): +10% to INDIVIDUAL_MENTAL training
        
        Args:
            career_id: Career ID
        
        Returns:
            Dict[TrainingFocus, float]: Mapping of training focus to bonus multiplier
                (1.0 = no bonus, 1.1 = 10% bonus)
        """
        bonuses = {}
        
        # Get all staff that can provide training bonuses
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.role.in_(self.BONUS_ELIGIBLE_ROLES)
            )
        )
        
        result = await self.db.execute(stmt)
        coaches = result.scalars().all()
        
        for coach in coaches:
            # Check if coach provides bonus (primary attribute > 15)
            primary_attr = coach.get_primary_attribute()
            
            if primary_attr > self.GOOD_COACH_THRESHOLD:
                bonus_multiplier = 1.0 + (self.BONUS_PERCENTAGE / 100.0)
                
                # Map coach role to training focus
                if coach.role == StaffRole.FITNESS_COACH:
                    bonuses[TrainingFocus.FITNESS] = bonus_multiplier
                    logger.debug(
                        f"Fitness Coach {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to FITNESS training"
                    )
                
                elif coach.role == StaffRole.DEFENSIVE_COACH:
                    bonuses[TrainingFocus.DEFENDING] = bonus_multiplier
                    logger.debug(
                        f"Defensive Coach {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to DEFENDING training"
                    )
                
                elif coach.role == StaffRole.ATTACKING_COACH:
                    bonuses[TrainingFocus.ATTACKING] = bonus_multiplier
                    logger.debug(
                        f"Attacking Coach {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to ATTACKING training"
                    )
                
                elif coach.role == StaffRole.GOALKEEPING_COACH:
                    bonuses[TrainingFocus.INDIVIDUAL_TECHNICAL] = bonus_multiplier
                    logger.debug(
                        f"Goalkeeping Coach {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to INDIVIDUAL_TECHNICAL training"
                    )
                
                elif coach.role == StaffRole.ASSISTANT_MANAGER:
                    bonuses[TrainingFocus.TACTICS] = bonus_multiplier
                    logger.debug(
                        f"Assistant Manager {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to TACTICS training"
                    )
                
                elif coach.role == StaffRole.SPORTS_SCIENTIST:
                    bonuses[TrainingFocus.INDIVIDUAL_MENTAL] = bonus_multiplier
                    logger.debug(
                        f"Sports Scientist {coach.name} provides {self.BONUS_PERCENTAGE}% "
                        f"bonus to INDIVIDUAL_MENTAL training"
                    )
        
        return bonuses
    
    async def get_staff_summary(self, career_id: int) -> Dict[str, any]:
        """
        Get summary of all staff for a career.
        
        Args:
            career_id: Career ID
        
        Returns:
            Dict containing:
                - total_staff: Total number of staff
                - specialist_coaches: Number of specialist coaches
                - total_wage_bill: Total weekly wage bill
                - staff_by_role: Dict mapping role to list of staff
                - expiring_contracts: List of staff with contracts expiring soon
        """
        staff_list = await self.get_all_staff(career_id)
        
        total_wage_bill = sum(s.wage for s in staff_list)
        specialist_coaches = [
            s for s in staff_list if s.role in self.SPECIALIST_COACH_ROLES
        ]
        
        # Group by role
        staff_by_role = {}
        for staff in staff_list:
            role_name = staff.role.value
            if role_name not in staff_by_role:
                staff_by_role[role_name] = []
            staff_by_role[role_name].append(staff.to_dict())
        
        # Find expiring contracts (< 6 months)
        expiring_contracts = [
            s.to_dict() for s in staff_list
            if s.is_contract_expiring_soon(weeks_threshold=26)
        ]
        
        return {
            "total_staff": len(staff_list),
            "specialist_coaches": len(specialist_coaches),
            "max_specialist_coaches": self.MAX_SPECIALIST_COACHES,
            "total_wage_bill": total_wage_bill,
            "staff_by_role": staff_by_role,
            "expiring_contracts": expiring_contracts
        }
    
    async def get_staff_management_view(
        self,
        career_id: int,
        club_id: int
    ) -> Dict[str, any]:
        """
        Get a comprehensive staff management view for the staff management screen.
        
        Implements Requirement 10.6: "THE Career_Manager SHALL display a staff management
        screen listing all current staff, their roles, attributes, and wages."
        
        This provides a detailed view including:
        1. All staff members grouped by role
        2. Each staff member's attributes, morale, contract status
        3. Available positions (unfilled roles)
        4. Specialist coach count vs limit (X/5)
        5. Total wage bill
        6. Staff with expiring contracts (< 6 months)
        7. Staff with low morale (< 40)
        8. Hiring recommendations (which roles would benefit the club most)
        
        Args:
            career_id: Career ID
            club_id: Club ID
        
        Returns:
            Dict containing comprehensive staff management data
        """
        # Get all staff for this career and club
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        result = await self.db.execute(stmt)
        staff_list = list(result.scalars().all())
        
        # 1. Group staff by role with full details
        staff_by_role: Dict[str, List[Dict]] = {}
        for role in StaffRole:
            staff_by_role[role.value] = []
        
        for staff in staff_list:
            staff_detail = {
                **staff.to_dict(),
                "role_display_name": staff.get_role_display_name(),
                "primary_attribute": staff.get_primary_attribute(),
                "average_attribute": round(staff.get_average_attribute(), 1),
                "contract_months_remaining": staff.get_contract_months_remaining(),
                "is_contract_expiring_soon": staff.is_contract_expiring_soon(weeks_threshold=26),
                "is_low_morale": staff.is_low_morale(),
                "is_high_morale": staff.is_high_morale(),
                "is_elite": staff.is_elite_staff(),
                "is_good": staff.is_good_staff(),
                "provides_bonus": self._staff_provides_bonus(staff),
            }
            staff_by_role[staff.role.value].append(staff_detail)
        
        # 2. Calculate specialist coach count
        specialist_count = sum(
            1 for s in staff_list if s.role in self.SPECIALIST_COACH_ROLES
        )
        
        # 3. Identify available (unfilled) positions
        filled_roles = set(s.role for s in staff_list)
        available_positions = [
            {
                "role": role.value,
                "display_name": self._get_role_display_name(role),
                "description": self._get_role_description(role),
            }
            for role in StaffRole
            if role not in filled_roles
        ]
        
        # 4. Total wage bill
        total_wage_bill = sum(s.wage for s in staff_list)
        
        # 5. Staff with expiring contracts (< 6 months / 26 weeks)
        expiring_contracts = [
            {
                "id": s.id,
                "name": s.name,
                "role": s.role.value,
                "role_display_name": s.get_role_display_name(),
                "contract_months_remaining": s.get_contract_months_remaining(),
                "contract_expiry_date": s.contract_expiry_date.isoformat() if s.contract_expiry_date else None,
                "wage": s.wage,
            }
            for s in staff_list
            if s.is_contract_expiring_soon(weeks_threshold=26)
        ]
        
        # 6. Staff with low morale (< 40)
        low_morale_staff = [
            {
                "id": s.id,
                "name": s.name,
                "role": s.role.value,
                "role_display_name": s.get_role_display_name(),
                "morale": s.morale,
            }
            for s in staff_list
            if s.is_low_morale()
        ]
        
        # 7. Hiring recommendations
        hiring_recommendations = self._generate_hiring_recommendations(
            staff_list, specialist_count
        )
        
        return {
            "career_id": career_id,
            "club_id": club_id,
            "total_staff": len(staff_list),
            "specialist_coaches_count": specialist_count,
            "max_specialist_coaches": self.MAX_SPECIALIST_COACHES,
            "specialist_coaches_display": f"{specialist_count}/{self.MAX_SPECIALIST_COACHES}",
            "total_wage_bill": total_wage_bill,
            "staff_by_role": staff_by_role,
            "available_positions": available_positions,
            "expiring_contracts": expiring_contracts,
            "low_morale_staff": low_morale_staff,
            "hiring_recommendations": hiring_recommendations,
        }
    
    def _staff_provides_bonus(self, staff: Staff) -> bool:
        """Check if a staff member provides any bonus based on their role and attributes."""
        return (
            staff.provides_fitness_bonus()
            or staff.provides_scouting_bonus()
            or staff.provides_medical_bonus()
            or (staff.role in self.BONUS_ELIGIBLE_ROLES and staff.get_primary_attribute() > self.GOOD_COACH_THRESHOLD)
        )
    
    def _get_role_display_name(self, role: StaffRole) -> str:
        """Get human-readable display name for a staff role."""
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
        return role_names.get(role, "Unknown")
    
    def _get_role_description(self, role: StaffRole) -> str:
        """Get description of what a staff role provides."""
        descriptions = {
            StaffRole.ASSISTANT_MANAGER: "Assists with tactical decisions and provides tactics training bonus",
            StaffRole.FITNESS_COACH: "Improves fitness training effectiveness (+10% bonus if fitness > 15)",
            StaffRole.GOALKEEPING_COACH: "Improves goalkeeper training and development",
            StaffRole.DEFENSIVE_COACH: "Improves defensive training and tactics",
            StaffRole.ATTACKING_COACH: "Improves attacking training and tactics",
            StaffRole.CHIEF_SCOUT: "Reduces scouting report time (-20% if scouting > 15)",
            StaffRole.PHYSIO: "Reduces injury recovery time (-10% if medical > 15)",
            StaffRole.SPORTS_SCIENTIST: "Improves player performance analysis and mental training",
        }
        return descriptions.get(role, "")
    
    def _generate_hiring_recommendations(
        self,
        staff_list: List[Staff],
        specialist_count: int
    ) -> List[Dict[str, any]]:
        """
        Generate hiring recommendations based on current staff composition.
        
        Recommends roles that would benefit the club most based on:
        - Missing key roles (Assistant Manager, Chief Scout, Physio)
        - Available specialist coach slots
        - Staff quality (low-attribute staff that could be upgraded)
        
        Args:
            staff_list: Current staff list
            specialist_count: Current specialist coach count
        
        Returns:
            List of hiring recommendations with priority and reason
        """
        recommendations = []
        filled_roles = {s.role: s for s in staff_list}
        
        # Priority 1: Missing essential roles
        essential_roles = [
            (StaffRole.ASSISTANT_MANAGER, "high", "Essential for tactical training bonus and team management"),
            (StaffRole.CHIEF_SCOUT, "high", "Essential for efficient scouting operations"),
            (StaffRole.PHYSIO, "high", "Essential for reducing injury recovery times"),
        ]
        
        for role, priority, reason in essential_roles:
            if role not in filled_roles:
                recommendations.append({
                    "role": role.value,
                    "role_display_name": self._get_role_display_name(role),
                    "priority": priority,
                    "reason": reason,
                })
        
        # Priority 2: Missing specialist coaches (if slots available)
        if specialist_count < self.MAX_SPECIALIST_COACHES:
            specialist_roles = [
                (StaffRole.FITNESS_COACH, "Improves fitness training effectiveness"),
                (StaffRole.DEFENSIVE_COACH, "Improves defensive training"),
                (StaffRole.ATTACKING_COACH, "Improves attacking training"),
                (StaffRole.GOALKEEPING_COACH, "Improves goalkeeper development"),
            ]
            
            for role, reason in specialist_roles:
                if role not in filled_roles:
                    recommendations.append({
                        "role": role.value,
                        "role_display_name": self._get_role_display_name(role),
                        "priority": "medium",
                        "reason": f"{reason} ({specialist_count}/{self.MAX_SPECIALIST_COACHES} specialist slots used)",
                    })
        
        # Priority 3: Missing non-essential roles
        if StaffRole.SPORTS_SCIENTIST not in filled_roles:
            recommendations.append({
                "role": StaffRole.SPORTS_SCIENTIST.value,
                "role_display_name": self._get_role_display_name(StaffRole.SPORTS_SCIENTIST),
                "priority": "low",
                "reason": "Provides mental training bonus and performance analysis",
            })
        
        # Priority 4: Upgrade low-quality staff
        for staff in staff_list:
            if staff.get_primary_attribute() < 10:
                recommendations.append({
                    "role": staff.role.value,
                    "role_display_name": staff.get_role_display_name(),
                    "priority": "low",
                    "reason": f"Current {staff.name} has low primary attribute ({staff.get_primary_attribute()}/20) - consider upgrading",
                    "current_staff_id": staff.id,
                })
        
        return recommendations
    
    async def check_contract_expiries(
        self,
        career_id: int,
        club_id: int,
        current_season: int,
        current_week: int
    ) -> Dict[str, any]:
        """
        Check for expired and expiring staff contracts during weekly progression.
        
        Implements Requirement 10.7: "IF a staff member's contract expires and is not
        renewed, THEN THE Career_Manager SHALL remove that staff member from the club."
        
        This method:
        1. Identifies staff with expired contracts
        2. Identifies staff with contracts expiring soon (< 6 months / 26 weeks)
        3. Returns notifications for the player-manager
        
        Args:
            career_id: Career ID
            club_id: Club ID
            current_season: Current in-game season number
            current_week: Current in-game week number (1-52)
        
        Returns:
            Dict containing:
                - expired: List of staff with expired contracts
                - expiring_soon: List of staff with contracts expiring within 26 weeks
                - notifications: List of notification messages for the player-manager
        """
        # Get all staff for this career and club
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        result = await self.db.execute(stmt)
        staff_list = list(result.scalars().all())
        
        expired = []
        expiring_soon = []
        notifications = []
        
        for staff in staff_list:
            # Use timezone-aware now matching the stored date's timezone
            tz = getattr(staff.contract_expiry_date, 'tzinfo', None)
            now = datetime.now(tz)
            
            # Check if contract has expired
            if staff.contract_expiry_date <= now:
                expired.append(staff.to_dict())
                notifications.append({
                    "type": "contract_expired",
                    "message": f"{staff.name} ({staff.get_role_display_name()}) contract has expired. They will leave the club.",
                    "staff_id": staff.id,
                    "season": current_season,
                    "week": current_week,
                })
            # Check if contract is expiring soon (< 26 weeks / 6 months)
            elif staff.is_contract_expiring_soon(weeks_threshold=26):
                expiring_soon.append(staff.to_dict())
                months_remaining = staff.get_contract_months_remaining()
                notifications.append({
                    "type": "contract_expiring_soon",
                    "message": f"{staff.name} ({staff.get_role_display_name()}) contract expires in {months_remaining} months. Consider renewing.",
                    "staff_id": staff.id,
                    "months_remaining": months_remaining,
                    "season": current_season,
                    "week": current_week,
                })
        
        logger.info(
            f"Contract check for career {career_id}: "
            f"{len(expired)} expired, {len(expiring_soon)} expiring soon"
        )
        
        return {
            "expired": expired,
            "expiring_soon": expiring_soon,
            "notifications": notifications,
        }
    
    async def renew_staff_contract(
        self,
        staff_id: int,
        career_id: int,
        new_years: int,
        new_wage: int
    ) -> Optional[Staff]:
        """
        Renew a staff member's contract before expiry.
        
        Implements Requirement 10.10: "THE Career_Manager SHALL allow the player-manager
        to negotiate staff contracts with duration (1-5 years) and wage."
        
        Args:
            staff_id: Staff member's ID
            career_id: Career ID (for validation)
            new_years: New contract duration in years (1-5)
            new_wage: New weekly wage
        
        Returns:
            Staff: Updated staff member, or None if not found
        
        Raises:
            ValueError: If contract years or wage are invalid
        """
        # Validate parameters
        if new_years < 1 or new_years > 5:
            raise ValueError("Contract years must be between 1 and 5")
        
        if new_wage <= 0:
            raise ValueError("Wage must be positive")
        
        # Find the staff member
        stmt = select(Staff).where(
            and_(
                Staff.id == staff_id,
                Staff.career_id == career_id
            )
        )
        result = await self.db.execute(stmt)
        staff = result.scalar_one_or_none()
        
        if not staff:
            logger.warning(f"Staff {staff_id} not found for career {career_id}")
            return None
        
        # Renew the contract
        staff.renew_contract(years=new_years, new_wage=new_wage)
        
        await self.db.commit()
        await self.db.refresh(staff)
        
        logger.info(
            f"Renewed contract for {staff.name} ({staff.role.value}): "
            f"{new_years} years, wage: {new_wage}"
        )
        
        return staff
    
    async def process_expired_contracts(
        self,
        career_id: int,
        club_id: int
    ) -> List[Dict[str, any]]:
        """
        Remove staff members with expired contracts from the club.
        
        Implements Requirement 10.7: "IF a staff member's contract expires and is not
        renewed, THEN THE Career_Manager SHALL remove that staff member from the club."
        
        This should be called during advance_week to process any expired contracts.
        
        Args:
            career_id: Career ID
            club_id: Club ID
        
        Returns:
            List of dicts with details of removed staff members
        """
        now = datetime.now()
        
        # Find all staff with expired contracts
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id,
                Staff.contract_expiry_date <= now
            )
        )
        result = await self.db.execute(stmt)
        expired_staff = list(result.scalars().all())
        
        removed = []
        for staff in expired_staff:
            removed.append({
                "id": staff.id,
                "name": staff.name,
                "role": staff.role.value,
                "role_display_name": staff.get_role_display_name(),
                "wage": staff.wage,
                "contract_expiry_date": staff.contract_expiry_date.isoformat() if staff.contract_expiry_date else None,
            })
            await self.db.delete(staff)
            logger.info(
                f"Removed {staff.name} ({staff.role.value}) from career {career_id} "
                f"due to expired contract"
            )
        
        if removed:
            await self.db.commit()
        
        return removed
    
    async def get_expiring_contracts(
        self,
        career_id: int,
        club_id: int,
        weeks_threshold: int = 26
    ) -> List[Dict[str, any]]:
        """
        Get staff members with contracts expiring within the specified threshold.
        
        Implements Requirement 5.4: "WHEN a player's contract has fewer than 6 months
        remaining, THE Career_Manager SHALL notify the player-manager with an alert."
        (Applied to staff contracts as well.)
        
        Args:
            career_id: Career ID
            club_id: Club ID
            weeks_threshold: Number of weeks to consider as "expiring soon" (default: 26 = ~6 months)
        
        Returns:
            List of dicts with staff contract expiry details, sorted by expiry date (soonest first)
        """
        now = datetime.now()
        threshold_date = now + timedelta(weeks=weeks_threshold)
        
        # Find staff with contracts expiring within threshold but not yet expired
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id,
                Staff.contract_expiry_date > now,
                Staff.contract_expiry_date <= threshold_date
            )
        ).order_by(Staff.contract_expiry_date.asc())
        
        result = await self.db.execute(stmt)
        expiring_staff = list(result.scalars().all())
        
        return [
            {
                "id": staff.id,
                "name": staff.name,
                "role": staff.role.value,
                "role_display_name": staff.get_role_display_name(),
                "wage": staff.wage,
                "contract_expiry_date": staff.contract_expiry_date.isoformat() if staff.contract_expiry_date else None,
                "months_remaining": staff.get_contract_months_remaining(),
                "weeks_remaining": max(0, (staff.contract_expiry_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days // 7),
                "primary_attribute": staff.get_primary_attribute(),
                "is_elite": staff.is_elite_staff(),
                "is_good": staff.is_good_staff(),
            }
            for staff in expiring_staff
        ]
    
    def generate_random_coach(
        self,
        role: StaffRole,
        quality: str = "average"
    ) -> Dict[str, any]:
        """
        Generate random coach attributes for hiring.
        
        Useful for AI-generated coaches or quick hiring.
        
        Args:
            role: Staff role
            quality: Coach quality ("poor", "average", "good", "elite")
        
        Returns:
            Dict containing coach attributes and suggested wage
        """
        # Quality ranges for attributes
        quality_ranges = {
            "poor": (5, 10),
            "average": (10, 15),
            "good": (15, 18),
            "elite": (18, 20)
        }
        
        attr_min, attr_max = quality_ranges.get(quality, (10, 15))
        
        # Generate attributes
        attributes = {
            "coaching": random.randint(attr_min, attr_max),
            "tactical_knowledge": random.randint(attr_min, attr_max),
            "man_management": random.randint(attr_min, attr_max),
            "scouting": random.randint(attr_min, attr_max),
            "medical": random.randint(attr_min, attr_max),
            "fitness": random.randint(attr_min, attr_max),
            "technical": random.randint(attr_min, attr_max),
            "mental": random.randint(attr_min, attr_max),
        }
        
        # Boost primary attribute for role
        if role == StaffRole.FITNESS_COACH:
            attributes["fitness"] = random.randint(attr_max, 20)
        elif role == StaffRole.DEFENSIVE_COACH:
            attributes["coaching"] = random.randint(attr_max, 20)
        elif role == StaffRole.ATTACKING_COACH:
            attributes["coaching"] = random.randint(attr_max, 20)
        elif role == StaffRole.GOALKEEPING_COACH:
            attributes["coaching"] = random.randint(attr_max, 20)
        elif role == StaffRole.CHIEF_SCOUT:
            attributes["scouting"] = random.randint(attr_max, 20)
        elif role == StaffRole.PHYSIO:
            attributes["medical"] = random.randint(attr_max, 20)
        
        # Calculate suggested wage based on quality
        base_wages = {
            "poor": 5000,
            "average": 10000,
            "good": 20000,
            "elite": 40000
        }
        
        suggested_wage = base_wages.get(quality, 10000)
        
        # Generate random age (30-65 for coaches)
        age = random.randint(30, 65)
        
        return {
            "attributes": attributes,
            "suggested_wage": suggested_wage,
            "age": age,
            "quality": quality
        }

    # ─── Scout Assignment Methods ────────────────────────────────────────────────

    # Available scouting regions
    SCOUTING_REGIONS = [
        "England",
        "Spain",
        "Germany",
        "France",
        "Italy",
        "Netherlands",
        "Portugal",
        "South America",
        "Africa",
        "Asia",
        "Scandinavia",
        "Eastern Europe",
    ]

    # Scout-eligible roles
    SCOUT_ROLES = [StaffRole.CHIEF_SCOUT]

    @classmethod
    def get_available_regions(cls) -> List[str]:
        """
        Return the list of available scouting regions.

        Returns:
            List[str]: Available geographic regions for scouting assignments
        """
        return list(cls.SCOUTING_REGIONS)

    async def assign_scout_to_region(
        self,
        career_id: int,
        scout_id: int,
        region: str,
    ) -> ScoutingAssignment:
        """
        Assign a scout to a geographic region.

        Args:
            career_id: Career ID
            scout_id: Staff ID of the scout
            region: Geographic region name

        Returns:
            ScoutingAssignment: The created assignment

        Raises:
            ValueError: If the staff member is not a scout, region is invalid,
                        or scout already has an active assignment to this region
        """
        # Validate region
        if region not in self.SCOUTING_REGIONS:
            raise ValueError(
                f"Invalid region '{region}'. Available regions: {', '.join(self.SCOUTING_REGIONS)}"
            )

        # Validate scout exists and has a scout role
        scout = await self._validate_scout(career_id, scout_id)

        # Check for duplicate active assignment to same region
        stmt = select(ScoutingAssignment).where(
            and_(
                ScoutingAssignment.career_id == career_id,
                ScoutingAssignment.staff_id == scout_id,
                ScoutingAssignment.assignment_type == AssignmentType.REGION,
                ScoutingAssignment.target_region == region,
                ScoutingAssignment.assignment_status != AssignmentStatus.COMPLETED,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Scout '{scout.name}' already has an active assignment to region '{region}'"
            )

        # Estimate weeks based on scout quality (higher scouting = faster)
        estimated_weeks = self._calculate_estimated_weeks(scout)

        assignment = ScoutingAssignment(
            career_id=career_id,
            staff_id=scout_id,
            assignment_type=AssignmentType.REGION,
            target_region=region,
            assignment_status=AssignmentStatus.ASSIGNED,
            estimated_weeks=estimated_weeks,
        )

        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)

        logger.info(
            f"Assigned scout '{scout.name}' to region '{region}' "
            f"(career {career_id}, estimated {estimated_weeks} weeks)"
        )

        return assignment

    async def assign_scout_to_competition(
        self,
        career_id: int,
        scout_id: int,
        competition: str,
    ) -> ScoutingAssignment:
        """
        Assign a scout to a specific competition.

        Args:
            career_id: Career ID
            scout_id: Staff ID of the scout
            competition: Competition name

        Returns:
            ScoutingAssignment: The created assignment

        Raises:
            ValueError: If the staff member is not a scout, competition is empty,
                        or scout already has an active assignment to this competition
        """
        # Validate competition name
        if not competition or not competition.strip():
            raise ValueError("Competition name cannot be empty")

        competition = competition.strip()

        # Validate scout exists and has a scout role
        scout = await self._validate_scout(career_id, scout_id)

        # Check for duplicate active assignment to same competition
        stmt = select(ScoutingAssignment).where(
            and_(
                ScoutingAssignment.career_id == career_id,
                ScoutingAssignment.staff_id == scout_id,
                ScoutingAssignment.assignment_type == AssignmentType.COMPETITION,
                ScoutingAssignment.target_competition == competition,
                ScoutingAssignment.assignment_status != AssignmentStatus.COMPLETED,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Scout '{scout.name}' already has an active assignment to competition '{competition}'"
            )

        # Estimate weeks based on scout quality
        estimated_weeks = self._calculate_estimated_weeks(scout)

        assignment = ScoutingAssignment(
            career_id=career_id,
            staff_id=scout_id,
            assignment_type=AssignmentType.COMPETITION,
            target_competition=competition,
            assignment_status=AssignmentStatus.ASSIGNED,
            estimated_weeks=estimated_weeks,
        )

        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)

        logger.info(
            f"Assigned scout '{scout.name}' to competition '{competition}' "
            f"(career {career_id}, estimated {estimated_weeks} weeks)"
        )

        return assignment

    async def get_scout_assignments(
        self,
        career_id: int,
    ) -> List[ScoutingAssignment]:
        """
        Get all current (non-completed) scout assignments for a career.

        Args:
            career_id: Career ID

        Returns:
            List[ScoutingAssignment]: All active scout assignments
        """
        stmt = select(ScoutingAssignment).where(
            and_(
                ScoutingAssignment.career_id == career_id,
                ScoutingAssignment.assignment_status != AssignmentStatus.COMPLETED,
            )
        ).order_by(ScoutingAssignment.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def remove_scout_assignment(
        self,
        assignment_id: int,
        career_id: int,
    ) -> bool:
        """
        Remove a scout assignment.

        Args:
            assignment_id: Assignment ID to remove
            career_id: Career ID (for validation)

        Returns:
            bool: True if assignment was removed, False if not found
        """
        stmt = select(ScoutingAssignment).where(
            and_(
                ScoutingAssignment.id == assignment_id,
                ScoutingAssignment.career_id == career_id,
            )
        )

        result = await self.db.execute(stmt)
        assignment = result.scalar_one_or_none()

        if not assignment:
            logger.warning(
                f"Assignment {assignment_id} not found for career {career_id}"
            )
            return False

        await self.db.delete(assignment)
        await self.db.commit()

        logger.info(
            f"Removed scout assignment {assignment_id} "
            f"(type={assignment.assignment_type.value}, career={career_id})"
        )

        return True

    async def get_idle_scouts(self, career_id: int) -> List[Staff]:
        """
        Get scouts that have no active (non-completed) assignments.

        Args:
            career_id: Career ID

        Returns:
            List[Staff]: Scouts without active assignments
        """
        # Get all scouts for this career
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.role.in_(self.SCOUT_ROLES),
            )
        )
        result = await self.db.execute(stmt)
        all_scouts = list(result.scalars().all())

        if not all_scouts:
            return []

        # Get scout IDs that have active assignments
        active_stmt = select(ScoutingAssignment.staff_id).where(
            and_(
                ScoutingAssignment.career_id == career_id,
                ScoutingAssignment.assignment_status != AssignmentStatus.COMPLETED,
            )
        ).distinct()

        active_result = await self.db.execute(active_stmt)
        busy_scout_ids = set(active_result.scalars().all())

        # Return scouts not in the busy set
        idle_scouts = [s for s in all_scouts if s.id not in busy_scout_ids]

        return idle_scouts

    # ─── Private Helpers ─────────────────────────────────────────────────────────

    async def _validate_scout(self, career_id: int, scout_id: int) -> Staff:
        """
        Validate that a staff member exists, belongs to the career, and has a scout role.

        Args:
            career_id: Career ID
            scout_id: Staff ID

        Returns:
            Staff: The validated scout

        Raises:
            ValueError: If staff not found or not a scout
        """
        stmt = select(Staff).where(
            and_(
                Staff.id == scout_id,
                Staff.career_id == career_id,
            )
        )
        result = await self.db.execute(stmt)
        staff = result.scalar_one_or_none()

        if not staff:
            raise ValueError(f"Staff member with ID {scout_id} not found in career {career_id}")

        if staff.role not in self.SCOUT_ROLES:
            raise ValueError(
                f"Staff member '{staff.name}' has role '{staff.role.value}', "
                f"which is not a scout role. Only {[r.value for r in self.SCOUT_ROLES]} can be assigned."
            )

        return staff

    def _calculate_estimated_weeks(self, scout: Staff) -> int:
        """
        Calculate estimated weeks for a scouting assignment based on scout quality.

        Higher scouting attribute = faster completion:
        - scouting >= 16: 2 weeks
        - scouting >= 12: 3 weeks
        - otherwise: 4 weeks

        Args:
            scout: The scout staff member

        Returns:
            int: Estimated weeks (2-4)
        """
        if scout.scouting >= 16:
            return 2
        elif scout.scouting >= 12:
            return 3
        else:
            return 4

    # ─── Staff Morale Simulation Methods ─────────────────────────────────────────

    # Morale thresholds
    HIGH_MORALE_THRESHOLD = 70
    MEDIUM_MORALE_MIN = 40
    LOW_MORALE_THRESHOLD = 40

    # Morale change limits per week
    MAX_WEEKLY_MORALE_CHANGE = 15
    MIN_WEEKLY_MORALE_CHANGE = -15

    # Effectiveness multipliers based on morale
    HIGH_MORALE_EFFECTIVENESS = 1.0    # Full effectiveness
    MEDIUM_MORALE_EFFECTIVENESS = 1.0  # Normal effectiveness
    LOW_MORALE_EFFECTIVENESS = 0.75    # Reduced effectiveness (25% reduction)

    # Probability of requesting to leave when morale is low
    LEAVE_REQUEST_PROBABILITY = 0.15  # 15% chance per week when morale < 40

    async def simulate_weekly_morale(
        self,
        career_id: int,
        club_id: int,
        match_results: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        Simulate weekly morale changes for all staff at a club.

        Updates staff morale based on weekly events including match results,
        wage satisfaction, contract length, club reputation vs staff quality,
        and random fluctuations.

        Args:
            career_id: Career ID
            club_id: Club ID
            match_results: List of match result dicts from the week, each containing:
                - result: "win", "draw", or "loss"
                - score_diff: Goal difference (positive = won by that many)

        Returns:
            List of dicts with morale change details for each staff member:
                - staff_id: Staff member ID
                - name: Staff member name
                - role: Staff role
                - old_morale: Previous morale value
                - new_morale: Updated morale value
                - change: Total morale change applied
                - factors: Dict of individual factor contributions
        """
        # Get all staff for this career and club
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        result = await self.db.execute(stmt)
        staff_list = list(result.scalars().all())

        if not staff_list:
            return []

        # Get club for reputation comparison
        from app.models.club import Club
        club_stmt = select(Club).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        club = club_result.scalar_one_or_none()

        morale_updates = []

        for staff in staff_list:
            old_morale = staff.morale
            factors = self.get_morale_factors(staff, match_results, club)

            # Sum all factors
            total_change = sum(factors.values())

            # Clamp to weekly limits
            total_change = max(
                self.MIN_WEEKLY_MORALE_CHANGE,
                min(self.MAX_WEEKLY_MORALE_CHANGE, total_change)
            )

            # Round to integer
            total_change = int(round(total_change))

            # Apply morale change
            staff.update_morale(total_change)

            morale_updates.append({
                "staff_id": staff.id,
                "name": staff.name,
                "role": staff.role.value,
                "old_morale": old_morale,
                "new_morale": staff.morale,
                "change": total_change,
                "factors": factors,
            })

        await self.db.commit()

        logger.info(
            f"Weekly morale simulation for career {career_id}, club {club_id}: "
            f"{len(morale_updates)} staff updated"
        )

        return morale_updates

    def get_morale_factors(
        self,
        staff: Staff,
        match_results: Optional[List[Dict[str, any]]] = None,
        club: Optional[any] = None
    ) -> Dict[str, float]:
        """
        Calculate individual morale factors affecting a staff member.

        Morale factors:
        - Team performance: winning = +morale, losing = -morale
        - Wage satisfaction: underpaid relative to quality = -morale
        - Contract length: short contract remaining = -morale
        - Club reputation vs staff quality: overqualified = -morale
        - Random events: small random fluctuation each week

        Args:
            staff: Staff member to evaluate
            match_results: List of match results from the week (optional)
            club: Club object for reputation comparison (optional)

        Returns:
            Dict mapping factor name to morale change value
        """
        factors: Dict[str, float] = {}

        # 1. Team performance factor
        if match_results:
            performance_change = 0.0
            for match in match_results:
                result = match.get("result", "draw")
                if result == "win":
                    performance_change += 3.0
                elif result == "draw":
                    performance_change += 0.5
                elif result == "loss":
                    performance_change -= 4.0
            factors["team_performance"] = performance_change
        else:
            factors["team_performance"] = 0.0

        # 2. Wage satisfaction factor
        # Staff with higher quality expect higher wages
        # Average attribute * 1000 is the "expected" wage baseline
        avg_attr = staff.get_average_attribute()
        expected_wage = avg_attr * 1000  # e.g., attr 15 expects ~15000/week
        if staff.wage < expected_wage * 0.6:
            # Significantly underpaid
            factors["wage_satisfaction"] = -4.0
        elif staff.wage < expected_wage * 0.8:
            # Somewhat underpaid
            factors["wage_satisfaction"] = -2.0
        elif staff.wage >= expected_wage * 1.2:
            # Well paid
            factors["wage_satisfaction"] = 1.0
        else:
            factors["wage_satisfaction"] = 0.0

        # 3. Contract length factor
        months_remaining = staff.get_contract_months_remaining()
        if months_remaining <= 3:
            factors["contract_length"] = -5.0
        elif months_remaining <= 6:
            factors["contract_length"] = -3.0
        elif months_remaining <= 12:
            factors["contract_length"] = -1.0
        else:
            factors["contract_length"] = 0.0

        # 4. Club reputation vs staff quality factor
        if club:
            # Staff quality on 1-100 scale (average attribute * 5)
            staff_quality_scaled = avg_attr * 5  # Maps 1-20 to 5-100
            club_reputation = club.reputation

            quality_diff = staff_quality_scaled - club_reputation
            if quality_diff > 20:
                # Staff is significantly overqualified for the club
                factors["reputation_mismatch"] = -4.0
            elif quality_diff > 10:
                # Staff is somewhat overqualified
                factors["reputation_mismatch"] = -2.0
            elif quality_diff < -20:
                # Staff is at a prestigious club (happy)
                factors["reputation_mismatch"] = 2.0
            else:
                factors["reputation_mismatch"] = 0.0
        else:
            factors["reputation_mismatch"] = 0.0

        # 5. Random fluctuation (small random change each week)
        factors["random_events"] = random.uniform(-2.0, 2.0)

        return factors

    async def apply_morale_effects(
        self,
        career_id: int
    ) -> Dict[str, any]:
        """
        Apply morale effects to staff effectiveness and check for leave requests.

        Morale effects:
        - High morale (>= 70): Full effectiveness (1.0 multiplier)
        - Medium morale (40-69): Normal effectiveness (1.0 multiplier)
        - Low morale (< 40): Reduced effectiveness (0.75 multiplier), may request to leave

        Args:
            career_id: Career ID

        Returns:
            Dict containing:
                - effectiveness_modifiers: Dict mapping staff_id to effectiveness multiplier
                - leave_requests: List of staff members requesting to leave
                - low_morale_warnings: List of staff with low morale (but not requesting leave)
        """
        staff_list = await self.get_all_staff(career_id)

        effectiveness_modifiers: Dict[int, float] = {}
        leave_requests: List[Dict[str, any]] = []
        low_morale_warnings: List[Dict[str, any]] = []

        for staff in staff_list:
            # Determine effectiveness based on morale
            if staff.morale >= self.HIGH_MORALE_THRESHOLD:
                effectiveness = self.HIGH_MORALE_EFFECTIVENESS
            elif staff.morale >= self.MEDIUM_MORALE_MIN:
                effectiveness = self.MEDIUM_MORALE_EFFECTIVENESS
            else:
                effectiveness = self.LOW_MORALE_EFFECTIVENESS

                # Check if staff wants to leave (random chance when morale is low)
                if random.random() < self.LEAVE_REQUEST_PROBABILITY:
                    leave_requests.append({
                        "staff_id": staff.id,
                        "name": staff.name,
                        "role": staff.role.value,
                        "role_display_name": staff.get_role_display_name(),
                        "morale": staff.morale,
                        "message": (
                            f"{staff.name} ({staff.get_role_display_name()}) is unhappy "
                            f"and has requested to leave the club."
                        ),
                    })
                else:
                    low_morale_warnings.append({
                        "staff_id": staff.id,
                        "name": staff.name,
                        "role": staff.role.value,
                        "role_display_name": staff.get_role_display_name(),
                        "morale": staff.morale,
                        "message": (
                            f"{staff.name} ({staff.get_role_display_name()}) has low morale "
                            f"({staff.morale}/100). Their effectiveness is reduced."
                        ),
                    })

            effectiveness_modifiers[staff.id] = effectiveness

        logger.info(
            f"Morale effects for career {career_id}: "
            f"{len(leave_requests)} leave requests, "
            f"{len(low_morale_warnings)} low morale warnings"
        )

        return {
            "effectiveness_modifiers": effectiveness_modifiers,
            "leave_requests": leave_requests,
            "low_morale_warnings": low_morale_warnings,
        }

    # ─── Staff Contract Negotiation Methods ──────────────────────────────────────

    # Base wage per quality point (average attribute)
    BASE_WAGE_PER_QUALITY = 1500

    # Quality thresholds for contract expectations
    HIGH_QUALITY_THRESHOLD = 16  # Staff with avg attribute >= 16 are "high quality"
    ELITE_QUALITY_THRESHOLD = 18  # Staff with avg attribute >= 18 are "elite"

    # Morale impact on negotiation willingness
    LOW_MORALE_ACCEPTANCE_BONUS = 0.2  # Low morale staff are 20% more likely to accept

    def get_staff_wage_expectation(self, staff: Staff) -> int:
        """
        Calculate what wage a staff member expects based on their quality.

        The expected wage is based on the staff member's average attribute level.
        Higher quality staff demand higher wages.

        Formula: average_attribute * BASE_WAGE_PER_QUALITY
        - Average staff (attr ~10): expects ~15,000/week
        - Good staff (attr ~15): expects ~22,500/week
        - Elite staff (attr ~18): expects ~27,000/week

        Args:
            staff: Staff member to evaluate

        Returns:
            int: Expected weekly wage
        """
        avg_attr = staff.get_average_attribute()
        expected_wage = int(avg_attr * self.BASE_WAGE_PER_QUALITY)
        return expected_wage

    def get_staff_contract_expectation(self, staff: Staff) -> int:
        """
        Calculate the minimum contract years a staff member expects.

        Higher quality staff demand longer contracts for security:
        - Elite staff (avg >= 18): minimum 3 years
        - High quality staff (avg >= 16): minimum 2 years
        - Average staff: minimum 1 year

        Args:
            staff: Staff member to evaluate

        Returns:
            int: Minimum contract years expected (1-5)
        """
        avg_attr = staff.get_average_attribute()

        if avg_attr >= self.ELITE_QUALITY_THRESHOLD:
            return 3
        elif avg_attr >= self.HIGH_QUALITY_THRESHOLD:
            return 2
        else:
            return 1

    async def negotiate_contract(
        self,
        staff_id: int,
        career_id: int,
        offered_years: int,
        offered_wage: int
    ) -> NegotiationResult:
        """
        Simulate contract negotiation with a staff member.

        The staff member can accept, counter-offer, or reject based on:
        - Staff quality (higher quality = higher demands)
        - Current morale (low morale = more likely to accept)
        - Offered wage vs expected wage
        - Offered years vs expected years

        Negotiation logic:
        1. If offered wage >= expected wage AND offered years >= expected years:
           -> Accept (with morale bonus making acceptance even more likely)
        2. If offered wage is within 80% of expected AND years are acceptable:
           -> Counter-offer with expected wage
        3. If offered wage < 60% of expected OR years far below expected:
           -> Reject outright

        Args:
            staff_id: Staff member's ID
            career_id: Career ID (for validation)
            offered_years: Offered contract duration in years (1-5)
            offered_wage: Offered weekly wage

        Returns:
            NegotiationResult: The outcome of the negotiation

        Raises:
            ValueError: If contract years or wage are invalid, or staff not found
        """
        # Validate parameters
        if offered_years < 1 or offered_years > 5:
            raise ValueError("Contract years must be between 1 and 5")

        if offered_wage <= 0:
            raise ValueError("Wage must be positive")

        # Find the staff member
        stmt = select(Staff).where(
            and_(
                Staff.id == staff_id,
                Staff.career_id == career_id
            )
        )
        result = await self.db.execute(stmt)
        staff = result.scalar_one_or_none()

        if not staff:
            raise ValueError(f"Staff member with ID {staff_id} not found in career {career_id}")

        # Calculate expectations
        expected_wage = self.get_staff_wage_expectation(staff)
        expected_years = self.get_staff_contract_expectation(staff)

        # Calculate wage ratio and years difference
        wage_ratio = offered_wage / expected_wage if expected_wage > 0 else 1.0
        years_diff = offered_years - expected_years

        # Morale adjustment: low morale staff are more willing to accept
        morale_factor = 0.0
        if staff.morale < self.LOW_MORALE_THRESHOLD:
            morale_factor = self.LOW_MORALE_ACCEPTANCE_BONUS

        # Decision logic
        # Acceptance threshold: wage >= 100% expected (lowered by morale)
        acceptance_wage_threshold = 1.0 - morale_factor

        if wage_ratio >= acceptance_wage_threshold and offered_years >= expected_years:
            # Staff accepts the offer
            return NegotiationResult(
                outcome="accepted",
                offered_years=offered_years,
                offered_wage=offered_wage,
                reason=f"{staff.name} is happy with the offer."
            )

        # Counter-offer zone: wage is between 60% and 100% of expected
        counter_offer_threshold = 0.6

        if wage_ratio >= counter_offer_threshold:
            # Staff makes a counter-offer
            counter_wage = expected_wage
            counter_years = max(offered_years, expected_years)

            # If years are too short, demand more years
            if offered_years < expected_years:
                counter_years = expected_years

            # Clamp counter years to valid range
            counter_years = min(5, max(1, counter_years))

            return NegotiationResult(
                outcome="counter_offer",
                offered_years=offered_years,
                offered_wage=offered_wage,
                counter_years=counter_years,
                counter_wage=counter_wage,
                reason=(
                    f"{staff.name} wants a better deal: "
                    f"{counter_wage}/week for {counter_years} years."
                )
            )

        # Rejection: wage is too low (< 60% of expected)
        return NegotiationResult(
            outcome="rejected",
            offered_years=offered_years,
            offered_wage=offered_wage,
            reason=(
                f"{staff.name} rejected the offer outright. "
                f"The wage is far below their expectations."
            )
        )

    # ─── Staff Wage Budget Management Methods ────────────────────────────────────

    # Percentage of total wage_budget allocated to staff wages
    STAFF_WAGE_BUDGET_PERCENTAGE = 0.30  # 30% of total wage_budget

    async def _check_staff_wage_budget(
        self,
        career_id: int,
        club_id: int,
        wage: int
    ) -> bool:
        """
        Internal helper to check staff wage budget during hiring.

        Returns True if the wage is affordable or if the club doesn't exist in DB
        (graceful fallback for cases where club isn't set up).
        Returns False only if the club exists and the wage would exceed the budget.

        Args:
            career_id: Career ID
            club_id: Club ID
            wage: Proposed weekly wage

        Returns:
            bool: True if hiring is allowed, False if budget would be exceeded
        """
        from app.models.club import Club

        # Check if club exists
        club_stmt = select(Club).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        club = club_result.scalar_one_or_none()

        if not club:
            # Club not in DB - skip budget check (backward compatibility)
            return True

        # Club exists - perform budget check
        return await self.can_afford_staff_wage(career_id, club_id, wage)

    async def get_staff_wage_budget_status(
        self,
        career_id: int,
        club_id: int
    ) -> Dict[str, any]:
        """
        Get current staff wage spending vs budget allocation.

        The staff wage budget is 30% of the club's total wage_budget.
        Returns current spending, budget limit, remaining capacity, and utilization percentage.

        Args:
            career_id: Career ID
            club_id: Club ID

        Returns:
            Dict containing:
                - total_wage_budget: Club's total wage budget
                - staff_wage_allocation: Amount allocated to staff wages (30% of total)
                - current_staff_wages: Total weekly wages of all current staff
                - remaining_budget: How much more can be spent on staff wages
                - utilization_percentage: Percentage of staff budget used (0-100+)
                - is_over_budget: Whether current spending exceeds the allocation
                - staff_count: Number of staff members
        """
        from app.models.club import Club

        # Get club's wage budget
        club_stmt = select(Club).where(Club.id == club_id)
        club_result = await self.db.execute(club_stmt)
        club = club_result.scalar_one_or_none()

        if not club:
            raise ValueError(f"Club with ID {club_id} not found")

        total_wage_budget = club.wage_budget
        staff_wage_allocation = int(total_wage_budget * self.STAFF_WAGE_BUDGET_PERCENTAGE)

        # Get total current staff wages
        stmt = select(func.coalesce(func.sum(Staff.wage), 0)).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        result = await self.db.execute(stmt)
        current_staff_wages = result.scalar_one()

        # Get staff count
        count_stmt = select(func.count(Staff.id)).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        count_result = await self.db.execute(count_stmt)
        staff_count = count_result.scalar_one()

        remaining_budget = staff_wage_allocation - current_staff_wages
        utilization_percentage = (
            (current_staff_wages / staff_wage_allocation * 100)
            if staff_wage_allocation > 0
            else 0.0
        )

        return {
            "total_wage_budget": total_wage_budget,
            "staff_wage_allocation": staff_wage_allocation,
            "current_staff_wages": current_staff_wages,
            "remaining_budget": remaining_budget,
            "utilization_percentage": round(utilization_percentage, 1),
            "is_over_budget": current_staff_wages > staff_wage_allocation,
            "staff_count": staff_count,
        }

    async def can_afford_staff_wage(
        self,
        career_id: int,
        club_id: int,
        additional_wage: int
    ) -> bool:
        """
        Check if hiring a staff member with the given wage would exceed the staff wage budget.

        The staff wage budget is 30% of the club's total wage_budget.
        Returns True if the additional wage fits within the budget, False otherwise.

        Args:
            career_id: Career ID
            club_id: Club ID
            additional_wage: The weekly wage of the staff member to be hired

        Returns:
            bool: True if the club can afford the additional staff wage, False otherwise
        """
        status = await self.get_staff_wage_budget_status(career_id, club_id)
        return status["remaining_budget"] >= additional_wage

    async def get_staff_wage_breakdown(
        self,
        career_id: int,
        club_id: int
    ) -> Dict[str, any]:
        """
        Get a breakdown of staff wages grouped by role.

        Args:
            career_id: Career ID
            club_id: Club ID

        Returns:
            Dict containing:
                - by_role: Dict mapping role name to total wages and count for that role
                - total_wages: Total weekly staff wages
                - highest_earner: Dict with name, role, and wage of highest-paid staff
                - lowest_earner: Dict with name, role, and wage of lowest-paid staff
                - average_wage: Average weekly wage across all staff
        """
        # Get all staff for this career and club
        stmt = select(Staff).where(
            and_(
                Staff.career_id == career_id,
                Staff.club_id == club_id
            )
        )
        result = await self.db.execute(stmt)
        staff_list = list(result.scalars().all())

        if not staff_list:
            return {
                "by_role": {},
                "total_wages": 0,
                "highest_earner": None,
                "lowest_earner": None,
                "average_wage": 0,
            }

        # Group wages by role
        by_role: Dict[str, Dict[str, any]] = {}
        for staff in staff_list:
            role_name = staff.role.value
            if role_name not in by_role:
                by_role[role_name] = {
                    "total_wages": 0,
                    "count": 0,
                    "staff_members": [],
                }
            by_role[role_name]["total_wages"] += staff.wage
            by_role[role_name]["count"] += 1
            by_role[role_name]["staff_members"].append({
                "id": staff.id,
                "name": staff.name,
                "wage": staff.wage,
            })

        total_wages = sum(s.wage for s in staff_list)
        average_wage = total_wages // len(staff_list) if staff_list else 0

        # Find highest and lowest earners
        highest = max(staff_list, key=lambda s: s.wage)
        lowest = min(staff_list, key=lambda s: s.wage)

        return {
            "by_role": by_role,
            "total_wages": total_wages,
            "highest_earner": {
                "id": highest.id,
                "name": highest.name,
                "role": highest.role.value,
                "wage": highest.wage,
            },
            "lowest_earner": {
                "id": lowest.id,
                "name": lowest.name,
                "role": lowest.role.value,
                "wage": lowest.wage,
            },
            "average_wage": average_wage,
        }
