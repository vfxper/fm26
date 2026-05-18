"""
Match Simulator — Generates realistic match results based on team CA.

Features:
- Poisson-distributed goals based on CA difference
- Home advantage (+15%)
- Match chronology: goals, yellow/red cards, substitutions
- Realistic stats: possession, shots, shots on target
- Uses real player names when available
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class MatchEvent:
    """A single event in the match timeline."""
    minute: int
    event_type: str  # "goal", "yellow_card", "red_card", "substitution", "half_time", "injury"
    team: str  # "home" or "away"
    player_name: str
    description: str


@dataclass
class InjuryEvent:
    """
    A player injury sustained during a match.

    Used both as a record in MatchResult.injuries (for DB persistence
    via the Injury model) and as the source of an injury MatchEvent in
    the visible timeline.

    Severity strings map directly to InjurySeverity enum values:
        "minor"    → 1-2 weeks
        "moderate" → 3-8 weeks
        "severe"   → 9+ weeks
    """
    player_name: str
    injury_type: str
    severity: str  # "minor" | "moderate" | "severe"
    recovery_weeks: int
    match_minute: int
    team: str = ""  # "home" or "away" — useful for the timeline UI
    injury_description: str = ""
    player_id: Optional[int] = None       # populated when known (DB-backed players)
    squad_player_id: Optional[int] = None  # populated for the human-controlled club


@dataclass
class MatchResult:
    """Full result of a simulated match."""
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    events: List[MatchEvent]
    possession_home: int  # percentage
    possession_away: int
    shots_home: int
    shots_away: int
    shots_on_target_home: int
    shots_on_target_away: int
    injuries: List[InjuryEvent] = field(default_factory=list)


class MatchSimulator:
    """
    Simulates a football match based on team CA (Current Ability).
    
    Logic:
    - Base goal expectancy: 1.3 goals per team per match
    - CA advantage: proportional boost (e.g. 160 vs 120 = +33% for stronger team)
    - Home advantage: +15% to home team goal expectancy
    - Goals distributed via Poisson distribution
    - Yellow cards: 2-5 per match
    - Red cards: ~5% chance per team
    - Substitutions: 3 per team (minutes 55-85)
    """

    # Generic player names for when DB has no data
    GENERIC_NAMES = [
        "Иванов", "Петров", "Сидоров", "Козлов", "Новиков",
        "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов",
        "Егоров", "Павлов", "Кузнецов", "Степанов", "Николаев",
        "Орлов", "Андреев", "Макаров", "Никитин", "Захаров",
        "García", "Rodríguez", "Martínez", "López", "González",
        "Silva", "Santos", "Oliveira", "Souza", "Costa",
        "Smith", "Johnson", "Williams", "Brown", "Jones",
        "Müller", "Schmidt", "Schneider", "Fischer", "Weber",
    ]

    # Injury catalogue, grouped roughly by body region.
    # Severity weights determine the share of (Minor / Moderate / Severe).
    # Per spec: Minor = 1-2 weeks, Moderate = 3-8 weeks, Severe = 9+ weeks.
    INJURY_TYPES = [
        # Lower-body, common
        "Растяжение задней поверхности бедра",   # Hamstring strain
        "Растяжение паха",                        # Groin strain
        "Растяжение икроножной мышцы",            # Calf strain
        "Растяжение четырёхглавой мышцы",         # Quadriceps strain
        "Подвернул лодыжку",                      # Ankle sprain
        "Травма колена",                          # Knee injury
        "Перелом плюсневой кости",                # Metatarsal fracture
        "Травма ахиллова сухожилия",              # Achilles
        "Ушиб бедра",                             # Thigh contusion
        # Upper-body / contact
        "Сотрясение",                             # Concussion
        "Перелом носа",                           # Broken nose
        "Травма плеча",                           # Shoulder
        "Ушиб рёбер",                             # Rib contusion
    ]

    # Severity distribution per acceptance criterion 11.1 (60/30/10).
    SEVERITY_WEIGHTS = (
        ("minor", 0.60, (1, 2)),
        ("moderate", 0.30, (3, 8)),
        ("severe", 0.10, (9, 16)),
    )

    def simulate(
        self,
        home_club: str,
        away_club: str,
        home_avg_ca: int,
        away_avg_ca: int,
        home_players: Optional[List[Dict[str, Any]]] = None,
        away_players: Optional[List[Dict[str, Any]]] = None,
        is_player_home: Optional[bool] = None,
        pitch_condition: str = "good",
        match_intensity: float = 1.0,
    ) -> MatchResult:
        """
        Simulate a full match.

        Args:
            home_club: Home team name
            away_club: Away team name
            home_avg_ca: Average CA of home squad
            away_avg_ca: Average CA of away squad
            home_players: Optional list of dicts with 'name', 'ca' and
                          (optional) 'position'.
            away_players: Optional list of dicts with the same keys.
            is_player_home: When True, the human-controlled team is the
                            home side; when False, the away side; when
                            None, both teams use AI-driven substitutions.
                            Substitutions are NEVER auto-generated for the
                            human's team — the player makes them in the UI.
            pitch_condition: One of "good", "soft", "heavy", "waterlogged".
                             Heavier pitches raise injury risk (Req 11.1).
            match_intensity: Multiplier on per-minute injury risk. 1.0 is a
                             standard match; 1.2+ is a derby / cup final.

        Returns:
            MatchResult with score, events, and stats
        """
        # Ensure we have player lists
        if not home_players or len(home_players) < 5:
            home_players = self._generate_generic_squad(home_club, home_avg_ca)
        if not away_players or len(away_players) < 5:
            away_players = self._generate_generic_squad(away_club, away_avg_ca)

        self._is_player_home = is_player_home  # consumed by _generate_substitutions

        # Calculate expected goals
        home_xg, away_xg = self._calculate_xg(home_avg_ca, away_avg_ca)

        # Generate goals via Poisson distribution
        home_score = self._poisson_goals(home_xg)
        away_score = self._poisson_goals(away_xg)

        # Generate all match events
        events: List[MatchEvent] = []

        # Half-time event
        events.append(MatchEvent(
            minute=45,
            event_type="half_time",
            team="",
            player_name="",
            description="Перерыв"
        ))

        # Simulate injuries FIRST so cards/subs can avoid already-injured players.
        # Per Req 11.1 / 11.3: removed from match, recovery timeline set.
        injuries: List[InjuryEvent] = []
        injured_names: set = set()
        self._simulate_injuries(
            injuries, injured_names,
            home_club, away_club,
            home_players, away_players,
            pitch_condition=pitch_condition,
            match_intensity=match_intensity,
        )

        # Add injury events to the timeline.
        for inj in injuries:
            club_name = home_club if inj.team == "home" else away_club
            severity_ru = {
                "minor": "лёгкая",
                "moderate": "средней тяжести",
                "severe": "серьёзная",
            }.get(inj.severity, inj.severity)
            events.append(MatchEvent(
                minute=inj.match_minute,
                event_type="injury",
                team=inj.team,
                player_name=inj.player_name,
                description=(
                    f"⚕ Травма: {inj.player_name} ({club_name}) — "
                    f"{inj.injury_type}, {severity_ru} ({inj.recovery_weeks} нед.)"
                )
            ))

        # Build active rosters that exclude injured players for the
        # remainder of the match.  Cards, subs and goal scorers are picked
        # only from these lists so injured players cannot keep playing.
        home_active = [p for p in home_players if p.get("name") not in injured_names]
        away_active = [p for p in away_players if p.get("name") not in injured_names]
        # Safety net: never leave a side with fewer than 5 outfield names to
        # pick from for events — fall back to the full list in that case.
        if len(home_active) < 5:
            home_active = home_players
        if len(away_active) < 5:
            away_active = away_players

        # Generate goals
        self._generate_goals(events, home_score, away_score,
                             home_club, away_club, home_active, away_active)

        # Generate yellow cards (2-5 per match)
        self._generate_yellow_cards(events, home_club, away_club,
                                    home_active, away_active)

        # Generate red cards (~5% chance per team)
        self._generate_red_cards(events, home_club, away_club,
                                 home_active, away_active)

        # Generate substitutions (3 per AI team).  Forced substitutions
        # for injuries on the AI side are already implicitly modelled by
        # _generate_substitutions picking from `*_active`.
        self._generate_substitutions(events, home_club, away_club,
                                     home_active, away_active)

        # Sort events by minute
        events.sort(key=lambda e: (e.minute, e.event_type != "half_time"))

        # Calculate stats
        possession_home, possession_away = self._calculate_possession(
            home_avg_ca, away_avg_ca)
        shots_home, shots_away = self._calculate_shots(
            home_score, away_score, home_xg, away_xg)
        sot_home = min(shots_home, home_score + random.randint(1, 4))
        sot_away = min(shots_away, away_score + random.randint(1, 4))

        return MatchResult(
            home_team=home_club,
            away_team=away_club,
            home_score=home_score,
            away_score=away_score,
            events=events,
            possession_home=possession_home,
            possession_away=possession_away,
            shots_home=shots_home,
            shots_away=shots_away,
            shots_on_target_home=sot_home,
            shots_on_target_away=sot_away,
            injuries=injuries,
        )

    # ─── Injuries ────────────────────────────────────────────────────────────

    # Per-match base rate.  Aim at ~1 injury per 8-10 matches at default
    # intensity / good pitch / squad of 22 — calibrated by attribute
    # multipliers that swing the realised rate ±60%.
    _BASE_INJURY_RATE = 0.006   # per player per match

    _PITCH_RISK = {
        "good": 1.00,
        "soft": 1.15,
        "heavy": 1.35,
        "waterlogged": 1.55,
    }

    def _compute_injury_probability(
        self,
        player: Dict[str, Any],
        match_intensity: float,
        pitch_condition: str,
    ) -> float:
        """
        Per-match injury probability for a single player.

        Mirrors Requirement 11.1: based on player attributes (bravery,
        stamina, strength), match intensity and pitch condition.

        Each attribute is normalised around 10 (the league-average) and
        contributes a small ± multiplier:
            • Higher stamina  → lower risk (better fitness, fewer mistakes when tired)
            • Higher strength → lower risk (less likely to get bumped off the ball)
            • Higher bravery  → slightly higher risk (more 50/50 challenges)
            • Higher CA reflects overall conditioning, small protective effect
            • Injury-prone flag adds a flat 15% (Req 11.9)
        """
        stamina  = self._safe_attr(player, "stamina", default=10)
        strength = self._safe_attr(player, "strength", default=10)
        bravery  = self._safe_attr(player, "bravery", default=10)

        stamina_factor  = max(0.6, 1.0 - (stamina  - 10) * 0.025)
        strength_factor = max(0.6, 1.0 - (strength - 10) * 0.020)
        bravery_factor  = min(1.4, 1.0 + (bravery  - 10) * 0.015)

        # CA is in the ~50-180 range; treat 120 as neutral.
        ca = max(50, int(player.get("ca", 100) or 100))
        ca_factor = max(0.7, 1.0 - (ca - 120) * 0.0015)

        pitch_factor = self._PITCH_RISK.get(
            (pitch_condition or "good").lower(), 1.0
        )

        prone_factor = 1.15 if player.get("is_injury_prone") else 1.0

        prob = (
            self._BASE_INJURY_RATE
            * stamina_factor * strength_factor * bravery_factor * ca_factor
            * max(0.5, float(match_intensity))
            * pitch_factor
            * prone_factor
        )
        # Clamp to sane bounds — never zero (freak injuries happen) and
        # never above ~3% per match (otherwise we'd lose half a squad
        # every game).
        return max(0.0005, min(0.030, prob))

    @staticmethod
    def _safe_attr(player: Dict[str, Any], key: str, default: int = 10) -> int:
        v = player.get(key)
        try:
            return int(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _roll_injury_severity(self) -> tuple:
        """Return (severity_label, recovery_weeks) per the design distribution."""
        r = random.random()
        cumulative = 0.0
        for label, weight, (mn, mx) in self.SEVERITY_WEIGHTS:
            cumulative += weight
            if r <= cumulative:
                return label, random.randint(mn, mx)
        # Fallback (only reached on float rounding)
        label, _w, (mn, mx) = self.SEVERITY_WEIGHTS[-1]
        return label, random.randint(mn, mx)

    def _simulate_injuries(
        self,
        injuries: List[InjuryEvent],
        injured_names: set,
        home_club: str,
        away_club: str,
        home_players: List[Dict[str, Any]],
        away_players: List[Dict[str, Any]],
        *,
        pitch_condition: str,
        match_intensity: float,
    ) -> None:
        """
        Roll an injury check for every player on both rosters.

        Outputs are written into ``injuries`` (full InjuryEvent records,
        ready for DB persistence) and ``injured_names`` (a name-only set
        used downstream to drop players from cards/subs/scoring picks
        for the rest of the match).

        Acceptance criteria covered here:
            11.1 — risk depends on bravery, stamina, strength, intensity,
                   pitch condition.
            11.2 — three severity buckets (Minor / Moderate / Severe).
            11.3 — injured player is removed from the match (handled by
                   the caller via `injured_names`); recovery timeline is
                   set via recovery_weeks on the InjuryEvent.
        """
        for team_label, club_name, players in (
            ("home", home_club, home_players),
            ("away", away_club, away_players),
        ):
            for player in players:
                prob = self._compute_injury_probability(
                    player, match_intensity, pitch_condition
                )
                if random.random() >= prob:
                    continue

                name = player.get("name") or "Unknown"
                if name in injured_names:
                    # Don't injure the same player twice in one game.
                    continue
                injured_names.add(name)

                severity, recovery_weeks = self._roll_injury_severity()
                injury_type = self._pick_injury_type(player.get("position"))
                # Time of injury — biased slightly later in the match
                # because fatigue accumulates.
                minute = max(1, min(95, int(random.triangular(5, 90, 65))))

                injuries.append(InjuryEvent(
                    player_name=name,
                    injury_type=injury_type,
                    severity=severity,
                    recovery_weeks=recovery_weeks,
                    match_minute=minute,
                    team=team_label,
                    injury_description=(
                        f"{injury_type} sustained in {minute}' "
                        f"({club_name})"
                    ),
                    player_id=player.get("player_id") or player.get("id"),
                    squad_player_id=player.get("squad_player_id"),
                ))

    def _pick_injury_type(self, position: Optional[str]) -> str:
        """Pick an injury type.  Goalkeepers skew toward upper-body issues."""
        pos = (position or "").upper()
        if "GK" in pos:
            # Mostly hands / shoulders / head for keepers.
            gk_pool = [
                "Травма плеча",
                "Сотрясение",
                "Перелом носа",
                "Травма колена",
                "Подвернул лодыжку",
            ]
            return random.choice(gk_pool)
        return random.choice(self.INJURY_TYPES)

    # ─── XG / score helpers (existing) ───────────────────────────────────────

    def _calculate_xg(self, home_ca: int, away_ca: int) -> tuple:
        """Calculate expected goals for each team based on CA difference."""
        base_xg = 1.3  # Base goal expectancy per team

        # Avoid division by zero
        if home_ca <= 0:
            home_ca = 100
        if away_ca <= 0:
            away_ca = 100

        avg_ca = (home_ca + away_ca) / 2

        # CA ratio determines goal boost
        # If home CA is 160 and away is 120, ratio = 160/140 = 1.14 -> +14%
        home_ratio = home_ca / avg_ca
        away_ratio = away_ca / avg_ca

        # Home advantage: +15%
        home_xg = base_xg * home_ratio * 1.15
        away_xg = base_xg * away_ratio * 0.85

        # Add some randomness (±10%)
        home_xg *= random.uniform(0.9, 1.1)
        away_xg *= random.uniform(0.9, 1.1)

        # Clamp to reasonable range
        home_xg = max(0.4, min(4.0, home_xg))
        away_xg = max(0.3, min(3.5, away_xg))

        return home_xg, away_xg

    def _poisson_goals(self, expected: float) -> int:
        """Generate goals using Poisson distribution."""
        goals = 0
        p = random.random()
        cumulative = 0.0
        for k in range(9):  # Max 8 goals
            prob = (expected ** k) * math.exp(-expected) / math.factorial(k)
            cumulative += prob
            if p <= cumulative:
                goals = k
                break
        else:
            goals = 8
        return goals

    def _generate_goals(
        self,
        events: List[MatchEvent],
        home_score: int,
        away_score: int,
        home_club: str,
        away_club: str,
        home_players: List[Dict],
        away_players: List[Dict],
    ):
        """Generate goal events with scorers and minutes."""
        total_goals = home_score + away_score
        if total_goals == 0:
            return

        # Generate unique minutes for goals
        available_minutes = list(range(1, 91))
        # Add injury time goals occasionally
        if random.random() < 0.3:
            available_minutes.extend([91, 92, 93])
        if random.random() < 0.15:
            available_minutes.extend([45, 46, 47])

        goal_minutes = sorted(random.sample(
            available_minutes, min(total_goals, len(available_minutes))
        ))

        # Distribute goals between teams
        # Shuffle assignment to make it more realistic
        goal_assignments = (["home"] * home_score + ["away"] * away_score)
        random.shuffle(goal_assignments)

        for i, minute in enumerate(goal_minutes):
            if i >= len(goal_assignments):
                break
            team = goal_assignments[i]
            club_name = home_club if team == "home" else away_club
            players = home_players if team == "home" else away_players

            # Pick scorer - weight by CA (better players score more)
            scorer = self._pick_scorer(players)

            events.append(MatchEvent(
                minute=minute,
                event_type="goal",
                team=team,
                player_name=scorer,
                description=f"⚽ Гол! {scorer} ({club_name})"
            ))

    def _generate_yellow_cards(
        self,
        events: List[MatchEvent],
        home_club: str,
        away_club: str,
        home_players: List[Dict],
        away_players: List[Dict],
    ):
        """Generate yellow card events."""
        num_yellows = random.randint(2, 5)
        for _ in range(num_yellows):
            team = random.choice(["home", "away"])
            club_name = home_club if team == "home" else away_club
            players = home_players if team == "home" else away_players
            player = random.choice(players)["name"]
            minute = random.randint(5, 89)

            events.append(MatchEvent(
                minute=minute,
                event_type="yellow_card",
                team=team,
                player_name=player,
                description=f"🟨 Жёлтая карточка: {player} ({club_name})"
            ))

    def _generate_red_cards(
        self,
        events: List[MatchEvent],
        home_club: str,
        away_club: str,
        home_players: List[Dict],
        away_players: List[Dict],
    ):
        """Generate red card events (~5% chance per team)."""
        for team in ["home", "away"]:
            if random.random() < 0.05:
                club_name = home_club if team == "home" else away_club
                players = home_players if team == "home" else away_players
                player = random.choice(players)["name"]
                minute = random.randint(25, 88)

                events.append(MatchEvent(
                    minute=minute,
                    event_type="red_card",
                    team=team,
                    player_name=player,
                    description=f"🟥 Красная карточка: {player} ({club_name})"
                ))

    def _generate_substitutions(
        self,
        events: List[MatchEvent],
        home_club: str,
        away_club: str,
        home_players: List[Dict],
        away_players: List[Dict],
    ):
        """Generate substitution events (3 per AI team, minutes 55-85).

        Substitutions are skipped for the human-controlled team — the
        player makes them in the UI; the AI never makes lineup decisions
        on their behalf.
        """
        is_player_home = getattr(self, "_is_player_home", None)
        for team in ["home", "away"]:
            # Skip the human's team: they will run subs themselves.
            if (is_player_home is True and team == "home") or \
               (is_player_home is False and team == "away"):
                continue

            club_name = home_club if team == "home" else away_club
            players = home_players if team == "home" else away_players

            if len(players) < 6:
                continue

            # Pick 3 substitution minutes
            sub_minutes = sorted(random.sample(range(55, 86), 3))

            # Pick players going out and coming in
            available = list(players)
            random.shuffle(available)
            subs_out = available[:3]
            subs_in = available[3:6] if len(available) >= 6 else available[:3]

            for i in range(min(3, len(subs_out), len(subs_in))):
                player_out = subs_out[i]["name"]
                player_in = subs_in[i]["name"]
                events.append(MatchEvent(
                    minute=sub_minutes[i],
                    event_type="substitution",
                    team=team,
                    player_name=f"{player_out} → {player_in}",
                    description=f"🔄 Замена: {player_out} → {player_in} ({club_name})"
                ))

    def _calculate_possession(self, home_ca: int, away_ca: int) -> tuple:
        """Calculate possession percentages based on CA."""
        total = home_ca + away_ca if (home_ca + away_ca) > 0 else 280
        base_home = (home_ca / total) * 100
        # Add randomness (±5%)
        possession_home = int(base_home + random.randint(-5, 5))
        possession_home = max(30, min(70, possession_home))
        possession_away = 100 - possession_home
        return possession_home, possession_away

    def _calculate_shots(
        self, home_score: int, away_score: int,
        home_xg: float, away_xg: float
    ) -> tuple:
        """Calculate total shots based on goals and xG."""
        # More xG = more shots attempted
        shots_home = home_score + random.randint(4, 10) + int(home_xg)
        shots_away = away_score + random.randint(3, 9) + int(away_xg)
        return shots_home, shots_away

    @staticmethod
    def _is_goalkeeper(player: Dict) -> bool:
        """A player is a GK if their position string contains 'GK'."""
        pos = (player.get("position") or "").upper()
        return "GK" in pos

    def _pick_scorer(self, players: List[Dict]) -> str:
        """Pick a goal scorer weighted by CA. Goalkeepers are excluded —
        a keeper scoring from open play would be a bug, not a feature."""
        if not players:
            return random.choice(self.GENERIC_NAMES)

        outfield = [p for p in players if not self._is_goalkeeper(p)]
        if not outfield:
            outfield = players  # fallback if no positions tagged

        # Weight by CA, biased towards strikers and attacking mids.
        weights = []
        for p in outfield:
            ca = p.get("ca", 100)
            pos = (p.get("position") or "").upper()
            if any(tag in pos for tag in ("ST", "AM", "FW")):
                w = ca * 1.6
            elif any(tag in pos for tag in (" M", "M ", "MC", "MR", "ML")):
                w = ca * 1.0
            else:
                w = ca * 0.4
            weights.append(max(1.0, w))

        total_weight = sum(weights)
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return outfield[i]["name"]

        return outfield[-1]["name"]

    def _generate_generic_squad(self, club_name: str, avg_ca: int) -> List[Dict]:
        """Generate a generic squad when no real players are available."""
        squad = []
        names = random.sample(self.GENERIC_NAMES, min(16, len(self.GENERIC_NAMES)))
        for i, name in enumerate(names):
            # Vary CA around the average
            ca = avg_ca + random.randint(-20, 20)
            squad.append({"name": name, "ca": max(50, ca)})
        return squad

    def to_dict(self, result: MatchResult) -> Dict[str, Any]:
        """Convert MatchResult to a JSON-serializable dict."""
        timeline = []
        for ev in result.events:
            entry = {
                "minute": ev.minute,
                "type": ev.event_type,
                "team": ev.team,
                "player": ev.player_name,
                "team_name": result.home_team if ev.team == "home" else result.away_team,
                "description": ev.description,
            }
            # For substitutions, split player names
            if ev.event_type == "substitution" and " → " in ev.player_name:
                parts = ev.player_name.split(" → ")
                entry["player_out"] = parts[0]
                entry["player_in"] = parts[1]
                entry["player"] = parts[0]
            timeline.append(entry)

        return {
            "home_team": result.home_team,
            "away_team": result.away_team,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "timeline": timeline,
            "possession_home": result.possession_home,
            "possession_away": result.possession_away,
            "shots_home": result.shots_home,
            "shots_away": result.shots_away,
            "shots_on_target_home": result.shots_on_target_home,
            "shots_on_target_away": result.shots_on_target_away,
            "injuries": [
                {
                    "player_name": inj.player_name,
                    "team": inj.team,
                    "team_name": result.home_team if inj.team == "home" else result.away_team,
                    "injury_type": inj.injury_type,
                    "severity": inj.severity,
                    "recovery_weeks": inj.recovery_weeks,
                    "match_minute": inj.match_minute,
                    "description": inj.injury_description,
                    "player_id": inj.player_id,
                    "squad_player_id": inj.squad_player_id,
                }
                for inj in result.injuries
            ],
        }
