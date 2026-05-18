"""
Tactics API Endpoints (Task 25)
GET /api/careers/{career_id}/tactics - Get all tactic presets
POST /api/careers/{career_id}/tactics - Create tactic preset
PUT /api/careers/{career_id}/tactics/{tactic_id} - Update tactic
DELETE /api/careers/{career_id}/tactics/{tactic_id} - Delete tactic
POST /api/careers/{career_id}/tactics/{tactic_id}/activate - Set active tactic
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.tactics_service import TacticsService, TacticPreset
from app.services.career_service import CareerService

router = APIRouter(prefix="/careers/{career_id}/tactics", tags=["tactics"])


class CreateTacticRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    formation: str = Field(default="4-4-2")
    mentality: str = Field(default="balanced")
    pressing: str = Field(default="medium")
    defensive_line: str = Field(default="standard")
    width: str = Field(default="standard")
    tempo: str = Field(default="normal")


class UpdateTacticRequest(BaseModel):
    name: Optional[str] = None
    formation: Optional[str] = None
    mentality: Optional[str] = None
    pressing: Optional[str] = None
    defensive_line: Optional[str] = None
    width: Optional[str] = None
    tempo: Optional[str] = None
    player_positions: Optional[List[Dict[str, Any]]] = None
    player_roles: Optional[List[Dict[str, Any]]] = None


@router.get("")
async def get_tactics(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all tactic presets for this career."""
    career = await _verify_career(career_id, user.id, db)
    service = TacticsService()

    # Load presets from career data
    presets_data = career.tactics_presets or []
    if isinstance(presets_data, str):
        import json
        presets_data = json.loads(presets_data)

    presets = service.deserialize_presets(presets_data) if presets_data else []

    # If no presets, create default
    if not presets:
        default = service.create_preset(presets, "Default 4-4-2", "4-4-2")
        presets_data = service.serialize_presets(presets)
        career.tactics_presets = presets_data
        await db.commit()

    return {
        "presets": service.serialize_presets(presets),
        "active_index": career.active_tactic_index or 0,
        "available_formations": service.get_formation_names(),
    }


@router.post("")
async def create_tactic(
    career_id: int,
    request: CreateTacticRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tactic preset (max 5)."""
    career = await _verify_career(career_id, user.id, db)
    service = TacticsService()

    presets_data = career.tactics_presets or []
    if isinstance(presets_data, str):
        import json
        presets_data = json.loads(presets_data)

    presets = service.deserialize_presets(presets_data) if presets_data else []

    if len(presets) >= 5:
        raise HTTPException(400, "Maximum 5 tactic presets allowed")

    new_preset = service.create_preset(presets, request.name, request.formation)
    career.tactics_presets = service.serialize_presets(presets)
    await db.commit()

    return {"success": True, "preset": new_preset.to_dict(), "total_presets": len(presets)}


@router.put("/{tactic_id}")
async def update_tactic(
    career_id: int,
    tactic_id: int,
    request: UpdateTacticRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a tactic preset."""
    career = await _verify_career(career_id, user.id, db)
    service = TacticsService()

    presets_data = career.tactics_presets or []
    if isinstance(presets_data, str):
        import json
        presets_data = json.loads(presets_data)

    presets = service.deserialize_presets(presets_data) if presets_data else []

    if tactic_id < 0 or tactic_id >= len(presets):
        raise HTTPException(404, "Tactic preset not found")

    preset = presets[tactic_id]

    if request.name:
        service.rename_preset(preset, request.name)
    if request.formation:
        formation = service.get_formation(request.formation)
        if formation:
            preset.formation = formation
    if request.mentality:
        preset.mentality = request.mentality
    if request.pressing:
        preset.pressing = request.pressing
    if request.defensive_line:
        preset.defensive_line = request.defensive_line
    if request.width:
        preset.width = request.width
    if request.tempo:
        preset.tempo = request.tempo

    career.tactics_presets = service.serialize_presets(presets)
    await db.commit()

    return {"success": True, "preset": preset.to_dict()}


@router.delete("/{tactic_id}")
async def delete_tactic(
    career_id: int,
    tactic_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tactic preset."""
    career = await _verify_career(career_id, user.id, db)
    service = TacticsService()

    presets_data = career.tactics_presets or []
    if isinstance(presets_data, str):
        import json
        presets_data = json.loads(presets_data)

    presets = service.deserialize_presets(presets_data) if presets_data else []

    if tactic_id < 0 or tactic_id >= len(presets):
        raise HTTPException(404, "Tactic preset not found")
    if len(presets) <= 1:
        raise HTTPException(400, "Cannot delete last tactic preset")

    service.delete_preset(presets, tactic_id)
    career.tactics_presets = service.serialize_presets(presets)
    await db.commit()

    return {"success": True, "remaining": len(presets)}


@router.post("/{tactic_id}/activate")
async def activate_tactic(
    career_id: int,
    tactic_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set active tactic for next match."""
    career = await _verify_career(career_id, user.id, db)

    presets_data = career.tactics_presets or []
    if isinstance(presets_data, str):
        import json
        presets_data = json.loads(presets_data)

    if tactic_id < 0 or tactic_id >= len(presets_data):
        raise HTTPException(404, "Tactic preset not found")

    career.active_tactic_index = tactic_id
    await db.commit()

    return {"success": True, "active_index": tactic_id}


async def _verify_career(career_id, user_id, db):
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user_id:
        raise HTTPException(403, "Not your career")
    return career
