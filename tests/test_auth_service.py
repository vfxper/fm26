"""
Tests for Authentication Service
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import (
    hash_password,
    verify_password,
    validate_email,
    create_access_token,
    verify_token,
    register_with_email,
    verify_email,
    login_with_email,
    login_with_google,
    link_telegram_to_account,
    request_email_for_telegram_user,
    AuthError,
    InvalidCredentialsError,
    EmailNotVerifiedError,
    EmailAlreadyExistsError,
    InvalidTokenError,
    AccountLinkError,
)
from app.models.user import User, AuthProvider


class TestPasswordHashing:
    """Tests for password hashing utilities"""

    def test_hash_password_returns_hash(self):
        hashed = hash_password("mypassword123")
        assert hashed != "mypassword123"
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = hash_password("testpass")
        assert verify_password("testpass", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("testpass")
        assert verify_password("wrongpass", hashed) is False

    def test_different_passwords_different_hashes(self):
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2


class TestEmailValidation:
    """Tests for email format validation"""

    def test_valid_emails(self):
        valid = [
            "user@example.com",
            "test.user@domain.org",
            "user+tag@gmail.com",
            "a@b.co",
        ]
        for email in valid:
            assert validate_email(email) is True, f"Expected {email} to be valid"

    def test_invalid_emails(self):
        invalid = [
            "",
            "notanemail",
            "@domain.com",
            "user@",
            "user @domain.com",
            None,
        ]
        for email in invalid:
            assert validate_email(email) is False, f"Expected {email!r} to be invalid"

    def test_email_too_long(self):
        long_email = "a" * 310 + "@example.com"  # 322 chars > 320 limit
        assert validate_email(long_email) is False


class TestJWTTokens:
    """Tests for JWT token creation and verification"""

    def test_create_and_verify_token(self):
        token = create_access_token(user_id=42)
        user_id = verify_token(token)
        assert user_id == 42

    def test_verify_invalid_token(self):
        result = verify_token("invalid.token.here")
        assert result is None

    def test_verify_expired_token(self):
        token = create_access_token(user_id=1, expires_delta=timedelta(seconds=-1))
        result = verify_token(token)
        assert result is None

    def test_token_contains_user_id(self):
        token = create_access_token(user_id=123)
        user_id = verify_token(token)
        assert user_id == 123


class TestRegisterWithEmail:
    """Tests for email registration"""

    @pytest.mark.asyncio
    async def test_successful_registration(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_db.execute.return_value = mock_result

        user, token = await register_with_email(
            mock_db, "test@example.com", "password123", "Test User"
        )

        assert user.email == "test@example.com"
        assert user.first_name == "Test User"
        assert user.email_verified is False
        assert user.auth_provider == AuthProvider.EMAIL.value
        assert user.password_hash is not None
        assert token is not None
        assert len(token) > 0
        mock_db.add.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_registration_invalid_email(self):
        mock_db = AsyncMock()

        with pytest.raises(AuthError, match="Invalid email format"):
            await register_with_email(mock_db, "notanemail", "password123", "Test")

    @pytest.mark.asyncio
    async def test_registration_weak_password(self):
        mock_db = AsyncMock()

        with pytest.raises(AuthError, match="at least 8 characters"):
            await register_with_email(mock_db, "test@example.com", "short", "Test")

    @pytest.mark.asyncio
    async def test_registration_email_already_exists(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Existing user
        mock_db.execute.return_value = mock_result

        with pytest.raises(EmailAlreadyExistsError):
            await register_with_email(
                mock_db, "existing@example.com", "password123", "Test"
            )


class TestVerifyEmail:
    """Tests for email verification"""

    @pytest.mark.asyncio
    async def test_successful_verification(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await verify_email(mock_db, "valid-token")

        assert result is True
        assert mock_user.email_verified is True
        assert mock_user.email_verification_token is None

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(InvalidTokenError, match="Invalid verification token"):
            await verify_email(mock_db, "bad-token")

    @pytest.mark.asyncio
    async def test_expired_token(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.email_verification_expires = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(InvalidTokenError, match="expired"):
            await verify_email(mock_db, "expired-token")


class TestLoginWithEmail:
    """Tests for email login"""

    @pytest.mark.asyncio
    async def test_successful_login(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = hash_password("correct_password")
        mock_user.email_verified = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        token = await login_with_email(mock_db, "user@example.com", "correct_password")

        assert token is not None
        assert verify_token(token) == 1

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.password_hash = hash_password("correct_password")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(InvalidCredentialsError):
            await login_with_email(mock_db, "user@example.com", "wrong_password")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(InvalidCredentialsError):
            await login_with_email(mock_db, "noone@example.com", "password")

    @pytest.mark.asyncio
    async def test_login_email_not_verified(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.password_hash = hash_password("password123")
        mock_user.email_verified = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(EmailNotVerifiedError):
            await login_with_email(mock_db, "user@example.com", "password123")


class TestLoginWithGoogle:
    """Tests for Google OAuth login"""

    @pytest.mark.asyncio
    async def test_new_google_user_created(self):
        mock_db = AsyncMock()
        
        # First call: no user by google_id
        # Second call: no user by email
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result_none
        
        # Track the user added to db so we can set id on flush
        added_users = []
        
        def track_add(user):
            added_users.append(user)
        mock_db.add = MagicMock(side_effect=track_add)
        
        async def mock_flush():
            for u in added_users:
                if u.id is None:
                    u.id = 10
        mock_db.flush = AsyncMock(side_effect=mock_flush)

        token = await login_with_google(
            mock_db, "google123", "user@gmail.com", "Google User"
        )

        assert token is not None
        assert verify_token(token) == 10
        assert len(added_users) == 1

    @pytest.mark.asyncio
    async def test_existing_google_user_login(self):
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 5
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        token = await login_with_google(
            mock_db, "google123", "user@gmail.com", "Google User"
        )

        assert token is not None
        assert verify_token(token) == 5
        mock_db.add.assert_not_called()


class TestLinkTelegramToAccount:
    """Tests for account linking"""

    @pytest.mark.asyncio
    async def test_successful_link(self):
        mock_db = AsyncMock()
        
        # First query: no existing telegram user
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        
        # Second query: the user to link
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.telegram_user_id = None
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_user
        
        mock_db.execute.side_effect = [mock_result_none, mock_result_user]

        result = await link_telegram_to_account(mock_db, 1, 12345)
        assert result.telegram_user_id == 12345

    @pytest.mark.asyncio
    async def test_link_already_used_telegram(self):
        mock_db = AsyncMock()
        
        # Telegram ID already linked to different user
        other_user = MagicMock()
        other_user.id = 2
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = other_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(AccountLinkError, match="already linked"):
            await link_telegram_to_account(mock_db, 1, 12345)

    @pytest.mark.asyncio
    async def test_link_user_not_found(self):
        mock_db = AsyncMock()
        
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result_none

        with pytest.raises(AccountLinkError, match="User not found"):
            await link_telegram_to_account(mock_db, 999, 12345)


class TestRequestEmailForTelegramUser:
    """Tests for Telegram user email verification flow"""

    @pytest.mark.asyncio
    async def test_successful_email_request(self):
        mock_db = AsyncMock()
        
        # First query: no existing user with this email
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        
        # Second query: the telegram user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_user
        
        mock_db.execute.side_effect = [mock_result_none, mock_result_user]

        token = await request_email_for_telegram_user(
            mock_db, 1, "user@example.com"
        )

        assert token is not None
        assert len(token) > 0
        assert mock_user.email == "user@example.com"
        assert mock_user.email_verified is False

    @pytest.mark.asyncio
    async def test_invalid_email_format(self):
        mock_db = AsyncMock()

        with pytest.raises(AuthError, match="Invalid email format"):
            await request_email_for_telegram_user(mock_db, 1, "notanemail")

    @pytest.mark.asyncio
    async def test_email_already_taken(self):
        mock_db = AsyncMock()
        
        # Email already used by another user
        existing_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(EmailAlreadyExistsError):
            await request_email_for_telegram_user(mock_db, 1, "taken@example.com")
