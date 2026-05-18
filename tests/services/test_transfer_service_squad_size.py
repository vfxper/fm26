"""
Tests for Transfer Service - Squad Size Validation (Task 8.8)

Tests the squad size validation functionality including:
- Validating squad size before transfers (max 40 players)
- Preventing transfers when squad is full
- Edge cases and boundary conditions
- Integration with transfer bids and loan deals
"""

import pytest
from app.services.transfer_service import TransferService, MAX_SQUAD_SIZE


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


class TestSquadSizeValidation:
    """Test squad size validation for transfers"""
    
    def test_validate_squad_size_empty_squad(self, transfer_service):
        """Test validation with empty squad (0 players)"""
        current_size = 0
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is True
    
    def test_validate_squad_size_minimum_squad(self, transfer_service):
        """Test validation with minimum squad size (1 player)"""
        current_size = 1
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is True
    
    def test_validate_squad_size_typical_squad(self, transfer_service):
        """Test validation with typical squad size (25 players)"""
        current_size = 25
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is True
    
    def test_validate_squad_size_near_maximum(self, transfer_service):
        """Test validation with squad near maximum (39 players)"""
        current_size = 39
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is True
    
    def test_validate_squad_size_at_maximum(self, transfer_service):
        """Test validation with squad at maximum (40 players) - should reject"""
        current_size = 40
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is False
    
    def test_validate_squad_size_over_maximum(self, transfer_service):
        """Test validation with squad over maximum (41 players) - should reject"""
        current_size = 41
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is False
    
    def test_validate_squad_size_far_over_maximum(self, transfer_service):
        """Test validation with squad far over maximum (50 players) - should reject"""
        current_size = 50
        
        result = transfer_service.validate_transfer_squad_size(current_size)
        
        assert result is False


class TestSquadSizeInTransferBids:
    """Test squad size validation in transfer bid context"""
    
    def test_transfer_bid_with_room_in_squad(self, transfer_service):
        """Test transfer bid when squad has room (39 players)"""
        result = transfer_service.submit_transfer_bid(
            career_week=5,  # Summer window
            career_transfer_budget=5_000_000,
            current_squad_size=39,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        # Should succeed (may be accepted or rejected by AI, but not due to squad size)
        assert result.success is True
        assert result.rejection_reason != "squad_full"
    
    def test_transfer_bid_with_full_squad(self, transfer_service):
        """Test transfer bid when squad is full (40 players)"""
        result = transfer_service.submit_transfer_bid(
            career_week=5,  # Summer window
            career_transfer_budget=5_000_000,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"
        assert "squad is full" in result.message.lower()
        assert "40" in result.message or "max" in result.message.lower()
    
    def test_transfer_bid_with_over_full_squad(self, transfer_service):
        """Test transfer bid when squad is over full (41 players)"""
        result = transfer_service.submit_transfer_bid(
            career_week=5,  # Summer window
            career_transfer_budget=5_000_000,
            current_squad_size=41,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"


class TestSquadSizeInLoanDeals:
    """Test squad size validation in loan deal context"""
    
    def test_season_long_loan_with_room_in_squad(self, transfer_service):
        """Test season-long loan when squad has room (39 players)"""
        result = transfer_service.submit_loan_offer(
            career_week=5,  # Summer window
            current_squad_size=39,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="season_long",
            wage_contribution=0.5,
        )
        
        # Should succeed (may be accepted or rejected by AI, but not due to squad size)
        assert result.success is True
        assert result.rejection_reason != "squad_full"
    
    def test_season_long_loan_with_full_squad(self, transfer_service):
        """Test season-long loan when squad is full (40 players)"""
        result = transfer_service.submit_loan_offer(
            career_week=5,  # Summer window
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="season_long",
            wage_contribution=0.5,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"
        assert "squad is full" in result.message.lower()
    
    def test_emergency_loan_with_full_squad(self, transfer_service):
        """Test emergency loan when squad is full (40 players)"""
        result = transfer_service.submit_loan_offer(
            career_week=15,  # Outside window
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="emergency",
            wage_contribution=0.8,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"


class TestSquadSizeInFreeAgentSigning:
    """Test squad size validation in free agent signing context"""
    
    def test_free_agent_signing_with_room_in_squad(self, transfer_service):
        """Test free agent signing when squad has room (39 players)"""
        result = transfer_service.sign_free_agent(
            career_week=15,  # Outside window (free agents allowed)
            current_squad_size=39,
            career_transfer_budget=5_000_000,
            wage_offer=8_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is True
        assert result.accepted is True
        assert result.rejection_reason != "squad_full"
    
    def test_free_agent_signing_with_full_squad(self, transfer_service):
        """Test free agent signing when squad is full (40 players)"""
        result = transfer_service.sign_free_agent(
            career_week=15,  # Outside window (free agents allowed)
            current_squad_size=40,
            career_transfer_budget=5_000_000,
            wage_offer=8_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert result.success is False
        assert result.accepted is False
        assert result.rejection_reason == "squad_full"
        assert "squad is full" in result.message.lower()


class TestSquadSizeConstants:
    """Test that squad size constants are correctly defined"""
    
    def test_max_squad_size_constant(self):
        """Test that MAX_SQUAD_SIZE constant is 40"""
        assert MAX_SQUAD_SIZE == 40
    
    def test_max_squad_size_used_in_validation(self, transfer_service):
        """Test that validation uses MAX_SQUAD_SIZE constant"""
        # Test at MAX_SQUAD_SIZE - 1 (should pass)
        assert transfer_service.validate_transfer_squad_size(MAX_SQUAD_SIZE - 1) is True
        
        # Test at MAX_SQUAD_SIZE (should fail)
        assert transfer_service.validate_transfer_squad_size(MAX_SQUAD_SIZE) is False
        
        # Test at MAX_SQUAD_SIZE + 1 (should fail)
        assert transfer_service.validate_transfer_squad_size(MAX_SQUAD_SIZE + 1) is False


class TestSquadSizeBoundaryConditions:
    """Test boundary conditions for squad size validation"""
    
    def test_validate_squad_size_boundary_38_players(self, transfer_service):
        """Test validation at 38 players (well within limit)"""
        assert transfer_service.validate_transfer_squad_size(38) is True
    
    def test_validate_squad_size_boundary_39_players(self, transfer_service):
        """Test validation at 39 players (last valid size)"""
        assert transfer_service.validate_transfer_squad_size(39) is True
    
    def test_validate_squad_size_boundary_40_players(self, transfer_service):
        """Test validation at 40 players (first invalid size)"""
        assert transfer_service.validate_transfer_squad_size(40) is False
    
    def test_validate_squad_size_boundary_41_players(self, transfer_service):
        """Test validation at 41 players (over limit)"""
        assert transfer_service.validate_transfer_squad_size(41) is False


class TestSquadSizeErrorMessages:
    """Test that error messages are clear and informative"""
    
    def test_transfer_bid_error_message_mentions_squad_full(self, transfer_service):
        """Test that transfer bid error message mentions squad is full"""
        result = transfer_service.submit_transfer_bid(
            career_week=5,
            career_transfer_budget=5_000_000,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        assert "squad" in result.message.lower()
        assert "full" in result.message.lower() or "40" in result.message
    
    def test_loan_offer_error_message_mentions_squad_full(self, transfer_service):
        """Test that loan offer error message mentions squad is full"""
        result = transfer_service.submit_loan_offer(
            career_week=5,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="season_long",
            wage_contribution=0.5,
        )
        
        assert "squad" in result.message.lower()
        assert "full" in result.message.lower() or "40" in result.message
    
    def test_free_agent_error_message_mentions_squad_full(self, transfer_service):
        """Test that free agent signing error message mentions squad is full"""
        result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,
            career_transfer_budget=5_000_000,
            wage_offer=8_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        
        assert "squad" in result.message.lower()
        assert "full" in result.message.lower() or "40" in result.message


class TestSquadSizeValidationPriority:
    """Test that squad size validation happens at the right priority"""
    
    def test_squad_size_checked_before_ai_acceptance(self, transfer_service):
        """Test that squad size is checked before AI acceptance calculation"""
        # Even with a perfect bid, squad size should prevent transfer
        result = transfer_service.submit_transfer_bid(
            career_week=5,
            career_transfer_budget=10_000_000,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_market_value=1_000_000,
            selling_club_balance=-5_000_000,  # Desperate to sell
            player_contract_months=6,  # Short contract
            player_squad_status="NOT_NEEDED",  # Unwanted player
            bid_amount=5_000_000,  # 5x market value
            wage_offer=20_000,
        )
        
        # Should fail due to squad size, not reach AI acceptance
        assert result.success is False
        assert result.rejection_reason == "squad_full"
        assert result.acceptance_probability == 0.0
    
    def test_squad_size_checked_after_window_validation(self, transfer_service):
        """Test that window validation happens before squad size check"""
        # Closed window should be checked first
        result = transfer_service.submit_transfer_bid(
            career_week=15,  # Outside window
            career_transfer_budget=5_000_000,
            current_squad_size=40,  # Full squad
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        # Should fail due to window being closed, not squad size
        assert result.success is False
        assert result.rejection_reason == "window_closed"


class TestSquadSizeIntegration:
    """Test squad size validation in realistic scenarios"""
    
    def test_building_squad_from_empty_to_full(self, transfer_service):
        """Test building a squad from 0 to 40 players"""
        for squad_size in range(40):
            result = transfer_service.validate_transfer_squad_size(squad_size)
            assert result is True, f"Squad size {squad_size} should be valid"
        
        # 40th player should fail
        result = transfer_service.validate_transfer_squad_size(40)
        assert result is False
    
    def test_multiple_transfer_types_with_full_squad(self, transfer_service):
        """Test that all transfer types respect squad size limit"""
        # Transfer bid
        bid_result = transfer_service.submit_transfer_bid(
            career_week=5,
            career_transfer_budget=5_000_000,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        assert bid_result.rejection_reason == "squad_full"
        
        # Season-long loan
        loan_result = transfer_service.submit_loan_offer(
            career_week=5,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="season_long",
            wage_contribution=0.5,
        )
        assert loan_result.rejection_reason == "squad_full"
        
        # Emergency loan
        emergency_result = transfer_service.submit_loan_offer(
            career_week=15,
            current_squad_size=40,
            player_club_id=2,
            career_club_id=1,
            player_contract_months=24,
            loan_type="emergency",
            wage_contribution=0.8,
        )
        assert emergency_result.rejection_reason == "squad_full"
        
        # Free agent
        free_agent_result = transfer_service.sign_free_agent(
            career_week=15,
            current_squad_size=40,
            career_transfer_budget=5_000_000,
            wage_offer=8_000,
            contract_years=3,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        assert free_agent_result.rejection_reason == "squad_full"


class TestSquadSizeEdgeCases:
    """Test edge cases and unusual scenarios"""
    
    def test_validate_squad_size_with_negative_size(self, transfer_service):
        """Test validation with negative squad size (invalid input)"""
        # Negative size should still return True (no validation on negative)
        # This is a design decision - the method only checks upper bound
        result = transfer_service.validate_transfer_squad_size(-1)
        assert result is True
    
    def test_validate_squad_size_with_very_large_size(self, transfer_service):
        """Test validation with very large squad size"""
        result = transfer_service.validate_transfer_squad_size(1000)
        assert result is False
    
    def test_transfer_bid_with_exactly_39_players(self, transfer_service):
        """Test transfer bid with exactly 39 players (last valid size)"""
        result = transfer_service.submit_transfer_bid(
            career_week=5,
            career_transfer_budget=5_000_000,
            current_squad_size=39,
            player_club_id=2,
            career_club_id=1,
            player_market_value=2_000_000,
            selling_club_balance=1_000_000,
            player_contract_months=24,
            player_squad_status="FIRST_TEAM",
            bid_amount=2_500_000,
            wage_offer=10_000,
        )
        
        # Should succeed (not fail due to squad size)
        assert result.success is True
        assert result.rejection_reason != "squad_full"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
