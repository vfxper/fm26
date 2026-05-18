"""
Manual test script for wage calculation functionality.
This script can be run directly to verify the wage calculation implementation.
"""

import sys
sys.path.insert(0, 'C:\\Users\\sin3\\Documents\\fm26\\fm26')

from app.services.transfer_service import (
    TransferService,
    WAGE_BUDGET_WARNING_THRESHOLD,
    WAGE_BUDGET_CRITICAL_THRESHOLD,
)


def test_wage_impact_calculation():
    """Test wage impact calculation"""
    service = TransferService()
    
    print("=" * 60)
    print("Testing Wage Impact Calculation (Task 8.11)")
    print("=" * 60)
    
    # Test 1: Normal case (no warning)
    print("\nTest 1: Normal case (no warning)")
    result = service.calculate_wage_impact(
        current_wage_bill=300_000,
        new_player_wage=10_000,
        wage_budget=500_000,
    )
    print(f"  Current wage bill: £{result.current_wage_bill:,}")
    print(f"  New player wage: £{result.new_player_wage:,}")
    print(f"  Projected wage bill: £{result.projected_wage_bill:,}")
    print(f"  Wage budget ratio: {result.wage_budget_ratio:.2%}")
    print(f"  Is warning: {result.is_warning}")
    print(f"  Is critical: {result.is_critical}")
    print(f"  Message: {result.message}")
    assert result.projected_wage_bill == 310_000
    assert result.wage_budget_ratio == 0.62
    assert result.is_warning is False
    assert result.is_critical is False
    print("  ✓ PASSED")
    
    # Test 2: Warning threshold (75%)
    print("\nTest 2: Warning threshold (75%)")
    result = service.calculate_wage_impact(
        current_wage_bill=300_000,
        new_player_wage=75_000,
        wage_budget=500_000,
    )
    print(f"  Current wage bill: £{result.current_wage_bill:,}")
    print(f"  New player wage: £{result.new_player_wage:,}")
    print(f"  Projected wage bill: £{result.projected_wage_bill:,}")
    print(f"  Wage budget ratio: {result.wage_budget_ratio:.2%}")
    print(f"  Is warning: {result.is_warning}")
    print(f"  Is critical: {result.is_critical}")
    print(f"  Message: {result.message}")
    assert result.projected_wage_bill == 375_000
    assert result.wage_budget_ratio == 0.75
    assert result.is_warning is True
    assert result.is_critical is False
    assert "WARNING" in result.message
    assert "75%" in result.message
    print("  ✓ PASSED")
    
    # Test 3: Critical threshold (90%)
    print("\nTest 3: Critical threshold (90%)")
    result = service.calculate_wage_impact(
        current_wage_bill=300_000,
        new_player_wage=150_000,
        wage_budget=500_000,
    )
    print(f"  Current wage bill: £{result.current_wage_bill:,}")
    print(f"  New player wage: £{result.new_player_wage:,}")
    print(f"  Projected wage bill: £{result.projected_wage_bill:,}")
    print(f"  Wage budget ratio: {result.wage_budget_ratio:.2%}")
    print(f"  Is warning: {result.is_warning}")
    print(f"  Is critical: {result.is_critical}")
    print(f"  Message: {result.message}")
    assert result.projected_wage_bill == 450_000
    assert result.wage_budget_ratio == 0.90
    assert result.is_warning is True
    assert result.is_critical is True
    assert "CRITICAL" in result.message
    assert "90%" in result.message
    print("  ✓ PASSED")
    
    # Test 4: Over budget
    print("\nTest 4: Over budget (110%)")
    result = service.calculate_wage_impact(
        current_wage_bill=400_000,
        new_player_wage=150_000,
        wage_budget=500_000,
    )
    print(f"  Current wage bill: £{result.current_wage_bill:,}")
    print(f"  New player wage: £{result.new_player_wage:,}")
    print(f"  Projected wage bill: £{result.projected_wage_bill:,}")
    print(f"  Wage budget ratio: {result.wage_budget_ratio:.2%}")
    print(f"  Is warning: {result.is_warning}")
    print(f"  Is critical: {result.is_critical}")
    print(f"  Message: {result.message}")
    assert result.projected_wage_bill == 550_000
    assert result.wage_budget_ratio == 1.10
    assert result.is_warning is True
    assert result.is_critical is True
    print("  ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("All wage impact calculation tests PASSED!")
    print("=" * 60)


def test_budget_status():
    """Test budget status functionality"""
    service = TransferService()
    
    print("\n" + "=" * 60)
    print("Testing Budget Status (Task 8.12)")
    print("=" * 60)
    
    # Test 1: Normal case
    print("\nTest 1: Normal budget status")
    result = service.get_budget_status(
        transfer_budget=5_000_000,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"  Transfer budget: £{result.transfer_budget:,}")
    print(f"  Wage budget: £{result.wage_budget:,}")
    print(f"  Current wage bill: £{result.current_wage_bill:,}")
    print(f"  Available transfer funds: £{result.available_transfer_funds:,}")
    print(f"  Available wage room: £{result.available_wage_room:,}")
    print(f"  Can make transfers: {result.can_make_transfers}")
    print(f"  Message: {result.message}")
    assert result.available_wage_room == 200_000
    assert result.can_make_transfers is True
    print("  ✓ PASSED")
    
    # Test 2: No wage room
    print("\nTest 2: No wage room")
    result = service.get_budget_status(
        transfer_budget=5_000_000,
        wage_budget=500_000,
        current_wage_bill=500_000,
    )
    print(f"  Available wage room: £{result.available_wage_room:,}")
    print(f"  Can make transfers: {result.can_make_transfers}")
    print(f"  Message: {result.message}")
    assert result.available_wage_room == 0
    assert result.can_make_transfers is False
    assert "no wage budget room" in result.message.lower()
    print("  ✓ PASSED")
    
    # Test 3: No transfer budget
    print("\nTest 3: No transfer budget")
    result = service.get_budget_status(
        transfer_budget=0,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"  Available transfer funds: £{result.available_transfer_funds:,}")
    print(f"  Can make transfers: {result.can_make_transfers}")
    print(f"  Message: {result.message}")
    assert result.available_transfer_funds == 0
    assert result.can_make_transfers is False
    assert "no transfer funds" in result.message.lower()
    print("  ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("All budget status tests PASSED!")
    print("=" * 60)


def test_can_afford_transfer():
    """Test can_afford_transfer functionality"""
    service = TransferService()
    
    print("\n" + "=" * 60)
    print("Testing Can Afford Transfer")
    print("=" * 60)
    
    # Test 1: Can afford
    print("\nTest 1: Can afford transfer")
    result = service.can_afford_transfer(
        transfer_budget=5_000_000,
        wage_budget=500_000,
        current_wage_bill=300_000,
        fee=1_000_000,
        wage=50_000,
    )
    print(f"  Transfer budget: £5,000,000")
    print(f"  Wage budget: £500,000")
    print(f"  Current wage bill: £300,000")
    print(f"  Transfer fee: £1,000,000")
    print(f"  Player wage: £50,000")
    print(f"  Can afford: {result}")
    assert result is True
    print("  ✓ PASSED")
    
    # Test 2: Cannot afford fee
    print("\nTest 2: Cannot afford transfer fee")
    result = service.can_afford_transfer(
        transfer_budget=500_000,
        wage_budget=500_000,
        current_wage_bill=300_000,
        fee=1_000_000,
        wage=50_000,
    )
    print(f"  Transfer budget: £500,000")
    print(f"  Transfer fee: £1,000,000")
    print(f"  Can afford: {result}")
    assert result is False
    print("  ✓ PASSED")
    
    # Test 3: Cannot afford wage
    print("\nTest 3: Cannot afford player wage")
    result = service.can_afford_transfer(
        transfer_budget=5_000_000,
        wage_budget=500_000,
        current_wage_bill=480_000,
        fee=1_000_000,
        wage=50_000,
    )
    print(f"  Wage budget: £500,000")
    print(f"  Current wage bill: £480,000")
    print(f"  Player wage: £50,000")
    print(f"  Projected wage bill: £530,000")
    print(f"  Can afford: {result}")
    assert result is False
    print("  ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("All can afford transfer tests PASSED!")
    print("=" * 60)


def test_constants():
    """Test that constants are correctly defined"""
    print("\n" + "=" * 60)
    print("Testing Constants")
    print("=" * 60)
    
    print(f"\nWAGE_BUDGET_WARNING_THRESHOLD: {WAGE_BUDGET_WARNING_THRESHOLD} (75%)")
    assert WAGE_BUDGET_WARNING_THRESHOLD == 0.75
    print("  ✓ PASSED")
    
    print(f"\nWAGE_BUDGET_CRITICAL_THRESHOLD: {WAGE_BUDGET_CRITICAL_THRESHOLD} (90%)")
    assert WAGE_BUDGET_CRITICAL_THRESHOLD == 0.90
    print("  ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("All constant tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_constants()
        test_wage_impact_calculation()
        test_budget_status()
        test_can_afford_transfer()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print("\nTask 8.11 Implementation Summary:")
        print("✓ Wage impact calculation implemented")
        print("✓ Warning threshold (75%) detection working")
        print("✓ Critical threshold (90%) detection working")
        print("✓ Budget status management implemented")
        print("✓ Can afford transfer validation working")
        print("✓ All edge cases handled correctly")
        print("\nThe wage calculation functionality is fully implemented and tested!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
