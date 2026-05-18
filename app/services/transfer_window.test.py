"""
Unit tests for Transfer Window Service

Tests the transfer window system including:
- Summer window (weeks 1-8)
- Winter window (weeks 26-30)
- Window status checking
- Transfer eligibility validation
- Timing calculations
"""

import pytest
from app.services.transfer_window import (
    TransferWindowService,
    TransferWindowStatus,
    WindowType,
)


class TestTransferWindowService:
    """Test suite for TransferWindowService"""
    
    @pytest.fixture
    def service(self):
        """Create a TransferWindowService instance for testing"""
        return TransferWindowService()
    
    # --- Summer Window Tests ---
    
    def test_summer_window_week_1(self, service):
        """Test that week 1 is in summer window"""
        status = service.get_window_status(1)
        assert status.is_open is True
        assert status.window_type == WindowType.SUMMER
        assert status.can_make_permanent_transfers is True
        assert status.can_make_loan_transfers is True
        assert status.can_make_emergency_loans is False
    
    def test_summer_window_week_5(self, service):
        """Test that week 5 is in summer window"""
        status = service.get_window_status(5)
        assert status.is_open is True
        assert status.window_type == WindowType.SUMMER
        assert status.weeks_until_closes == 4  # Weeks 5, 6, 7, 8
    
    def test_summer_window_week_8(self, service):
        """Test that week 8 is the last week of summer window"""
        status = service.get_window_status(8)
        assert status.is_open is True
        assert status.window_type == WindowType.SUMMER
        assert status.weeks_until_closes == 1  # Last week
    
    def test_summer_window_duration(self, service):
        """Test that summer window lasts exactly 8 weeks"""
        summer_weeks = [week for week in range(1, 53) 
                       if service.is_window_open(week) and 
                       service.get_window_type(week) == WindowType.SUMMER]
        assert len(summer_weeks) == 8
        assert summer_weeks == list(range(1, 9))
    
    # --- Winter Window Tests ---
    
    def test_winter_window_week_26(self, service):
        """Test that week 26 is the first week of winter window"""
        status = service.get_window_status(26)
        assert status.is_open is True
        assert status.window_type == WindowType.WINTER
        assert status.can_make_permanent_transfers is True
        assert status.can_make_loan_transfers is True
        assert status.can_make_emergency_loans is False
    
    def test_winter_window_week_28(self, service):
        """Test that week 28 is in winter window"""
        status = service.get_window_status(28)
        assert status.is_open is True
        assert status.window_type == WindowType.WINTER
        assert status.weeks_until_closes == 3  # Weeks 28, 29, 30
    
    def test_winter_window_week_30(self, service):
        """Test that week 30 is the last week of winter window"""
        status = service.get_window_status(30)
        assert status.is_open is True
        assert status.window_type == WindowType.WINTER
        assert status.weeks_until_closes == 1  # Last week
    
    def test_winter_window_duration(self, service):
        """Test that winter window lasts exactly 5 weeks"""
        winter_weeks = [week for week in range(1, 53) 
                       if service.is_window_open(week) and 
                       service.get_window_type(week) == WindowType.WINTER]
        assert len(winter_weeks) == 5
        assert winter_weeks == list(range(26, 31))
    
    # --- Closed Window Tests ---
    
    def test_window_closed_week_9(self, service):
        """Test that week 9 is outside transfer window"""
        status = service.get_window_status(9)
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
        assert status.can_make_permanent_transfers is False
        assert status.can_make_loan_transfers is False
        assert status.can_make_emergency_loans is True
    
    def test_window_closed_week_15(self, service):
        """Test that week 15 is outside transfer window"""
        status = service.get_window_status(15)
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
    
    def test_window_closed_week_25(self, service):
        """Test that week 25 is outside transfer window (just before winter)"""
        status = service.get_window_status(25)
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
        assert status.weeks_until_opens == 1  # Winter window opens next week
    
    def test_window_closed_week_31(self, service):
        """Test that week 31 is outside transfer window (just after winter)"""
        status = service.get_window_status(31)
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
    
    def test_window_closed_week_52(self, service):
        """Test that week 52 is outside transfer window (end of season)"""
        status = service.get_window_status(52)
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
        assert status.weeks_until_opens == 1  # Summer window opens next season
    
    # --- Transfer Type Eligibility Tests ---
    
    def test_permanent_transfers_allowed_in_summer(self, service):
        """Test that permanent transfers are allowed during summer window"""
        for week in range(1, 9):
            assert service.can_make_permanent_transfer(week) is True
    
    def test_permanent_transfers_allowed_in_winter(self, service):
        """Test that permanent transfers are allowed during winter window"""
        for week in range(26, 31):
            assert service.can_make_permanent_transfer(week) is True
    
    def test_permanent_transfers_not_allowed_outside_windows(self, service):
        """Test that permanent transfers are not allowed outside windows"""
        for week in range(9, 26):
            assert service.can_make_permanent_transfer(week) is False
        for week in range(31, 53):
            assert service.can_make_permanent_transfer(week) is False
    
    def test_loan_transfers_allowed_in_summer(self, service):
        """Test that loan transfers are allowed during summer window"""
        for week in range(1, 9):
            assert service.can_make_loan_transfer(week) is True
    
    def test_loan_transfers_allowed_in_winter(self, service):
        """Test that loan transfers are allowed during winter window"""
        for week in range(26, 31):
            assert service.can_make_loan_transfer(week) is True
    
    def test_loan_transfers_not_allowed_outside_windows(self, service):
        """Test that loan transfers are not allowed outside windows"""
        for week in range(9, 26):
            assert service.can_make_loan_transfer(week) is False
        for week in range(31, 53):
            assert service.can_make_loan_transfer(week) is False
    
    def test_emergency_loans_allowed_outside_windows(self, service):
        """Test that emergency loans are allowed outside transfer windows"""
        # Between summer and winter
        for week in range(9, 26):
            assert service.can_make_emergency_loan(week) is True
        # After winter
        for week in range(31, 53):
            assert service.can_make_emergency_loan(week) is True
    
    def test_emergency_loans_not_allowed_in_windows(self, service):
        """Test that emergency loans are not allowed during transfer windows"""
        # Summer window
        for week in range(1, 9):
            assert service.can_make_emergency_loan(week) is False
        # Winter window
        for week in range(26, 31):
            assert service.can_make_emergency_loan(week) is False
    
    def test_free_agents_always_allowed(self, service):
        """Test that free agent signings are allowed year-round"""
        for week in range(1, 53):
            assert service.can_sign_free_agent(week) is True
    
    # --- Timing Calculation Tests ---
    
    def test_weeks_until_opens_during_summer(self, service):
        """Test that weeks_until_opens is 0 during summer window"""
        status = service.get_window_status(5)
        assert status.weeks_until_opens == 0
    
    def test_weeks_until_opens_during_winter(self, service):
        """Test that weeks_until_opens is 0 during winter window"""
        status = service.get_window_status(28)
        assert status.weeks_until_opens == 0
    
    def test_weeks_until_opens_between_windows(self, service):
        """Test weeks_until_opens calculation between summer and winter"""
        # Week 9: 17 weeks until winter window (26 - 9 = 17)
        status = service.get_window_status(9)
        assert status.weeks_until_opens == 17
        
        # Week 15: 11 weeks until winter window (26 - 15 = 11)
        status = service.get_window_status(15)
        assert status.weeks_until_opens == 11
        
        # Week 25: 1 week until winter window (26 - 25 = 1)
        status = service.get_window_status(25)
        assert status.weeks_until_opens == 1
    
    def test_weeks_until_opens_after_winter(self, service):
        """Test weeks_until_opens calculation after winter window"""
        # Week 31: 22 weeks until next summer (52 - 31 + 1 = 22)
        status = service.get_window_status(31)
        assert status.weeks_until_opens == 22
        
        # Week 40: 13 weeks until next summer (52 - 40 + 1 = 13)
        status = service.get_window_status(40)
        assert status.weeks_until_opens == 13
        
        # Week 52: 1 week until next summer (52 - 52 + 1 = 1)
        status = service.get_window_status(52)
        assert status.weeks_until_opens == 1
    
    def test_weeks_until_closes_in_summer(self, service):
        """Test weeks_until_closes calculation during summer window"""
        # Week 1: 8 weeks remaining (8 - 1 + 1 = 8)
        status = service.get_window_status(1)
        assert status.weeks_until_closes == 8
        
        # Week 5: 4 weeks remaining (8 - 5 + 1 = 4)
        status = service.get_window_status(5)
        assert status.weeks_until_closes == 4
        
        # Week 8: 1 week remaining (8 - 8 + 1 = 1)
        status = service.get_window_status(8)
        assert status.weeks_until_closes == 1
    
    def test_weeks_until_closes_in_winter(self, service):
        """Test weeks_until_closes calculation during winter window"""
        # Week 26: 5 weeks remaining (30 - 26 + 1 = 5)
        status = service.get_window_status(26)
        assert status.weeks_until_closes == 5
        
        # Week 28: 3 weeks remaining (30 - 28 + 1 = 3)
        status = service.get_window_status(28)
        assert status.weeks_until_closes == 3
        
        # Week 30: 1 week remaining (30 - 30 + 1 = 1)
        status = service.get_window_status(30)
        assert status.weeks_until_closes == 1
    
    def test_weeks_until_closes_outside_windows(self, service):
        """Test that weeks_until_closes is 0 outside windows"""
        status = service.get_window_status(15)
        assert status.weeks_until_closes == 0
        
        status = service.get_window_status(40)
        assert status.weeks_until_closes == 0
    
    # --- Helper Method Tests ---
    
    def test_is_window_open(self, service):
        """Test is_window_open helper method"""
        assert service.is_window_open(1) is True
        assert service.is_window_open(5) is True
        assert service.is_window_open(8) is True
        assert service.is_window_open(9) is False
        assert service.is_window_open(15) is False
        assert service.is_window_open(26) is True
        assert service.is_window_open(30) is True
        assert service.is_window_open(31) is False
    
    def test_get_window_type(self, service):
        """Test get_window_type helper method"""
        assert service.get_window_type(1) == WindowType.SUMMER
        assert service.get_window_type(5) == WindowType.SUMMER
        assert service.get_window_type(8) == WindowType.SUMMER
        assert service.get_window_type(9) == WindowType.CLOSED
        assert service.get_window_type(15) == WindowType.CLOSED
        assert service.get_window_type(26) == WindowType.WINTER
        assert service.get_window_type(28) == WindowType.WINTER
        assert service.get_window_type(30) == WindowType.WINTER
        assert service.get_window_type(31) == WindowType.CLOSED
    
    def test_get_weeks_until_next_window(self, service):
        """Test get_weeks_until_next_window helper method"""
        assert service.get_weeks_until_next_window(1) == 0  # In summer window
        assert service.get_weeks_until_next_window(9) == 17  # 17 weeks to winter
        assert service.get_weeks_until_next_window(26) == 0  # In winter window
        assert service.get_weeks_until_next_window(31) == 22  # 22 weeks to next summer
    
    def test_get_weeks_until_window_closes(self, service):
        """Test get_weeks_until_window_closes helper method"""
        assert service.get_weeks_until_window_closes(1) == 8  # 8 weeks left in summer
        assert service.get_weeks_until_window_closes(9) == 0  # Not in window
        assert service.get_weeks_until_window_closes(26) == 5  # 5 weeks left in winter
        assert service.get_weeks_until_window_closes(31) == 0  # Not in window
    
    # --- Edge Case Tests ---
    
    def test_invalid_week_raises_error(self, service):
        """Test that invalid week numbers raise ValueError"""
        with pytest.raises(ValueError, match="Invalid week"):
            service.get_window_status(0)
        
        with pytest.raises(ValueError, match="Invalid week"):
            service.get_window_status(53)
        
        with pytest.raises(ValueError, match="Invalid week"):
            service.get_window_status(-1)
        
        with pytest.raises(ValueError, match="Invalid week"):
            service.get_window_status(100)
    
    def test_boundary_weeks(self, service):
        """Test boundary weeks between windows"""
        # Week 8 (last of summer) -> Week 9 (first closed)
        assert service.is_window_open(8) is True
        assert service.is_window_open(9) is False
        
        # Week 25 (last closed before winter) -> Week 26 (first of winter)
        assert service.is_window_open(25) is False
        assert service.is_window_open(26) is True
        
        # Week 30 (last of winter) -> Week 31 (first closed)
        assert service.is_window_open(30) is True
        assert service.is_window_open(31) is False
    
    # --- Integration Tests ---
    
    def test_full_season_window_coverage(self, service):
        """Test that all 52 weeks are properly categorized"""
        summer_count = 0
        winter_count = 0
        closed_count = 0
        
        for week in range(1, 53):
            window_type = service.get_window_type(week)
            if window_type == WindowType.SUMMER:
                summer_count += 1
            elif window_type == WindowType.WINTER:
                winter_count += 1
            elif window_type == WindowType.CLOSED:
                closed_count += 1
        
        assert summer_count == 8  # 8 weeks of summer
        assert winter_count == 5  # 5 weeks of winter
        assert closed_count == 39  # 39 weeks closed (52 - 8 - 5)
        assert summer_count + winter_count + closed_count == 52
    
    def test_window_status_to_dict(self, service):
        """Test that TransferWindowStatus.to_dict() works correctly"""
        status = service.get_window_status(5)
        status_dict = status.to_dict()
        
        assert isinstance(status_dict, dict)
        assert status_dict["is_open"] is True
        assert status_dict["window_type"] == "summer"
        assert status_dict["current_week"] == 5
        assert "weeks_until_opens" in status_dict
        assert "weeks_until_closes" in status_dict
        assert "can_make_permanent_transfers" in status_dict
        assert "can_make_loan_transfers" in status_dict
        assert "can_sign_free_agents" in status_dict
        assert "can_make_emergency_loans" in status_dict
    
    def test_get_window_info(self, service):
        """Test get_window_info comprehensive information"""
        info = service.get_window_info(5)
        
        assert "current_status" in info
        assert "summer_window" in info
        assert "winter_window" in info
        assert "rules" in info
        
        assert info["summer_window"]["start"] == 1
        assert info["summer_window"]["end"] == 8
        assert info["summer_window"]["duration"] == 8
        
        assert info["winter_window"]["start"] == 26
        assert info["winter_window"]["end"] == 30
        assert info["winter_window"]["duration"] == 5
        
        assert "permanent_transfers" in info["rules"]
        assert "loan_transfers" in info["rules"]
        assert "emergency_loans" in info["rules"]
        assert "free_agents" in info["rules"]
    
    # --- Scenario Tests ---
    
    def test_scenario_start_of_season(self, service):
        """Test transfer window at start of season (week 1)"""
        status = service.get_window_status(1)
        
        assert status.is_open is True
        assert status.window_type == WindowType.SUMMER
        assert status.can_make_permanent_transfers is True
        assert status.can_make_loan_transfers is True
        assert status.can_sign_free_agents is True
        assert status.can_make_emergency_loans is False
        assert status.weeks_until_closes == 8
    
    def test_scenario_mid_season(self, service):
        """Test transfer window mid-season (week 15)"""
        status = service.get_window_status(15)
        
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
        assert status.can_make_permanent_transfers is False
        assert status.can_make_loan_transfers is False
        assert status.can_sign_free_agents is True
        assert status.can_make_emergency_loans is True
        assert status.weeks_until_opens == 11  # 11 weeks to winter window
    
    def test_scenario_winter_window(self, service):
        """Test transfer window during winter (week 28)"""
        status = service.get_window_status(28)
        
        assert status.is_open is True
        assert status.window_type == WindowType.WINTER
        assert status.can_make_permanent_transfers is True
        assert status.can_make_loan_transfers is True
        assert status.can_sign_free_agents is True
        assert status.can_make_emergency_loans is False
        assert status.weeks_until_closes == 3
    
    def test_scenario_end_of_season(self, service):
        """Test transfer window at end of season (week 52)"""
        status = service.get_window_status(52)
        
        assert status.is_open is False
        assert status.window_type == WindowType.CLOSED
        assert status.can_make_permanent_transfers is False
        assert status.can_make_loan_transfers is False
        assert status.can_sign_free_agents is True
        assert status.can_make_emergency_loans is True
        assert status.weeks_until_opens == 1  # Next week is week 1 of next season


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
