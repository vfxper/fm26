"""
Simple test runner for squad size validation tests
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the test module
from tests.services.test_transfer_service_squad_size import *

# Run a few key tests manually
def run_tests():
    print("Running Squad Size Validation Tests...")
    print("=" * 60)
    
    service = TransferService()
    
    # Test 1: Empty squad
    print("\n1. Testing empty squad (0 players)...")
    result = service.validate_transfer_squad_size(0)
    assert result is True, "Empty squad should be valid"
    print("   ✓ PASS")
    
    # Test 2: Typical squad
    print("\n2. Testing typical squad (25 players)...")
    result = service.validate_transfer_squad_size(25)
    assert result is True, "Squad with 25 players should be valid"
    print("   ✓ PASS")
    
    # Test 3: Near maximum
    print("\n3. Testing near maximum (39 players)...")
    result = service.validate_transfer_squad_size(39)
    assert result is True, "Squad with 39 players should be valid"
    print("   ✓ PASS")
    
    # Test 4: At maximum
    print("\n4. Testing at maximum (40 players)...")
    result = service.validate_transfer_squad_size(40)
    assert result is False, "Squad with 40 players should be invalid"
    print("   ✓ PASS")
    
    # Test 5: Over maximum
    print("\n5. Testing over maximum (41 players)...")
    result = service.validate_transfer_squad_size(41)
    assert result is False, "Squad with 41 players should be invalid"
    print("   ✓ PASS")
    
    # Test 6: Transfer bid with full squad
    print("\n6. Testing transfer bid with full squad...")
    result = service.submit_transfer_bid(
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
    assert result.success is False, "Transfer bid should fail with full squad"
    assert result.rejection_reason == "squad_full", "Rejection reason should be squad_full"
    assert "squad is full" in result.message.lower(), "Message should mention squad is full"
    print("   ✓ PASS")
    
    # Test 7: Loan with full squad
    print("\n7. Testing loan with full squad...")
    result = service.submit_loan_offer(
        career_week=5,
        current_squad_size=40,
        player_club_id=2,
        career_club_id=1,
        player_contract_months=24,
        loan_type="season_long",
        wage_contribution=0.5,
    )
    assert result.success is False, "Loan should fail with full squad"
    assert result.rejection_reason == "squad_full", "Rejection reason should be squad_full"
    print("   ✓ PASS")
    
    # Test 8: Free agent with full squad
    print("\n8. Testing free agent signing with full squad...")
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=40,
        career_transfer_budget=5_000_000,
        wage_offer=8_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    assert result.success is False, "Free agent signing should fail with full squad"
    assert result.rejection_reason == "squad_full", "Rejection reason should be squad_full"
    print("   ✓ PASS")
    
    # Test 9: MAX_SQUAD_SIZE constant
    print("\n9. Testing MAX_SQUAD_SIZE constant...")
    assert MAX_SQUAD_SIZE == 40, "MAX_SQUAD_SIZE should be 40"
    print("   ✓ PASS")
    
    # Test 10: Building squad from 0 to 40
    print("\n10. Testing building squad from 0 to 40...")
    for size in range(40):
        result = service.validate_transfer_squad_size(size)
        assert result is True, f"Squad size {size} should be valid"
    result = service.validate_transfer_squad_size(40)
    assert result is False, "Squad size 40 should be invalid"
    print("   ✓ PASS")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
