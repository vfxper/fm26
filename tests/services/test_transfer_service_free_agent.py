"""
Tests for Transfer Service - Free Agent Signing System (Task 8.9)

Tests the free agent signing functionality including:
- Signing free agents outside transfer windows
- No transfer fee required (only wage agreement)
- Squad size validation
- Wage budget validation
- Contract validation
- Edge cases and boundary conditions
"""

import pytest
from app.services.transfer_service import (
    TransferService,
    MAX_SQUAD_SIZE,
    MIN_CONTRACT_YEARS,
    MAX_CONTRACT_YEARS,
)


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


class TestFreeAgentSigningBasics:
    """Test basic free agent signing functionality"""
    
    def test_sign_free_agent_success(self, transfer_service):
        """Test successfully signing a free agent"""
        result = transfer_service.sign_free_agent(
            career_week=15,  # Outside transfer window
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
        assert result.message == "Free agent signed successfully."
        assert result.bid_amount == 0  # No transfer fee
        assert result.acceptance_probability == 1.0  # Always accepted
        assert result.rejection_reason is None
    
    def test_sign_free_agent_during_transfer_window(self, transfer_service):
        """Test signing free agent during transfer window (should still work)"""
        result = transfer_service.sign_free_agent(
            career_week=5,  # During summer window
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Free agents can be signed any time, including during windows
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_outside_transfer_window(self, transfer_service):
        """Test signing free agent outside transfer window (main use case)"""
        result = transfer_service.sign_free_agent(
            career_week=15,  # Outside window
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_no_transfer_fee(self, transfer_service):
        """Test that free agent signing has no transfer fee"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=0,  # No transfer budget
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should succeed even with zero transfer budget
        assert result.success is True
        assert result.accepted is True
        assert result.bid_amount == 0


class TestFreeAgentSquadSizeValidation:
    """Test squad size validation for free agent signing"""
    
    def test_sign_free_agent_with_room_in_squad(self, transfer_service):
        """Test signing free agent when squad has room"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=39,  # One spot left
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
        assert result.rejection_reason != "squad_full"
    
    def test_sign_free_agent_with_full_squad(self, transfer_service):
        """Test signing free agent when squad is full (40 players)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,  # Squad full
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"
        assert "squad is full" in result.message.lower()
        assert "40" in result.message or "max" in result.message.lower()
    
    def test_sign_free_agent_with_over_full_squad(self, transfer_service):
        """Test signing free agent when squad is over full"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=41,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"


class TestFreeAgentWageBudgetValidation:
    """Test wage budget validation for free agent signing"""
    
    def test_sign_free_agent_with_sufficient_wage_budget(self, transfer_service):
        """Test signing free agent with sufficient wage budget"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,  # 300k + 10k = 310k < 500k
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_insufficient_wage_budget(self, transfer_service):
        """Test signing free agent with insufficient wage budget"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=50_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=480_000,  # 480k + 50k = 530k > 500k
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "wage_budget_exceeded"
        assert "wage budget" in result.message.lower()
    
    def test_sign_free_agent_at_wage_budget_limit(self, transfer_service):
        """Test signing free agent exactly at wage budget limit"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=490_000,  # 490k + 10k = 500k (exactly at limit)
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_one_over_wage_budget(self, transfer_service):
        """Test signing free agent one unit over wage budget"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_001,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=490_000,  # 490k + 10,001 = 500,001 > 500k
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "wage_budget_exceeded"


class TestFreeAgentContractValidation:
    """Test contract validation for free agent signing"""
    
    def test_sign_free_agent_with_valid_contract_1_year(self, transfer_service):
        """Test signing free agent with 1-year contract (minimum)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=1,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_valid_contract_5_years(self, transfer_service):
        """Test signing free agent with 5-year contract (maximum)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=5,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_valid_contract_3_years(self, transfer_service):
        """Test signing free agent with 3-year contract (typical)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_zero_year_contract(self, transfer_service):
        """Test signing free agent with 0-year contract (invalid)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=0,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "invalid_contract"
        assert "contract must be" in result.message.lower()
    
    def test_sign_free_agent_with_negative_contract(self, transfer_service):
        """Test signing free agent with negative contract years (invalid)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=-1,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "invalid_contract"
    
    def test_sign_free_agent_with_6_year_contract(self, transfer_service):
        """Test signing free agent with 6-year contract (over maximum)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=6,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "invalid_contract"


class TestFreeAgentWageValidation:
    """Test wage offer validation for free agent signing"""
    
    def test_sign_free_agent_with_positive_wage(self, transfer_service):
        """Test signing free agent with positive wage"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_zero_wage(self, transfer_service):
        """Test signing free agent with zero wage (invalid)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=0,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "invalid_wage"
        assert "wage offer must be positive" in result.message.lower()
    
    def test_sign_free_agent_with_negative_wage(self, transfer_service):
        """Test signing free agent with negative wage (invalid)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=-5_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "invalid_wage"
    
    def test_sign_free_agent_with_minimum_wage(self, transfer_service):
        """Test signing free agent with minimum wage (1)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=1,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_very_high_wage(self, transfer_service):
        """Test signing free agent with very high wage"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=100_000,
            contract_years=3,
            wage_budget=1_000_000,
            current_wage_bill=500_000,
        )
        
        assert result.success is True
        assert result.accepted is True




class TestFreeAgentAllWeeks:
    """Test free agent signing across all weeks of the season"""
    
    def test_sign_free_agent_week_1(self, transfer_service):
        """Test signing free agent in week 1 (summer window)"""
        result = transfer_service.sign_free_agent(
            career_week=1,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_week_10(self, transfer_service):
        """Test signing free agent in week 10 (outside window)"""
        result = transfer_service.sign_free_agent(
            career_week=10,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_week_27(self, transfer_service):
        """Test signing free agent in week 27 (winter window)"""
        result = transfer_service.sign_free_agent(
            career_week=27,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_week_52(self, transfer_service):
        """Test signing free agent in week 52 (end of season)"""
        result = transfer_service.sign_free_agent(
            career_week=52,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True


class TestFreeAgentAcceptanceProbability:
    """Test that free agents are always accepted"""
    
    def test_free_agent_always_accepted(self, transfer_service):
        """Test that free agents are always accepted (probability = 1.0)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.acceptance_probability == 1.0
    
    def test_free_agent_no_rejection_reason_on_success(self, transfer_service):
        """Test that successful free agent signing has no rejection reason"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.rejection_reason is None


class TestFreeAgentValidationPriority:
    """Test validation order for free agent signing"""
    
    def test_squad_size_checked_first(self, transfer_service):
        """Test that squad size is checked before other validations"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,  # Full squad
            career_transfer_budget=5_000_000,
            wage_offer=0,  # Invalid wage (but squad size should fail first)
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should fail due to squad size, not wage
        assert result.success is False
        assert result.rejection_reason == "squad_full"
    
    def test_contract_validation_after_squad_size(self, transfer_service):
        """Test that contract validation happens after squad size check"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,  # Valid squad size
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=0,  # Invalid contract
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should fail due to invalid contract
        assert result.success is False
        assert result.rejection_reason == "invalid_contract"
    
    def test_wage_validation_after_contract(self, transfer_service):
        """Test that wage validation happens after contract validation"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=0,  # Invalid wage
            contract_years=3,  # Valid contract
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should fail due to invalid wage
        assert result.success is False
        assert result.rejection_reason == "invalid_wage"
    
    def test_wage_budget_checked_last(self, transfer_service):
        """Test that wage budget is checked after other validations"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=50_000,  # Valid wage but exceeds budget
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=480_000,
        )
        
        # Should fail due to wage budget
        assert result.success is False
        assert result.rejection_reason == "wage_budget_exceeded"


class TestFreeAgentEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_sign_free_agent_with_empty_squad(self, transfer_service):
        """Test signing free agent with empty squad (0 players)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=0,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=0,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_zero_current_wage_bill(self, transfer_service):
        """Test signing free agent with zero current wage bill"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=0,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_zero_transfer_budget(self, transfer_service):
        """Test signing free agent with zero transfer budget (should work)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=0,  # No transfer budget
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should succeed because free agents don't require transfer budget
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_negative_transfer_budget(self, transfer_service):
        """Test signing free agent with negative transfer budget (should work)"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=-1_000_000,  # Negative budget
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        # Should succeed because free agents don't use transfer budget
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_with_very_large_wage_budget(self, transfer_service):
        """Test signing free agent with very large wage budget"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=10_000_000,  # Very large budget
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True


class TestFreeAgentErrorMessages:
    """Test that error messages are clear and informative"""
    
    def test_squad_full_error_message(self, transfer_service):
        """Test squad full error message"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "squad" in result.message.lower()
        assert "full" in result.message.lower() or "40" in result.message
    
    def test_invalid_contract_error_message(self, transfer_service):
        """Test invalid contract error message"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=0,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "contract" in result.message.lower()
        assert "1" in result.message and "5" in result.message
    
    def test_invalid_wage_error_message(self, transfer_service):
        """Test invalid wage error message"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=0,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "wage" in result.message.lower()
        assert "positive" in result.message.lower()
    
    def test_wage_budget_exceeded_error_message(self, transfer_service):
        """Test wage budget exceeded error message"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=50_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=480_000,
        )
        
        assert "wage budget" in result.message.lower()
    
    def test_success_message(self, transfer_service):
        """Test success message"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "free agent" in result.message.lower()
        assert "signed" in result.message.lower() or "success" in result.message.lower()


class TestFreeAgentConstants:
    """Test that contract constants are correctly defined"""
    
    def test_min_contract_years_constant(self):
        """Test that MIN_CONTRACT_YEARS constant is 1"""
        assert MIN_CONTRACT_YEARS == 1
    
    def test_max_contract_years_constant(self):
        """Test that MAX_CONTRACT_YEARS constant is 5"""
        assert MAX_CONTRACT_YEARS == 5
    
    def test_contract_validation_uses_constants(self, transfer_service):
        """Test that contract validation uses the constants"""
        # Test at MIN_CONTRACT_YEARS (should pass)
        result_min = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=MIN_CONTRACT_YEARS,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_min.success is True
        
        # Test at MAX_CONTRACT_YEARS (should pass)
        result_max = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=MAX_CONTRACT_YEARS,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_max.success is True
        
        # Test below MIN_CONTRACT_YEARS (should fail)
        result_below = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=MIN_CONTRACT_YEARS - 1,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_below.success is False
        
        # Test above MAX_CONTRACT_YEARS (should fail)
        result_above = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=MAX_CONTRACT_YEARS + 1,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_above.success is False


class TestFreeAgentRealisticScenarios:
    """Test realistic free agent signing scenarios"""
    
    def test_sign_experienced_free_agent_high_wage(self, transfer_service):
        """Test signing experienced free agent with high wage"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=28,
            career_transfer_budget=2_000_000,
            wage_offer=25_000,  # High wage for experienced player
            contract_years=2,  # Shorter contract for older player
            wage_budget=800_000,
            current_wage_bill=600_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_young_free_agent_low_wage(self, transfer_service):
        """Test signing young free agent with low wage"""
        result = transfer_service.sign_free_agent(
            career_week=20,
            current_squad_size=30,
            career_transfer_budget=1_000_000,
            wage_offer=3_000,  # Low wage for young player
            contract_years=4,  # Longer contract for development
            wage_budget=600_000,
            current_wage_bill=450_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_squad_depth(self, transfer_service):
        """Test signing free agent for squad depth"""
        result = transfer_service.sign_free_agent(
            career_week=35,
            current_squad_size=22,
            career_transfer_budget=500_000,
            wage_offer=5_000,  # Modest wage for backup player
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=350_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_free_agent_emergency_cover(self, transfer_service):
        """Test signing free agent for emergency cover (injuries)"""
        result = transfer_service.sign_free_agent(
            career_week=40,
            current_squad_size=18,  # Small squad due to injuries
            career_transfer_budget=100_000,
            wage_offer=4_000,
            contract_years=1,  # Short-term cover
            wage_budget=400_000,
            current_wage_bill=280_000,
        )
        
        assert result.success is True
        assert result.accepted is True
    
    def test_sign_multiple_free_agents_wage_accumulation(self, transfer_service):
        """Test signing multiple free agents and wage bill accumulation"""
        # First free agent
        result1 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result1.success is True
        
        # Second free agent (wage bill now 310k)
        result2 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=26,
            career_transfer_budget=5_000_000,
            wage_offer=15_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=310_000,
        )
        assert result2.success is True
        
        # Third free agent (wage bill now 325k)
        result3 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=27,
            career_transfer_budget=5_000_000,
            wage_offer=20_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=325_000,
        )
        assert result3.success is True
        
        # Fourth free agent would exceed budget (wage bill 345k + 200k > 500k)
        result4 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=28,
            career_transfer_budget=5_000_000,
            wage_offer=200_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=345_000,
        )
        assert result4.success is False
        assert result4.rejection_reason == "wage_budget_exceeded"


class TestFreeAgentBoundaryConditions:
    """Test boundary conditions for all validations"""
    
    def test_squad_size_boundary_39_to_40(self, transfer_service):
        """Test squad size boundary from 39 to 40"""
        # 39 players - should succeed
        result_39 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=39,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_39.success is True
        
        # 40 players - should fail
        result_40 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_40.success is False
    
    def test_contract_years_boundary_0_to_1(self, transfer_service):
        """Test contract years boundary from 0 to 1"""
        # 0 years - should fail
        result_0 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=0,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_0.success is False
        
        # 1 year - should succeed
        result_1 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=1,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_1.success is True
    
    def test_contract_years_boundary_5_to_6(self, transfer_service):
        """Test contract years boundary from 5 to 6"""
        # 5 years - should succeed
        result_5 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=5,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_5.success is True
        
        # 6 years - should fail
        result_6 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=6,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_6.success is False
    
    def test_wage_offer_boundary_0_to_1(self, transfer_service):
        """Test wage offer boundary from 0 to 1"""
        # 0 wage - should fail
        result_0 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=0,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_0.success is False
        
        # 1 wage - should succeed
        result_1 = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=1,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert result_1.success is True
    
    def test_wage_budget_exact_boundary(self, transfer_service):
        """Test wage budget exact boundary"""
        # Exactly at budget - should succeed
        result_exact = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=490_000,  # 490k + 10k = 500k
        )
        assert result_exact.success is True
        
        # One over budget - should fail
        result_over = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_001,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=490_000,  # 490k + 10,001 = 500,001
        )
        assert result_over.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
