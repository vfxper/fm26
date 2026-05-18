"""
User Model - Represents users in the system (Telegram, Email, Google OAuth)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, Boolean, Text, Index, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AuthProvider(str, enum.Enum):
    """Authentication provider types"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    GOOGLE = "google"


class User(Base):
    """
    User model representing application users.
    
    Users can authenticate via Telegram, email/password, or Google OAuth.
    The system supports account linking between providers.
    
    Attributes:
        id: Primary key, auto-increment
        telegram_user_id: Unique Telegram user ID (nullable for email/google users)
        username: Optional Telegram username
        first_name: Optional first name
        last_name: Optional last name
        language_code: Language code for localization (default 'en')
        email: Optional email address (unique)
        password_hash: Hashed password for email auth
        email_verified: Whether email has been verified
        email_verification_token: Token for email verification
        email_verification_expires: Expiry for verification token
        google_id: Google OAuth user ID
        auth_provider: Primary authentication provider
        settings_json: User settings stored as JSON text
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        last_login_at: Timestamp of last login
    """
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Telegram user identification (nullable - not all users come from Telegram)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
        comment="Telegram user ID (bigint to support Telegram's ID range)"
    )
    
    # User profile information
    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram username (without @)"
    )
    
    first_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="First name"
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Last name"
    )
    
    # Email authentication fields
    email: Mapped[Optional[str]] = mapped_column(
        String(320),
        unique=True,
        nullable=True,
        index=True,
        comment="Email address for email/password auth"
    )
    
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt hashed password"
    )
    
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether email has been verified"
    )
    
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Token for email verification"
    )
    
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Expiry datetime for email verification token"
    )
    
    # Google OAuth fields
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Google OAuth user ID"
    )
    
    # Auth provider tracking
    auth_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AuthProvider.TELEGRAM.value,
        server_default=AuthProvider.TELEGRAM.value,
        comment="Primary authentication provider (telegram, email, google)"
    )
    
    # User settings (JSON text)
    settings_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User settings stored as JSON"
    )
    
    # Localization
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        server_default="en",
        comment="Language code for localization (e.g., 'en', 'ru')"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when user was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when user was last updated"
    )
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last login"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_telegram_user_id', 'telegram_user_id'),
        Index('idx_users_username', 'username'),
        Index('idx_users_last_login_at', 'last_login_at'),
        Index('idx_users_email', 'email'),
        Index('idx_users_google_id', 'google_id'),
    )
    
    def __repr__(self) -> str:
        """String representation of User"""
        return (
            f"<User(id={self.id}, "
            f"telegram_user_id={self.telegram_user_id}, "
            f"email={self.email}, "
            f"auth_provider={self.auth_provider})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert User model to dictionary.
        
        Returns:
            dict: Dictionary representation of the user
        """
        return {
            "id": self.id,
            "telegram_user_id": self.telegram_user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "email_verified": self.email_verified,
            "google_id": self.google_id,
            "auth_provider": self.auth_provider,
            "language_code": self.language_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
