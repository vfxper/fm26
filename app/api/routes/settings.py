"""
Settings API Routes

Endpoints for user settings management.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.services.settings_service import (
    get_user_settings,
    update_settings,
    reset_settings,
    SettingsValidationError,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Request/Response Models ---

class SettingsResponse(BaseModel):
    language: str
    match_speed: int
    sound_effects: bool
    background_music: bool
    notifications_match: bool
    notifications_transfer: bool
    notifications_training: bool
    notifications_contract: bool
    theme: str


class UpdateSettingsRequest(BaseModel):
    language: Optional[str] = None
    match_speed: Optional[int] = None
    sound_effects: Optional[bool] = None
    background_music: Optional[bool] = None
    notifications_match: Optional[bool] = None
    notifications_transfer: Optional[bool] = None
    notifications_training: Optional[bool] = None
    notifications_contract: Optional[bool] = None
    theme: Optional[str] = None


# --- Endpoints ---

@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current user's settings."""
    settings = await get_user_settings(db, current_user.id)
    return SettingsResponse(**settings)


@router.put("", response_model=SettingsResponse)
async def update_user_settings(
    request: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update user settings. Only provided fields are updated."""
    # Filter out None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if not updates:
        # No changes, return current settings
        settings = await get_user_settings(db, current_user.id)
        return SettingsResponse(**settings)
    
    try:
        settings = await update_settings(db, current_user.id, updates)
        return SettingsResponse(**settings)
    except SettingsValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reset", response_model=SettingsResponse)
async def reset_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Reset all settings to defaults."""
    try:
        settings = await reset_settings(db, current_user.id)
        return SettingsResponse(**settings)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
