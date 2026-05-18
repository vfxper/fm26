"""
Career Service - Career initialization and management

This module provides functionality for creating and managing football manager careers.
It handles career initialization, club selection, manager profile setup, and career state management.
"""

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError

from app.models.career import Career
from app.models.user import User
from app.models.club import Club

logger = logging.getLogger(__name__)


@dataclass
class HallOfFameEntry:
    """A single Hall of Fame achievement entry."""
    achievement_type: str  # e.g., "trophy", "record", "milestone"
    title: str  # e.g., "League Champion 2024"
    description: str
    season: int
    week: int
    value: Optional[int] = None  # e.g., points total, goals scored

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "achievement_type": self.achievement_type,
            "title": self.title,
            "description": self.description,
            "season": self.season,
            "week": self.week,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HallOfFameEntry":
        """Create a HallOfFameEntry from a dictionary."""
        return cls(
            achievement_type=data["achievement_type"],
            title=data["title"],
            description=data["description"],
            season=data["season"],
            week=data["week"],
            value=data.get("value"),
        )


@dataclass
class MatchResult:
    """Summary of a match processed during the week."""
    match_id: int
    opponent: str
    score_home: int
    score_away: int
    result: str  # 'win', 'draw', 'loss'


@dataclass
class TrainingUpdate:
    """Summary of weekly training progress."""
    players_trained: int
    focus_area: str
    improvement_points: int


@dataclass
class AgedPlayer:
    """A player who had a birthday this week."""
    player_id: int
    player_name: str
    new_age: int


@dataclass
class FinanceUpdate:
    """Weekly finance changes."""
    income: int
    expenditure: int
    balance_change: int
    new_balance: int


@dataclass
class ContractNotification:
    """Notification about an expiring contract."""
    player_id: int
    player_name: str
    weeks_remaining: int


@dataclass
class WeekEvent:
    """A random event that occurred during the week."""
    event_type: str  # 'injury', 'media', 'board_message', 'transfer_rumour'
    description: str
    impact: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SackingEvent:
    """Represents a sacking event that ends the career."""
    reason: str
    season: int
    week: int
    board_confidence_at_sacking: int
    career_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoardObjective:
    """A single board objective for the season."""
    objective_type: str  # e.g., "league_position", "cup_progress", "youth_development", "financial"
    description: str  # Human-readable description
    target_value: int  # e.g., position 6 for "Finish in top 6"
    current_value: Optional[int] = None  # Current progress
    is_met: bool = False  # Whether objective is achieved
    priority: str = "primary"  # "primary" or "secondary"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "objective_type": self.objective_type,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "is_met": self.is_met,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoardObjective":
        """Create a BoardObjective from a dictionary."""
        return cls(
            objective_type=data["objective_type"],
            description=data["description"],
            target_value=data["target_value"],
            current_value=data.get("current_value"),
            is_met=data.get("is_met", False),
            priority=data.get("priority", "primary"),
        )


@dataclass
class ManagerFatigueStatus:
    """Status of manager fatigue based on consecutive losses."""
    consecutive_losses: int
    is_fatigued: bool  # True when consecutive_losses >= 5
    morale_penalty: int  # Penalty to apply to all players (0 if not fatigued)
    description: str


@dataclass
class WeekSummary:
    """
    Summary of everything that happened when advancing one week.
    
    Contains results from all subsystems processed during the weekly advance.
    """
    season: int
    week: int
    previous_season: int
    previous_week: int
    matches: List[MatchResult] = field(default_factory=list)
    training: Optional[TrainingUpdate] = None
    aged_players: List[AgedPlayer] = field(default_factory=list)
    finances: Optional[FinanceUpdate] = None
    contract_notifications: List[ContractNotification] = field(default_factory=list)
    events: List[WeekEvent] = field(default_factory=list)
    board_confidence_change: int = 0
    new_board_confidence: int = 50
    season_changed: bool = False
    sacking: Optional[SackingEvent] = None
    manager_fatigue: Optional[ManagerFatigueStatus] = None
    medical_update: Optional[Dict[str, Any]] = None


class CareerServiceError(Exception):
    """Base exception for career service errors"""
    pass


class UserNotFoundError(CareerServiceError):
    """Raised when user is not found"""
    pass


class ClubNotFoundError(CareerServiceError):
    """Raised when club is not found"""
    pass


class CareerAlreadyExistsError(CareerServiceError):
    """Raised when user already has an active career"""
    pass


class InvalidManagerNameError(CareerServiceError):
    """Raised when manager name is invalid"""
    pass


class CareerService:
    """
    Service for managing football manager careers.
    
    This service handles:
    - Career initialization with club selection
    - Manager profile creation with attributes
    - Career state management (season, week, board confidence)
    - Career statistics tracking
    
    Example:
        >>> async with get_db_session() as session:
        ...     service = CareerService(session)
        ...     career = await service.initialize_career(
        ...         user_id=1,
        ...         manager_name="John Smith",
        ...         club_id=5
        ...     )
        ...     print(f"Career created: {career.id}")
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the career service.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
    
    async def initialize_career(
        self,
        user_id: int,
        manager_name: str,
        club_id: int,
        check_existing: bool = True
    ) -> Career:
        """
        Initialize a new career for a user.
        
        This method:
        1. Validates the user exists
        2. Validates the club exists
        3. Checks if user already has an active career (optional)
        4. Creates a new career with initial state:
           - Season 1, Week 1
           - Board confidence: 50
           - Manager reputation: 50
           - Manager attributes: 10 (default for all 9 attributes)
           - All statistics: 0
        
        Args:
            user_id: Database ID of the user (not Telegram user ID)
            manager_name: Name of the manager (1-255 characters)
            club_id: Database ID of the club to manage
            check_existing: If True, raise error if user has existing career
            
        Returns:
            Career: Newly created career object
            
        Raises:
            UserNotFoundError: If user doesn't exist
            ClubNotFoundError: If club doesn't exist
            CareerAlreadyExistsError: If user already has a career and check_existing=True
            InvalidManagerNameError: If manager name is invalid
            
        Example:
            >>> service = CareerService(session)
            >>> career = await service.initialize_career(
            ...     user_id=1,
            ...     manager_name="Alex Ferguson",
            ...     club_id=10
            ... )
            >>> print(f"Managing {career.club_id} as {career.manager_name}")
        """
        logger.info(
            f"Initializing career for user_id={user_id}, "
            f"manager_name='{manager_name}', club_id={club_id}"
        )
        
        # 1. Validate manager name
        if not manager_name or not manager_name.strip():
            raise InvalidManagerNameError("Manager name cannot be empty")
        
        manager_name = manager_name.strip()
        if len(manager_name) > 255:
            raise InvalidManagerNameError("Manager name cannot exceed 255 characters")
        
        # 2. Validate user exists
        user = await self._get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with id {user_id} not found")
        
        # 3. Validate club exists
        club = await self._get_club_by_id(club_id)
        if not club:
            raise ClubNotFoundError(f"Club with id {club_id} not found")
        
        # 4. Check for existing career
        if check_existing:
            existing_career = await self._get_user_career(user_id)
            if existing_career:
                raise CareerAlreadyExistsError(
                    f"User {user_id} already has an active career (id={existing_career.id})"
                )
        
        # 5. Create new career with initial state
        career = Career(
            user_id=user_id,
            club_id=club_id,
            manager_name=manager_name,
            # Season/Week Progression (start at season 1, week 1)
            current_season=1,
            current_week=1,
            # Board System (start with neutral confidence)
            board_confidence=50,
            board_objectives=None,  # Will be set by board objectives system
            # Manager Profile (start with average reputation)
            manager_reputation=50,
            # Manager Attributes (start with average attributes: 10/20)
            tactical_knowledge=10,
            man_management=10,
            motivating=10,
            attacking=10,
            defending=10,
            technical=10,
            mental=10,
            youth_development=10,
            board_relations=10,
            # Career Statistics (all start at 0)
            seasons_managed=0,
            trophies_won=0,
            matches_won=0,
            matches_drawn=0,
            matches_lost=0,
            total_transfer_spend=0
        )
        
        try:
            self.session.add(career)
            await self.session.flush()  # Flush to get the ID
            
            logger.info(
                f"Career created successfully: id={career.id}, "
                f"user_id={user_id}, club_id={club_id}, "
                f"manager_name='{manager_name}'"
            )
            
            return career
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Database integrity error creating career: {str(e)}")
            raise CareerServiceError(f"Failed to create career: {str(e)}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Unexpected error creating career: {str(e)}")
            raise CareerServiceError(f"Failed to create career: {str(e)}")
    
    async def get_career_by_id(self, career_id: int) -> Optional[Career]:
        """
        Get a career by its ID.
        
        Args:
            career_id: Database ID of the career
            
        Returns:
            Career object if found, None otherwise
            
        Example:
            >>> career = await service.get_career_by_id(1)
            >>> if career:
            ...     print(f"Career: {career.manager_name} at {career.club_id}")
        """
        try:
            result = await self.session.execute(
                select(Career).where(Career.id == career_id)
            )
            career = result.scalar_one_or_none()
            
            if career:
                logger.debug(f"Found career: id={career_id}")
            else:
                logger.debug(f"Career not found: id={career_id}")
            
            return career
            
        except Exception as e:
            logger.error(f"Error fetching career {career_id}: {str(e)}")
            raise CareerServiceError(f"Failed to fetch career: {str(e)}")
    
    async def get_user_career(self, user_id: int) -> Optional[Career]:
        """
        Get the active career for a user.
        
        Note: Currently assumes one career per user. In future versions,
        this could be extended to support multiple careers.
        
        Args:
            user_id: Database ID of the user
            
        Returns:
            Career object if found, None otherwise
            
        Example:
            >>> career = await service.get_user_career(1)
            >>> if career:
            ...     print(f"User's career: Season {career.current_season}, Week {career.current_week}")
        """
        return await self._get_user_career(user_id)
    
    async def get_career_summary(self, career_id: int) -> Dict[str, Any]:
        """
        Get a summary of career information.
        
        Args:
            career_id: Database ID of the career
            
        Returns:
            Dictionary with career summary information
            
        Raises:
            CareerServiceError: If career not found
            
        Example:
            >>> summary = await service.get_career_summary(1)
            >>> print(f"Manager: {summary['manager_name']}")
            >>> print(f"Club: {summary['club_name']}")
            >>> print(f"Season: {summary['current_season']}, Week: {summary['current_week']}")
        """
        career = await self.get_career_by_id(career_id)
        if not career:
            raise CareerServiceError(f"Career {career_id} not found")
        
        # Get club information
        club = await self._get_club_by_id(career.club_id)
        
        # Get user information
        user = await self._get_user_by_id(career.user_id)
        
        return {
            'career_id': career.id,
            'manager_name': career.manager_name,
            'club_id': career.club_id,
            'club_name': club.name if club else 'Unknown',
            'club_reputation': club.reputation if club else 0,
            'user_id': career.user_id,
            'telegram_user_id': user.telegram_user_id if user else None,
            'current_season': career.current_season,
            'current_week': career.current_week,
            'board_confidence': career.board_confidence,
            'manager_reputation': career.manager_reputation,
            'manager_attributes': {
                'tactical_knowledge': career.tactical_knowledge,
                'man_management': career.man_management,
                'motivating': career.motivating,
                'attacking': career.attacking,
                'defending': career.defending,
                'technical': career.technical,
                'mental': career.mental,
                'youth_development': career.youth_development,
                'board_relations': career.board_relations,
                'average': career.get_average_manager_attribute()
            },
            'statistics': {
                'seasons_managed': career.seasons_managed,
                'trophies_won': career.trophies_won,
                'matches_won': career.matches_won,
                'matches_drawn': career.matches_drawn,
                'matches_lost': career.matches_lost,
                'total_matches': career.get_total_matches(),
                'win_percentage': career.get_win_percentage(),
                'total_transfer_spend': career.total_transfer_spend
            },
            'board_status': {
                'is_confident': career.is_board_confident(),
                'is_under_pressure': career.is_under_pressure()
            },
            'created_at': career.created_at.isoformat() if career.created_at else None,
            'updated_at': career.updated_at.isoformat() if career.updated_at else None,
            'save_timestamp': career.save_timestamp.isoformat() if career.save_timestamp else None
        }
    
    async def advance_week(self, career_id: int) -> WeekSummary:
        """
        Progress career by 1 week, processing all weekly updates.
        
        This method orchestrates all subsystems that need to run each week:
        1. Process scheduled matches
        2. Update player training
        3. Age players on birthdays
        4. Update finances
        5. Check contract expirations
        6. Generate events (injuries, media, board messages)
        7. Update board confidence
        8. Update save timestamp
        
        Args:
            career_id: Database ID of the career to advance
            
        Returns:
            WeekSummary: Summary of all events and changes during the week
            
        Raises:
            CareerServiceError: If career not found or update fails
            
        Example:
            >>> service = CareerService(session)
            >>> summary = await service.advance_week(career_id=1)
            >>> print(f"Advanced to Season {summary.season}, Week {summary.week}")
            >>> print(f"Matches played: {len(summary.matches)}")
        """
        logger.info(f"Advancing week for career_id={career_id}")
        
        # 1. Get the career
        career = await self.get_career_by_id(career_id)
        if not career:
            raise CareerServiceError(f"Career {career_id} not found")
        
        # Store previous state
        previous_season = career.current_season
        previous_week = career.current_week
        
        # 2. Advance the week counter
        career.advance_week()
        season_changed = career.current_season != previous_season
        
        # 3. Process all subsystems
        matches = await self._process_matches(career)
        training = await self._process_training(career)
        aged_players = await self._process_player_aging(career)
        finances = await self._process_finances(career)
        contract_notifications = await self._check_contract_expirations(career)
        events = await self._generate_weekly_events(career)
        medical_update = await self._process_medical_recovery(career)
        board_confidence_change = await self._update_board_confidence(career, matches)
        await self._update_manager_reputation(career, matches)

        # 3.5 Check sacking conditions
        sacking_event = None
        # Track consecutive low confidence weeks via a simple heuristic:
        # If confidence is critically low after this week's update, count it
        consecutive_low_weeks = self._estimate_consecutive_low_confidence_weeks(career)
        sacking_check = self.check_sacking_conditions(
            career, consecutive_low_confidence_weeks=consecutive_low_weeks
        )
        if sacking_check["should_sack"]:
            sacking_event = self.trigger_sacking_event(
                career, sacking_check["reason"]
            )

        # 3.6 Check manager fatigue
        recent_results = self.get_recent_results(career)
        manager_fatigue = self.check_manager_fatigue(career, recent_results)
        
        # 4. Update save timestamp
        career.save_timestamp = datetime.now(timezone.utc)
        
        # 5. Flush changes
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(f"Error saving week advance for career {career_id}: {str(e)}")
            raise CareerServiceError(f"Failed to advance week: {str(e)}")
        
        # 6. Build and return summary
        summary = WeekSummary(
            season=career.current_season,
            week=career.current_week,
            previous_season=previous_season,
            previous_week=previous_week,
            matches=matches,
            training=training,
            aged_players=aged_players,
            finances=finances,
            contract_notifications=contract_notifications,
            events=events,
            board_confidence_change=board_confidence_change,
            new_board_confidence=career.board_confidence,
            season_changed=season_changed,
            sacking=sacking_event,
            manager_fatigue=manager_fatigue,
            medical_update=medical_update,
        )
        
        logger.info(
            f"Week advanced for career {career_id}: "
            f"S{previous_season}W{previous_week} -> S{career.current_season}W{career.current_week}"
        )
        
        return summary
    
    # --- Weekly subsystem stubs ---

    def _estimate_consecutive_low_confidence_weeks(self, career: Career) -> int:
        """
        Estimate consecutive weeks with critically low board confidence.

        Uses a heuristic based on current confidence level:
        - If confidence < CRITICAL_CONFIDENCE_THRESHOLD, estimate weeks based on
          how far below the threshold the confidence is.
        - This is a simplified approach; a full implementation would track
          weekly confidence history in a separate table.

        Args:
            career: The career to check

        Returns:
            int: Estimated consecutive weeks with critically low confidence
        """
        if career.board_confidence >= self.CRITICAL_CONFIDENCE_THRESHOLD:
            return 0

        # The lower the confidence, the more weeks we estimate it's been low.
        # At confidence 1, estimate ~8 weeks; at 19, estimate ~1 week.
        # This provides a reasonable heuristic without needing history tracking.
        deficit = self.CRITICAL_CONFIDENCE_THRESHOLD - career.board_confidence
        # Scale: each 5 points below threshold ≈ 1 additional week
        estimated_weeks = max(1, deficit // 4)
        return estimated_weeks

    async def _process_matches(self, career: Career) -> List[MatchResult]:
        """
        Process any matches scheduled for this week.
        
        Stub: Returns empty list until fixture/match scheduling is implemented.
        """
        # TODO: Query fixtures table for matches this week
        # TODO: Simulate matches using MatchSimulator
        # TODO: Update career match statistics
        return []
    
    async def _process_training(self, career: Career) -> TrainingUpdate:
        """
        Simulate weekly training for all squad players.
        
        Stub: Returns a default training summary until training module is implemented.
        """
        # TODO: Get training schedule for career
        # TODO: Apply attribute changes based on training focus
        # TODO: Factor in coach bonuses and facilities level
        return TrainingUpdate(
            players_trained=0,
            focus_area="General",
            improvement_points=0,
        )
    
    async def _process_player_aging(self, career: Career) -> List[AgedPlayer]:
        """
        Check for player birthdays this week and age them.
        
        Stub: Returns empty list until player birthday tracking is implemented.
        """
        # TODO: Query squad players whose birthday falls in this week
        # TODO: Increment age, apply age-related attribute changes
        return []
    
    async def _process_finances(self, career: Career) -> FinanceUpdate:
        """
        Process weekly financial updates (wages, revenue, etc.).
        
        Stub: Returns zero-change finance update until finance module is implemented.
        """
        # TODO: Deduct weekly wages
        # TODO: Add matchday revenue if match was played
        # TODO: Process sponsorship income
        # TODO: Update club balance
        return FinanceUpdate(
            income=0,
            expenditure=0,
            balance_change=0,
            new_balance=0,
        )
    
    async def _check_contract_expirations(self, career: Career) -> List[ContractNotification]:
        """
        Check for contracts expiring soon and generate notifications.
        
        Stub: Returns empty list until contract system is implemented.
        """
        # TODO: Query squad players with contracts expiring within 26 weeks
        # TODO: Generate notifications for contracts < 6 months remaining
        return []
    
    async def _process_medical_recovery(
        self, career: Career
    ) -> Optional[Dict[str, Any]]:
        """
        Process weekly injury recovery for the career via MedicalService.

        Each in-game week, ACTIVE injuries advance toward RECOVERING and
        RECOVERING injuries advance toward RECOVERED. Implements
        Requirement 11.3 and 11.7.

        Returns:
            Optional[Dict[str, Any]]: Recovery summary dict from
                MedicalService.process_weekly_recovery, or None on failure.
        """
        try:
            # Local import to avoid circular import at module load time
            from app.services.medical_service import MedicalService

            service = MedicalService(self.session)
            return await service.process_weekly_recovery(
                career_id=career.id,
                season=career.current_season,
                week=career.current_week,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"Medical recovery processing failed for career {career.id}: {e}"
            )
            return None

    async def _generate_weekly_events(self, career: Career) -> List[WeekEvent]:
        """
        Generate random weekly events (injuries, media, board messages).
        
        Stub: Generates occasional random events with low probability.
        """
        events: List[WeekEvent] = []
        
        # Small chance of a training ground injury
        if random.random() < 0.05:
            events.append(WeekEvent(
                event_type="injury",
                description="A player picked up a minor knock in training.",
                impact={"severity": "minor", "weeks_out": 1},
            ))
        
        # Small chance of a media event
        if random.random() < 0.08:
            events.append(WeekEvent(
                event_type="media",
                description="Local press are asking about the team's form.",
                impact={"reputation_effect": 0},
            ))
        
        # Small chance of a board message
        if random.random() < 0.03:
            events.append(WeekEvent(
                event_type="board_message",
                description="The board are pleased with the current direction.",
                impact={"confidence_effect": 1},
            ))
        
        return events
    
    async def _update_board_confidence(
        self, career: Career, matches: List[MatchResult]
    ) -> int:
        """
        Update board confidence based on weekly results.
        
        Applies a small random drift when no matches are played,
        and result-based changes when matches occur.
        
        Returns:
            int: The change in board confidence this week
        """
        change = 0
        
        # Apply match result effects
        for match in matches:
            if match.result == "win":
                change += 2
            elif match.result == "draw":
                change += 0
            elif match.result == "loss":
                change -= 2
        
        # Small random drift when no matches (simulates general sentiment)
        if not matches:
            change = random.choice([-1, 0, 0, 0, 1])
        
        # Apply change with bounds (1-100)
        new_confidence = max(1, min(100, career.board_confidence + change))
        actual_change = new_confidence - career.board_confidence
        career.board_confidence = new_confidence
        
        return actual_change
    
    # --- Sacking System ---

    # Number of consecutive weeks with critically low confidence to trigger sacking
    CRITICAL_CONFIDENCE_THRESHOLD = 20
    CRITICAL_CONFIDENCE_WEEKS_REQUIRED = 4
    CONSECUTIVE_FAILED_SEASONS_REQUIRED = 2

    def get_consecutive_failed_seasons(self, career: Career) -> int:
        """
        Determine how many consecutive seasons the manager has failed board objectives.

        Checks the board_objectives JSON history. Each season's objectives are stored
        as a JSON array. If all primary objectives are failed for consecutive seasons,
        the count increases.

        Args:
            career: The career to check

        Returns:
            int: Number of consecutive failed seasons (from most recent backwards)
        """
        if not career.board_objectives:
            return 0

        try:
            objectives_data = json.loads(career.board_objectives)
        except (json.JSONDecodeError, TypeError):
            return 0

        # Check if objectives_data is a list of season records (list of lists)
        # or a single season's objectives (list of dicts)
        if not objectives_data:
            return 0

        # If it's a list of season records (each element is a list of objectives)
        if isinstance(objectives_data[0], list):
            consecutive_failures = 0
            # Check from most recent season backwards
            for season_objectives in reversed(objectives_data):
                primary_objectives = [
                    obj for obj in season_objectives
                    if obj.get("priority") == "primary"
                ]
                if not primary_objectives:
                    break
                # Season is failed if any primary objective is not met
                all_primary_failed = all(
                    not obj.get("is_met", False) for obj in primary_objectives
                )
                if all_primary_failed:
                    consecutive_failures += 1
                else:
                    break
            return consecutive_failures
        else:
            # Single season format - check if current objectives are all failed
            primary_objectives = [
                obj for obj in objectives_data
                if obj.get("priority") == "primary"
            ]
            if not primary_objectives:
                return 0
            all_primary_failed = all(
                not obj.get("is_met", False) for obj in primary_objectives
            )
            return 1 if all_primary_failed else 0

    def check_sacking_conditions(
        self,
        career: Career,
        consecutive_low_confidence_weeks: int = 0,
    ) -> Dict[str, Any]:
        """
        Check if sacking conditions are met.

        Sacking can be triggered by:
        1. Board confidence < 20 for 4+ consecutive weeks
        2. Board objectives failed for 2 consecutive seasons

        Args:
            career: The career to check
            consecutive_low_confidence_weeks: Number of consecutive weeks with
                board_confidence < CRITICAL_CONFIDENCE_THRESHOLD

        Returns:
            Dict with keys:
                - should_sack (bool): Whether the manager should be sacked
                - reason (str): Reason for sacking (empty if not sacking)
                - severity (str): "critical" or "none"
        """
        # Check condition 1: Critically low confidence for extended period
        if (
            career.board_confidence < self.CRITICAL_CONFIDENCE_THRESHOLD
            and consecutive_low_confidence_weeks >= self.CRITICAL_CONFIDENCE_WEEKS_REQUIRED
        ):
            return {
                "should_sack": True,
                "reason": (
                    f"Board confidence critically low ({career.board_confidence}%) "
                    f"for {consecutive_low_confidence_weeks} consecutive weeks"
                ),
                "severity": "critical",
            }

        # Check condition 2: Failed objectives for 2 consecutive seasons
        consecutive_failures = self.get_consecutive_failed_seasons(career)
        if consecutive_failures >= self.CONSECUTIVE_FAILED_SEASONS_REQUIRED:
            return {
                "should_sack": True,
                "reason": (
                    f"Failed board objectives for {consecutive_failures} "
                    f"consecutive seasons"
                ),
                "severity": "critical",
            }

        return {
            "should_sack": False,
            "reason": "",
            "severity": "none",
        }

    def trigger_sacking_event(self, career: Career, reason: str) -> SackingEvent:
        """
        Trigger a sacking event, ending the career.

        Marks the career as inactive by setting board_objectives to a JSON
        object containing {"career_ended": true, "sacking_reason": reason}.
        This convention signals that the career is no longer active.

        Args:
            career: The career to end
            reason: The reason for sacking

        Returns:
            SackingEvent: Details of the sacking
        """
        # Build career summary
        career_summary = {
            "seasons_managed": career.seasons_managed,
            "trophies_won": career.trophies_won,
            "matches_won": career.matches_won,
            "matches_drawn": career.matches_drawn,
            "matches_lost": career.matches_lost,
            "total_transfer_spend": career.total_transfer_spend,
            "final_reputation": career.manager_reputation,
        }

        sacking_event = SackingEvent(
            reason=reason,
            season=career.current_season,
            week=career.current_week,
            board_confidence_at_sacking=career.board_confidence,
            career_summary=career_summary,
        )

        # Mark career as ended using board_objectives JSON convention
        ended_data = json.dumps({
            "career_ended": True,
            "sacking_reason": reason,
            "sacking_season": career.current_season,
            "sacking_week": career.current_week,
        })
        career.board_objectives = ended_data

        logger.info(
            f"Sacking triggered for career {career.id}: reason='{reason}', "
            f"season={career.current_season}, week={career.current_week}, "
            f"board_confidence={career.board_confidence}"
        )

        return sacking_event

    def is_career_active(self, career: Career) -> bool:
        """
        Check if a career is still active (not sacked).

        Args:
            career: The career to check

        Returns:
            bool: True if career is active, False if ended by sacking
        """
        if not career.board_objectives:
            return True
        try:
            data = json.loads(career.board_objectives)
            if isinstance(data, dict) and data.get("career_ended"):
                return False
        except (json.JSONDecodeError, TypeError):
            pass
        return True

    # --- Manager Reputation System ---

    @staticmethod
    def calculate_reputation_change(event_type: str, **kwargs) -> int:
        """
        Calculate the reputation change for a given event.

        Args:
            event_type: Type of event that occurred. Valid values:
                - "match_win" -> +1
                - "match_draw" -> 0
                - "match_loss" -> -1
                - "trophy_won" -> +5 to +10 (based on trophy_importance kwarg: 1-3)
                - "objectives_met" -> +3
                - "objectives_failed" -> -3
                - "season_end_overperform" -> +5
                - "season_end_underperform" -> -5
                - "promoted" -> +8
                - "relegated" -> -10
            **kwargs: Additional parameters (e.g., trophy_importance for trophy_won)

        Returns:
            int: The reputation change value (can be negative)
        """
        event_map = {
            "match_win": 1,
            "match_draw": 0,
            "match_loss": -1,
            "objectives_met": 3,
            "objectives_failed": -3,
            "season_end_overperform": 5,
            "season_end_underperform": -5,
            "promoted": 8,
            "relegated": -10,
        }

        if event_type == "trophy_won":
            # trophy_importance: 1 = minor (+5), 2 = major (+7), 3 = top (+10)
            importance = kwargs.get("trophy_importance", 1)
            if importance >= 3:
                return 10
            elif importance >= 2:
                return 7
            else:
                return 5

        return event_map.get(event_type, 0)

    async def update_manager_reputation(self, career: Career, event_type: str, **kwargs) -> int:
        """
        Update manager reputation based on an event.

        Adjusts the career's manager_reputation field, clamping to 1-100.

        Args:
            career: The career to update
            event_type: Type of event (see calculate_reputation_change)
            **kwargs: Additional parameters passed to calculate_reputation_change

        Returns:
            int: The actual change applied (after clamping)
        """
        change = self.calculate_reputation_change(event_type, **kwargs)
        if change == 0:
            return 0

        new_reputation = max(1, min(100, career.manager_reputation + change))
        actual_change = new_reputation - career.manager_reputation
        career.manager_reputation = new_reputation

        return actual_change

    async def _update_manager_reputation(self, career: Career, matches: List[MatchResult]) -> int:
        """
        Update manager reputation based on weekly match results.

        Called from advance_week to apply reputation changes for matches played.

        Args:
            career: The career to update
            matches: List of match results from this week

        Returns:
            int: Total reputation change this week
        """
        total_change = 0

        for match in matches:
            if match.result == "win":
                total_change += await self.update_manager_reputation(career, "match_win")
            elif match.result == "draw":
                total_change += await self.update_manager_reputation(career, "match_draw")
            elif match.result == "loss":
                total_change += await self.update_manager_reputation(career, "match_loss")

        return total_change

    # --- Board Objectives System ---

    def generate_board_objectives(
        self,
        club_reputation: int,
        current_league_position: int,
        season_number: int,
    ) -> List[BoardObjective]:
        """
        Generate board objectives appropriate for the club's level.

        Top clubs (rep 70+): Win the league, Win domestic cup, Reach CL semi-final
        Mid clubs (rep 40-69): Finish top half, Reach cup quarter-final, Develop youth
        Low clubs (rep <40): Avoid relegation, Reach cup 3rd round, Balance budget

        Args:
            club_reputation: Club reputation (1-100)
            current_league_position: Current league position (1-20)
            season_number: Current season number

        Returns:
            List of 2-4 BoardObjective instances
        """
        objectives: List[BoardObjective] = []

        if club_reputation >= 70:
            # Top clubs get hard objectives
            objectives.append(BoardObjective(
                objective_type="league_position",
                description="Win the league",
                target_value=1,
                priority="primary",
            ))
            objectives.append(BoardObjective(
                objective_type="cup_progress",
                description="Win the domestic cup",
                target_value=1,  # 1 = win the final
                priority="primary",
            ))
            objectives.append(BoardObjective(
                objective_type="cup_progress",
                description="Reach Champions League semi-final",
                target_value=4,  # round 4 = semi-final
                priority="secondary",
            ))
        elif club_reputation >= 40:
            # Mid clubs get moderate objectives
            objectives.append(BoardObjective(
                objective_type="league_position",
                description="Finish in the top half",
                target_value=10,
                priority="primary",
            ))
            objectives.append(BoardObjective(
                objective_type="cup_progress",
                description="Reach the cup quarter-final",
                target_value=3,  # round 3 = quarter-final
                priority="secondary",
            ))
            objectives.append(BoardObjective(
                objective_type="youth_development",
                description="Develop a youth player into the first team",
                target_value=1,
                priority="secondary",
            ))
        else:
            # Low clubs get survival objectives
            objectives.append(BoardObjective(
                objective_type="league_position",
                description="Avoid relegation",
                target_value=17,  # finish 17th or better (out of 20)
                priority="primary",
            ))
            objectives.append(BoardObjective(
                objective_type="cup_progress",
                description="Reach the cup 3rd round",
                target_value=3,
                priority="secondary",
            ))
            objectives.append(BoardObjective(
                objective_type="financial",
                description="Balance the budget",
                target_value=0,  # 0 = non-negative balance
                priority="secondary",
            ))

        # Add an extra objective for later seasons to increase challenge
        if season_number >= 3 and club_reputation >= 40:
            objectives.append(BoardObjective(
                objective_type="financial",
                description="Reduce net transfer spend",
                target_value=0,
                priority="secondary",
            ))

        return objectives

    def evaluate_objectives(
        self,
        career: Career,
        current_league_position: int,
        cup_round_reached: int = 0,
        youth_players_promoted: int = 0,
        club_balance: int = 0,
    ) -> List[BoardObjective]:
        """
        Evaluate board objectives against current progress.

        Args:
            career: The career to evaluate objectives for
            current_league_position: Current league position (1-20)
            cup_round_reached: Furthest cup round reached this season
            youth_players_promoted: Number of youth players promoted
            club_balance: Current club balance

        Returns:
            List of BoardObjective with updated current_value and is_met fields
        """
        if not career.board_objectives:
            return []

        objectives_data = json.loads(career.board_objectives)
        objectives = [BoardObjective.from_dict(obj) for obj in objectives_data]

        for obj in objectives:
            if obj.objective_type == "league_position":
                obj.current_value = current_league_position
                # For league position, lower is better (1st is best)
                obj.is_met = current_league_position <= obj.target_value
            elif obj.objective_type == "cup_progress":
                obj.current_value = cup_round_reached
                # For cup progress, higher round is better
                obj.is_met = cup_round_reached >= obj.target_value
            elif obj.objective_type == "youth_development":
                obj.current_value = youth_players_promoted
                obj.is_met = youth_players_promoted >= obj.target_value
            elif obj.objective_type == "financial":
                obj.current_value = club_balance
                obj.is_met = club_balance >= obj.target_value

        return objectives

    def set_season_objectives(
        self,
        career: Career,
        club_reputation: int,
        current_league_position: int,
    ) -> List[BoardObjective]:
        """
        Generate and store objectives for the new season.

        Args:
            career: The career to set objectives for
            club_reputation: Club reputation (1-100)
            current_league_position: Current league position (1-20)

        Returns:
            List of BoardObjective set for the season
        """
        objectives = self.generate_board_objectives(
            club_reputation=club_reputation,
            current_league_position=current_league_position,
            season_number=career.current_season,
        )

        # Store as JSON in career.board_objectives
        objectives_json = json.dumps([obj.to_dict() for obj in objectives])
        career.board_objectives = objectives_json

        return objectives

    # --- Manager Attribute Progression System ---

    # Valid manager attributes
    VALID_MANAGER_ATTRIBUTES = [
        "tactical_knowledge",
        "man_management",
        "motivating",
        "attacking",
        "defending",
        "technical",
        "mental",
        "youth_development",
        "board_relations",
    ]

    # Achievement-to-attribute mapping
    ACHIEVEMENT_PROGRESSION_MAP: Dict[str, Dict[str, int]] = {
        "league_win": {"tactical_knowledge": 1, "motivating": 1},
        "cup_win": {"man_management": 1, "mental": 1},
        "continental_win": {"tactical_knowledge": 1, "attacking": 1, "defending": 1},
        "season_top_scorer": {"attacking": 1},
        "season_best_defense": {"defending": 1},
        "youth_player_promoted": {"youth_development": 1},
        "board_objectives_met": {"board_relations": 1},
        "unbeaten_run_10": {"motivating": 1, "mental": 1},
        "transfer_profit": {"technical": 1},
    }

    def progress_manager_attribute(
        self, career: Career, attribute_name: str, change: int
    ) -> int:
        """
        Apply a change to a single manager attribute, clamping to 1-20.

        Args:
            career: The career to update
            attribute_name: One of the 9 valid manager attributes
            change: The amount to change (positive or negative)

        Returns:
            int: The actual change applied (after clamping)

        Raises:
            ValueError: If attribute_name is not a valid manager attribute
        """
        if attribute_name not in self.VALID_MANAGER_ATTRIBUTES:
            raise ValueError(
                f"Invalid attribute name '{attribute_name}'. "
                f"Must be one of: {', '.join(self.VALID_MANAGER_ATTRIBUTES)}"
            )

        current_value = getattr(career, attribute_name)
        new_value = max(1, min(20, current_value + change))
        actual_change = new_value - current_value
        setattr(career, attribute_name, new_value)

        logger.debug(
            f"Manager attribute '{attribute_name}' changed: "
            f"{current_value} -> {new_value} (change={actual_change})"
        )

        return actual_change

    def process_achievement_progression(
        self, career: Career, achievement: str
    ) -> Dict[str, int]:
        """
        Process an achievement and apply the corresponding attribute increases.

        Maps achievements to attribute changes using ACHIEVEMENT_PROGRESSION_MAP.

        Args:
            career: The career to update
            achievement: The achievement type (e.g., "league_win", "cup_win")

        Returns:
            Dict[str, int]: Dictionary of {attribute_name: actual_change_applied}
            Empty dict if achievement is not recognized.
        """
        attribute_changes = self.ACHIEVEMENT_PROGRESSION_MAP.get(achievement)
        if not attribute_changes:
            logger.warning(f"Unknown achievement type: '{achievement}'")
            return {}

        applied_changes: Dict[str, int] = {}
        for attr_name, change_amount in attribute_changes.items():
            actual_change = self.progress_manager_attribute(
                career, attr_name, change_amount
            )
            if actual_change != 0:
                applied_changes[attr_name] = actual_change

        logger.info(
            f"Achievement '{achievement}' processed for career {career.id}: "
            f"changes={applied_changes}"
        )

        return applied_changes

    def process_season_end_progression(
        self, career: Career, achievements: List[str]
    ) -> Dict[str, int]:
        """
        Process end-of-season attribute progression.

        Evaluates the season's achievements and applies attribute increases.
        Also applies a small random progression chance (+1 to a random attribute,
        20% chance per season).

        Args:
            career: The career to update
            achievements: List of achievement strings earned this season

        Returns:
            Dict[str, int]: Summary of all attribute changes applied
                {attribute_name: total_change}
        """
        all_changes: Dict[str, int] = {}

        # Process each achievement
        for achievement in achievements:
            changes = self.process_achievement_progression(career, achievement)
            for attr_name, change in changes.items():
                all_changes[attr_name] = all_changes.get(attr_name, 0) + change

        # Random progression chance (20% per season)
        if random.random() < 0.20:
            random_attr = random.choice(self.VALID_MANAGER_ATTRIBUTES)
            actual_change = self.progress_manager_attribute(career, random_attr, 1)
            if actual_change != 0:
                all_changes[random_attr] = all_changes.get(random_attr, 0) + actual_change
                logger.info(
                    f"Random season progression: '{random_attr}' +1 for career {career.id}"
                )

        logger.info(
            f"Season-end progression for career {career.id}: "
            f"achievements={achievements}, total_changes={all_changes}"
        )

        return all_changes

    # --- Hall of Fame System ---

    # Milestone definitions: (stat_check_fn, threshold, achievement_type, title_template, description_template)
    MILESTONES = [
        {
            "stat": "total_matches",
            "threshold": 100,
            "achievement_type": "milestone",
            "title": "Century of Matches",
            "description": "Managed 100 matches",
        },
        {
            "stat": "matches_won",
            "threshold": 50,
            "achievement_type": "milestone",
            "title": "50 Victories",
            "description": "Won 50 matches",
        },
        {
            "stat": "trophies_won",
            "threshold": 1,
            "achievement_type": "trophy",
            "title": "First Trophy",
            "description": "Won the first trophy of the career",
        },
        {
            "stat": "trophies_won",
            "threshold": 5,
            "achievement_type": "trophy",
            "title": "Trophy Collector",
            "description": "Won 5 trophies",
        },
        {
            "stat": "seasons_managed",
            "threshold": 10,
            "achievement_type": "milestone",
            "title": "Decade of Management",
            "description": "Managed for 10 seasons",
        },
        {
            "stat": "win_percentage",
            "threshold": 60,
            "achievement_type": "record",
            "title": "Elite Win Rate",
            "description": "Achieved a win percentage above 60%",
        },
    ]

    def get_hall_of_fame(self, career: Career) -> List["HallOfFameEntry"]:
        """
        Compile the Hall of Fame for a career.

        Combines stored entries with auto-detected milestones based on
        current career statistics.

        Args:
            career: The career to get the Hall of Fame for

        Returns:
            List[HallOfFameEntry]: All Hall of Fame entries (stored + auto-detected)
        """
        entries: List[HallOfFameEntry] = []

        # Load stored entries
        entries.extend(self._load_hall_of_fame_entries(career))

        # Auto-detect milestones from current stats
        detected = self._detect_milestones(career)

        # Avoid duplicates: only add detected entries not already stored
        stored_titles = {e.title for e in entries}
        for entry in detected:
            if entry.title not in stored_titles:
                entries.append(entry)

        return entries

    def add_hall_of_fame_entry(self, career: Career, entry: "HallOfFameEntry") -> None:
        """
        Add a new achievement to the career's Hall of Fame.

        Stores entries in the career's board_objectives JSON field under
        a "hall_of_fame" key, or in a dedicated JSON structure if board_objectives
        is already used for other purposes.

        Args:
            career: The career to add the entry to
            entry: The HallOfFameEntry to add
        """
        entries = self._load_hall_of_fame_entries(career)
        entries.append(entry)
        self._save_hall_of_fame_entries(career, entries)

        logger.info(
            f"Hall of Fame entry added for career {career.id}: "
            f"'{entry.title}' ({entry.achievement_type})"
        )

    def _detect_milestones(self, career: Career) -> List["HallOfFameEntry"]:
        """
        Auto-detect milestones from career statistics.

        Checks current career stats against milestone thresholds.

        Args:
            career: The career to check

        Returns:
            List[HallOfFameEntry]: Detected milestone entries
        """
        detected: List[HallOfFameEntry] = []
        total_matches = career.get_total_matches()
        win_percentage = career.get_win_percentage()

        for milestone in self.MILESTONES:
            stat = milestone["stat"]

            # Get the current value for this stat
            if stat == "total_matches":
                current_value = total_matches
            elif stat == "win_percentage":
                current_value = win_percentage
                # Only check win percentage if enough matches played (min 20)
                if total_matches < 20:
                    continue
            else:
                current_value = getattr(career, stat, 0)

            threshold = milestone["threshold"]
            if current_value >= threshold:
                detected.append(HallOfFameEntry(
                    achievement_type=milestone["achievement_type"],
                    title=milestone["title"],
                    description=milestone["description"],
                    season=career.current_season,
                    week=career.current_week,
                    value=int(current_value) if isinstance(current_value, float) else current_value,
                ))

        return detected

    def _load_hall_of_fame_entries(self, career: Career) -> List["HallOfFameEntry"]:
        """
        Load stored Hall of Fame entries from the career.

        Entries are stored in the board_objectives JSON field under a
        "hall_of_fame" key.

        Args:
            career: The career to load entries from

        Returns:
            List[HallOfFameEntry]: Stored entries
        """
        if not career.board_objectives:
            return []

        try:
            data = json.loads(career.board_objectives)
        except (json.JSONDecodeError, TypeError):
            return []

        # Look for hall_of_fame key in the JSON structure
        if isinstance(data, dict) and "hall_of_fame" in data:
            hof_data = data["hall_of_fame"]
            return [HallOfFameEntry.from_dict(entry) for entry in hof_data]

        return []

    def _save_hall_of_fame_entries(
        self, career: Career, entries: List["HallOfFameEntry"]
    ) -> None:
        """
        Save Hall of Fame entries to the career's board_objectives field.

        Preserves existing board_objectives data by nesting hall_of_fame
        within the JSON structure.

        Args:
            career: The career to save entries to
            entries: The entries to save
        """
        # Load existing data
        existing_data: Dict[str, Any] = {}
        if career.board_objectives:
            try:
                parsed = json.loads(career.board_objectives)
                if isinstance(parsed, dict):
                    existing_data = parsed
                elif isinstance(parsed, list):
                    # Preserve existing list-based objectives under a key
                    existing_data = {"objectives": parsed}
            except (json.JSONDecodeError, TypeError):
                pass

        # Store hall of fame entries
        existing_data["hall_of_fame"] = [entry.to_dict() for entry in entries]

        career.board_objectives = json.dumps(existing_data)

    # --- Manager Fatigue System ---

    def calculate_fatigue_morale_penalty(self, consecutive_losses: int) -> int:
        """
        Calculate the morale penalty based on consecutive losses.

        Penalty scale:
            - 0-4 losses: 0 penalty
            - 5 losses: -5 penalty
            - 6 losses: -8 penalty
            - 7+ losses: -10 penalty

        Args:
            consecutive_losses: Number of consecutive losses from recent results

        Returns:
            int: The morale penalty (negative value, or 0 if not fatigued)
        """
        if consecutive_losses < 5:
            return 0
        elif consecutive_losses == 5:
            return -5
        elif consecutive_losses == 6:
            return -8
        else:
            return -10

    def check_manager_fatigue(
        self, career: Career, recent_results: List[str]
    ) -> ManagerFatigueStatus:
        """
        Check manager fatigue based on recent match results.

        Counts consecutive losses from the end of the results list.
        When 5 or more consecutive losses are detected, the manager is
        considered fatigued and a morale penalty applies to all players.

        Args:
            career: The career to check fatigue for
            recent_results: List of recent match results ("W", "D", "L")
                ordered chronologically (oldest first, most recent last)

        Returns:
            ManagerFatigueStatus: Current fatigue status with penalty info
        """
        # Count consecutive losses from the end of the list
        consecutive_losses = 0
        for result in reversed(recent_results):
            if result == "L":
                consecutive_losses += 1
            else:
                break

        is_fatigued = consecutive_losses >= 5
        morale_penalty = self.calculate_fatigue_morale_penalty(consecutive_losses)

        if is_fatigued:
            description = (
                f"Manager is fatigued after {consecutive_losses} consecutive losses. "
                f"Morale penalty of {morale_penalty} applied to all players."
            )
        else:
            description = "Manager is not fatigued."

        return ManagerFatigueStatus(
            consecutive_losses=consecutive_losses,
            is_fatigued=is_fatigued,
            morale_penalty=morale_penalty,
            description=description,
        )

    def get_recent_results(self, career: Career) -> List[str]:
        """
        Get the recent match results for a career.

        Returns results as a list of "W", "D", "L" strings.
        Currently returns results derived from career statistics as a stub.
        A full implementation would query the match history table.

        Args:
            career: The career to get results for

        Returns:
            List[str]: Recent match results (oldest first, most recent last).
                Returns empty list if no matches have been played.
        """
        # Stub: In a full implementation, this would query the matches table
        # for the most recent N matches and return their results in order.
        # For now, return an empty list (no match history tracking yet).
        return []

    # Private helper methods
    
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by database ID"""
        try:
            result = await self.session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None
    
    async def _get_club_by_id(self, club_id: int) -> Optional[Club]:
        """Get club by database ID"""
        try:
            result = await self.session.execute(
                select(Club).where(Club.id == club_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching club {club_id}: {str(e)}")
            return None
    
    async def _get_user_career(self, user_id: int) -> Optional[Career]:
        """Get the active career for a user (internal helper)"""
        try:
            result = await self.session.execute(
                select(Career)
                .where(Career.user_id == user_id)
                .order_by(Career.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching career for user {user_id}: {str(e)}")
            return None
