"""
Training Service - Handles weekly training session simulation and player attribute development

This module implements the Training_Module functionality for simulating weekly training
sessions and updating player attributes based on training focus, intensity, age, and
coaching staff quality.

Key Features:
- Weekly training session simulation
- Age-based attribute progression (players < 24) and decline (players > 30)
- Training focus area effects on specific attributes
- Training intensity modifiers (Light, Normal, Heavy)
- Coach bonus application
- Training Facilities infrastructure bonus
- Automatic rehabilitation for injured players
- Attribute history tracking
"""

import json
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.injury import Injury, InjuryStatus
from app.models.club import Club
from app.models.career import Career
from app.core.logging import get_logger

logger = get_logger(__name__)


class TrainingService:
    """
    Service for managing training sessions and player attribute development.
    
    Implements Requirement 7.2: "THE Training_Module SHALL simulate weekly training
    sessions and update player attributes at the end of each in-game week."
    """
    
    # Attribute caps
    MIN_ATTRIBUTE = 1
    MAX_ATTRIBUTE = 20
    
    # Development thresholds
    YOUNG_PLAYER_AGE = 24  # Players under this age can improve
    OLD_PLAYER_AGE = 30    # Players over this age can decline
    
    # Youth player thresholds (age 15-18)
    YOUTH_PLAYER_MIN_AGE = 15  # Minimum age for youth player
    YOUTH_PLAYER_MAX_AGE = 18  # Maximum age for youth player
    
    # Consecutive weeks thresholds
    IMPROVEMENT_WEEKS = 4       # Weeks needed for young player improvement
    YOUTH_IMPROVEMENT_WEEKS = 3 # Weeks needed for youth player improvement (accelerated)
    DECLINE_WEEKS = 8           # Weeks without fitness for old player decline
    
    # Base improvement/decline amounts
    BASE_IMPROVEMENT = 1        # Base attribute points gained
    BASE_DECLINE = 1            # Base attribute points lost
    
    # Youth development multiplier
    YOUTH_DEVELOPMENT_MULTIPLIER = 1.5  # 1.5x improvement rate for youth players
    
    # Youth Academy level bonuses (level 1-5)
    YOUTH_ACADEMY_LEVEL_BONUSES = {
        1: 1.0,   # Basic - no bonus
        2: 1.1,   # Standard - 10% bonus
        3: 1.2,   # Good - 20% bonus
        4: 1.3,   # Excellent - 30% bonus
        5: 1.5,   # World Class - 50% bonus
    }
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize TrainingService.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session
    
    async def simulate_weekly_training(
        self,
        career_id: int,
        season: int,
        week: int,
        training_intensity: TrainingIntensity = TrainingIntensity.NORMAL,
        coach_bonuses: Optional[Dict[TrainingFocus, float]] = None,
        infrastructure_bonus: Optional[float] = None,
        auto_fetch_coach_bonuses: bool = True,
        auto_fetch_infrastructure_bonus: bool = True,
        youth_academy_level: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Simulate weekly training session for all players in a career.
        
        Implements Requirement 7.2: Weekly training session simulation.
        
        Args:
            career_id: Career ID
            season: Current season number
            week: Current week number (1-52)
            training_intensity: Team-wide training intensity setting
            coach_bonuses: Dict mapping training focus to bonus multiplier (1.0 = no bonus, 1.1 = 10% bonus)
            infrastructure_bonus: Training facilities bonus multiplier (1.0 = no bonus). If None, auto-fetched.
            auto_fetch_coach_bonuses: If True, automatically fetch coach bonuses from StaffService
            auto_fetch_infrastructure_bonus: If True and infrastructure_bonus is None, automatically fetch from InfrastructureService
            youth_academy_level: Youth Academy infrastructure level (1-5). If None, auto-fetched from career's club.
        
        Returns:
            Dict containing:
                - players_trained: Number of players trained
                - improvements: List of player improvements
                - declines: List of player declines
                - injuries: List of training injuries
                - youth_developments: List of youth player developments
                - summary: Training session summary
        """
        logger.info(
            f"Simulating weekly training for career {career_id}, "
            f"season {season}, week {week}, intensity {training_intensity.value}"
        )
        
        # Auto-fetch coach bonuses if requested and not provided
        if auto_fetch_coach_bonuses and coach_bonuses is None:
            from app.services.staff_service import StaffService
            staff_service = StaffService(self.db)
            coach_bonuses = await staff_service.get_coach_bonuses(career_id)
            logger.debug(f"Auto-fetched coach bonuses: {coach_bonuses}")
        
        # Auto-fetch infrastructure bonus if requested and not provided
        if auto_fetch_infrastructure_bonus and infrastructure_bonus is None:
            infrastructure_bonus = await self._get_training_facilities_bonus(career_id)
            logger.debug(f"Auto-fetched infrastructure bonus: {infrastructure_bonus}")
        
        # Default to 1.0 if still None (e.g., auto_fetch disabled and not provided)
        if infrastructure_bonus is None:
            infrastructure_bonus = 1.0
        
        # Auto-fetch youth academy level if not provided
        if youth_academy_level is None:
            youth_academy_level = await self._get_youth_academy_level(career_id)
        
        coach_bonuses = coach_bonuses or {}
        improvements = []
        declines = []
        injuries = []
        youth_developments = []
        
        # Get all training schedules for this week
        stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
            .options(selectinload(TrainingSchedule.squad_player))
        )
        
        result = await self.db.execute(stmt)
        training_schedules = result.scalars().all()
        
        if not training_schedules:
            logger.warning(f"No training schedules found for career {career_id}, season {season}, week {week}")
            return {
                "players_trained": 0,
                "improvements": [],
                "declines": [],
                "injuries": [],
                "summary": "No training schedules found"
            }
        
        # Process each player's training
        for schedule in training_schedules:
            try:
                # Get player data
                player = await self._get_player(schedule.player_id)
                if not player:
                    logger.warning(f"Player {schedule.player_id} not found")
                    continue
                
                # Skip if player is injured (should be on rehabilitation)
                if schedule.is_injured:
                    logger.debug(f"Player {player.name} is injured, on rehabilitation")
                    continue
                
                # Calculate effective bonuses
                focus_bonus = coach_bonuses.get(schedule.training_focus, 1.0)
                intensity_multiplier = schedule.get_development_rate_multiplier()
                total_multiplier = focus_bonus * infrastructure_bonus * intensity_multiplier
                
                # Check if player is a youth player (age 15-18) - accelerated development
                if self._is_youth_player(player):
                    youth_dev = await self._process_youth_player_training(
                        player, schedule, total_multiplier, youth_academy_level
                    )
                    if youth_dev:
                        youth_developments.append(youth_dev)
                
                # Check for attribute improvements (young players, non-youth path)
                elif player.age < self.YOUNG_PLAYER_AGE:
                    improvement = await self._process_young_player_training(
                        player, schedule, total_multiplier
                    )
                    if improvement:
                        improvements.append(improvement)
                
                # Check for attribute decline (old players)
                elif player.age > self.OLD_PLAYER_AGE:
                    decline = await self._process_old_player_training(
                        player, schedule
                    )
                    if decline:
                        declines.append(decline)
                
                # Simulate training injury risk
                injury = await self._simulate_training_injury(
                    player, schedule, career_id, season, week
                )
                if injury:
                    injuries.append(injury)
                
            except Exception as e:
                logger.error(f"Error processing training for player {schedule.player_id}: {e}")
                continue
        
        # Commit all changes
        await self.db.commit()
        
        summary = self._generate_training_summary(
            len(training_schedules), improvements, declines, injuries, youth_developments
        )
        
        logger.info(f"Weekly training completed: {summary}")
        
        return {
            "players_trained": len(training_schedules),
            "improvements": improvements,
            "declines": declines,
            "injuries": injuries,
            "youth_developments": youth_developments,
            "summary": summary
        }
    
    async def _process_young_player_training(
        self,
        player: Player,
        schedule: TrainingSchedule,
        multiplier: float
    ) -> Optional[Dict[str, any]]:
        """
        Process training for young players (under 24 years old).
        
        Implements Requirement 7.3: "WHEN a player under 24 years old is assigned to
        a training focus area for 4 consecutive in-game weeks, THE Training_Module
        SHALL increase the relevant attributes by 1 point (capped at PA)."
        
        Args:
            player: Player model
            schedule: TrainingSchedule model
            multiplier: Combined bonus multiplier
        
        Returns:
            Dict with improvement details if improvement occurred, None otherwise
        """
        # Check if player has trained for enough consecutive weeks
        if schedule.consecutive_weeks < self.IMPROVEMENT_WEEKS:
            return None
        
        # Get attributes affected by this training focus
        affected_attributes = schedule.get_affected_attributes()
        if not affected_attributes:
            return None
        
        # Calculate improvement amount (base * multiplier, rounded)
        improvement_amount = max(1, round(self.BASE_IMPROVEMENT * multiplier))
        
        # Apply improvements to affected attributes
        improvements_made = {}
        for attr_name in affected_attributes:
            current_value = getattr(player, attr_name, None)
            if current_value is None:
                continue
            
            # Check if attribute can be improved (not at PA cap)
            if current_value >= player.pa or current_value >= self.MAX_ATTRIBUTE:
                continue
            
            # Calculate new value (capped at PA and MAX_ATTRIBUTE)
            new_value = min(
                current_value + improvement_amount,
                player.pa,
                self.MAX_ATTRIBUTE
            )
            
            if new_value > current_value:
                setattr(player, attr_name, new_value)
                improvements_made[attr_name] = {
                    "old": current_value,
                    "new": new_value,
                    "change": new_value - current_value
                }
        
        if improvements_made:
            # Update attribute improvements in schedule
            schedule.attribute_improvements = json.dumps(improvements_made)
            
            # Reset consecutive weeks counter after improvement
            schedule.reset_consecutive_weeks()
            
            logger.info(
                f"Player {player.name} (age {player.age}) improved: {improvements_made}"
            )
            
            return {
                "player_id": player.id,
                "player_name": player.name,
                "age": player.age,
                "training_focus": schedule.training_focus.value,
                "improvements": improvements_made,
                "multiplier": multiplier
            }
        
        return None
    
    async def _process_old_player_training(
        self,
        player: Player,
        schedule: TrainingSchedule
    ) -> Optional[Dict[str, any]]:
        """
        Process training for old players (over 30 years old).
        
        Implements Requirement 7.4: "WHEN a player over 30 years old is not assigned
        to a Fitness training focus, THE Training_Module SHALL decrease the player's
        stamina and pace attributes by 1 point per 8 in-game weeks."
        
        Args:
            player: Player model
            schedule: TrainingSchedule model
        
        Returns:
            Dict with decline details if decline occurred, None otherwise
        """
        # Only decline if not on fitness training and enough weeks have passed
        if schedule.is_fitness_training():
            return None
        
        if schedule.consecutive_weeks < self.DECLINE_WEEKS:
            return None
        
        # Decline stamina and pace
        declines_made = {}
        
        for attr_name in ["stamina", "pace"]:
            current_value = getattr(player, attr_name, None)
            if current_value is None:
                continue
            
            # Don't decline below minimum
            if current_value <= self.MIN_ATTRIBUTE:
                continue
            
            new_value = max(current_value - self.BASE_DECLINE, self.MIN_ATTRIBUTE)
            
            if new_value < current_value:
                setattr(player, attr_name, new_value)
                declines_made[attr_name] = {
                    "old": current_value,
                    "new": new_value,
                    "change": new_value - current_value
                }
        
        if declines_made:
            # Update attribute improvements (actually declines) in schedule
            schedule.attribute_improvements = json.dumps(declines_made)
            
            # Reset consecutive weeks counter after decline
            schedule.reset_consecutive_weeks()
            
            logger.info(
                f"Player {player.name} (age {player.age}) declined: {declines_made}"
            )
            
            return {
                "player_id": player.id,
                "player_name": player.name,
                "age": player.age,
                "training_focus": schedule.training_focus.value,
                "declines": declines_made
            }
        
        return None
    
    def _is_youth_player(self, player: Player) -> bool:
        """
        Check if a player qualifies as a youth player (age 15-18).
        
        Youth players receive accelerated development compared to regular
        young players (age 19-23).
        
        Args:
            player: Player model
        
        Returns:
            True if player is aged 15-18, False otherwise
        """
        return self.YOUTH_PLAYER_MIN_AGE <= player.age <= self.YOUTH_PLAYER_MAX_AGE
    
    async def _process_youth_player_training(
        self,
        player: Player,
        schedule: TrainingSchedule,
        multiplier: float,
        youth_academy_level: int = 1
    ) -> Optional[Dict[str, any]]:
        """
        Process training for youth players (age 15-18) with accelerated development.
        
        Youth players benefit from:
        - Faster improvement (3 consecutive weeks instead of 4)
        - Enhanced development rate (1.5x base multiplier)
        - Youth Academy infrastructure bonus
        
        Implements Requirement 7.9: "THE Training_Module SHALL simulate youth player
        development through the Youth_Academy with weekly attribute updates."
        
        Args:
            player: Player model (must be age 15-18)
            schedule: TrainingSchedule model
            multiplier: Combined bonus multiplier (coach + infrastructure + intensity)
            youth_academy_level: Youth Academy infrastructure level (1-5)
        
        Returns:
            Dict with youth development details if improvement occurred, None otherwise
        """
        # Youth players improve after fewer consecutive weeks
        if schedule.consecutive_weeks < self.YOUTH_IMPROVEMENT_WEEKS:
            return None
        
        # Get attributes affected by this training focus
        affected_attributes = schedule.get_affected_attributes()
        if not affected_attributes:
            return None
        
        # Calculate youth-specific multiplier
        academy_bonus = self.YOUTH_ACADEMY_LEVEL_BONUSES.get(youth_academy_level, 1.0)
        youth_multiplier = multiplier * self.YOUTH_DEVELOPMENT_MULTIPLIER * academy_bonus
        
        # Calculate improvement amount (base * youth_multiplier, rounded)
        improvement_amount = max(1, round(self.BASE_IMPROVEMENT * youth_multiplier))
        
        # Apply improvements to affected attributes
        improvements_made = {}
        for attr_name in affected_attributes:
            current_value = getattr(player, attr_name, None)
            if current_value is None:
                continue
            
            # Check if attribute can be improved (not at PA cap)
            if current_value >= player.pa or current_value >= self.MAX_ATTRIBUTE:
                continue
            
            # Calculate new value (capped at PA and MAX_ATTRIBUTE)
            new_value = min(
                current_value + improvement_amount,
                player.pa,
                self.MAX_ATTRIBUTE
            )
            
            if new_value > current_value:
                setattr(player, attr_name, new_value)
                improvements_made[attr_name] = {
                    "old": current_value,
                    "new": new_value,
                    "change": new_value - current_value
                }
        
        if improvements_made:
            # Update attribute improvements in schedule
            schedule.attribute_improvements = json.dumps(improvements_made)
            
            # Reset consecutive weeks counter after improvement
            schedule.reset_consecutive_weeks()
            
            logger.info(
                f"Youth player {player.name} (age {player.age}) developed: "
                f"{improvements_made} (academy level: {youth_academy_level})"
            )
            
            return {
                "player_id": player.id,
                "player_name": player.name,
                "age": player.age,
                "training_focus": schedule.training_focus.value,
                "improvements": improvements_made,
                "multiplier": youth_multiplier,
                "youth_academy_level": youth_academy_level,
                "is_youth_development": True
            }
        
        return None
    
    async def _get_youth_academy_level(self, career_id: int) -> int:
        """
        Get the Youth Academy infrastructure level for a career's club.
        
        Args:
            career_id: Career ID
        
        Returns:
            Youth Academy level (1-5), defaults to 1 if not found
        """
        stmt = (
            select(Club.youth_academy_level)
            .join(Career, Career.club_id == Club.id)
            .where(Career.id == career_id)
        )
        
        result = await self.db.execute(stmt)
        level = result.scalar_one_or_none()
        return level if level is not None else 1

    async def _get_training_facilities_bonus(self, career_id: int) -> float:
        """
        Get the Training Facilities infrastructure bonus for a career's club.

        Fetches the club's training_facilities_level and returns the corresponding
        training_bonus_multiplier from the InfrastructureService's CATEGORY_EFFECTS.

        Args:
            career_id: Career ID

        Returns:
            Training bonus multiplier (1.0 to 1.6), defaults to 1.0 if not found
        """
        from app.services.infrastructure_service import (
            CATEGORY_EFFECTS,
            InfrastructureCategory,
        )

        stmt = (
            select(Club.training_facilities_level)
            .join(Career, Career.club_id == Club.id)
            .where(Career.id == career_id)
        )

        result = await self.db.execute(stmt)
        level = result.scalar_one_or_none()

        if level is None:
            return 1.0

        effects = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][level]
        return effects["training_bonus_multiplier"]
    
    def get_youth_players_from_squad(
        self,
        players: List[Player]
    ) -> List[Player]:
        """
        Identify youth players (age 15-18) from a list of players.
        
        Args:
            players: List of Player models
        
        Returns:
            List of players aged 15-18
        """
        return [p for p in players if self._is_youth_player(p)]
    
    async def get_youth_player_development_report(
        self,
        career_id: int,
        season: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Get a comprehensive development report for all youth players in a career.
        
        This report tracks youth player progression separately, showing:
        - All youth players in the squad
        - Their current training focus and progress
        - Total attribute improvements this season
        - Development rate compared to regular young players
        - Youth Academy level impact
        
        Args:
            career_id: Career ID
            season: Optional season filter (None = current season data)
        
        Returns:
            Dict containing:
                - career_id: Career ID
                - youth_academy_level: Current Youth Academy level
                - youth_players: List of youth player development entries
                - total_youth_players: Count of youth players
                - total_improvements_this_season: Total attribute points gained
                - average_development_rate: Average improvement per youth player
                - top_developers: Top 3 youth players by improvement
        """
        logger.info(f"Generating youth player development report for career {career_id}")
        
        # Get youth academy level
        youth_academy_level = await self._get_youth_academy_level(career_id)
        
        # Get all squad players for this career who are youth age
        stmt = (
            select(Player, SquadPlayer)
            .join(SquadPlayer, SquadPlayer.player_id == Player.id)
            .where(
                and_(
                    SquadPlayer.career_id == career_id,
                    Player.age >= self.YOUTH_PLAYER_MIN_AGE,
                    Player.age <= self.YOUTH_PLAYER_MAX_AGE
                )
            )
            .order_by(Player.age, Player.name)
        )
        
        result = await self.db.execute(stmt)
        youth_rows = result.all()
        
        # Get training history for youth players
        youth_player_ids = [player.id for player, _ in youth_rows]
        
        # Build conditions for training history query
        history_conditions = [
            TrainingSchedule.career_id == career_id,
            TrainingSchedule.player_id.in_(youth_player_ids),
            TrainingSchedule.attribute_improvements.isnot(None)
        ]
        
        if season is not None:
            history_conditions.append(TrainingSchedule.season == season)
        
        history_stmt = (
            select(TrainingSchedule)
            .where(and_(*history_conditions))
            .order_by(TrainingSchedule.season.desc(), TrainingSchedule.week.desc())
        )
        
        history_result = await self.db.execute(history_stmt)
        training_histories = history_result.scalars().all()
        
        # Aggregate improvements per player
        player_improvements: Dict[int, Dict[str, any]] = {}
        for schedule in training_histories:
            if not schedule.attribute_improvements:
                continue
            try:
                changes = json.loads(schedule.attribute_improvements)
                if schedule.player_id not in player_improvements:
                    player_improvements[schedule.player_id] = {
                        "total_points": 0,
                        "improvements_count": 0,
                        "attributes_improved": {}
                    }
                
                for attr_name, change_data in changes.items():
                    change_value = change_data.get("change", 0)
                    if change_value > 0:
                        player_improvements[schedule.player_id]["total_points"] += change_value
                        player_improvements[schedule.player_id]["improvements_count"] += 1
                        attrs = player_improvements[schedule.player_id]["attributes_improved"]
                        attrs[attr_name] = attrs.get(attr_name, 0) + change_value
            except json.JSONDecodeError:
                continue
        
        # Get current training schedules for youth players
        current_schedules: Dict[int, TrainingSchedule] = {}
        if youth_player_ids:
            schedule_stmt = (
                select(TrainingSchedule)
                .where(
                    and_(
                        TrainingSchedule.career_id == career_id,
                        TrainingSchedule.player_id.in_(youth_player_ids)
                    )
                )
                .order_by(TrainingSchedule.season.desc(), TrainingSchedule.week.desc())
            )
            schedule_result = await self.db.execute(schedule_stmt)
            for sched in schedule_result.scalars().all():
                if sched.player_id not in current_schedules:
                    current_schedules[sched.player_id] = sched
        
        # Build youth player entries
        youth_players = []
        total_improvements = 0
        
        for player, squad_player in youth_rows:
            player_imp = player_improvements.get(player.id, {
                "total_points": 0,
                "improvements_count": 0,
                "attributes_improved": {}
            })
            
            current_schedule = current_schedules.get(player.id)
            
            # Calculate progress towards next improvement
            consecutive_weeks = current_schedule.consecutive_weeks if current_schedule else 0
            progress_pct = min(100, int((consecutive_weeks / self.YOUTH_IMPROVEMENT_WEEKS) * 100))
            
            youth_entry = {
                "player_id": player.id,
                "squad_player_id": squad_player.id,
                "name": player.name,
                "age": player.age,
                "position": player.position,
                "ca": player.ca,
                "pa": player.pa,
                "potential_gap": player.pa - player.ca,
                "current_training_focus": (
                    current_schedule.training_focus.value if current_schedule else None
                ),
                "consecutive_weeks": consecutive_weeks,
                "progress_to_next_improvement": {
                    "current_weeks": consecutive_weeks,
                    "required_weeks": self.YOUTH_IMPROVEMENT_WEEKS,
                    "percentage": progress_pct
                },
                "season_improvements": player_imp,
                "development_multiplier": (
                    self.YOUTH_DEVELOPMENT_MULTIPLIER
                    * self.YOUTH_ACADEMY_LEVEL_BONUSES.get(youth_academy_level, 1.0)
                ),
                "is_injured": current_schedule.is_injured if current_schedule else False
            }
            
            youth_players.append(youth_entry)
            total_improvements += player_imp["total_points"]
        
        # Calculate top developers
        youth_players_sorted = sorted(
            youth_players,
            key=lambda x: x["season_improvements"]["total_points"],
            reverse=True
        )
        top_developers = youth_players_sorted[:3] if youth_players_sorted else []
        
        # Calculate average development rate
        avg_development = (
            total_improvements / len(youth_players) if youth_players else 0.0
        )
        
        return {
            "career_id": career_id,
            "youth_academy_level": youth_academy_level,
            "youth_academy_level_name": self._get_academy_level_name(youth_academy_level),
            "youth_players": youth_players,
            "total_youth_players": len(youth_players),
            "total_improvements_this_season": total_improvements,
            "average_development_rate": round(avg_development, 2),
            "top_developers": [
                {
                    "player_id": p["player_id"],
                    "name": p["name"],
                    "age": p["age"],
                    "total_points_gained": p["season_improvements"]["total_points"]
                }
                for p in top_developers
            ],
            "development_bonus": {
                "youth_multiplier": self.YOUTH_DEVELOPMENT_MULTIPLIER,
                "academy_bonus": self.YOUTH_ACADEMY_LEVEL_BONUSES.get(youth_academy_level, 1.0),
                "combined_bonus": (
                    self.YOUTH_DEVELOPMENT_MULTIPLIER
                    * self.YOUTH_ACADEMY_LEVEL_BONUSES.get(youth_academy_level, 1.0)
                ),
                "weeks_to_improve": self.YOUTH_IMPROVEMENT_WEEKS,
                "regular_weeks_to_improve": self.IMPROVEMENT_WEEKS
            }
        }
    
    @staticmethod
    def _get_academy_level_name(level: int) -> str:
        """
        Get human-readable name for Youth Academy level.
        
        Args:
            level: Youth Academy level (1-5)
        
        Returns:
            Human-readable level name
        """
        level_names = {
            1: "Basic",
            2: "Standard",
            3: "Good",
            4: "Excellent",
            5: "World Class"
        }
        return level_names.get(level, "Unknown")

    async def _simulate_training_injury(
        self,
        player: Player,
        schedule: TrainingSchedule,
        career_id: int,
        season: int,
        week: int
    ) -> Optional[Dict[str, any]]:
        """
        Simulate training ground injury risk.
        
        Implements Requirement 11.6: "THE Medical_Module SHALL simulate training
        ground injuries with a weekly probability based on training intensity and
        player age."
        
        Args:
            player: Player model
            schedule: TrainingSchedule model
            career_id: Career ID
            season: Current season
            week: Current week
        
        Returns:
            Dict with injury details if injury occurred, None otherwise
        """
        # Base injury probability (1% per week)
        base_probability = 0.01
        
        # Age factor (older players more injury-prone)
        age_factor = 1.0
        if player.age > 35:
            age_factor = 2.0
        elif player.age > 30:
            age_factor = 1.5
        
        # Training intensity factor
        intensity_factor = schedule.get_injury_risk_multiplier()
        
        # Calculate final probability
        injury_probability = base_probability * age_factor * intensity_factor
        
        # Roll for injury
        if random.random() < injury_probability:
            # Determine injury severity (Minor: 70%, Moderate: 25%, Severe: 5%)
            severity_roll = random.random()
            if severity_roll < 0.70:
                severity = "minor"
                weeks_out = random.randint(1, 2)
            elif severity_roll < 0.95:
                severity = "moderate"
                weeks_out = random.randint(3, 8)
            else:
                severity = "severe"
                weeks_out = random.randint(9, 20)
            
            # Calculate expected recovery date (weeks_out * 7 days from now)
            from datetime import timedelta
            injury_date = datetime.now()
            expected_recovery_date = injury_date + timedelta(weeks=weeks_out)
            
            # Create injury record
            injury = Injury(
                career_id=career_id,
                player_id=player.id,
                squad_player_id=schedule.squad_player_id,
                injury_type=f"Training ground injury ({severity})",
                severity=severity,
                season=season,
                week=week,
                recovery_weeks=weeks_out,
                injury_date=injury_date,
                expected_recovery_date=expected_recovery_date,
                status="active"
            )
            
            self.db.add(injury)
            
            # Mark player as injured in training schedule
            schedule.set_injured()
            
            logger.warning(
                f"Player {player.name} injured in training: {severity} "
                f"({weeks_out} weeks out)"
            )
            
            return {
                "player_id": player.id,
                "player_name": player.name,
                "injury_type": injury.injury_type,
                "severity": severity,
                "weeks_out": weeks_out
            }
        
        return None
    
    async def _get_player(self, player_id: int) -> Optional[Player]:
        """
        Get player by ID.
        
        Args:
            player_id: Player ID
        
        Returns:
            Player model or None if not found
        """
        stmt = select(Player).where(Player.id == player_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def _generate_training_summary(
        self,
        total_players: int,
        improvements: List[Dict],
        declines: List[Dict],
        injuries: List[Dict],
        youth_developments: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate human-readable training summary.
        
        Args:
            total_players: Total number of players trained
            improvements: List of player improvements
            declines: List of player declines
            injuries: List of training injuries
            youth_developments: List of youth player developments
        
        Returns:
            Summary string
        """
        summary_parts = [f"{total_players} players trained"]
        
        if improvements:
            summary_parts.append(f"{len(improvements)} players improved")
        
        if youth_developments:
            summary_parts.append(f"{len(youth_developments)} youth players developed")
        
        if declines:
            summary_parts.append(f"{len(declines)} players declined")
        
        if injuries:
            summary_parts.append(f"{len(injuries)} training injuries")
        
        return ", ".join(summary_parts)
    
    async def assign_training_focus(
        self,
        career_id: int,
        squad_player_id: int,
        training_focus: TrainingFocus,
        season: int,
        week: int,
        training_intensity: Optional[TrainingIntensity] = None
    ) -> TrainingSchedule:
        """
        Assign training focus to a player for the current week.
        
        Implements Requirement 7.7: "IF a player is injured, THEN THE Training_Module
        SHALL assign that player to rehabilitation training automatically and prevent
        assignment to other focus areas."
        
        If training_intensity is not provided, the career's team-wide training
        intensity setting will be used.
        
        Args:
            career_id: Career ID
            squad_player_id: Squad player ID
            training_focus: Training focus area
            season: Current season
            week: Current week
            training_intensity: Training intensity (if None, uses career's setting)
        
        Returns:
            TrainingSchedule model
        
        Raises:
            ValueError: If trying to assign injured player to non-REHABILITATION focus
        """
        # Auto-fetch training intensity from career if not provided
        if training_intensity is None:
            career_stmt = select(Career).where(Career.id == career_id)
            career_result = await self.db.execute(career_stmt)
            career = career_result.scalar_one_or_none()
            training_intensity = (
                career.training_intensity if career else TrainingIntensity.NORMAL
            )
        
        # Check if schedule already exists for this week
        stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.squad_player_id == squad_player_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
        )
        
        result = await self.db.execute(stmt)
        existing_schedule = result.scalar_one_or_none()
        
        if existing_schedule:
            # Prevent assigning injured players to non-REHABILITATION focus
            if existing_schedule.is_injured and training_focus != TrainingFocus.REHABILITATION:
                raise ValueError(
                    f"Cannot assign injured player to {training_focus.value} training. "
                    f"Injured players must remain on rehabilitation."
                )
            
            # Update existing schedule
            old_focus = existing_schedule.training_focus
            existing_schedule.training_focus = training_focus
            existing_schedule.training_intensity = training_intensity
            
            # Reset consecutive weeks if focus changed
            if old_focus != training_focus:
                existing_schedule.reset_consecutive_weeks()
            else:
                existing_schedule.increment_consecutive_weeks()
            
            await self.db.commit()
            return existing_schedule
        
        # Get player_id from squad_player
        stmt = select(SquadPlayer).where(SquadPlayer.id == squad_player_id)
        result = await self.db.execute(stmt)
        squad_player = result.scalar_one_or_none()
        
        if not squad_player:
            raise ValueError(f"Squad player {squad_player_id} not found")
        
        # Check if player has an active injury (query Injury table)
        injury_stmt = (
            select(Injury)
            .where(
                and_(
                    Injury.career_id == career_id,
                    Injury.squad_player_id == squad_player_id,
                    Injury.status == InjuryStatus.ACTIVE
                )
            )
        )
        injury_result = await self.db.execute(injury_stmt)
        active_injury = injury_result.scalar_one_or_none()
        
        if active_injury and training_focus != TrainingFocus.REHABILITATION:
            raise ValueError(
                f"Cannot assign injured player to {training_focus.value} training. "
                f"Injured players must remain on rehabilitation."
            )
        
        # Create new schedule
        schedule = TrainingSchedule(
            career_id=career_id,
            player_id=squad_player.player_id,
            squad_player_id=squad_player_id,
            training_focus=training_focus,
            training_intensity=training_intensity,
            season=season,
            week=week,
            consecutive_weeks=1,
            is_injured=active_injury is not None
        )
        
        self.db.add(schedule)
        await self.db.commit()
        
        return schedule
    
    async def get_training_schedule(
        self,
        career_id: int,
        season: int,
        week: int
    ) -> List[TrainingSchedule]:
        """
        Get training schedule for all players in a career for a specific week.
        
        Args:
            career_id: Career ID
            season: Season number
            week: Week number
        
        Returns:
            List of TrainingSchedule models
        """
        stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
            .options(selectinload(TrainingSchedule.squad_player))
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_training_schedule_view(
        self,
        career_id: int,
        season: int,
        week: int
    ) -> Dict[str, any]:
        """
        Get a formatted training schedule view for all players in a career.
        
        Implements Requirement 7.6: "THE Training_Module SHALL display a training
        schedule view showing all players and their assigned focus areas for the
        current week."
        
        Returns a structured view showing:
        - All players and their current training focus
        - Training intensity
        - Consecutive weeks in current focus
        - Progress towards next improvement
        - Any injured players on rehabilitation
        
        Args:
            career_id: Career ID
            season: Season number
            week: Week number
        
        Returns:
            Dict containing:
                - season: Current season
                - week: Current week
                - training_intensity: Team-wide training intensity
                - total_players: Total number of players in training
                - players: List of player training entries with formatted details
                - injured_players: List of injured players on rehabilitation
                - focus_summary: Summary of players per training focus area
        """
        logger.info(
            f"Getting training schedule view for career {career_id}, "
            f"season {season}, week {week}"
        )
        
        # Get all training schedules for this week with player data via join
        stmt = (
            select(TrainingSchedule, Player, SquadPlayer)
            .join(Player, TrainingSchedule.player_id == Player.id)
            .join(SquadPlayer, TrainingSchedule.squad_player_id == SquadPlayer.id)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
            .order_by(Player.name)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        if not rows:
            logger.warning(
                f"No training schedules found for career {career_id}, "
                f"season {season}, week {week}"
            )
            return {
                "season": season,
                "week": week,
                "training_intensity": TrainingIntensity.NORMAL.value,
                "total_players": 0,
                "players": [],
                "injured_players": [],
                "focus_summary": {}
            }
        
        players_view = []
        injured_players = []
        focus_counts: Dict[str, int] = {}
        team_intensity = None
        
        for schedule, player, squad_player in rows:
            # Track team-wide intensity (should be same for all)
            if team_intensity is None:
                team_intensity = schedule.training_intensity
            
            # Calculate progress towards next improvement
            progress = self._calculate_improvement_progress(
                player.age, schedule.consecutive_weeks
            )
            
            # Build player training entry
            player_entry = {
                "player_id": player.id,
                "squad_player_id": squad_player.id,
                "name": player.name,
                "position": player.position,
                "age": player.age,
                "squad_number": squad_player.squad_number,
                "training_focus": schedule.training_focus.value,
                "training_focus_display": self._get_focus_display_name(
                    schedule.training_focus
                ),
                "training_intensity": schedule.training_intensity.value,
                "consecutive_weeks": schedule.consecutive_weeks,
                "progress": progress,
                "is_injured": schedule.is_injured,
                "affected_attributes": schedule.get_affected_attributes(),
            }
            
            if schedule.is_injured:
                injured_players.append(player_entry)
            
            players_view.append(player_entry)
            
            # Count players per focus area
            focus_key = schedule.training_focus.value
            focus_counts[focus_key] = focus_counts.get(focus_key, 0) + 1
        
        return {
            "season": season,
            "week": week,
            "training_intensity": (
                team_intensity.value if team_intensity else TrainingIntensity.NORMAL.value
            ),
            "total_players": len(players_view),
            "players": players_view,
            "injured_players": injured_players,
            "focus_summary": focus_counts
        }
    
    def _calculate_improvement_progress(
        self, player_age: int, consecutive_weeks: int
    ) -> Dict[str, any]:
        """
        Calculate progress towards next attribute improvement or decline.
        
        Args:
            player_age: Player's current age
            consecutive_weeks: Consecutive weeks in current focus
        
        Returns:
            Dict with progress information:
                - eligible: Whether player is eligible for improvement/decline
                - type: "improvement", "decline", "youth_development", or "none"
                - current_weeks: Current consecutive weeks
                - required_weeks: Weeks required for next change
                - percentage: Progress percentage (0-100)
                - description: Human-readable progress description
        """
        if self.YOUTH_PLAYER_MIN_AGE <= player_age <= self.YOUTH_PLAYER_MAX_AGE:
            # Youth player - accelerated improvement
            required = self.YOUTH_IMPROVEMENT_WEEKS
            percentage = min(100, int((consecutive_weeks / required) * 100))
            return {
                "eligible": True,
                "type": "youth_development",
                "current_weeks": consecutive_weeks,
                "required_weeks": required,
                "percentage": percentage,
                "description": (
                    f"{consecutive_weeks}/{required} weeks "
                    f"({percentage}% towards youth development - accelerated)"
                )
            }
        elif player_age < self.YOUNG_PLAYER_AGE:
            # Young player - can improve
            required = self.IMPROVEMENT_WEEKS
            percentage = min(100, int((consecutive_weeks / required) * 100))
            return {
                "eligible": True,
                "type": "improvement",
                "current_weeks": consecutive_weeks,
                "required_weeks": required,
                "percentage": percentage,
                "description": (
                    f"{consecutive_weeks}/{required} weeks "
                    f"({percentage}% towards improvement)"
                )
            }
        elif player_age > self.OLD_PLAYER_AGE:
            # Old player - may decline if not on fitness
            required = self.DECLINE_WEEKS
            percentage = min(100, int((consecutive_weeks / required) * 100))
            return {
                "eligible": True,
                "type": "decline",
                "current_weeks": consecutive_weeks,
                "required_weeks": required,
                "percentage": percentage,
                "description": (
                    f"{consecutive_weeks}/{required} weeks "
                    f"({percentage}% towards decline if not on fitness)"
                )
            }
        else:
            # Player between 24-30 - no automatic improvement/decline
            return {
                "eligible": False,
                "type": "none",
                "current_weeks": consecutive_weeks,
                "required_weeks": 0,
                "percentage": 0,
                "description": "Player age 24-30: no automatic attribute changes"
            }
    
    @staticmethod
    def _get_focus_display_name(focus: TrainingFocus) -> str:
        """
        Get human-readable display name for a training focus area.
        
        Args:
            focus: TrainingFocus enum value
        
        Returns:
            Human-readable display name
        """
        display_names = {
            TrainingFocus.GENERAL: "General",
            TrainingFocus.FITNESS: "Fitness",
            TrainingFocus.TACTICS: "Tactics",
            TrainingFocus.ATTACKING: "Attacking",
            TrainingFocus.DEFENDING: "Defending",
            TrainingFocus.SET_PIECES: "Set Pieces",
            TrainingFocus.INDIVIDUAL_TECHNICAL: "Individual Technical",
            TrainingFocus.INDIVIDUAL_MENTAL: "Individual Mental",
            TrainingFocus.REHABILITATION: "Rehabilitation",
        }
        return display_names.get(focus, focus.value)
    
    async def get_player_attribute_history(
        self,
        player_id: int,
        career_id: int,
        season: Optional[int] = None,
        limit: int = 52
    ) -> List[Dict[str, any]]:
        """
        Get player's attribute history over time.
        
        Implements Requirement 7.8: "THE Training_Module SHALL track and display
        each player's attribute history over the career."
        
        Args:
            player_id: Player ID
            career_id: Career ID
            season: Optional season number to filter by (None = all seasons)
            limit: Maximum number of records to return (default: 52 weeks)
        
        Returns:
            List of attribute history records sorted by most recent first
        """
        conditions = [
            TrainingSchedule.player_id == player_id,
            TrainingSchedule.career_id == career_id,
            TrainingSchedule.attribute_improvements.isnot(None)
        ]
        
        if season is not None:
            conditions.append(TrainingSchedule.season == season)
        
        stmt = (
            select(TrainingSchedule)
            .where(and_(*conditions))
            .order_by(TrainingSchedule.season.desc(), TrainingSchedule.week.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        schedules = result.scalars().all()
        
        history = []
        for schedule in schedules:
            if schedule.attribute_improvements:
                try:
                    improvements = json.loads(schedule.attribute_improvements)
                    history.append({
                        "season": schedule.season,
                        "week": schedule.week,
                        "training_focus": schedule.training_focus.value,
                        "changes": improvements,
                        "date": schedule.created_at.isoformat() if schedule.created_at else None
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in attribute_improvements for schedule {schedule.id}")
                    continue
        
        return history

    async def get_player_attribute_history_summary(
        self,
        player_id: int,
        career_id: int,
        season: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Get summary statistics for a player's attribute history.
        
        Provides aggregated data about total improvements, declines, and
        per-attribute breakdowns useful for displaying career progression.
        
        Args:
            player_id: Player ID
            career_id: Career ID
            season: Optional season number to filter by (None = all seasons)
        
        Returns:
            Dict containing:
                - total_changes: Total number of weeks with attribute changes
                - total_improvements: Count of individual attribute improvements
                - total_declines: Count of individual attribute declines
                - net_change: Net attribute points gained (improvements - declines)
                - attributes_improved: Dict of attribute name -> total points gained
                - attributes_declined: Dict of attribute name -> total points lost
                - best_attribute_gain: Attribute with the most improvement
                - worst_attribute_loss: Attribute with the most decline
        """
        # Fetch all history records (no limit for summary)
        history = await self.get_player_attribute_history(
            player_id=player_id,
            career_id=career_id,
            season=season,
            limit=9999
        )
        
        total_improvements = 0
        total_declines = 0
        attributes_improved: Dict[str, int] = {}
        attributes_declined: Dict[str, int] = {}
        
        for record in history:
            changes = record.get("changes", {})
            for attr_name, change_data in changes.items():
                change_value = change_data.get("change", 0)
                if change_value > 0:
                    total_improvements += 1
                    attributes_improved[attr_name] = (
                        attributes_improved.get(attr_name, 0) + change_value
                    )
                elif change_value < 0:
                    total_declines += 1
                    attributes_declined[attr_name] = (
                        attributes_declined.get(attr_name, 0) + abs(change_value)
                    )
        
        # Calculate net change
        total_gained = sum(attributes_improved.values())
        total_lost = sum(attributes_declined.values())
        net_change = total_gained - total_lost
        
        # Find best gain and worst loss
        best_attribute_gain = None
        if attributes_improved:
            best_attr = max(attributes_improved, key=attributes_improved.get)
            best_attribute_gain = {
                "attribute": best_attr,
                "points_gained": attributes_improved[best_attr]
            }
        
        worst_attribute_loss = None
        if attributes_declined:
            worst_attr = max(attributes_declined, key=attributes_declined.get)
            worst_attribute_loss = {
                "attribute": worst_attr,
                "points_lost": attributes_declined[worst_attr]
            }
        
        return {
            "total_changes": len(history),
            "total_improvements": total_improvements,
            "total_declines": total_declines,
            "net_change": net_change,
            "total_points_gained": total_gained,
            "total_points_lost": total_lost,
            "attributes_improved": attributes_improved,
            "attributes_declined": attributes_declined,
            "best_attribute_gain": best_attribute_gain,
            "worst_attribute_loss": worst_attribute_loss
        }

    async def get_player_attribute_progression(
        self,
        player_id: int,
        career_id: int,
        attributes: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Get attribute progression chart data for a player over their career.
        
        Returns time-series data suitable for rendering progression charts,
        showing how specific attributes have changed week by week.
        
        Args:
            player_id: Player ID
            career_id: Career ID
            attributes: Optional list of attribute names to track.
                        If None, tracks all attributes that have changed.
        
        Returns:
            Dict containing:
                - player_id: Player ID
                - career_id: Career ID
                - timeline: List of data points ordered chronologically
                  Each point: {season, week, attribute, old_value, new_value}
                - attribute_series: Dict of attribute name -> list of
                  {season, week, value} for chart rendering
                - current_values: Dict of attribute name -> current value
        """
        # Fetch all history in chronological order
        conditions = [
            TrainingSchedule.player_id == player_id,
            TrainingSchedule.career_id == career_id,
            TrainingSchedule.attribute_improvements.isnot(None)
        ]
        
        stmt = (
            select(TrainingSchedule)
            .where(and_(*conditions))
            .order_by(TrainingSchedule.season.asc(), TrainingSchedule.week.asc())
        )
        
        result = await self.db.execute(stmt)
        schedules = result.scalars().all()
        
        timeline = []
        attribute_series: Dict[str, List[Dict[str, any]]] = {}
        
        for schedule in schedules:
            if not schedule.attribute_improvements:
                continue
            
            try:
                changes = json.loads(schedule.attribute_improvements)
            except json.JSONDecodeError:
                continue
            
            for attr_name, change_data in changes.items():
                # Filter by requested attributes if specified
                if attributes and attr_name not in attributes:
                    continue
                
                old_value = change_data.get("old", 0)
                new_value = change_data.get("new", 0)
                
                timeline.append({
                    "season": schedule.season,
                    "week": schedule.week,
                    "attribute": attr_name,
                    "old_value": old_value,
                    "new_value": new_value,
                    "change": change_data.get("change", new_value - old_value)
                })
                
                # Build per-attribute series for chart rendering
                if attr_name not in attribute_series:
                    attribute_series[attr_name] = []
                    # Add the initial value as the first data point
                    attribute_series[attr_name].append({
                        "season": schedule.season,
                        "week": schedule.week,
                        "value": old_value,
                        "is_initial": True
                    })
                
                attribute_series[attr_name].append({
                    "season": schedule.season,
                    "week": schedule.week,
                    "value": new_value,
                    "is_initial": False
                })
        
        # Get current attribute values from the player
        player = await self._get_player(player_id)
        current_values = {}
        if player:
            for attr_name in attribute_series.keys():
                value = getattr(player, attr_name, None)
                if value is not None:
                    current_values[attr_name] = value
        
        return {
            "player_id": player_id,
            "career_id": career_id,
            "timeline": timeline,
            "attribute_series": attribute_series,
            "current_values": current_values
        }

    async def set_player_injured(
        self,
        career_id: int,
        squad_player_id: int,
        season: int,
        week: int
    ) -> Optional[TrainingSchedule]:
        """
        Set a player's training to REHABILITATION when they get injured.
        
        This method is called when a player gets injured (from match or training)
        to automatically assign them to rehabilitation training. It saves the
        player's previous training focus so it can be restored on recovery.
        
        Implements Requirement 7.7: "IF a player is injured, THEN THE Training_Module
        SHALL assign that player to rehabilitation training automatically and prevent
        assignment to other focus areas."
        
        Args:
            career_id: Career ID
            squad_player_id: Squad player ID
            season: Current season
            week: Current week
        
        Returns:
            Updated TrainingSchedule or None if no schedule exists
        """
        logger.info(
            f"Setting player (squad_player_id={squad_player_id}) to rehabilitation "
            f"for career {career_id}, season {season}, week {week}"
        )
        
        # Find the player's current training schedule
        stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.squad_player_id == squad_player_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
        )
        
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if schedule:
            # Use the model's set_injured method which saves previous focus
            schedule.set_injured()
            await self.db.commit()
            logger.info(
                f"Player (squad_player_id={squad_player_id}) moved to rehabilitation. "
                f"Previous focus: {schedule.previous_training_focus}"
            )
            return schedule
        else:
            # No schedule exists for this week - create one with REHABILITATION
            # Get player_id from squad_player
            sp_stmt = select(SquadPlayer).where(SquadPlayer.id == squad_player_id)
            sp_result = await self.db.execute(sp_stmt)
            squad_player = sp_result.scalar_one_or_none()
            
            if not squad_player:
                logger.warning(f"Squad player {squad_player_id} not found")
                return None
            
            schedule = TrainingSchedule(
                career_id=career_id,
                player_id=squad_player.player_id,
                squad_player_id=squad_player_id,
                training_focus=TrainingFocus.REHABILITATION,
                training_intensity=TrainingIntensity.NORMAL,
                season=season,
                week=week,
                consecutive_weeks=1,
                is_injured=True,
                previous_training_focus=TrainingFocus.GENERAL.value
            )
            
            self.db.add(schedule)
            await self.db.commit()
            logger.info(
                f"Created rehabilitation schedule for player "
                f"(squad_player_id={squad_player_id})"
            )
            return schedule
    
    async def recover_player_from_injury(
        self,
        career_id: int,
        squad_player_id: int,
        season: int,
        week: int
    ) -> Optional[TrainingSchedule]:
        """
        Handle player recovery from injury by restoring their previous training focus.
        
        When a player recovers from injury, their training focus is restored to
        what it was before the injury, or defaults to GENERAL if no previous
        focus was saved.
        
        Args:
            career_id: Career ID
            squad_player_id: Squad player ID
            season: Current season
            week: Current week
        
        Returns:
            Updated TrainingSchedule or None if no schedule exists
        """
        logger.info(
            f"Recovering player (squad_player_id={squad_player_id}) from injury "
            f"for career {career_id}, season {season}, week {week}"
        )
        
        # Find the player's current training schedule
        stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.squad_player_id == squad_player_id,
                    TrainingSchedule.season == season,
                    TrainingSchedule.week == week
                )
            )
        )
        
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if schedule and schedule.is_injured:
            # Use the model's clear_injured method which restores previous focus
            schedule.clear_injured()
            await self.db.commit()
            logger.info(
                f"Player (squad_player_id={squad_player_id}) recovered. "
                f"Training focus restored to: {schedule.training_focus.value}"
            )
            return schedule
        elif schedule:
            logger.warning(
                f"Player (squad_player_id={squad_player_id}) is not marked as injured"
            )
            return schedule
        else:
            logger.warning(
                f"No training schedule found for player "
                f"(squad_player_id={squad_player_id}) in season {season}, week {week}"
            )
            return None

    async def set_training_intensity(
        self,
        career_id: int,
        intensity: TrainingIntensity
    ) -> Dict[str, any]:
        """
        Set team-wide training intensity for a career.
        
        Updates the career's training intensity setting and applies it to all
        existing training schedules for the current week. New schedules created
        after this call will also use the updated intensity.
        
        Training Intensity Effects:
            - LIGHT: 0.8x development rate, 0.7x injury risk
            - NORMAL: 1.0x development rate, 1.0x injury risk
            - HEAVY: 1.2x development rate, 1.5x injury risk
        
        Args:
            career_id: Career ID
            intensity: New training intensity (LIGHT, NORMAL, or HEAVY)
        
        Returns:
            Dict containing:
                - career_id: Career ID
                - previous_intensity: Previous intensity value
                - new_intensity: New intensity value
                - schedules_updated: Number of training schedules updated
                - development_multiplier: New development rate multiplier
                - injury_risk_multiplier: New injury risk multiplier
        
        Raises:
            ValueError: If career_id is invalid or intensity is not a valid TrainingIntensity
        """
        logger.info(
            f"Setting training intensity to {intensity.value} for career {career_id}"
        )
        
        # Get the career to update
        stmt = select(Career).where(Career.id == career_id)
        result = await self.db.execute(stmt)
        career = result.scalar_one_or_none()
        
        if not career:
            raise ValueError(f"Career {career_id} not found")
        
        # Store previous intensity
        previous_intensity = career.training_intensity
        
        # Update career-level training intensity
        career.training_intensity = intensity
        
        # Update all current training schedules for this career's current week
        schedule_stmt = (
            select(TrainingSchedule)
            .where(
                and_(
                    TrainingSchedule.career_id == career_id,
                    TrainingSchedule.season == career.current_season,
                    TrainingSchedule.week == career.current_week
                )
            )
        )
        
        schedule_result = await self.db.execute(schedule_stmt)
        schedules = schedule_result.scalars().all()
        
        schedules_updated = 0
        for schedule in schedules:
            schedule.training_intensity = intensity
            schedules_updated += 1
        
        await self.db.commit()
        
        # Calculate multipliers for the new intensity
        development_multiplier = self._get_development_multiplier(intensity)
        injury_risk_multiplier = self._get_injury_risk_multiplier(intensity)
        
        logger.info(
            f"Training intensity updated for career {career_id}: "
            f"{previous_intensity.value} -> {intensity.value}, "
            f"{schedules_updated} schedules updated"
        )
        
        return {
            "career_id": career_id,
            "previous_intensity": previous_intensity.value,
            "new_intensity": intensity.value,
            "schedules_updated": schedules_updated,
            "development_multiplier": development_multiplier,
            "injury_risk_multiplier": injury_risk_multiplier
        }
    
    async def get_training_intensity(
        self,
        career_id: int
    ) -> Dict[str, any]:
        """
        Get the current team-wide training intensity for a career.
        
        Args:
            career_id: Career ID
        
        Returns:
            Dict containing:
                - career_id: Career ID
                - intensity: Current training intensity value (light, normal, heavy)
                - development_multiplier: Current development rate multiplier
                - injury_risk_multiplier: Current injury risk multiplier
                - description: Human-readable description of the intensity effects
        
        Raises:
            ValueError: If career_id is invalid
        """
        stmt = select(Career).where(Career.id == career_id)
        result = await self.db.execute(stmt)
        career = result.scalar_one_or_none()
        
        if not career:
            raise ValueError(f"Career {career_id} not found")
        
        intensity = career.training_intensity
        development_multiplier = self._get_development_multiplier(intensity)
        injury_risk_multiplier = self._get_injury_risk_multiplier(intensity)
        
        descriptions = {
            TrainingIntensity.LIGHT: (
                "Light training: Reduced injury risk (0.7x) but slower "
                "attribute development (0.8x). Ideal for injury-prone squads "
                "or during congested fixture periods."
            ),
            TrainingIntensity.NORMAL: (
                "Normal training: Balanced injury risk (1.0x) and attribute "
                "development (1.0x). Standard setting for most situations."
            ),
            TrainingIntensity.HEAVY: (
                "Heavy training: Faster attribute development (1.2x) but "
                "significantly higher injury risk (1.5x). Best used with "
                "a deep squad and good medical facilities."
            ),
        }
        
        return {
            "career_id": career_id,
            "intensity": intensity.value,
            "development_multiplier": development_multiplier,
            "injury_risk_multiplier": injury_risk_multiplier,
            "description": descriptions.get(intensity, "Unknown intensity")
        }
    
    @staticmethod
    def _get_development_multiplier(intensity: TrainingIntensity) -> float:
        """
        Get development rate multiplier for a given training intensity.
        
        Args:
            intensity: Training intensity level
        
        Returns:
            float: Development rate multiplier
        """
        multipliers = {
            TrainingIntensity.LIGHT: 0.8,
            TrainingIntensity.NORMAL: 1.0,
            TrainingIntensity.HEAVY: 1.2,
        }
        return multipliers.get(intensity, 1.0)
    
    @staticmethod
    def _get_injury_risk_multiplier(intensity: TrainingIntensity) -> float:
        """
        Get injury risk multiplier for a given training intensity.
        
        Args:
            intensity: Training intensity level
        
        Returns:
            float: Injury risk multiplier
        """
        multipliers = {
            TrainingIntensity.LIGHT: 0.7,
            TrainingIntensity.NORMAL: 1.0,
            TrainingIntensity.HEAVY: 1.5,
        }
        return multipliers.get(intensity, 1.0)

    @staticmethod
    def calculate_injury_risk(player: Player, intensity: TrainingIntensity) -> Dict[str, any]:
        """
        Calculate injury risk probability for a player at a given training intensity.
        
        This is a pure calculation method with no side effects - it does not roll
        for injury or modify any state. Use this to display risk information to
        the player-manager.
        
        The calculation follows the same formula as _simulate_training_injury:
            final_probability = base_probability * age_factor * intensity_factor
        
        Where:
            - base_probability: 0.01 (1% per week)
            - age_factor: 1.0 (age ≤ 30), 1.5 (age 31-35), 2.0 (age > 35)
            - intensity_factor: 0.7 (Light), 1.0 (Normal), 1.5 (Heavy)
        
        Args:
            player: Player model with age attribute
            intensity: Training intensity level (LIGHT, NORMAL, or HEAVY)
        
        Returns:
            Dict containing:
                - player_id: Player ID
                - player_name: Player name
                - age: Player age
                - base_probability: Base injury probability (0.01)
                - age_factor: Age-based multiplier
                - intensity_factor: Intensity-based multiplier
                - final_probability: Combined injury probability per week
                - risk_percentage: Probability as a percentage string
                - risk_level: Categorical risk level (Low, Medium, High, Very High)
        """
        # Base injury probability (1% per week)
        base_probability = 0.01

        # Age factor (older players more injury-prone)
        age_factor = 1.0
        if player.age > 35:
            age_factor = 2.0
        elif player.age > 30:
            age_factor = 1.5

        # Training intensity factor
        intensity_multipliers = {
            TrainingIntensity.LIGHT: 0.7,
            TrainingIntensity.NORMAL: 1.0,
            TrainingIntensity.HEAVY: 1.5,
        }
        intensity_factor = intensity_multipliers.get(intensity, 1.0)

        # Calculate final probability
        final_probability = base_probability * age_factor * intensity_factor

        # Determine risk level category
        if final_probability <= 0.01:
            risk_level = "Low"
        elif final_probability <= 0.015:
            risk_level = "Medium"
        elif final_probability <= 0.02:
            risk_level = "High"
        else:
            risk_level = "Very High"

        return {
            "player_id": player.id,
            "player_name": player.name,
            "age": player.age,
            "base_probability": base_probability,
            "age_factor": age_factor,
            "intensity_factor": intensity_factor,
            "final_probability": final_probability,
            "risk_percentage": f"{final_probability * 100:.2f}%",
            "risk_level": risk_level,
        }

    async def get_squad_injury_risk_report(
        self,
        career_id: int
    ) -> Dict[str, any]:
        """
        Generate an injury risk report for the entire squad in a career.
        
        Retrieves all squad players and calculates their individual injury risk
        based on the career's current training intensity and each player's age.
        
        Args:
            career_id: Career ID
        
        Returns:
            Dict containing:
                - career_id: Career ID
                - intensity: Current training intensity
                - total_players: Number of players in squad
                - risk_summary: Dict with counts per risk level
                - players: List of individual player risk assessments (sorted by risk, highest first)
        
        Raises:
            ValueError: If career_id is invalid
        """
        # Get career to determine current intensity
        stmt = select(Career).where(Career.id == career_id)
        result = await self.db.execute(stmt)
        career = result.scalar_one_or_none()

        if not career:
            raise ValueError(f"Career {career_id} not found")

        intensity = career.training_intensity

        # Get all squad players with their player data using explicit join
        squad_stmt = (
            select(Player, SquadPlayer)
            .join(SquadPlayer, SquadPlayer.player_id == Player.id)
            .where(SquadPlayer.career_id == career_id)
            .order_by(Player.name)
        )
        squad_result = await self.db.execute(squad_stmt)
        squad_rows = squad_result.all()

        # Calculate risk for each player
        player_risks = []
        risk_summary = {"Low": 0, "Medium": 0, "High": 0, "Very High": 0}

        for player, squad_player in squad_rows:
            risk_data = self.calculate_injury_risk(player, intensity)
            player_risks.append(risk_data)
            risk_summary[risk_data["risk_level"]] += 1

        # Sort by final_probability descending (highest risk first)
        player_risks.sort(key=lambda x: x["final_probability"], reverse=True)

        return {
            "career_id": career_id,
            "intensity": intensity.value,
            "total_players": len(player_risks),
            "risk_summary": risk_summary,
            "players": player_risks,
        }
