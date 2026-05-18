"""
Custom Exceptions - Application-specific exceptions
"""

from fastapi import HTTPException, status


class TFMException(Exception):
    """Base exception for Telegram Football Manager"""
    
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PlayerNotFoundException(TFMException):
    """Raised when player is not found"""
    
    def __init__(self, player_id: int):
        super().__init__(
            message=f"Player with ID {player_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class CareerNotFoundException(TFMException):
    """Raised when career is not found"""
    
    def __init__(self, career_id: int):
        super().__init__(
            message=f"Career with ID {career_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ClubNotFoundException(TFMException):
    """Raised when club is not found"""
    
    def __init__(self, club_id: int):
        super().__init__(
            message=f"Club with ID {club_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class MatchNotFoundException(TFMException):
    """Raised when match is not found"""
    
    def __init__(self, match_id: int):
        super().__init__(
            message=f"Match with ID {match_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class TransferWindowClosedException(TFMException):
    """Raised when attempting transfer outside transfer window"""
    
    def __init__(self):
        super().__init__(
            message="Transfer window is currently closed",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InsufficientFundsException(TFMException):
    """Raised when club has insufficient funds for operation"""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            message=f"Insufficient funds. Required: {required}, Available: {available}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class SquadSizeLimitException(TFMException):
    """Raised when squad size limit is exceeded"""
    
    def __init__(self, current: int, maximum: int):
        super().__init__(
            message=f"Squad size limit exceeded. Current: {current}, Maximum: {maximum}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidTacticException(TFMException):
    """Raised when tactic configuration is invalid"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid tactic: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PlayerInjuredException(TFMException):
    """Raised when attempting to use injured player"""
    
    def __init__(self, player_id: int):
        super().__init__(
            message=f"Player {player_id} is currently injured",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuthenticationException(TFMException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class RateLimitException(TFMException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
