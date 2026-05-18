"""
Medical API Endpoints (Task 14.4)

GET /api/careers/{career_id}/injuries - Injury list screen (Requirement 11.4)

Returns the current injury list for a career using MedicalService, which
reads from the canonical `injuries` table populated by the match-day
injury simulation. Each row contains the player, injury type, severity,
status, and estimated return date so the frontend can render the
medical-centre injury list screen.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.medical_service import MedicalService
from app.services.career_service import CareerService

router = APIRouter(tags=["medical"])


async def _verify_career(career_id: int, user_id: int, db: AsyncSession):
    """Ensure the career exists and belongs to the calling user."""
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user_id:
        raise HTTPException(403, "Not your career")
    return career


@router.get("/careers/{career_id}/injuries")
async def get_injury_list(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the active injury list for a career.

    Returns ACTIVE and RECOVERING injuries with player name, position,
    injury type, severity, status, and expected return date. Implements
    Requirement 11.4 (injury list screen).
    """
    await _verify_career(career_id, user.id, db)
    service = MedicalService(db)
    injuries = await service.get_injury_list(career_id)
    return {
        "career_id": career_id,
        "count": len(injuries),
        "injuries": injuries,
    }
