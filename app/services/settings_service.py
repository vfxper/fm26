"""
Settings Service - User settings management

Handles user preferences including language, match speed, sound,
notifications, and theme settings.
"""

import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User


# Default settings applied to all new users
DEFAULT_SETTINGS = {
    "language": "en",  # en, ru, es, de, fr
    "match_speed": 2,  # 1, 2, 4, 10
    "sound_effects": True,
    "background_music": True,
    "notifications_match": True,
    "notifications_transfer": True,
    "notifications_training": True,
    "notifications_contract": True,
    "theme": "auto",  # auto, dark, light
}

# Valid values for constrained settings
VALID_LANGUAGES = {"en", "ru", "es", "de", "fr"}
VALID_MATCH_SPEEDS = {1, 2, 4, 10}
VALID_THEMES = {"auto", "dark", "light"}

# Boolean setting keys
BOOLEAN_SETTINGS = {
    "sound_effects",
    "background_music",
    "notifications_match",
    "notifications_transfer",
    "notifications_training",
    "notifications_contract",
}


class SettingsValidationError(Exception):
    """Raised when settings values are invalid"""
    pass


def validate_settings(settings: dict) -> dict:
    """
    Validate settings values against allowed options.
    
    Args:
        settings: Dictionary of settings to validate
        
    Returns:
        dict: Validated settings (only valid keys/values)
        
    Raises:
        SettingsValidationError: If any value is invalid
    """
    validated = {}
    
    for key, value in settings.items():
        if key not in DEFAULT_SETTINGS:
            raise SettingsValidationError(f"Unknown setting: {key}")
        
        if key == "language":
            if value not in VALID_LANGUAGES:
                raise SettingsValidationError(
                    f"Invalid language '{value}'. Must be one of: {', '.join(sorted(VALID_LANGUAGES))}"
                )
        elif key == "match_speed":
            if value not in VALID_MATCH_SPEEDS:
                raise SettingsValidationError(
                    f"Invalid match_speed '{value}'. Must be one of: {sorted(VALID_MATCH_SPEEDS)}"
                )
        elif key == "theme":
            if value not in VALID_THEMES:
                raise SettingsValidationError(
                    f"Invalid theme '{value}'. Must be one of: {', '.join(sorted(VALID_THEMES))}"
                )
        elif key in BOOLEAN_SETTINGS:
            if not isinstance(value, bool):
                raise SettingsValidationError(
                    f"Setting '{key}' must be a boolean (true/false)"
                )
        
        validated[key] = value
    
    return validated


async def get_user_settings(db: AsyncSession, user_id: int) -> dict:
    """
    Get all settings for a user, with defaults for any missing values.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        dict: Complete settings dictionary with defaults applied
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        return dict(DEFAULT_SETTINGS)
    
    # Parse stored settings or use empty dict
    stored_settings = {}
    if user.settings_json:
        try:
            stored_settings = json.loads(user.settings_json)
        except (json.JSONDecodeError, TypeError):
            stored_settings = {}
    
    # Merge with defaults (stored values override defaults)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored_settings)
    
    return merged


async def update_settings(db: AsyncSession, user_id: int, settings: dict) -> dict:
    """
    Update specific settings for a user. Only provided keys are updated.
    
    Args:
        db: Database session
        user_id: User ID
        settings: Dictionary of settings to update
        
    Returns:
        dict: Complete updated settings
        
    Raises:
        SettingsValidationError: If any value is invalid
        ValueError: If user not found
    """
    # Validate input
    validated = validate_settings(settings)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise ValueError(f"User with id {user_id} not found")
    
    # Load existing settings
    current_settings = {}
    if user.settings_json:
        try:
            current_settings = json.loads(user.settings_json)
        except (json.JSONDecodeError, TypeError):
            current_settings = {}
    
    # Merge new settings
    current_settings.update(validated)
    
    # Persist
    user.settings_json = json.dumps(current_settings)
    await db.flush()
    
    # Return complete settings with defaults
    merged = dict(DEFAULT_SETTINGS)
    merged.update(current_settings)
    return merged


async def reset_settings(db: AsyncSession, user_id: int) -> dict:
    """
    Reset all settings to defaults for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        dict: Default settings
        
    Raises:
        ValueError: If user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise ValueError(f"User with id {user_id} not found")
    
    # Clear stored settings (will fall back to defaults)
    user.settings_json = None
    await db.flush()
    
    return dict(DEFAULT_SETTINGS)
