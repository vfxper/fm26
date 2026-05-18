"""
Calendar API Endpoints
GET  /api/calendar/{career_id}/month - Monthly events
GET  /api/calendar/{career_id}/day - Day detail
POST /api/calendar/{career_id}/template - Create recurring template
GET  /api/calendar/{career_id}/template - Get templates
POST /api/calendar/{career_id}/template/{template_id}/apply - Apply template to month
PUT  /api/calendar/{career_id}/event/{event_id}/travel-override - Override travel
GET  /api/calendar/{career_id}/reminders - Active reminders
POST /api/calendar/{career_id}/reminders/{reminder_id}/dismiss - Dismiss reminder
"""

import json
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/calendar", tags=["calendar"])


# === Request/Response Models ===

class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    day_assignments: dict = Field(..., description="Day-of-week to event type mapping")


class TravelOverrideRequest(BaseModel):
    departure_time: Optional[str] = None
    transport_mode: Optional[str] = None


class FriendlyCreatePayload(BaseModel):
    event_date: str = Field(..., description="YYYY-MM-DD")
    opponent_club_id: int = Field(..., ge=1)
    match_type: str = Field(..., pattern="^(home|away|commercial_tour|closed_door)$")
    kick_off_time: str = Field("18:00")
    tour_venue_id: Optional[int] = None
    description_suffix: Optional[str] = Field(None, max_length=80)


# === Endpoints ===

@router.get("/{career_id}/month")
async def get_month_events(
    career_id: int,
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    types: Optional[str] = Query(None, description="Comma-separated event types filter"),
    team: Optional[str] = Query(None, description="Team filter: first_team, youth, loaned"),
    db: AsyncSession = Depends(get_db),
):
    """Get all calendar events for a given month with optional filtering."""
    # Build date range for the month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    # Base query - exclude cancelled events
    query = """
        SELECT id, event_date, event_type, competition_id, home_club_id, away_club_id,
               is_locked, priority, kick_off_time, weather_data, description,
               travel_data, original_date, reschedule_reason, template_id
        FROM calendar_events
        WHERE career_id = :career_id
          AND event_date >= :start_date
          AND event_date < :end_date
          AND is_cancelled = 0
    """
    params = {"career_id": career_id, "start_date": start_date, "end_date": end_date}

    # Type filter
    if types:
        type_list = [t.strip() for t in types.split(",") if t.strip()]
        if type_list:
            placeholders = ", ".join(f":type_{i}" for i in range(len(type_list)))
            query += f" AND event_type IN ({placeholders})"
            for i, t in enumerate(type_list):
                params[f"type_{i}"] = t

    query += " ORDER BY event_date, priority DESC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    events = []
    for row in rows:
        events.append({
            "id": row[0],
            "event_date": row[1],
            "event_type": row[2],
            "competition_id": row[3],
            "home_club_id": row[4],
            "away_club_id": row[5],
            "is_locked": bool(row[6]),
            "priority": row[7],
            "kick_off_time": row[8],
            "weather_data": json.loads(row[9]) if row[9] else None,
            "description": row[10],
            "travel_data": json.loads(row[11]) if row[11] else None,
            "original_date": row[12],
            "reschedule_reason": row[13],
            "template_id": row[14],
        })

    # Get next milestone for countdown
    today_str = str(date.today())
    milestone_result = await db.execute(
        text("""
            SELECT event_date, description FROM calendar_events
            WHERE career_id = :career_id
              AND event_type = 'milestone'
              AND event_date >= :today
              AND is_cancelled = 0
            ORDER BY event_date
            LIMIT 1
        """),
        {"career_id": career_id, "today": today_str},
    )
    milestone_row = milestone_result.fetchone()
    next_milestone = None
    if milestone_row:
        next_milestone = {
            "date": milestone_row[0],
            "description": milestone_row[1],
        }

    return {
        "year": year,
        "month": month,
        "events": events,
        "next_milestone": next_milestone,
    }


@router.get("/{career_id}/day")
async def get_day_events(
    career_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """Get all events for a specific date."""
    result = await db.execute(
        text("""
            SELECT id, event_date, event_type, competition_id, home_club_id, away_club_id,
                   is_locked, priority, kick_off_time, weather_data, description,
                   travel_data, original_date, reschedule_reason, template_id
            FROM calendar_events
            WHERE career_id = :career_id
              AND event_date = :event_date
              AND is_cancelled = 0
            ORDER BY priority DESC, kick_off_time
        """),
        {"career_id": career_id, "event_date": date},
    )
    rows = result.fetchall()

    events = []
    for row in rows:
        events.append({
            "id": row[0],
            "event_date": row[1],
            "event_type": row[2],
            "competition_id": row[3],
            "home_club_id": row[4],
            "away_club_id": row[5],
            "is_locked": bool(row[6]),
            "priority": row[7],
            "kick_off_time": row[8],
            "weather_data": json.loads(row[9]) if row[9] else None,
            "description": row[10],
            "travel_data": json.loads(row[11]) if row[11] else None,
            "original_date": row[12],
            "reschedule_reason": row[13],
            "template_id": row[14],
        })

    return {"date": date, "events": events}


@router.post("/{career_id}/template")
async def create_template(
    career_id: int,
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a recurring weekly template."""
    day_assignments_json = json.dumps(request.day_assignments)

    await db.execute(
        text("""
            INSERT INTO recurring_templates (career_id, name, day_assignments, is_active)
            VALUES (:career_id, :name, :day_assignments, 1)
        """),
        {
            "career_id": career_id,
            "name": request.name,
            "day_assignments": day_assignments_json,
        },
    )
    await db.commit()

    # Get the created template ID
    id_result = await db.execute(text("SELECT last_insert_rowid()"))
    template_id = id_result.scalar() or 0

    return {
        "id": template_id,
        "career_id": career_id,
        "name": request.name,
        "day_assignments": request.day_assignments,
        "is_active": True,
    }


@router.get("/{career_id}/template")
async def get_templates(
    career_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all recurring templates for a career."""
    result = await db.execute(
        text("""
            SELECT id, name, day_assignments, is_active
            FROM recurring_templates
            WHERE career_id = :career_id
            ORDER BY id DESC
        """),
        {"career_id": career_id},
    )
    rows = result.fetchall()

    templates = []
    for row in rows:
        templates.append({
            "id": row[0],
            "name": row[1],
            "day_assignments": json.loads(row[2]) if row[2] else {},
            "is_active": bool(row[3]),
        })

    return {"templates": templates}


@router.post("/{career_id}/template/{template_id}/apply")
async def apply_template(
    career_id: int,
    template_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Apply a recurring template to a specific month."""
    # Get the template
    result = await db.execute(
        text("SELECT day_assignments FROM recurring_templates WHERE id = :tid AND career_id = :cid"),
        {"tid": template_id, "cid": career_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Template not found")

    day_assignments = json.loads(row[0]) if row[0] else {}

    # Day name to weekday number mapping (Monday=0)
    day_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }

    # Generate events for each day of the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Get existing locked/match events for the month to avoid conflicts
    existing_result = await db.execute(
        text("""
            SELECT event_date FROM calendar_events
            WHERE career_id = :career_id
              AND event_date >= :start
              AND event_date < :end
              AND is_cancelled = 0
              AND (event_type = 'match' OR event_type = 'international' OR is_locked = 1)
        """),
        {"career_id": career_id, "start": str(start_date), "end": str(end_date)},
    )
    blocked_dates = {r[0] for r in existing_result.fetchall()}

    created_events = []
    current = start_date
    while current < end_date:
        weekday = current.weekday()
        # Find matching day assignment
        for day_name, day_num in day_map.items():
            if day_num == weekday and day_name in day_assignments:
                event_type = day_assignments[day_name]
                # Skip if date is blocked
                if str(current) in blocked_dates or current in blocked_dates:
                    continue
                # Insert the event
                await db.execute(
                    text("""
                        INSERT INTO calendar_events
                        (career_id, event_date, event_type, is_locked, priority,
                         description, is_cancelled, template_id)
                        VALUES
                        (:career_id, :event_date, :event_type, 0, 3,
                         :description, 0, :template_id)
                    """),
                    {
                        "career_id": career_id,
                        "event_date": str(current),
                        "event_type": event_type,
                        "description": f"Template: {event_type}",
                        "template_id": template_id,
                    },
                )
                created_events.append({
                    "event_date": str(current),
                    "event_type": event_type,
                })
                break
        current += timedelta(days=1)

    await db.commit()

    return {
        "applied": True,
        "template_id": template_id,
        "month": month,
        "year": year,
        "events_created": len(created_events),
        "events": created_events,
    }


@router.put("/{career_id}/event/{event_id}/travel-override")
async def travel_override(
    career_id: int,
    event_id: int,
    request: TravelOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """Override travel departure time or transport mode for an event."""
    # Verify event exists and belongs to career
    result = await db.execute(
        text("""
            SELECT id, travel_data FROM calendar_events
            WHERE id = :eid AND career_id = :cid AND is_cancelled = 0
        """),
        {"eid": event_id, "cid": career_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Event not found")

    # Parse existing travel data or create new
    travel_data = json.loads(row[1]) if row[1] else {}

    # Apply overrides
    if request.departure_time:
        travel_data["departure_time"] = request.departure_time
        travel_data["is_override"] = True
    if request.transport_mode:
        if request.transport_mode not in ("bus", "plane"):
            raise HTTPException(400, "transport_mode must be 'bus' or 'plane'")
        travel_data["transport_mode"] = request.transport_mode
        travel_data["is_override"] = True

    # Update the event
    await db.execute(
        text("""
            UPDATE calendar_events SET travel_data = :travel_data
            WHERE id = :eid AND career_id = :cid
        """),
        {"travel_data": json.dumps(travel_data), "eid": event_id, "cid": career_id},
    )
    await db.commit()

    return {"success": True, "event_id": event_id, "travel_data": travel_data}


@router.get("/{career_id}/reminders")
async def get_reminders(
    career_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get active (undismissed) reminders for a career."""
    service = ReminderService(db)
    reminders = service.get_active_reminders(career_id)

    return {
        "reminders": [
            {
                "id": idx,
                "event_id": r.event_id,
                "reminder_type": r.reminder_type,
                "message": r.message,
                "trigger_date": str(r.trigger_date),
            }
            for idx, r in enumerate(reminders)
        ]
    }


@router.post("/{career_id}/reminders/{reminder_id}/dismiss")
async def dismiss_reminder(
    career_id: int,
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a specific reminder."""
    service = ReminderService(db)
    success = service.dismiss_reminder(career_id, reminder_id)
    if not success:
        raise HTTPException(404, "Reminder not found")
    return {"success": True, "reminder_id": reminder_id}


def _parse_ucl_round_from_description(description: str) -> tuple[Optional[str], Optional[int]]:
    """
    Parse the UCL ``round_type`` and ``leg`` from a calendar event description.

    Supports both the Russian player-facing format (e.g.
    ``"Лига чемпионов, тур 3: ..."``, ``"Лига чемпионов, 1/8 финала
    (матч 2): ..."``) and the English non-player format (e.g.
    ``"Champions League Matchday 3: ..."``,
    ``"Champions League Round of 16 (leg 2): ..."``).

    Returns a ``(round_type, leg)`` tuple. ``leg`` is ``None`` for
    league_phase and final, otherwise 1 or 2. If parsing fails returns
    ``(None, None)``.
    """
    import re

    if not description:
        return (None, None)
    desc = description

    # ─── Russian (player) variants ────────────────────────────────────
    m = re.search(r"Лига чемпионов,\s*тур\s*(\d+)", desc)
    if m:
        return ("league_phase", None)

    m = re.search(r"Лига чемпионов,\s*квалификация плей-офф\s*\(матч\s*(\d+)\)", desc)
    if m:
        return ("knockout_playoff", int(m.group(1)))

    m = re.search(r"Лига чемпионов,\s*1/8 финала\s*\(матч\s*(\d+)\)", desc)
    if m:
        return ("round_of_16", int(m.group(1)))

    m = re.search(r"Лига чемпионов,\s*1/4 финала\s*\(матч\s*(\d+)\)", desc)
    if m:
        return ("quarter_final", int(m.group(1)))

    m = re.search(r"Лига чемпионов,\s*1/2 финала\s*\(матч\s*(\d+)\)", desc)
    if m:
        return ("semi_final", int(m.group(1)))

    if re.search(r"Лига чемпионов,\s*финал", desc):
        return ("final", None)

    # ─── English (non-player) variants ────────────────────────────────
    m = re.search(r"Champions League\s+Matchday\s+(\d+)", desc)
    if m:
        return ("league_phase", None)

    m = re.search(r"Champions League\s+Knockout Playoff\s*\(leg\s*(\d+)\)", desc)
    if m:
        return ("knockout_playoff", int(m.group(1)))

    m = re.search(r"Champions League\s+Round of 16\s*\(leg\s*(\d+)\)", desc)
    if m:
        return ("round_of_16", int(m.group(1)))

    m = re.search(r"Champions League\s+Quarter Final\s*\(leg\s*(\d+)\)", desc)
    if m:
        return ("quarter_final", int(m.group(1)))

    m = re.search(r"Champions League\s+Semi Final\s*\(leg\s*(\d+)\)", desc)
    if m:
        return ("semi_final", int(m.group(1)))

    if re.search(r"Champions League\s+Final", desc):
        return ("final", None)

    return (None, None)


@router.post("/{career_id}/match/{event_id}/simulate")
async def simulate_match_event(
    career_id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Simulate a match event and return result + commentary."""
    from app.services.match_engine import MatchEngine
    from app.data.club_budgets import CLUBS

    # Get the match event
    result = await db.execute(
        text("""
            SELECT id, event_date, event_type, home_club_id, away_club_id, description, competition_id, priority
            FROM calendar_events
            WHERE id = :eid AND career_id = :cid AND is_cancelled = 0
        """),
        {"eid": event_id, "cid": career_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Match event not found")

    if row[2] != "match":
        raise HTTPException(400, "Event is not a match")

    # Block simulation if the match hasn't been reached yet on the in-game
    # clock. This makes the calendar respect the player's progression — a
    # match on 2026-02-15 cannot be played while the clock still reads
    # 2025-08-01.
    cur_date_row = await db.execute(
        text("SELECT game_date FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    cur_date_val = cur_date_row.scalar() or "2025-07-01"
    event_date_val = row[1]
    if str(event_date_val) > str(cur_date_val):
        raise HTTPException(
            400,
            f"Матч {event_date_val} ещё не наступил (сейчас {cur_date_val}). "
            f"Нажмите «Следующий день» пока не дойдёте до даты матча.",
        )

    home_id = row[3]
    away_id = row[4]

    # Determine actual home/away clubs
    # If home_club_id is set, use that; if away_club_id is set, the player's club is away
    # We need to figure out the opponent from the description "vs OpponentName (H)" or "(A)"
    description = row[5] or ""
    competition_id = row[6]

    # Detect whether this calendar event belongs to a UCL competition.
    # We need this before running the MatchEngine so we can reject the
    # request with HTTP 400 if the opponent could not be resolved
    # (Requirement 12.2).
    is_ucl_event = False
    if competition_id is not None:
        comp_check = await db.execute(
            text(
                "SELECT competition_type, name FROM competitions WHERE id = :cid"
            ),
            {"cid": competition_id},
        )
        comp_row = comp_check.fetchone()
        if comp_row is not None:
            ctype = (comp_row[0] or "").lower()
            cname = (comp_row[1] or "").strip()
            if ctype == "continental_cup" and cname == "Champions League":
                is_ucl_event = True

    # Get player's club
    career_result = await db.execute(
        text("SELECT club_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    player_club_id = career_row[0]

    # Get player's club name
    player_club_name = "Unknown"
    if 1 <= player_club_id <= len(CLUBS):
        player_club_name = CLUBS[player_club_id - 1][0]

    # Parse opponent from description
    opponent_name = "Opponent"
    is_home = "(H)" in description
    if "vs " in description:
        try:
            opponent_part = description.split("vs ", 1)[1]
            opponent_name = opponent_part.replace(" (H)", "").replace(" (A)", "").strip()
        except Exception:
            pass

    # Find opponent club_id
    opponent_club_id = 0
    for idx, (name, _, _, _) in enumerate(CLUBS, start=1):
        if name.lower() == opponent_name.lower():
            opponent_club_id = idx
            break

    # For UCL events, the opponent may be a participant that is not in
    # CLUBS (e.g. Bodø/Glimt, Qarabağ, Pafos, Kairat, Slavia Prague,
    # Olympiacos, Copenhagen, Club Brugge, Union Saint-Gilloise). In that
    # case MatchEngine still simulates the match with placeholder team
    # CA = 100, and we resolve the UCL participant by club_name below.
    # We do NOT raise HTTP 400 here — it would block legitimate fixtures
    # against the 9 non-CLUBS UCL participants.

    # If the calendar event has explicit home_club_id and away_club_id
    # (set by FriendlyMatchService and any future generator that doesn't
    # rely on description parsing), prefer those over description-based
    # parsing. This makes friendly matches simulate correctly even when
    # their description is "Товарищеский матч: A – B" (no "vs ... (H)" tag).
    if home_id and away_id:
        actual_home_id = int(home_id)
        actual_away_id = int(away_id)
        actual_home_name = (
            CLUBS[actual_home_id - 1][0]
            if 1 <= actual_home_id <= len(CLUBS)
            else "Home"
        )
        actual_away_name = (
            CLUBS[actual_away_id - 1][0]
            if 1 <= actual_away_id <= len(CLUBS)
            else "Away"
        )
    elif is_ucl_event:
        # UCL match where at least one participant isn't in CLUBS (Pafos,
        # Kairat, Bodø/Glimt, etc.). The description follows the format
        # "Champions League Matchday N: HomeName vs AwayName" or
        # "Лига чемпионов, тур N: vs Opponent (H|A)" for the player.
        actual_home_id = int(home_id) if home_id else 0
        actual_away_id = int(away_id) if away_id else 0
        actual_home_name = "Home"
        actual_away_name = "Away"
        # Try to recover names from description
        if "Champions League" in description and " vs " in description and ":" in description:
            try:
                rhs = description.split(":", 1)[1].strip()
                parts = rhs.split(" vs ", 1)
                if len(parts) == 2:
                    actual_home_name = parts[0].strip()
                    actual_away_name = parts[1].strip()
            except Exception:
                pass
        elif "vs " in description and player_club_id:
            # Player-facing Russian description: "...: vs Opponent (H|A)"
            opp = description.split("vs ", 1)[1].replace(" (H)", "").replace(" (A)", "").strip()
            if "(H)" in description:
                actual_home_name = player_club_name
                actual_away_name = opp
                if not actual_home_id:
                    actual_home_id = player_club_id
            else:
                actual_home_name = opp
                actual_away_name = player_club_name
                if not actual_away_id:
                    actual_away_id = player_club_id
        # If still missing CLUBS-based ids, use the player's club id as
        # placeholder so MatchEngine can run with default CA = 100.
        if not actual_home_id:
            actual_home_id = player_club_id or 0
        if not actual_away_id:
            actual_away_id = player_club_id or 0
    else:
        # Set actual home/away from description parsing (legacy league path).
        if is_home:
            actual_home_id = player_club_id
            actual_home_name = player_club_name
            actual_away_id = opponent_club_id
            actual_away_name = opponent_name
        else:
            actual_home_id = opponent_club_id
            actual_home_name = opponent_name
            actual_away_id = player_club_id
            actual_away_name = player_club_name

    # ── UCL: reject if opponent cannot be resolved (Req 12.2) ────────────
    # For UCL events that fell back to description-based parsing (no
    # explicit home_club_id/away_club_id), make sure we can resolve the
    # opponent either to a CLUBS entry OR to an existing
    # ucl_participants.club_name row for this competition. Otherwise the
    # simulation would run against placeholder players and the UCL
    # persistence hook would silently no-op (Requirement 12.2).
    if is_ucl_event and not (home_id and away_id):
        # Determine the opponent name for this UCL event. For player-
        # facing events the opponent is what comes after "vs ". For
        # non-player events both names appear after the colon separated
        # by " vs ".
        candidate_names: list[str] = []
        if "Champions League" in description and " vs " in description and ":" in description:
            try:
                rhs = description.split(":", 1)[1].strip()
                parts = rhs.split(" vs ", 1)
                if len(parts) == 2:
                    candidate_names = [parts[0].strip(), parts[1].strip()]
            except Exception:
                pass
        elif "vs " in description:
            try:
                opp_part = description.split("vs ", 1)[1]
                opp_part = (
                    opp_part.replace(" (H)", "").replace(" (A)", "").strip()
                )
                # Strip a trailing " (Venue, City)" suffix used for the
                # final's neutral-venue description.
                if opp_part.endswith(")") and " (" in opp_part:
                    opp_part = opp_part.rsplit(" (", 1)[0].strip()
                candidate_names = [opp_part]
            except Exception:
                pass

        unresolved: list[str] = []
        for name in candidate_names:
            if not name:
                continue
            # 1) CLUBS lookup (case-insensitive).
            clubs_match = any(
                cname.lower() == name.lower() for cname, *_ in CLUBS
            )
            if clubs_match:
                continue
            # 2) ucl_participants lookup for this competition.
            r = await db.execute(
                text(
                    "SELECT 1 FROM ucl_participants "
                    "WHERE competition_id = :cid "
                    "AND LOWER(club_name) = LOWER(:n) LIMIT 1"
                ),
                {"cid": competition_id, "n": name},
            )
            if r.scalar() is not None:
                continue
            unresolved.append(name)

        if unresolved:
            raise HTTPException(
                400, "Opponent club not found in CLUBS list"
            )

    # Run simulation. Determine which side is human-controlled so we
    # don't auto-sub their players.
    engine = MatchEngine(db)
    is_player_home: Optional[bool] = None
    if player_club_id is not None:
        if actual_home_id == player_club_id:
            is_player_home = True
        elif actual_away_id == player_club_id:
            is_player_home = False
    match_result = await engine.simulate_match(
        actual_home_id, actual_away_id,
        actual_home_name, actual_away_name,
        is_player_home=is_player_home,
        career_id=career_id,
    )

    # Update event with score in description. We append " | RESULT: H-A" so
    # that league-table aggregation in matches.py can recover scores from
    # the description on rebuild.
    new_description = (
        f"{description} | RESULT: {match_result.home_score}-{match_result.away_score}"
        if description else
        f"{actual_home_name} {match_result.home_score} - {match_result.away_score} {actual_away_name}"
    )
    await db.execute(
        text("""
            UPDATE calendar_events
            SET description = :desc, is_locked = 1
            WHERE id = :eid
        """),
        {"desc": new_description, "eid": event_id}
    )
    await db.commit()

    # Update the in-memory league table ONLY for league fixtures
    # (priority=6). Friendlies (priority=2), cup ties (priority=4),
    # mandatory matches (priority=9) and UCL (priority=8) must not
    # affect the domestic league standings.
    event_priority = row[7] if len(row) > 7 else None
    is_league_match = (event_priority == 6)
    if is_league_match:
        try:
            from app.api.routes.matches import _update_league_table
            _update_league_table(
                career_id=career_id,
                home_team=actual_home_name,
                away_team=actual_away_name,
                home_score=match_result.home_score,
                away_score=match_result.away_score,
            )
        except Exception:
            pass  # league table is best-effort; never block the match

        # Attribute stats for the user's league match.
        try:
            from app.services.player_stats_service import attribute_match_to_players
            from app.data.club_budgets import CLUBS as ALL_CLUBS
            club_row = (await db.execute(
                text("SELECT club_id, current_season FROM careers WHERE id = :c"),
                {"c": career_id}
            )).fetchone()
            # Resolve the user's league name for the competition label.
            lg = None
            if club_row and club_row[0]:
                ccid = int(club_row[0])
                if 1 <= ccid <= len(ALL_CLUBS):
                    lg = ALL_CLUBS[ccid - 1][3]  # (name, scout, transfer, league)
            comp_label = f"league:{lg}" if lg else "league:?"
            season = int(club_row[1]) if club_row and club_row[1] else 1
            await attribute_match_to_players(
                db,
                career_id=career_id,
                season=season,
                competition=comp_label,
                home_club=actual_home_name,
                away_club=actual_away_name,
                home_score=match_result.home_score,
                away_score=match_result.away_score,
                commit=False,
            )
        except Exception:
            pass

        # Also auto-simulate every OTHER league match scheduled today,
        # so the table stays consistent with the player's progression.
        try:
            from app.services.background_match_runner import (
                run_background_matches_for_day,
            )
            await run_background_matches_for_day(
                db, career_id=career_id, on_date=str(event_date_val)
            )
        except Exception:
            pass

    # UCL persistence hook (Requirements 8.1, 8.2, 8.4, 12.4).
    # We must keep the description update intact even if UCL persistence
    # fails — this is why the commit above runs first and the call below
    # is wrapped in try/except.
    if is_ucl_event and competition_id is not None:
        try:
            from app.services.ucl_generator import UCLGenerator

            round_type, leg = _parse_ucl_round_from_description(description)
            if round_type is not None:
                # Resolve participant ids for the actual home/away teams.
                # Try by club_id first; fall back to club_name for non-CLUBS
                # participants (Bodø/Glimt, Qarabağ, Pafos, etc.).
                async def _resolve_pid(club_id: int, club_name: str):
                    if club_id and club_id > 0:
                        r = await db.execute(
                            text(
                                "SELECT id FROM ucl_participants "
                                "WHERE competition_id = :cid AND club_id = :club "
                                "LIMIT 1"
                            ),
                            {"cid": competition_id, "club": club_id},
                        )
                        v = r.scalar()
                        if v is not None:
                            return v
                    if club_name:
                        r = await db.execute(
                            text(
                                "SELECT id FROM ucl_participants "
                                "WHERE competition_id = :cid "
                                "AND LOWER(club_name) = LOWER(:name) "
                                "LIMIT 1"
                            ),
                            {"cid": competition_id, "name": club_name},
                        )
                        v = r.scalar()
                        if v is not None:
                            return v
                    return None

                actual_home_pid = await _resolve_pid(actual_home_id, actual_home_name)
                actual_away_pid = await _resolve_pid(actual_away_id, actual_away_name)

                if actual_home_pid is not None and actual_away_pid is not None:
                    ucl = UCLGenerator(db)
                    await ucl.persist_match_result(
                        competition_id=competition_id,
                        calendar_event_id=event_id,
                        home_participant_id=int(actual_home_pid),
                        away_participant_id=int(actual_away_pid),
                        home_score=match_result.home_score,
                        away_score=match_result.away_score,
                        round_type=round_type,
                        leg=leg,
                        career_id=career_id,
                        player_club_id=player_club_id,
                    )
                    await db.commit()
                else:
                    print(
                        f"UCL persist warning: could not resolve participants "
                        f"for clubs {actual_home_id}/{actual_away_id} "
                        f"in competition {competition_id}"
                    )
            else:
                print(
                    f"UCL persist warning: could not parse round_type from "
                    f"description: {description!r}"
                )
        except Exception as e:  # noqa: BLE001 — keep simulation response intact
            print(f"UCL persist warning: {e}")

    # ─── Auto-simulate AI vs AI matches on the same day ──────────────────
    # When the player simulates their match for a date, we also play out
    # every other unfinished match that falls on the same date so the
    # league/UCL standings progress for the whole world.
    ai_matches_played = 0
    try:
        same_day = row[1]  # event_date string from the original SELECT
        ai_rows = await db.execute(
            text(
                """
                SELECT id, home_club_id, away_club_id, description, competition_id
                FROM calendar_events
                WHERE career_id = :cid
                  AND event_date = :ed
                  AND event_type = 'match'
                  AND is_cancelled = 0
                  AND is_locked = 0
                  AND id != :eid
                """
            ),
            {"cid": career_id, "ed": same_day, "eid": event_id},
        )
        ai_pending = ai_rows.fetchall()
        for ai in ai_pending:
            ai_id = int(ai[0])
            ai_home_id = ai[1]
            ai_away_id = ai[2]
            ai_desc = ai[3] or ""
            ai_comp_id = ai[4]

            # Resolve home/away club_ids — prefer explicit columns, fall
            # back to UCL participants table for non-CLUBS UCL teams.
            ai_actual_home = None
            ai_actual_away = None
            if ai_home_id and ai_away_id:
                ai_actual_home = int(ai_home_id)
                ai_actual_away = int(ai_away_id)
            elif ai_comp_id is not None:
                # UCL match where one or both participants are not in CLUBS
                # (Pafos, Kairat, Bodø/Glimt, etc.). Resolve names from the
                # description and synthesize ids — MatchEngine accepts any int.
                # Description format: "Champions League Matchday N: HomeName vs AwayName"
                if " vs " in ai_desc and ":" in ai_desc:
                    try:
                        rhs = ai_desc.split(":", 1)[1].strip()
                        parts = rhs.split(" vs ", 1)
                        if len(parts) == 2:
                            ai_home_name = parts[0].strip()
                            ai_away_name = parts[1].strip()
                            ai_actual_home = int(ai_home_id) if ai_home_id else 0
                            ai_actual_away = int(ai_away_id) if ai_away_id else 0
                            # Run AI sim with placeholder ids (MatchEngine handles 0 → default)
                            try:
                                ai_result = await engine.simulate_match(
                                    ai_actual_home, ai_actual_away,
                                    ai_home_name, ai_away_name,
                                )
                                ai_new_desc = (
                                    f"{ai_home_name} {ai_result.home_score} - "
                                    f"{ai_result.away_score} {ai_away_name}"
                                )
                                await db.execute(
                                    text(
                                        """
                                        UPDATE calendar_events
                                        SET description = :desc, is_locked = 1
                                        WHERE id = :eid
                                        """
                                    ),
                                    {"desc": ai_new_desc, "eid": ai_id},
                                )
                                # Persist UCL via participant resolution by name
                                if is_ucl_event and ai_comp_id == competition_id:
                                    try:
                                        from app.services.ucl_generator import UCLGenerator
                                        ai_round_type, ai_leg = _parse_ucl_round_from_description(ai_desc)
                                        if ai_round_type is not None:
                                            ph = await db.execute(
                                                text("SELECT id FROM ucl_participants WHERE competition_id=:cid AND LOWER(club_name)=LOWER(:n) LIMIT 1"),
                                                {"cid": ai_comp_id, "n": ai_home_name},
                                            )
                                            ai_home_pid = ph.scalar()
                                            pa = await db.execute(
                                                text("SELECT id FROM ucl_participants WHERE competition_id=:cid AND LOWER(club_name)=LOWER(:n) LIMIT 1"),
                                                {"cid": ai_comp_id, "n": ai_away_name},
                                            )
                                            ai_away_pid = pa.scalar()
                                            if ai_home_pid is not None and ai_away_pid is not None:
                                                ucl = UCLGenerator(db)
                                                await ucl.persist_match_result(
                                                    competition_id=ai_comp_id,
                                                    calendar_event_id=ai_id,
                                                    home_participant_id=int(ai_home_pid),
                                                    away_participant_id=int(ai_away_pid),
                                                    home_score=ai_result.home_score,
                                                    away_score=ai_result.away_score,
                                                    round_type=ai_round_type,
                                                    leg=ai_leg,
                                                    career_id=career_id,
                                                    player_club_id=player_club_id,
                                                )
                                    except Exception as e_ucl2:  # noqa: BLE001
                                        print(f"AI UCL persist (non-CLUBS) warning: {e_ucl2}")
                                ai_matches_played += 1
                            except Exception as e_ai2:
                                print(f"AI non-CLUBS match {ai_id} sim failed: {e_ai2}")
                            continue
                    except Exception:
                        pass
                # If we got here we couldn't resolve names, skip
                continue
            else:
                # League match with no explicit home/away ids — skip
                continue

            ai_home_name = (
                CLUBS[ai_actual_home - 1][0]
                if 1 <= ai_actual_home <= len(CLUBS)
                else "Home"
            )
            ai_away_name = (
                CLUBS[ai_actual_away - 1][0]
                if 1 <= ai_actual_away <= len(CLUBS)
                else "Away"
            )

            try:
                ai_result = await engine.simulate_match(
                    ai_actual_home, ai_actual_away,
                    ai_home_name, ai_away_name,
                )
                ai_new_desc = (
                    f"{ai_home_name} {ai_result.home_score} - "
                    f"{ai_result.away_score} {ai_away_name}"
                )
                await db.execute(
                    text(
                        """
                        UPDATE calendar_events
                        SET description = :desc, is_locked = 1
                        WHERE id = :eid
                        """
                    ),
                    {"desc": ai_new_desc, "eid": ai_id},
                )

                # If this AI match belongs to the same UCL competition,
                # also persist standings/ties.
                if ai_comp_id is not None and is_ucl_event and ai_comp_id == competition_id:
                    try:
                        from app.services.ucl_generator import UCLGenerator
                        ai_round_type, ai_leg = _parse_ucl_round_from_description(ai_desc)
                        if ai_round_type is not None:
                            async def _resolve_ai_pid(club_id, club_name):
                                if club_id and club_id > 0:
                                    r = await db.execute(
                                        text(
                                            "SELECT id FROM ucl_participants "
                                            "WHERE competition_id = :cid AND club_id = :club LIMIT 1"
                                        ),
                                        {"cid": ai_comp_id, "club": club_id},
                                    )
                                    v = r.scalar()
                                    if v is not None:
                                        return v
                                if club_name:
                                    r = await db.execute(
                                        text(
                                            "SELECT id FROM ucl_participants "
                                            "WHERE competition_id = :cid "
                                            "AND LOWER(club_name) = LOWER(:name) LIMIT 1"
                                        ),
                                        {"cid": ai_comp_id, "name": club_name},
                                    )
                                    v = r.scalar()
                                    if v is not None:
                                        return v
                                return None
                            ai_home_pid = await _resolve_ai_pid(ai_actual_home, ai_home_name)
                            ai_away_pid = await _resolve_ai_pid(ai_actual_away, ai_away_name)
                            if ai_home_pid is not None and ai_away_pid is not None:
                                ucl = UCLGenerator(db)
                                await ucl.persist_match_result(
                                    competition_id=ai_comp_id,
                                    calendar_event_id=ai_id,
                                    home_participant_id=int(ai_home_pid),
                                    away_participant_id=int(ai_away_pid),
                                    home_score=ai_result.home_score,
                                    away_score=ai_result.away_score,
                                    round_type=ai_round_type,
                                    leg=ai_leg,
                                    career_id=career_id,
                                    player_club_id=player_club_id,
                                )
                    except Exception as e_ucl:  # noqa: BLE001
                        print(f"AI UCL persist warning: {e_ucl}")

                ai_matches_played += 1
            except Exception as e_ai:  # noqa: BLE001
                # One failed AI match shouldn't break the whole batch.
                print(f"AI match {ai_id} sim failed: {e_ai}")
                continue

        if ai_matches_played > 0:
            await db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"AI auto-sim batch warning: {e}")

    # ─── Inbox: notify the user about THEIR match result ─────────────────
    # Only emit the inbox row when the player's club actually played in
    # this fixture (i.e. resolved is_player_home above).
    try:
        if is_player_home is not None:
            from app.api.routes.inbox import push_inbox_message

            player_score = (
                match_result.home_score if is_player_home else match_result.away_score
            )
            opponent_score = (
                match_result.away_score if is_player_home else match_result.home_score
            )
            opponent = (
                match_result.away_team_name
                if is_player_home
                else match_result.home_team_name
            )

            if player_score > opponent_score:
                outcome = "Победа"
                cat = "match_win"
            elif player_score < opponent_score:
                outcome = "Поражение"
                cat = "match_loss"
            else:
                outcome = "Ничья"
                cat = "match_draw"

            venue = "дома" if is_player_home else "в гостях"
            subject = (
                f"{outcome} {venue}: {opponent} {match_result.home_score}-"
                f"{match_result.away_score}"
                if is_player_home
                else
                f"{outcome} {venue}: {opponent} {match_result.away_score}-"
                f"{match_result.home_score}"
            )
            # Build a short body: top scorers and shot stats.
            scorers = [e for e in match_result.events if e.event_type == "goal"]
            top_lines = [f"{e.minute}' {e.team}: {e.player_name}" for e in scorers[:6]]
            body = (
                f"Владение: {match_result.home_possession}-"
                f"{match_result.away_possession}, "
                f"удары: {match_result.home_shots}-{match_result.away_shots}\n"
                + "\n".join(top_lines)
            )
            await push_inbox_message(
                db,
                career_id,
                category=cat,
                subject=subject,
                body=body,
                on_date=str(event_date_val),
            )
    except Exception as e_inbox:  # noqa: BLE001
        print(f"Inbox match push warning: {e_inbox}")

    return {
        "success": True,
        "ai_matches_played": ai_matches_played,
        "home_team": match_result.home_team_name,
        "away_team": match_result.away_team_name,
        "home_score": match_result.home_score,
        "away_score": match_result.away_score,
        "possession": {
            "home": match_result.home_possession,
            "away": match_result.away_possession,
        },
        "shots": {
            "home": match_result.home_shots,
            "away": match_result.away_shots,
        },
        "shots_on_target": {
            "home": match_result.home_shots_on_target,
            "away": match_result.away_shots_on_target,
        },
        "events": [
            {
                "minute": e.minute,
                "type": e.event_type,
                "team": e.team,
                "player": e.player_name,
                "description": e.description,
            }
            for e in match_result.events
        ],
    }


@router.post("/{career_id}/friendly", status_code=201)
async def create_friendly(
    career_id: int,
    payload: FriendlyCreatePayload,
    db: AsyncSession = Depends(get_db),
):
    """Create a user-arranged friendly match.

    See Requirements 1.4-1.6, 6.8.
    """
    from app.services.friendly_match_service import (
        FriendlyMatchService,
        FriendlyCreateRequest,
        ValidationError as FriendlyValidationError,
    )

    try:
        ev_date = date.fromisoformat(payload.event_date)
    except ValueError:
        raise HTTPException(422, "Неверный формат даты")

    service = FriendlyMatchService(db)
    try:
        result = await service.create_friendly(
            career_id,
            FriendlyCreateRequest(
                event_date=ev_date,
                opponent_club_id=payload.opponent_club_id,
                match_type=payload.match_type,
                kick_off_time=payload.kick_off_time,
                tour_venue_id=payload.tour_venue_id,
                description_suffix=payload.description_suffix,
            ),
        )
    except FriendlyValidationError as ve:
        raise HTTPException(ve.http_status, ve.message)

    return {
        "id": result.event_id,
        "event_date": str(result.event_date),
        "kick_off_time": result.kick_off_time,
        "home_club_id": result.home_club_id,
        "away_club_id": result.away_club_id,
        "description": result.description,
        "travel_data": result.travel_data,
        "warnings": result.warnings,
    }


@router.delete("/{career_id}/friendly/{event_id}")
async def cancel_friendly(
    career_id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft-cancel a user-arranged friendly. See Requirements 8.1-8.5."""
    from app.services.friendly_match_service import (
        FriendlyMatchService,
        ValidationError as FriendlyValidationError,
    )

    service = FriendlyMatchService(db)
    try:
        cancelled_id = await service.cancel_friendly(career_id, event_id)
    except FriendlyValidationError as ve:
        raise HTTPException(ve.http_status, ve.message)
    return {"success": True, "event_id": cancelled_id}


@router.get("/tour-venues")
async def list_tour_venues():
    """List commercial-tour venues. See Requirement 4.1."""
    from app.data.tour_venues import get_tour_venues
    return {"venues": get_tour_venues()}
