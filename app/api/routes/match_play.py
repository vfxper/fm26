"""
Halftime / interactive match play endpoints.

Three steps:

  POST /api/careers/{cid}/match/{event_id}/start
    → simulate the first half (1..45'), persist state in
      ``match_sessions`` and return the half-time snapshot
      (score, events, lineups, bench).

  POST /api/careers/{cid}/match/{event_id}/sub
    body: { team: "home"|"away", out_name, in_player: {name, position, ca} }
    → apply one substitution (max 5 per team), update state.

  POST /api/careers/{cid}/match/{event_id}/resume
    → simulate the second half (46..90'), persist match result via
      the same path the legacy /simulate endpoint uses, drop the
      session row, return final score.

The match_engine state dict already contains JSON-friendly types
(int, str, list of dicts) — we just need to convert ``events``
(list of MatchEvent dataclass) when serialising and back when
deserialising.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.data.club_budgets import CLUBS
from app.services.match_engine import MatchEngine, MatchEvent


router = APIRouter(tags=["match-play"])


# ───── helpers ────────────────────────────────────────────────────────────

def _serialise_state(state: dict) -> str:
    """JSON-serialise the engine state. Converts MatchEvent dataclasses
    to plain dicts."""
    s = dict(state)
    evs = s.get("events") or []
    s["events"] = [asdict(e) if hasattr(e, "__dataclass_fields__") else e
                   for e in evs]
    return json.dumps(s, ensure_ascii=False)


def _deserialise_state(raw: str) -> dict:
    """Inverse of _serialise_state. Returns a state dict ready to feed
    back into MatchEngine.simulate_second_half."""
    s = json.loads(raw)
    evs = s.get("events") or []
    # Engine accepts both dicts and MatchEvent — leave dicts so the
    # engine converts them once.
    s["events"] = evs
    return s


async def _load_event(
    db: AsyncSession, career_id: int, event_id: int
) -> dict:
    """Fetch the calendar_events row for this match. Raise 404 if missing."""
    r = await db.execute(text(
        "SELECT id, event_date, event_type, home_club_id, away_club_id, "
        "       priority, description "
        "FROM calendar_events WHERE id = :i AND career_id = :c"
    ), {"i": event_id, "c": career_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, f"Calendar event {event_id} not found")
    return {
        "id": int(row[0]),
        "event_date": row[1],
        "event_type": row[2],
        "home_club_id": row[3],
        "away_club_id": row[4],
        "priority": int(row[5] or 0),
        "description": row[6] or "",
    }


def _club_name_by_id(cid: Optional[int]) -> str:
    if not cid or not (1 <= cid <= len(CLUBS)):
        return f"Club #{cid}"
    return CLUBS[cid - 1][0]


async def _get_session_row(
    db: AsyncSession, career_id: int, event_id: int
) -> Optional[dict]:
    r = await db.execute(text(
        "SELECT id, phase, state_json FROM match_sessions "
        "WHERE career_id = :c AND event_id = :e"
    ), {"c": career_id, "e": event_id})
    row = r.fetchone()
    if not row:
        return None
    return {"id": int(row[0]), "phase": row[1], "state_json": row[2]}


# ───── /start ─────────────────────────────────────────────────────────────


@router.post("/{career_id}/match/{event_id}/start")
async def start_match(
    career_id: int,
    event_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulate the first half and return halftime state."""
    # Load event & figure out who's home/away.
    ev = await _load_event(db, career_id, event_id)
    if ev["priority"] < 2:
        raise HTTPException(400, "Этот ивент не является матчем")

    home_id = ev["home_club_id"]
    away_id = ev["away_club_id"]
    home_name = _club_name_by_id(home_id)
    away_name = _club_name_by_id(away_id)

    # Determine if the player is home or away.
    pclub_row = await db.execute(text(
        "SELECT club_id FROM careers WHERE id = :c"
    ), {"c": career_id})
    pclub = pclub_row.scalar()
    is_player_home: Optional[bool] = None
    if pclub == home_id:
        is_player_home = True
    elif pclub == away_id:
        is_player_home = False

    # Reuse existing session if one is already in progress.
    existing = await _get_session_row(db, career_id, event_id)
    if existing and existing["phase"] == "halftime":
        state = _deserialise_state(existing["state_json"])
        return _halftime_response(state, event_id)

    engine = MatchEngine(db)
    state = await engine.simulate_first_half(
        home_id or 0, away_id or 0, home_name, away_name,
        is_player_home=is_player_home, career_id=career_id,
    )

    # Persist.
    raw = _serialise_state(state)
    await db.execute(text(
        "INSERT INTO match_sessions "
        "(career_id, event_id, phase, state_json) "
        "VALUES (:c, :e, 'halftime', :s)"
    ), {"c": career_id, "e": event_id, "s": raw})
    await db.commit()

    return _halftime_response(state, event_id)


def _halftime_response(state: dict, event_id: int) -> dict:
    """Shape the half-time payload returned to the UI."""
    is_player_home = state.get("is_player_home")
    player_team = (
        "home" if is_player_home is True
        else "away" if is_player_home is False
        else None
    )
    starters = state.get(f"{player_team}_players", []) if player_team else []
    bench = state.get(f"{player_team}_bench", []) if player_team else []

    # Convert events to dicts for the UI.
    evs = state.get("events") or []
    events = [
        e if isinstance(e, dict) else asdict(e)
        for e in evs
    ]

    return {
        "event_id": event_id,
        "phase": state.get("phase", "halftime"),
        "minute": state.get("current_minute", 45),
        "home_score": state.get("home_score", 0),
        "away_score": state.get("away_score", 0),
        "home_team_name": state.get("home_club_name", ""),
        "away_team_name": state.get("away_club_name", ""),
        "home_shots": state.get("home_shots", 0),
        "away_shots": state.get("away_shots", 0),
        "home_possession": state.get("home_possession", 50),
        "away_possession": state.get("away_possession", 50),
        "subs_made": state.get("subs_made", {"home": 0, "away": 0}),
        "subs_allowed": 5,
        "player_team": player_team,
        # Formation name (4-3-3 etc) so the frontend can render the same
        # pitch layout users see on the tactics screen.
        "formation": state.get("home_formation" if is_player_home else "away_formation")
                     or state.get("formation")
                     or "4-3-3",
        # starting_xi: {slot_code -> player_id} mirrors what the tactics
        # screen sends. Lets the frontend place each starter on the
        # correct formation slot (CB, LM, ST, ...).
        "starting_xi": state.get("home_starting_xi" if is_player_home else "away_starting_xi") or {},
        "starters": starters,
        "bench": bench,
        "events": events,
    }


# ───── /sub ───────────────────────────────────────────────────────────────


class SubRequest(BaseModel):
    team: str       # "home" or "away"
    out_name: str
    in_player_name: str   # bench player to bring on


@router.post("/{career_id}/match/{event_id}/sub")
async def sub(
    career_id: int,
    event_id: int,
    body: SubRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply one substitution to an in-progress match."""
    sess = await _get_session_row(db, career_id, event_id)
    if not sess or sess["phase"] != "halftime":
        raise HTTPException(400, "Матч не на перерыве")

    state = _deserialise_state(sess["state_json"])

    if body.team not in ("home", "away"):
        raise HTTPException(422, "team должен быть 'home' или 'away'")
    if state["subs_made"][body.team] >= 5:
        raise HTTPException(422, "Лимит замен (5) исчерпан")

    bench = state.get(f"{body.team}_bench", [])
    in_player = next(
        (p for p in bench if p.get("name") == body.in_player_name),
        None,
    )
    if not in_player:
        raise HTTPException(404, f"Игрок {body.in_player_name} не найден на скамейке")

    starters = state.get(f"{body.team}_players", [])
    if not any(p.get("name") == body.out_name for p in starters):
        raise HTTPException(404, f"Игрок {body.out_name} не найден в стартовом составе")

    engine = MatchEngine(db)
    engine._apply_substitution(state, {
        "team": body.team,
        "out_name": body.out_name,
        "in_player": dict(in_player),
    })

    # Persist updated state.
    raw = _serialise_state(state)
    await db.execute(text(
        "UPDATE match_sessions SET state_json = :s, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = :i"
    ), {"s": raw, "i": sess["id"]})
    await db.commit()

    return _halftime_response(state, event_id)


# ───── /resume ────────────────────────────────────────────────────────────


@router.post("/{career_id}/match/{event_id}/resume")
async def resume_match(
    career_id: int,
    event_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulate minutes 46..90, persist final result, drop session row."""
    sess = await _get_session_row(db, career_id, event_id)
    if not sess or sess["phase"] != "halftime":
        raise HTTPException(400, "Матч не на перерыве")

    state = _deserialise_state(sess["state_json"])
    engine = MatchEngine(db)
    result = await engine.simulate_second_half(state, subs=None)

    # Persist match result on the calendar event.
    new_desc_prefix = state.get("home_club_name", "Home") + " vs " + state.get("away_club_name", "Away")
    new_desc = (
        f"{new_desc_prefix} | RESULT: {result.home_score}-{result.away_score}"
    )
    await db.execute(text(
        "UPDATE calendar_events SET description = :d, is_locked = 1 "
        "WHERE id = :e AND career_id = :c"
    ), {"d": new_desc, "e": event_id, "c": career_id})
    await db.execute(text(
        "DELETE FROM match_sessions WHERE id = :i"
    ), {"i": sess["id"]})

    # Attribute goals/assists/appearances to actual players so the
    # stats screen shows real names. Detect competition from the
    # calendar event payload (UCL / league / cup).
    try:
        from app.services.player_stats_service import attribute_match_to_players
        from app.data.club_budgets import CLUBS as ALL_CLUBS
        # Build goal_events from real engine MatchEvent stream so the
        # stats table gets the actual scorers (instead of a weighted
        # random pick). Each MatchEvent has player_name + team
        # ("home"/"away"); the engine doesn't currently track assists
        # so we leave assister fields blank — the service can still
        # pick an assister from the roster as fallback.
        goal_events_list = []
        try:
            for ev in (result.events or []):
                if getattr(ev, "event_type", None) == "goal":
                    goal_events_list.append({
                        "side": getattr(ev, "team", "home") or "home",
                        "scorer_id": None,
                        "scorer_name": getattr(ev, "player_name", None) or "",
                        "assister_id": None,
                        "assister_name": None,
                    })
        except Exception:
            goal_events_list = []
        # Read event metadata to figure out competition.
        ev = (await db.execute(text(
            "SELECT event_type, competition_id, description "
            "FROM calendar_events WHERE id = :e"
        ), {"e": event_id})).fetchone()
        comp_label = "league:?"
        if ev:
            etype = (ev[0] or "").lower()
            if etype in ("ucl", "ucl_match"):
                comp_label = "ucl"
            elif etype in ("uel", "uel_match"):
                comp_label = "uel"
            elif etype in ("uecl", "uecl_match"):
                comp_label = "uecl"
            elif etype in ("league_match", "match"):
                club_row = (await db.execute(text(
                    "SELECT club_id FROM careers WHERE id = :c"
                ), {"c": career_id})).fetchone()
                if club_row and club_row[0]:
                    ccid = int(club_row[0])
                    if 1 <= ccid <= len(ALL_CLUBS):
                        lg = ALL_CLUBS[ccid - 1][3]
                        if lg:
                            comp_label = f"league:{lg}"
        season_row = (await db.execute(text(
            "SELECT current_season FROM careers WHERE id = :c"
        ), {"c": career_id})).fetchone()
        season = int(season_row[0]) if season_row and season_row[0] else 1
        await attribute_match_to_players(
            db,
            career_id=career_id,
            season=season,
            competition=comp_label,
            home_club=state.get("home_club_name", ""),
            away_club=state.get("away_club_name", ""),
            home_score=result.home_score,
            away_score=result.away_score,
            commit=False,
            goal_events=goal_events_list or None,
        )
    except Exception as e:  # noqa: BLE001
        # Stats are nice-to-have — never block match completion on them.
        print(f"  stats attribution warning: {e}")

    await db.commit()

    return {
        "event_id": event_id,
        "phase": "finished",
        "home_score": result.home_score,
        "away_score": result.away_score,
        "home_team_name": result.home_team_name,
        "away_team_name": result.away_team_name,
        "home_shots": result.home_shots,
        "away_shots": result.away_shots,
        "home_possession": result.home_possession,
        "away_possession": result.away_possession,
        "events": [asdict(e) if hasattr(e, "__dataclass_fields__") else e
                   for e in result.events],
    }
