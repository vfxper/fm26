"""
Squad API Endpoints (Task 24)
GET /api/careers/{career_id}/squad - Get full squad
POST /api/careers/{career_id}/squad/lineup - Set matchday lineup
PUT /api/careers/{career_id}/squad/{player_id}/status - Update squad status
POST /api/careers/{career_id}/squad/{player_id}/interact - Player interaction
GET /api/careers/{career_id}/squad/{player_id} - Get player details
POST /api/careers/{career_id}/squad/{player_id}/contract - Manage contract
GET /api/players/{player_id}/profile - Get complete player profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.squad_service import SquadService
from app.services.career_service import CareerService
from app.models.squad_player import SquadPlayer
from app.models.player import Player

router = APIRouter(tags=["squad"])


class LineupRequest(BaseModel):
    starters: List[int] = Field(..., min_length=11, max_length=11, description="11 player IDs")
    subs: List[int] = Field(..., max_length=7, description="Up to 7 substitute player IDs")


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="key_player, first_team, rotation, backup, youth, not_needed")


class InteractionRequest(BaseModel):
    interaction_type: str = Field(..., description="praise, criticise, encourage, warn, fine, drop")
    reason: Optional[str] = None


class ContractRequest(BaseModel):
    action: str = Field(..., description="offer_new, terminate, release")
    wage: Optional[int] = None
    years: Optional[int] = Field(None, ge=1, le=5)


# === Squad Endpoints ===

@router.get("/careers/{career_id}/squad")
async def get_squad(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full squad with all player details."""
    # Use raw SQL for SQLite compatibility
    try:
        result = await db.execute(
            text("""
                SELECT sp.id, sp.player_id, sp.squad_number, sp.status, sp.morale, sp.fitness, sp.wage, sp.is_injured,
                       p.name, p.position, p.age, p.ca, p.pa, p.nationality, p.club, p.wage as player_wage,
                       sp.contract_years, sp.contract_expiry, sp.is_transfer_listed, sp.is_loan_listed,
                       sp.training_role, sp.individual_focus, sp.individual_intensity
                FROM squad_players sp
                JOIN players p ON p.id = sp.player_id
                WHERE sp.career_id = :cid
                ORDER BY sp.squad_number
            """),
            {"cid": career_id}
        )
        rows = result.fetchall()
        
        squad = []
        for row in rows:
            squad.append({
                "squad_player_id": row[0],
                "player_id": row[1],
                "squad_number": row[2],
                "status": row[3],
                "morale": row[4],
                "fitness": row[5],
                # Use the SQUAD-PLAYER wage (sp.wage = career-specific
                # contract). p.wage is the global CSV default and gets
                # confusingly displayed even after renegotiation if we
                # keep it as the primary source. Fall back only if the
                # career row wasn't initialised with a wage yet.
                "wage": row[6] or row[15] or 0,
                "is_injured": row[7],
                "name": row[8],
                "position": row[9],
                "age": row[10],
                "ca": row[11],
                "pa": row[12],
                "nationality": row[13],
                "club": row[14],
                "contract_years": row[16] or 0,
                "contract_expiry": row[17],
                "is_transfer_listed": bool(row[18]) if row[18] is not None else False,
                "is_loan_listed": bool(row[19]) if row[19] is not None else False,
                "training_role": row[20],
                "individual_focus": row[21],
                "individual_intensity": row[22] or "normal",
            })
        
        return {"squad": squad, "count": len(squad)}
    except Exception as e:
        return {"squad": [], "count": 0, "error": str(e)}


@router.post("/careers/{career_id}/squad/lineup")
async def set_lineup(
    career_id: int,
    request: LineupRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set matchday lineup (11 starters + up to 7 subs)."""
    career = await _verify_career(career_id, user.id, db)
    service = SquadService()

    # Validate
    validation = service.validate_matchday_squad(
        starters_count=len(request.starters),
        subs_count=len(request.subs),
    )
    if not validation.is_valid:
        raise HTTPException(400, f"Invalid lineup: {validation.message}")

    # Store lineup in career data
    career.matchday_lineup = {
        "starters": request.starters,
        "subs": request.subs,
    }
    await db.commit()

    return {"success": True, "starters": len(request.starters), "subs": len(request.subs)}


@router.put("/careers/{career_id}/squad/{player_id}/status")
async def update_status(
    career_id: int,
    player_id: int,
    request: StatusUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update player squad status."""
    await _verify_career(career_id, user.id, db)

    result = await db.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Player not in squad")

    service = SquadService()
    service.set_squad_status(sp, request.status)
    await db.commit()

    return {"success": True, "player_id": player_id, "new_status": request.status}


@router.post("/careers/{career_id}/squad/{player_id}/interact")
async def interact_with_player(
    career_id: int,
    player_id: int,
    request: InteractionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Interact with a player (praise, criticise, etc.)."""
    await _verify_career(career_id, user.id, db)

    result = await db.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Player not in squad")

    service = SquadService()
    interaction_result = service.interact_with_player(
        squad_player=sp,
        interaction_type=request.interaction_type,
        player_personality=getattr(sp, 'personality', 'balanced'),
    )
    await db.commit()

    return {
        "success": True,
        "result": interaction_result.__dict__ if hasattr(interaction_result, '__dict__') else str(interaction_result),
    }


@router.get("/careers/{career_id}/squad/{player_id}")
async def get_squad_player(
    career_id: int,
    player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed player info within squad context."""
    await _verify_career(career_id, user.id, db)

    result = await db.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Player not in squad")

    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()

    service = SquadService()
    profile = service.get_player_full_profile(player, sp)

    return profile


@router.post("/careers/{career_id}/squad/{player_id}/contract")
async def manage_contract(
    career_id: int,
    player_id: int,
    request: ContractRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manage player contract (offer new, terminate, release).

    Uses raw SQL because the SquadPlayer ORM model and the actual
    run_local.py schema have drifted apart (ORM has contract_start_date/
    end_date, the live SQLite has contract_expiry/contract_years).
    """
    await _verify_career(career_id, user.id, db)

    cur = await db.execute(text(
        "SELECT id, wage, contract_years, contract_expiry "
        "FROM squad_players WHERE career_id = :c AND player_id = :p"
    ), {"c": career_id, "p": player_id})
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Player not in squad")
    sp_id, cur_wage, cur_years, cur_expiry = row

    if request.action == "release":
        await db.execute(text(
            "DELETE FROM squad_players WHERE id = :i"
        ), {"i": sp_id})
        await db.commit()
        return {"success": True, "action": "released", "player_id": player_id}

    elif request.action == "offer_new":
        new_wage = int(request.wage) if request.wage else cur_wage
        new_years = int(request.years) if request.years else cur_years
        new_expiry = cur_expiry
        if request.years:
            try:
                cur_d = await db.execute(
                    text("SELECT current_date FROM careers WHERE id = :c"),
                    {"c": career_id},
                )
                d = cur_d.scalar()
                base_year = None
                if d:
                    import re
                    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d))
                    if m:
                        base_year = int(m.group(1))
                        suffix = f"{m.group(2)}-{m.group(3)}"
                if base_year is None:
                    # No career current_date set — fall back to a sane
                    # season anchor (June 30 of next year).
                    from datetime import date as _date
                    base_year = _date.today().year
                    suffix = "06-30"
                new_expiry = f"{base_year + int(request.years)}-{suffix}"
            except Exception:
                pass

        await db.execute(text(
            "UPDATE squad_players SET wage = :w, contract_years = :y, "
            "contract_expiry = :e WHERE id = :i"
        ), {"w": new_wage, "y": new_years, "e": new_expiry, "i": sp_id})
        await db.commit()
        return {
            "success": True,
            "action": "contract_offered",
            "wage": new_wage,
            "years": new_years,
            "expiry": new_expiry,
        }

    return {"success": False, "message": "Unknown action"}


# === Player Profile (global, not career-specific) ===

@router.get("/players/{player_id}/profile")
async def get_player_profile(
    player_id: int,
    career_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get complete player profile. If career_id provided, shows full attrs for own squad players."""
    result = await db.execute(
        text("""SELECT id, name, age, nationality, club, position, ca, pa, height, weight,
                left_foot, right_foot, price, wage, traits,
                corners, crossing, dribbling, finishing, first_touch, free_kick, heading,
                long_shots, long_throws, marking, passing, penalty_taking, tackling, technique,
                aggression, anticipation, bravery, composure, concentration, decisions,
                determination, flair, leadership, off_the_ball, positioning, teamwork, vision, work_rate,
                acceleration, agility, balance, jumping_reach, natural_fitness, pace, stamina, strength
                FROM players WHERE id = :pid"""),
        {"pid": player_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Player not found")

    # Check if player is in user's squad (show full attributes)
    is_own_player = False
    if career_id:
        sq_result = await db.execute(
            text("SELECT 1 FROM squad_players WHERE career_id = :cid AND player_id = :pid"),
            {"cid": career_id, "pid": player_id}
        )
        is_own_player = sq_result.fetchone() is not None

    base_info = {
        "id": row[0],
        "name": row[1],
        "age": row[2],
        "nationality": row[3],
        "club": row[4],
        "position": row[5],
        "height": row[8],
        "weight": row[9],
        "left_foot": row[10],
        "right_foot": row[11],
        "price": row[12],
        "wage": row[13],
        "traits": row[14],
    }

    if is_own_player:
        # Own player - show everything including CA/PA and all attributes
        base_info["ca"] = row[6]
        base_info["pa"] = row[7]
        base_info["attributes"] = {
            "corners": row[15], "crossing": row[16], "dribbling": row[17],
            "finishing": row[18], "first_touch": row[19], "free_kick": row[20],
            "heading": row[21], "long_shots": row[22], "long_throws": row[23],
            "marking": row[24], "passing": row[25], "penalty_taking": row[26],
            "tackling": row[27], "technique": row[28],
            "aggression": row[29], "anticipation": row[30], "bravery": row[31],
            "composure": row[32], "concentration": row[33], "decisions": row[34],
            "determination": row[35], "flair": row[36], "leadership": row[37],
            "off_the_ball": row[38], "positioning": row[39], "teamwork": row[40],
            "vision": row[41], "work_rate": row[42],
            "acceleration": row[43], "agility": row[44], "balance": row[45],
            "jumping_reach": row[46], "natural_fitness": row[47], "pace": row[48],
            "stamina": row[49], "strength": row[50],
        }
    else:
        # Not own player — check if we've scouted them. If yes, expose
        # the player's attributes BUT report CA/PA only as a star rating
        # (FM-style) — the precise number stays hidden so the user has
        # to make judgement calls on quality, not just sort by CA.
        scout_level = 0
        if career_id:
            try:
                sk_result = await db.execute(text(
                    "SELECT level FROM scout_knowledge "
                    "WHERE career_id = :cid AND player_id = :pid"
                ), {"cid": career_id, "pid": player_id})
                row_sk = sk_result.fetchone()
                if row_sk:
                    scout_level = int(row_sk[0] or 0)
            except Exception:
                scout_level = 0

        if scout_level >= 1:
            ca_real = row[6] or 100
            pa_real = abs(row[7] or 100)

            def _stars(value: int) -> float:
                """Round CA/PA to a half-star (0..5) FM-style."""
                v = max(0, min(200, value)) / 40.0
                return round(v * 2) / 2

            base_info["ca"] = None
            base_info["pa"] = None
            base_info["ca_stars"] = _stars(ca_real)
            base_info["pa_stars"] = _stars(pa_real)
            base_info["attributes"] = {
                "corners": row[15], "crossing": row[16], "dribbling": row[17],
                "finishing": row[18], "first_touch": row[19], "free_kick": row[20],
                "heading": row[21], "long_shots": row[22], "long_throws": row[23],
                "marking": row[24], "passing": row[25], "penalty_taking": row[26],
                "tackling": row[27], "technique": row[28],
                "aggression": row[29], "anticipation": row[30], "bravery": row[31],
                "composure": row[32], "concentration": row[33], "decisions": row[34],
                "determination": row[35], "flair": row[36], "leadership": row[37],
                "off_the_ball": row[38], "positioning": row[39], "teamwork": row[40],
                "vision": row[41], "work_rate": row[42],
                "acceleration": row[43], "agility": row[44], "balance": row[45],
                "jumping_reach": row[46], "natural_fitness": row[47], "pace": row[48],
                "stamina": row[49], "strength": row[50],
            }
            base_info["scouting_required"] = False
            base_info["scout_level"] = scout_level
        else:
            base_info["ca"] = None
            base_info["pa"] = None
            base_info["attributes"] = None
            base_info["scouting_required"] = True
            base_info["scout_level"] = 0

    return base_info


# === Helpers ===

async def _verify_career(career_id: int, user_id: int, db: AsyncSession):
    """Verify career exists and belongs to user (raw SQL for SQLite compat)."""
    result = await db.execute(
        text("SELECT id, user_id, club_id, budget, board_confidence FROM careers WHERE id = :cid"),
        {"cid": career_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[1] != user_id:
        raise HTTPException(403, "Not your career")
    # Return a simple namespace object
    class CareerRow:
        id = row[0]
        user_id = row[1]
        club_id = row[2]
        budget = row[3]
        board_confidence = row[4]
    return CareerRow()



@router.post("/careers/{career_id}/squad/{squad_player_id}/transfer-list")
async def toggle_transfer_listed(
    career_id: int,
    squad_player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flip ``is_transfer_listed`` on a squad_player row. Returns the new state.

    Body is ignored — this is a simple toggle. Use a different endpoint
    if you need to set the flag explicitly.
    """
    # Verify career ownership
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    # Read current flag
    cur = await db.execute(
        text(
            "SELECT is_transfer_listed FROM squad_players "
            "WHERE id = :sid AND career_id = :cid"
        ),
        {"sid": squad_player_id, "cid": career_id},
    )
    crow = cur.fetchone()
    if not crow:
        raise HTTPException(404, "Squad player not found")
    new_flag = 0 if crow[0] else 1
    await db.execute(
        text(
            "UPDATE squad_players SET is_transfer_listed = :v "
            "WHERE id = :sid AND career_id = :cid"
        ),
        {"v": new_flag, "sid": squad_player_id, "cid": career_id},
    )
    await db.commit()
    return {"success": True, "is_transfer_listed": bool(new_flag)}


@router.post("/careers/{career_id}/squad/{squad_player_id}/loan-list")
async def toggle_loan_listed(
    career_id: int,
    squad_player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flip ``is_loan_listed`` on a squad_player row."""
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    cur = await db.execute(
        text(
            "SELECT is_loan_listed FROM squad_players "
            "WHERE id = :sid AND career_id = :cid"
        ),
        {"sid": squad_player_id, "cid": career_id},
    )
    crow = cur.fetchone()
    if not crow:
        raise HTTPException(404, "Squad player not found")
    new_flag = 0 if crow[0] else 1
    await db.execute(
        text(
            "UPDATE squad_players SET is_loan_listed = :v "
            "WHERE id = :sid AND career_id = :cid"
        ),
        {"v": new_flag, "sid": squad_player_id, "cid": career_id},
    )
    await db.commit()
    return {"success": True, "is_loan_listed": bool(new_flag)}


# ─── Individual training role + focus + intensity ───────────────────────


class IndividualTrainingRequest(BaseModel):
    training_role: Optional[str] = None        # role code from training_roles.py
    individual_focus: Optional[str] = None     # attribute name
    individual_intensity: Optional[str] = None # low|normal|high


@router.post("/careers/{career_id}/squad/{squad_player_id}/individual-training")
async def set_individual_training(
    career_id: int,
    squad_player_id: int,
    body: IndividualTrainingRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id=:c"), {"c": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    sets = []
    params: Dict[str, Any] = {"sid": squad_player_id, "c": career_id}
    if body.training_role is not None:
        sets.append("training_role = :tr"); params["tr"] = body.training_role
    if body.individual_focus is not None:
        sets.append("individual_focus = :fo"); params["fo"] = body.individual_focus
    if body.individual_intensity is not None:
        sets.append("individual_intensity = :it"); params["it"] = body.individual_intensity
    if not sets:
        return {"success": False, "message": "Nothing to update"}

    await db.execute(
        text(
            f"UPDATE squad_players SET {', '.join(sets)} "
            "WHERE id = :sid AND career_id = :c"
        ),
        params,
    )
    await db.commit()
    return {"success": True}


@router.get("/careers/{career_id}/squad/{squad_player_id}/individual-training")
async def get_individual_training(
    career_id: int,
    squad_player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current training_role / focus / intensity for one squad row."""
    r = await db.execute(text(
        "SELECT training_role, individual_focus, individual_intensity "
        "FROM squad_players WHERE id=:sid AND career_id=:c"
    ), {"sid": squad_player_id, "c": career_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Squad player not found")
    return {
        "training_role": row[0],
        "individual_focus": row[1],
        "individual_intensity": row[2] or "normal",
    }
