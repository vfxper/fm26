"""
Scouting Centre API Endpoints

GET  /api/careers/{id}/scouting/centre - Get scouting centre overview
POST /api/careers/{id}/scouting/assign - Create assignment
GET  /api/careers/{id}/scouting/reports - Get all reports (with filters)
POST /api/careers/{id}/scouting/reports/{report_id}/shortlist - Add to shortlist
GET  /api/careers/{id}/scouting/shortlist - Get shortlist
GET  /api/careers/{id}/scouting/knowledge-map - Get knowledge map
GET  /api/careers/{id}/scouting/budget - Get budget status
POST /api/careers/{id}/scouting/budget/request - Request budget increase
GET  /api/careers/{id}/scouting/scouts - Get all scouts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.scouting_centre import ScoutingCentre

router = APIRouter(prefix="/careers/{career_id}/scouting", tags=["scouting"])

# In-memory scouting centres per career (for local dev)
# In production this would be serialized to DB
_centres: dict = {}


def _get_centre(career_id: int) -> ScoutingCentre:
    if career_id not in _centres:
        centre = ScoutingCentre()
        # Add default scouts (all start as idle)
        centre.hire_scout("Carlos Mendes", judging=14, potential=13, 
                         regions={"Spain": 80, "Portugal": 70, "Brazil": 50}, wage=6000)
        centre.hire_scout("Hans Mueller", judging=12, potential=15,
                         regions={"Germany": 85, "Austria": 60, "Netherlands": 40}, wage=5000)
        centre.hire_scout("Marco Rossi", judging=13, potential=11,
                         regions={"Italy": 75, "France": 45, "Argentina": 30}, wage=5500)
        
        # Try to set realistic scouting budget based on club
        try:
            from app.data.club_budgets import CLUBS
            # We'll set it when we know the club - for now use default
        except Exception:
            pass
        
        _centres[career_id] = centre
    else:
        # Fix: ensure scouts without active assignments are idle
        centre = _centres[career_id]
        for scout in centre.scouts:
            active = [a for a in centre.assignments if a.scout_id == scout.id and a.status == "active"]
            if not active:
                scout.status = "idle"
                scout.current_assignment = None
    return _centres[career_id]


class AssignmentRequest(BaseModel):
    scout_id: int
    assignment_type: str = Field(..., description="player, region, competition")
    target: str = Field(..., description="Country name, player ID, or competition name")
    position_filter: Optional[str] = None
    age_min: Optional[int] = Field(None, ge=15, le=45)
    age_max: Optional[int] = Field(None, ge=15, le=45)
    max_price: Optional[int] = None
    duration_weeks: int = Field(default=4, ge=1, le=12)
    priority: str = Field(default="normal", description="low, normal, high, urgent")


class BudgetRequest(BaseModel):
    amount: float = Field(..., gt=0)


@router.get("/centre")
async def get_scouting_centre(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full scouting centre overview."""
    centre = _get_centre(career_id)
    
    return {
        "scouts": [
            {
                "id": s.id, "name": s.name, "status": s.status,
                "judging_ability": s.judging_ability, "judging_potential": s.judging_potential,
                "wage": s.wage, "current_assignment": s.current_assignment,
                "top_regions": sorted(s.region_knowledge.items(), key=lambda x: -x[1])[:5],
            }
            for s in centre.scouts
        ],
        "active_assignments": [
            {
                "id": a.id, "scout_id": a.scout_id, "type": a.assignment_type,
                "target": a.target, "weeks_elapsed": a.weeks_elapsed,
                "duration_weeks": a.duration_weeks, "priority": a.priority,
                "reports_generated": a.reports_generated, "status": a.status,
            }
            for a in centre.assignments if a.status == "active"
        ],
        "recent_reports": [
            {
                "id": r.id, "player_name": r.player_name, "player_id": r.player_id,
                "stars": r.current_ability_stars, "potential_stars": r.potential_stars,
                "recommendation": r.recommendation, "status": r.status,
                "summary": r.summary_text[:200], "created_at": r.created_at,
                "revealed_attributes": r.revealed_attributes,
            }
            for r in sorted(centre.reports, key=lambda x: x.created_at or "", reverse=True)[:10]
        ],
        "budget": centre.get_budget_status(),
        "shortlist_count": len(centre.shortlist),
    }


@router.post("/assign")
async def create_assignment(
    career_id: int,
    request: AssignmentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scouting assignment."""
    centre = _get_centre(career_id)
    
    assignment = centre.create_assignment(
        scout_id=request.scout_id,
        assignment_type=request.assignment_type,
        target=request.target,
        position_filter=request.position_filter,
        age_min=request.age_min,
        age_max=request.age_max,
        max_price=request.max_price,
        duration_weeks=request.duration_weeks,
        priority=request.priority,
    )
    
    if not assignment:
        raise HTTPException(400, "Cannot create assignment (scout busy or over budget)")
    
    return {
        "success": True,
        "assignment_id": assignment.id,
        "scout_id": assignment.scout_id,
        "target": assignment.target,
        "duration_weeks": assignment.duration_weeks,
    }


@router.get("/reports")
async def get_reports(
    career_id: int,
    status: Optional[str] = Query(None, description="new, shortlisted, rejected"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all scouting reports with optional status filter."""
    centre = _get_centre(career_id)
    
    reports = centre.reports
    if status:
        reports = [r for r in reports if r.status == status]
    
    return {
        "reports": [
            {
                "id": r.id, "player_id": r.player_id, "player_name": r.player_name,
                "scout_name": r.scout_name,
                "current_ability_stars": r.current_ability_stars,
                "potential_stars": r.potential_stars,
                "recommendation": r.recommendation,
                "strengths": r.strengths,
                "weaknesses": r.weaknesses,
                "summary_text": r.summary_text,
                "accuracy_pct": r.accuracy_pct,
                "revealed_attributes": r.revealed_attributes,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.post("/reports/{report_id}/shortlist")
async def shortlist_report(
    career_id: int,
    report_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add player from report to shortlist."""
    centre = _get_centre(career_id)
    
    report = next((r for r in centre.reports if r.id == report_id), None)
    if not report:
        raise HTTPException(404, "Report not found")
    
    report.status = "shortlisted"
    success = centre.add_to_shortlist(report.player_id)
    
    return {"success": success, "shortlist_count": len(centre.shortlist)}


@router.get("/shortlist")
async def get_shortlist(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get shortlisted players."""
    centre = _get_centre(career_id)
    
    # Get player details from DB
    players = []
    for pid in centre.shortlist:
        try:
            result = await db.execute(
                text("SELECT id, name, age, position, nationality, club, ca, pa FROM players WHERE id = :pid"),
                {"pid": pid}
            )
            row = result.fetchone()
            if row:
                players.append({
                    "id": row[0], "name": row[1], "age": row[2],
                    "position": row[3], "nationality": row[4],
                    "club": row[5], "ca": row[6], "pa": row[7],
                })
        except Exception:
            pass
    
    return {"shortlist": players, "count": len(players), "max": 50}


@router.get("/knowledge-map")
async def get_knowledge_map(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge map (country -> knowledge level)."""
    centre = _get_centre(career_id)
    knowledge = centre.get_knowledge_map()
    
    return {
        "knowledge": knowledge,
        "total_countries": len(knowledge),
        "well_known": [k for k, v in knowledge.items() if v >= 60],
        "partially_known": [k for k, v in knowledge.items() if 20 <= v < 60],
        "unknown": [k for k, v in knowledge.items() if v < 20],
    }


@router.get("/budget")
async def get_scouting_budget(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scouting budget status."""
    centre = _get_centre(career_id)
    return centre.get_budget_status()


@router.post("/budget/request")
async def request_budget_increase(
    career_id: int,
    request: BudgetRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request scouting budget increase from board."""
    centre = _get_centre(career_id)
    result = centre.request_budget_increase(request.amount, board_confidence=50)
    return result


@router.get("/scouts")
async def get_scouts(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all scouts with their details."""
    centre = _get_centre(career_id)
    return {
        "scouts": [
            {
                "id": s.id, "name": s.name, "status": s.status,
                "judging_ability": s.judging_ability,
                "judging_potential": s.judging_potential,
                "tactical_knowledge": s.tactical_knowledge,
                "adaptability": s.adaptability,
                "determination": s.determination,
                "wage": s.wage,
                "region_knowledge": s.region_knowledge,
                "current_assignment": s.current_assignment,
            }
            for s in centre.scouts
        ]
    }


@router.post("/instant-report/{player_id}")
async def instant_scout_report(
    career_id: int,
    player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get instant scout report on a specific player. Once paid for in
    a career, the report is cached and re-served free."""
    centre = _get_centre(career_id)

    # Cache check — if the player has already been scouted in this career,
    # serve a free re-render of the existing report.
    try:
        cached = await db.execute(text(
            "SELECT 1 FROM scout_knowledge WHERE career_id=:c AND player_id=:p AND level >= 2 LIMIT 1"
        ), {"c": career_id, "p": player_id})
        already = cached.fetchone() is not None
    except Exception:
        already = False

    cost = 0 if already else 20000
    if cost and centre.budget_spent + cost > centre.scouting_budget:
        raise HTTPException(400, "Insufficient scouting budget for instant report")
    
    # Get player from DB
    result = await db.execute(
        text("""SELECT id, name, age, position, nationality, club, ca, pa, 
                pace, dribbling, passing, finishing, tackling, heading, vision, 
                strength, composure, stamina, concentration, decisions, work_rate, marking, wage
                FROM players WHERE id = :pid"""),
        {"pid": player_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Player not found")
    
    player = {
        "id": row[0], "name": row[1], "age": row[2], "position": row[3],
        "nationality": row[4], "club": row[5], "ca": row[6], "pa": row[7],
        "pace": row[8], "dribbling": row[9], "passing": row[10], "finishing": row[11],
        "tackling": row[12], "heading": row[13], "vision": row[14], "strength": row[15],
        "composure": row[16], "stamina": row[17], "concentration": row[18],
        "decisions": row[19], "work_rate": row[20], "marking": row[21], "wage": row[22],
    }
    
    # Use best available scout
    best_scout = max(centre.scouts, key=lambda s: s.judging_ability) if centre.scouts else None
    if not best_scout:
        raise HTTPException(400, "No scouts available")
    
    # Generate instant report (higher accuracy for instant)
    from app.services.scouting_centre import ScoutAssignment
    fake_assignment = ScoutAssignment(id=0, scout_id=best_scout.id, assignment_type="player", target=str(player_id))
    report = centre._generate_report(best_scout, fake_assignment, player)
    centre.reports.append(report)
    centre.budget_spent += cost

    # Mark the player as fully scouted so future opens are free.
    try:
        on_date_row = await db.execute(text("SELECT game_date FROM careers WHERE id=:c"), {"c": career_id})
        on_date = on_date_row.scalar() or "2025-07-01"
        ex = await db.execute(text(
            "SELECT level FROM scout_knowledge WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": player_id})
        existing = ex.scalar()
        if existing is None:
            await db.execute(text(
                "INSERT INTO scout_knowledge (career_id, player_id, level, last_seen_date) "
                "VALUES (:c, :p, 2, :d)"
            ), {"c": career_id, "p": player_id, "d": on_date})
        elif existing < 2:
            await db.execute(text(
                "UPDATE scout_knowledge SET level=2, last_seen_date=:d "
                "WHERE career_id=:c AND player_id=:p"
            ), {"c": career_id, "p": player_id, "d": on_date})
        await db.commit()
    except Exception:
        pass
    
    return {
        "success": True,
        "cost": cost,
        "report": {
            "id": report.id,
            "player_name": report.player_name,
            "player_id": report.player_id,
            # ── Make sure the UI never shows "?·—" again. These come
            # straight from the players row, regardless of what the
            # report's revealed_attributes contains.
            "age": player["age"],
            "position": player["position"],
            "club": player["club"],
            "nationality": player["nationality"],
            "wage": player["wage"],
            # CA / PA are NEVER exposed as exact numbers — only as star
            # ratings (0-5 with 0.5 steps) that the scout report
            # already calculated.
            "ca": None,
            "pa": None,
            "ca_stars": report.current_ability_stars,
            "pa_stars": report.potential_stars,
            "current_ability_stars": report.current_ability_stars,
            "potential_stars": report.potential_stars,
            "recommendation": report.recommendation,
            "strengths": report.strengths,
            "weaknesses": report.weaknesses,
            "summary_text": report.summary_text,
            "revealed_attributes": report.revealed_attributes,
            "accuracy_pct": report.accuracy_pct,
        }
    }
