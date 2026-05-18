"""
Infrastructure Service - Manages club infrastructure categories and upgrades

This module implements the Infrastructure System for managing club infrastructure
across 5 categories: Stadium, Training Facilities, Youth Academy, Medical Centre,
and Scouting Network.

Each category has 5 upgrade levels (1-5):
    1 = Basic
    2 = Standard
    3 = Good
    4 = Excellent
    5 = World Class

Key Features:
- Define infrastructure categories with names, descriptions, and effects per level
- Define upgrade costs and durations per level for each category
- Provide overview of all infrastructure for a club
- Provide detailed info for a single category
- Calculate bonuses/effects based on current level

Implements Requirement 9: Инфраструктура клуба
"""

import random
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sql_func

from app.models.club import Club
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.staff import Staff
from app.models.infrastructure_upgrade import InfrastructureUpgrade, UpgradeStatus
from app.services.finance_service import FinanceService
from app.models.financial_transaction import ExpenditureCategory
from app.core.logging import get_logger

logger = get_logger(__name__)


class InfrastructureCategory(str, Enum):
    """Enumeration of the 5 infrastructure categories."""
    STADIUM = "stadium"
    TRAINING_FACILITIES = "training_facilities"
    YOUTH_ACADEMY = "youth_academy"
    MEDICAL_CENTRE = "medical_centre"
    SCOUTING_NETWORK = "scouting_network"


# Level names mapping (1-5)
LEVEL_NAMES = {
    1: "Basic",
    2: "Standard",
    3: "Good",
    4: "Excellent",
    5: "World Class",
}


# Infrastructure category definitions with descriptions
CATEGORY_DEFINITIONS = {
    InfrastructureCategory.STADIUM: {
        "name": "Stadium",
        "description": (
            "The club's stadium determines matchday revenue capacity. "
            "Higher levels increase seating capacity and facilities, "
            "attracting more fans and generating more income per match."
        ),
        "model_field": "stadium_level",
    },
    InfrastructureCategory.TRAINING_FACILITIES: {
        "name": "Training Facilities",
        "description": (
            "Training facilities affect player attribute development rates. "
            "Better facilities provide bonus multipliers to all training focus areas, "
            "helping players reach their potential faster."
        ),
        "model_field": "training_facilities_level",
    },
    InfrastructureCategory.YOUTH_ACADEMY: {
        "name": "Youth Academy",
        "description": (
            "The youth academy determines the quality of youth prospects generated. "
            "Higher levels produce more talented young players with higher potential ability "
            "and better starting attributes."
        ),
        "model_field": "youth_academy_level",
    },
    InfrastructureCategory.MEDICAL_CENTRE: {
        "name": "Medical Centre",
        "description": (
            "The medical centre affects player injury recovery times. "
            "Each level above Standard reduces average recovery time by 10%, "
            "getting players back on the pitch faster."
        ),
        "model_field": "medical_centre_level",
    },
    InfrastructureCategory.SCOUTING_NETWORK: {
        "name": "Scouting Network",
        "description": (
            "The scouting network determines the accuracy of player attribute "
            "information revealed during scouting. Higher levels reveal more "
            "accurate data and reduce scouting report generation time."
        ),
        "model_field": "scouting_network_level",
    },
}


# Effects/bonuses per level for each category
# Each level maps to a dict of effect names and their values
CATEGORY_EFFECTS = {
    InfrastructureCategory.STADIUM: {
        1: {
            "matchday_revenue_multiplier": 1.0,
            "max_capacity": 10_000,
            "fan_satisfaction_bonus": 0,
            "description": "Basic stadium with minimal facilities. Limited revenue potential.",
        },
        2: {
            "matchday_revenue_multiplier": 1.25,
            "max_capacity": 25_000,
            "fan_satisfaction_bonus": 5,
            "description": "Standard stadium with adequate seating and basic amenities.",
        },
        3: {
            "matchday_revenue_multiplier": 1.5,
            "max_capacity": 40_000,
            "fan_satisfaction_bonus": 10,
            "description": "Good stadium with modern facilities and corporate boxes.",
        },
        4: {
            "matchday_revenue_multiplier": 1.85,
            "max_capacity": 60_000,
            "fan_satisfaction_bonus": 15,
            "description": "Excellent stadium with premium hospitality and retail areas.",
        },
        5: {
            "matchday_revenue_multiplier": 2.25,
            "max_capacity": 80_000,
            "fan_satisfaction_bonus": 20,
            "description": "World class stadium rivalling the best venues in world football.",
        },
    },
    InfrastructureCategory.TRAINING_FACILITIES: {
        1: {
            "training_bonus_multiplier": 1.0,
            "injury_prevention_bonus": 0,
            "description": "Basic training pitches with minimal equipment.",
        },
        2: {
            "training_bonus_multiplier": 1.1,
            "injury_prevention_bonus": 5,
            "description": "Standard facilities with gym and recovery areas.",
        },
        3: {
            "training_bonus_multiplier": 1.25,
            "injury_prevention_bonus": 10,
            "description": "Good facilities with specialist equipment and analysis tools.",
        },
        4: {
            "training_bonus_multiplier": 1.4,
            "injury_prevention_bonus": 15,
            "description": "Excellent facilities with cutting-edge technology and dedicated areas.",
        },
        5: {
            "training_bonus_multiplier": 1.6,
            "injury_prevention_bonus": 20,
            "description": "World class training complex with state-of-the-art everything.",
        },
    },
    InfrastructureCategory.YOUTH_ACADEMY: {
        1: {
            "youth_quality_bonus": 0,
            "max_youth_pa": 120,
            "youth_intake_size": 3,
            "description": "Basic youth setup producing limited prospects.",
        },
        2: {
            "youth_quality_bonus": 5,
            "max_youth_pa": 140,
            "youth_intake_size": 4,
            "description": "Standard academy with structured development programme.",
        },
        3: {
            "youth_quality_bonus": 10,
            "max_youth_pa": 160,
            "youth_intake_size": 5,
            "description": "Good academy attracting talented youngsters from the region.",
        },
        4: {
            "youth_quality_bonus": 15,
            "max_youth_pa": 180,
            "youth_intake_size": 6,
            "description": "Excellent academy with national reputation for development.",
        },
        5: {
            "youth_quality_bonus": 20,
            "max_youth_pa": 200,
            "youth_intake_size": 8,
            "description": "World class academy producing future international stars.",
        },
    },
    InfrastructureCategory.MEDICAL_CENTRE: {
        1: {
            "recovery_time_reduction_percent": 0,
            "injury_detection_bonus": 0,
            "rehab_quality_bonus": 0,
            "description": "Basic medical room with limited diagnostic equipment.",
        },
        2: {
            "recovery_time_reduction_percent": 0,
            "injury_detection_bonus": 5,
            "rehab_quality_bonus": 5,
            "description": "Standard medical centre with qualified physiotherapists.",
        },
        3: {
            "recovery_time_reduction_percent": 10,
            "injury_detection_bonus": 10,
            "rehab_quality_bonus": 10,
            "description": "Good medical centre with modern rehabilitation equipment.",
        },
        4: {
            "recovery_time_reduction_percent": 20,
            "injury_detection_bonus": 15,
            "rehab_quality_bonus": 15,
            "description": "Excellent medical centre with specialist consultants on staff.",
        },
        5: {
            "recovery_time_reduction_percent": 30,
            "injury_detection_bonus": 20,
            "rehab_quality_bonus": 20,
            "description": "World class medical facility with cutting-edge treatment options.",
        },
    },
    InfrastructureCategory.SCOUTING_NETWORK: {
        1: {
            "attribute_accuracy_percent": 60,
            "scouting_speed_bonus": 0,
            "scouting_range": "local",
            "description": "Basic scouting limited to local region only.",
        },
        2: {
            "attribute_accuracy_percent": 70,
            "scouting_speed_bonus": 10,
            "scouting_range": "national",
            "description": "Standard network covering the domestic league.",
        },
        3: {
            "attribute_accuracy_percent": 80,
            "scouting_speed_bonus": 20,
            "scouting_range": "continental",
            "description": "Good network with scouts across the continent.",
        },
        4: {
            "attribute_accuracy_percent": 90,
            "scouting_speed_bonus": 30,
            "scouting_range": "international",
            "description": "Excellent network with global reach and detailed reports.",
        },
        5: {
            "attribute_accuracy_percent": 95,
            "scouting_speed_bonus": 40,
            "scouting_range": "worldwide",
            "description": "World class network with scouts in every major football nation.",
        },
    },
}


# Upgrade costs per level (cost to upgrade FROM current level TO next level)
# Key is the target level (level being upgraded to)
UPGRADE_COSTS = {
    InfrastructureCategory.STADIUM: {
        2: 5_000_000,
        3: 15_000_000,
        4: 35_000_000,
        5: 75_000_000,
    },
    InfrastructureCategory.TRAINING_FACILITIES: {
        2: 2_000_000,
        3: 5_000_000,
        4: 12_000_000,
        5: 25_000_000,
    },
    InfrastructureCategory.YOUTH_ACADEMY: {
        2: 3_000_000,
        3: 8_000_000,
        4: 18_000_000,
        5: 40_000_000,
    },
    InfrastructureCategory.MEDICAL_CENTRE: {
        2: 1_500_000,
        3: 4_000_000,
        4: 10_000_000,
        5: 20_000_000,
    },
    InfrastructureCategory.SCOUTING_NETWORK: {
        2: 1_000_000,
        3: 3_000_000,
        4: 8_000_000,
        5: 15_000_000,
    },
}


# Upgrade durations in weeks per level (time to complete upgrade TO target level)
# Requirement 9.9: "Infrastructure upgrades SHALL take between 4 and 26 in-game weeks"
UPGRADE_DURATIONS = {
    InfrastructureCategory.STADIUM: {
        2: 8,
        3: 14,
        4: 20,
        5: 26,
    },
    InfrastructureCategory.TRAINING_FACILITIES: {
        2: 4,
        3: 8,
        4: 12,
        5: 18,
    },
    InfrastructureCategory.YOUTH_ACADEMY: {
        2: 6,
        3: 10,
        4: 16,
        5: 22,
    },
    InfrastructureCategory.MEDICAL_CENTRE: {
        2: 4,
        3: 6,
        4: 10,
        5: 16,
    },
    InfrastructureCategory.SCOUTING_NETWORK: {
        2: 4,
        3: 6,
        4: 10,
        5: 14,
    },
}


class InfrastructureService:
    """
    Service for managing club infrastructure categories and upgrades.

    Implements Requirement 9: Инфраструктура клуба

    Provides methods to:
    - Get an overview of all 5 infrastructure categories for a club
    - Get detailed information for a single category
    - Look up upgrade costs, durations, and effects per level
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize InfrastructureService.

        Args:
            db_session: Async database session for persistence operations
        """
        self.db = db_session

    async def get_infrastructure_overview(self, club_id: int) -> Dict:
        """
        Get an overview of all 5 infrastructure categories for a club.

        Returns current levels, level names, and brief effects for each category.

        Args:
            club_id: ID of the club

        Returns:
            Dict containing:
                - club_id: Club ID
                - club_name: Club name
                - categories: List of category summaries with current level and effects
                - average_level: Average infrastructure level across all categories

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        categories = []
        for category in InfrastructureCategory:
            definition = CATEGORY_DEFINITIONS[category]
            field_name = definition["model_field"]
            current_level = getattr(club, field_name)
            effects = CATEGORY_EFFECTS[category][current_level]

            category_summary = {
                "category": category.value,
                "name": definition["name"],
                "description": definition["description"],
                "current_level": current_level,
                "level_name": LEVEL_NAMES[current_level],
                "effects": effects,
                "can_upgrade": current_level < 5,
            }

            # Add next upgrade info if not at max level
            if current_level < 5:
                next_level = current_level + 1
                category_summary["next_upgrade"] = {
                    "target_level": next_level,
                    "target_level_name": LEVEL_NAMES[next_level],
                    "cost": UPGRADE_COSTS[category][next_level],
                    "duration_weeks": UPGRADE_DURATIONS[category][next_level],
                }

            categories.append(category_summary)

        # Calculate average level
        levels = [
            club.stadium_level,
            club.training_facilities_level,
            club.youth_academy_level,
            club.medical_centre_level,
            club.scouting_network_level,
        ]
        average_level = sum(levels) / len(levels)

        return {
            "club_id": club_id,
            "club_name": club.name,
            "categories": categories,
            "average_level": round(average_level, 2),
        }

    async def get_category_details(
        self, club_id: int, category: InfrastructureCategory
    ) -> Dict:
        """
        Get detailed information for a single infrastructure category.

        Returns full details including current level, all level effects,
        upgrade path with costs and durations.

        Args:
            club_id: ID of the club
            category: The infrastructure category to get details for

        Returns:
            Dict containing:
                - club_id: Club ID
                - category: Category enum value
                - name: Category display name
                - description: Category description
                - current_level: Current level (1-5)
                - level_name: Current level name
                - current_effects: Effects at current level
                - all_levels: List of all 5 levels with effects
                - upgrade_path: Remaining upgrades with costs and durations
                - is_max_level: Whether the category is at max level

        Raises:
            ValueError: If club_id is not found or category is invalid
        """
        if not isinstance(category, InfrastructureCategory):
            raise ValueError(
                f"Invalid category: {category}. "
                f"Valid categories: {[c.value for c in InfrastructureCategory]}"
            )

        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        definition = CATEGORY_DEFINITIONS[category]
        field_name = definition["model_field"]
        current_level = getattr(club, field_name)

        # Build all levels info
        all_levels = []
        for level in range(1, 6):
            level_info = {
                "level": level,
                "level_name": LEVEL_NAMES[level],
                "effects": CATEGORY_EFFECTS[category][level],
                "is_current": level == current_level,
            }
            # Add upgrade cost/duration for levels 2-5
            if level >= 2:
                level_info["upgrade_cost"] = UPGRADE_COSTS[category][level]
                level_info["upgrade_duration_weeks"] = UPGRADE_DURATIONS[category][level]
            all_levels.append(level_info)

        # Build upgrade path (remaining upgrades from current level)
        upgrade_path = []
        for level in range(current_level + 1, 6):
            upgrade_path.append({
                "target_level": level,
                "target_level_name": LEVEL_NAMES[level],
                "cost": UPGRADE_COSTS[category][level],
                "duration_weeks": UPGRADE_DURATIONS[category][level],
                "effects": CATEGORY_EFFECTS[category][level],
            })

        return {
            "club_id": club_id,
            "category": category.value,
            "name": definition["name"],
            "description": definition["description"],
            "current_level": current_level,
            "level_name": LEVEL_NAMES[current_level],
            "current_effects": CATEGORY_EFFECTS[category][current_level],
            "all_levels": all_levels,
            "upgrade_path": upgrade_path,
            "is_max_level": current_level >= 5,
        }

    def get_upgrade_cost(
        self, category: InfrastructureCategory, target_level: int
    ) -> int:
        """
        Get the cost to upgrade a category to a specific level.

        Args:
            category: The infrastructure category
            target_level: The target level (2-5)

        Returns:
            The upgrade cost in currency units

        Raises:
            ValueError: If target_level is invalid (must be 2-5)
        """
        if target_level < 2 or target_level > 5:
            raise ValueError(
                f"Target level must be between 2 and 5, got {target_level}"
            )
        return UPGRADE_COSTS[category][target_level]

    def get_upgrade_duration(
        self, category: InfrastructureCategory, target_level: int
    ) -> int:
        """
        Get the duration in weeks to upgrade a category to a specific level.

        Args:
            category: The infrastructure category
            target_level: The target level (2-5)

        Returns:
            The upgrade duration in weeks

        Raises:
            ValueError: If target_level is invalid (must be 2-5)
        """
        if target_level < 2 or target_level > 5:
            raise ValueError(
                f"Target level must be between 2 and 5, got {target_level}"
            )
        return UPGRADE_DURATIONS[category][target_level]

    def get_level_effects(
        self, category: InfrastructureCategory, level: int
    ) -> Dict:
        """
        Get the effects/bonuses for a category at a specific level.

        Args:
            category: The infrastructure category
            level: The level (1-5)

        Returns:
            Dict of effect names and their values at the specified level

        Raises:
            ValueError: If level is invalid (must be 1-5)
        """
        if level < 1 or level > 5:
            raise ValueError(f"Level must be between 1 and 5, got {level}")
        return CATEGORY_EFFECTS[category][level]

    def get_all_categories(self) -> List[Dict]:
        """
        Get a list of all infrastructure category definitions.

        Returns:
            List of dicts with category name, description, and enum value
        """
        return [
            {
                "category": category.value,
                "name": CATEGORY_DEFINITIONS[category]["name"],
                "description": CATEGORY_DEFINITIONS[category]["description"],
            }
            for category in InfrastructureCategory
        ]

    async def _get_club(self, club_id: int) -> Optional[Club]:
        """
        Retrieve a club by ID from the database.

        Args:
            club_id: ID of the club

        Returns:
            Club instance or None if not found
        """
        stmt = select(Club).where(Club.id == club_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # --- Infrastructure Upgrade Request System (Task 12.3) ---

    async def request_upgrade(
        self,
        club_id: int,
        career_id: int,
        category: InfrastructureCategory,
        season: int,
        week: int,
    ) -> Dict:
        """
        Request an infrastructure upgrade for a club.

        Validates the upgrade is possible, checks affordability, ensures no
        duplicate in-progress upgrades for the same category, deducts cost,
        and creates an upgrade record with a completion date.

        Implements Requirement 9.3: "THE Career_Manager SHALL allow the player-manager
        to request infrastructure upgrades from the board, subject to board approval
        and club financial health."

        Args:
            club_id: ID of the club requesting the upgrade
            career_id: ID of the career
            category: Infrastructure category to upgrade
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            Dict containing:
                - success: Whether the upgrade was approved
                - message: Human-readable result message
                - upgrade: Upgrade details (if approved)

        Raises:
            ValueError: If club_id is not found or category is invalid
        """
        if not isinstance(category, InfrastructureCategory):
            raise ValueError(
                f"Invalid category: {category}. "
                f"Valid categories: {[c.value for c in InfrastructureCategory]}"
            )

        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        # 1. Check if already at max level
        definition = CATEGORY_DEFINITIONS[category]
        field_name = definition["model_field"]
        current_level = getattr(club, field_name)

        if current_level >= 5:
            return {
                "success": False,
                "message": (
                    f"{definition['name']} is already at maximum level "
                    f"(World Class). No further upgrades available."
                ),
                "upgrade": None,
            }

        target_level = current_level + 1
        cost = UPGRADE_COSTS[category][target_level]
        duration = UPGRADE_DURATIONS[category][target_level]

        # 2. Check if there's already an upgrade in progress for this category
        active_upgrade = await self._get_active_upgrade_for_category(
            club_id, career_id, category
        )
        if active_upgrade is not None:
            return {
                "success": False,
                "message": (
                    f"{definition['name']} already has an upgrade in progress "
                    f"(to level {active_upgrade.to_level} - "
                    f"{LEVEL_NAMES[active_upgrade.to_level]}). "
                    f"Wait for it to complete before requesting another."
                ),
                "upgrade": None,
            }

        # 3. Check if the club can afford the upgrade using FinanceService
        finance_service = FinanceService(self.db)
        validation = await finance_service.validate_expenditure(
            club_id=club_id,
            amount=cost,
            category=ExpenditureCategory.INFRASTRUCTURE,
        )

        if not validation["allowed"]:
            return {
                "success": False,
                "message": (
                    f"Cannot afford {definition['name']} upgrade to "
                    f"{LEVEL_NAMES[target_level]}. "
                    f"Cost: {cost:,}. Reason: {validation['reason']}"
                ),
                "upgrade": None,
            }

        # 4. Deduct the cost from club balance
        await finance_service.record_expenditure(
            club_id=club_id,
            career_id=career_id,
            category=ExpenditureCategory.INFRASTRUCTURE,
            amount=cost,
            description=(
                f"Infrastructure upgrade: {definition['name']} "
                f"from {LEVEL_NAMES[current_level]} to {LEVEL_NAMES[target_level]}"
            ),
            season=season,
            week=week,
        )

        # 5. Calculate completion date
        completion_season, completion_week = self._calculate_completion_date(
            season, week, duration
        )

        # 6. Create the upgrade record
        upgrade = InfrastructureUpgrade(
            club_id=club_id,
            career_id=career_id,
            category=category.value,
            from_level=current_level,
            to_level=target_level,
            cost=cost,
            duration_weeks=duration,
            start_season=season,
            start_week=week,
            completion_season=completion_season,
            completion_week=completion_week,
            status=UpgradeStatus.IN_PROGRESS.value,
        )

        self.db.add(upgrade)
        await self.db.flush()

        logger.info(
            f"Infrastructure upgrade requested: club={club_id}, "
            f"category={category.value}, "
            f"from_level={current_level}, to_level={target_level}, "
            f"cost={cost}, duration={duration} weeks, "
            f"completion: season {completion_season} week {completion_week}"
        )

        return {
            "success": True,
            "message": (
                f"{definition['name']} upgrade to {LEVEL_NAMES[target_level]} approved! "
                f"Cost: {cost:,}. "
                f"Completion in {duration} weeks "
                f"(Season {completion_season}, Week {completion_week})."
            ),
            "upgrade": upgrade.to_dict(),
        }

    async def check_upgrade_progress(
        self,
        club_id: int,
        career_id: int,
        season: int,
        week: int,
    ) -> Dict:
        """
        Check if any in-progress upgrades have completed.

        This method should be called during advance_week to check if any
        upgrades have reached their completion date. Completed upgrades
        will have their level applied to the club.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            season: Current in-game season
            week: Current in-game week (1-52)

        Returns:
            Dict containing:
                - completed_upgrades: List of upgrades that were completed this check
                - still_in_progress: List of upgrades still in progress
        """
        # Get all in-progress upgrades for this club/career
        stmt = select(InfrastructureUpgrade).where(
            and_(
                InfrastructureUpgrade.club_id == club_id,
                InfrastructureUpgrade.career_id == career_id,
                InfrastructureUpgrade.status == UpgradeStatus.IN_PROGRESS.value,
            )
        )
        result = await self.db.execute(stmt)
        active_upgrades = list(result.scalars().all())

        completed_upgrades = []
        still_in_progress = []

        for upgrade in active_upgrades:
            if self._is_upgrade_due(upgrade, season, week):
                # Complete this upgrade
                completed = await self.complete_upgrade(upgrade.id)
                if completed:
                    completed_upgrades.append(completed)
            else:
                still_in_progress.append(upgrade.to_dict())

        return {
            "completed_upgrades": completed_upgrades,
            "still_in_progress": still_in_progress,
        }

    async def get_active_upgrades(
        self,
        club_id: int,
        career_id: int,
    ) -> List[Dict]:
        """
        Get all in-progress upgrades for a club.

        Args:
            club_id: ID of the club
            career_id: ID of the career

        Returns:
            List of upgrade dicts for all in-progress upgrades
        """
        stmt = select(InfrastructureUpgrade).where(
            and_(
                InfrastructureUpgrade.club_id == club_id,
                InfrastructureUpgrade.career_id == career_id,
                InfrastructureUpgrade.status == UpgradeStatus.IN_PROGRESS.value,
            )
        )
        result = await self.db.execute(stmt)
        upgrades = list(result.scalars().all())

        return [upgrade.to_dict() for upgrade in upgrades]

    async def complete_upgrade(self, upgrade_id: int) -> Optional[Dict]:
        """
        Complete an infrastructure upgrade and increase the club's level.

        Marks the upgrade as completed and updates the club's infrastructure
        level for the relevant category.

        Args:
            upgrade_id: ID of the upgrade to complete

        Returns:
            Dict with upgrade details if completed, None if upgrade not found
            or already completed
        """
        stmt = select(InfrastructureUpgrade).where(
            InfrastructureUpgrade.id == upgrade_id
        )
        result = await self.db.execute(stmt)
        upgrade = result.scalar_one_or_none()

        if upgrade is None:
            logger.warning(f"Upgrade with id {upgrade_id} not found")
            return None

        if upgrade.status != UpgradeStatus.IN_PROGRESS.value:
            logger.warning(
                f"Upgrade {upgrade_id} is not in progress "
                f"(status: {upgrade.status})"
            )
            return None

        # Get the club and update the infrastructure level
        club = await self._get_club(upgrade.club_id)
        if club is None:
            logger.error(
                f"Club {upgrade.club_id} not found when completing upgrade {upgrade_id}"
            )
            return None

        # Update the club's infrastructure level
        category = InfrastructureCategory(upgrade.category)
        definition = CATEGORY_DEFINITIONS[category]
        field_name = definition["model_field"]
        setattr(club, field_name, upgrade.to_level)

        # Mark upgrade as completed
        upgrade.status = UpgradeStatus.COMPLETED.value
        upgrade.completed_at = datetime.now(timezone.utc)

        await self.db.flush()

        logger.info(
            f"Infrastructure upgrade completed: club={upgrade.club_id}, "
            f"category={upgrade.category}, "
            f"new_level={upgrade.to_level} ({LEVEL_NAMES[upgrade.to_level]})"
        )

        return {
            "upgrade_id": upgrade.id,
            "club_id": upgrade.club_id,
            "category": upgrade.category,
            "category_name": definition["name"],
            "from_level": upgrade.from_level,
            "to_level": upgrade.to_level,
            "new_level_name": LEVEL_NAMES[upgrade.to_level],
            "message": (
                f"{definition['name']} upgrade complete! "
                f"Now at {LEVEL_NAMES[upgrade.to_level]} level."
            ),
        }

    # --- Private Helper Methods ---

    async def _get_active_upgrade_for_category(
        self,
        club_id: int,
        career_id: int,
        category: InfrastructureCategory,
    ) -> Optional[InfrastructureUpgrade]:
        """
        Check if there's an active upgrade for a specific category.

        Args:
            club_id: ID of the club
            career_id: ID of the career
            category: Infrastructure category to check

        Returns:
            InfrastructureUpgrade if one is in progress, None otherwise
        """
        stmt = select(InfrastructureUpgrade).where(
            and_(
                InfrastructureUpgrade.club_id == club_id,
                InfrastructureUpgrade.career_id == career_id,
                InfrastructureUpgrade.category == category.value,
                InfrastructureUpgrade.status == UpgradeStatus.IN_PROGRESS.value,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _calculate_completion_date(
        self, start_season: int, start_week: int, duration_weeks: int
    ) -> tuple:
        """
        Calculate the completion season and week given a start date and duration.

        Handles week overflow into the next season (52 weeks per season).

        Args:
            start_season: Starting season
            start_week: Starting week (1-52)
            duration_weeks: Duration in weeks

        Returns:
            Tuple of (completion_season, completion_week)
        """
        total_weeks = start_week + duration_weeks
        extra_seasons = (total_weeks - 1) // 52
        completion_week = ((total_weeks - 1) % 52) + 1
        completion_season = start_season + extra_seasons

        return completion_season, completion_week

    def _is_upgrade_due(
        self, upgrade: InfrastructureUpgrade, current_season: int, current_week: int
    ) -> bool:
        """
        Check if an upgrade has reached or passed its completion date.

        Args:
            upgrade: The upgrade to check
            current_season: Current in-game season
            current_week: Current in-game week

        Returns:
            True if the upgrade is due for completion
        """
        if current_season > upgrade.completion_season:
            return True
        if (
            current_season == upgrade.completion_season
            and current_week >= upgrade.completion_week
        ):
            return True
        return False

    # --- Training Facilities Bonus Integration (Task 12.4) ---

    async def get_training_facilities_bonus(self, club_id: int) -> float:
        """
        Get the training bonus multiplier for a club's current Training Facilities level.

        The training bonus multiplier is applied to all attribute development during
        weekly training simulation. Higher Training Facilities levels provide greater
        bonuses:
            - Level 1 (Basic): 1.0x (no bonus)
            - Level 2 (Standard): 1.1x (10% bonus)
            - Level 3 (Good): 1.25x (25% bonus)
            - Level 4 (Excellent): 1.4x (40% bonus)
            - Level 5 (World Class): 1.6x (60% bonus)

        Args:
            club_id: ID of the club

        Returns:
            The training_bonus_multiplier for the club's Training Facilities level.
            Defaults to 1.0 if the club is not found.

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.training_facilities_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.TRAINING_FACILITIES][level]
        return effects["training_bonus_multiplier"]

    # --- Youth Academy Quality Integration (Task 12.5) ---

    async def get_youth_academy_quality(self, club_id: int) -> Dict:
        """
        Get the youth academy quality effects for a club's current Youth Academy level.

        The Youth Academy level affects the quality of youth prospects generated.
        Higher levels produce more talented young players with higher potential ability
        and better starting attributes.

        Effects per level:
            - Level 1 (Basic): youth_quality_bonus=0, max_youth_pa=120, youth_intake_size=3
            - Level 2 (Standard): youth_quality_bonus=5, max_youth_pa=140, youth_intake_size=4
            - Level 3 (Good): youth_quality_bonus=10, max_youth_pa=160, youth_intake_size=5
            - Level 4 (Excellent): youth_quality_bonus=15, max_youth_pa=180, youth_intake_size=6
            - Level 5 (World Class): youth_quality_bonus=20, max_youth_pa=200, youth_intake_size=8

        This method is used when generating youth prospects to determine their
        max PA and quality.

        Implements Requirement 9.5: "WHEN a Youth Academy upgrade is completed,
        THE Youth_Academy SHALL generate higher-quality youth prospects."

        Args:
            club_id: ID of the club

        Returns:
            Dict containing:
                - youth_quality_bonus: Bonus added to youth prospect base attributes (0-20)
                - max_youth_pa: Maximum potential ability for generated youth prospects (120-200)
                - youth_intake_size: Number of youth prospects generated per intake (3-8)
                - level: Current Youth Academy level (1-5)
                - level_name: Human-readable level name

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.youth_academy_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.YOUTH_ACADEMY][level]

        return {
            "youth_quality_bonus": effects["youth_quality_bonus"],
            "max_youth_pa": effects["max_youth_pa"],
            "youth_intake_size": effects["youth_intake_size"],
            "level": level,
            "level_name": LEVEL_NAMES[level],
        }

    # --- Medical Centre Recovery Reduction (Task 12.6) ---

    async def get_medical_centre_recovery_reduction(self, club_id: int) -> int:
        """
        Get the recovery time reduction percentage for a club's Medical Centre level.

        Each level above Standard (level 2) reduces average player injury recovery
        time by 10%. The reduction percentage is defined in CATEGORY_EFFECTS.

        Reduction per level:
            - Level 1 (Basic): 0% reduction
            - Level 2 (Standard): 0% reduction (baseline)
            - Level 3 (Good): 10% reduction
            - Level 4 (Excellent): 20% reduction
            - Level 5 (World Class): 30% reduction

        Args:
            club_id: ID of the club

        Returns:
            The recovery_time_reduction_percent for the club's Medical Centre level.

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.medical_centre_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.MEDICAL_CENTRE][level]
        return effects["recovery_time_reduction_percent"]

    async def calculate_adjusted_recovery_weeks(
        self, base_weeks: int, club_id: int
    ) -> int:
        """
        Calculate adjusted injury recovery time based on Medical Centre level.

        Applies the Medical Centre's recovery time reduction percentage to the
        base recovery time. The result is always at least 1 week.

        Formula: adjusted_weeks = max(1, round(base_weeks * (1 - reduction_percent/100)))

        Args:
            base_weeks: Base recovery time in weeks (before Medical Centre bonus)
            club_id: ID of the club

        Returns:
            Adjusted recovery time in weeks (minimum 1 week)

        Raises:
            ValueError: If club_id is not found
        """
        reduction_percent = await self.get_medical_centre_recovery_reduction(club_id)
        adjusted = base_weeks * (1 - reduction_percent / 100)
        return max(1, round(adjusted))

    # --- Scouting Network Impact on Attribute Accuracy (Task 12.7) ---

    async def get_scouting_network_accuracy(self, club_id: int) -> Dict:
        """
        Get the scouting network accuracy effects for a club's current Scouting Network level.

        The Scouting Network level determines how accurate scouted player attributes are
        and how fast scouting reports are generated.

        Effects per level:
            - Level 1 (Basic): attribute_accuracy_percent=60, scouting_speed_bonus=0
            - Level 2 (Standard): attribute_accuracy_percent=70, scouting_speed_bonus=10
            - Level 3 (Good): attribute_accuracy_percent=80, scouting_speed_bonus=20
            - Level 4 (Excellent): attribute_accuracy_percent=90, scouting_speed_bonus=30
            - Level 5 (World Class): attribute_accuracy_percent=95, scouting_speed_bonus=40

        Args:
            club_id: ID of the club

        Returns:
            Dict containing:
                - attribute_accuracy_percent: How accurate revealed attributes are (60-95)
                - scouting_speed_bonus: Percentage bonus to scouting speed (0-40)
                - level: Current Scouting Network level (1-5)
                - level_name: Human-readable level name

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.scouting_network_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.SCOUTING_NETWORK][level]

        return {
            "attribute_accuracy_percent": effects["attribute_accuracy_percent"],
            "scouting_speed_bonus": effects["scouting_speed_bonus"],
            "level": level,
            "level_name": LEVEL_NAMES[level],
        }

    # --- Stadium Impact on Matchday Revenue (Task 12.8) ---

    async def get_stadium_revenue_multiplier(self, club_id: int) -> float:
        """
        Get the matchday revenue multiplier for a club's current Stadium level.

        The revenue multiplier is applied to matchday revenue calculations.
        Higher Stadium levels provide greater revenue multipliers:
            - Level 1 (Basic): 1.0x (no bonus)
            - Level 2 (Standard): 1.25x (25% bonus)
            - Level 3 (Good): 1.5x (50% bonus)
            - Level 4 (Excellent): 1.85x (85% bonus)
            - Level 5 (World Class): 2.25x (125% bonus)

        This method is used by FinanceService.calculate_matchday_revenue() to apply
        the stadium bonus to matchday income.

        Args:
            club_id: ID of the club

        Returns:
            The matchday_revenue_multiplier for the club's Stadium level.

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.stadium_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]
        return effects["matchday_revenue_multiplier"]

    async def get_stadium_capacity(self, club_id: int) -> int:
        """
        Get the maximum stadium capacity for a club's current Stadium level.

        The capacity determines the maximum number of fans that can attend
        a home match. Higher Stadium levels provide greater capacity:
            - Level 1 (Basic): 10,000
            - Level 2 (Standard): 25,000
            - Level 3 (Good): 40,000
            - Level 4 (Excellent): 60,000
            - Level 5 (World Class): 80,000

        This method is used by FinanceService.calculate_matchday_revenue() to
        determine the maximum attendance for revenue calculations.

        Args:
            club_id: ID of the club

        Returns:
            The max_capacity for the club's Stadium level.

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        level = club.stadium_level
        effects = CATEGORY_EFFECTS[InfrastructureCategory.STADIUM][level]
        return effects["max_capacity"]

    async def calculate_revealed_attribute_accuracy(
        self, true_value: int, club_id: int
    ) -> int:
        """
        Calculate the revealed attribute value with noise based on Scouting Network accuracy.

        Given a true attribute value, applies random noise based on the club's
        Scouting Network level. Higher accuracy means less noise (deviation).

        The maximum deviation is calculated as:
            max_deviation = max(1, (100 - attribute_accuracy_percent) // 10)

        This gives:
            - 60% accuracy: ±4 deviation
            - 70% accuracy: ±3 deviation
            - 80% accuracy: ±2 deviation
            - 90% accuracy: ±1 deviation
            - 95% accuracy: ±1 deviation

        The revealed value is clamped to the valid attribute range [1, 20].

        Args:
            true_value: The actual attribute value (1-20)
            club_id: ID of the club

        Returns:
            The revealed attribute value with accuracy-based noise applied,
            clamped to [1, 20].

        Raises:
            ValueError: If club_id is not found
        """
        accuracy_info = await self.get_scouting_network_accuracy(club_id)
        accuracy_percent = accuracy_info["attribute_accuracy_percent"]

        # Calculate maximum deviation based on accuracy
        max_deviation = max(1, (100 - accuracy_percent) // 10)

        # Apply random noise within the deviation range
        noise = random.randint(-max_deviation, max_deviation)
        revealed_value = true_value + noise

        # Clamp to valid attribute range [1, 20]
        revealed_value = max(1, min(20, revealed_value))

        return revealed_value

    # --- Club Overview Screen with Infrastructure Display (Task 12.10) ---

    async def get_club_overview(self, club_id: int, career_id: int) -> Dict:
        """
        Get a comprehensive club overview including infrastructure status.

        Generates a complete club overview screen combining:
        1. Club basic info (name, reputation, balance)
        2. All 5 infrastructure categories with current levels and effects
        3. Any active upgrades in progress
        4. Financial summary (balance, transfer budget, wage bill)
        5. Squad summary (total players, average age, average CA)
        6. Staff summary (total staff, key roles filled)

        This method is the primary data source for the club overview screen
        in the Telegram Web App.

        Args:
            club_id: ID of the club
            career_id: ID of the career

        Returns:
            Dict containing:
                - club_info: Basic club information
                - infrastructure: All 5 categories with levels and effects
                - active_upgrades: List of upgrades currently in progress
                - financial_summary: Balance, transfer budget, wage bill
                - squad_summary: Total players, average age, average CA
                - staff_summary: Total staff, roles filled

        Raises:
            ValueError: If club_id is not found
        """
        club = await self._get_club(club_id)
        if club is None:
            raise ValueError(f"Club with id {club_id} not found")

        # 1. Club basic info
        club_info = {
            "id": club.id,
            "name": club.name,
            "reputation": club.reputation,
            "league": club.league,
            "country": club.country,
            "balance": club.balance,
        }

        # 2. Infrastructure categories with levels and effects
        infrastructure = []
        for category in InfrastructureCategory:
            definition = CATEGORY_DEFINITIONS[category]
            field_name = definition["model_field"]
            current_level = getattr(club, field_name)
            effects = CATEGORY_EFFECTS[category][current_level]

            infrastructure.append({
                "category": category.value,
                "name": definition["name"],
                "current_level": current_level,
                "level_name": LEVEL_NAMES[current_level],
                "effects": effects,
                "can_upgrade": current_level < 5,
            })

        # 3. Active upgrades in progress
        active_upgrades = await self.get_active_upgrades(club_id, career_id)

        # 4. Financial summary
        financial_summary = {
            "balance": club.balance,
            "transfer_budget": club.transfer_budget,
            "wage_budget": club.wage_budget,
            "matchday_revenue": club.matchday_revenue,
            "is_in_deficit": club.balance < 0,
        }

        # Calculate actual weekly wage bill from squad players
        player_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(SquadPlayer.wage), 0).label("total_wages"),
            )
            .where(SquadPlayer.career_id == career_id)
        )
        player_wages_result = await self.db.execute(player_wages_stmt)
        player_wages_weekly = int(player_wages_result.scalar() or 0)

        staff_wages_stmt = (
            select(
                sql_func.coalesce(sql_func.sum(Staff.wage), 0).label("total_wages"),
            )
            .where(
                and_(
                    Staff.career_id == career_id,
                    Staff.club_id == club_id,
                )
            )
        )
        staff_wages_result = await self.db.execute(staff_wages_stmt)
        staff_wages_weekly = int(staff_wages_result.scalar() or 0)

        financial_summary["weekly_wage_bill"] = player_wages_weekly + staff_wages_weekly
        financial_summary["player_wages_weekly"] = player_wages_weekly
        financial_summary["staff_wages_weekly"] = staff_wages_weekly

        # 5. Squad summary (total players, average age, average CA)
        squad_stats_stmt = (
            select(
                sql_func.count(SquadPlayer.id).label("total_players"),
            )
            .where(SquadPlayer.career_id == career_id)
        )
        squad_stats_result = await self.db.execute(squad_stats_stmt)
        total_players = int(squad_stats_result.scalar() or 0)

        # Get average age and average CA by joining with Player table
        average_age = 0.0
        average_ca = 0.0
        if total_players > 0:
            avg_stmt = (
                select(
                    sql_func.avg(Player.age).label("avg_age"),
                    sql_func.avg(Player.ca).label("avg_ca"),
                )
                .join(SquadPlayer, SquadPlayer.player_id == Player.id)
                .where(SquadPlayer.career_id == career_id)
            )
            avg_result = await self.db.execute(avg_stmt)
            avg_row = avg_result.one()
            average_age = round(float(avg_row.avg_age or 0), 1)
            average_ca = round(float(avg_row.avg_ca or 0), 1)

        squad_summary = {
            "total_players": total_players,
            "average_age": average_age,
            "average_ca": average_ca,
        }

        # 6. Staff summary (total staff, key roles filled)
        staff_count_stmt = (
            select(sql_func.count(Staff.id).label("total_staff"))
            .where(
                and_(
                    Staff.career_id == career_id,
                    Staff.club_id == club_id,
                )
            )
        )
        staff_count_result = await self.db.execute(staff_count_stmt)
        total_staff = int(staff_count_result.scalar() or 0)

        # Get roles filled
        roles_stmt = (
            select(Staff.role)
            .where(
                and_(
                    Staff.career_id == career_id,
                    Staff.club_id == club_id,
                )
            )
            .distinct()
        )
        roles_result = await self.db.execute(roles_stmt)
        filled_roles = [row[0].value if hasattr(row[0], 'value') else str(row[0]) for row in roles_result.all()]

        staff_summary = {
            "total_staff": total_staff,
            "roles_filled": filled_roles,
            "total_roles_available": 8,
            "roles_vacant": 8 - len(filled_roles),
        }

        return {
            "club_info": club_info,
            "infrastructure": infrastructure,
            "active_upgrades": active_upgrades,
            "financial_summary": financial_summary,
            "squad_summary": squad_summary,
            "staff_summary": staff_summary,
        }
