"""
Squad Service - Squad management, contracts, morale, and player interactions.

This module provides functionality for managing football squads including:
- Squad size validation (18-40 players)
- Matchday squad selection (11 starters + 7 subs)
- Player contract tracking and expiry notifications
- Squad status management
- Player morale calculation and its impact on CA
- Player interactions (praise, criticise, promise time, discuss contract)
- Transfer request logic
- Player aging system
- Non-EU player restrictions
- Full player attribute display
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# --- Constants ---

MIN_SQUAD_SIZE = 18
MAX_SQUAD_SIZE = 40
MATCHDAY_STARTERS = 11
MATCHDAY_SUBS = 7
MATCHDAY_TOTAL = MATCHDAY_STARTERS + MATCHDAY_SUBS

LOW_MORALE_THRESHOLD = 40
VERY_LOW_MORALE_THRESHOLD = 20
TRANSFER_REQUEST_WEEKS = 3
MORALE_CA_PENALTY_PERCENT = 5
MAX_NON_EU_STARTERS = 3  # Default, overridden per league
CONTRACT_EXPIRY_THRESHOLD_MONTHS = 6


# --- Data Classes ---

@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class ContractInfo:
    """Contract information for a squad player."""
    player_id: int
    contract_start_date: date
    contract_end_date: date
    wage: int
    release_clause: Optional[int]
    months_remaining: Optional[int]
    is_expiring_soon: bool


@dataclass
class ContractNotification:
    """Notification about an expiring contract."""
    player_id: int
    player_name: str
    contract_end_date: date
    months_remaining: int
    squad_status: str


@dataclass
class InteractionResult:
    """Result of a player interaction."""
    interaction_type: str
    morale_change: int
    new_morale: int
    message: str


@dataclass
class AgingResult:
    """Result of aging a player."""
    player_id: int
    new_age: int
    ca_change: int
    new_ca: int
    description: str


# --- Squad Status Enum (mirrors model) ---

class SquadStatus:
    """Squad status constants matching the model enum."""
    KEY_PLAYER = "KEY_PLAYER"
    FIRST_TEAM = "FIRST_TEAM"
    ROTATION = "ROTATION"
    BACKUP = "BACKUP"
    NOT_NEEDED = "NOT_NEEDED"

    ALL = [KEY_PLAYER, FIRST_TEAM, ROTATION, BACKUP, NOT_NEEDED]


# --- EU Nationality Lists ---

EU_NATIONALITIES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden",
    # EEA + Switzerland (treated as EU for football purposes)
    "Norway", "Iceland", "Liechtenstein", "Switzerland",
}


# --- League Foreign Player Rules ---
# Not all leagues have non-EU restrictions. This dict maps league_id/name
# to their specific foreign player rules. Leagues not listed have NO restriction.
# Format: {league_key: {"max_foreign_starters": int, "rule_type": str, "description": str}}

LEAGUE_FOREIGN_PLAYER_RULES: Dict[str, Dict[str, Any]] = {
    "turkey_super_lig": {
        "max_foreign_starters": 3,
        "rule_type": "non_eu",
        "description": "Maximum 3 non-EU players in starting 11",
    },
    "russia_premier_league": {
        "max_foreign_starters": 8,
        "rule_type": "foreign",
        "description": "Maximum 8 foreign players in matchday squad",
    },
    "saudi_pro_league": {
        "max_foreign_starters": 8,
        "rule_type": "foreign",
        "description": "Maximum 8 foreign players in matchday squad",
    },
    "china_super_league": {
        "max_foreign_starters": 5,
        "rule_type": "foreign",
        "description": "Maximum 5 foreign players in starting 11",
    },
    "japan_j_league": {
        "max_foreign_starters": 5,
        "rule_type": "foreign",
        "description": "Maximum 5 foreign players in matchday squad",
    },
    "south_korea_k_league": {
        "max_foreign_starters": 4,
        "rule_type": "foreign",
        "description": "Maximum 4 foreign players in starting 11",
    },
    # European leagues with NO non-EU restriction (most top leagues):
    # England, Spain, Germany, Italy, France, Netherlands, Portugal - no limit
}


# --- SquadService Class ---

class SquadService:
    """
    Service for managing football squads.

    Provides synchronous validation and calculation methods for squad management.
    No database access is performed directly; callers pass in data as needed.

    Example:
        >>> service = SquadService()
        >>> service.validate_squad_size(25)
        True
        >>> service.can_add_player(40)
        False
    """

    # ---------------------------------------------------------------
    # 7.1 Squad size validation (18-40 players)
    # ---------------------------------------------------------------

    def validate_squad_size(self, squad_count: int) -> bool:
        """
        Validate that squad size is within allowed range.

        Args:
            squad_count: Current number of players in the squad.

        Returns:
            True if squad_count is between MIN_SQUAD_SIZE and MAX_SQUAD_SIZE inclusive.
        """
        return MIN_SQUAD_SIZE <= squad_count <= MAX_SQUAD_SIZE

    def can_add_player(self, current_squad_size: int) -> bool:
        """
        Check if a player can be added to the squad.

        Args:
            current_squad_size: Current number of players in the squad.

        Returns:
            True if adding one more player would not exceed MAX_SQUAD_SIZE.
        """
        return current_squad_size < MAX_SQUAD_SIZE

    def can_remove_player(self, current_squad_size: int) -> bool:
        """
        Check if a player can be removed from the squad.

        Args:
            current_squad_size: Current number of players in the squad.

        Returns:
            True if removing one player would not go below MIN_SQUAD_SIZE.
        """
        return current_squad_size > MIN_SQUAD_SIZE

    # ---------------------------------------------------------------
    # 7.2 Matchday squad selection (11 starters + 7 subs)
    # ---------------------------------------------------------------

    def validate_matchday_squad(
        self, starters: List[Any], subs: List[Any]
    ) -> ValidationResult:
        """
        Validate a matchday squad selection.

        Args:
            starters: List of starter players (should be exactly 11).
            subs: List of substitute players (should be exactly 7).

        Returns:
            ValidationResult with is_valid and any error messages.
        """
        errors: List[str] = []

        if len(starters) != MATCHDAY_STARTERS:
            errors.append(
                f"Must have exactly {MATCHDAY_STARTERS} starters, got {len(starters)}"
            )

        if len(subs) != MATCHDAY_SUBS:
            errors.append(
                f"Must have exactly {MATCHDAY_SUBS} substitutes, got {len(subs)}"
            )

        total = len(starters) + len(subs)
        if total != MATCHDAY_TOTAL:
            errors.append(
                f"Matchday squad must be {MATCHDAY_TOTAL} players, got {total}"
            )

        # Check for duplicates
        all_players = starters + subs
        if len(set(id(p) for p in all_players)) != len(all_players):
            errors.append("Duplicate players found in matchday squad")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # ---------------------------------------------------------------
    # 7.3 Player contract tracking
    # ---------------------------------------------------------------

    def get_contract_info(self, squad_player: Any) -> ContractInfo:
        """
        Get contract information for a squad player.

        Args:
            squad_player: A SquadPlayer instance (or duck-typed object with
                          contract_start_date, contract_end_date, wage,
                          release_clause, contract_months_remaining, player_id).

        Returns:
            ContractInfo dataclass with all contract details.
        """
        months_remaining = squad_player.contract_months_remaining
        is_expiring = (
            months_remaining is not None
            and months_remaining <= CONTRACT_EXPIRY_THRESHOLD_MONTHS
        )

        return ContractInfo(
            player_id=squad_player.player_id,
            contract_start_date=squad_player.contract_start_date,
            contract_end_date=squad_player.contract_end_date,
            wage=squad_player.wage,
            release_clause=squad_player.release_clause,
            months_remaining=months_remaining,
            is_expiring_soon=is_expiring,
        )

    def check_expiring_contracts(
        self,
        squad_players: List[Any],
        threshold_months: int = CONTRACT_EXPIRY_THRESHOLD_MONTHS,
    ) -> List[Any]:
        """
        Filter squad players whose contracts are expiring within threshold.

        Args:
            squad_players: List of SquadPlayer instances.
            threshold_months: Months threshold for "expiring soon" (default 6).

        Returns:
            List of squad players with contracts expiring within threshold.
        """
        expiring = []
        for sp in squad_players:
            if sp.contract_months_remaining is not None and sp.contract_months_remaining <= threshold_months:
                expiring.append(sp)
        return expiring

    # ---------------------------------------------------------------
    # 7.4 Contract expiry notifications
    # ---------------------------------------------------------------

    def generate_contract_notifications(
        self,
        squad_players: List[Any],
        player_names: Optional[Dict[int, str]] = None,
    ) -> List[ContractNotification]:
        """
        Generate notifications for players with expiring contracts (< 6 months).

        Args:
            squad_players: List of SquadPlayer instances.
            player_names: Optional mapping of player_id -> player_name.
                          If not provided, uses "Player {player_id}".

        Returns:
            List of ContractNotification for players with < 6 months remaining.
        """
        if player_names is None:
            player_names = {}

        notifications: List[ContractNotification] = []
        expiring = self.check_expiring_contracts(squad_players)

        for sp in expiring:
            name = player_names.get(sp.player_id, f"Player {sp.player_id}")
            status = (
                sp.squad_status.value
                if hasattr(sp.squad_status, "value")
                else str(sp.squad_status)
            )
            notifications.append(
                ContractNotification(
                    player_id=sp.player_id,
                    player_name=name,
                    contract_end_date=sp.contract_end_date,
                    months_remaining=sp.contract_months_remaining,
                    squad_status=status,
                )
            )

        # Sort by months remaining (most urgent first)
        notifications.sort(key=lambda n: n.months_remaining)
        return notifications

    # ---------------------------------------------------------------
    # 7.5 Squad status system
    # ---------------------------------------------------------------

    def set_squad_status(self, squad_player: Any, new_status: str) -> None:
        """
        Set a player's squad status.

        Args:
            squad_player: A SquadPlayer instance.
            new_status: One of SquadStatus constants.

        Raises:
            ValueError: If new_status is not a valid squad status.
        """
        if new_status not in SquadStatus.ALL:
            raise ValueError(
                f"Invalid squad status '{new_status}'. "
                f"Must be one of: {SquadStatus.ALL}"
            )

        # Import the enum from the model if the squad_player uses it
        if hasattr(squad_player, "squad_status"):
            from app.models.squad_player import SquadStatus as ModelSquadStatus
            try:
                squad_player.squad_status = ModelSquadStatus(new_status)
            except (ValueError, KeyError):
                squad_player.squad_status = new_status

    def get_squad_by_status(
        self, squad_players: List[Any], status: str
    ) -> List[Any]:
        """
        Filter squad players by their squad status.

        Args:
            squad_players: List of SquadPlayer instances.
            status: The squad status to filter by.

        Returns:
            List of squad players matching the given status.
        """
        result = []
        for sp in squad_players:
            sp_status = (
                sp.squad_status.value
                if hasattr(sp.squad_status, "value")
                else str(sp.squad_status)
            )
            if sp_status == status:
                result.append(sp)
        return result

    # ---------------------------------------------------------------
    # 7.6 Player morale calculation
    # ---------------------------------------------------------------

    def calculate_morale(
        self,
        squad_player: Any,
        recent_results: List[str],
        playing_time_ratio: float,
    ) -> int:
        """
        Calculate player morale based on multiple factors.

        Factors:
        - Squad status: Key players expect more, backups expect less
        - Playing time: Ratio of minutes played vs expected
        - Recent results: Team form affects morale
        - Contract satisfaction: Low months remaining reduces morale

        Args:
            squad_player: A SquadPlayer instance.
            recent_results: List of recent match results ("win", "draw", "loss").
            playing_time_ratio: Ratio of actual playing time to expected (0.0-1.0+).

        Returns:
            Calculated morale value (1-100).
        """
        base_morale = 50

        # Factor 1: Squad status expectations
        status = (
            squad_player.squad_status.value
            if hasattr(squad_player.squad_status, "value")
            else str(squad_player.squad_status)
        )
        status_expectations = {
            SquadStatus.KEY_PLAYER: 0.8,
            SquadStatus.FIRST_TEAM: 0.6,
            SquadStatus.ROTATION: 0.4,
            SquadStatus.BACKUP: 0.2,
            SquadStatus.NOT_NEEDED: 0.1,
        }
        expected_time = status_expectations.get(status, 0.5)

        # Playing time satisfaction: compare actual vs expected
        if expected_time > 0:
            time_satisfaction = playing_time_ratio / expected_time
        else:
            time_satisfaction = 1.0

        if time_satisfaction >= 1.0:
            base_morale += 15
        elif time_satisfaction >= 0.7:
            base_morale += 5
        elif time_satisfaction >= 0.4:
            base_morale -= 5
        else:
            base_morale -= 15

        # Factor 2: Recent results
        if recent_results:
            wins = recent_results.count("win")
            losses = recent_results.count("loss")
            total = len(recent_results)
            win_ratio = wins / total
            loss_ratio = losses / total

            if win_ratio >= 0.6:
                base_morale += 10
            elif win_ratio >= 0.4:
                base_morale += 5
            elif loss_ratio >= 0.6:
                base_morale -= 10
            elif loss_ratio >= 0.4:
                base_morale -= 5

        # Factor 3: Contract satisfaction
        months_remaining = squad_player.contract_months_remaining
        if months_remaining is not None:
            if months_remaining <= 3:
                base_morale -= 10
            elif months_remaining <= 6:
                base_morale -= 5

        # Factor 4: Current morale inertia (blend with existing)
        current_morale = squad_player.morale
        # Weighted average: 60% calculated, 40% current (smooth transitions)
        final_morale = int(base_morale * 0.6 + current_morale * 0.4)

        # Clamp to valid range
        return max(1, min(100, final_morale))

    # ---------------------------------------------------------------
    # 7.7 Morale impact on CA
    # ---------------------------------------------------------------

    def get_effective_ca(self, player_ca: int, morale: int) -> int:
        """
        Calculate effective CA considering morale penalty.

        If morale < 40, reduce CA by 5%.

        Args:
            player_ca: The player's base Current Ability.
            morale: The player's current morale (1-100).

        Returns:
            Effective CA (reduced if morale is low).
        """
        if morale < LOW_MORALE_THRESHOLD:
            penalty = player_ca * MORALE_CA_PENALTY_PERCENT / 100
            return max(1, int(player_ca - penalty))
        return player_ca

    # ---------------------------------------------------------------
    # 7.8 Player interaction system
    # ---------------------------------------------------------------

    def interact_with_player(
        self, squad_player: Any, interaction_type: str
    ) -> InteractionResult:
        """
        Perform a player interaction and calculate morale impact.

        Interaction types and their effects:
        - "praise": +5 to +10 morale (more effective for low morale players)
        - "criticise": -5 to -15 morale (can motivate determined players)
        - "promise_time": +10 morale (but creates expectation)
        - "discuss_contract": +5 morale (shows interest in player's future)

        Args:
            squad_player: A SquadPlayer instance.
            interaction_type: One of "praise", "criticise", "promise_time",
                              "discuss_contract".

        Returns:
            InteractionResult with morale change and message.

        Raises:
            ValueError: If interaction_type is not valid.
        """
        valid_types = {"praise", "criticise", "promise_time", "discuss_contract"}
        if interaction_type not in valid_types:
            raise ValueError(
                f"Invalid interaction type '{interaction_type}'. "
                f"Must be one of: {valid_types}"
            )

        current_morale = squad_player.morale
        morale_change = 0
        message = ""

        if interaction_type == "praise":
            # More effective when morale is low
            if current_morale < 40:
                morale_change = 10
                message = "The player is grateful for the recognition and feels motivated."
            elif current_morale < 70:
                morale_change = 7
                message = "The player appreciates the praise."
            else:
                morale_change = 5
                message = "The player acknowledges the praise with a nod."

        elif interaction_type == "criticise":
            # Can backfire on low-morale players, motivate determined ones
            if current_morale < 30:
                morale_change = -15
                message = "The player is devastated by the criticism."
            elif current_morale < 60:
                morale_change = -10
                message = "The player is unhappy with the criticism."
            else:
                morale_change = -5
                message = "The player takes the criticism on board."

        elif interaction_type == "promise_time":
            morale_change = 10
            message = "The player is pleased with the promise of more playing time."

        elif interaction_type == "discuss_contract":
            if squad_player.contract_months_remaining is not None and squad_player.contract_months_remaining <= 6:
                morale_change = 8
                message = "The player is relieved you want to discuss their future."
            else:
                morale_change = 5
                message = "The player appreciates the contract discussion."

        # Apply morale change
        new_morale = max(1, min(100, current_morale + morale_change))
        squad_player.morale = new_morale

        return InteractionResult(
            interaction_type=interaction_type,
            morale_change=morale_change,
            new_morale=new_morale,
            message=message,
        )

    # ---------------------------------------------------------------
    # 7.9 Transfer request logic
    # ---------------------------------------------------------------

    def check_transfer_request(
        self, squad_player: Any, consecutive_low_morale_weeks: int
    ) -> bool:
        """
        Check if a player should submit a transfer request.

        A transfer request is triggered when morale < 20 for 3 consecutive weeks.

        Args:
            squad_player: A SquadPlayer instance.
            consecutive_low_morale_weeks: Number of consecutive weeks with
                                          morale < 20.

        Returns:
            True if the player should submit a transfer request.
        """
        return (
            squad_player.morale < VERY_LOW_MORALE_THRESHOLD
            and consecutive_low_morale_weeks >= TRANSFER_REQUEST_WEEKS
        )

    # ---------------------------------------------------------------
    # 7.10 Player aging system
    # ---------------------------------------------------------------

    def age_player(
        self, player: Any, current_ca: int, current_pa: int
    ) -> AgingResult:
        """
        Age a player by 1 year and recalculate CA.

        Age effects on CA:
        - Under 24: CA can grow towards PA (+1 to +3 per year)
        - 24-29: Peak years, CA stable (0 to +1)
        - 30-32: Early decline (-1 to -2 per year)
        - 33+: Significant decline (-2 to -4 per year)

        Args:
            player: A Player instance (must have 'age' attribute).
            current_ca: The player's current CA.
            current_pa: The player's potential ability.

        Returns:
            AgingResult with new age, CA change, and description.
        """
        old_age = player.age
        new_age = old_age + 1
        player.age = new_age

        ca_change = 0
        description = ""

        if new_age < 24:
            # Growth phase: move towards PA
            room_to_grow = max(0, current_pa - current_ca)
            if room_to_grow > 0:
                # Younger players grow faster
                if new_age < 20:
                    ca_change = min(3, room_to_grow)
                elif new_age < 22:
                    ca_change = min(2, room_to_grow)
                else:
                    ca_change = min(1, room_to_grow)
                description = f"Player developing well, CA increased by {ca_change}."
            else:
                description = "Player has reached their potential."

        elif new_age <= 29:
            # Peak years
            if current_ca < current_pa:
                ca_change = min(1, current_pa - current_ca)
                description = "Player in peak years, slight improvement."
            else:
                ca_change = 0
                description = "Player maintaining peak performance."

        elif new_age <= 32:
            # Early decline
            ca_change = -1 if new_age <= 31 else -2
            description = f"Player beginning to decline, CA reduced by {abs(ca_change)}."

        else:
            # Significant decline
            if new_age <= 35:
                ca_change = -3
            else:
                ca_change = -4
            description = f"Player in significant decline, CA reduced by {abs(ca_change)}."

        new_ca = max(1, min(200, current_ca + ca_change))

        return AgingResult(
            player_id=player.id if hasattr(player, "id") else 0,
            new_age=new_age,
            ca_change=ca_change,
            new_ca=new_ca,
            description=description,
        )

    # ---------------------------------------------------------------
    # 7.11 Non-EU player restrictions (league-configurable)
    # ---------------------------------------------------------------

    def get_league_foreign_rules(self, league_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get foreign player rules for a specific league.

        Not all leagues have restrictions. Returns None if the league
        has no foreign player limit (e.g., England, Spain, Germany, etc.).

        Args:
            league_key: League identifier (e.g., "turkey_super_lig").
                        If None, returns None (no restriction).

        Returns:
            Dict with rule details, or None if no restriction applies.
        """
        if league_key is None:
            return None
        return LEAGUE_FOREIGN_PLAYER_RULES.get(league_key)

    def validate_non_eu_restriction(
        self,
        starters: List[Any],
        max_non_eu: int = MAX_NON_EU_STARTERS,
        league_key: Optional[str] = None,
    ) -> bool:
        """
        Validate that the starting 11 does not exceed the foreign player limit.

        This restriction is league-specific. Not all leagues enforce it.
        If league_key is provided and the league has no rules, returns True (no restriction).
        If league_key is None, falls back to max_non_eu parameter.

        Args:
            starters: List of player objects (must have 'nationality' attribute).
            max_non_eu: Maximum allowed non-EU players (default 3, used as fallback).
            league_key: Optional league identifier to look up specific rules.

        Returns:
            True if the restriction is satisfied or doesn't apply.
        """
        # Check if league has specific rules
        if league_key is not None:
            rules = self.get_league_foreign_rules(league_key)
            if rules is None:
                # League has no foreign player restriction
                return True
            max_non_eu = rules["max_foreign_starters"]

        non_eu_count = self.count_non_eu_players(starters)
        return non_eu_count <= max_non_eu

    def has_foreign_player_restriction(self, league_key: str) -> bool:
        """
        Check if a league has any foreign player restriction.

        Args:
            league_key: League identifier.

        Returns:
            True if the league has a restriction, False otherwise.
        """
        return league_key in LEAGUE_FOREIGN_PLAYER_RULES

    def count_non_eu_players(self, players: List[Any]) -> int:
        """
        Count the number of non-EU players in a list.

        Args:
            players: List of player objects with 'nationality' attribute.

        Returns:
            Number of players whose nationality is not in the EU set.
        """
        count = 0
        for player in players:
            nationality = getattr(player, "nationality", "")
            if nationality not in EU_NATIONALITIES:
                count += 1
        return count

    # ---------------------------------------------------------------
    # 7.12 Player attribute display
    # ---------------------------------------------------------------

    def get_player_full_profile(
        self, squad_player: Any, player: Any
    ) -> Dict[str, Any]:
        """
        Get a complete player profile combining Player and SquadPlayer data.

        Args:
            squad_player: A SquadPlayer instance with contract/squad info.
            player: A Player instance with all attributes.

        Returns:
            Dictionary with complete player profile including all attributes,
            contract info, squad status, morale, and statistics.
        """
        # Basic info
        profile: Dict[str, Any] = {
            "id": player.id if hasattr(player, "id") else None,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "nationality": player.nationality,
            "club": player.club,
            "height": player.height,
            "weight": player.weight,
            "left_foot": player.left_foot,
            "right_foot": player.right_foot,
        }

        # Ability
        profile["ability"] = {
            "ca": player.ca,
            "pa": player.pa,
            "effective_ca": self.get_effective_ca(player.ca, squad_player.morale),
        }

        # Technical attributes
        profile["technical"] = {
            "corners": player.corners,
            "crossing": player.crossing,
            "dribbling": player.dribbling,
            "finishing": player.finishing,
            "first_touch": player.first_touch,
            "free_kicks": player.free_kicks,
            "heading": player.heading,
            "long_shots": player.long_shots,
            "long_throws": player.long_throws,
            "marking": player.marking,
            "passing": player.passing,
            "penalty": player.penalty,
            "tackling": player.tackling,
            "technique": player.technique,
        }

        # Mental attributes
        profile["mental"] = {
            "aggression": player.aggression,
            "anticipation": player.anticipation,
            "bravery": player.bravery,
            "composure": player.composure,
            "concentration": player.concentration,
            "decisions": player.decisions,
            "determination": player.determination,
            "flair": player.flair,
            "leadership": player.leadership,
            "off_the_ball": player.off_the_ball,
            "positioning": player.positioning,
            "teamwork": player.teamwork,
            "vision": player.vision,
            "work_rate": player.work_rate,
        }

        # Physical attributes
        profile["physical"] = {
            "acceleration": player.acceleration,
            "agility": player.agility,
            "balance": player.balance,
            "jumping": player.jumping,
            "stamina": player.stamina,
            "pace": player.pace,
            "endurance": player.endurance,
            "strength": player.strength,
        }

        # Traits
        profile["traits"] = player.traits if hasattr(player, "traits") else None

        # Contract info
        squad_status = (
            squad_player.squad_status.value
            if hasattr(squad_player.squad_status, "value")
            else str(squad_player.squad_status)
        )
        profile["contract"] = {
            "start_date": (
                squad_player.contract_start_date.isoformat()
                if squad_player.contract_start_date
                else None
            ),
            "end_date": (
                squad_player.contract_end_date.isoformat()
                if squad_player.contract_end_date
                else None
            ),
            "wage": squad_player.wage,
            "release_clause": squad_player.release_clause,
            "months_remaining": squad_player.contract_months_remaining,
        }

        # Squad info
        profile["squad"] = {
            "status": squad_status,
            "number": squad_player.squad_number,
            "morale": squad_player.morale,
            "joined_date": (
                squad_player.joined_date.isoformat()
                if squad_player.joined_date
                else None
            ),
        }

        # Statistics
        profile["statistics"] = {
            "appearances": squad_player.appearances,
            "goals": squad_player.goals,
            "assists": squad_player.assists,
            "minutes_played": squad_player.minutes_played,
            "yellow_cards": squad_player.yellow_cards,
            "red_cards": squad_player.red_cards,
            "goals_per_appearance": squad_player.get_goals_per_appearance(),
            "assists_per_appearance": squad_player.get_assists_per_appearance(),
        }

        # Financial
        profile["financial"] = {
            "price": player.price,
            "wage": player.wage,
        }

        return profile
