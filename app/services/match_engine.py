"""
MatchEngine — Simulates a single football match and produces a result + text commentary.

Given two clubs (home and away), this engine fetches the top 11 players from each squad,
computes team strength (average CA), applies a small home advantage, and then runs a
minute-by-minute probabilistic simulation across 90 minutes. It returns a structured
``MatchResult`` containing the score, statistics, and a list of ``MatchEvent`` objects
that can be rendered as text commentary.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.position_fit import assign_roles, fit, role_zone_of


# ─── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class MatchEvent:
    """A single event that occurred during the match."""
    minute: int
    event_type: str  # "goal", "yellow_card", "red_card", "substitution", "miss", "save"
    team: str        # "home" or "away"
    player_name: str
    description: str


@dataclass
class MatchResult:
    """Final result of a simulated match."""
    home_score: int
    away_score: int
    events: List[MatchEvent] = field(default_factory=list)
    home_possession: int = 50  # 0-100
    away_possession: int = 50
    home_shots: int = 0
    away_shots: int = 0
    home_shots_on_target: int = 0
    away_shots_on_target: int = 0
    home_team_name: str = ""
    away_team_name: str = ""


# ─── Tactic-driven match modifiers ─────────────────────────────────────────────
# Returned tuple: (own_shot_mult, opp_shot_mult, own_conv_mult, opp_conv_mult)
# where conv = conversion rate (probability that a shot on target becomes goal).
# These multipliers are applied to the side controlled by the player.

_MENTALITY_MATCH_MODIFIERS = {
    # very_defensive: 0.7x own shots, 0.65x opp shots, +5% own keeper saves
    "very_defensive": (0.70, 0.65, 0.85, 0.85),
    "defensive":      (0.85, 0.80, 0.95, 0.95),
    "balanced":       (1.00, 1.00, 1.00, 1.00),
    "attacking":      (1.20, 1.10, 1.10, 1.05),
    "very_attacking": (1.45, 1.30, 1.20, 1.15),
    # legacy aliases
    "cautious":       (0.92, 0.90, 0.97, 0.97),
    "positive":       (1.10, 1.05, 1.05, 1.02),
}


# ─── Fatigue: per-minute drain rate ─────────────────────────────────────────
# `team_fatigue` starts at 1.0 and is multiplied by ``(1 - drain)`` each
# minute. Drain depends on tempo + pressing — pushing both to 100% bleeds
# stamina ~3x faster than the balanced default.
#
# Derived multiplier `fatigue_factor = team_fatigue ** 0.6` is applied to:
#   * shot probability
#   * conversion (probability that a shot on target is a goal)
# so a tired team is both less dangerous AND less clinical.
#
# A balanced team finishes the match around 0.92 (≈8% drop in late game).
# A very_attacking + 100% press team can drop to ~0.78 (22% drop).
_FATIGUE_BASE_PER_MIN = 0.0009   # 90 minutes * 0.0009 ≈ 8.1% loss


def _fatigue_drain_per_min(mentality: str, pressing_n: int, tempo: str) -> float:
    """Return the per-minute fatigue drain rate for a team."""
    rate = _FATIGUE_BASE_PER_MIN
    m = (mentality or "balanced").lower()
    if m == "very_attacking":
        rate *= 1.6
    elif m == "attacking" or m == "positive":
        rate *= 1.25
    elif m == "very_defensive":
        rate *= 0.8
    elif m == "defensive" or m == "cautious":
        rate *= 0.9
    # pressing — 0..100 already extracted by _tactic_match_modifiers caller
    if pressing_n >= 90:
        rate *= 1.7
    elif pressing_n >= 70:
        rate *= 1.35
    elif pressing_n >= 30:
        rate *= 1.10
    elif pressing_n <= 5:
        rate *= 0.7
    # tempo
    t = (tempo or "normal").lower()
    if t in ("high", "fast", "very_high"):
        rate *= 1.30
    elif t in ("low", "slow", "very_low"):
        rate *= 0.80
    return rate


def _pressing_to_int(pressing: str) -> int:
    p = str(pressing or "medium").lower()
    if p in ("off", "none", "0"):
        return 0
    if p == "low":
        return 25
    if p == "medium":
        return 50
    if p == "high":
        return 75
    if p == "extreme":
        return 100
    if p.isdigit():
        return max(0, min(100, int(p)))
    return 50


def _tactic_match_modifiers(mentality: str, pressing: str) -> tuple:
    """Return (own_shot, opp_shot, own_conv, opp_conv) multipliers for the
    player-controlled team."""
    base = _MENTALITY_MATCH_MODIFIERS.get(
        (mentality or "balanced").lower(),
        (1.0, 1.0, 1.0, 1.0),
    )
    own_shot, opp_shot, own_conv, opp_conv = base

    # Pressing modifiers — high press generates more chances at the
    # cost of more counters. Off press = the opposite.
    n = _pressing_to_int(pressing)
    if n == 0:
        own_shot *= 0.92
        opp_shot *= 1.10
    elif n <= 30:
        own_shot *= 0.98
        opp_shot *= 1.02
    elif n <= 70:
        pass  # neutral
    elif n <= 90:
        own_shot *= 1.10
        opp_shot *= 1.08
    else:
        own_shot *= 1.20
        opp_shot *= 1.20

    return (own_shot, opp_shot, own_conv, opp_conv)


# ─── MatchEngine ──────────────────────────────────────────────────────────────


class MatchEngine:
    """Simulates a single football match between two clubs."""

    DEFAULT_TEAM_CA = 100

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Public API ───────────────────────────────────────────────────────────

    async def simulate_match(
        self,
        home_club_id: int,
        away_club_id: int,
        home_club_name: str,
        away_club_name: str,
        is_player_home: Optional[bool] = None,
        career_id: Optional[int] = None,
    ) -> MatchResult:
        """Simulate a full 90-minute match in one shot.

        Internally this just runs the first half, then the second half
        (no manual substitutions — the AI side gets its random subs in
        the 60-75 minute window as before). The two-phase API is used
        when the player wants a half-time pause:

            state = await engine.simulate_first_half(...)
            # ... user makes substitutions ...
            result = await engine.simulate_second_half(state, subs)
        """
        state = await self.simulate_first_half(
            home_club_id, away_club_id,
            home_club_name, away_club_name,
            is_player_home=is_player_home,
            career_id=career_id,
        )
        return await self.simulate_second_half(state, subs=None)

    async def simulate_first_half(
        self,
        home_club_id: int,
        away_club_id: int,
        home_club_name: str,
        away_club_name: str,
        is_player_home: Optional[bool] = None,
        career_id: Optional[int] = None,
    ) -> dict:
        """Simulate minutes 1..45 and return a state dict that can be
        passed to ``simulate_second_half`` to finish the game.

        The state dict is JSON-serialisable — that's important because
        the route layer persists it in ``match_sessions.state_json``.
        """
        state = await self._prepare_match_state(
            home_club_id, away_club_id,
            home_club_name, away_club_name,
            is_player_home, career_id,
        )
        # Run minutes 1..45.
        self._simulate_minute_range(state, start=1, end=45)
        state["current_minute"] = 45
        state["phase"] = "halftime"
        return state

    async def simulate_second_half(
        self,
        state: dict,
        subs: Optional[List[dict]] = None,
    ) -> MatchResult:
        """Apply substitutions (if any), simulate 46..90, return the
        final ``MatchResult``.

        ``subs`` is a list of ``{"team": "home"|"away", "out_name": str,
        "in_player": {"name", "position", "ca", "role_zone"}}``.
        """
        if state.get("phase") != "halftime":
            raise ValueError(
                f"simulate_second_half called in phase {state.get('phase')!r}; "
                "expected 'halftime'."
            )

        if subs:
            for s in subs:
                self._apply_substitution(state, s)

        self._simulate_minute_range(state, start=46, end=90)
        state["phase"] = "finished"
        return self._finalise(state)

    # ─── Internal: state setup ────────────────────────────────────────────────

    async def _prepare_match_state(
        self,
        home_club_id: int,
        away_club_id: int,
        home_club_name: str,
        away_club_name: str,
        is_player_home: Optional[bool],
        career_id: Optional[int],
    ) -> dict:
        """Build the per-match state dict used by simulate_minute_range.

        Everything in here used to be the prologue of `simulate_match`.
        It is JSON-friendly so the state can survive a roundtrip
        through the database between halves.
        """
        own_shot_mult = own_conv_mult = 1.0
        opp_shot_mult = opp_conv_mult = 1.0
        own_drain = opp_drain = _FATIGUE_BASE_PER_MIN
        if career_id is not None and is_player_home is not None:
            try:
                r = await self.session.execute(text(
                    "SELECT mentality, pressing, tempo FROM career_tactics "
                    "WHERE career_id = :c"
                ), {"c": career_id})
                row = r.fetchone()
                if row:
                    ment = (row[0] or "balanced").lower()
                    press = row[1] or "medium"
                    tempo = (row[2] if len(row) > 2 else None) or "normal"
                    own_shot_mult, opp_shot_mult, own_conv_mult, opp_conv_mult = (
                        _tactic_match_modifiers(ment, press)
                    )
                    own_drain = _fatigue_drain_per_min(
                        ment, _pressing_to_int(press), tempo
                    )
            except Exception:
                pass

        home_players = assign_roles(
            await self._get_top_players(home_club_id, limit=11)
        )
        away_players = assign_roles(
            await self._get_top_players(away_club_id, limit=11)
        )

        home_strength = self._effective_team_ca(home_players) + 5
        away_strength = self._effective_team_ca(away_players)

        home_possession = max(35, min(70, int(50 + (home_strength - away_strength) * 1.5)))

        if is_player_home is True:
            home_shot_mult = own_shot_mult; home_conv_mult = own_conv_mult
            away_shot_mult = opp_shot_mult; away_conv_mult = opp_conv_mult
            home_drain = own_drain; away_drain = opp_drain
        elif is_player_home is False:
            home_shot_mult = opp_shot_mult; home_conv_mult = opp_conv_mult
            away_shot_mult = own_shot_mult; away_conv_mult = own_conv_mult
            home_drain = opp_drain; away_drain = own_drain
        else:
            home_shot_mult = home_conv_mult = 1.0
            away_shot_mult = away_conv_mult = 1.0
            home_drain = away_drain = _FATIGUE_BASE_PER_MIN

        # Bench: players ranked 12..20 by CA, also assigned role_zones
        # so the engine can pick replacements correctly. Only computed
        # for the player's side because AI auto-subs are abstract.
        home_bench = await self._get_top_players(home_club_id, limit=20)
        home_bench = [p for p in home_bench[11:]] if len(home_bench) > 11 else []
        away_bench = await self._get_top_players(away_club_id, limit=20)
        away_bench = [p for p in away_bench[11:]] if len(away_bench) > 11 else []

        return {
            "phase": "first_half",
            "current_minute": 0,
            "career_id": career_id,
            "is_player_home": is_player_home,
            "home_club_id": home_club_id,
            "away_club_id": away_club_id,
            "home_club_name": home_club_name,
            "away_club_name": away_club_name,
            "home_players": home_players,
            "away_players": away_players,
            "home_bench": home_bench,
            "away_bench": away_bench,
            "home_strength": home_strength,
            "away_strength": away_strength,
            "home_possession": home_possession,
            "away_possession": 100 - home_possession,
            "home_score": 0, "away_score": 0,
            "home_shots": 0, "away_shots": 0,
            "home_sot": 0, "away_sot": 0,
            "home_fatigue": 1.0, "away_fatigue": 1.0,
            "home_shot_mult": home_shot_mult, "home_conv_mult": home_conv_mult,
            "away_shot_mult": away_shot_mult, "away_conv_mult": away_conv_mult,
            "home_drain": home_drain, "away_drain": away_drain,
            "events": [],
            "subs_made": {"home": 0, "away": 0},
            # Track who was subbed off so the client can show "73' Vinicius → Endrick".
            "sub_log": [],
        }

    # ─── Internal: minute loop ────────────────────────────────────────────────

    def _simulate_minute_range(self, state: dict, *, start: int, end: int) -> None:
        """Simulate minutes [start..end] in-place on ``state``."""
        events: List[MatchEvent] = state["events"] if isinstance(state["events"], list) else []
        # Convert previously-serialised events back into dataclasses so
        # we can keep appending. (When state has just been built this
        # is a no-op — the list is already empty/dataclass.)
        if events and isinstance(events[0], dict):
            events = [MatchEvent(**e) for e in events]
        state["events"] = events

        home_players = state["home_players"]
        away_players = state["away_players"]
        home_strength = state["home_strength"]
        away_strength = state["away_strength"]
        home_shot_mult = state["home_shot_mult"]
        home_conv_mult = state["home_conv_mult"]
        away_shot_mult = state["away_shot_mult"]
        away_conv_mult = state["away_conv_mult"]
        home_drain = state["home_drain"]
        away_drain = state["away_drain"]
        home_fatigue = state["home_fatigue"]
        away_fatigue = state["away_fatigue"]

        is_player_home = state.get("is_player_home")
        home_club_name = state["home_club_name"]
        away_club_name = state["away_club_name"]

        for minute in range(start, end + 1):
            # Half-time recovery for the home/away teams.
            if minute == 46:
                home_fatigue = min(1.0, home_fatigue + 0.01)
                away_fatigue = min(1.0, away_fatigue + 0.01)
            home_fatigue *= (1.0 - home_drain)
            away_fatigue *= (1.0 - away_drain)
            home_ff = home_fatigue ** 0.6
            away_ff = away_fatigue ** 0.6

            # Home shot.
            if random.random() < 0.05 * (home_strength / 100) * home_shot_mult * home_ff:
                state["home_shots"] += 1
                if random.random() < 0.4:
                    state["home_sot"] += 1
                    if random.random() < 0.25 * home_conv_mult * home_ff:
                        state["home_score"] += 1
                        scorer = self._pick_outfield(home_players)
                        events.append(MatchEvent(
                            minute=minute, event_type="goal", team="home",
                            player_name=scorer["name"],
                            description=f"⚽ Гол! {scorer['name']} забивает за {home_club_name}!",
                        ))
                    else:
                        # Save: emit only ~30% of the time so the
                        # timeline isn't dominated by routine GK work.
                        if random.random() < 0.30:
                            gk = self._pick_goalkeeper(away_players)
                            events.append(MatchEvent(
                                minute=minute, event_type="save", team="away",
                                player_name=gk["name"],
                                description=f"🧤 Сейв: {gk['name']}",
                            ))
                # Wide shots are almost always noise. Drop them entirely
                # from the timeline — keep them only in shots count.

            # Away shot.
            if random.random() < 0.05 * (away_strength / 100) * away_shot_mult * away_ff:
                state["away_shots"] += 1
                if random.random() < 0.4:
                    state["away_sot"] += 1
                    if random.random() < 0.25 * away_conv_mult * away_ff:
                        state["away_score"] += 1
                        scorer = self._pick_outfield(away_players)
                        events.append(MatchEvent(
                            minute=minute, event_type="goal", team="away",
                            player_name=scorer["name"],
                            description=f"⚽ Гол! {scorer['name']} забивает за {away_club_name}!",
                        ))
                    else:
                        if random.random() < 0.30:
                            gk = self._pick_goalkeeper(home_players)
                            events.append(MatchEvent(
                                minute=minute, event_type="save", team="home",
                                player_name=gk["name"],
                                description=f"🧤 Сейв: {gk['name']}",
                            ))
                # Wide shots dropped from timeline (counted in stats only).

            # Yellow card (rare).
            if random.random() < 0.005:
                team = "home" if random.random() < 0.5 else "away"
                roster = home_players if team == "home" else away_players
                if roster:
                    player = random.choice(roster)
                    events.append(MatchEvent(
                        minute=minute, event_type="yellow_card", team=team,
                        player_name=player["name"],
                        description=f"🟨 Жёлтая карточка: {player['name']}",
                    ))

            # AI-side substitutions (60/70/75). The human team is left
            # alone — its subs come through the explicit `subs`
            # parameter on simulate_second_half. When the player asked
            # for a full-90 simulation though (no halftime pause), we
            # also auto-sub their team here so they're not missing out
            # on fresh legs.
            if minute in (60, 70, 75) and random.random() < 0.5:
                allowed_teams: list[str] = []
                if is_player_home is None or is_player_home is True:
                    allowed_teams.append("away")
                if is_player_home is None or is_player_home is False:
                    allowed_teams.append("home")
                # When auto-running both halves in one go, also sub for
                # the human side automatically.
                if state.get("auto_subs_for_player"):
                    if is_player_home is True and "home" not in allowed_teams:
                        allowed_teams.append("home")
                    if is_player_home is False and "away" not in allowed_teams:
                        allowed_teams.append("away")
                if not allowed_teams:
                    continue
                team = random.choice(allowed_teams)
                club_name = home_club_name if team == "home" else away_club_name
                events.append(MatchEvent(
                    minute=minute, event_type="substitution", team=team,
                    player_name="",
                    description=f"🔄 Замена: {club_name}",
                ))
                if state.get("auto_subs_for_player") and (
                    (team == "home" and is_player_home is True)
                    or (team == "away" and is_player_home is False)
                ):
                    self._auto_sub_player_team(state, team, minute)

        state["home_fatigue"] = home_fatigue
        state["away_fatigue"] = away_fatigue
        state["current_minute"] = end
        state["events"] = events

    # ─── Internal: substitutions ──────────────────────────────────────────────

    def _apply_substitution(self, state: dict, sub: dict) -> None:
        """Replace a starter with a bench player for the human side.
        Validates ``subs_made[team] < 5`` and that the in-player is on
        the bench. Fails silently if the request is invalid (the route
        layer is responsible for surfacing errors)."""
        team = sub.get("team")
        if team not in ("home", "away"):
            return
        if state["subs_made"][team] >= 5:
            return

        starters_key = f"{team}_players"
        bench_key = f"{team}_bench"
        starters = state[starters_key]
        bench = state[bench_key]

        out_name = (sub.get("out_name") or "").strip()
        in_pl = sub.get("in_player") or {}

        out_idx = next((i for i, p in enumerate(starters)
                        if p.get("name") == out_name), None)
        if out_idx is None:
            return
        if not in_pl.get("name"):
            return
        # Inherit the role_zone of the player going off so the engine's
        # picker keeps weighting the new player into the same role.
        replaced = starters[out_idx]
        in_pl.setdefault("role_zone", replaced.get("role_zone"))

        # Remove from bench if present, otherwise accept any provided dict.
        bench[:] = [p for p in bench if p.get("name") != in_pl.get("name")]
        starters[out_idx] = in_pl
        state["subs_made"][team] += 1
        state.setdefault("events", []).append(MatchEvent(
            minute=state.get("current_minute", 45),
            event_type="substitution", team=team,
            player_name=in_pl.get("name", ""),
            description=(
                f"🔄 {team.upper()}: {out_name} → {in_pl.get('name', '')}"
            ),
        ))
        state.setdefault("sub_log", []).append({
            "minute": state.get("current_minute", 45),
            "team": team, "out": out_name, "in": in_pl.get("name", ""),
        })

    def _auto_sub_player_team(self, state: dict, team: str, minute: int) -> None:
        """Pick the most-tired non-GK starter and replace them with the
        best CA bench player of the same zone."""
        if state["subs_made"][team] >= 5:
            return
        starters = state[f"{team}_players"]
        bench = state[f"{team}_bench"]
        if not bench:
            return
        candidates = [p for p in starters if p.get("role_zone") != "GK"]
        if not candidates:
            return
        out_pl = min(candidates, key=lambda p: p.get("ca") or 100)
        zone = out_pl.get("role_zone") or role_zone_of(out_pl.get("position", ""))
        same_zone = [p for p in bench if role_zone_of(p.get("position", "")) == zone]
        in_pl = (max(same_zone, key=lambda p: p.get("ca") or 0)
                 if same_zone else bench[0])
        self._apply_substitution(state, {
            "team": team, "out_name": out_pl["name"], "in_player": in_pl,
        })

    # ─── Internal: finalise ───────────────────────────────────────────────────

    def _finalise(self, state: dict) -> MatchResult:
        evs = state["events"]
        if evs and isinstance(evs[0], dict):
            evs = [MatchEvent(**e) for e in evs]
        return MatchResult(
            home_score=state["home_score"], away_score=state["away_score"],
            events=evs,
            home_possession=state["home_possession"],
            away_possession=state["away_possession"],
            home_shots=state["home_shots"], away_shots=state["away_shots"],
            home_shots_on_target=state["home_sot"],
            away_shots_on_target=state["away_sot"],
            home_team_name=state["home_club_name"],
            away_team_name=state["away_club_name"],
        )

    # ─── Helpers: player selection ────────────────────────────────────────────

    @staticmethod
    def _effective_team_ca(players: List[dict]) -> int:
        """
        Average effective CA = ``ca × fit(position, role_zone)``.

        Players assigned to roles outside their natural zone (e.g. a CB
        deployed at AM) get a sub-1.0 fit multiplier, which drags the
        whole team's effective ability down. This is what makes a GK
        played as a striker actually hurt the team.
        """
        if not players:
            return MatchEngine.DEFAULT_TEAM_CA
        total = 0.0
        for p in players:
            zone = p.get("role_zone") or role_zone_of(p.get("position", ""))
            total += (p.get("ca") or 0) * fit(p.get("position", ""), zone)
        return int(total / len(players))

    @staticmethod
    def _pick_outfield(players: List[dict]) -> dict:
        """
        Pick a player to credit for an attacking event (shot/goal/miss).
        Weighted by role: ATT > MID > DEF, and within a role by
        ``ca × fit``. A goalkeeper played up front (fit ≈ 0.20) is
        therefore very unlikely to be picked, and even if picked, the
        rest of the engine (conversion % etc.) is unaffected — but the
        team's effective strength was already discounted in
        ``_effective_team_ca``.
        """
        outfield = [p for p in players if (p.get("role_zone") != "GK")]
        if not outfield:
            outfield = [p for p in players if "GK" not in (p.get("position") or "")]
        if not outfield:
            return players[0] if players else {"name": "Unknown Player", "position": "CM", "ca": 100}

        # Bias toward attackers and midfielders.
        zone_weight = {"ATT": 5.0, "MID": 3.0, "DEF": 1.0, "GK": 0.2}
        weights = []
        for p in outfield:
            zone = p.get("role_zone") or role_zone_of(p.get("position", ""))
            zw = zone_weight.get(zone, 1.0)
            f = fit(p.get("position", ""), zone)
            ca = max(p.get("ca") or 1, 1)
            weights.append(zw * f * ca)
        if sum(weights) <= 0:
            return random.choice(outfield)
        return random.choices(outfield, weights=weights, k=1)[0]

    @staticmethod
    def _pick_goalkeeper(players: List[dict]) -> dict:
        """
        Pick the goalkeeper. Prefers a player with role_zone='GK',
        falls back to anyone whose natural position contains GK,
        finally to the first player.
        """
        gk = next((p for p in players if p.get("role_zone") == "GK"), None)
        if gk:
            return gk
        gk = next((p for p in players if "GK" in (p.get("position") or "")), None)
        if gk:
            return gk
        if players:
            return players[0]
        return {"name": "Unknown Keeper", "position": "GK", "ca": 100}

    # ─── Helpers: data access ─────────────────────────────────────────────────

    async def _get_team_ca(self, club_id: int) -> int:
        """Average CA of the top 11 players for the given club. Defaults to 100."""
        from app.data.club_budgets import CLUBS

        if 1 <= club_id <= len(CLUBS):
            club_name = CLUBS[club_id - 1][0]
        else:
            return self.DEFAULT_TEAM_CA

        first_token = club_name.split()[0] if club_name.split() else club_name
        result = await self.session.execute(
            text(
                """
                SELECT ca FROM players
                WHERE club = :club_name OR club LIKE :pattern
                ORDER BY ca DESC LIMIT 11
                """
            ),
            {"club_name": club_name, "pattern": f"%{first_token}%"},
        )
        cas = [row[0] for row in result.fetchall() if row[0]]
        if not cas:
            return self.DEFAULT_TEAM_CA
        return sum(cas) // len(cas)

    async def _get_top_players(self, club_id: int, limit: int = 11) -> List[dict]:
        """Top ``limit`` players for the given club, by CA descending. Defaults to placeholders."""
        from app.data.club_budgets import CLUBS

        if 1 <= club_id <= len(CLUBS):
            club_name = CLUBS[club_id - 1][0]
        else:
            return [
                {"name": f"Player {i}", "position": "CM", "ca": 100}
                for i in range(1, limit + 1)
            ]

        first_token = club_name.split()[0] if club_name.split() else club_name
        result = await self.session.execute(
            text(
                """
                SELECT name, position, ca FROM players
                WHERE club = :club_name OR club LIKE :pattern
                ORDER BY ca DESC LIMIT :lim
                """
            ),
            {
                "club_name": club_name,
                "pattern": f"%{first_token}%",
                "lim": limit,
            },
        )
        rows = result.fetchall()
        if not rows:
            return [
                {"name": f"Player {i}", "position": "CM", "ca": 100}
                for i in range(1, limit + 1)
            ]
        return [
            {"name": r[0], "position": r[1], "ca": r[2]}
            for r in rows
        ]
