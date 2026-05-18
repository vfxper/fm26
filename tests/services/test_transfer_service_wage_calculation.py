"""
Tests for Transfer Service - Wage Calculation in Transfer Negotiations (Task 8.11)

Tests the wage calculation functionality including:
- Calculate impact of new player's wage on club finances
- Provide warning flags for wage budget thresholds (75%, 90%)
- Support wage budget management
- Edge cases and boundary conditions
"""

import pytest
from app.services.transfer_service import (
    TransferService,
    WageImpact,
    BudgetStatus,
    WAGE_BUDGET_WARNING_THRESHOLD,
    WAGE_BUDGET_CRITICAL_THRESHOLD,
)


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


class TestWageImpactCalculationBasics:
    """Test basic wage impact calculation functionality"""
    
    def test_calculate_wage_impact_normal_case(self, transfer_service):
        """Test wage impact calculation with normal values"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=10_000,
            wage_budget=500_000,
        )
        
        assert isinstance(result, WageImpact)
        assert result.current_wage_bill == 300_000
        assert result.new_player_wage == 10_000
        assert result.projected_wage_bill == 310_000
        assert result.wage_budget_ratio == 310_000 / 500_000
        assert result.is_warning is False
        assert result.is_critical is False
        assert "acceptable" in result.message.lower()
    
    def test_calculate_wage_impact_zero_current_bill(self, transfer_service):
        """Test wage impact with zero current wage bill"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=0,
            new_player_wage=10_000,
            wage_budget=500_000,
        )
        
        assert result.current_wage_bill == 0
        assert result.new_player_wage == 10_000
        assert result.projected_wage_bill == 10_000
        assert result.wage_budget_ratio == 10_000 / 500_000
        assert result.is_warning is False
        assert result.is_critical is False
    
    def test_calculate_wage_impact_zero_new_wage(self, transfer_service):
        """Test wage impact with zero new player wage"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=0,
            wage_budget=500_000,
        )
        
        assert result.current_wage_bill == 300_000
        assert result.new_player_wage == 0
        assert result.projected_wage_bill == 300_000
        assert result.wage_budget_ratio == 300_000 / 500_000
        assert result.is_warning is False
        assert result.is_critical is False


class TestWageImpactWarningThresholds:
    """Test warning threshold detection (75% of budget)"""
    
    def test_wage_impact_below_warning_threshold(self, transfer_service):
        """Test wage impact below 75% threshold (no warning)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=50_000,
            wage_budget=500_000,
        )
        
        # 350k / 500k = 0.70 (70%) - below 75% threshold
        assert result.wage_budget_ratio == 0.70
        assert result.is_warning is False
        assert result.is_critical is False
        assert "acceptable" in result.message.lower()
    
    def test_wage_impact_at_warning_threshold(self, transfer_service):
        """Test wage impact exactly at 75% threshold (warning)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=75_000,
            wage_budget=500_000,
        )
        
        # 375k / 500k = 0.75 (75%) - exactly at threshold
        assert result.wage_budget_ratio == 0.75
        assert result.is_warning is True
        assert result.is_critical is False
        assert "WARNING" in result.message
        assert "75%" in result.message
    
    def test_wage_impact_above_warning_threshold(self, transfer_service):
        """Test wage impact above 75% threshold (warning)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=100_000,
            wage_budget=500_000,
        )
        
        # 400k / 500k = 0.80 (80%) - above 75% threshold
        assert result.wage_budget_ratio == 0.80
        assert result.is_warning is True
        assert result.is_critical is False
        assert "WARNING" in result.message
    
    def test_wage_impact_just_below_warning_threshold(self, transfer_service):
        """Test wage impact just below 75% threshold (no warning)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=74_999,
            wage_budget=500_000,
        )
        
        # 374,999 / 500k = 0.749998 (74.9998%) - just below threshold
        assert result.wage_budget_ratio < 0.75
        assert result.is_warning is False
        assert result.is_critical is False


class TestWageImpactCriticalThresholds:
    """Test critical threshold detection (90% of budget)"""
    
    def test_wage_impact_below_critical_threshold(self, transfer_service):
        """Test wage impact below 90% threshold (warning but not critical)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=140_000,
            wage_budget=500_000,
        )
        
        # 440k / 500k = 0.88 (88%) - above warning but below critical
        assert result.wage_budget_ratio == 0.88
        assert result.is_warning is True
        assert result.is_critical is False
        assert "WARNING" in result.message
        assert "CRITICAL" not in result.message
    
    def test_wage_impact_at_critical_threshold(self, transfer_service):
        """Test wage impact exactly at 90% threshold (critical)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=150_000,
            wage_budget=500_000,
        )
        
        # 450k / 500k = 0.90 (90%) - exactly at critical threshold
        assert result.wage_budget_ratio == 0.90
        assert result.is_warning is True
        assert result.is_critical is True
        assert "CRITICAL" in result.message
        assert "90%" in result.message
    
    def test_wage_impact_above_critical_threshold(self, transfer_service):
        """Test wage impact above 90% threshold (critical)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=200_000,
            wage_budget=500_000,
        )
        
        # 500k / 500k = 1.00 (100%) - above critical threshold
        assert result.wage_budget_ratio == 1.00
        assert result.is_warning is True
        assert result.is_critical is True
        assert "CRITICAL" in result.message
    
    def test_wage_impact_just_below_critical_threshold(self, transfer_service):
        """Test wage impact just below 90% threshold (warning only)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=149_999,
            wage_budget=500_000,
        )
        
        # 449,999 / 500k = 0.899998 (89.9998%) - just below critical
        assert result.wage_budget_ratio < 0.90
        assert result.is_warning is True
        assert result.is_critical is False
        assert "WARNING" in result.message
        assert "CRITICAL" not in result.message


class TestWageImpactOverBudget:
    """Test wage impact when exceeding budget"""
    
    def test_wage_impact_exceeds_budget(self, transfer_service):
        """Test wage impact when projected bill exceeds budget"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=400_000,
            new_player_wage=150_000,
            wage_budget=500_000,
        )
        
        # 550k / 500k = 1.10 (110%) - exceeds budget
        assert result.projected_wage_bill == 550_000
        assert result.wage_budget_ratio == 1.10
        assert result.is_warning is True
        assert result.is_critical is True
        assert "CRITICAL" in result.message
    
    def test_wage_impact_far_exceeds_budget(self, transfer_service):
        """Test wage impact when far exceeding budget"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=400_000,
            new_player_wage=300_000,
            wage_budget=500_000,
        )
        
        # 700k / 500k = 1.40 (140%) - far exceeds budget
        assert result.projected_wage_bill == 700_000
        assert result.wage_budget_ratio == 1.40
        assert result.is_warning is True
        assert result.is_critical is True


class TestWageImpactZeroBudget:
    """Test wage impact with zero or negative budget"""
    
    def test_wage_impact_zero_budget_zero_bill(self, transfer_service):
        """Test wage impact with zero budget and zero bill"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=0,
            new_player_wage=10_000,
            wage_budget=0,
        )
        
        assert result.projected_wage_bill == 10_000
        assert result.wage_budget_ratio == 0.0  # Special case handling
    
    def test_wage_impact_zero_budget_positive_bill(self, transfer_service):
        """Test wage impact with zero budget and positive bill"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=100_000,
            new_player_wage=10_000,
            wage_budget=0,
        )
        
        assert result.projected_wage_bill == 110_000
        # When budget is 0 and projected > 0, ratio should be 1.0
        assert result.wage_budget_ratio == 1.0


class TestBudgetStatusBasics:
    """Test basic budget status functionality"""
    
    def test_get_budget_status_normal_case(self, transfer_service):
        """Test budget status with normal values"""
        result = transfer_service.get_budget_status(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert isinstance(result, BudgetStatus)
        assert result.transfer_budget == 5_000_000
        assert result.wage_budget == 500_000
        assert result.current_wage_bill == 300_000
        assert result.available_transfer_funds == 5_000_000
        assert result.available_wage_room == 200_000
        assert result.can_make_transfers is True
        assert "available" in result.message.lower()
    
    def test_get_budget_status_zero_wage_room(self, transfer_service):
        """Test budget status with zero wage room"""
        result = transfer_service.get_budget_status(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=500_000,
        )
        
        assert result.available_wage_room == 0
        assert result.can_make_transfers is False
        assert "no wage budget room" in result.message.lower()
    
    def test_get_budget_status_zero_transfer_budget(self, transfer_service):
        """Test budget status with zero transfer budget"""
        result = transfer_service.get_budget_status(
            transfer_budget=0,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.available_transfer_funds == 0
        assert result.can_make_transfers is False
        assert "no transfer funds" in result.message.lower()
    
    def test_get_budget_status_both_zero(self, transfer_service):
        """Test budget status with both budgets exhausted"""
        result = transfer_service.get_budget_status(
            transfer_budget=0,
            wage_budget=500_000,
            current_wage_bill=500_000,
        )
        
        assert result.available_transfer_funds == 0
        assert result.available_wage_room == 0
        assert result.can_make_transfers is False


class TestCanAffordTransfer:
    """Test can_afford_transfer functionality"""
    
    def test_can_afford_transfer_success(self, transfer_service):
        """Test can afford transfer with sufficient budgets"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=300_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is True
    
    def test_cannot_afford_transfer_fee(self, transfer_service):
        """Test cannot afford transfer due to insufficient transfer budget"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=500_000,
            wage_budget=500_000,
            current_wage_bill=300_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is False
    
    def test_cannot_afford_transfer_wage(self, transfer_service):
        """Test cannot afford transfer due to insufficient wage budget"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=480_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is False
    
    def test_cannot_afford_transfer_both(self, transfer_service):
        """Test cannot afford transfer due to both budgets"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=500_000,
            wage_budget=500_000,
            current_wage_bill=480_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is False
    
    def test_can_afford_transfer_at_limits(self, transfer_service):
        """Test can afford transfer exactly at budget limits"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=1_000_000,
            wage_budget=500_000,
            current_wage_bill=450_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is True
    
    def test_cannot_afford_transfer_one_over_fee(self, transfer_service):
        """Test cannot afford transfer one unit over fee budget"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=999_999,
            wage_budget=500_000,
            current_wage_bill=300_000,
            fee=1_000_000,
            wage=50_000,
        )
        
        assert result is False
    
    def test_cannot_afford_transfer_one_over_wage(self, transfer_service):
        """Test cannot afford transfer one unit over wage budget"""
        result = transfer_service.can_afford_transfer(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=450_000,
            fee=1_000_000,
            wage=50_001,
        )
        
        assert result is False


class TestWageImpactConstants:
    """Test that wage threshold constants are correctly defined"""
    
    def test_warning_threshold_constant(self):
        """Test that WAGE_BUDGET_WARNING_THRESHOLD is 0.75 (75%)"""
        assert WAGE_BUDGET_WARNING_THRESHOLD == 0.75
    
    def test_critical_threshold_constant(self):
        """Test that WAGE_BUDGET_CRITICAL_THRESHOLD is 0.90 (90%)"""
        assert WAGE_BUDGET_CRITICAL_THRESHOLD == 0.90
    
    def test_thresholds_are_ordered(self):
        """Test that warning threshold is less than critical threshold"""
        assert WAGE_BUDGET_WARNING_THRESHOLD < WAGE_BUDGET_CRITICAL_THRESHOLD


class TestWageImpactRealisticScenarios:
    """Test realistic wage impact scenarios"""
    
    def test_sign_star_player_high_wage(self, transfer_service):
        """Test signing star player with high wage"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=600_000,
            new_player_wage=100_000,  # Star player
            wage_budget=800_000,
        )
        
        # 700k / 800k = 0.875 (87.5%) - warning but not critical
        assert result.wage_budget_ratio == 0.875
        assert result.is_warning is True
        assert result.is_critical is False
    
    def test_sign_young_prospect_low_wage(self, transfer_service):
        """Test signing young prospect with low wage"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=400_000,
            new_player_wage=5_000,  # Young prospect
            wage_budget=600_000,
        )
        
        # 405k / 600k = 0.675 (67.5%) - safe
        assert result.wage_budget_ratio == 0.675
        assert result.is_warning is False
        assert result.is_critical is False
    
    def test_sign_backup_player_moderate_wage(self, transfer_service):
        """Test signing backup player with moderate wage"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=450_000,
            new_player_wage=20_000,  # Backup player
            wage_budget=600_000,
        )
        
        # 470k / 600k = 0.783 (78.3%) - warning
        assert result.wage_budget_ratio == pytest.approx(0.783, rel=0.01)
        assert result.is_warning is True
        assert result.is_critical is False
    
    def test_club_in_financial_trouble(self, transfer_service):
        """Test club already at high wage bill trying to sign player"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=550_000,
            new_player_wage=50_000,
            wage_budget=600_000,
        )
        
        # 600k / 600k = 1.00 (100%) - critical
        assert result.wage_budget_ratio == 1.00
        assert result.is_warning is True
        assert result.is_critical is True


class TestWageImpactEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_wage_impact_negative_current_bill(self, transfer_service):
        """Test wage impact with negative current bill (unusual but possible)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=-100_000,
            new_player_wage=50_000,
            wage_budget=500_000,
        )
        
        # -100k + 50k = -50k
        assert result.projected_wage_bill == -50_000
        assert result.current_wage_bill == -100_000
    
    def test_wage_impact_negative_new_wage(self, transfer_service):
        """Test wage impact with negative new wage (unusual)"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=-10_000,
            wage_budget=500_000,
        )
        
        # 300k + (-10k) = 290k
        assert result.projected_wage_bill == 290_000
        assert result.new_player_wage == -10_000
    
    def test_wage_impact_very_large_numbers(self, transfer_service):
        """Test wage impact with very large numbers"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=10_000_000,
            new_player_wage=500_000,
            wage_budget=15_000_000,
        )
        
        # 10.5M / 15M = 0.70 (70%)
        assert result.projected_wage_bill == 10_500_000
        assert result.wage_budget_ratio == 0.70
        assert result.is_warning is False
    
    def test_wage_impact_very_small_numbers(self, transfer_service):
        """Test wage impact with very small numbers"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=100,
            new_player_wage=50,
            wage_budget=200,
        )
        
        # 150 / 200 = 0.75 (75%)
        assert result.projected_wage_bill == 150
        assert result.wage_budget_ratio == 0.75
        assert result.is_warning is True


class TestWageImpactMessageContent:
    """Test that wage impact messages are clear and informative"""
    
    def test_acceptable_message(self, transfer_service):
        """Test acceptable wage impact message"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=50_000,
            wage_budget=500_000,
        )
        
        assert "acceptable" in result.message.lower()
        assert "WARNING" not in result.message
        assert "CRITICAL" not in result.message
    
    def test_warning_message(self, transfer_service):
        """Test warning wage impact message"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=300_000,
            new_player_wage=100_000,
            wage_budget=500_000,
        )
        
        assert "WARNING" in result.message
        assert "75%" in result.message
        assert "CRITICAL" not in result.message
    
    def test_critical_message(self, transfer_service):
        """Test critical wage impact message"""
        result = transfer_service.calculate_wage_impact(
            current_wage_bill=400_000,
            new_player_wage=100_000,
            wage_budget=500_000,
        )
        
        assert "CRITICAL" in result.message
        assert "90%" in result.message


class TestBudgetStatusMessageContent:
    """Test that budget status messages are clear and informative"""
    
    def test_budget_available_message(self, transfer_service):
        """Test budget available message"""
        result = transfer_service.get_budget_status(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "available" in result.message.lower()
        assert "5000000" in result.message or "5,000,000" in result.message
        assert "200000" in result.message or "200,000" in result.message
    
    def test_no_transfer_funds_message(self, transfer_service):
        """Test no transfer funds message"""
        result = transfer_service.get_budget_status(
            transfer_budget=0,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "no transfer funds" in result.message.lower()
    
    def test_no_wage_room_message(self, transfer_service):
        """Test no wage room message"""
        result = transfer_service.get_budget_status(
            transfer_budget=5_000_000,
            wage_budget=500_000,
            current_wage_bill=500_000,
        )
        
        assert "no wage budget room" in result.message.lower()
