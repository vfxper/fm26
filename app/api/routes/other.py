"""
Other API Endpoints (Task 29)
Finances, Infrastructure, Staff, Scouting, Media, Competitions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.career_service import CareerService

router = APIRouter(tags=["other"])


# === FINANCES ===

@router.get("/careers/{career_id}/finances")
async def get_finances(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a thin financial summary the dashboard tile can render.

    This is intentionally minimal — the full FinanceService would
    require club_id/season parameters and a populated transactions
    table. The home tile only needs ``balance``, ``transfer_budget``
    and weekly ``wage_budget``, which we can pull straight from the
    careers + CLUBS data we already have.
    """
    from sqlalchemy import text as _t
    car = await db.execute(_t(
        "SELECT user_id, club_id, budget FROM careers WHERE id = :c"
    ), {"c": career_id})
    row = car.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        from fastapi import HTTPException
        raise HTTPException(403, "Not your career")

    club_id = row[1]
    transfer_budget = int(row[2] or 0)

    # Look up the weekly wage budget from the static CLUBS list.
    wage_budget = 0
    try:
        from app.data.club_budgets import CLUBS, get_wage_budget
        if club_id and 1 <= club_id <= len(CLUBS):
            club_name = CLUBS[club_id - 1][0]
            wage_budget = int(get_wage_budget(club_name) or 0)
    except Exception:
        pass

    # Current weekly wage outlay (sum of squad_players.wage).
    cur_wage_bill = 0
    try:
        r = await db.execute(_t(
            "SELECT COALESCE(SUM(wage), 0) FROM squad_players WHERE career_id = :c"
        ), {"c": career_id})
        cur_wage_bill = int(r.scalar() or 0)
    except Exception:
        pass

    return {
        "career_id": career_id,
        "club_id": club_id,
        "balance": transfer_budget,
        "transfer_budget": transfer_budget,
        "wage_budget": wage_budget,
        "weekly_wage_budget": wage_budget,
        "current_wage_bill": cur_wage_bill,
    }


class BudgetRequestModel(BaseModel):
    amount: int = Field(..., gt=0)
    reason: str = Field(default="transfers")


@router.post("/careers/{career_id}/finances/budget-request")
async def request_budget(
    career_id: int,
    request: BudgetRequestModel,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request budget increase from board."""
    career = await _verify(career_id, user.id, db)
    from app.services.finance_service import FinanceService
    service = FinanceService(db)
    result = await service.request_budget_increase(career_id, request.amount, request.reason)
    await db.commit()
    return result


# === INFRASTRUCTURE ===

@router.get("/careers/{career_id}/infrastructure")
async def get_infrastructure(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get infrastructure levels."""
    career = await _verify(career_id, user.id, db)
    from app.services.infrastructure_service import InfrastructureService
    service = InfrastructureService(db)
    levels = await service.get_infrastructure_levels(career_id)
    return levels


class UpgradeRequest(BaseModel):
    category: str = Field(..., description="stadium, training, academy, medical, scouting")


@router.post("/careers/{career_id}/infrastructure/upgrade")
async def request_upgrade(
    career_id: int,
    request: UpgradeRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request infrastructure upgrade."""
    career = await _verify(career_id, user.id, db)
    from app.services.infrastructure_service import InfrastructureService
    service = InfrastructureService(db)
    result = await service.request_upgrade(career_id, request.category)
    await db.commit()
    return result


# === STAFF ===

@router.get("/careers/{career_id}/staff")
async def get_staff(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all staff members."""
    career = await _verify(career_id, user.id, db)
    from app.services.staff_service import StaffService
    service = StaffService(db)
    staff = await service.get_all_staff(career_id)
    return {"staff": staff}


class HireStaffRequest(BaseModel):
    role: str = Field(..., description="assistant, fitness_coach, gk_coach, scout, physio, analyst, youth_coach, chief_scout")
    name: Optional[str] = None


@router.post("/careers/{career_id}/staff/hire")
async def hire_staff(
    career_id: int,
    request: HireStaffRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hire a new staff member."""
    career = await _verify(career_id, user.id, db)
    from app.services.staff_service import StaffService
    service = StaffService(db)
    result = await service.hire_staff(career_id, request.role, request.name)
    await db.commit()
    return result


@router.delete("/careers/{career_id}/staff/{staff_id}")
async def fire_staff(
    career_id: int,
    staff_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fire a staff member."""
    career = await _verify(career_id, user.id, db)
    from app.services.staff_service import StaffService
    service = StaffService(db)
    result = await service.fire_staff(career_id, staff_id)
    await db.commit()
    return result


# === SCOUTING ===

@router.get("/careers/{career_id}/scouting")
async def get_scouting(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scouting assignments and reports."""
    career = await _verify(career_id, user.id, db)
    from app.services.scouting_service import ScoutingService
    service = ScoutingService(db)
    assignments = await service.get_assignments(career_id)
    return assignments


class ScoutAssignRequest(BaseModel):
    scout_id: int
    target_type: str = Field(..., description="player, region, competition")
    target_id: Optional[int] = None
    target_name: Optional[str] = None


@router.post("/careers/{career_id}/scouting/assign")
async def assign_scout(
    career_id: int,
    request: ScoutAssignRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign scout to a player/region/competition."""
    career = await _verify(career_id, user.id, db)
    from app.services.scouting_service import ScoutingService
    service = ScoutingService(db)
    result = await service.assign_scout(
        career_id, request.scout_id, request.target_type,
        request.target_id, request.target_name
    )
    await db.commit()
    return result


# === MEDIA ===

@router.get("/careers/{career_id}/media/news")
async def get_news(
    career_id: int,
    page: int = Query(1, ge=1),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get news feed."""
    career = await _verify(career_id, user.id, db)
    from app.services.media_service import MediaService
    service = MediaService(db)
    news = await service.get_news_feed(career_id, page=page)
    return news


class PressConferenceResponse(BaseModel):
    choice_index: int = Field(..., ge=0, le=4)


@router.post("/careers/{career_id}/media/press-conference")
async def respond_press(
    career_id: int,
    request: PressConferenceResponse,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Respond to press conference question."""
    career = await _verify(career_id, user.id, db)
    from app.services.media_service import MediaService
    service = MediaService(db)
    result = await service.respond_to_press(career_id, request.choice_index)
    await db.commit()
    return result


# === COMPETITIONS ===

@router.get("/competitions/{competition_id}/standings")
async def get_standings(
    competition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get league table / standings."""
    from app.services.competition_service import CompetitionService
    service = CompetitionService(db)
    standings = await service.get_standings(competition_id)
    return standings


@router.get("/competitions/{competition_id}/fixtures")
async def get_competition_fixtures(
    competition_id: int,
    week: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get fixtures for a competition."""
    from app.services.competition_service import CompetitionService
    service = CompetitionService(db)
    fixtures = await service.get_fixtures(competition_id, week=week)
    return fixtures


# === Helper ===

async def _verify(career_id, user_id, db):
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user_id:
        raise HTTPException(403, "Not your career")
    return career
