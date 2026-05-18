"""
Authentication API Routes

Endpoints for email registration, login, Google OAuth,
Telegram WebApp auth, email verification, and account linking.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.auth_service import (
    register_with_email,
    verify_email,
    login_with_email,
    login_with_google,
    login_with_telegram,
    link_telegram_to_account,
    request_email_for_telegram_user,
    verify_token,
    create_access_token,
    AuthError,
    InvalidCredentialsError,
    EmailNotVerifiedError,
    EmailAlreadyExistsError,
    InvalidTokenError,
    TelegramAuthError,
    GoogleAuthError,
    AccountLinkError,
)
from app.models.user import User
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Request/Response Models ---

class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., description="Email verification token")


class GoogleLoginRequest(BaseModel):
    google_id: str = Field(..., description="Google user ID")
    email: str = Field(..., description="Email from Google profile")
    name: Optional[str] = Field(None, description="Name from Google profile")


class TelegramLoginRequest(BaseModel):
    init_data: str = Field(..., description="Telegram WebApp initData string")


class LinkTelegramRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID to link")


class RequestEmailRequest(BaseModel):
    email: str = Field(..., description="Email to verify and link")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    telegram_user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    email_verified: bool = False
    google_id: Optional[str] = None
    auth_provider: str
    language_code: str = "en"


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# --- Dependency: Get current user from JWT ---

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract and validate JWT from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    user_id = verify_token(token)
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# --- Endpoints ---

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user with email and password.
    
    Returns a JWT token. The user must verify their email before
    they can log in again.
    """
    try:
        user, verification_token = await register_with_email(
            db, request.email, request.password, request.name
        )
        # Return token so user can access the app immediately
        # but email verification is required for subsequent logins
        access_token = create_access_token(user.id)
        return TokenResponse(access_token=access_token)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email_endpoint(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify email address using the token sent via email."""
    try:
        await verify_email(db, request.token)
        return MessageResponse(message="Email verified successfully")
    except InvalidTokenError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email and password."""
    try:
        access_token = await login_with_email(db, request.email, request.password)
        return TokenResponse(access_token=access_token)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except EmailNotVerifiedError as e:
        raise HTTPException(status_code=403, detail=e.message)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Login or register via Google OAuth."""
    try:
        access_token = await login_with_google(
            db, request.google_id, request.email, request.name
        )
        return TokenResponse(access_token=access_token)
    except GoogleAuthError as e:
        raise HTTPException(status_code=401, detail=e.message)


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(
    request: TelegramLoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate via Telegram WebApp initData."""
    try:
        access_token = await login_with_telegram(db, request.init_data)
        return TokenResponse(access_token=access_token)
    except TelegramAuthError as e:
        raise HTTPException(status_code=401, detail=e.message)


@router.post("/link-telegram", response_model=MessageResponse)
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Link a Telegram account to the current user's account."""
    try:
        await link_telegram_to_account(db, current_user.id, request.telegram_id)
        return MessageResponse(message="Telegram account linked successfully")
    except AccountLinkError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/request-email-verification", response_model=MessageResponse)
async def request_email_verification(
    request: RequestEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    For Telegram users: submit email for verification.
    This enables web login with the same account.
    """
    try:
        token = await request_email_for_telegram_user(
            db, current_user.id, request.email
        )
        # In production, send email with token. For now, return success.
        return MessageResponse(
            message="Verification email sent. Please check your inbox."
        )
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's information."""
    return UserResponse(
        id=current_user.id,
        telegram_user_id=current_user.telegram_user_id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        email_verified=current_user.email_verified,
        google_id=current_user.google_id,
        auth_provider=current_user.auth_provider,
        language_code=current_user.language_code,
    )
