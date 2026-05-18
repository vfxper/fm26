"""
UCLGenerator — Generates and manages the UEFA Champions League competition
for a career (modern 2024/25+ Swiss-system + knockout format).

Design reference: .kiro/specs/uefa-champions-league/design.md

This module follows the same patterns as `app/services/calendar_engine.py`:
- async SQLAlchemy session
- raw SQL via `text()` for SQLite compatibility
- a `random.Random` instance is injected for deterministic schedules

Top-level entrypoint is `generate_competition(career_id, year, player_club_id)`,
which is idempotent on `(name='Champions League', season=year)` and returns
the existing competition_id when one is already present.

Most downstream methods (Swiss pairings, knockout bracket, tie resolution,
result persistence) are stubbed here — they are implemented by subsequent
tasks in the spec.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.league_configs import FIFA_INTERNATIONAL_WINDOWS
from app.data.ucl_config import (
    UCL_FINAL_VENUE,
    UCL_LEAGUE_PHASE_TARGETS,
    UCL_PARTICIPANTS,
    UCL_R16_BRACKET_MAP,
    get_final_date,
)


# ─── Errors ───────────────────────────────────────────────────────────────────


class UCLScheduleError(Exception):
    """Raised when the Swiss-system pairing algorithm cannot satisfy constraints."""


# ─── Supporting Dataclasses ───────────────────────────────────────────────────


@dataclass
class Participant:
    """A registered UCL participant for a competition."""
    id: int                       # ucl_participants.id
    club_id: Optional[int]        # 1-based CLUBS index, or None
    club_name: str
    country: str
    seed: int                     # 1-36 (1 = top pot rank)


@dataclass
class StandingRow:
    """A single row of the league phase standings table."""
    participant_id: int
    club_name: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    rank: int


@dataclass
class TieResult:
    """Result of resolving a two-legged knockout tie."""
    tie_id: int
    aggregate_home: int
    aggregate_away: int
    winner_participant_id: int
    winner_decided_by: str        # 'aggregate' | 'extra_time' | 'penalties'


# ─── 6 standard rounds, in order, used by generate_competition ───────────────


_UCL_ROUND_ORDER: List[Tuple[str, int]] = [
    ("league_phase", 1),
    ("knockout_playoff", 2),
    ("round_of_16", 3),
    ("quarter_final", 4),
    ("semi_final", 5),
    ("final", 6),
]


# ─── UCLGenerator ─────────────────────────────────────────────────────────────


class UCLGenerator:
    """
    Generates and manages the UEFA Champions League competition for a career.
    """

    def __init__(
        self,
        session: AsyncSession,
        rng: Optional[random.Random] = None,
    ):
        self.session = session
        self.rng = rng or random.Random()

    # ─── Top-level lifecycle ──────────────────────────────────────────────

    async def generate_competition(
        self,
        career_id: int,
        year: int,
        player_club_id: Optional[int],
    ) -> int:
        """
        Generate a UCL competition shell for the given career and season year.

        Steps:
          1. Idempotency: if a 'Champions League' competition already exists
             for `season=year`, return its id without creating duplicates.
          2. Insert one `competitions` row with `competition_type='continental_cup'`,
             `name='Champions League'`, `season=year`, `status='active'`.
          3. Insert 36 `ucl_participants` rows from UCL_PARTICIPANTS with
             `seed = idx+1` (1-based).
          4. Insert 6 `competition_rounds` rows (league_phase, knockout_playoff,
             round_of_16, quarter_final, semi_final, final) with `round_order`
             1..6.
          5. Initialise 36 `ucl_standings` rows (all counters 0, rank NULL).
          6. Build Swiss-system pairings (`build_swiss_pairings`), resolve
             8 matchday dates (`assign_matchdays_to_dates`), and insert
             144 `calendar_events` rows for the league phase (priority=8,
             21:00 kick-off, Russian description for the player's club).

        Returns the new (or existing) `competition_id`.
        """
        # 1. Idempotency check — competitions are associated by season only.
        existing = await self.session.execute(
            text(
                "SELECT id FROM competitions "
                "WHERE name = :name AND season = :season "
                "LIMIT 1"
            ),
            {"name": "Champions League", "season": year},
        )
        existing_id = existing.scalar()
        if existing_id is not None:
            return int(existing_id)

        # 2. Insert competitions row.
        await self.session.execute(
            text(
                """
                INSERT INTO competitions
                    (name, competition_type, season, status)
                VALUES
                    (:name, :competition_type, :season, :status)
                """
            ),
            {
                "name": "Champions League",
                "competition_type": "continental_cup",
                "season": year,
                "status": "active",
            },
        )
        # SQLite-style last-insert-rowid (mirrors calendar_engine.py pattern).
        comp_id_row = await self.session.execute(text("SELECT last_insert_rowid()"))
        competition_id = int(comp_id_row.scalar() or 0)
        if competition_id <= 0:
            raise UCLScheduleError(
                "Failed to create UCL competition row (last_insert_rowid returned 0)"
            )

        # 3. Insert 36 ucl_participants rows. Seed is 1-based index in
        #    UCL_PARTICIPANTS (England top, then Spain, Germany, Italy, France,
        #    Netherlands, Portugal, Belgium, others) — see ucl_config.py.
        participant_ids: List[int] = []
        for idx, (display_name, club_id, country) in enumerate(UCL_PARTICIPANTS):
            seed = idx + 1
            await self.session.execute(
                text(
                    """
                    INSERT INTO ucl_participants
                        (competition_id, club_id, club_name, country, seed, final_rank)
                    VALUES
                        (:competition_id, :club_id, :club_name, :country, :seed, NULL)
                    """
                ),
                {
                    "competition_id": competition_id,
                    "club_id": club_id,
                    "club_name": display_name,
                    "country": country,
                    "seed": seed,
                },
            )
            pid_row = await self.session.execute(text("SELECT last_insert_rowid()"))
            pid = int(pid_row.scalar() or 0)
            if pid <= 0:
                raise UCLScheduleError(
                    f"Failed to insert ucl_participants row for seed={seed} ({display_name})"
                )
            participant_ids.append(pid)

        # 4. Insert 6 competition_rounds rows.
        for round_type, round_order in _UCL_ROUND_ORDER:
            await self.session.execute(
                text(
                    """
                    INSERT INTO competition_rounds
                        (competition_id, round_type, round_order, is_completed)
                    VALUES
                        (:competition_id, :round_type, :round_order, 0)
                    """
                ),
                {
                    "competition_id": competition_id,
                    "round_type": round_type,
                    "round_order": round_order,
                },
            )

        # 5. Initialise 36 ucl_standings rows (all zero, rank NULL).
        for pid in participant_ids:
            await self.session.execute(
                text(
                    """
                    INSERT INTO ucl_standings
                        (competition_id, participant_id,
                         played, won, drawn, lost,
                         goals_for, goals_against, goal_difference, points, rank)
                    VALUES
                        (:competition_id, :participant_id,
                         0, 0, 0, 0,
                         0, 0, 0, 0, NULL)
                    """
                ),
                {"competition_id": competition_id, "participant_id": pid},
            )

        # 6. Build Swiss-system pairings and resolve calendar dates, then
        #    insert the 144 league-phase calendar events. This wiring keeps
        #    new careers self-contained — the league phase appears on the
        #    calendar immediately after career creation.
        participants = [
            Participant(
                id=pid,
                club_id=club_id,
                club_name=display_name,
                country=country,
                seed=idx + 1,
            )
            for idx, ((display_name, club_id, country), pid) in enumerate(
                zip(UCL_PARTICIPANTS, participant_ids)
            )
        ]
        pairings = self.build_swiss_pairings(participants)
        dates = self.assign_matchdays_to_dates(
            pairings, year, blocked_ranges=[]
        )

        # Persist pairings so background_match_runner can replay the
        # exact schedule for off-screen matches.
        for md_idx, day in enumerate(pairings):
            md_num = md_idx + 1
            for home_pid, away_pid in day:
                await self.session.execute(
                    text(
                        "INSERT INTO ucl_phase_matchups "
                        "(competition_id, matchday, home_participant_id, "
                        " away_participant_id, played) "
                        "VALUES (:c, :md, :h, :a, 0)"
                    ),
                    {
                        "c": competition_id,
                        "md": md_num,
                        "h": home_pid,
                        "a": away_pid,
                    },
                )

        await self._insert_league_phase_events(
            career_id=career_id,
            competition_id=competition_id,
            pairings=pairings,
            dates=dates,
            player_club_id=player_club_id,
        )

        await self.session.commit()
        return competition_id

    # ─── Helpers ──────────────────────────────────────────────────────────

    async def _resolve_participant_club_id(
        self,
        participant_id: int,
    ) -> Optional[int]:
        """
        Resolve a UCL participant id to its 1-based CLUBS index (`club_id`),
        or None when the participant is a non-CLUBS entry (string-only,
        e.g. Bodø/Glimt, Pafos).
        """
        row = await self.session.execute(
            text("SELECT club_id FROM ucl_participants WHERE id = :pid"),
            {"pid": participant_id},
        )
        value = row.scalar()
        if value is None:
            return None
        return int(value)

    async def _get_round_id(
        self,
        competition_id: int,
        round_type: str,
    ) -> int:
        """
        Look up the `competition_rounds.id` for a (competition_id, round_type)
        pair. Raises `UCLScheduleError` when the row is missing.
        """
        row = await self.session.execute(
            text(
                "SELECT id FROM competition_rounds "
                "WHERE competition_id = :cid AND round_type = :rt"
            ),
            {"cid": competition_id, "rt": round_type},
        )
        rid = row.scalar()
        if rid is None:
            raise UCLScheduleError(
                f"No competition_rounds row for competition_id={competition_id}, "
                f"round_type={round_type!r}"
            )
        return int(rid)

    async def _participant_lookup(
        self,
        competition_id: int,
    ) -> dict[int, tuple[Optional[int], str]]:
        """
        Load all 36 participants for the competition into a single
        ``{participant_id: (club_id, club_name)}`` cache. Cuts down on
        per-event SELECT churn during league-phase event insertion.
        """
        rows = await self.session.execute(
            text(
                "SELECT id, club_id, club_name FROM ucl_participants "
                "WHERE competition_id = :cid"
            ),
            {"cid": competition_id},
        )
        cache: dict[int, tuple[Optional[int], str]] = {}
        for pid, club_id, club_name in rows.fetchall():
            cache[int(pid)] = (
                int(club_id) if club_id is not None else None,
                str(club_name),
            )
        return cache

    async def _player_locked_dates(
        self,
        career_id: int,
        player_club_id: Optional[int],
    ) -> Set[date]:
        """
        Return the set of dates that already have a `priority>=10` event for
        the player's club. UCL events involving the player's club SHALL NOT
        be scheduled on these dates (Requirement 12.5).
        """
        if player_club_id is None:
            return set()
        rows = await self.session.execute(
            text(
                """
                SELECT DISTINCT event_date FROM calendar_events
                WHERE career_id = :career_id
                  AND priority >= 10
                  AND (home_club_id = :club_id OR away_club_id = :club_id)
                """
            ),
            {"career_id": career_id, "club_id": player_club_id},
        )
        result: Set[date] = set()
        for (ds,) in rows.fetchall():
            try:
                if isinstance(ds, date):
                    result.add(ds)
                else:
                    result.add(date.fromisoformat(str(ds)))
            except Exception:
                continue
        return result

    async def _insert_league_phase_events(
        self,
        career_id: int,
        competition_id: int,
        pairings: List[List[Tuple[int, int]]],
        dates: List[date],
        player_club_id: Optional[int],
    ) -> None:
        """
        Insert calendar events for the league phase.

        Behaviour:
          * If `player_club_id` is given, ONLY the 8 matchdays of the
            player's club are added to the calendar (one match per
            matchday — i.e. exactly one UCL row per gameweek). Other 17
            matches per matchday remain implicit; their results are
            simulated by the standings auto-completion path and never
            shown in the user's personal calendar.
          * If `player_club_id` is None (no UCL participant for this
            career), no calendar rows are added; the competition still
            exists for read-only viewing.

        This avoids the bug where 18 UCL matches were stamped onto every
        Tuesday/Wednesday in the player's calendar.
        """
        if len(pairings) != 8 or len(dates) != 8:
            raise UCLScheduleError(
                f"_insert_league_phase_events expects 8 matchdays and 8 dates, "
                f"got {len(pairings)} pairings and {len(dates)} dates"
            )

        if player_club_id is None:
            # No participant for this career — keep the calendar clean.
            return

        cache = await self._participant_lookup(competition_id)
        player_locked = await self._player_locked_dates(career_id, player_club_id)

        for md_idx, day_pairs in enumerate(pairings):
            matchday = md_idx + 1
            base_date = dates[md_idx]

            # Find THE single match involving the player's club on this matchday.
            # In a Swiss-system schedule each participant plays exactly once per
            # matchday, so there is at most one such pair.
            player_pair: Optional[Tuple[int, int]] = None
            for home_pid, away_pid in day_pairs:
                home_club_id, _ = cache.get(home_pid, (None, "?"))
                away_club_id, _ = cache.get(away_pid, (None, "?"))
                if home_club_id == player_club_id or away_club_id == player_club_id:
                    player_pair = (home_pid, away_pid)
                    break

            if player_pair is None:
                continue  # player not playing this matchday (shouldn't happen)

            home_pid, away_pid = player_pair
            home_club_id, home_name = cache.get(home_pid, (None, "?"))
            away_club_id, away_name = cache.get(away_pid, (None, "?"))

            is_player_home = home_club_id == player_club_id
            opponent_name = away_name if is_player_home else home_name

            # Per-event date fallback for player's locked dates only.
            event_date = base_date
            if event_date in player_locked:
                fallback = self._find_available_slot(
                    base_date, [(d, d) for d in sorted(player_locked)]
                )
                if fallback is not None:
                    event_date = fallback

            description = self._build_event_description(
                round_type="league_phase",
                matchday=matchday,
                leg=None,
                player_club_id=player_club_id,
                home_club_name=home_name,
                away_club_name=away_name,
                is_player_home=is_player_home,
                opponent_name=opponent_name,
            )

            await self.session.execute(
                text(
                    """
                    INSERT INTO calendar_events
                        (career_id, event_date, event_type, competition_id,
                         home_club_id, away_club_id, is_locked, priority,
                         kick_off_time, description, is_cancelled)
                    VALUES
                        (:career_id, :event_date, :event_type, :competition_id,
                         :home_club_id, :away_club_id, :is_locked, :priority,
                         :kick_off_time, :description, :is_cancelled)
                    """
                ),
                {
                    "career_id": career_id,
                    "event_date": str(event_date),
                    "event_type": "match",
                    "competition_id": competition_id,
                    "home_club_id": home_club_id,
                    "away_club_id": away_club_id,
                    "is_locked": 0,
                    "priority": 8,
                    "kick_off_time": "21:00",
                    "description": description,
                    "is_cancelled": 0,
                },
            )

    # ─── League phase scheduling (subsequent tasks) ───────────────────────

    def build_swiss_pairings(
        self,
        participants: List[Participant],
    ) -> List[List[Tuple[int, int]]]:
        """
        Build 8 matchdays of 18 (home_pid, away_pid) pairs each, satisfying:
          * each participant appears exactly once per matchday
          * each participant has exactly 8 distinct opponents over the 8 days
          * each participant plays 4 home and 4 away matches

        Algorithm:
          1. Circle-method round-robin among the 36 participants (35 rounds
             of 18 perfect-matched pairs each); take the first 8 rounds.
             Initial participant order is shuffled with `self.rng` so the
             schedule varies per seed but is reproducible.
          2. Build an Eulerian orientation over the 144 resulting unordered
             pairs. Because every participant has degree 8 in this graph
             (an even number), an Eulerian orientation exists and yields
             in-degree = out-degree = 4 for every node — i.e. exactly
             4 home and 4 away assignments per participant.
          3. Validate every post-condition before returning; raise
             `UCLScheduleError` if any fail.
        """
        if len(participants) != 36:
            raise UCLScheduleError(
                f"build_swiss_pairings requires exactly 36 participants, got {len(participants)}"
            )

        # ── Step 1: Circle-method pairings ───────────────────────────────
        working = list(participants)
        self.rng.shuffle(working)
        ids = [p.id for p in working]
        n = len(ids)  # 36

        rotation = ids[1:]  # length 35
        all_pairs: List[Tuple[int, int]] = []          # flat list, all 144 edges
        pair_to_round: List[int] = []                  # parallel: round index per edge

        for round_idx in range(8):
            rotated = [ids[0]] + rotation[round_idx:] + rotation[:round_idx]
            for i in range(n // 2):
                a = rotated[i]
                b = rotated[n - 1 - i]
                all_pairs.append((a, b))
                pair_to_round.append(round_idx)

        # ── Step 2: Eulerian orientation for balanced home/away ─────────
        directed = self._orient_balanced(all_pairs)

        # ── Step 3: Reassemble into 8 matchdays ──────────────────────────
        matchdays: List[List[Tuple[int, int]]] = [[] for _ in range(8)]
        for eidx, oriented in enumerate(directed):
            matchdays[pair_to_round[eidx]].append(oriented)

        # ── Step 4: Validate post-conditions ─────────────────────────────
        appearances: dict[int, int] = {pid: 0 for pid in ids}
        opponents: dict[int, Set[int]] = {pid: set() for pid in ids}
        home_counts: dict[int, int] = {pid: 0 for pid in ids}
        away_counts: dict[int, int] = {pid: 0 for pid in ids}

        for md_idx, day in enumerate(matchdays):
            if len(day) != 18:
                raise UCLScheduleError(
                    f"Matchday {md_idx + 1} has {len(day)} matches, expected 18"
                )
            seen_today: Set[int] = set()
            for home, away in day:
                if home in seen_today or away in seen_today:
                    raise UCLScheduleError(
                        f"Participant appears twice on matchday {md_idx + 1}"
                    )
                seen_today.add(home)
                seen_today.add(away)
                appearances[home] += 1
                appearances[away] += 1
                home_counts[home] += 1
                away_counts[away] += 1
                if away in opponents[home] or home in opponents[away]:
                    raise UCLScheduleError(
                        f"Duplicate opponent pairing on matchday {md_idx + 1}: "
                        f"{home} vs {away}"
                    )
                opponents[home].add(away)
                opponents[away].add(home)

        for pid in ids:
            if appearances[pid] != 8:
                raise UCLScheduleError(
                    f"Participant {pid} appears {appearances[pid]} times, expected 8"
                )
            if len(opponents[pid]) != 8:
                raise UCLScheduleError(
                    f"Participant {pid} has {len(opponents[pid])} distinct opponents, expected 8"
                )
            if home_counts[pid] != 4 or away_counts[pid] != 4:
                raise UCLScheduleError(
                    f"Participant {pid} home/away split is "
                    f"{home_counts[pid]}/{away_counts[pid]}, expected 4/4"
                )

        total = sum(len(d) for d in matchdays)
        if total != 144:
            raise UCLScheduleError(
                f"Total matches across 8 matchdays is {total}, expected 144"
            )

        return matchdays

    @staticmethod
    def _orient_balanced(
        raw_pairs: List[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """
        Orient an undirected multigraph so every vertex has equal in- and
        out-degree (Eulerian orientation). Implemented via iterative
        Hierholzer: each connected component is Eulerian because every
        vertex in our schedule has even degree (8), so the orientation
        produced by the Eulerian walk satisfies in == out at every vertex.

        Returns a list of (home, away) tuples in the same order as
        `raw_pairs`.
        """
        from collections import defaultdict

        # Adjacency list: node -> list of [other, edge_idx]. We pop from the
        # end of these lists as edges are consumed, so use list-of-lists.
        adj: dict[int, list[list[int]]] = defaultdict(list)
        for eidx, (a, b) in enumerate(raw_pairs):
            adj[a].append([b, eidx])
            adj[b].append([a, eidx])

        used = [False] * len(raw_pairs)
        directed: List[Optional[Tuple[int, int]]] = [None] * len(raw_pairs)

        # Process every node so disconnected components are handled. Sorting
        # gives deterministic output for a given input pair order.
        for start in sorted(adj.keys()):
            # Hierholzer's algorithm — iterative, with edge-direction
            # recorded as we traverse from v to w.
            stack = [start]
            while stack:
                v = stack[-1]
                # Discard already-used edges from the back of v's list
                while adj[v] and used[adj[v][-1][1]]:
                    adj[v].pop()
                if adj[v]:
                    w, eidx = adj[v].pop()
                    used[eidx] = True
                    directed[eidx] = (v, w)
                    stack.append(w)
                else:
                    stack.pop()

        # Sanity check — every edge must be oriented.
        for eidx, oriented in enumerate(directed):
            if oriented is None:
                raise UCLScheduleError(
                    f"Eulerian orientation failed: edge {eidx} ({raw_pairs[eidx]}) "
                    f"left unoriented"
                )

        return [d for d in directed if d is not None]

    def assign_matchdays_to_dates(
        self,
        matchdays: List[List[Tuple[int, int]]],
        year: int,
        blocked_ranges: List[Tuple[date, date]],
    ) -> List[date]:
        """
        Resolve each entry in `UCL_LEAGUE_PHASE_TARGETS` to a concrete date
        in the season starting in `year`.

        Conventions:
          * `month >= 9`  → use `year`
          * `month <= 1`  → use `year + 1`
          * `week_of_month`: 1..4 selects the Nth occurrence of the weekday
            in the month, `5` means "the last occurrence in the month"
          * `weekday`: 1 → Tuesday, 2 → Wednesday

        Each computed date is checked against `FIFA_INTERNATIONAL_WINDOWS`
        and the caller-supplied `blocked_ranges`. Conflicts are resolved by
        searching for the nearest allowed Tuesday/Wednesday within ±7 days
        of the target. If no slot is available, raises `UCLScheduleError`.
        """
        if len(matchdays) != 8:
            raise UCLScheduleError(
                f"assign_matchdays_to_dates expects 8 matchdays, got {len(matchdays)}"
            )
        if len(UCL_LEAGUE_PHASE_TARGETS) != 8:
            raise UCLScheduleError(
                "UCL_LEAGUE_PHASE_TARGETS must define exactly 8 target dates"
            )

        # Pre-compute concrete FIFA window date ranges for `year` and `year+1`,
        # so a Sept date in `year` and a Jan date in `year+1` are both checked
        # against the right windows.
        fifa_ranges: List[Tuple[date, date]] = []
        for window in FIFA_INTERNATIONAL_WINDOWS:
            start_md = window["start"]   # "MM-DD"
            end_md = window["end"]
            for y in (year, year + 1):
                fifa_ranges.append(
                    (
                        self._parse_md(y, start_md),
                        self._parse_md(y, end_md),
                    )
                )

        all_blocked = list(fifa_ranges) + list(blocked_ranges or [])

        chosen: List[date] = []
        for month, week, weekday_num in UCL_LEAGUE_PHASE_TARGETS:
            target_year = year if month >= 9 else year + 1
            target = self._compute_target_date(target_year, month, week, weekday_num)
            slot = self._find_available_slot(target, all_blocked)
            if slot is None:
                raise UCLScheduleError(
                    f"No available Tuesday/Wednesday slot within ±7 days of {target} "
                    f"(month={month}, week={week}, weekday={weekday_num})"
                )
            chosen.append(slot)

        return chosen

    @staticmethod
    def _parse_md(year: int, md: str) -> date:
        """Parse an "MM-DD" string into a `date` for the given year."""
        month_str, day_str = md.split("-")
        return date(year, int(month_str), int(day_str))

    @staticmethod
    def _compute_target_date(
        target_year: int,
        month: int,
        week: int,
        weekday_num: int,
    ) -> date:
        """
        Compute the target date for a (month, week, weekday) triple.

        `weekday_num`: 1 = Tuesday (Python weekday() == 1),
                       2 = Wednesday (Python weekday() == 2).
        `week`: 1..4 selects the Nth occurrence of the weekday in the month;
                5 selects the last occurrence in the month.
        """
        py_weekday = weekday_num  # 1 → Tue, 2 → Wed; matches Python's weekday()

        if week == 5:
            # Last occurrence: start at the last day of the month and walk
            # backwards.
            if month == 12:
                next_month_first = date(target_year + 1, 1, 1)
            else:
                next_month_first = date(target_year, month + 1, 1)
            d = next_month_first - timedelta(days=1)
            while d.weekday() != py_weekday:
                d -= timedelta(days=1)
            return d

        # First occurrence in the month:
        first = date(target_year, month, 1)
        offset = (py_weekday - first.weekday()) % 7
        first_match = first + timedelta(days=offset)
        # Add (week - 1) weeks for Nth occurrence.
        target = first_match + timedelta(days=7 * (week - 1))
        # Defensive: if (week - 1) pushed us past the month, that's a config
        # error in UCL_LEAGUE_PHASE_TARGETS.
        if target.month != month or target.year != target_year:
            raise UCLScheduleError(
                f"Computed target {target} falls outside requested month "
                f"{target_year}-{month:02d} (week={week}, weekday={weekday_num})"
            )
        return target

    @staticmethod
    def _find_available_slot(
        target: date,
        blocked: List[Tuple[date, date]],
    ) -> Optional[date]:
        """
        Search for an available Tuesday/Wednesday within ±7 days of `target`.

        Search order: 0, +1, -1, +2, -2, ..., +7, -7. Only Tuesdays
        (weekday()==1) and Wednesdays (weekday()==2) are considered. A
        candidate is considered available when it falls outside every
        (start, end) range in `blocked` (ranges are inclusive on both ends).
        """
        deltas: List[int] = [0]
        for d in range(1, 8):
            deltas.append(d)
            deltas.append(-d)

        for delta in deltas:
            candidate = target + timedelta(days=delta)
            if candidate.weekday() not in (1, 2):
                continue
            if not UCLGenerator._is_blocked(candidate, blocked):
                return candidate
        return None

    @staticmethod
    def _is_blocked(d: date, ranges: List[Tuple[date, date]]) -> bool:
        """True iff `d` falls within any inclusive (start, end) range."""
        for start, end in ranges:
            if start <= d <= end:
                return True
        return False

    # ─── Standings ────────────────────────────────────────────────────────

    async def update_standing(
        self,
        competition_id: int,
        home_participant_id: int,
        away_participant_id: int,
        home_score: int,
        away_score: int,
    ) -> None:
        """
        Update both participants' rows in `ucl_standings` for a league-phase
        result, then recompute ranks 1-36 across all 36 standings rows for
        the competition.

        Tie-breaker for ranking: ``points DESC, goal_difference DESC,
        goals_for DESC, club_name ASC``.
        """
        # Determine outcome from each side's perspective.
        if home_score > away_score:
            home_w, home_d, home_l, home_pts = 1, 0, 0, 3
            away_w, away_d, away_l, away_pts = 0, 0, 1, 0
        elif away_score > home_score:
            home_w, home_d, home_l, home_pts = 0, 0, 1, 0
            away_w, away_d, away_l, away_pts = 1, 0, 0, 3
        else:
            home_w, home_d, home_l, home_pts = 0, 1, 0, 1
            away_w, away_d, away_l, away_pts = 0, 1, 0, 1

        # Apply increments. goal_difference is recomputed inline so we do
        # not rely on a previous value being correct.
        await self.session.execute(
            text(
                """
                UPDATE ucl_standings
                SET played = played + 1,
                    won = won + :w,
                    drawn = drawn + :d,
                    lost = lost + :l,
                    goals_for = goals_for + :gf,
                    goals_against = goals_against + :ga,
                    goal_difference = (goals_for + :gf) - (goals_against + :ga),
                    points = points + :pts
                WHERE competition_id = :cid AND participant_id = :pid
                """
            ),
            {
                "cid": competition_id,
                "pid": home_participant_id,
                "w": home_w,
                "d": home_d,
                "l": home_l,
                "gf": home_score,
                "ga": away_score,
                "pts": home_pts,
            },
        )
        await self.session.execute(
            text(
                """
                UPDATE ucl_standings
                SET played = played + 1,
                    won = won + :w,
                    drawn = drawn + :d,
                    lost = lost + :l,
                    goals_for = goals_for + :gf,
                    goals_against = goals_against + :ga,
                    goal_difference = (goals_for + :gf) - (goals_against + :ga),
                    points = points + :pts
                WHERE competition_id = :cid AND participant_id = :pid
                """
            ),
            {
                "cid": competition_id,
                "pid": away_participant_id,
                "w": away_w,
                "d": away_d,
                "l": away_l,
                "gf": away_score,
                "ga": home_score,
                "pts": away_pts,
            },
        )

        await self._recompute_ranks(competition_id)

    async def _recompute_ranks(self, competition_id: int) -> None:
        """
        Re-sort all 36 standings rows by
        ``(points DESC, goal_difference DESC, goals_for DESC, club_name ASC)``
        and write the resulting 1-based rank back to `ucl_standings.rank`.
        """
        rows = await self.session.execute(
            text(
                """
                SELECT s.participant_id
                FROM ucl_standings s
                JOIN ucl_participants p ON p.id = s.participant_id
                WHERE s.competition_id = :cid
                ORDER BY s.points DESC,
                         s.goal_difference DESC,
                         s.goals_for DESC,
                         p.club_name ASC
                """
            ),
            {"cid": competition_id},
        )
        for rank, (participant_id,) in enumerate(rows.fetchall(), start=1):
            await self.session.execute(
                text(
                    """
                    UPDATE ucl_standings
                    SET rank = :rank
                    WHERE competition_id = :cid AND participant_id = :pid
                    """
                ),
                {"cid": competition_id, "pid": int(participant_id), "rank": rank},
            )

    async def get_league_phase_table(
        self,
        competition_id: int,
    ) -> List[StandingRow]:
        """
        Return the 36-row standings table for the given UCL competition,
        sorted by ``points DESC, goal_difference DESC, goals_for DESC,
        club_name ASC``. Returned ``rank`` is the position in the sort
        order (1-36) and reflects the live ordering even if a previous
        ``rank`` column write is stale.
        """
        rows = await self.session.execute(
            text(
                """
                SELECT s.participant_id, p.club_name,
                       s.played, s.won, s.drawn, s.lost,
                       s.goals_for, s.goals_against, s.goal_difference,
                       s.points, s.rank
                FROM ucl_standings s
                JOIN ucl_participants p ON p.id = s.participant_id
                WHERE s.competition_id = :cid
                ORDER BY s.points DESC,
                         s.goal_difference DESC,
                         s.goals_for DESC,
                         p.club_name ASC
                """
            ),
            {"cid": competition_id},
        )
        out: List[StandingRow] = []
        for idx, r in enumerate(rows.fetchall(), start=1):
            (
                pid,
                club_name,
                played,
                won,
                drawn,
                lost,
                gf,
                ga,
                gd,
                points,
                rank_col,
            ) = r
            out.append(
                StandingRow(
                    participant_id=int(pid),
                    club_name=str(club_name),
                    played=int(played or 0),
                    won=int(won or 0),
                    drawn=int(drawn or 0),
                    lost=int(lost or 0),
                    goals_for=int(gf or 0),
                    goals_against=int(ga or 0),
                    goal_difference=int(gd or 0),
                    points=int(points or 0),
                    rank=int(rank_col) if rank_col is not None else idx,
                )
            )
        return out

    # ─── Knockout phase ───────────────────────────────────────────────────

    @staticmethod
    def _next_round(round_type: str) -> Optional[str]:
        return {
            "knockout_playoff": "round_of_16",
            "round_of_16": "quarter_final",
            "quarter_final": "semi_final",
            "semi_final": "final",
        }.get(round_type)

    @staticmethod
    def _round_first_tuesday(year: int, month: int) -> date:
        """Return the first Tuesday on/after the 1st of the given month."""
        d = date(year, month, 1)
        # Tuesday = weekday() == 1
        offset = (1 - d.weekday()) % 7
        return d + timedelta(days=offset)

    async def _insert_two_legged_calendar_events(
        self,
        career_id: int,
        competition_id: int,
        round_type: str,
        ties: List[dict],
        leg1_date: date,
        leg2_date: date,
        player_club_id: Optional[int],
    ) -> None:
        """
        Insert calendar_events for two-legged knockout ties.

        ONLY ties involving ``player_club_id`` are added to the calendar —
        other ties happen "off-screen" and their winners are computed by
        the standings/auto-completion path. This mirrors how a real club
        manager only sees their own fixtures, never the entire bracket.
        If ``player_club_id`` is None, no rows are inserted.
        """
        if player_club_id is None:
            return

        cache = await self._participant_lookup(competition_id)
        for tie in ties:
            home_pid = int(tie["home_participant_id"])
            away_pid = int(tie["away_participant_id"])
            home_club_id, home_name = cache.get(home_pid, (None, "?"))
            away_club_id, away_name = cache.get(away_pid, (None, "?"))

            # Skip ties that don't involve the player's club.
            if home_club_id != player_club_id and away_club_id != player_club_id:
                continue

            # Leg 1: at away_participant's stadium.
            for leg, ev_date, ev_home_club_id, ev_home_name, ev_away_club_id, ev_away_name in (
                (1, leg1_date, away_club_id, away_name, home_club_id, home_name),
                (2, leg2_date, home_club_id, home_name, away_club_id, away_name),
            ):
                # Determine player involvement for the description.
                is_player_home: Optional[bool] = None
                opponent_name: Optional[str] = None
                if player_club_id is not None:
                    if ev_home_club_id == player_club_id:
                        is_player_home = True
                        opponent_name = ev_away_name
                    elif ev_away_club_id == player_club_id:
                        is_player_home = False
                        opponent_name = ev_home_name

                description = self._build_event_description(
                    round_type=round_type,
                    matchday=None,
                    leg=leg,
                    player_club_id=player_club_id,
                    home_club_name=ev_home_name,
                    away_club_name=ev_away_name,
                    is_player_home=is_player_home,
                    opponent_name=opponent_name,
                )

                await self.session.execute(
                    text(
                        """
                        INSERT INTO calendar_events
                            (career_id, event_date, event_type, competition_id,
                             home_club_id, away_club_id, is_locked, priority,
                             kick_off_time, description, is_cancelled)
                        VALUES
                            (:career_id, :event_date, :event_type, :competition_id,
                             :home_club_id, :away_club_id, :is_locked, :priority,
                             :kick_off_time, :description, :is_cancelled)
                        """
                    ),
                    {
                        "career_id": career_id,
                        "event_date": str(ev_date),
                        "event_type": "match",
                        "competition_id": competition_id,
                        "home_club_id": ev_home_club_id,
                        "away_club_id": ev_away_club_id,
                        "is_locked": 0,
                        "priority": 8,
                        "kick_off_time": "21:00",
                        "description": description,
                        "is_cancelled": 0,
                    },
                )

    async def _competition_season(self, competition_id: int) -> int:
        row = await self.session.execute(
            text("SELECT season FROM competitions WHERE id = :cid"),
            {"cid": competition_id},
        )
        season = row.scalar()
        if season is None:
            raise UCLScheduleError(
                f"competition_id={competition_id} has no season"
            )
        return int(season)

    async def finalize_league_phase(
        self,
        competition_id: int,
        career_id: Optional[int] = None,
        player_club_id: Optional[int] = None,
    ) -> None:
        """
        Close out the league phase and seed the knockout playoff round.

        Steps:
          1. Recompute final ranks 1-36 and write them back to
             `ucl_participants.final_rank`.
          2. Mark the `league_phase` round as completed.
          3. Pair ranks [9-16] with ranks [17-24] in the knockout playoff
             bracket: bracket_position 1 = (rank 9, rank 24),
             position 2 = (rank 10, rank 23), …, position 8 = (rank 16,
             rank 17). The high-seeded participant becomes
             ``home_participant_id`` so it plays leg 2 at home.
          4. Insert 8 `ucl_ties` rows for the knockout playoff.
          5. Insert 16 `calendar_events` rows (8 leg-1 + 8 leg-2) for
             early-February of (season + 1).
        """
        # 1. Recompute ranks (in case some standings rows are stale) and
        # copy each participant's rank into final_rank.
        await self._recompute_ranks(competition_id)
        rows = await self.session.execute(
            text(
                """
                SELECT s.participant_id, s.rank
                FROM ucl_standings s
                WHERE s.competition_id = :cid
                """
            ),
            {"cid": competition_id},
        )
        for participant_id, rank in rows.fetchall():
            if rank is None:
                continue
            await self.session.execute(
                text(
                    "UPDATE ucl_participants "
                    "SET final_rank = :rank WHERE id = :pid"
                ),
                {"rank": int(rank), "pid": int(participant_id)},
            )

        # 2. Mark league_phase round as completed.
        await self.session.execute(
            text(
                "UPDATE competition_rounds "
                "SET is_completed = 1 "
                "WHERE competition_id = :cid AND round_type = 'league_phase'"
            ),
            {"cid": competition_id},
        )

        # 3. Build playoff pairings — fetch the 16 participants ranked 9-24.
        rank_rows = await self.session.execute(
            text(
                """
                SELECT participant_id, rank
                FROM ucl_standings
                WHERE competition_id = :cid AND rank BETWEEN 9 AND 24
                ORDER BY rank ASC
                """
            ),
            {"cid": competition_id},
        )
        ranked = {int(rank): int(pid) for pid, rank in rank_rows.fetchall()}
        if len(ranked) != 16:
            raise UCLScheduleError(
                f"finalize_league_phase: expected 16 participants ranked 9-24, "
                f"got {len(ranked)}"
            )

        round_id = await self._get_round_id(competition_id, "knockout_playoff")
        ties: List[dict] = []
        for bracket_position in range(1, 9):
            high_rank = 8 + bracket_position           # 9..16
            low_rank = 25 - bracket_position           # 24..17
            home_pid = ranked[high_rank]
            away_pid = ranked[low_rank]
            await self.session.execute(
                text(
                    """
                    INSERT INTO ucl_ties
                        (competition_id, round_id,
                         home_participant_id, away_participant_id,
                         bracket_position)
                    VALUES
                        (:cid, :rid, :home_pid, :away_pid, :pos)
                    """
                ),
                {
                    "cid": competition_id,
                    "rid": round_id,
                    "home_pid": home_pid,
                    "away_pid": away_pid,
                    "pos": bracket_position,
                },
            )
            ties.append(
                {
                    "home_participant_id": home_pid,
                    "away_participant_id": away_pid,
                }
            )

        # 4. Schedule + insert 16 calendar_events.
        if career_id is not None:
            season = await self._competition_season(competition_id)
            leg1 = self._round_first_tuesday(season + 1, 2)
            leg2 = leg1 + timedelta(days=7)
            await self._insert_two_legged_calendar_events(
                career_id=career_id,
                competition_id=competition_id,
                round_type="knockout_playoff",
                ties=ties,
                leg1_date=leg1,
                leg2_date=leg2,
                player_club_id=player_club_id,
            )

    async def build_round_of_16(
        self,
        competition_id: int,
        career_id: Optional[int] = None,
        player_club_id: Optional[int] = None,
    ) -> None:
        """
        Seed the Round of 16 from the 8 direct qualifiers (final_rank 1-8)
        and the 8 winners of the knockout playoff round.

        Pairing follows ``UCL_R16_BRACKET_MAP``: seed 1 (best direct
        qualifier) plays the lowest-seeded playoff winner; seed 2 plays
        the second-lowest; etc. The direct qualifier is the high seed and
        plays leg 2 at home (``home_participant_id``).
        """
        # Verify all 8 playoff ties have a winner.
        playoff_round_id = await self._get_round_id(competition_id, "knockout_playoff")
        winners = await self.session.execute(
            text(
                """
                SELECT bracket_position, winner_participant_id
                FROM ucl_ties
                WHERE round_id = :rid
                ORDER BY bracket_position ASC
                """
            ),
            {"rid": playoff_round_id},
        )
        playoff_winners: list[tuple[int, int]] = []  # (bracket_position, pid)
        for pos, pid in winners.fetchall():
            if pid is None:
                raise UCLScheduleError(
                    "build_round_of_16: knockout_playoff has unfinished ties"
                )
            playoff_winners.append((int(pos), int(pid)))
        if len(playoff_winners) != 8:
            raise UCLScheduleError(
                f"build_round_of_16: expected 8 playoff winners, got {len(playoff_winners)}"
            )

        # Sort the 8 playoff winners by their final_rank ascending — best
        # surviving 9-16 first. The ``UCL_R16_BRACKET_MAP`` value is the
        # 1-based index into this sorted list.
        winner_pids = [pid for _pos, pid in playoff_winners]
        rank_rows = await self.session.execute(
            text(
                f"""
                SELECT id, final_rank FROM ucl_participants
                WHERE id IN ({",".join(str(p) for p in winner_pids)})
                """
            ),
        )
        rank_by_pid: dict[int, int] = {
            int(pid): int(r) if r is not None else 999
            for pid, r in rank_rows.fetchall()
        }
        sorted_winners = sorted(winner_pids, key=lambda p: rank_by_pid.get(p, 999))
        # Now ``sorted_winners[i-1]`` is the i-th best playoff winner
        # (1-based index). UCL_R16_BRACKET_MAP[seed] gives that index.

        # Fetch direct qualifiers (final_rank 1-8).
        dq_rows = await self.session.execute(
            text(
                """
                SELECT id, final_rank FROM ucl_participants
                WHERE competition_id = :cid AND final_rank BETWEEN 1 AND 8
                ORDER BY final_rank ASC
                """
            ),
            {"cid": competition_id},
        )
        direct_qualifiers: dict[int, int] = {
            int(r): int(pid) for pid, r in dq_rows.fetchall()
        }
        if len(direct_qualifiers) != 8:
            raise UCLScheduleError(
                f"build_round_of_16: expected 8 direct qualifiers, "
                f"got {len(direct_qualifiers)}"
            )

        r16_round_id = await self._get_round_id(competition_id, "round_of_16")
        ties: List[dict] = []
        for seed in range(1, 9):
            home_pid = direct_qualifiers[seed]
            opponent_idx = UCL_R16_BRACKET_MAP[seed]  # 1-based
            away_pid = sorted_winners[opponent_idx - 1]
            await self.session.execute(
                text(
                    """
                    INSERT INTO ucl_ties
                        (competition_id, round_id,
                         home_participant_id, away_participant_id,
                         bracket_position)
                    VALUES
                        (:cid, :rid, :home_pid, :away_pid, :pos)
                    """
                ),
                {
                    "cid": competition_id,
                    "rid": r16_round_id,
                    "home_pid": home_pid,
                    "away_pid": away_pid,
                    "pos": seed,
                },
            )
            ties.append(
                {
                    "home_participant_id": home_pid,
                    "away_participant_id": away_pid,
                }
            )

        # Schedule + insert 16 calendar_events (early March of season+1).
        if career_id is not None:
            season = await self._competition_season(competition_id)
            leg1 = self._round_first_tuesday(season + 1, 3)
            leg2 = leg1 + timedelta(days=7)
            await self._insert_two_legged_calendar_events(
                career_id=career_id,
                competition_id=competition_id,
                round_type="round_of_16",
                ties=ties,
                leg1_date=leg1,
                leg2_date=leg2,
                player_club_id=player_club_id,
            )

        # Mark the playoff round done.
        await self.session.execute(
            text(
                "UPDATE competition_rounds "
                "SET is_completed = 1 "
                "WHERE competition_id = :cid AND round_type = 'knockout_playoff'"
            ),
            {"cid": competition_id},
        )

    async def advance_bracket(
        self,
        competition_id: int,
        from_round: str,
        career_id: Optional[int] = None,
        player_club_id: Optional[int] = None,
    ) -> None:
        """
        Advance the bracket from ``from_round`` to its successor.

        from_round → to_round mapping:
          * ``round_of_16``   → ``quarter_final`` (4 ties)
          * ``quarter_final`` → ``semi_final`` (2 ties)
          * ``semi_final``    → ``final`` (1 single-leg tie)

        Winners are paired by `bracket_position`: positions 1 and 2 produce
        the next round's position-1 tie (1's winner is the home/high
        seed); positions 3 and 4 produce position-2; etc.
        """
        to_round = self._next_round(from_round)
        if to_round is None or to_round == "round_of_16":
            raise UCLScheduleError(
                f"advance_bracket: invalid transition from {from_round!r}"
            )

        from_round_id = await self._get_round_id(competition_id, from_round)
        to_round_id = await self._get_round_id(competition_id, to_round)

        rows = await self.session.execute(
            text(
                """
                SELECT bracket_position, winner_participant_id
                FROM ucl_ties
                WHERE round_id = :rid
                ORDER BY bracket_position ASC
                """
            ),
            {"rid": from_round_id},
        )
        winners: list[tuple[int, int]] = []
        for pos, pid in rows.fetchall():
            if pid is None:
                raise UCLScheduleError(
                    f"advance_bracket: {from_round} has unfinished ties"
                )
            winners.append((int(pos), int(pid)))

        # Pair winners — sorted by bracket_position ASC.
        winners.sort(key=lambda x: x[0])
        new_ties: List[dict] = []
        for new_pos, base in enumerate(range(0, len(winners), 2), start=1):
            home_pid = winners[base][1]
            away_pid = winners[base + 1][1]
            await self.session.execute(
                text(
                    """
                    INSERT INTO ucl_ties
                        (competition_id, round_id,
                         home_participant_id, away_participant_id,
                         bracket_position)
                    VALUES
                        (:cid, :rid, :home_pid, :away_pid, :pos)
                    """
                ),
                {
                    "cid": competition_id,
                    "rid": to_round_id,
                    "home_pid": home_pid,
                    "away_pid": away_pid,
                    "pos": new_pos,
                },
            )
            new_ties.append(
                {
                    "home_participant_id": home_pid,
                    "away_participant_id": away_pid,
                }
            )

        # Mark the from_round as completed.
        await self.session.execute(
            text(
                "UPDATE competition_rounds "
                "SET is_completed = 1 "
                "WHERE competition_id = :cid AND round_type = :rt"
            ),
            {"cid": competition_id, "rt": from_round},
        )

        # Insert calendar_events for the new round.
        if career_id is None:
            return

        season = await self._competition_season(competition_id)
        next_year = season + 1

        if to_round == "final":
            # Single-leg final on the last Saturday of May (year+1) at the
            # fixed neutral venue. ONLY add to player's calendar if their
            # club is one of the two finalists.
            final_date = get_final_date(next_year)
            cache = await self._participant_lookup(competition_id)
            tie = new_ties[0]
            home_pid = int(tie["home_participant_id"])
            away_pid = int(tie["away_participant_id"])
            home_club_id, home_name = cache.get(home_pid, (None, "?"))
            away_club_id, away_name = cache.get(away_pid, (None, "?"))

            if player_club_id is None or (
                home_club_id != player_club_id and away_club_id != player_club_id
            ):
                # Player did not reach the final — no calendar event.
                return

            is_player_home = home_club_id == player_club_id
            opponent_name = away_name if is_player_home else home_name

            description = self._build_event_description(
                round_type="final",
                matchday=None,
                leg=None,
                player_club_id=player_club_id,
                home_club_name=home_name,
                away_club_name=away_name,
                is_player_home=is_player_home,
                opponent_name=opponent_name,
                neutral_venue=UCL_FINAL_VENUE,
            )

            await self.session.execute(
                text(
                    """
                    INSERT INTO calendar_events
                        (career_id, event_date, event_type, competition_id,
                         home_club_id, away_club_id, is_locked, priority,
                         kick_off_time, description, is_cancelled)
                    VALUES
                        (:career_id, :event_date, :event_type, :competition_id,
                         :home_club_id, :away_club_id, :is_locked, :priority,
                         :kick_off_time, :description, :is_cancelled)
                    """
                ),
                {
                    "career_id": career_id,
                    "event_date": str(final_date),
                    "event_type": "match",
                    "competition_id": competition_id,
                    "home_club_id": home_club_id,
                    "away_club_id": away_club_id,
                    "is_locked": 0,
                    "priority": 8,
                    "kick_off_time": "21:00",
                    "description": description,
                    "is_cancelled": 0,
                },
            )
            return

        # Two-legged round (QF or SF) — first Tuesday of April for QF;
        # third Tuesday of April for SF.
        if to_round == "quarter_final":
            leg1 = self._round_first_tuesday(next_year, 4)
        elif to_round == "semi_final":
            leg1 = self._round_first_tuesday(next_year, 4) + timedelta(days=21)
        else:
            leg1 = self._round_first_tuesday(next_year, 4)
        leg2 = leg1 + timedelta(days=7)

        await self._insert_two_legged_calendar_events(
            career_id=career_id,
            competition_id=competition_id,
            round_type=to_round,
            ties=new_ties,
            leg1_date=leg1,
            leg2_date=leg2,
            player_club_id=player_club_id,
        )

    async def crown_champion(
        self,
        competition_id: int,
        winner_participant_id: int,
    ) -> None:
        """
        Mark the UCL competition as completed.

        Updates ``competitions.status`` to ``'completed'`` and marks the
        ``final`` round in ``competition_rounds`` as completed. The
        winner's participant id is intentionally not denormalised onto
        ``competitions`` — call sites can recover it from ``ucl_ties``
        for the final round.
        """
        await self.session.execute(
            text(
                "UPDATE competitions SET status = 'completed' "
                "WHERE id = :cid"
            ),
            {"cid": competition_id},
        )
        await self.session.execute(
            text(
                "UPDATE competition_rounds "
                "SET is_completed = 1 "
                "WHERE competition_id = :cid AND round_type = 'final'"
            ),
            {"cid": competition_id},
        )

    # ─── Match result handling ────────────────────────────────────────────

    def _resolve_tie(self, tie: dict) -> TieResult:
        """
        Determine the winner of a two-legged knockout tie.

        Aggregate scoring (no away-goals rule, per Requirement 5.7):
          * ``aggregate_home = leg1_home_score + leg2_away_score``
          * ``aggregate_away = leg1_away_score + leg2_home_score``

        Tie-break order:
          1. If the aggregates are unequal, ``decided_by='aggregate'``.
          2. Else simulate 30 minutes of extra time: each side may score one
             ET goal with probability 0.4 (independent draws); apply ET
             goals to aggregates. If still tied, simulate a penalty
             shootout (5 kicks per side then sudden death) using
             ``self.rng``.
        """
        l1h = int(tie.get("leg1_home_score") or 0)
        l1a = int(tie.get("leg1_away_score") or 0)
        l2h = int(tie.get("leg2_home_score") or 0)
        l2a = int(tie.get("leg2_away_score") or 0)

        aggregate_home = l1h + l2a
        aggregate_away = l1a + l2h

        home_pid = int(tie["home_participant_id"])
        away_pid = int(tie["away_participant_id"])
        tie_id = int(tie.get("id") or 0)

        if aggregate_home != aggregate_away:
            winner = home_pid if aggregate_home > aggregate_away else away_pid
            return TieResult(
                tie_id=tie_id,
                aggregate_home=aggregate_home,
                aggregate_away=aggregate_away,
                winner_participant_id=winner,
                winner_decided_by="aggregate",
            )

        # Extra time — independent 0.4 probability per side for one goal.
        et_home = 1 if self.rng.random() < 0.4 else 0
        et_away = 1 if self.rng.random() < 0.4 else 0
        aggregate_home += et_home
        aggregate_away += et_away

        if aggregate_home != aggregate_away:
            winner = home_pid if aggregate_home > aggregate_away else away_pid
            return TieResult(
                tie_id=tie_id,
                aggregate_home=aggregate_home,
                aggregate_away=aggregate_away,
                winner_participant_id=winner,
                winner_decided_by="extra_time",
            )

        # Penalty shootout — 5 kicks each, then sudden death.
        winner = self._penalty_shootout(home_pid, away_pid)
        return TieResult(
            tie_id=tie_id,
            aggregate_home=aggregate_home,
            aggregate_away=aggregate_away,
            winner_participant_id=winner,
            winner_decided_by="penalties",
        )

    def _penalty_shootout(self, home_pid: int, away_pid: int) -> int:
        """Simulate a penalty shootout; returns the winning participant id."""
        home_score = sum(1 for _ in range(5) if self.rng.random() < 0.75)
        away_score = sum(1 for _ in range(5) if self.rng.random() < 0.75)
        while home_score == away_score:
            h = 1 if self.rng.random() < 0.75 else 0
            a = 1 if self.rng.random() < 0.75 else 0
            home_score += h
            away_score += a
        return home_pid if home_score > away_score else away_pid

    async def _all_round_ties_decided(
        self,
        competition_id: int,
        round_type: str,
    ) -> bool:
        """True iff every tie in the given round has a winner_participant_id."""
        round_id = await self._get_round_id(competition_id, round_type)
        row = await self.session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM ucl_ties
                WHERE round_id = :rid AND winner_participant_id IS NULL
                """
            ),
            {"rid": round_id},
        )
        return int(row.scalar() or 0) == 0

    async def persist_match_result(
        self,
        competition_id: int,
        calendar_event_id: int,
        home_participant_id: int,
        away_participant_id: int,
        home_score: int,
        away_score: int,
        round_type: str,
        leg: Optional[int],
        career_id: Optional[int] = None,
        player_club_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Persist a UCL match result.

        For ``round_type='league_phase'`` simply updates standings via
        ``update_standing``. For knockout rounds, locates the
        corresponding ``ucl_ties`` row by the participant pair (in either
        orientation) and writes scores into the right leg's columns:

          * Convention: ``home_participant_id`` is the higher seed and
            plays the SECOND leg at home. So if the calendar event home
            equals ``tie.home_participant_id``, this is leg 2; if it
            equals ``tie.away_participant_id``, this is leg 1.

        Once both legs are recorded the tie is resolved via
        ``_resolve_tie``; aggregates and the winner are written back. If
        all ties of the round are now decided, ``advance_bracket`` (or
        ``build_round_of_16`` for knockout_playoff) runs. The final is
        handled as a single-leg match.

        Returns the ``winner_participant_id`` when a tie/final is decided,
        else None.
        """
        if round_type == "league_phase":
            await self.update_standing(
                competition_id=competition_id,
                home_participant_id=home_participant_id,
                away_participant_id=away_participant_id,
                home_score=home_score,
                away_score=away_score,
            )
            return None

        if round_type == "final":
            return await self._persist_final_result(
                competition_id=competition_id,
                home_participant_id=home_participant_id,
                away_participant_id=away_participant_id,
                home_score=home_score,
                away_score=away_score,
            )

        # Knockout rounds: locate the tie by participant pair (either
        # orientation).
        round_id = await self._get_round_id(competition_id, round_type)
        tie_row = await self.session.execute(
            text(
                """
                SELECT id, home_participant_id, away_participant_id,
                       leg1_home_score, leg1_away_score,
                       leg2_home_score, leg2_away_score
                FROM ucl_ties
                WHERE round_id = :rid
                  AND (
                    (home_participant_id = :a AND away_participant_id = :b)
                    OR (home_participant_id = :b AND away_participant_id = :a)
                  )
                LIMIT 1
                """
            ),
            {
                "rid": round_id,
                "a": home_participant_id,
                "b": away_participant_id,
            },
        )
        row = tie_row.fetchone()
        if row is None:
            # No matching tie — log and bail (Requirement 12.3).
            return None

        tie_id = int(row[0])
        tie_home = int(row[1])
        tie_away = int(row[2])

        # Determine which leg's columns to write into based on which side
        # is the calendar-event home.
        if home_participant_id == tie_away:
            # Calendar event home == tie's away participant → leg 1.
            actual_leg = 1
            update_sql = (
                "UPDATE ucl_ties "
                "SET leg1_home_score = :hs, leg1_away_score = :as_ "
                "WHERE id = :tid"
            )
        elif home_participant_id == tie_home:
            # Calendar event home == tie's home participant → leg 2.
            actual_leg = 2
            update_sql = (
                "UPDATE ucl_ties "
                "SET leg2_home_score = :hs, leg2_away_score = :as_ "
                "WHERE id = :tid"
            )
        else:
            return None

        await self.session.execute(
            text(update_sql),
            {"tid": tie_id, "hs": home_score, "as_": away_score},
        )

        # Re-fetch the tie to check whether both legs are now complete.
        refreshed = await self.session.execute(
            text(
                """
                SELECT id, home_participant_id, away_participant_id,
                       leg1_home_score, leg1_away_score,
                       leg2_home_score, leg2_away_score
                FROM ucl_ties
                WHERE id = :tid
                """
            ),
            {"tid": tie_id},
        )
        rr = refreshed.fetchone()
        if rr is None:
            return None
        legs_ready = (
            rr[3] is not None
            and rr[4] is not None
            and rr[5] is not None
            and rr[6] is not None
        )
        if not legs_ready:
            return None

        result = self._resolve_tie(
            {
                "id": rr[0],
                "home_participant_id": rr[1],
                "away_participant_id": rr[2],
                "leg1_home_score": rr[3],
                "leg1_away_score": rr[4],
                "leg2_home_score": rr[5],
                "leg2_away_score": rr[6],
            }
        )
        await self.session.execute(
            text(
                """
                UPDATE ucl_ties
                SET aggregate_home = :ah,
                    aggregate_away = :aa,
                    winner_participant_id = :wpid,
                    winner_decided_by = :decided
                WHERE id = :tid
                """
            ),
            {
                "ah": result.aggregate_home,
                "aa": result.aggregate_away,
                "wpid": result.winner_participant_id,
                "decided": result.winner_decided_by,
                "tid": tie_id,
            },
        )

        # If the whole round is decided, advance the bracket.
        if await self._all_round_ties_decided(competition_id, round_type):
            if round_type == "knockout_playoff":
                await self.build_round_of_16(
                    competition_id,
                    career_id=career_id,
                    player_club_id=player_club_id,
                )
            else:
                await self.advance_bracket(
                    competition_id,
                    from_round=round_type,
                    career_id=career_id,
                    player_club_id=player_club_id,
                )

        return result.winner_participant_id

    async def _persist_final_result(
        self,
        competition_id: int,
        home_participant_id: int,
        away_participant_id: int,
        home_score: int,
        away_score: int,
    ) -> Optional[int]:
        """Single-leg final: write leg-1 columns, decide winner, crown."""
        round_id = await self._get_round_id(competition_id, "final")
        tie_row = await self.session.execute(
            text(
                """
                SELECT id, home_participant_id, away_participant_id
                FROM ucl_ties
                WHERE round_id = :rid
                  AND (
                    (home_participant_id = :a AND away_participant_id = :b)
                    OR (home_participant_id = :b AND away_participant_id = :a)
                  )
                LIMIT 1
                """
            ),
            {
                "rid": round_id,
                "a": home_participant_id,
                "b": away_participant_id,
            },
        )
        row = tie_row.fetchone()
        if row is None:
            return None
        tie_id = int(row[0])
        tie_home = int(row[1])
        tie_away = int(row[2])

        # Normalise scores so that "home" is always the tie's
        # ``home_participant_id`` for storage purposes.
        if home_participant_id == tie_home:
            tie_home_score = home_score
            tie_away_score = away_score
        else:
            tie_home_score = away_score
            tie_away_score = home_score

        await self.session.execute(
            text(
                """
                UPDATE ucl_ties
                SET leg1_home_score = :hs, leg1_away_score = :as_
                WHERE id = :tid
                """
            ),
            {"tid": tie_id, "hs": tie_home_score, "as_": tie_away_score},
        )

        # Resolve winner — single match, so use ET/penalties on draw.
        if tie_home_score > tie_away_score:
            winner = tie_home
            decided = "single_match"
            agg_h = tie_home_score
            agg_a = tie_away_score
        elif tie_away_score > tie_home_score:
            winner = tie_away
            decided = "single_match"
            agg_h = tie_home_score
            agg_a = tie_away_score
        else:
            # Extra time + penalties.
            et_h = 1 if self.rng.random() < 0.4 else 0
            et_a = 1 if self.rng.random() < 0.4 else 0
            agg_h = tie_home_score + et_h
            agg_a = tie_away_score + et_a
            if agg_h != agg_a:
                winner = tie_home if agg_h > agg_a else tie_away
                decided = "extra_time"
            else:
                winner = self._penalty_shootout(tie_home, tie_away)
                decided = "penalties"

        await self.session.execute(
            text(
                """
                UPDATE ucl_ties
                SET aggregate_home = :ah,
                    aggregate_away = :aa,
                    winner_participant_id = :wpid,
                    winner_decided_by = :decided
                WHERE id = :tid
                """
            ),
            {
                "ah": agg_h,
                "aa": agg_a,
                "wpid": winner,
                "decided": decided,
                "tid": tie_id,
            },
        )
        await self.crown_champion(competition_id, winner)
        return winner

    # ─── Description builder ──────────────────────────────────────────────

    def _build_event_description(
        self,
        round_type: str,
        matchday: Optional[int],
        leg: Optional[int],
        player_club_id: Optional[int],
        home_club_name: str,
        away_club_name: str,
        is_player_home: Optional[bool],
        opponent_name: Optional[str],
        neutral_venue: Optional[str] = None,
    ) -> str:
        """
        Build a calendar-event description string for a UCL match.

        For matches involving the player's club (i.e. ``player_club_id`` is
        set AND ``opponent_name`` is provided), produce a Russian
        description of the form
        ``"Лига чемпионов, {round_label}: vs {opponent_name} (H|A)"``,
        where the ``(H)`` / ``(A)`` tag is derived from ``is_player_home``.

        For all other matches, produce an English description containing
        both ``home_club_name`` and ``away_club_name`` separated by
        ``" vs "``.

        For the final, the description SHALL contain ``neutral_venue`` as a
        substring.
        """
        # Player is involved when we have an opponent_name AND a player_club_id
        # to anchor the (H)/(A) tag.
        is_player_match = (
            player_club_id is not None
            and opponent_name is not None
            and is_player_home is not None
        )

        if is_player_match:
            tag = "(H)" if is_player_home else "(A)"
            if round_type == "league_phase":
                return (
                    f"Лига чемпионов, тур {matchday}: vs {opponent_name} {tag}"
                )
            if round_type == "knockout_playoff":
                return (
                    f"Лига чемпионов, квалификация плей-офф (матч {leg}): "
                    f"vs {opponent_name} {tag}"
                )
            if round_type == "round_of_16":
                return (
                    f"Лига чемпионов, 1/8 финала (матч {leg}): "
                    f"vs {opponent_name} {tag}"
                )
            if round_type == "quarter_final":
                return (
                    f"Лига чемпионов, 1/4 финала (матч {leg}): "
                    f"vs {opponent_name} {tag}"
                )
            if round_type == "semi_final":
                return (
                    f"Лига чемпионов, 1/2 финала (матч {leg}): "
                    f"vs {opponent_name} {tag}"
                )
            if round_type == "final":
                venue = neutral_venue or UCL_FINAL_VENUE
                return (
                    f"Лига чемпионов, финал: vs {opponent_name} {tag} ({venue})"
                )

        # ── Non-player matches: English descriptions ─────────────────────
        if round_type == "league_phase":
            return (
                f"Champions League Matchday {matchday}: "
                f"{home_club_name} vs {away_club_name}"
            )
        if round_type == "knockout_playoff":
            return (
                f"Champions League Knockout Playoff (leg {leg}): "
                f"{home_club_name} vs {away_club_name}"
            )
        if round_type == "round_of_16":
            return (
                f"Champions League Round of 16 (leg {leg}): "
                f"{home_club_name} vs {away_club_name}"
            )
        if round_type == "quarter_final":
            return (
                f"Champions League Quarter Final (leg {leg}): "
                f"{home_club_name} vs {away_club_name}"
            )
        if round_type == "semi_final":
            return (
                f"Champions League Semi Final (leg {leg}): "
                f"{home_club_name} vs {away_club_name}"
            )
        if round_type == "final":
            venue = neutral_venue or UCL_FINAL_VENUE
            return (
                f"Champions League Final: "
                f"{home_club_name} vs {away_club_name} ({venue})"
            )

        # Fallback — should not happen for known round types.
        return f"Champions League: {home_club_name} vs {away_club_name}"
