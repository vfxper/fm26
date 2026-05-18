"""
Player stats service — attributes goals/assists to individual players
after a match (whether human-played or AI-vs-AI background-run).

Persists per-player season tallies to the `player_match_stats` table
defined in run_local.py:
    (career_id, player_id, club_name, competition, season,
     goals, assists, appearances)

Distribution model:
- Each goal is assigned to one scorer, weighted by attacking position
  bias × CA. Goals are always credited to the scoring side's roster.
- Each assist is assigned to a different player on the same side,
  weighted by creative-position bias × CA. ~80% of goals get an assist
  (some are solo runs / direct free kicks / penalties).
- Appearances: top-11 players by CA on each side get +1 appearance per
  match (rough proxy — we don't track minutes for AI-vs-AI matches).

The competition string is one of:
    "league:<league name>"     — e.g. "league:Premier League"
    "ucl"                      — UEFA Champions League
    "uel"                      — UEFA Europa League
    "uecl"                     — UEFA Conference League
    "domestic_cup:<league>"    — domestic cups
"""

from __future__ import annotations

import random
from typing import List, Dict, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ──────────────────────────────────────────────────────────────────────
# Position weighting tables. Higher weight = more likely to score / assist.
# Positions are FM-CSV strings — we match by substring so "ST", "ST/AM"
# and "AM ST" all hit the striker bucket.
# ──────────────────────────────────────────────────────────────────────

_GOAL_WEIGHTS = (
    ("ST", 10.0),   # strikers — primary scorers
    ("CF", 10.0),
    ("AM", 4.0),    # attacking mids — half as many as ST
    ("AMC", 4.0),
    ("AMR", 3.5),   # wingers
    ("AML", 3.5),
    ("MR", 1.5),
    ("ML", 1.5),
    ("MC", 1.5),    # central mid — third of AM
    ("DM", 0.4),
    ("WB", 0.25),
    ("FB", 0.2),
    ("CB", 0.15),   # defenders rarely score (set pieces)
    ("DC", 0.15),
    ("DR", 0.15),
    ("DL", 0.15),
    ("GK", 0.0),    # GKs effectively never score
)

_ASSIST_WEIGHTS = (
    ("AM", 6.0),
    ("AMC", 6.0),
    ("AMR", 5.0),
    ("AML", 5.0),
    ("MC", 3.5),
    ("MR", 3.0),
    ("ML", 3.0),
    ("DM", 1.5),
    ("ST", 2.5),
    ("CF", 2.5),
    ("WB", 1.0),
    ("FB", 0.7),
    ("CB", 0.2),
    ("DC", 0.2),
    ("DR", 0.2),
    ("DL", 0.2),
    ("GK", 0.0),
)


def _position_weight(position: str, table) -> float:
    """Return the weight for a player's position. Falls back to 0.5."""
    if not position:
        return 0.5
    pos_upper = position.upper()
    # Prefer the longest prefix match, so "AMR" hits before "AM".
    best = 0.5
    best_len = 0
    for token, weight in table:
        if token in pos_upper and len(token) > best_len:
            best = weight
            best_len = len(token)
    return best


# ──────────────────────────────────────────────────────────────────────
# Roster fetching
# ──────────────────────────────────────────────────────────────────────


async def _get_club_roster(
    db: AsyncSession, club_name: str, limit: int = 22
) -> List[Dict]:
    """Top-N players for a club ordered by CA. Falls back to CSV alias."""
    if not club_name:
        return []
    rows = await db.execute(
        text(
            "SELECT id, name, position, ca FROM players "
            "WHERE club = :cn ORDER BY ca DESC LIMIT :n"
        ),
        {"cn": club_name, "n": limit},
    )
    out = [
        {"id": r[0], "name": r[1], "position": r[2] or "", "ca": r[3] or 70}
        for r in rows.fetchall()
    ]
    if not out:
        try:
            from app.data.club_budgets import CLUBS_TO_CSV
            csv_name = CLUBS_TO_CSV.get(club_name)
            if csv_name and csv_name != club_name:
                rows = await db.execute(
                    text(
                        "SELECT id, name, position, ca FROM players "
                        "WHERE club = :cn ORDER BY ca DESC LIMIT :n"
                    ),
                    {"cn": csv_name, "n": limit},
                )
                out = [
                    {"id": r[0], "name": r[1], "position": r[2] or "", "ca": r[3] or 70}
                    for r in rows.fetchall()
                ]
        except Exception:
            pass
    return out


def _weighted_pick(
    roster: List[Dict],
    table,
    exclude_ids: Optional[set] = None,
) -> Optional[Dict]:
    """Pick one player from the roster weighted by position+CA."""
    exclude_ids = exclude_ids or set()
    pool = [p for p in roster if p["id"] not in exclude_ids]
    if not pool:
        return None
    weights = [
        max(0.05, _position_weight(p["position"], table) * (p["ca"] / 100.0))
        for p in pool
    ]
    total = sum(weights)
    if total <= 0:
        return random.choice(pool)
    r = random.uniform(0, total)
    acc = 0.0
    for p, w in zip(pool, weights):
        acc += w
        if acc >= r:
            return p
    return pool[-1]


# ──────────────────────────────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────────────────────────────


async def _upsert_stats(
    db: AsyncSession,
    *,
    career_id: int,
    player_id: int,
    club_name: str,
    competition: str,
    season: int,
    goals: int = 0,
    assists: int = 0,
    appearance: bool = False,
) -> None:
    """Increment a player's tally in player_match_stats."""
    if goals == 0 and assists == 0 and not appearance:
        return
    apps = 1 if appearance else 0
    # SQLite-compatible upsert via SELECT-then-INSERT/UPDATE.
    row = (
        await db.execute(
            text(
                "SELECT id, goals, assists, appearances FROM player_match_stats "
                "WHERE career_id = :c AND player_id = :p "
                "AND competition = :comp AND season = :s"
            ),
            {
                "c": career_id, "p": player_id,
                "comp": competition, "s": season,
            },
        )
    ).fetchone()
    if row:
        await db.execute(
            text(
                "UPDATE player_match_stats "
                "SET goals = goals + :g, assists = assists + :a, "
                "    appearances = appearances + :app, "
                "    club_name = :cn "
                "WHERE id = :rid"
            ),
            {
                "g": goals, "a": assists, "app": apps,
                "cn": club_name or "", "rid": row[0],
            },
        )
    else:
        await db.execute(
            text(
                "INSERT INTO player_match_stats "
                "(career_id, player_id, club_name, competition, season, "
                " goals, assists, appearances) "
                "VALUES (:c, :p, :cn, :comp, :s, :g, :a, :app)"
            ),
            {
                "c": career_id, "p": player_id, "cn": club_name or "",
                "comp": competition, "s": season,
                "g": goals, "a": assists, "app": apps,
            },
        )


# ──────────────────────────────────────────────────────────────────────
# Public API: distribute one match's worth of goals/assists/appearances.
# ──────────────────────────────────────────────────────────────────────


async def attribute_match_to_players(
    db: AsyncSession,
    *,
    career_id: int,
    season: int,
    competition: str,
    home_club: str,
    away_club: str,
    home_score: int,
    away_score: int,
    commit: bool = False,
    goal_events: Optional[list] = None,
) -> Dict:
    """Persist per-player goals/assists/appearances for one match.

    If ``goal_events`` is provided (real scorer/assister data from the
    match engine), use that. Otherwise fall back to weighted random
    pick from the rosters (used for AI-vs-AI background sims that
    don't run the full engine).

    ``goal_events`` shape: list of dicts with keys
        {"side": "home"|"away", "scorer_id": int|None, "scorer_name": str,
         "assister_id": int|None, "assister_name": str|None}

    Returns a small summary dict with the chosen scorer/assist names so
    callers can pipe them into a match feed if desired.
    """
    home_roster = await _get_club_roster(db, home_club)
    away_roster = await _get_club_roster(db, away_club)

    summary: Dict[str, list] = {"goals": [], "assists": []}

    # 1. Appearances: top-11 of each side get +1.
    for p in home_roster[:11]:
        await _upsert_stats(
            db, career_id=career_id, player_id=p["id"],
            club_name=home_club, competition=competition,
            season=season, appearance=True,
        )
    for p in away_roster[:11]:
        await _upsert_stats(
            db, career_id=career_id, player_id=p["id"],
            club_name=away_club, competition=competition,
            season=season, appearance=True,
        )

    # 2a. Real events path — use the engine's scorers/assisters directly.
    if goal_events:
        for ev in goal_events:
            side = ev.get("side", "home")
            club = home_club if side == "home" else away_club
            roster = home_roster if side == "home" else away_roster
            roster_by_id = {p["id"]: p for p in roster}
            roster_by_name = {(p["name"] or "").strip().lower(): p for p in roster}

            scorer = None
            sid = ev.get("scorer_id")
            if sid and sid in roster_by_id:
                scorer = roster_by_id[sid]
            elif ev.get("scorer_name"):
                key = ev["scorer_name"].strip().lower()
                scorer = roster_by_name.get(key)
            if not scorer:
                continue
            await _upsert_stats(
                db, career_id=career_id, player_id=scorer["id"],
                club_name=club, competition=competition,
                season=season, goals=1,
            )
            summary["goals"].append(
                {"side": side, "name": scorer["name"], "club": club}
            )

            assister = None
            aid = ev.get("assister_id")
            if aid and aid in roster_by_id:
                assister = roster_by_id[aid]
            elif ev.get("assister_name"):
                key = ev["assister_name"].strip().lower()
                assister = roster_by_name.get(key)
            if assister and assister["id"] != scorer["id"]:
                await _upsert_stats(
                    db, career_id=career_id, player_id=assister["id"],
                    club_name=club, competition=competition,
                    season=season, assists=1,
                )
                summary["assists"].append(
                    {"side": side, "name": assister["name"], "club": club}
                )

        if commit:
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise
        return summary

    # 2b. Fallback: random weighted pick (AI-vs-AI background sims).
    #    multiple times — strikers do score braces.
    for side, roster, club, n_goals in (
        ("home", home_roster, home_club, home_score),
        ("away", away_roster, away_club, away_score),
    ):
        if n_goals <= 0 or not roster:
            continue
        for _ in range(n_goals):
            scorer = _weighted_pick(roster, _GOAL_WEIGHTS)
            if not scorer:
                continue
            await _upsert_stats(
                db, career_id=career_id, player_id=scorer["id"],
                club_name=club, competition=competition,
                season=season, goals=1,
            )
            summary["goals"].append(
                {"side": side, "name": scorer["name"], "club": club}
            )
            # Assist: 75% chance, picked from same roster excluding the
            # scorer. Penalty/solo-goal heuristic via the 25% no-assist.
            if random.random() < 0.75:
                assister = _weighted_pick(
                    roster, _ASSIST_WEIGHTS,
                    exclude_ids={scorer["id"]},
                )
                if assister:
                    await _upsert_stats(
                        db, career_id=career_id, player_id=assister["id"],
                        club_name=club, competition=competition,
                        season=season, assists=1,
                    )
                    summary["assists"].append(
                        {"side": side, "name": assister["name"], "club": club}
                    )

    if commit:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return summary
