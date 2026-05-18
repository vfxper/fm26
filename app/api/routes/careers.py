"""
Career API Endpoints (Task 23)
POST /api/careers - Create new career
GET /api/careers/{career_id} - Get career details
POST /api/careers/{career_id}/advance-week - Progress to next week
GET /api/careers/{career_id}/objectives - Get board objectives
GET /api/careers/{career_id}/statistics - Get career statistics
POST /api/careers/{career_id}/save - Manual save
GET /api/careers/{career_id}/saves - List all saves
POST /api/careers/{career_id}/load - Load specific save
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import random
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.career_service import (
    CareerService, CareerServiceError, UserNotFoundError,
    ClubNotFoundError, CareerAlreadyExistsError
)

router = APIRouter(prefix="/careers", tags=["careers"])


# === Request/Response Models ===

class CreateCareerRequest(BaseModel):
    club_id: int = Field(..., description="ID of the club to manage")
    manager_name: str = Field(..., min_length=2, max_length=50, description="Manager name")
    difficulty: str = Field(default="normal", description="Difficulty: easy, normal, hard")
    game_mode: str = Field(
        default="full",
        pattern=r"^(full|ucl_only)$",
        description="Game mode: 'full' (standard career) or 'ucl_only' (UCL competition only)",
    )
    manager_age: Optional[int] = Field(default=40, ge=24, le=75, description="Manager age (24-75)")
    manager_country: Optional[str] = Field(default="England", max_length=60)
    dev_style: Optional[str] = Field(default="balanced", description="balanced | attack | defense | youth")
    formation: Optional[str] = Field(default="4-3-3", description="Starting tactical formation")


class CareerResponse(BaseModel):
    id: int
    user_id: int
    club_id: int
    club_name: Optional[str] = None
    manager_name: str
    season: int
    week: int
    game_date: Optional[str] = None  # ISO YYYY-MM-DD
    current_date: Optional[str] = None  # alias for backwards compat
    budget: float
    reputation: int
    board_confidence: int
    status: str
    game_mode: str = "full"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class WeekSummaryResponse(BaseModel):
    season: int
    week: int
    game_date: Optional[str] = None
    current_date: Optional[str] = None
    matches: List[Dict[str, Any]] = []
    training: Optional[Dict[str, Any]] = None
    finances: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []
    notifications: List[str] = []
    board_confidence: int = 50
    reputation: int = 50
    # Set when the user's club has a match today that hasn't been
    # played yet. The frontend uses this to interrupt the
    # "Continue" loop and show the match-day modal.
    match_today: Optional[Dict[str, Any]] = None


class ObjectiveResponse(BaseModel):
    objectives: List[Dict[str, Any]]
    evaluation: Optional[Dict[str, Any]] = None


class SaveRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Save name (optional)")


class LoadRequest(BaseModel):
    save_id: int = Field(..., description="Save slot ID to load")


# === Endpoints ===

@router.post("", response_model=CareerResponse, status_code=status.HTTP_201_CREATED)
async def create_career(
    request: CreateCareerRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new career save.

    Multi-user safe: only the careers belonging to the CURRENT user are
    wiped. Other users' carrers are left untouched. Each user can have
    exactly one active career at a time (creating a new one nukes their
    previous save).
    """
    # Find the user's existing careers and only wipe THOSE.
    own_careers = await db.execute(text(
        "SELECT id FROM careers WHERE user_id = :u"
    ), {"u": user.id})
    own_ids = [r[0] for r in own_careers.fetchall()]
    if own_ids:
        cascading = [
            "squad_players", "calendar_events", "inbox_messages",
            "matches", "match_events", "transfers", "injuries",
            "competitions", "ucl_participants", "ucl_matches",
            "ucl_phase_matchups", "training_schedules",
            "scouting_assignments", "scout_knowledge",
            "scouting_reports", "media_events", "news",
            "career_saves", "career_settings",
            "transfer_offers", "ai_transfers", "ai_window_quota",
            "scout_assignments", "player_injuries",
            "player_promises", "career_tactics",
            "match_sessions",
        ]
        ph = ",".join(f":c{i}" for i in range(len(own_ids)))
        params = {f"c{i}": cid for i, cid in enumerate(own_ids)}
        for t in cascading:
            try:
                await db.execute(text(
                    f"DELETE FROM {t} WHERE career_id IN ({ph})"
                ), params)
            except Exception:
                pass
        try:
            await db.execute(text(
                f"DELETE FROM careers WHERE id IN ({ph})"
            ), params)
        except Exception:
            pass
        await db.commit()
        # Wipe in-memory league-table cache only for THIS user's careers.
        try:
            from app.api.routes.matches import _league_tables
            for cid in own_ids:
                _league_tables.pop(cid, None)
        except Exception:
            pass

    # Direct SQL insert (works with both SQLite and PostgreSQL)
    try:
        # Resolve the managed club. In `ucl_only` mode, request.club_id is a
        # 1-based index into UCL_PARTICIPANTS; in `full` mode it indexes CLUBS.
        is_ucl_only = request.game_mode == "ucl_only"
        ucl_participant_club_id: Optional[int] = None  # 1-based CLUBS index of UCL participant if present
        ucl_seed: Optional[int] = None
        career_club_id = request.club_id  # what we store in careers.club_id

        if is_ucl_only:
            from app.data.ucl_config import UCL_PARTICIPANTS
            if not (1 <= request.club_id <= len(UCL_PARTICIPANTS)):
                raise HTTPException(404, "UCL participant not found")
            ucl_seed = request.club_id
            participant_name, participant_clubs_id, _country = UCL_PARTICIPANTS[ucl_seed - 1]
            club_name = participant_name
            ucl_participant_club_id = participant_clubs_id
            # Map career.club_id: prefer real CLUBS index when available, else use synthetic 1000+seed
            if participant_clubs_id is not None:
                career_club_id = participant_clubs_id
            else:
                career_club_id = 1000 + ucl_seed
        else:
            # Get club name from club_budgets list (clubs endpoint returns 1-based index)
            club_name = None
            try:
                from app.data.club_budgets import CLUBS
                if 1 <= request.club_id <= len(CLUBS):
                    club_name = CLUBS[request.club_id - 1][0]
            except Exception:
                pass

            # Fallback: try DB
            if not club_name:
                try:
                    club_result = await db.execute(
                        text("SELECT name FROM clubs WHERE id = :cid"),
                        {"cid": request.club_id}
                    )
                    club_row = club_result.fetchone()
                    if club_row:
                        club_name = club_row[0]
                except Exception:
                    pass

            if not club_name:
                raise HTTPException(404, "Club not found")

        # Get realistic budget for this club
        try:
            from app.data.club_budgets import get_club_budget
            scouting_budget, transfer_budget = get_club_budget(club_name)
        except Exception:
            scouting_budget, transfer_budget = 1000000, 10000000

        # Insert career directly via SQL
        result = await db.execute(
            text("""
                INSERT INTO careers (user_id, club_id, manager_name, current_season, current_week, game_date,
                    budget, manager_reputation, board_confidence, status,
                    tactical_knowledge, man_management, motivating, attacking, defending,
                    technical, mental, youth_development, board_relations,
                    seasons_managed, trophies_won, matches_won, matches_drawn, matches_lost, total_transfer_spend,
                    game_mode, manager_age, manager_country, dev_style)
                VALUES (:uid, :cid, :mname, 1, 1, '2025-07-01',
                    :budget, 50, 50, 'active',
                    10, 10, 10, 10, 10, 10, 10, 10, 10,
                    0, 0, 0, 0, 0, 0,
                    :gmode, :mage, :mcountry, :dstyle)
            """),
            {
                "uid": user.id,
                "cid": career_club_id,
                "mname": request.manager_name,
                "budget": transfer_budget,
                "gmode": request.game_mode,
                "mage": request.manager_age or 40,
                "mcountry": request.manager_country or "England",
                "dstyle": request.dev_style or "balanced",
            }
        )
        # Capture the new row id BEFORE commit() — last_insert_rowid()
        # is per-connection state that becomes unreliable across commits
        # in async SQLAlchemy pools. lastrowid on the result is set
        # synchronously by the dialect driver.
        career_id = (
            getattr(result, "lastrowid", None)
            or (
                result.inserted_primary_key[0]
                if getattr(result, "inserted_primary_key", None) else None
            )
        )
        await db.commit()

        # Fallback: re-query by user_id+manager_name pair (user_id is unique
        # per career under our "one career per user" rule).
        if not career_id:
            row = (await db.execute(
                text("SELECT id FROM careers WHERE user_id = :u "
                     "ORDER BY id DESC LIMIT 1"),
                {"u": user.id},
            )).fetchone()
            career_id = int(row[0]) if row else 1

        # Auto-populate squad. Runs in BOTH game modes — ucl_only career
        # still needs a squad to play matches with.
        try:
            players = []

            # Try exact match first — ALWAYS take only the strongest 25
            # players (no point including 8 academy goalkeepers).
            player_result = await db.execute(
                text("SELECT id, wage FROM players WHERE club = :club_name "
                     "ORDER BY ca DESC LIMIT 25"),
                {"club_name": club_name}
            )
            players = player_result.fetchall()

            # If no exact match, try every CSV-name alias for this club.
            if not players:
                try:
                    from app.data.club_budgets import CLUBS_TO_CSV
                    aliases = CLUBS_TO_CSV.get(club_name) or []
                    for alias in aliases:
                        player_result = await db.execute(
                            text("SELECT id, wage FROM players WHERE club = :club_name "
                                 "ORDER BY ca DESC LIMIT 25"),
                            {"club_name": alias}
                        )
                        players = player_result.fetchall()
                        if players:
                            print(f"  Squad matched via alias: '{alias}' -> {len(players)} players")
                            break
                except Exception:
                    pass

            # If still no match, try LIKE match on the most distinctive word
            # (avoid common words like "FC", "Real", "Club").
            if not players:
                # Pick the longest non-stopword token from club_name as the
                # search anchor.
                STOP = {"FC", "FK", "Club", "AC", "AS", "SC",
                        "United", "City", "Real", "Royal", "Royale", "of"}
                tokens = [w for w in club_name.split()
                          if len(w) > 3 and w not in STOP]
                if tokens:
                    anchor = max(tokens, key=len)
                    player_result = await db.execute(
                        text("SELECT id, wage FROM players WHERE club LIKE :pattern "
                             "ORDER BY ca DESC LIMIT 30"),
                        {"pattern": f"%{anchor}%"}
                    )
                    players = player_result.fetchall()
                    if players:
                        print(f"  Squad matched via LIKE '{anchor}' -> {len(players)} players")

            # Ultimate fallback: take 23 random unaffiliated CSV players.
            # Better than an empty squad so the user can play matches.
            if not players:
                player_result = await db.execute(
                    text(
                        "SELECT id, wage FROM players WHERE club IS NULL OR club = '' "
                        "ORDER BY ca DESC LIMIT 23"
                    )
                )
                players = player_result.fetchall()
            if not players:
                # As an absolute last resort, take top-23 by CA from anywhere.
                player_result = await db.execute(
                    text(
                        "SELECT id, wage FROM players "
                        "ORDER BY ca DESC LIMIT 23"
                    )
                )
                players = player_result.fetchall()
                print(
                    f"  WARNING: no players matched club '{club_name}' — "
                    f"used top-23 fallback squad"
                )

            # Top-up: if we matched but got fewer than 18 players, fill the
            # roster up to 23 with similarly-skilled free agents so the
            # match engine has enough bodies. Player IDs already in
            # `players` are excluded.
            if 0 < len(players) < 18:
                have_ids = {int(p[0]) for p in players}
                placeholders = ",".join(f":x{i}" for i in range(len(have_ids)))
                params = {f"x{i}": pid for i, pid in enumerate(have_ids)}
                avg_ca = max(80, sum(int(p[0]) for p in players) // max(1, len(players)) // 1000 * 50 + 80)
                fill_sql = (
                    "SELECT id, wage FROM players "
                    f"WHERE id NOT IN ({placeholders}) "
                    "AND ca BETWEEN 70 AND 150 "
                    "ORDER BY RANDOM() LIMIT :need"
                )
                params["need"] = 23 - len(players)
                fill_res = await db.execute(text(fill_sql), params)
                fillers = fill_res.fetchall()
                if fillers:
                    players = list(players) + list(fillers)
                    print(
                        f"  Squad top-up: added {len(fillers)} filler players "
                        f"to '{club_name}' (now {len(players)} total)"
                    )

            # Assign squad numbers by position to look like a real squad:
            # 1, 13, 25 -> goalkeepers
            # 2-6, 14-18 -> defenders
            # 7-8, 19-22 -> midfielders
            # 9-11, 23 -> attackers
            # Resolve each player's CSV position once, then bucket them.
            pid_pos = {}
            if players:
                ph = ",".join(f":p{i}" for i in range(len(players)))
                qparams = {f"p{i}": int(p[0]) for i, p in enumerate(players)}
                pos_rows = await db.execute(
                    text(f"SELECT id, position FROM players WHERE id IN ({ph})"),
                    qparams,
                )
                for row in pos_rows.fetchall():
                    pid_pos[int(row[0])] = (row[1] or "").upper()

            def _bucket(pos: str) -> str:
                if "GK" in pos: return "GK"
                if pos.startswith("ST") or "/ST" in pos or "AM/ST" in pos: return "ATT"
                if "AM" in pos: return "AM"
                if pos.startswith("M") or pos.startswith("DM") or "M C" in pos or "M/AM" in pos: return "MID"
                return "DEF"

            buckets = {"GK": [], "DEF": [], "MID": [], "AM": [], "ATT": []}
            for pid, _ in [(int(p[0]), p[1]) for p in players]:
                buckets[_bucket(pid_pos.get(pid, ""))].append(pid)

            num_ranges = {
                "GK":  [1, 13, 25],
                "DEF": [2, 3, 4, 5, 6, 14, 15, 16, 17, 18, 24, 26],
                "MID": [6, 7, 8, 19, 20, 21, 27, 28],
                "AM":  [10, 11, 22, 29, 30],
                "ATT": [9, 10, 11, 23, 31, 32, 33],
            }
            assigned: dict[int, int] = {}
            used_nums: set[int] = set()
            for bk, pids in buckets.items():
                pool = list(num_ranges.get(bk, []))
                for pid in pids:
                    chosen = None
                    for n in pool:
                        if n not in used_nums:
                            chosen = n
                            break
                    if chosen is None:
                        # fall back to next free 1..99
                        for n in range(1, 100):
                            if n not in used_nums:
                                chosen = n
                                break
                    used_nums.add(chosen)
                    assigned[pid] = chosen

            for player_row in players:
                # Morale starts at 100 for everyone at career start —
                # they'll lose it through bench time, broken promises,
                # poor results etc.
                pid = int(player_row[0])
                num = assigned.get(pid, 99)
                await db.execute(
                    text("""
                        INSERT INTO squad_players (career_id, player_id, squad_number, status, morale, fitness, wage, contract_years, contract_expiry, is_transfer_listed, is_loan_listed, is_injured, is_loaned)
                        VALUES (:cid, :pid, :num, 'starter', 100, 100, :wage, 2, '2027-06-30', 0, 0, 0, 0)
                    """),
                    {"cid": career_id, "pid": pid, "num": num, "wage": player_row[1] or 50000}
                )
            await db.commit()

            # Auto-assign squad roles based on relative CA. A weak team's
            # best player is still a "star" in that squad, even if he'd
            # only be a "starter" at Real Madrid.
            try:
                from app.services.squad_roles import auto_assign_roles
                rows = await db.execute(text(
                    "SELECT sp.id, p.ca, p.age FROM squad_players sp "
                    "JOIN players p ON p.id = sp.player_id "
                    "WHERE sp.career_id = :c"
                ), {"c": career_id})
                squad = [
                    {"sp_id": r[0], "ca": r[1] or 0, "age": r[2] or 25}
                    for r in rows.fetchall()
                ]
                roles = auto_assign_roles(squad)
                for member, role in zip(squad, roles):
                    await db.execute(text(
                        "UPDATE squad_players SET status = :r WHERE id = :i"
                    ), {"r": role, "i": member["sp_id"]})
                await db.commit()
                print(f"  Roles assigned: {dict((r, roles.count(r)) for r in set(roles))}")
            except Exception as e:
                print(f"Role assignment warning: {e}")

            print(f"  Squad populated: {len(players)} players for {club_name}")
        except Exception as e:
            print(f"Squad populate warning: {e}")

        # Domestic league calendar — full mode only.
        if not is_ucl_only:
            try:
                from app.services.calendar_engine import CalendarEngine
                calendar_engine = CalendarEngine(db)
                await calendar_engine.generate_season(career_id, request.club_id, club_name, 2025)
                print(f"  Calendar generated for {club_name}")
            except Exception as e:
                print(f"  Calendar generation warning: {e}")
        else:
            print(f"  ucl_only mode: skipping league calendar for {club_name}")

        # Persist initial tactic if user picked one in the wizard.
        try:
            await db.execute(text(
                "INSERT OR REPLACE INTO career_tactics "
                "(career_id, formation) VALUES (:c, :f)"
            ), {"c": career_id, "f": request.formation or "4-3-3"})
            await db.commit()
        except Exception as e:
            print(f"  Tactic init warning: {e}")

        # Auto-generate UCL competition
        try:
            from app.services.ucl_generator import UCLGenerator
            ucl = UCLGenerator(db)
            # In ucl_only mode, anchor player descriptions to the participant's
            # CLUBS index when available; else None (events use generic descriptions).
            anchor_club_id = ucl_participant_club_id if is_ucl_only else request.club_id
            await ucl.generate_competition(career_id, year=2025, player_club_id=anchor_club_id)
            print(f"  UCL competition generated for career {career_id}")
        except Exception as e:
            print(f"  UCL generation warning: {e}")

        # Auto-generate UEL + UECL league-phase fixtures (basic
        # schedule only — knockout for these two not modelled yet).
        # Player sees calendar entries only if their club is on the roster.
        try:
            from app.services.eu_competitions import generate_eu_competitions
            anchor_club_id = ucl_participant_club_id if is_ucl_only else request.club_id
            eu_summary = await generate_eu_competitions(
                db, career_id=career_id, year=2025,
                player_club_id=anchor_club_id,
                player_club_name=club_name,
            )
            print(f"  EU competitions: {eu_summary}")
        except Exception as e:
            print(f"  EU competitions warning: {e}")

        # Manager appointment news — first thing the user sees on the
        # Inbox tab. Headline matches FM-style press release.
        try:
            from app.api.routes.inbox import push_inbox_message
            await push_inbox_message(
                db,
                career_id,
                category="appointment",
                subject=f"{request.manager_name} — новый тренер {club_name}",
                body=(
                    f"{club_name} объявил о назначении {request.manager_name} "
                    f"главным тренером команды. Совет директоров выделил "
                    f"бюджет £{int(transfer_budget):,} на трансферы и ждёт "
                    "сильного старта сезона."
                ),
                on_date="2025-07-01",
                is_pinned=True,
            )
        except Exception:
            pass

        return CareerResponse(
            id=career_id,
            user_id=user.id,
            club_id=career_club_id,
            club_name=club_name,
            manager_name=request.manager_name,
            season=1,
            week=1,
            budget=float(transfer_budget),
            reputation=50,
            board_confidence=50,
            status="active",
            game_mode=request.game_mode,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to create career: {str(e)}")


@router.get("/{career_id}", response_model=CareerResponse)
async def get_career(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get career details."""
    # Use raw SQL for SQLite compatibility
    try:
        result = await db.execute(
            text("""SELECT id, user_id, club_id, manager_name, current_season, current_week,
                    budget, manager_reputation, board_confidence, status, game_mode, game_date
                    FROM careers WHERE id = :cid"""),
            {"cid": career_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(404, "Career not found")
        if row[1] != user.id:
            raise HTTPException(403, "Not your career")
        
        # Get club name. For ucl_only mode with a synthetic id (>=1000), look up
        # the participant directly from UCL_PARTICIPANTS instead of CLUBS.
        club_name = None
        club_id_val = row[2]
        game_mode = row[10] or "full"
        try:
            if club_id_val is not None and club_id_val >= 1000:
                from app.data.ucl_config import UCL_PARTICIPANTS
                seed = club_id_val - 1000
                if 1 <= seed <= len(UCL_PARTICIPANTS):
                    club_name = UCL_PARTICIPANTS[seed - 1][0]
            else:
                from app.data.club_budgets import CLUBS
                if club_id_val is not None and 1 <= club_id_val <= len(CLUBS):
                    club_name = CLUBS[club_id_val - 1][0]
        except Exception:
            pass
        
        return CareerResponse(
            id=row[0],
            user_id=row[1],
            club_id=row[2],
            club_name=club_name,
            manager_name=row[3],
            season=row[4] or 1,
            week=row[5] or 1,
            game_date=row[11] or "2025-07-01",
            current_date=row[11] or "2025-07-01",
            budget=float(row[6] or 50000000),
            reputation=row[7] or 50,
            board_confidence=row[8] or 50,
            status=row[9] or "active",
            game_mode=game_mode,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/{career_id}/advance-day", response_model=WeekSummaryResponse)
async def advance_day(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advance career by one in-game day. Updates `game_date` (YYYY-MM-DD)."""
    result = await db.execute(
        text(
            "SELECT id, user_id, current_season, current_week, board_confidence, "
            "manager_reputation, game_date FROM careers WHERE id = :cid"
        ),
        {"cid": career_id}
    )
    career_row = result.fetchone()
    if not career_row:
        raise HTTPException(404, "Career not found")
    if career_row[1] != user.id:
        raise HTTPException(403, "Not your career")

    cur_date_str = career_row[6] or "2025-07-01"
    try:
        cur_date = datetime.strptime(cur_date_str, "%Y-%m-%d").date()
    except ValueError:
        cur_date = datetime(2025, 7, 1).date()
    new_date = cur_date + timedelta(days=1)

    # Derive the FM-style "season/week" cosmetic counters from the date.
    # Season starts on July 1 of the season-start year. Each Monday flips
    # the week counter. Once the date crosses next-year July 1 the season
    # rolls over.
    season = career_row[2] or 1
    season_start_year = 2025 + (season - 1)
    season_start = datetime(season_start_year, 7, 1).date()
    if new_date >= datetime(season_start_year + 1, 7, 1).date():
        season += 1
        season_start_year += 1
        season_start = datetime(season_start_year, 7, 1).date()
    days_into_season = max(0, (new_date - season_start).days)
    week = days_into_season // 7 + 1

    await db.execute(
        text(
            "UPDATE careers SET game_date = :d, current_week = :w, "
            "current_season = :s WHERE id = :cid"
        ),
        {"d": str(new_date), "w": week, "s": season, "cid": career_id},
    )
    await db.commit()

    board_confidence = career_row[4] or 50
    reputation = career_row[5] or 50
    notifications = []

    # ── Transfer-window state-change notification ────────────────────────
    # Detect transitions of the window status between yesterday and today
    # and push a single inbox event so the user knows when they can
    # buy/sell. Window: summer 1-8, winter 26-30.
    try:
        from app.services.transfer_window import (
            TransferWindowService, WindowType,
        )
        tws = TransferWindowService()
        prev_week = ((days_into_season - 1) // 7) + 1 if days_into_season > 0 else 1
        prev_week = max(1, min(52, prev_week))
        new_week = max(1, min(52, week))
        prev_status = tws.get_window_status(prev_week).window_type
        new_status = tws.get_window_status(new_week).window_type
        if prev_status != new_status:
            from app.api.routes.inbox import push_inbox_message
            if new_status == WindowType.CLOSED:
                subject = "Трансферное окно закрыто"
                body = (
                    "Покупки и продажи теперь невозможны до следующего "
                    "окна. Свободных агентов и экстренные аренды по-"
                    "прежнему можно подписать."
                )
            elif new_status == WindowType.SUMMER:
                subject = "Открыто летнее трансферное окно"
                body = (
                    "Окно открыто до 8-й недели сезона. Самое время "
                    "усилить состав — переговоры доступны во вкладке "
                    "Переговоры."
                )
            else:  # WINTER
                subject = "Открыто зимнее трансферное окно"
                body = (
                    "Зимнее окно открыто до 30-й недели сезона. "
                    "Можно довести состав до нужного баланса перед "
                    "решающей частью сезона."
                )
            try:
                await push_inbox_message(
                    db, career_id,
                    category="news",
                    subject=subject, body=body, date=str(new_date),
                )
                await db.commit()
                notifications.append(subject)
            except Exception:
                pass
    except Exception:
        pass

    # ── AI auto-simulation of background matches ──────────────────────────
    # Each new in-game day, simulate every NON-PLAYER match scheduled on
    # this date so the league/UCL tables stay in sync with the player's
    # progression. The player's own match is left untouched (they will
    # play it from the Match tab).
    try:
        from app.services.background_match_runner import (
            run_background_matches_for_day,
        )
        ai_results = await run_background_matches_for_day(
            db, career_id=career_id, on_date=str(new_date)
        )
        for line in ai_results.get("notifications", []):
            notifications.append(line)
        if ai_results.get("ucl_advanced"):
            notifications.append(
                f"🌟 ЛЧ: " + ai_results["ucl_advanced"]
            )
    except Exception as e:
        # Background simulation is best-effort; never block the day flip.
        notifications.append(f"⚠ Авто-сим: {e}")

    # Process scouting once per Monday only (was running every day before).
    if new_date.weekday() == 0:
        try:
            from app.api.routes.scouting import _get_centre
            centre = _get_centre(career_id)
            player_result = await db.execute(text(
                "SELECT id, name, age, position, nationality, club, ca, pa, pace, dribbling, "
                "passing, finishing, tackling, heading, vision, strength, composure, stamina, "
                "concentration, decisions, work_rate, marking FROM players "
                "ORDER BY RANDOM() LIMIT 500"
            ))
            all_players = []
            for row in player_result.fetchall():
                all_players.append({
                    "id": row[0], "name": row[1], "age": row[2], "position": row[3],
                    "nationality": row[4], "club": row[5], "ca": row[6], "pa": row[7],
                    "pace": row[8], "dribbling": row[9], "passing": row[10], "finishing": row[11],
                    "tackling": row[12], "heading": row[13], "vision": row[14], "strength": row[15],
                    "composure": row[16], "stamina": row[17], "concentration": row[18],
                    "decisions": row[19], "work_rate": row[20], "marking": row[21],
                })
            new_reports = centre.process_week(all_players)
            if new_reports:
                for r in new_reports:
                    notifications.append(f"🔍 Скаут нашёл: {r.player_name} ({r.recommendation})")
        except Exception:
            pass  # Scouting is non-fatal

    # ─── Daily AI-vs-AI transfers (window-gated) ─────────────────────────
    try:
        from app.services.ai_transfer_engine import run_daily_ai_transfers
        from app.data.club_budgets import CLUBS as _CLUBS
        cclub_row = await db.execute(text(
            "SELECT club_id FROM careers WHERE id = :c"
        ), {"c": career_id})
        cc = cclub_row.scalar()
        player_club_name = None
        if cc and 1 <= cc <= len(_CLUBS):
            player_club_name = _CLUBS[cc - 1][0]
        ai_news = await run_daily_ai_transfers(
            db, career_id=career_id, on_date=str(new_date),
            player_club_name=player_club_name,
        )
        # NOTE: run_daily_ai_transfers() already pushes each headline to
        # the inbox under category="news_transfer". We deliberately do
        # NOT append them to `notifications` here, otherwise every
        # transfer would show up TWICE (once as news_transfer, once as
        # news) — that's the duplication the user reported.
        _ = ai_news  # kept for future use / debugging
    except Exception as e:
        print(f"AI transfers warning: {e}")

    # ─── Scouting deliveries (assignments whose due_date has come) ──────
    try:
        from app.services.scouting_service import deliver_due_assignments
        delivered = await deliver_due_assignments(
            db, career_id=career_id, on_date=str(new_date)
        )
        for d in delivered:
            cnt = len((d.get("result") or {}).get("players", []))
            notifications.append(f"🔎 Готов отчёт скаута: {cnt} игроков")
    except Exception as e:
        print(f"Scout delivery warning: {e}")

    # ─── Injury system: training risk + recoveries ───────────────────────
    try:
        from app.services.injury_service import (
            ensure_catalogue_seeded, run_daily_training_check,
            progress_recoveries,
        )
        await ensure_catalogue_seeded(db)
        try:
            mr = await db.execute(text(
                "SELECT training_mode FROM careers WHERE id=:c"
            ), {"c": career_id})
            training_mode = mr.scalar() or "balanced"
        except Exception:
            training_mode = "balanced"
        await run_daily_training_check(
            db, career_id=career_id, on_date=str(new_date),
            training_intensity=training_mode,
        )
        await progress_recoveries(db, career_id=career_id, on_date=str(new_date))
    except Exception as e:
        print(f"Injury daily warning: {e}")

    # ─── Player development tick (CA/PA + birthdays) ─────────────────────
    try:
        from app.services.player_development import run_daily_progression
        try:
            mr = await db.execute(text(
                "SELECT training_mode FROM careers WHERE id=:c"
            ), {"c": career_id})
            # If the user hasn't picked a training plan yet, leave it as
            # "none" — that maps to a much slower progression rate so the
            # user has a reason to set one up.
            tm_dev = mr.scalar() or "none"
        except Exception:
            tm_dev = "none"
        dev = await run_daily_progression(
            db, career_id=career_id, on_date=str(new_date),
            training_mode=tm_dev,
        )
        if dev.get("birthdays", 0) > 0:
            notifications.append(f"🎂 {dev['birthdays']} игроков отметили день рождения")
        if dev.get("promotions", 0) >= 3:
            notifications.append(f"📈 {dev['promotions']} игроков выросли в CA сегодня")
    except Exception as e:
        print(f"Player dev warning: {e}")

    # ─── Promises (daily expiry check) ────────────────────────────────────
    try:
        from app.services.promise_service import evaluate_promises
        broken = await evaluate_promises(db, career_id=career_id, on_date=str(new_date))
        if broken:
            notifications.append(f"💢 Нарушенных обещаний: {broken}")
    except Exception as e:
        print(f"Promise eval warning: {e}")

    # ─── Weekly player requests (every Monday) ───────────────────────────
    if new_date.weekday() == 0:
        try:
            from app.services.player_requests import run_weekly_player_requests
            n = await run_weekly_player_requests(
                db, career_id=career_id, on_date=str(new_date)
            )
            if n:
                notifications.append(f"📩 Игроки прислали {n} обращений")
        except Exception as e:
            print(f"Player requests warning: {e}")
        # Contract expiry — runs same day. Players whose contract is up
        # leave on free transfer. Players within 6 months of expiry get
        # a one-time renewal demand in the inbox.
        try:
            from app.services.contract_expiry import run_weekly_contract_expiry
            left_n, demand_n = await run_weekly_contract_expiry(
                db, career_id=career_id, on_date=str(new_date)
            )
            if left_n:
                notifications.append(f"📋 {left_n} игроков ушло по истечении контракта")
            if demand_n:
                notifications.append(f"📋 {demand_n} игроков требуют продления")
        except Exception as e:
            print(f"Contract expiry warning: {e}")

    # Push every accumulated notification line as an inbox message so the
    # user can scroll back through past events. We dedupe identical
    # subjects to avoid blowing up the inbox on busy days.
    if notifications:
        try:
            from app.api.routes.inbox import push_inbox_message
            seen: set[str] = set()
            for line in notifications:
                if not line or line in seen:
                    continue
                seen.add(line)
                # Pick category from the leading emoji/keyword.
                cat = "news"
                low = line.lower()
                if "скаут" in low or "🔍" in line:
                    cat = "scouting"
                elif "лч" in low or "🌟" in line or "champions" in low:
                    cat = "ucl"
                elif "матч" in low or "победа" in low or "ничья" in low or "поражение" in low:
                    cat = "match"
                elif "контракт" in low:
                    cat = "contract"
                elif "трансфер" in low:
                    cat = "transfer"
                elif "⚠" in line:
                    cat = "warning"
                # Subject = first 80 chars; body = rest.
                subj = line[:80]
                body = line[80:] if len(line) > 80 else ""
                await push_inbox_message(
                    db,
                    career_id,
                    category=cat,
                    subject=subj,
                    body=body,
                    on_date=str(new_date),
                )
        except Exception:
            pass

    # ── Match-today detection ─────────────────────────────────────────
    # If the new in-game date has a non-locked match involving the
    # player's club, surface it so the UI can show a modal asking
    # "Сыграть с перерывом / Симулировать". The player should NEVER be
    # able to advance past their own match without making a choice.
    match_today: Optional[Dict[str, Any]] = None
    try:
        cclub = await db.execute(text(
            "SELECT club_id FROM careers WHERE id = :c"
        ), {"c": career_id})
        player_club_id = cclub.scalar()
        if player_club_id is not None:
            ev_row = await db.execute(text(
                "SELECT id, event_type, home_club_id, away_club_id, "
                "       description, kick_off_time, priority "
                "FROM calendar_events "
                "WHERE career_id = :c "
                "  AND event_date = :d "
                "  AND COALESCE(is_cancelled, 0) = 0 "
                "  AND COALESCE(is_locked, 0) = 0 "
                "  AND event_type IN ('match', 'uel', 'uecl') "
                "  AND (home_club_id = :pc OR away_club_id = :pc) "
                "ORDER BY priority DESC, id ASC LIMIT 1"
            ), {"c": career_id, "d": str(new_date), "pc": player_club_id})
            ev = ev_row.fetchone()
            if ev:
                match_today = {
                    "event_id": int(ev[0]),
                    "event_type": ev[1],
                    "home_club_id": ev[2],
                    "away_club_id": ev[3],
                    "description": ev[4] or "",
                    "kick_off_time": ev[5] or "",
                    "priority": int(ev[6] or 0),
                    "is_player_home": (ev[2] == player_club_id),
                }
    except Exception as e:
        print(f"  match-today detect warning: {e}")

    return WeekSummaryResponse(
        season=season,
        week=week,
        game_date=str(new_date),
        current_date=str(new_date),
        matches=[],
        training=None,
        finances=None,
        events=[],
        notifications=notifications,
        board_confidence=board_confidence,
        reputation=reputation,
        match_today=match_today,
    )


@router.post("/{career_id}/advance-week", response_model=WeekSummaryResponse)
async def advance_week(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Legacy weekly advance — kept for backwards compatibility, calls
    advance_day 7 times. New UI should use ``/advance-day``."""
    last: Optional[WeekSummaryResponse] = None
    for _ in range(7):
        last = await advance_day(career_id, user=user, db=db)
    if last is None:
        raise HTTPException(500, "advance_week loop produced no result")
    return last


class JumpToDateRequest(BaseModel):
    target_date: str = Field(..., description="ISO date YYYY-MM-DD to jump to")
    auto_play_user_matches: bool = Field(
        default=True,
        description="If True, the user's matches between current date and "
                    "the target are auto-simulated using saved formation. "
                    "If False, the loop stops on the first user match.",
    )


@router.post("/{career_id}/jump-to-date")
async def jump_to_date(
    career_id: int,
    request: JumpToDateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fast-forward up to 6 months. Player matches are auto-simulated
    using the saved lineup unless ``auto_play_user_matches=False``."""
    # Verify ownership.
    car = await db.execute(text(
        "SELECT user_id, game_date FROM careers WHERE id = :c"
    ), {"c": career_id})
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    cur_iso = row[1] or "2025-07-01"
    try:
        from datetime import date as _date
        cy, cm, cd = (int(p) for p in cur_iso.split("-"))
        ty, tm, td = (int(p) for p in request.target_date.split("-"))
        cur_d = _date(cy, cm, cd)
        tgt_d = _date(ty, tm, td)
    except Exception:
        raise HTTPException(422, "Bad target_date format (expected YYYY-MM-DD)")
    if tgt_d <= cur_d:
        raise HTTPException(422, "target_date must be after current date")
    days_to_jump = (tgt_d - cur_d).days
    if days_to_jump > 200:
        raise HTTPException(422, "Cannot jump more than 200 days at once")

    # Loop. Auto-simulate user matches via simulate_match_event.
    auto_played = 0
    stopped_at: Optional[str] = None
    for _ in range(days_to_jump):
        summary = await advance_day(career_id, user=user, db=db)
        mt = summary.match_today
        if mt and mt.get("event_id"):
            if request.auto_play_user_matches:
                # Auto-simulate by reusing the existing simulate path.
                try:
                    from app.api.routes.calendar import simulate_match_event
                    await simulate_match_event(
                        career_id=career_id, event_id=int(mt["event_id"]),
                        user=user, db=db,
                    )
                    auto_played += 1
                except Exception as e:
                    print(f"  jump auto-sim warning: {e}")
            else:
                stopped_at = summary.current_date
                return {
                    "stopped_at": stopped_at,
                    "match_today": mt,
                    "auto_played": auto_played,
                }
    return {
        "current_date": str(tgt_d),
        "auto_played": auto_played,
        "stopped_at": None,
    }


@router.get("/{career_id}/objectives", response_model=ObjectiveResponse)
async def get_objectives(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get board objectives for current season."""
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user.id:
        raise HTTPException(403, "Not your career")

    objectives = service.generate_board_objectives(career)
    evaluation = service.evaluate_objectives(career)

    return ObjectiveResponse(
        objectives=[o.to_dict() if hasattr(o, 'to_dict') else o for o in objectives],
        evaluation=evaluation,
    )


@router.get("/{career_id}/statistics")
async def get_statistics(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get career statistics summary."""
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user.id:
        raise HTTPException(403, "Not your career")

    summary = await service.get_career_summary(career_id)
    hall_of_fame = service.get_hall_of_fame(career)

    return {
        "summary": summary,
        "hall_of_fame": [h.to_dict() for h in hall_of_fame],
        "recent_results": service.get_recent_results(career),
    }


@router.post("/{career_id}/save")
async def save_career(
    career_id: int,
    request: SaveRequest = SaveRequest(),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manual save current career state."""
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user.id:
        raise HTTPException(403, "Not your career")

    from app.services.save_service import SaveService
    save_svc = SaveService(db)
    result = await save_svc.manual_save(career_id, user.id, request.name)
    return result


@router.get("/{career_id}/saves")
async def list_saves(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all save slots for this career."""
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user.id:
        raise HTTPException(403, "Not your career")

    from app.services.save_service import SaveService
    save_svc = SaveService(db)
    saves = await save_svc.list_saves(career_id, user.id)
    return {"saves": saves}


@router.post("/{career_id}/load")
async def load_save(
    career_id: int,
    request: LoadRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load a specific save slot."""
    from app.services.save_service import SaveService
    save_svc = SaveService(db)
    result = await save_svc.load_save(request.save_id, user.id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Load failed"))
    return result


@router.delete("/{career_id}")
async def delete_career(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a career and all related rows.

    Cascades manually because we use raw SQL — drops squad rows,
    calendar events, inbox messages, UCL data, news, scouting, etc.
    """
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    # Tables that key off career_id. List is permissive — DELETE
    # against a non-existing table is wrapped in try/except so the
    # endpoint stays robust during schema evolution.
    tables = [
        "squad_players",
        "calendar_events",
        "inbox_messages",
        "matches",
        "match_events",
        "transfers",
        "injuries",
        "competitions",
        "ucl_participants",
        "ucl_matches",
        "ucl_phase_matchups",
        "training_schedules",
        "scouting_assignments",
        "scouting_reports",
        "media_events",
        "news",
        "saves",
        "career_settings",
    ]
    for t in tables:
        try:
            await db.execute(
                text(f"DELETE FROM {t} WHERE career_id = :cid"),
                {"cid": career_id},
            )
        except Exception:
            pass
    await db.execute(
        text("DELETE FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    await db.commit()
    return {"success": True, "deleted": career_id}


# ─── Training ───────────────────────────────────────────────────────────


class TrainingModeRequest(BaseModel):
    mode: str = Field(
        ...,
        pattern=r"^(balanced|attack|defense|fitness|set_pieces|recovery)$",
        description="Training focus for the week",
    )


@router.get("/{career_id}/training")
async def get_training(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current training mode for the career."""
    car = await db.execute(
        text("SELECT user_id, training_mode FROM careers WHERE id = :cid"),
        {"cid": career_id},
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")
    return {"mode": row[1] or "balanced"}


@router.post("/{career_id}/training")
async def set_training(
    career_id: int,
    request: TrainingModeRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a new training mode for the career.

    The careers table may not yet have a ``training_mode`` column on
    older saves — we ALTER it lazily on first use.
    """
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    # Lazily add the column if missing. SQLite ALTER is a no-op on retry
    # because we wrap in try/except.
    try:
        await db.execute(
            text(
                "ALTER TABLE careers ADD COLUMN training_mode "
                "VARCHAR(20) DEFAULT 'balanced'"
            )
        )
        await db.commit()
    except Exception:
        pass  # column already exists

    await db.execute(
        text("UPDATE careers SET training_mode = :m WHERE id = :cid"),
        {"m": request.mode, "cid": career_id},
    )
    await db.commit()
    return {"success": True, "mode": request.mode}
