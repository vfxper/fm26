"""
Tests for Settings Service
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.settings_service import (
    DEFAULT_SETTINGS,
    validate_settings,
    get_user_settings,
    update_settings,
    reset_settings,
    SettingsValidationError,
    VALID_LANGUAGES,
    VALID_MATCH_SPEEDS,
    VALID_THEMES,
)


class TestValidateSettings:
    """Tests for settings validation"""

    def test_valid_language(self):
        for lang in VALID_LANGUAGES:
            result = validate_settings({"language": lang})
            assert result == {"language": lang}

    def test_invalid_language(self):
        with pytest.raises(SettingsValidationError, match="Invalid language"):
            validate_settings({"language": "xx"})

    def test_valid_match_speed(self):
        for speed in VALID_MATCH_SPEEDS:
            result = validate_settings({"match_speed": speed})
            assert result == {"match_speed": speed}

    def test_invalid_match_speed(self):
        with pytest.raises(SettingsValidationError, match="Invalid match_speed"):
            validate_settings({"match_speed": 3})

    def test_valid_theme(self):
        for theme in VALID_THEMES:
            result = validate_settings({"theme": theme})
            assert result == {"theme": theme}

    def test_invalid_theme(self):
        with pytest.raises(SettingsValidationError, match="Invalid theme"):
            validate_settings({"theme": "neon"})

    def test_valid_boolean_settings(self):
        result = validate_settings({"sound_effects": False, "background_music": True})
        assert result == {"sound_effects": False, "background_music": True}

    def test_invalid_boolean_setting(self):
        with pytest.raises(SettingsValidationError, match="must be a boolean"):
            validate_settings({"sound_effects": "yes"})

    def test_unknown_setting_key(self):
        with pytest.raises(SettingsValidationError, match="Unknown setting"):
            validate_settings({"unknown_key": "value"})

    def test_multiple_valid_settings(self):
        settings = {
            "language": "ru",
            "match_speed": 4,
            "theme": "dark",
            "sound_effects": False,
        }
        result = validate_settings(settings)
        assert result == settings

    def test_empty_settings(self):
        result = validate_settings({})
        assert result == {}


class TestGetUserSettings:
    """Tests for get_user_settings"""

    @pytest.mark.asyncio
    async def test_returns_defaults_when_user_not_found(self):
        """When user doesn't exist, return defaults"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await get_user_settings(mock_db, 999)
        assert result == DEFAULT_SETTINGS

    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_stored_settings(self):
        """When user has no settings_json, return defaults"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await get_user_settings(mock_db, 1)
        assert result == DEFAULT_SETTINGS

    @pytest.mark.asyncio
    async def test_merges_stored_with_defaults(self):
        """Stored settings override defaults, missing keys use defaults"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = json.dumps({"language": "ru", "theme": "dark"})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await get_user_settings(mock_db, 1)
        assert result["language"] == "ru"
        assert result["theme"] == "dark"
        assert result["match_speed"] == DEFAULT_SETTINGS["match_speed"]
        assert result["sound_effects"] == DEFAULT_SETTINGS["sound_effects"]

    @pytest.mark.asyncio
    async def test_handles_corrupted_json(self):
        """If settings_json is corrupted, return defaults"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = "not valid json{{"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await get_user_settings(mock_db, 1)
        assert result == DEFAULT_SETTINGS


class TestUpdateSettings:
    """Tests for update_settings"""

    @pytest.mark.asyncio
    async def test_raises_on_user_not_found(self):
        """Should raise ValueError if user doesn't exist"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await update_settings(mock_db, 999, {"language": "ru"})

    @pytest.mark.asyncio
    async def test_raises_on_invalid_settings(self):
        """Should raise SettingsValidationError for invalid values"""
        mock_db = AsyncMock()

        with pytest.raises(SettingsValidationError):
            await update_settings(mock_db, 1, {"language": "invalid"})

    @pytest.mark.asyncio
    async def test_updates_and_merges_settings(self):
        """Should merge new settings with existing ones"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = json.dumps({"language": "en", "theme": "light"})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await update_settings(mock_db, 1, {"language": "fr"})
        
        # Verify the user's settings_json was updated
        stored = json.loads(mock_user.settings_json)
        assert stored["language"] == "fr"
        assert stored["theme"] == "light"  # preserved
        
        # Verify returned result includes defaults
        assert result["language"] == "fr"
        assert result["match_speed"] == DEFAULT_SETTINGS["match_speed"]

    @pytest.mark.asyncio
    async def test_updates_from_empty_settings(self):
        """Should work when user has no existing settings"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await update_settings(mock_db, 1, {"match_speed": 10})
        
        stored = json.loads(mock_user.settings_json)
        assert stored["match_speed"] == 10
        assert result["match_speed"] == 10


class TestResetSettings:
    """Tests for reset_settings"""

    @pytest.mark.asyncio
    async def test_raises_on_user_not_found(self):
        """Should raise ValueError if user doesn't exist"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await reset_settings(mock_db, 999)

    @pytest.mark.asyncio
    async def test_clears_settings_and_returns_defaults(self):
        """Should set settings_json to None and return defaults"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.settings_json = json.dumps({"language": "ru", "theme": "dark"})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await reset_settings(mock_db, 1)
        
        assert mock_user.settings_json is None
        assert result == DEFAULT_SETTINGS
