"""
Background match runner — keeps standings tables in sync with the in-game date.

Each in-game day this module simulates every league/UCL match that is
NOT the player's own match. Idempotent — every fixture is marked
``played`` after simulation so calling this twice for the same date
won't double-count goals.

The player's calendar event (priority=6 league or UCL on-calendar) is
NEVER touched here; they play it themselves from the Match tab.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.club_budgets import CLUBS


# ──────────────────────────────────────────────────────────────────────
# Score sampling
# ──────────────────────────────────────────────────────────────────────


def _sample_score(home_ca: int, away_ca: int,
                   home_buff: float = 0.0, away_buff: float = 0.0) -> Tuple[int, int]:
    """Return (home_score, away_score) using xG-driven Poisson sampling.

    `home_buff` and `away_buff` are tactic-derived modifiers in -0.6..+0.6
    range, added to the team's xG. They encode the buff/debuff trade-off
    of mentality: very-attacking gives +0.5 to your xG but +0.3 to the
    opponent's (you're more open at the back), very-defensive gives
    -0.4 to yours but -0.4 to theirs (parking the bus).
    """
    base = 1.4
    delta = (home_ca - away_ca) / 40.0
    home_xg = max(0.2, min(5.5, base + 0.3 + delta + home_buff))
    away_xg = max(0.2, min(5.5, base - delta + away_buff))
    return _poisson(home_xg), _poisson(away_xg)


# ──────────────────────────────────────────────────────────────────────
# Tactic effect tables
# ──────────────────────────────────────────────────────────────────────

# Mentality buffs as (own_xg_delta, opp_xg_delta).
# very_defensive: park the bus — both your and their attacks dry up.
# defensive:      cautious — moderate dampening on both sides.
# balanced:       no effect.
# attacking:      push for goals — your xG up, theirs slightly up.
# very_attacking: all-out attack — big xG up for both.
_MENTALITY_BUFFS = {
    "very_defensive": (-0.40, -0.40),
    "defensive":      (-0.20, -0.15),
    "balanced":       ( 0.00,  0.00),
    "attacking":      (+0.25, +0.10),
    "very_attacking": (+0.50, +0.30),
    # legacy aliases
    "cautious":       (-0.10, -0.05),
    "positive":       (+0.15, +0.05),
}


def _pressing_buff(pressing_str: Optional[str]) -> tuple:
    """Pressing → (own_xg_delta, opp_xg_delta).

    pressing_str is "off" / "0".."100" or legacy enum (low/medium/high/extreme).

    Off:        opp +0.10 (free passes for them), own -0.05 (slow buildup).
    Light (1-30):  small win/loss.
    Medium (31-70): balanced.
    High (71-90):  +0.15 own, but stamina drain → +0.10 opp counter.
    Extreme (91+): +0.25 own, +0.20 opp (you get caught on counters).
    """
    s = str(pressing_str or "medium").lower()
    if s in ("off", "none", "0"):
        return (-0.05, +0.10)
    n = None
    if s.isdigit():
        n = int(s)
    elif s == "low":
        n = 25
    elif s == "medium":
        n = 50
    elif s == "high":
        n = 75
    elif s == "extreme":
        n = 100
    if n is None:
        n = 50
    n = max(0, min(100, n))
    if n <= 30:
        return (0.0, +0.05)
    if n <= 70:
        return (+0.05, 0.00)
    if n <= 90:
        return (+0.15, +0.10)
    return (+0.25, +0.20)


async def _read_career_tactics(
    db: AsyncSession, career_id: int
) -> Tuple[float, float]:
    """Return (own_xg_buff, opp_xg_buff) from the career's saved tactic.

    Combines mentality + pressing. Returns (0, 0) if no row found.
    """
    try:
        r = await db.execute(text(
            "SELECT mentality, pressing FROM career_tactics WHERE career_id=:c"
        ), {"c": career_id})
        row = r.fetchone()
    except Exception:
        return (0.0, 0.0)
    if not row:
        return (0.0, 0.0)
    ment = (row[0] or "balanced").lower()
    press = row[1] or "medium"
    m_own, m_opp = _MENTALITY_BUFFS.get(ment, (0.0, 0.0))
    p_own, p_opp = _pressing_buff(press)
    return (m_own + p_own, m_opp + p_opp)


def _poisson(mean: float) -> int:
    """Knuth's algorithm — fast for one match."""
    L = pow(2.71828, -mean)
    k = 0
    p = 1.0
    while p > L and k < 9:
        k += 1
        p *= random.random()
    return max(0, k - 1)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


async def _team_avg_ca(db: AsyncSession, club_name: str) -> int:
    """Average CA of the top-11 players for a club. Defaults to 110."""
    if not club_name:
        return 110
    rows = await db.execute(
        text(
            "SELECT ca FROM players WHERE club = :cn ORDER BY ca DESC LIMIT 11"
        ),
        {"cn": club_name},
    )
    cas = [r[0] for r in rows.fetchall() if r[0]]
    if not cas:
        try:
            from app.data.club_budgets import CLUBS_TO_CSV
            csv_name = CLUBS_TO_CSV.get(club_name)
            if csv_name and csv_name != club_name:
                rows = await db.execute(
                    text(
                        "SELECT ca FROM players WHERE club = :cn "
                        "ORDER BY ca DESC LIMIT 11"
                    ),
                    {"cn": csv_name},
                )
                cas = [r[0] for r in rows.fetchall() if r[0]]
        except Exception:
            pass
    if not cas:
        return 110
    return sum(cas) // len(cas)


async def _player_club_name(db: AsyncSession, career_id: int) -> Optional[str]:
    pc = await db.execute(
        text("SELECT club_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = pc.fetchone()
    if not row or not row[0]:
        return None
    cid = row[0]
    if 1 <= cid <= len(CLUBS):
        return CLUBS[cid - 1][0]
    if cid >= 1000:
        try:
            from app.data.ucl_config import UCL_PARTICIPANTS
            seed = cid - 1000
            if 1 <= seed <= len(UCL_PARTICIPANTS):
                return UCL_PARTICIPANTS[seed - 1][0]
        except Exception:
            pass
    return None


async def _read_career_season(db: AsyncSession, career_id: int) -> int:
    """Return the career's current season number (defaults to 1)."""
    try:
        r = await db.execute(
            text("SELECT current_season FROM careers WHERE id = :c"),
            {"c": career_id},
        )
        row = r.fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception:
        pass
    return 1


# ──────────────────────────────────────────────────────────────────────
# Domestic league background simulation
# ──────────────────────────────────────────────────────────────────────


def _circle_method_round_robin(teams: List[str]) -> List[List[Tuple[str, str]]]:
    """Round-robin schedule. MUST mirror CalendarEngine's algorithm so
    matchday N here lines up with matchday N in the calendar."""
    teams = list(teams)
    if len(teams) % 2 == 1:
        teams.append("__BYE__")
    n = len(teams)
    out = []
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home != "__BYE__" and away != "__BYE__":
                pairs.append((home, away))
        out.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    second = [[(a, h) for h, a in md] for md in out]
    return out + second


async def _simulate_league_background(
    db: AsyncSession,
    career_id: int,
    on_date: str,
    notifications: List[str],
) -> None:
    """Simulate every league fixture (priority=6) on `on_date` that does
    NOT involve the player. Each fixture is locked after simulation so
    we never double-count.
    """
    player_club = await _player_club_name(db, career_id)
    if not player_club:
        return

    # Player's own league fixture(s) for this date.
    rows = await db.execute(
        text(
            """
            SELECT id, description
            FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND event_date = :d
              AND priority = 6
              AND is_cancelled = 0
              AND description LIKE '%Matchday%'
              AND description NOT LIKE '%RESULT:%'
            """
        ),
        {"cid": career_id, "d": on_date},
    )
    fixtures = list(rows.fetchall())

    md_num = None
    league_label = None
    for fx in fixtures:
        desc = fx[1] or ""
        if "Matchday " in desc:
            try:
                md_num = int(desc.split("Matchday ")[1].split(":")[0].strip())
                league_label = desc.split("Matchday")[0].strip()
                break
            except (IndexError, ValueError):
                pass
    if md_num is None:
        return

    # Resolve the player's domestic league.
    player_league = None
    for cname, _, _, cleague in CLUBS:
        if cname == player_club:
            player_league = cleague
            break
    if not player_league:
        return
    league_clubs = [c[0] for c in CLUBS if c[3] == player_league]
    if len(league_clubs) < 4:
        return

    pairs_by_md = _circle_method_round_robin(league_clubs)
    if md_num < 1 or md_num > len(pairs_by_md):
        return
    today_pairs = pairs_by_md[md_num - 1]

    # Idempotency cache: which (home, away) pairs have ALREADY been
    # auto-simulated for this league+matchday in this career? Stored
    # as a side-table marker via the in-memory `_league_tables` dict.
    # We use a simple per-career set.
    from app.api.routes.matches import _update_league_table

    sentinel_tag = f"__bg_md_{player_league}_{md_num}__"
    if not hasattr(_update_league_table, "_bg_done"):
        _update_league_table._bg_done = {}  # type: ignore[attr-defined]
    bg_done: Dict[int, Set[str]] = _update_league_table._bg_done  # type: ignore[attr-defined]
    done_set = bg_done.setdefault(career_id, set())
    if sentinel_tag in done_set:
        return  # already simulated for this matchday in this career

    background_count = 0
    # Determine current season once for stats persistence.
    season = await _read_career_season(db, career_id)
    competition_label = f"league:{player_league}" if player_league else "league:?"

    from app.services.player_stats_service import attribute_match_to_players

    for home, away in today_pairs:
        if home == player_club or away == player_club:
            continue
        home_ca = await _team_avg_ca(db, home)
        away_ca = await _team_avg_ca(db, away)
        h, a = _sample_score(home_ca + 5, away_ca)
        _update_league_table(career_id, home, away, h, a)
        # Distribute goals/assists/appearances to actual players so the
        # "Top scorers / Top assists" tables on the frontend reflect
        # every AI-vs-AI league match in the universe.
        try:
            await attribute_match_to_players(
                db,
                career_id=career_id,
                season=season,
                competition=competition_label,
                home_club=home,
                away_club=away,
                home_score=h,
                away_score=a,
                commit=False,
            )
        except Exception:
            pass
        background_count += 1

    if background_count:
        # Single commit for all matchday stats — much cheaper than
        # committing per match.
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        done_set.add(sentinel_tag)
        # Same as the UCL block below — these auto-simulations are
        # noise that doesn't change anything the user can act on.
        # Keep them silent.
        _ = (player_league, md_num, background_count)


# ──────────────────────────────────────────────────────────────────────
# UCL background simulation
# ──────────────────────────────────────────────────────────────────────


async def _simulate_ucl_background(
    db: AsyncSession,
    career_id: int,
    on_date: str,
    notifications: List[str],
) -> Optional[str]:
    """Simulate every UCL match for the matchday tied to `on_date` that
    is NOT the player's match. Reads pairings from
    ``ucl_phase_matchups`` and marks each row ``played=1``.

    Also kicks off ``finalize_league_phase`` once all 8 matchdays are
    complete.
    """
    cr = await db.execute(
        text(
            "SELECT id FROM competitions "
            "WHERE name = 'Champions League' "
            "ORDER BY id DESC LIMIT 1"
        )
    )
    cr_row = cr.fetchone()
    if not cr_row:
        return None
    competition_id = int(cr_row[0])

    # Player's UCL participant id (if any).
    pcr = await db.execute(
        text("SELECT club_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    pc_row = pcr.fetchone()
    player_club_id = pc_row[0] if pc_row else None
    player_pid: Optional[int] = None
    if player_club_id is not None:
        r = await db.execute(
            text(
                "SELECT id FROM ucl_participants "
                "WHERE competition_id = :cid AND club_id = :pcid"
            ),
            {"cid": competition_id, "pcid": player_club_id},
        )
        v = r.scalar()
        if v is not None:
            player_pid = int(v)

    # Identify today's matchday from the player's calendar.
    md_event = await db.execute(
        text(
            """
            SELECT description FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND event_date = :d
              AND competition_id = :comp
            ORDER BY id LIMIT 1
            """
        ),
        {"cid": career_id, "d": on_date, "comp": competition_id},
    )
    md_row = md_event.fetchone()
    md_num: Optional[int] = None
    if md_row:
        desc = md_row[0] or ""
        for needle in ("тур ", "Matchday "):
            if needle in desc:
                try:
                    md_num = int(
                        desc.split(needle)[1].split(":")[0].split(" ")[0].strip()
                    )
                    break
                except (IndexError, ValueError):
                    pass

    if md_num is None:
        # No UCL game today for the player; nothing to do.
        return None

    # Fetch UNPLAYED matchups for this matchday.
    rows = await db.execute(
        text(
            "SELECT id, home_participant_id, away_participant_id "
            "FROM ucl_phase_matchups "
            "WHERE competition_id = :c AND matchday = :md AND played = 0"
        ),
        {"c": competition_id, "md": md_num},
    )
    unplayed = list(rows.fetchall())
    if not unplayed:
        return None

    # Build participant_id → (club_name, club_id) cache.
    p_rows = await db.execute(
        text(
            "SELECT id, club_name, club_id FROM ucl_participants "
            "WHERE competition_id = :c"
        ),
        {"c": competition_id},
    )
    pcache = {int(r[0]): (r[1], r[2]) for r in p_rows.fetchall()}

    # Lazy-import the generator to reuse update_standing.
    from app.services.ucl_generator import UCLGenerator
    gen = UCLGenerator(db)

    simulated = 0
    season = await _read_career_season(db, career_id)
    from app.services.player_stats_service import attribute_match_to_players

    for tie_id, home_pid, away_pid in unplayed:
        home_pid = int(home_pid)
        away_pid = int(away_pid)
        # Skip the player's own match; they'll play it.
        if player_pid is not None and (
            home_pid == player_pid or away_pid == player_pid
        ):
            continue
        home_name = pcache.get(home_pid, ("?", None))[0]
        away_name = pcache.get(away_pid, ("?", None))[0]
        home_ca = await _team_avg_ca(db, home_name)
        away_ca = await _team_avg_ca(db, away_name)
        h, a = _sample_score(home_ca + 5, away_ca)
        await gen.update_standing(
            competition_id=competition_id,
            home_participant_id=home_pid,
            away_participant_id=away_pid,
            home_score=h,
            away_score=a,
        )
        # UCL stats — same model as league.
        try:
            await attribute_match_to_players(
                db,
                career_id=career_id,
                season=season,
                competition="ucl",
                home_club=home_name,
                away_club=away_name,
                home_score=h,
                away_score=a,
                commit=False,
            )
        except Exception:
            pass
        await db.execute(
            text("UPDATE ucl_phase_matchups SET played = 1 WHERE id = :tid"),
            {"tid": tie_id},
        )
        simulated += 1

    if simulated:
        # Auto-simulating background league matches is a routine
        # plumbing task — we deliberately don't surface it to the user.
        # The user sees only events that affect THEIR career (their
        # match results, transfer offers, board reactions etc.).
        pass

    summary: Optional[str] = None
    # Last matchday → kick off knockout playoff once all 36 played 8.
    if md_num == 8:
        cnt = await db.execute(
            text(
                "SELECT COUNT(*) FROM ucl_standings "
                "WHERE competition_id = :c AND played = 8"
            ),
            {"c": competition_id},
        )
        if int(cnt.scalar() or 0) == 36:
            try:
                await gen.finalize_league_phase(
                    competition_id, career_id=career_id,
                    player_club_id=player_club_id,
                )
                summary = "лига завершена, начинается плей-офф"
            except Exception as e:
                notifications.append(f"⚠ ЛЧ финализация: {e}")

    await db.commit()
    return summary


async def run_background_matches_for_day(
    db: AsyncSession,
    career_id: int,
    on_date: str,
) -> Dict[str, object]:
    """Top-level entry point used by ``advance_day``."""
    notifications: List[str] = []
    await _simulate_league_background(db, career_id, on_date, notifications)
    ucl_summary = await _simulate_ucl_background(db, career_id, on_date, notifications)
    return {"notifications": notifications, "ucl_advanced": ucl_summary}
