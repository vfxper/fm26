"""
Authentication Service - Multi-provider auth (Email, Google OAuth, Telegram)

Supports:
- Email/password registration and login with email verification
- Google OAuth login (auto-verified email)
- Telegram WebApp authentication via initData HMAC
- Account linking between providers
- JWT token management
"""

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import unquote, parse_qs

import bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, AuthProvider


# Email regex pattern (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Token expiry
EMAIL_VERIFICATION_EXPIRY_HOURS = 24


class AuthError(Exception):
    """Base authentication error"""
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidCredentialsError(AuthError):
    """Invalid email/password combination"""
    def __init__(self):
        super().__init__("Invalid email or password", "invalid_credentials")


class EmailNotVerifiedError(AuthError):
    """Email not yet verified"""
    def __init__(self):
        super().__init__("Email not verified. Please check your inbox.", "email_not_verified")


class EmailAlreadyExistsError(AuthError):
    """Email already registered"""
    def __init__(self):
        super().__init__("An account with this email already exists", "email_exists")


class InvalidTokenError(AuthError):
    """Invalid or expired token"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, "invalid_token")


class TelegramAuthError(AuthError):
    """Telegram authentication validation failed"""
    def __init__(self):
        super().__init__("Invalid Telegram authentication data", "telegram_auth_failed")


class GoogleAuthError(AuthError):
    """Google OAuth validation failed"""
    def __init__(self, message: str = "Invalid Google authentication"):
        super().__init__(message, "google_auth_failed")


class AccountLinkError(AuthError):
    """Account linking failed"""
    def __init__(self, message: str):
        super().__init__(message, "link_failed")


# --- Password Utilities ---

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# --- Email Validation ---

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str) or len(email) > 320:
        return False
    return EMAIL_REGEX.match(email) is not None


# --- JWT Token Management ---

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiry duration
        
    Returns:
        str: Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[int]:
    """
    Verify a JWT token and extract user_id.
    
    Args:
        token: JWT token string
        
    Returns:
        int: User ID if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        return int(user_id_str)
    except (JWTError, ValueError):
        return None


# --- Email Registration ---

async def register_with_email(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
) -> tuple[User, str]:
    """
    Register a new user with email and password.
    
    Args:
        db: Database session
        email: User's email address
        password: Plain text password (will be hashed)
        name: User's display name
        
    Returns:
        tuple: (User object, verification_token)
        
    Raises:
        AuthError: If email is invalid
        EmailAlreadyExistsError: If email already registered
    """
    # Validate email format
    email_lower = email.strip().lower()
    if not validate_email(email_lower):
        raise AuthError("Invalid email format", "invalid_email")
    
    # Validate password strength
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters", "weak_password")
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email_lower))
    existing = result.scalar_one_or_none()
    if existing:
        raise EmailAlreadyExistsError()
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_EXPIRY_HOURS)
    
    # Create user
    user = User(
        email=email_lower,
        password_hash=hash_password(password),
        first_name=name,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_expires=verification_expires,
        auth_provider=AuthProvider.EMAIL.value,
    )
    
    db.add(user)
    await db.flush()
    
    return user, verification_token


# --- Email Verification ---

async def verify_email(db: AsyncSession, token: str) -> bool:
    """
    Verify a user's email using the verification token.
    
    Args:
        db: Database session
        token: Verification token from email link
        
    Returns:
        bool: True if verification succeeded
        
    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    result = await db.execute(
        select(User).where(User.email_verification_token == token)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise InvalidTokenError("Invalid verification token")
    
    # Check expiry
    if user.email_verification_expires and user.email_verification_expires.replace(
        tzinfo=timezone.utc
    ) < datetime.now(timezone.utc):
        raise InvalidTokenError("Verification token has expired")
    
    # Mark as verified
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    await db.flush()
    
    return True


# --- Email Login ---

async def login_with_email(db: AsyncSession, email: str, password: str) -> str:
    """
    Authenticate a user with email and password.
    
    Args:
        db: Database session
        email: User's email
        password: Plain text password
        
    Returns:
        str: JWT access token
        
    Raises:
        InvalidCredentialsError: If email/password don't match
        EmailNotVerifiedError: If email not verified
    """
    email_lower = email.strip().lower()
    
    result = await db.execute(select(User).where(User.email == email_lower))
    user = result.scalar_one_or_none()
    
    if user is None or not user.password_hash:
        raise InvalidCredentialsError()
    
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    
    if not user.email_verified:
        raise EmailNotVerifiedError()
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    
    return create_access_token(user.id)


# --- Google OAuth ---

async def login_with_google(
    db: AsyncSession,
    google_id: str,
    email: str,
    name: Optional[str] = None,
) -> str:
    """
    Authenticate or register a user via Google OAuth.
    
    Google already verifies the email, so we auto-verify it.
    
    Args:
        db: Database session
        google_id: Google user ID from ID token
        email: Email from Google profile
        name: Display name from Google profile
        
    Returns:
        str: JWT access token
    """
    email_lower = email.strip().lower()
    
    # Try to find by google_id first
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        # Try to find by email (might be an existing email user)
        result = await db.execute(select(User).where(User.email == email_lower))
        user = result.scalar_one_or_none()
        
        if user:
            # Link Google to existing account
            user.google_id = google_id
            user.email_verified = True  # Google verified it
        else:
            # Create new user
            user = User(
                google_id=google_id,
                email=email_lower,
                first_name=name,
                email_verified=True,  # Google already verified
                auth_provider=AuthProvider.GOOGLE.value,
            )
            db.add(user)
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    
    return create_access_token(user.id)


# --- Telegram Authentication ---

def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    
    Args:
        init_data: Raw initData string from Telegram WebApp
        bot_token: Bot token for HMAC validation
        
    Returns:
        dict: Parsed user data if valid, None if invalid
    """
    try:
        # Parse the init_data query string
        parsed = parse_qs(init_data)
        
        # Extract hash
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None
        
        # Build data-check-string (sorted key=value pairs, excluding hash)
        data_pairs = []
        for key_value in init_data.split("&"):
            key = key_value.split("=", 1)[0]
            if key != "hash":
                data_pairs.append(key_value)
        
        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)
        
        # Compute HMAC
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        
        # Compare
        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        
        # Parse user data
        user_data_str = parsed.get("user", [None])[0]
        if not user_data_str:
            return None
        
        user_data = json.loads(unquote(user_data_str))
        return user_data
        
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


async def login_with_telegram(db: AsyncSession, init_data: str) -> str:
    """
    Authenticate a user via Telegram WebApp initData.
    
    Args:
        db: Database session
        init_data: Raw initData from Telegram WebApp
        
    Returns:
        str: JWT access token
        
    Raises:
        TelegramAuthError: If initData validation fails
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise TelegramAuthError()
    
    user_data = validate_telegram_init_data(init_data, bot_token)
    if user_data is None:
        raise TelegramAuthError()
    
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise TelegramAuthError()
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        # Create new Telegram user
        user = User(
            telegram_user_id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            language_code=user_data.get("language_code", "en"),
            auth_provider=AuthProvider.TELEGRAM.value,
        )
        db.add(user)
    else:
        # Update profile from Telegram
        user.username = user_data.get("username", user.username)
        user.first_name = user_data.get("first_name", user.first_name)
        user.last_name = user_data.get("last_name", user.last_name)
    
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    
    return create_access_token(user.id)


# --- Account Linking ---

async def link_telegram_to_account(
    db: AsyncSession,
    user_id: int,
    telegram_id: int,
) -> User:
    """
    Link a Telegram account to an existing user account.
    
    Allows playing from both web and Telegram with the same account.
    
    Args:
        db: Database session
        user_id: Existing user's ID
        telegram_id: Telegram user ID to link
        
    Returns:
        User: Updated user object
        
    Raises:
        AccountLinkError: If linking fails
    """
    # Check if telegram_id is already linked to another account
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_id)
    )
    existing_telegram_user = result.scalar_one_or_none()
    
    if existing_telegram_user and existing_telegram_user.id != user_id:
        raise AccountLinkError(
            "This Telegram account is already linked to another user"
        )
    
    # Get the user to link
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise AccountLinkError("User not found")
    
    if user.telegram_user_id and user.telegram_user_id != telegram_id:
        raise AccountLinkError(
            "This account is already linked to a different Telegram account"
        )
    
    user.telegram_user_id = telegram_id
    await db.flush()
    
    return user


# --- Telegram Email Verification Flow ---

async def request_email_for_telegram_user(
    db: AsyncSession,
    user_id: int,
    email: str,
) -> str:
    """
    For Telegram users on first login: request email verification.
    
    This enables the user to also log in via web browser.
    
    Args:
        db: Database session
        user_id: Telegram user's ID
        email: Email to verify and link
        
    Returns:
        str: Verification token
        
    Raises:
        AuthError: If email invalid or already taken
    """
    email_lower = email.strip().lower()
    if not validate_email(email_lower):
        raise AuthError("Invalid email format", "invalid_email")
    
    # Check if email is already used by another account
    result = await db.execute(
        select(User).where(User.email == email_lower, User.id != user_id)
    )
    if result.scalar_one_or_none():
        raise EmailAlreadyExistsError()
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("User not found", "user_not_found")
    
    # Set email and verification token
    verification_token = secrets.token_urlsafe(32)
    user.email = email_lower
    user.email_verified = False
    user.email_verification_token = verification_token
    user.email_verification_expires = datetime.now(timezone.utc) + timedelta(
        hours=EMAIL_VERIFICATION_EXPIRY_HOURS
    )
    await db.flush()
    
    return verification_token
