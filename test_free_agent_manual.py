"""
Manual test script for Free Agent Signing System (Task 8.9)

This script tests the free agent signing functionality without requiring pytest.
Run with: python test_free_agent_manual.py
"""

import sys
sys.path.insert(0, '.')

from app.services.transfer_service import TransferService


def test_free_agent_signing():
    """Manual test of free agent signing functionality"""
    service = TransferService()
    
    print("=" * 80)
    print("FREE AGENT SIGNING SYSTEM - MANUAL TEST (Task 8.9)")
    print("=" * 80)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic free agent signing (success)
    print("\n1. BASIC FREE AGENT SIGNING (SUCCESS)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,  # Outside transfer window
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Accepted: {result.accepted}")
    print(f"Transfer Fee: {result.bid_amount}")
    print(f"Acceptance Probability: {result.acceptance_probability}")
    if result.success and result.accepted and result.bid_amount == 0:
        print("✓ PASSED")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 2: Free agent signing outside transfer window
    print("\n2. FREE AGENT SIGNING OUTSIDE TRANSFER WINDOW")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=20,  # Outside window
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Week: 20 (outside window)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    if result.success and result.accepted:
        print("✓ PASSED - Free agents can be signed outside windows")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 3: Free agent signing during transfer window (should also work)
    print("\n3. FREE AGENT SIGNING DURING TRANSFER WINDOW")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=5,  # During summer window
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Week: 5 (during summer window)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    if result.success and result.accepted:
        print("✓ PASSED - Free agents can be signed during windows too")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 4: Squad size validation (full squad)
    print("\n4. SQUAD SIZE VALIDATION (FULL SQUAD)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=40,  # Full squad
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Squad Size: 40 (max)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Rejection Reason: {result.rejection_reason}")
    if not result.success and result.rejection_reason == "squad_full":
        print("✓ PASSED - Squad full validation works")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 5: Wage budget validation (insufficient)
    print("\n5. WAGE BUDGET VALIDATION (INSUFFICIENT)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=50_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=480_000,  # 480k + 50k > 500k
    )
    print(f"Wage Offer: 50,000")
    print(f"Current Wage Bill: 480,000")
    print(f"Wage Budget: 500,000")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Rejection Reason: {result.rejection_reason}")
    if not result.success and result.rejection_reason == "wage_budget_exceeded":
        print("✓ PASSED - Wage budget validation works")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 6: Contract validation (invalid - 0 years)
    print("\n6. CONTRACT VALIDATION (INVALID - 0 YEARS)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=0,  # Invalid
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Contract Years: 0 (invalid)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Rejection Reason: {result.rejection_reason}")
    if not result.success and result.rejection_reason == "invalid_contract":
        print("✓ PASSED - Contract validation works")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 7: Contract validation (invalid - 6 years)
    print("\n7. CONTRACT VALIDATION (INVALID - 6 YEARS)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=6,  # Over maximum
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Contract Years: 6 (over maximum of 5)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Rejection Reason: {result.rejection_reason}")
    if not result.success and result.rejection_reason == "invalid_contract":
        print("✓ PASSED - Contract maximum validation works")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 8: Wage validation (invalid - 0 wage)
    print("\n8. WAGE VALIDATION (INVALID - 0 WAGE)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=0,  # Invalid
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Wage Offer: 0 (invalid)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Rejection Reason: {result.rejection_reason}")
    if not result.success and result.rejection_reason == "invalid_wage":
        print("✓ PASSED - Wage validation works")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 9: No transfer fee required
    print("\n9. NO TRANSFER FEE REQUIRED")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=0,  # No transfer budget
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Transfer Budget: 0 (no budget)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Transfer Fee: {result.bid_amount}")
    if result.success and result.bid_amount == 0:
        print("✓ PASSED - No transfer fee required for free agents")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 10: Contract range validation (1-5 years)
    print("\n10. CONTRACT RANGE VALIDATION (1-5 YEARS)")
    print("-" * 80)
    tests_total += 1
    all_valid = True
    for years in [1, 2, 3, 4, 5]:
        result = service.sign_free_agent(
            career_week=15,
            current_squad_size=25,
            career_transfer_budget=5_000_000,
            wage_offer=10_000,
            contract_years=years,
            wage_budget=500_000,
            current_wage_bill=300_000,
        )
        print(f"  {years} years: {'✓' if result.success else '✗'}")
        if not result.success:
            all_valid = False
    if all_valid:
        print("✓ PASSED - All valid contract lengths (1-5) work")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 11: Acceptance probability is always 1.0
    print("\n11. ACCEPTANCE PROBABILITY (ALWAYS 1.0)")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    print(f"Acceptance Probability: {result.acceptance_probability}")
    if result.acceptance_probability == 1.0:
        print("✓ PASSED - Free agents always accepted (no negotiation)")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Test 12: Wage budget at exact limit
    print("\n12. WAGE BUDGET AT EXACT LIMIT")
    print("-" * 80)
    tests_total += 1
    result = service.sign_free_agent(
        career_week=15,
        current_squad_size=25,
        career_transfer_budget=5_000_000,
        wage_offer=10_000,
        contract_years=3,
        wage_budget=500_000,
        current_wage_bill=490_000,  # Exactly at limit
    )
    print(f"Wage Offer: 10,000")
    print(f"Current Wage Bill: 490,000")
    print(f"Wage Budget: 500,000")
    print(f"Total: 500,000 (exactly at limit)")
    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    if result.success:
        print("✓ PASSED - Can sign at exact wage budget limit")
        tests_passed += 1
    else:
        print("✗ FAILED")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print(f"Success Rate: {(tests_passed/tests_total)*100:.1f}%")
    
    if tests_passed == tests_total:
        print("\n✓ ALL TESTS PASSED! Free agent signing system is working correctly.")
        print("\nKey Features Verified:")
        print("  ✓ Free agents can be signed outside transfer windows")
        print("  ✓ Free agents can be signed during transfer windows")
        print("  ✓ No transfer fee required (only wage agreement)")
        print("  ✓ Squad size validation (max 40 players)")
        print("  ✓ Wage budget validation")
        print("  ✓ Contract validation (1-5 years)")
        print("  ✓ Wage offer validation (must be positive)")
        print("  ✓ Free agents always accepted (probability = 1.0)")
        return 0
    else:
        print(f"\n✗ {tests_total - tests_passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = test_free_agent_signing()
    sys.exit(exit_code)
