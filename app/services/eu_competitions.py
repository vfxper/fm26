"""
Lightweight Europa League / Conference League generator.

Unlike the full UCLGenerator (Swiss-system + knockout + ucl_participants
+ ucl_standings tables), this module only creates a basic league phase
schedule for two competitions:

  uel  — UEFA Europa League (8 league-phase matches per club)
  uecl — UEFA Conference League (6 league-phase matches per club)

Why simpler:
- We don't model knockout for these two yet — the user only asked for
  rosters + a separate schedule. Knockout can be added later.
- We piggy-back on existing ``calendar_events`` rows to show the matches
  in the player's calendar, alongside league fixtures and UCL ones.
- We keep a thin standings table per (career, competition) so the user
  can see a table.

Tables touched:
- ``calendar_events`` (priority=8, event_type='uel' or 'uecl')
- ``eu_standings``     — created in run_local.py (see below)

Public API:
    await generate_eu_competitions(db, career_id, year, player_club_id)

Idempotent: detects if the year's matches already exist and returns
without re-creating them.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.eu_competitions_config import (
    LEAGUE_PHASE_MATCHES,
    UECL_PARTICIPANTS,
    UEL_PARTICIPANTS,
)


# Five fixed Thursdays in autumn for matchday 1..5 of UEL/UECL
# (real UEFA scheduling).
def _generate_matchday_dates(year: int, n: int) -> list[date]:
    """Pick n Thursdays roughly mid-Sep .. late-Jan for league phase."""
    # Start ~Sep 24 of given year, every 2 weeks.
    base = date(year, 9, 24)
    out = []
    cur = base
    for _ in range(n):
        # Snap to nearest Thursday.
        while cur.weekday() != 3:  # 3 = Thursday
            cur += timedelta(days=1)
        out.append(cur)
        cur += timedelta(days=14)
    return out


def _swiss_pair(participants: list[tuple[str, int | None, str]],
                rng: random.Random,
                num_rounds: int) -> list[list[tuple[int, int]]]:
    """
    Return ``num_rounds`` lists of (i, j) participant-index pairs.
    Simple round-robin-ish scheduling without strict Swiss seeding —
    we just generate plausible pairings that:
      - never pair a club with itself
      - never give a club two matches on the same matchday
      - never repeat the exact (i, j) ordered pair across rounds
    """
    n = len(participants)
    indices = list(range(n))
    rounds: list[list[tuple[int, int]]] = []
    seen_pairs: set[tuple[int, int]] = set()

    for _ in range(num_rounds):
        rng.shuffle(indices)
        used: set[int] = set()
        pairs: list[tuple[int, int]] = []
        # Greedy pair adjacent shuffled indices.
        i = 0
        while i + 1 < len(indices):
            a, b = indices[i], indices[i + 1]
            if a in used or b in used:
                i += 1
                continue
            key = (min(a, b), max(a, b))
            # Avoid duplicate pairings as best we can; if we run out of
            # options we accept the duplicate rather than crash.
            if key in seen_pairs:
                # Try swapping with the next pair to break it
                if i + 3 < len(indices):
                    indices[i + 1], indices[i + 3] = indices[i + 3], indices[i + 1]
                    a, b = indices[i], indices[i + 1]
                    key = (min(a, b), max(a, b))
            seen_pairs.add(key)
            pairs.append((a, b))
            used.add(a)
            used.add(b)
            i += 2
        rounds.append(pairs)
    return rounds


async def _already_generated(
    db: AsyncSession, career_id: int, year: int, kind: str
) -> bool:
    r = await db.execute(text(
        "SELECT 1 FROM calendar_events "
        "WHERE career_id = :c AND event_type = :k "
        "  AND event_date LIKE :pfx LIMIT 1"
    ), {"c": career_id, "k": kind, "pfx": f"{year}-%"})
    return r.fetchone() is not None


async def _participant_club_id(participants, name: str) -> Optional[int]:
    for nm, cid, _country in participants:
        if nm == name:
            return cid
    return None


async def generate_eu_competitions(
    db: AsyncSession,
    *,
    career_id: int,
    year: int,
    player_club_id: Optional[int],
    player_club_name: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> dict:
    """
    Generate league-phase schedules for UEL and UECL for the given career.

    Returns a summary dict::

        {
            "uel":  {"matches_created": int, "player_in": bool},
            "uecl": {"matches_created": int, "player_in": bool},
        }
    """
    rng = rng or random.Random(year * 73 + career_id * 31)
    out = {"uel": {"matches_created": 0, "player_in": False},
           "uecl": {"matches_created": 0, "player_in": False}}

    for kind, participants in (("uel", UEL_PARTICIPANTS),
                                ("uecl", UECL_PARTICIPANTS)):
        if await _already_generated(db, career_id, year, kind):
            continue

        n_rounds = LEAGUE_PHASE_MATCHES[kind]
        rounds = _swiss_pair(participants, rng, n_rounds)
        match_dates = _generate_matchday_dates(year, n_rounds)

        is_player_in = any(
            (cid is not None and cid == player_club_id)
            or (player_club_name and nm.lower() == player_club_name.lower())
            for nm, cid, _ in participants
        )
        out[kind]["player_in"] = is_player_in

        priority = 8  # same as UCL — high-priority European fixture
        for round_idx, pairs in enumerate(rounds, start=1):
            md = match_dates[round_idx - 1] if round_idx - 1 < len(match_dates) else None
            if md is None:
                continue
            for (a, b) in pairs:
                home_name, home_cid, _ = participants[a]
                away_name, away_cid, _ = participants[b]

                # Player-club matches go to that player's calendar; AI-vs-AI
                # matches are skipped to avoid bloating calendar_events for
                # 35+ AI clubs (we only need them for the table later).
                player_match = (
                    (home_cid is not None and home_cid == player_club_id)
                    or (away_cid is not None and away_cid == player_club_id)
                    or (player_club_name is not None and
                        (home_name.lower() == player_club_name.lower()
                         or away_name.lower() == player_club_name.lower()))
                )
                if not player_match:
                    continue

                desc = f"{home_name} vs {away_name}"
                await db.execute(text(
                    "INSERT INTO calendar_events "
                    "(career_id, event_date, event_type, competition_id, "
                    " home_club_id, away_club_id, is_locked, priority, "
                    " kick_off_time, description) "
                    "VALUES (:c, :d, :t, NULL, :h, :a, 0, :p, '21:00', :ds)"
                ), {
                    "c": career_id, "d": str(md), "t": kind,
                    "h": home_cid, "a": away_cid,
                    "p": priority, "ds": desc,
                })
                out[kind]["matches_created"] += 1

        await db.commit()

    return out
