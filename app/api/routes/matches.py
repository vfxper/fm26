"""
Matches API Endpoints
POST /api/careers/{career_id}/matches/simulate - Simulate next match
GET /api/careers/{career_id}/matches/next - Get next upcoming match info
GET /api/careers/{career_id}/league-table - Get current league standings
GET /api/careers/{career_id}/matches/{match_id} - Get match result
GET /api/careers/{career_id}/matches/history - Get match history
GET /api/careers/{career_id}/matches/upcoming - Get upcoming fixtures
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/careers/{career_id}/matches", tags=["matches"])

# Separate router for league-table (different prefix)
league_router = APIRouter(prefix="/careers/{career_id}", tags=["league"])

# In-memory league table storage per career
# Structure: {career_id: {club_name: {played, won, drawn, lost, gf, ga, points}}}
_league_tables: Dict[int, Dict[str, Dict[str, int]]] = {}


class SimulateRequest(BaseModel):
    speed: str = Field(default="normal", description="instant, fast, normal, slow")


def _get_or_build_league_table(career_id: int) -> Dict[str, Dict[str, int]]:
    """Get league table for a career, initializing if needed."""
    if career_id not in _league_tables:
        _league_tables[career_id] = {}
    return _league_tables[career_id]


def _update_league_table(
    career_id: int,
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
):
    """Update league table with a match result."""
    table = _get_or_build_league_table(career_id)

    # Initialize teams if not present
    for team in [home_team, away_team]:
        if team not in table:
            table[team] = {
                "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "gd": 0, "points": 0,
            }

    # Update home team
    table[home_team]["played"] += 1
    table[home_team]["gf"] += home_score
    table[home_team]["ga"] += away_score
    table[home_team]["gd"] = table[home_team]["gf"] - table[home_team]["ga"]

    # Update away team
    table[away_team]["played"] += 1
    table[away_team]["gf"] += away_score
    table[away_team]["ga"] += home_score
    table[away_team]["gd"] = table[away_team]["gf"] - table[away_team]["ga"]

    if home_score > away_score:
        table[home_team]["won"] += 1
        table[home_team]["points"] += 3
        table[away_team]["lost"] += 1
    elif home_score < away_score:
        table[away_team]["won"] += 1
        table[away_team]["points"] += 3
        table[home_team]["lost"] += 1
    else:
        table[home_team]["drawn"] += 1
        table[home_team]["points"] += 1
        table[away_team]["drawn"] += 1
        table[away_team]["points"] += 1


@router.post("/simulate")
async def simulate_match(
    career_id: int,
    request: SimulateRequest = SimulateRequest(),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulate the next scheduled match from calendar_events. Returns match result with timeline."""
    from app.services.match_simulator import MatchSimulator

    # Verify career ownership
    career_result = await db.execute(
        text("SELECT id, user_id, club_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    club_id = career_row[2]

    # Get club name (CLUBS index for normal careers, UCL participant for ucl_only)
    club_name = None
    try:
        from app.data.club_budgets import CLUBS
        if club_id is not None and 1 <= club_id <= len(CLUBS):
            club_name = CLUBS[club_id - 1][0]
    except Exception:
        pass

    # Fallback: ucl_only mode uses synthetic id (>=1000) → look up UCL participant.
    if not club_name and club_id and club_id >= 1000:
        try:
            from app.data.ucl_config import UCL_PARTICIPANTS
            seed = club_id - 1000
            if 1 <= seed <= len(UCL_PARTICIPANTS):
                club_name = UCL_PARTICIPANTS[seed - 1][0]
        except Exception:
            pass

    # Last-ditch fallback: read clubs table.
    if not club_name:
        try:
            row = await db.execute(
                text("SELECT name FROM clubs WHERE id = :cid"), {"cid": club_id}
            )
            r = row.fetchone()
            if r and r[0]:
                club_name = r[0]
        except Exception:
            pass

    if not club_name:
        raise HTTPException(400, "Club not found for this career")

    # Read the in-game game_date so we can block matches that haven't arrived yet.
    cur_date_row = await db.execute(
        text("SELECT game_date FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    cur_date_val = cur_date_row.scalar() or "2025-07-01"

    # Find next scheduled match from calendar_events (any non-played match
    # belonging to this career, regardless of competition — league, UCL, cup,
    # friendlies all qualify).
    next_match_result = await db.execute(
        text("""
            SELECT id, event_date, home_club_id, away_club_id, description
            FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND is_cancelled = 0
              AND is_locked = 0
              AND description NOT LIKE '%RESULT:%'
            ORDER BY event_date ASC
            LIMIT 1
        """),
        {"cid": career_id}
    )
    match_row = next_match_result.fetchone()

    if not match_row:
        return {"error": "no_matches", "message": "Нет предстоящих матчей для симуляции"}

    event_id = match_row[0]
    event_date = match_row[1]
    if str(event_date) > str(cur_date_val):
        return {
            "error": "not_yet",
            "message": (
                f"Матч {event_date} ещё не наступил (сейчас {cur_date_val}). "
                f"Нажмите «Следующий день» пока не дойдёте до даты матча."
            ),
            "match_date": str(event_date),
            "current_date": str(cur_date_val),
        }
    home_club_id = match_row[2]
    away_club_id = match_row[3]
    description = match_row[4] or ""

    # Determine if home or away, and extract opponent name from description
    is_home = home_club_id == club_id
    opponent_name = ""
    if "vs " in description:
        # Format: "La Liga Matchday 5: vs Barcelona (H)"
        parts = description.split("vs ", 1)
        if len(parts) > 1:
            opponent_name = parts[1].replace("(H)", "").replace("(A)", "").strip()

    home_team_name = club_name if is_home else opponent_name
    away_team_name = opponent_name if is_home else club_name

    # Get players for the player's club. We pull the physical/mental
    # attributes used by the injury model so risk scales with each
    # player's traits (Req 11.1). `id` is needed to persist injuries
    # against the right Player row.
    player_result = await db.execute(
        text(
            "SELECT id, name, ca, position, bravery, stamina, strength "
            "FROM players WHERE club = :club_name LIMIT 25"
        ),
        {"club_name": club_name}
    )
    my_players_rows = player_result.fetchall()

    # Try CSV name mapping if no players found
    if not my_players_rows:
        try:
            from app.data.club_budgets import CLUBS_TO_CSV
            csv_name = CLUBS_TO_CSV.get(club_name)
            if csv_name:
                player_result = await db.execute(
                    text(
                        "SELECT id, name, ca, position, bravery, stamina, strength "
                        "FROM players WHERE club = :club_name LIMIT 25"
                    ),
                    {"club_name": csv_name}
                )
                my_players_rows = player_result.fetchall()
        except Exception:
            pass

    # Get players for the opponent
    opp_result = await db.execute(
        text(
            "SELECT id, name, ca, position, bravery, stamina, strength "
            "FROM players WHERE club = :club_name LIMIT 25"
        ),
        {"club_name": opponent_name}
    )
    opp_players_rows = opp_result.fetchall()

    # Try CSV name mapping for opponent
    if not opp_players_rows:
        try:
            from app.data.club_budgets import CLUBS_TO_CSV
            csv_name = CLUBS_TO_CSV.get(opponent_name)
            if csv_name:
                opp_result = await db.execute(
                    text(
                        "SELECT id, name, ca, position, bravery, stamina, strength "
                        "FROM players WHERE club = :club_name LIMIT 25"
                    ),
                    {"club_name": csv_name}
                )
                opp_players_rows = opp_result.fetchall()
        except Exception:
            pass

    # Also try LIKE match for opponent
    if not opp_players_rows and opponent_name:
        first_word = opponent_name.split()[0] if opponent_name.split() else opponent_name
        if len(first_word) > 2:
            opp_result = await db.execute(
                text(
                    "SELECT id, name, ca, position, bravery, stamina, strength "
                    "FROM players WHERE club LIKE :pattern LIMIT 25"
                ),
                {"pattern": f"%{first_word}%"}
            )
            opp_players_rows = opp_result.fetchall()

    # Last-resort: pull a CA-balanced 18-player squad of REAL players
    # from the DB (any club). Prevents the generic "Иванов/Петров"
    # squad from being used for a known club like Leganés.
    if not opp_players_rows:
        opp_result = await db.execute(
            text(
                "SELECT id, name, ca, position, bravery, stamina, strength "
                "FROM players "
                "WHERE ca BETWEEN 90 AND 130 "
                "ORDER BY RANDOM() LIMIT 18"
            )
        )
        opp_players_rows = opp_result.fetchall()

    def _row_to_player(row) -> Dict[str, Any]:
        # row order: id, name, ca, position, bravery, stamina, strength
        return {
            "player_id": row[0],
            "name": row[1],
            "ca": row[2] or 120,
            "position": row[3] or "",
            "bravery": row[4] if row[4] is not None else 10,
            "stamina": row[5] if row[5] is not None else 10,
            "strength": row[6] if row[6] is not None else 10,
        }

    # Build player lists with positions for the simulator
    my_players = [_row_to_player(r) for r in my_players_rows]
    opp_players = [_row_to_player(r) for r in opp_players_rows]

    # Attach squad_player_id for the human's roster (if rows exist for
    # this career), so injuries can be persisted against the SquadPlayer
    # row that the rest of the medical module reads from.
    if my_players:
        try:
            sp_rows = await db.execute(
                text(
                    "SELECT player_id, id FROM squad_players "
                    "WHERE career_id = :cid"
                ),
                {"cid": career_id},
            )
            sp_map = {row[0]: row[1] for row in sp_rows.fetchall()}
            if sp_map:
                for p in my_players:
                    sp_id = sp_map.get(p.get("player_id"))
                    if sp_id is not None:
                        p["squad_player_id"] = sp_id
        except Exception:
            # squad_players table may not yet exist in older saves —
            # injury persistence will fall back gracefully below.
            pass

    # Calculate average CA
    my_avg_ca = sum(p["ca"] for p in my_players) // len(my_players) if my_players else 130
    opp_avg_ca = sum(p["ca"] for p in opp_players) // len(opp_players) if opp_players else 120

    home_ca = my_avg_ca if is_home else opp_avg_ca
    away_ca = opp_avg_ca if is_home else my_avg_ca
    home_players = my_players if is_home else opp_players
    away_players = opp_players if is_home else my_players

    # Run simulation using the enhanced simulator. Pass `is_player_home`
    # so the simulator knows which side is human-controlled and skips
    # auto-substitutions for that team.
    simulator = MatchSimulator()
    match_result = simulator.simulate(
        home_club=home_team_name,
        away_club=away_team_name,
        home_avg_ca=home_ca,
        away_avg_ca=away_ca,
        home_players=home_players,
        away_players=away_players,
        is_player_home=is_home,
    )

    # Convert to dict for JSON response
    result_dict = simulator.to_dict(match_result)

    # Update league table
    _update_league_table(
        career_id=career_id,
        home_team=home_team_name,
        away_team=away_team_name,
        home_score=match_result.home_score,
        away_score=match_result.away_score,
    )

    # Mark the calendar event as played (update description with score)
    score_text = f"{match_result.home_score}-{match_result.away_score}"
    new_description = f"{description} | RESULT: {score_text}"
    await db.execute(
        text("UPDATE calendar_events SET description = :desc WHERE id = :eid"),
        {"desc": new_description, "eid": event_id}
    )

    # Persist injuries for the human-controlled club (Req 11.1, 11.3).
    # Only injuries that hit our team's players are saved against this
    # career — the opponent's medical records aren't tracked.
    persisted_injuries = 0
    if match_result.injuries:
        from datetime import datetime as _dt, timedelta as _td
        # Best-effort current date from the career row (string YYYY-MM-DD)
        try:
            injury_date = _dt.strptime(str(cur_date_val), "%Y-%m-%d")
        except Exception:
            injury_date = _dt.utcnow()

        # Compute season + week for the Injury row context.
        season_row = await db.execute(
            text("SELECT current_season, current_week FROM careers WHERE id = :cid"),
            {"cid": career_id},
        )
        season_data = season_row.fetchone()
        cur_season = (season_data[0] if season_data and season_data[0] else 1)
        cur_week = (season_data[1] if season_data and season_data[1] else 1)
        # Some saves keep these columns optional — clamp to schema range.
        cur_week = max(1, min(52, int(cur_week or 1)))
        cur_season = max(1, int(cur_season or 1))

        my_team_label = "home" if is_home else "away"
        severity_map = {
            "minor": "minor",
            "moderate": "moderate",
            "severe": "severe",
        }

        for inj in match_result.injuries:
            if inj.team != my_team_label:
                continue  # only persist for the human's club
            if inj.player_id is None or inj.squad_player_id is None:
                # We can't satisfy the FKs, so skip persistence for this
                # one — it still appears in the timeline / response.
                continue

            try:
                expected_recovery = injury_date + _td(weeks=int(inj.recovery_weeks))
                await db.execute(
                    text(
                        "INSERT INTO injuries ("
                        "career_id, player_id, squad_player_id, "
                        "injury_type, injury_description, severity, status, "
                        "injury_date, expected_recovery_date, recovery_weeks, "
                        "match_minute, season, week, sharpness_penalty, "
                        "is_injury_prone_flag) "
                        "VALUES ("
                        ":cid, :pid, :spid, "
                        ":itype, :idesc, :sev, 'active', "
                        ":idate, :erdate, :rweeks, "
                        ":minute, :season, :week, 10, 0)"
                    ),
                    {
                        "cid": career_id,
                        "pid": inj.player_id,
                        "spid": inj.squad_player_id,
                        "itype": inj.injury_type[:100],
                        "idesc": inj.injury_description,
                        "sev": severity_map.get(inj.severity, "minor"),
                        "idate": injury_date.isoformat(),
                        "erdate": expected_recovery.isoformat(),
                        "rweeks": int(inj.recovery_weeks),
                        "minute": int(inj.match_minute),
                        "season": cur_season,
                        "week": cur_week,
                    },
                )
                # Best-effort: flip squad_players.is_injured if the column exists
                try:
                    await db.execute(
                        text(
                            "UPDATE squad_players SET is_injured = 1 "
                            "WHERE id = :sid"
                        ),
                        {"sid": inj.squad_player_id},
                    )
                except Exception:
                    pass
                persisted_injuries += 1
            except Exception:
                # Don't let injury persistence break the match result —
                # tables may not exist on older saves.
                continue

    await db.commit()

    return {
        "match_id": event_id,
        "home_team": home_team_name,
        "away_team": away_team_name,
        "home_score": match_result.home_score,
        "away_score": match_result.away_score,
        "timeline": result_dict["timeline"],
        "possession_home": match_result.possession_home,
        "possession_away": match_result.possession_away,
        "shots_home": match_result.shots_home,
        "shots_away": match_result.shots_away,
        "shots_on_target_home": match_result.shots_on_target_home,
        "shots_on_target_away": match_result.shots_on_target_away,
        "event_date": str(event_date),
        "is_home": is_home,
        "injuries": result_dict["injuries"],
    }


@router.get("/next")
async def get_next_match(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get info about the next upcoming match (opponent, date, competition)."""
    # Verify career
    career_result = await db.execute(
        text("SELECT id, user_id, club_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    club_id = career_row[2]

    # Get club name
    club_name = None
    try:
        from app.data.club_budgets import CLUBS
        if 1 <= club_id <= len(CLUBS):
            club_name = CLUBS[club_id - 1][0]
    except Exception:
        pass

    # Find next match
    result = await db.execute(
        text("""
            SELECT id, event_date, home_club_id, away_club_id, description, kick_off_time
            FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND is_cancelled = 0
              AND is_locked = 0
              AND description NOT LIKE '%RESULT:%'
            ORDER BY event_date ASC
            LIMIT 1
        """),
        {"cid": career_id}
    )
    row = result.fetchone()

    if not row:
        return {"has_match": False, "message": "Нет предстоящих матчей"}

    description = row[4] or ""
    is_home = row[2] == club_id

    # Extract opponent
    opponent_name = ""
    if "vs " in description:
        parts = description.split("vs ", 1)
        if len(parts) > 1:
            opponent_name = parts[1].replace("(H)", "").replace("(A)", "").strip()

    # Extract matchday number
    matchday = ""
    if "Matchday " in description:
        try:
            md_part = description.split("Matchday ")[1].split(":")[0]
            matchday = md_part.strip()
        except (IndexError, ValueError):
            pass

    # Extract competition name
    competition = ""
    if "Matchday" in description:
        competition = description.split("Matchday")[0].strip()

    return {
        "has_match": True,
        "match_id": row[0],
        "event_date": str(row[1]),
        "opponent": opponent_name,
        "is_home": is_home,
        "venue": "Дома" if is_home else "В гостях",
        "kick_off_time": row[5] or "15:00",
        "competition": competition,
        "matchday": matchday,
        "description": description,
    }


@router.get("/{match_id}")
async def get_match(
    career_id: int,
    match_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get match result details from calendar_events."""
    # Verify career
    career_result = await db.execute(
        text("SELECT id, user_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    result = await db.execute(
        text("""SELECT id, event_date, home_club_id, away_club_id, description
                FROM calendar_events WHERE id = :mid AND career_id = :cid"""),
        {"mid": match_id, "cid": career_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Match not found")

    return {
        "id": row[0],
        "event_date": str(row[1]),
        "description": row[4],
        "status": "completed" if "RESULT:" in (row[4] or "") else "scheduled",
    }


@router.get("/history")
async def get_match_history(
    career_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=5, le=50),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get match history for this career (played matches from calendar_events)."""
    career_result = await db.execute(
        text("SELECT id, user_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    offset = (page - 1) * per_page
    result = await db.execute(
        text("""
            SELECT id, event_date, description
            FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND description LIKE '%RESULT:%'
            ORDER BY event_date DESC
            LIMIT :lim OFFSET :off
        """),
        {"cid": career_id, "lim": per_page, "off": offset}
    )
    rows = result.fetchall()

    matches = []
    for row in rows:
        desc = row[2] or ""
        matches.append({
            "id": row[0],
            "event_date": str(row[1]),
            "description": desc,
        })

    return {"matches": matches, "page": page}


@router.get("/upcoming")
async def get_upcoming(
    career_id: int,
    limit: int = Query(5, ge=1, le=20),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming fixtures from calendar_events."""
    career_result = await db.execute(
        text("SELECT id, user_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    result = await db.execute(
        text("""
            SELECT id, event_date, description, home_club_id, away_club_id
            FROM calendar_events
            WHERE career_id = :cid
              AND event_type = 'match'
              AND is_cancelled = 0
              AND is_locked = 0
              AND description NOT LIKE '%RESULT:%'
            ORDER BY event_date ASC
            LIMIT :lim
        """),
        {"cid": career_id, "lim": limit}
    )
    rows = result.fetchall()

    fixtures = []
    for row in rows:
        fixtures.append({
            "id": row[0],
            "event_date": str(row[1]),
            "description": row[2],
        })

    return {"fixtures": fixtures}



# ─── League Table Endpoint ────────────────────────────────────────────────────


@league_router.get("/league-table")
async def get_league_table(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current league standings based on all simulated matches for this career.
    Rebuilds from DB if in-memory table is empty.
    """
    # Verify career
    career_result = await db.execute(
        text("SELECT id, user_id, club_id FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    club_id = career_row[2]

    # Resolve player's club name with the same fallbacks as simulate_match
    player_club = None
    try:
        from app.data.club_budgets import CLUBS
        if club_id is not None and 1 <= club_id <= len(CLUBS):
            player_club = CLUBS[club_id - 1][0]
    except Exception:
        pass
    if not player_club and club_id and club_id >= 1000:
        try:
            from app.data.ucl_config import UCL_PARTICIPANTS
            seed = club_id - 1000
            if 1 <= seed <= len(UCL_PARTICIPANTS):
                player_club = UCL_PARTICIPANTS[seed - 1][0]
        except Exception:
            pass

    # If in-memory table is empty, rebuild from DB
    table = _get_or_build_league_table(career_id)
    if not table:
        # Rebuild from played matches in calendar_events
        result = await db.execute(
            text("""
                SELECT description
                FROM calendar_events
                WHERE career_id = :cid
                  AND event_type = 'match'
                  AND priority = 6
                  AND description LIKE '%RESULT:%'
                ORDER BY event_date ASC
            """),
            {"cid": career_id}
        )
        rows = result.fetchall()

        for row in rows:
            desc = row[0] or ""
            # Parse: "La Liga Matchday 5: vs Barcelona (H) | RESULT: 2-1"
            if "RESULT:" not in desc:
                continue
            try:
                result_part = desc.split("RESULT:")[1].strip()
                scores = result_part.split("-")
                home_score = int(scores[0].strip())
                away_score = int(scores[1].strip())

                # Determine teams
                opponent = ""
                if "vs " in desc:
                    parts = desc.split("vs ", 1)
                    if len(parts) > 1:
                        opponent = parts[1].split("(")[0].strip()

                is_home = "(H)" in desc
                home_team = player_club if is_home else opponent
                away_team = opponent if is_home else player_club

                if home_team and away_team:
                    _update_league_table(career_id, home_team, away_team, home_score, away_score)
            except (ValueError, IndexError):
                continue

        # Also initialize all league clubs with 0 if not present
        if player_club:
            try:
                from app.data.club_budgets import CLUBS as ALL_CLUBS
                player_league = None
                for cname, _, _, cleague in ALL_CLUBS:
                    if cname == player_club:
                        player_league = cleague
                        break
                if player_league:
                    league_clubs = [cname for cname, _, _, cleague in ALL_CLUBS if cleague == player_league]
                    table = _get_or_build_league_table(career_id)
                    for club in league_clubs:
                        if club not in table:
                            table[club] = {
                                "played": 0, "won": 0, "drawn": 0, "lost": 0,
                                "gf": 0, "ga": 0, "gd": 0, "points": 0,
                            }
            except Exception:
                pass

    table = _get_or_build_league_table(career_id)

    # Sort by points, then goal difference, then goals for
    standings = []
    for club_name, stats in table.items():
        standings.append({
            "club": club_name,
            "played": stats["played"],
            "won": stats["won"],
            "drawn": stats["drawn"],
            "lost": stats["lost"],
            "gf": stats["gf"],
            "ga": stats["ga"],
            "gd": stats["gd"],
            "points": stats["points"],
            "is_player": club_name == player_club,
        })

    standings.sort(key=lambda x: (-x["points"], -x["gd"], -x["gf"]))

    # Add position
    for i, entry in enumerate(standings):
        entry["position"] = i + 1

    return {
        "standings": standings,
        "player_club": player_club,
        "total_clubs": len(standings),
    }


# ─── UCL Standings Endpoint ───────────────────────────────────────────────────


@league_router.get("/ucl-table")
async def get_ucl_table(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the UEFA Champions League league-phase standings for the player's career.

    Reads the live ``ucl_standings`` table (joined with ``ucl_participants``)
    for the active 'Champions League' competition. Always shows all 36
    clubs sorted by rank.
    """
    # Verify career
    career_result = await db.execute(
        text("SELECT id, user_id, club_id FROM careers WHERE id = :cid"),
        {"cid": career_id},
    )
    career_row = career_result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    club_id = career_row[2]
    player_club = None
    try:
        from app.data.club_budgets import CLUBS
        if club_id is not None and 1 <= club_id <= len(CLUBS):
            player_club = CLUBS[club_id - 1][0]
    except Exception:
        pass

    # Find the active UCL competition. There may be multiple seasons —
    # pick the most recently created one.
    comp_result = await db.execute(
        text(
            "SELECT id, season FROM competitions "
            "WHERE name = 'Champions League' "
            "ORDER BY id DESC LIMIT 1"
        )
    )
    comp_row = comp_result.fetchone()
    if not comp_row:
        return {"standings": [], "player_club": player_club, "season": None,
                "total_clubs": 0, "message": "Champions League not generated yet"}

    competition_id, season = comp_row[0], comp_row[1]

    rows = await db.execute(
        text(
            """
            SELECT p.club_name, p.country, p.club_id,
                   s.played, s.won, s.drawn, s.lost,
                   s.goals_for, s.goals_against, s.goal_difference,
                   s.points, s.rank
            FROM ucl_standings s
            JOIN ucl_participants p ON p.id = s.participant_id
            WHERE s.competition_id = :cid
            ORDER BY
                CASE WHEN s.rank IS NULL THEN 1 ELSE 0 END,
                s.rank ASC,
                s.points DESC,
                s.goal_difference DESC,
                s.goals_for DESC,
                p.club_name ASC
            """
        ),
        {"cid": competition_id},
    )
    standings = []
    for i, r in enumerate(rows.fetchall(), start=1):
        is_player = (player_club and r[0] == player_club)
        standings.append({
            "position": r[11] or i,
            "club": r[0],
            "country": r[1],
            "played": r[3] or 0,
            "won": r[4] or 0,
            "drawn": r[5] or 0,
            "lost": r[6] or 0,
            "gf": r[7] or 0,
            "ga": r[8] or 0,
            "gd": r[9] or 0,
            "points": r[10] or 0,
            "is_player": bool(is_player),
        })

    return {
        "standings": standings,
        "player_club": player_club,
        "season": season,
        "competition_id": competition_id,
        "total_clubs": len(standings),
    }
