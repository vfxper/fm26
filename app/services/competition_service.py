"""
Competition Service - Manages football competition lifecycle

This module implements the Competition Engine functionality for managing
domestic leagues, domestic cups, and continental cups. It handles fixture
generation, AI match simulation, league tables, promotion/relegation,
prize money distribution, trophy events, European qualification,
multi-season support, cup draws, and player availability checking.

Implements Tasks 17.1-17.14: Competition Engine Implementation
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.models.competition import Competition, CompetitionType
from app.models.fixture import Fixture, FixtureStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# Prize money defaults by league position (positions 1-20)
DEFAULT_LEAGUE_PRIZE_MONEY = {
    "1": 50_000_000, "2": 40_000_000, "3": 35_000_000, "4": 30_000_000,
    "5": 27_000_000, "6": 24_000_000, "7": 21_000_000, "8": 19_000_000,
    "9": 17_000_000, "10": 15_000_000, "11": 13_000_000, "12": 11_000_000,
    "13": 10_000_000, "14": 9_000_000, "15": 8_000_000, "16": 7_000_000,
    "17": 6_000_000, "18": 5_000_000, "19": 4_000_000, "20": 3_000_000,
}

# Cup prize money
DEFAULT_CUP_PRIZE_MONEY = {
    "winner": 10_000_000,
    "runner_up": 5_000_000,
    "semi_final": 2_500_000,
    "quarter_final": 1_250_000,
}

# Continental cup prize money
DEFAULT_CONTINENTAL_PRIZE_MONEY = {
    "winner": 30_000_000,
    "runner_up": 20_000_000,
    "semi_final": 12_000_000,
    "quarter_final": 8_000_000,
    "group_stage": 4_000_000,
}


@dataclass
class LeagueStanding:
    """Represents a team's standing in a league table."""
    club_id: int
    club_name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0

    def to_dict(self) -> dict:
        return {
            "club_id": self.club_id,
            "club_name": self.club_name,
            "played": self.played,
            "won": self.won,
            "drawn": self.drawn,
            "lost": self.lost,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
        }


@dataclass
class MatchResultSimple:
    """Simplified match result from AI simulation."""
    home_goals: int
    away_goals: int
    home_club_id: int
    away_club_id: int


@dataclass
class SquadAvailability:
    """Squad availability report for a fixture."""
    available_players: List[int] = field(default_factory=list)
    injured_players: List[Dict] = field(default_factory=list)
    suspended_players: List[Dict] = field(default_factory=list)
    total_squad_size: int = 0
    available_count: int = 0


class CompetitionService:
    """
    Service for managing football competitions including leagues, cups,
    and continental tournaments.

    Provides methods for:
    - Creating and managing domestic leagues (20 clubs, 38 matchdays)
    - Creating and managing domestic cups (knockout format)
    - Creating and managing continental cups (group stage + knockout)
    - Generating fixture lists (round-robin for leagues, draws for cups)
    - Simulating AI matches (simplified random results based on team strength)
    - Maintaining live league tables
    - Processing promotion and relegation
    - Distributing prize money
    - Generating trophy celebration events
    - Determining European qualification
    - Displaying fixture lists with results
    - Supporting multi-season career progression
    - Drawing cup rounds (randomized seeded)
    - Checking player availability (injuries/suspensions)
    """

    def __init__(self, db_session=None):
        """
        Initialize CompetitionService.

        Args:
            db_session: Optional async database session for persistence operations.
                       If None, service operates in memory-only mode.
        """
        self.db = db_session

    # =========================================================================
    # Task 17.1: Create domestic league simulation (20 clubs, 38 matchdays)
    # =========================================================================

    async def create_league(
        self,
        career_id: int,
        clubs: List[Dict],
        name: str = "Premier League",
        season: int = 2024,
        country: str = "England",
    ) -> Competition:
        """
        Create a domestic league competition with 20 teams and 38 matchdays.

        A round-robin league where each team plays every other team twice
        (once home, once away), resulting in 38 matchdays for 20 teams.

        Args:
            career_id: ID of the career this competition belongs to
            clubs: List of club dicts with at least 'id' and 'name' keys
            name: Competition name (default: "Premier League")
            season: Season year (default: 2024)
            country: Country (default: "England")

        Returns:
            Competition: The created competition object

        Raises:
            ValueError: If clubs list doesn't contain exactly 20 teams
        """
        if len(clubs) != 20:
            raise ValueError(
                f"Domestic league requires exactly 20 clubs, got {len(clubs)}"
            )

        num_matchdays = (len(clubs) - 1) * 2  # 38 for 20 teams

        competition = Competition(
            name=name,
            competition_type=CompetitionType.DOMESTIC_LEAGUE,
            season=season,
            country=country,
            num_teams=len(clubs),
            num_matchdays=num_matchdays,
            current_matchday=1,
            prize_money=json.dumps(DEFAULT_LEAGUE_PRIZE_MONEY),
            reputation_winner=15,
            reputation_runner_up=8,
            promotion_places=0,  # Top division has no promotion
            relegation_places=3,
            playoff_places=0,
            champions_league_places=4,
            europa_league_places=2,
            is_active=True,
            is_completed=False,
        )

        if self.db:
            self.db.add(competition)
            await self.db.flush()

        # Generate fixtures for the league
        fixtures = self.generate_league_fixtures(competition, clubs)

        if self.db:
            for fixture in fixtures:
                self.db.add(fixture)
            await self.db.flush()

        logger.info(
            f"Created league '{name}' with {len(clubs)} clubs, "
            f"{num_matchdays} matchdays, {len(fixtures)} fixtures"
        )

        return competition


    # =========================================================================
    # Task 17.2: Implement domestic cup (knockout format)
    # =========================================================================

    async def create_domestic_cup(
        self,
        career_id: int,
        clubs: List[Dict],
        name: str = "FA Cup",
        season: int = 2024,
        country: str = "England",
    ) -> Competition:
        """
        Create a domestic cup competition in knockout format.

        The cup uses single-elimination knockout rounds. The number of rounds
        depends on the number of teams (must be a power of 2, or teams get byes).

        Args:
            career_id: ID of the career this competition belongs to
            clubs: List of club dicts with at least 'id' and 'name' keys
            name: Competition name (default: "FA Cup")
            season: Season year (default: 2024)
            country: Country (default: "England")

        Returns:
            Competition: The created competition object

        Raises:
            ValueError: If clubs list has fewer than 2 teams
        """
        if len(clubs) < 2:
            raise ValueError(
                f"Domestic cup requires at least 2 clubs, got {len(clubs)}"
            )

        # Calculate number of rounds needed
        import math
        num_rounds = math.ceil(math.log2(len(clubs)))

        competition = Competition(
            name=name,
            competition_type=CompetitionType.DOMESTIC_CUP,
            season=season,
            country=country,
            num_teams=len(clubs),
            num_matchdays=num_rounds,
            current_matchday=1,
            prize_money=json.dumps(DEFAULT_CUP_PRIZE_MONEY),
            reputation_winner=10,
            reputation_runner_up=5,
            promotion_places=0,
            relegation_places=0,
            playoff_places=0,
            champions_league_places=0,
            europa_league_places=0,
            is_active=True,
            is_completed=False,
        )

        if self.db:
            self.db.add(competition)
            await self.db.flush()

        logger.info(
            f"Created domestic cup '{name}' with {len(clubs)} clubs, "
            f"{num_rounds} rounds"
        )

        return competition

    # =========================================================================
    # Task 17.3: Create continental cup (group stage + knockout)
    # =========================================================================

    async def create_continental_cup(
        self,
        career_id: int,
        clubs: List[Dict],
        name: str = "Champions League",
        season: int = 2024,
        country: str = "Europe",
    ) -> Competition:
        """
        Create a continental cup with group stage (8 groups of 4) + knockout.

        Format:
        - Group stage: 8 groups of 4 teams, each team plays 6 matches
        - Knockout: Round of 16, Quarter-finals, Semi-finals, Final
        - Total matchdays: 6 (group) + 4 (knockout) = 10

        Args:
            career_id: ID of the career this competition belongs to
            clubs: List of club dicts with at least 'id', 'name', 'reputation' keys
            name: Competition name (default: "Champions League")
            season: Season year (default: 2024)
            country: Country/region (default: "Europe")

        Returns:
            Competition: The created competition object

        Raises:
            ValueError: If clubs list doesn't contain exactly 32 teams
        """
        if len(clubs) != 32:
            raise ValueError(
                f"Continental cup requires exactly 32 clubs, got {len(clubs)}"
            )

        # 6 group stage matchdays + 4 knockout rounds (R16, QF, SF, Final)
        num_matchdays = 10

        competition = Competition(
            name=name,
            competition_type=CompetitionType.CONTINENTAL_CUP,
            season=season,
            country=country,
            num_teams=len(clubs),
            num_matchdays=num_matchdays,
            current_matchday=1,
            prize_money=json.dumps(DEFAULT_CONTINENTAL_PRIZE_MONEY),
            reputation_winner=20,
            reputation_runner_up=12,
            promotion_places=0,
            relegation_places=0,
            playoff_places=0,
            champions_league_places=0,
            europa_league_places=0,
            is_active=True,
            is_completed=False,
        )

        if self.db:
            self.db.add(competition)
            await self.db.flush()

        logger.info(
            f"Created continental cup '{name}' with {len(clubs)} clubs, "
            f"{num_matchdays} matchdays (6 group + 4 knockout)"
        )

        return competition


    # =========================================================================
    # Task 17.4: Implement fixture list generation
    # =========================================================================

    def generate_league_fixtures(
        self,
        competition: Competition,
        clubs: List[Dict],
        start_date: Optional[datetime] = None,
    ) -> List[Fixture]:
        """
        Generate a complete round-robin fixture list for a league.

        Uses a round-robin scheduling algorithm to ensure each team plays
        every other team twice (once home, once away). For N teams, this
        produces N-1 matchdays in the first half and N-1 in the second half,
        totaling (N-1)*2 matchdays with N/2 matches per matchday.

        Algorithm:
        - Fix one team and rotate the others (circle method)
        - First half: generate all pairings
        - Second half: reverse home/away from first half

        Args:
            competition: The competition to generate fixtures for
            clubs: List of club dicts with 'id' and 'name' keys
            start_date: Optional start date for fixtures (default: season start)

        Returns:
            List[Fixture]: Generated fixture objects
        """
        if start_date is None:
            start_date = datetime(competition.season, 8, 10, 15, 0)  # Aug 10

        n = len(clubs)
        club_ids = [c["id"] for c in clubs]
        fixtures = []

        # Round-robin algorithm (circle method)
        # For N teams, we have N-1 rounds in the first half
        half_rounds = n - 1
        matches_per_round = n // 2

        # Create rotation list (fix first team, rotate rest)
        rotation = list(range(n))

        for round_num in range(half_rounds):
            matchday = round_num + 1
            match_date = start_date + timedelta(weeks=round_num)

            for match_idx in range(matches_per_round):
                # Pair teams from outside in
                home_idx = rotation[match_idx]
                away_idx = rotation[n - 1 - match_idx]

                fixture = Fixture(
                    competition_id=competition.id if competition.id else 0,
                    home_club_id=club_ids[home_idx],
                    away_club_id=club_ids[away_idx],
                    matchday=matchday,
                    scheduled_date=match_date,
                    status=FixtureStatus.SCHEDULED,
                )
                fixtures.append(fixture)

            # Rotate: fix position 0, rotate positions 1..n-1
            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]

        # Second half: reverse home/away
        for round_num in range(half_rounds):
            matchday = half_rounds + round_num + 1
            match_date = start_date + timedelta(weeks=half_rounds + round_num)

            # Get the corresponding first-half fixtures
            first_half_start = round_num * matches_per_round
            first_half_end = first_half_start + matches_per_round

            for i in range(first_half_start, first_half_end):
                original = fixtures[i]
                fixture = Fixture(
                    competition_id=competition.id if competition.id else 0,
                    home_club_id=original.away_club_id,
                    away_club_id=original.home_club_id,
                    matchday=matchday,
                    scheduled_date=match_date,
                    status=FixtureStatus.SCHEDULED,
                )
                fixtures.append(fixture)

        return fixtures


    # =========================================================================
    # Task 17.5: Create AI match simulation for non-player matches
    # =========================================================================

    def simulate_ai_match(
        self,
        home_club: Dict,
        away_club: Dict,
    ) -> MatchResultSimple:
        """
        Simulate a match between two AI-controlled teams.

        Uses a simplified simulation based on team strength (reputation).
        Higher reputation teams are more likely to score and win.
        Home advantage gives +10% to the home team's effective strength.

        Goal distribution follows a Poisson-like model:
        - Base expected goals: 1.3 per team
        - Modified by relative strength difference
        - Home advantage: +0.3 expected goals

        Args:
            home_club: Dict with 'id', 'name', 'reputation' keys
            away_club: Dict with 'id', 'name', 'reputation' keys

        Returns:
            MatchResultSimple: The simulated match result
        """
        home_rep = home_club.get("reputation", 50)
        away_rep = away_club.get("reputation", 50)

        # Calculate expected goals based on reputation difference
        # Base: 1.3 goals per team, modified by strength
        strength_diff = (home_rep - away_rep) / 100.0  # -1.0 to +1.0

        home_expected = 1.3 + strength_diff * 0.8 + 0.3  # Home advantage
        away_expected = 1.3 - strength_diff * 0.8

        # Clamp expected goals
        home_expected = max(0.3, min(3.5, home_expected))
        away_expected = max(0.3, min(3.5, away_expected))

        # Generate goals using weighted random (simplified Poisson)
        home_goals = self._generate_goals(home_expected)
        away_goals = self._generate_goals(away_expected)

        return MatchResultSimple(
            home_goals=home_goals,
            away_goals=away_goals,
            home_club_id=home_club["id"],
            away_club_id=away_club["id"],
        )

    def _generate_goals(self, expected: float) -> int:
        """
        Generate a goal count based on expected goals using weighted random.

        Approximates a Poisson distribution using cumulative probabilities.

        Args:
            expected: Expected number of goals (lambda parameter)

        Returns:
            int: Number of goals scored (0-6)
        """
        import math

        # Calculate Poisson probabilities for 0-6 goals
        probabilities = []
        for k in range(7):
            prob = (math.exp(-expected) * (expected ** k)) / math.factorial(k)
            probabilities.append(prob)

        # Normalize
        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]

        # Cumulative distribution
        r = random.random()
        cumulative = 0.0
        for goals, prob in enumerate(probabilities):
            cumulative += prob
            if r <= cumulative:
                return goals

        return 0  # Fallback


    # =========================================================================
    # Task 17.6: Implement live league table updates
    # =========================================================================

    def get_league_table(
        self,
        competition_id: int,
        clubs: List[Dict],
        results: List[Dict],
    ) -> List[LeagueStanding]:
        """
        Calculate and return the current league table sorted by standings.

        Sorting order:
        1. Points (descending)
        2. Goal difference (descending)
        3. Goals scored (descending)
        4. Club name (ascending, as tiebreaker)

        Args:
            competition_id: ID of the competition
            clubs: List of club dicts with 'id' and 'name' keys
            results: List of completed match result dicts with keys:
                     'home_club_id', 'away_club_id', 'home_goals', 'away_goals'

        Returns:
            List[LeagueStanding]: Sorted league table
        """
        # Initialize standings for all clubs
        standings: Dict[int, LeagueStanding] = {}
        for club in clubs:
            standings[club["id"]] = LeagueStanding(
                club_id=club["id"],
                club_name=club["name"],
            )

        # Process each result
        for result in results:
            home_id = result["home_club_id"]
            away_id = result["away_club_id"]
            home_goals = result["home_goals"]
            away_goals = result["away_goals"]

            if home_id not in standings or away_id not in standings:
                continue

            home = standings[home_id]
            away = standings[away_id]

            # Update matches played
            home.played += 1
            away.played += 1

            # Update goals
            home.goals_for += home_goals
            home.goals_against += away_goals
            away.goals_for += away_goals
            away.goals_against += home_goals

            # Update goal difference
            home.goal_difference = home.goals_for - home.goals_against
            away.goal_difference = away.goals_for - away.goals_against

            # Update wins/draws/losses and points
            if home_goals > away_goals:
                home.won += 1
                home.points += 3
                away.lost += 1
            elif home_goals < away_goals:
                away.won += 1
                away.points += 3
                home.lost += 1
            else:
                home.drawn += 1
                away.drawn += 1
                home.points += 1
                away.points += 1

        # Sort: points desc, goal_difference desc, goals_for desc, name asc
        table = sorted(
            standings.values(),
            key=lambda s: (-s.points, -s.goal_difference, -s.goals_for, s.club_name),
        )

        return table


    # =========================================================================
    # Task 17.7: Create promotion and relegation system
    # =========================================================================

    def process_promotion_relegation(
        self,
        competition: Competition,
        table: List[LeagueStanding],
    ) -> Dict:
        """
        Process promotion and relegation at the end of a season.

        Determines which teams are promoted, relegated, or enter playoffs
        based on the competition's configured places.

        Args:
            competition: The competition with promotion/relegation settings
            table: Final league table (sorted by position)

        Returns:
            Dict with keys:
                - promoted: List of club_ids promoted
                - relegated: List of club_ids relegated
                - playoff: List of club_ids entering playoffs
                - champion: club_id of the league champion
        """
        promoted = []
        relegated = []
        playoff = []
        champion = table[0].club_id if table else None

        # Promoted teams (top N from lower division - not applicable for top division)
        if competition.promotion_places > 0:
            for i in range(min(competition.promotion_places, len(table))):
                promoted.append(table[i].club_id)

        # Playoff places (just below promotion spots)
        if competition.playoff_places > 0:
            start = competition.promotion_places
            end = start + competition.playoff_places
            for i in range(start, min(end, len(table))):
                playoff.append(table[i].club_id)

        # Relegated teams (bottom N)
        if competition.relegation_places > 0:
            for i in range(competition.relegation_places):
                idx = len(table) - 1 - i
                if idx >= 0:
                    relegated.append(table[idx].club_id)

        return {
            "promoted": promoted,
            "relegated": relegated,
            "playoff": playoff,
            "champion": champion,
        }

    # =========================================================================
    # Task 17.8: Implement prize money and reputation awards
    # =========================================================================

    def distribute_season_prizes(
        self,
        competition: Competition,
        table: List[LeagueStanding],
    ) -> List[Dict]:
        """
        Distribute prize money and reputation awards based on final standings.

        For leagues: awards by position (1st-20th).
        For cups: awards by round reached (winner, runner-up, semi-finalist, etc.)

        Args:
            competition: The competition with prize money configuration
            table: Final league table or cup results

        Returns:
            List of dicts with keys:
                - club_id: Club receiving the prize
                - position: Final position (1-based)
                - prize_money: Amount awarded
                - reputation_award: Reputation points awarded
        """
        prizes = []
        prize_config = {}

        if competition.prize_money:
            prize_config = json.loads(competition.prize_money)

        for position, standing in enumerate(table, 1):
            prize_amount = prize_config.get(str(position), 0)

            # Reputation awards
            reputation_award = 0
            if position == 1:
                reputation_award = competition.reputation_winner
            elif position == 2:
                reputation_award = competition.reputation_runner_up

            prizes.append({
                "club_id": standing.club_id,
                "club_name": standing.club_name,
                "position": position,
                "prize_money": prize_amount,
                "reputation_award": reputation_award,
            })

        return prizes


    # =========================================================================
    # Task 17.9: Create trophy celebration events
    # =========================================================================

    def generate_trophy_event(
        self,
        career_id: int,
        competition: Competition,
        position: int,
        club_id: int,
        club_name: str,
    ) -> Dict:
        """
        Generate a trophy celebration event for a club finishing in a winning position.

        Creates event data suitable for the media/event system. Trophy events
        are generated for the winner (position 1) and runner-up (position 2).

        Args:
            career_id: ID of the career
            competition: The competition
            position: Final position (1 = winner, 2 = runner-up)
            club_id: ID of the club
            club_name: Name of the club

        Returns:
            Dict with trophy event data:
                - event_type: "trophy_celebration" or "runner_up"
                - career_id: Career ID
                - competition_name: Name of the competition
                - competition_type: Type of competition
                - club_id: Club ID
                - club_name: Club name
                - position: Final position
                - message: Celebration message
                - reputation_award: Reputation points awarded
                - morale_boost: Morale boost for squad (0-20)
        """
        if position == 1:
            event_type = "trophy_celebration"
            message = f"🏆 {club_name} wins the {competition.name}!"
            morale_boost = 15
            reputation_award = competition.reputation_winner
        elif position == 2:
            event_type = "runner_up"
            message = f"🥈 {club_name} finishes as runner-up in the {competition.name}"
            morale_boost = 5
            reputation_award = competition.reputation_runner_up
        else:
            event_type = "season_end"
            message = f"{club_name} finishes {position}{'st' if position == 1 else 'nd' if position == 2 else 'rd' if position == 3 else 'th'} in the {competition.name}"
            morale_boost = 0
            reputation_award = 0

        return {
            "event_type": event_type,
            "career_id": career_id,
            "competition_name": competition.name,
            "competition_type": competition.competition_type,
            "club_id": club_id,
            "club_name": club_name,
            "position": position,
            "message": message,
            "reputation_award": reputation_award,
            "morale_boost": morale_boost,
        }

    # =========================================================================
    # Task 17.10: Implement European qualification logic
    # =========================================================================

    def determine_european_qualifiers(
        self,
        competition: Competition,
        table: List[LeagueStanding],
    ) -> Dict:
        """
        Determine which teams qualify for European competitions.

        Based on the competition's configured Champions League and Europa League
        places, selects the top teams from the final league table.

        Args:
            competition: The competition with European qualification settings
            table: Final league table (sorted by position)

        Returns:
            Dict with keys:
                - champions_league: List of club_ids qualifying for CL
                - europa_league: List of club_ids qualifying for EL
                - total_qualifiers: Total number of European qualifiers
        """
        champions_league = []
        europa_league = []

        # Champions League places (top N)
        cl_places = competition.champions_league_places
        for i in range(min(cl_places, len(table))):
            champions_league.append({
                "club_id": table[i].club_id,
                "club_name": table[i].club_name,
                "position": i + 1,
            })

        # Europa League places (next M after CL places)
        el_places = competition.europa_league_places
        el_start = cl_places
        for i in range(el_start, min(el_start + el_places, len(table))):
            europa_league.append({
                "club_id": table[i].club_id,
                "club_name": table[i].club_name,
                "position": i + 1,
            })

        return {
            "champions_league": champions_league,
            "europa_league": europa_league,
            "total_qualifiers": len(champions_league) + len(europa_league),
        }


    # =========================================================================
    # Task 17.11: Create fixture list display with results
    # =========================================================================

    def get_fixture_list(
        self,
        fixtures: List[Dict],
        matchday: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get fixture list with results for display.

        Filters fixtures by matchday if specified, and formats them for display
        including scores for completed matches.

        Args:
            fixtures: List of fixture dicts with keys:
                      'id', 'matchday', 'home_club_id', 'away_club_id',
                      'home_club_name', 'away_club_name', 'status',
                      'home_goals' (optional), 'away_goals' (optional)
            matchday: Optional matchday filter (None = all matchdays)

        Returns:
            List of formatted fixture dicts with keys:
                - id: Fixture ID
                - matchday: Matchday number
                - home_club: Home club name
                - away_club: Away club name
                - status: Fixture status
                - score: Score string (e.g., "2 - 1") or None if not played
                - home_goals: Goals scored by home team (or None)
                - away_goals: Goals scored by away team (or None)
        """
        result = []

        for fixture in fixtures:
            if matchday is not None and fixture.get("matchday") != matchday:
                continue

            home_goals = fixture.get("home_goals")
            away_goals = fixture.get("away_goals")
            status = fixture.get("status", "scheduled")

            score = None
            if status == "completed" and home_goals is not None and away_goals is not None:
                score = f"{home_goals} - {away_goals}"

            result.append({
                "id": fixture.get("id"),
                "matchday": fixture.get("matchday"),
                "home_club": fixture.get("home_club_name", f"Club {fixture.get('home_club_id')}"),
                "away_club": fixture.get("away_club_name", f"Club {fixture.get('away_club_id')}"),
                "status": status,
                "score": score,
                "home_goals": home_goals,
                "away_goals": away_goals,
            })

        return result

    # =========================================================================
    # Task 17.12: Implement multi-season career support
    # =========================================================================

    def advance_to_next_season(
        self,
        career_id: int,
        current_season: int,
        competitions: List[Competition],
        league_table: List[LeagueStanding],
        clubs: List[Dict],
    ) -> Dict:
        """
        Handle season transition for multi-season career support.

        Processes end-of-season activities:
        1. Mark all current competitions as completed
        2. Process promotion/relegation
        3. Distribute prize money
        4. Determine European qualifiers
        5. Generate trophy events
        6. Prepare data for next season creation

        Args:
            career_id: ID of the career
            current_season: The season that just ended
            competitions: List of active competitions for the season
            league_table: Final league table
            clubs: List of all club dicts

        Returns:
            Dict with season transition data:
                - previous_season: Season that ended
                - next_season: New season number
                - promotion_relegation: Promotion/relegation results
                - prizes: Prize distribution results
                - european_qualifiers: European qualification results
                - trophy_events: List of trophy events generated
        """
        next_season = current_season + 1
        promotion_relegation = {}
        prizes = []
        european_qualifiers = {}
        trophy_events = []

        for competition in competitions:
            # Mark competition as completed
            competition.complete_competition()

            if competition.is_league():
                # Process promotion/relegation
                promotion_relegation = self.process_promotion_relegation(
                    competition, league_table
                )

                # Distribute prizes
                prizes = self.distribute_season_prizes(competition, league_table)

                # Determine European qualifiers
                european_qualifiers = self.determine_european_qualifiers(
                    competition, league_table
                )

                # Generate trophy events for winner and runner-up
                if league_table:
                    winner_event = self.generate_trophy_event(
                        career_id, competition, 1,
                        league_table[0].club_id, league_table[0].club_name,
                    )
                    trophy_events.append(winner_event)

                    if len(league_table) > 1:
                        runner_up_event = self.generate_trophy_event(
                            career_id, competition, 2,
                            league_table[1].club_id, league_table[1].club_name,
                        )
                        trophy_events.append(runner_up_event)

        return {
            "previous_season": current_season,
            "next_season": next_season,
            "promotion_relegation": promotion_relegation,
            "prizes": prizes,
            "european_qualifiers": european_qualifiers,
            "trophy_events": trophy_events,
        }


    # =========================================================================
    # Task 17.13: Create cup draw system (randomized seeded)
    # =========================================================================

    def draw_cup_round(
        self,
        competition: Competition,
        round_number: int,
        clubs: List[Dict],
        seeded: bool = True,
    ) -> List[Tuple[Dict, Dict]]:
        """
        Perform a randomized seeded cup draw for a specific round.

        Seeded draws split teams into pots based on reputation:
        - Pot 1 (seeded): Top half by reputation
        - Pot 2 (unseeded): Bottom half by reputation
        Each match pairs one seeded team (home) with one unseeded team (away).

        If unseeded, teams are randomly paired without regard to reputation.

        Args:
            competition: The cup competition
            round_number: The round number being drawn
            clubs: List of club dicts with 'id', 'name', 'reputation' keys
            seeded: Whether to use seeded draw (default: True)

        Returns:
            List of tuples (home_club, away_club) representing the draw

        Raises:
            ValueError: If odd number of clubs or fewer than 2
        """
        if len(clubs) < 2:
            raise ValueError("Need at least 2 clubs for a cup draw")
        if len(clubs) % 2 != 0:
            raise ValueError(
                f"Need even number of clubs for cup draw, got {len(clubs)}"
            )

        draw = []

        if seeded:
            # Sort by reputation descending
            sorted_clubs = sorted(
                clubs, key=lambda c: c.get("reputation", 50), reverse=True
            )

            # Split into seeded (top half) and unseeded (bottom half)
            mid = len(sorted_clubs) // 2
            seeded_clubs = sorted_clubs[:mid]
            unseeded_clubs = sorted_clubs[mid:]

            # Shuffle within pots
            random.shuffle(seeded_clubs)
            random.shuffle(unseeded_clubs)

            # Pair seeded (home) with unseeded (away)
            for i in range(len(seeded_clubs)):
                draw.append((seeded_clubs[i], unseeded_clubs[i]))
        else:
            # Fully random draw
            shuffled = list(clubs)
            random.shuffle(shuffled)

            for i in range(0, len(shuffled), 2):
                draw.append((shuffled[i], shuffled[i + 1]))

        return draw

    def generate_cup_fixtures(
        self,
        competition: Competition,
        draw: List[Tuple[Dict, Dict]],
        round_number: int,
        round_name: str,
        start_date: Optional[datetime] = None,
    ) -> List[Fixture]:
        """
        Generate fixtures from a cup draw.

        Args:
            competition: The cup competition
            draw: List of (home_club, away_club) tuples from draw_cup_round
            round_number: The round number (used as matchday)
            round_name: Human-readable round name (e.g., "Quarter Final")
            start_date: Optional scheduled date for fixtures

        Returns:
            List[Fixture]: Generated fixture objects
        """
        if start_date is None:
            start_date = datetime(competition.season, 1, 15, 20, 0)

        fixtures = []
        for home_club, away_club in draw:
            fixture = Fixture(
                competition_id=competition.id if competition.id else 0,
                home_club_id=home_club["id"],
                away_club_id=away_club["id"],
                matchday=round_number,
                round_name=round_name,
                scheduled_date=start_date,
                status=FixtureStatus.SCHEDULED,
            )
            fixtures.append(fixture)

        return fixtures


    # =========================================================================
    # Task 17.14: Implement player availability checking
    # =========================================================================

    def check_squad_availability(
        self,
        squad_players: List[Dict],
        injuries: List[Dict],
        suspensions: List[Dict],
    ) -> SquadAvailability:
        """
        Check squad availability for a fixture considering injuries and suspensions.

        A player is unavailable if:
        - They have an active injury (status = "active")
        - They are suspended (accumulated yellow cards or red card ban)

        Args:
            squad_players: List of squad player dicts with keys:
                          'id', 'player_id', 'player_name'
            injuries: List of active injury dicts with keys:
                     'player_id', 'injury_type', 'severity', 'recovery_weeks'
            suspensions: List of suspension dicts with keys:
                        'player_id', 'reason', 'matches_remaining'

        Returns:
            SquadAvailability: Availability report
        """
        # Build sets of unavailable player IDs
        injured_player_ids = {inj["player_id"] for inj in injuries}
        suspended_player_ids = {sus["player_id"] for sus in suspensions}
        unavailable_ids = injured_player_ids | suspended_player_ids

        available_players = []
        injured_list = []
        suspended_list = []

        for sp in squad_players:
            player_id = sp["player_id"]

            if player_id in injured_player_ids:
                # Find the injury details
                injury_info = next(
                    (inj for inj in injuries if inj["player_id"] == player_id),
                    None,
                )
                injured_list.append({
                    "player_id": player_id,
                    "player_name": sp.get("player_name", f"Player {player_id}"),
                    "injury_type": injury_info["injury_type"] if injury_info else "Unknown",
                    "severity": injury_info.get("severity", "unknown") if injury_info else "unknown",
                    "recovery_weeks": injury_info.get("recovery_weeks", 0) if injury_info else 0,
                })
            elif player_id in suspended_player_ids:
                # Find the suspension details
                suspension_info = next(
                    (sus for sus in suspensions if sus["player_id"] == player_id),
                    None,
                )
                suspended_list.append({
                    "player_id": player_id,
                    "player_name": sp.get("player_name", f"Player {player_id}"),
                    "reason": suspension_info["reason"] if suspension_info else "Unknown",
                    "matches_remaining": suspension_info.get("matches_remaining", 0) if suspension_info else 0,
                })
            else:
                available_players.append(player_id)

        return SquadAvailability(
            available_players=available_players,
            injured_players=injured_list,
            suspended_players=suspended_list,
            total_squad_size=len(squad_players),
            available_count=len(available_players),
        )
