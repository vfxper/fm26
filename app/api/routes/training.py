"""
Training API Endpoints (Task 27)
GET /api/careers/{career_id}/training/schedule - Get training schedule
PUT /api/careers/{career_id}/training/{player_id} - Assign training focus
PUT /api/careers/{career_id}/training/intensity - Set training intensity
GET /api/careers/{career_id}/training/{player_id}/history - Get attribute history
GET /api/careers/{career_id}/training/injury-risk - Get squad injury risk report
GET /api/careers/{career_id}/training/youth - Get youth development report
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.training_service import TrainingService
from app.services.career_service import CareerService

router = APIRouter(prefix="/careers/{career_id}/training", tags=["training"])


class AssignFocusRequest(BaseModel):
    focus: str = Field(..., description="Training focus: general, fitness, tactics, attacking, defending, technical, shooting, goalkeeping")


class IntensityRequest(BaseModel):
    intensity: str = Field(..., description="light, normal, heavy")


@router.get("/schedule")
async def get_schedule(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current training schedule for all players."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)
    schedule = await service.get_training_schedule_view(career_id)
    return schedule


@router.put("/{player_id}")
async def assign_focus(
    career_id: int,
    player_id: int,
    request: AssignFocusRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign training focus to a player."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)

    try:
        result = await service.assign_training_focus(career_id, player_id, request.focus)
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@router.put("/intensity")
async def set_intensity(
    career_id: int,
    request: IntensityRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set team training intensity."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)

    try:
        result = await service.set_training_intensity(career_id, request.intensity)
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{player_id}/history")
async def get_attribute_history(
    career_id: int,
    player_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get player attribute progression history."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)

    try:
        history = await service.get_player_attribute_history_summary(career_id, player_id)
        return history
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/injury-risk")
async def get_injury_risk(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get injury risk report for entire squad."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)

    try:
        report = await service.get_squad_injury_risk_report(career_id)
        return report
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/youth")
async def get_youth_report(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get youth player development report."""
    await _verify_career(career_id, user.id, db)
    service = TrainingService(db)

    try:
        report = await service.get_youth_player_development_report(career_id)
        return report
    except Exception as e:
        raise HTTPException(400, str(e))


async def _verify_career(career_id, user_id, db):
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user_id:
        raise HTTPException(403, "Not your career")
    return career
