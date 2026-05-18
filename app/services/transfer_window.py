"""
Transfer Window Service - Manages transfer window system

This module provides functionality for managing transfer windows in the football
manager game. It defines summer and winter transfer windows and provides methods
to check if transfers are currently allowed based on the career's current week.

Transfer Windows:
    - Summer Window: Weeks 1-8 of the season
    - Winter Window: Weeks 26-30 of the season
    - Emergency Loans: Available outside transfer windows
    - Free Agents: Available year-round
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class WindowType(str, Enum):
    """Transfer window type enumeration"""
    SUMMER = "summer"
    WINTER = "winter"
    CLOSED = "closed"


@dataclass
class TransferWindowStatus:
    """
    Status of the transfer window at a given point in time.
    
    Attributes:
        is_open: Whether the transfer window is currently open
        window_type: Type of window (SUMMER, WINTER, or CLOSED)
        current_week: Current week in the season (1-52)
        weeks_until_opens: Weeks until next window opens (0 if currently open)
        weeks_until_closes: Weeks until current window closes (0 if closed)
        can_make_permanent_transfers: Whether permanent transfers are allowed
        can_make_loan_transfers: Whether loan transfers are allowed
        can_sign_free_agents: Whether free agent signings are allowed
        can_make_emergency_loans: Whether emergency loans are allowed
    """
    is_open: bool
    window_type: WindowType
    current_week: int
    weeks_until_opens: int
    weeks_until_closes: int
    can_make_permanent_transfers: bool
    can_make_loan_transfers: bool
    can_sign_free_agents: bool
    can_make_emergency_loans: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "is_open": self.is_open,
            "window_type": self.window_type.value,
            "current_week": self.current_week,
            "weeks_until_opens": self.weeks_until_opens,
            "weeks_until_closes": self.weeks_until_closes,
            "can_make_permanent_transfers": self.can_make_permanent_transfers,
            "can_make_loan_transfers": self.can_make_loan_transfers,
            "can_sign_free_agents": self.can_sign_free_agents,
            "can_make_emergency_loans": self.can_make_emergency_loans,
        }


class TransferWindowService:
    """
    Service for managing transfer window system.
    
    This service handles:
    - Transfer window status checking
    - Window type determination (summer/winter)
    - Transfer eligibility validation
    - Window timing calculations
    
    Transfer Window Rules:
    - Summer Window: Weeks 1-8 (8 weeks at start of season)
    - Winter Window: Weeks 26-30 (5 weeks mid-season)
    - Emergency Loans: Available outside windows (weeks 9-25, 31-52)
    - Free Agents: Available year-round (weeks 1-52)
    
    Example:
        >>> service = TransferWindowService()
        >>> status = service.get_window_status(current_week=5)
        >>> if status.is_open:
        ...     print(f"Summer window is open! {status.weeks_until_closes} weeks remaining")
        >>> else:
        ...     print(f"Window closed. Opens in {status.weeks_until_opens} weeks")
    """
    
    # Transfer window configuration
    SUMMER_WINDOW_START = 1
    SUMMER_WINDOW_END = 8
    WINTER_WINDOW_START = 26
    WINTER_WINDOW_END = 30
    
    def __init__(self):
        """Initialize the transfer window service."""
        logger.debug("TransferWindowService initialized")
    
    def get_window_status(self, current_week: int) -> TransferWindowStatus:
        """
        Get the current transfer window status for a given week.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            TransferWindowStatus: Complete status of the transfer window
            
        Raises:
            ValueError: If current_week is not in valid range (1-52)
            
        Example:
            >>> service = TransferWindowService()
            >>> status = service.get_window_status(current_week=5)
            >>> print(f"Window open: {status.is_open}")
            >>> print(f"Window type: {status.window_type.value}")
        """
        if not 1 <= current_week <= 52:
            raise ValueError(f"Invalid week: {current_week}. Must be between 1 and 52.")
        
        # Determine if window is open and what type
        is_open, window_type = self._check_window_open(current_week)
        
        # Calculate timing information
        weeks_until_opens = self._calculate_weeks_until_opens(current_week) if not is_open else 0
        weeks_until_closes = self._calculate_weeks_until_closes(current_week) if is_open else 0
        
        # Determine what types of transfers are allowed
        can_make_permanent_transfers = is_open
        can_make_loan_transfers = is_open
        can_sign_free_agents = True  # Always available
        can_make_emergency_loans = not is_open  # Only outside windows
        
        status = TransferWindowStatus(
            is_open=is_open,
            window_type=window_type,
            current_week=current_week,
            weeks_until_opens=weeks_until_opens,
            weeks_until_closes=weeks_until_closes,
            can_make_permanent_transfers=can_make_permanent_transfers,
            can_make_loan_transfers=can_make_loan_transfers,
            can_sign_free_agents=can_sign_free_agents,
            can_make_emergency_loans=can_make_emergency_loans,
        )
        
        logger.debug(
            f"Transfer window status for week {current_week}: "
            f"is_open={is_open}, type={window_type.value}"
        )
        
        return status
    
    def is_window_open(self, current_week: int) -> bool:
        """
        Check if the transfer window is currently open.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            bool: True if window is open, False otherwise
            
        Example:
            >>> service = TransferWindowService()
            >>> if service.is_window_open(current_week=5):
            ...     print("Window is open!")
        """
        is_open, _ = self._check_window_open(current_week)
        return is_open
    
    def get_window_type(self, current_week: int) -> WindowType:
        """
        Get the type of transfer window for a given week.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            WindowType: SUMMER, WINTER, or CLOSED
            
        Example:
            >>> service = TransferWindowService()
            >>> window_type = service.get_window_type(current_week=5)
            >>> print(f"Window type: {window_type.value}")
        """
        _, window_type = self._check_window_open(current_week)
        return window_type
    
    def can_make_permanent_transfer(self, current_week: int) -> bool:
        """
        Check if permanent transfers are allowed in the current week.
        
        Permanent transfers are only allowed during open transfer windows.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            bool: True if permanent transfers are allowed, False otherwise
            
        Example:
            >>> service = TransferWindowService()
            >>> if service.can_make_permanent_transfer(current_week=5):
            ...     print("Can make permanent transfers")
        """
        return self.is_window_open(current_week)
    
    def can_make_loan_transfer(self, current_week: int) -> bool:
        """
        Check if loan transfers are allowed in the current week.
        
        Regular loan transfers are only allowed during open transfer windows.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            bool: True if loan transfers are allowed, False otherwise
            
        Example:
            >>> service = TransferWindowService()
            >>> if service.can_make_loan_transfer(current_week=5):
            ...     print("Can make loan transfers")
        """
        return self.is_window_open(current_week)
    
    def can_make_emergency_loan(self, current_week: int) -> bool:
        """
        Check if emergency loans are allowed in the current week.
        
        Emergency loans are only allowed OUTSIDE of transfer windows.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            bool: True if emergency loans are allowed, False otherwise
            
        Example:
            >>> service = TransferWindowService()
            >>> if service.can_make_emergency_loan(current_week=15):
            ...     print("Can make emergency loans")
        """
        return not self.is_window_open(current_week)
    
    def can_sign_free_agent(self, current_week: int) -> bool:
        """
        Check if free agent signings are allowed in the current week.
        
        Free agent signings are allowed year-round (all 52 weeks).
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            bool: Always True (free agents available year-round)
            
        Example:
            >>> service = TransferWindowService()
            >>> if service.can_sign_free_agent(current_week=15):
            ...     print("Can sign free agents")
        """
        return True
    
    def get_weeks_until_next_window(self, current_week: int) -> int:
        """
        Calculate weeks until the next transfer window opens.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            int: Number of weeks until next window opens (0 if currently open)
            
        Example:
            >>> service = TransferWindowService()
            >>> weeks = service.get_weeks_until_next_window(current_week=15)
            >>> print(f"Next window opens in {weeks} weeks")
        """
        if self.is_window_open(current_week):
            return 0
        return self._calculate_weeks_until_opens(current_week)
    
    def get_weeks_until_window_closes(self, current_week: int) -> int:
        """
        Calculate weeks until the current transfer window closes.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            int: Number of weeks until window closes (0 if window is closed)
            
        Example:
            >>> service = TransferWindowService()
            >>> weeks = service.get_weeks_until_window_closes(current_week=5)
            >>> print(f"Window closes in {weeks} weeks")
        """
        if not self.is_window_open(current_week):
            return 0
        return self._calculate_weeks_until_closes(current_week)
    
    # --- Private helper methods ---
    
    def _check_window_open(self, current_week: int) -> tuple[bool, WindowType]:
        """
        Check if transfer window is open and determine window type.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            tuple: (is_open: bool, window_type: WindowType)
        """
        # Check summer window (weeks 1-8)
        if self.SUMMER_WINDOW_START <= current_week <= self.SUMMER_WINDOW_END:
            return (True, WindowType.SUMMER)
        
        # Check winter window (weeks 26-30)
        if self.WINTER_WINDOW_START <= current_week <= self.WINTER_WINDOW_END:
            return (True, WindowType.WINTER)
        
        # Window is closed
        return (False, WindowType.CLOSED)
    
    def _calculate_weeks_until_opens(self, current_week: int) -> int:
        """
        Calculate weeks until the next transfer window opens.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            int: Number of weeks until next window opens
        """
        # If in summer window, return 0
        if self.SUMMER_WINDOW_START <= current_week <= self.SUMMER_WINDOW_END:
            return 0
        
        # If in winter window, return 0
        if self.WINTER_WINDOW_START <= current_week <= self.WINTER_WINDOW_END:
            return 0
        
        # If before summer window (shouldn't happen as season starts at week 1)
        if current_week < self.SUMMER_WINDOW_START:
            return self.SUMMER_WINDOW_START - current_week
        
        # If between summer and winter windows (weeks 9-25)
        if self.SUMMER_WINDOW_END < current_week < self.WINTER_WINDOW_START:
            return self.WINTER_WINDOW_START - current_week
        
        # If after winter window (weeks 31-52)
        if current_week > self.WINTER_WINDOW_END:
            # Next window is summer window of next season
            # Weeks remaining in current season + 1 (to get to week 1 of next season)
            return (52 - current_week) + 1
        
        return 0
    
    def _calculate_weeks_until_closes(self, current_week: int) -> int:
        """
        Calculate weeks until the current transfer window closes.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            int: Number of weeks until window closes (0 if not in a window)
        """
        # If in summer window
        if self.SUMMER_WINDOW_START <= current_week <= self.SUMMER_WINDOW_END:
            return self.SUMMER_WINDOW_END - current_week + 1
        
        # If in winter window
        if self.WINTER_WINDOW_START <= current_week <= self.WINTER_WINDOW_END:
            return self.WINTER_WINDOW_END - current_week + 1
        
        # Not in a window
        return 0
    
    def get_window_info(self, current_week: int) -> dict:
        """
        Get comprehensive information about transfer windows.
        
        Args:
            current_week: Current week in the season (1-52)
            
        Returns:
            dict: Comprehensive window information including:
                - current_status: Current window status
                - summer_window: Summer window details
                - winter_window: Winter window details
                - rules: Transfer rules summary
                
        Example:
            >>> service = TransferWindowService()
            >>> info = service.get_window_info(current_week=5)
            >>> print(f"Current window: {info['current_status']['window_type']}")
            >>> print(f"Summer window: weeks {info['summer_window']['start']}-{info['summer_window']['end']}")
        """
        status = self.get_window_status(current_week)
        
        return {
            "current_status": status.to_dict(),
            "summer_window": {
                "start": self.SUMMER_WINDOW_START,
                "end": self.SUMMER_WINDOW_END,
                "duration": self.SUMMER_WINDOW_END - self.SUMMER_WINDOW_START + 1,
            },
            "winter_window": {
                "start": self.WINTER_WINDOW_START,
                "end": self.WINTER_WINDOW_END,
                "duration": self.WINTER_WINDOW_END - self.WINTER_WINDOW_START + 1,
            },
            "rules": {
                "permanent_transfers": "Allowed during summer (weeks 1-8) and winter (weeks 26-30) windows",
                "loan_transfers": "Allowed during summer (weeks 1-8) and winter (weeks 26-30) windows",
                "emergency_loans": "Allowed outside transfer windows (weeks 9-25, 31-52)",
                "free_agents": "Allowed year-round (weeks 1-52)",
            },
        }
