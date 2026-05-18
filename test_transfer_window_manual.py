"""
Manual test script for Transfer Window Service
"""

import sys
sys.path.insert(0, '.')

from app.services.transfer_window import TransferWindowService, WindowType

def test_transfer_window():
    """Manual test of transfer window functionality"""
    service = TransferWindowService()
    
    print("=" * 60)
    print("TRANSFER WINDOW SERVICE - MANUAL TEST")
    print("=" * 60)
    
    # Test summer window
    print("\n1. SUMMER WINDOW TESTS (Weeks 1-8)")
    print("-" * 60)
    for week in [1, 5, 8]:
        status = service.get_window_status(week)
        print(f"Week {week}:")
        print(f"  - Window Open: {status.is_open}")
        print(f"  - Window Type: {status.window_type.value}")
        print(f"  - Weeks Until Closes: {status.weeks_until_closes}")
        print(f"  - Can Make Permanent Transfers: {status.can_make_permanent_transfers}")
        print()
    
    # Test closed period between windows
    print("\n2. CLOSED PERIOD TESTS (Weeks 9-25)")
    print("-" * 60)
    for week in [9, 15, 25]:
        status = service.get_window_status(week)
        print(f"Week {week}:")
        print(f"  - Window Open: {status.is_open}")
        print(f"  - Window Type: {status.window_type.value}")
        print(f"  - Weeks Until Opens: {status.weeks_until_opens}")
        print(f"  - Can Make Emergency Loans: {status.can_make_emergency_loans}")
        print()
    
    # Test winter window
    print("\n3. WINTER WINDOW TESTS (Weeks 26-30)")
    print("-" * 60)
    for week in [26, 28, 30]:
        status = service.get_window_status(week)
        print(f"Week {week}:")
        print(f"  - Window Open: {status.is_open}")
        print(f"  - Window Type: {status.window_type.value}")
        print(f"  - Weeks Until Closes: {status.weeks_until_closes}")
        print(f"  - Can Make Permanent Transfers: {status.can_make_permanent_transfers}")
        print()
    
    # Test closed period after winter
    print("\n4. CLOSED PERIOD TESTS (Weeks 31-52)")
    print("-" * 60)
    for week in [31, 40, 52]:
        status = service.get_window_status(week)
        print(f"Week {week}:")
        print(f"  - Window Open: {status.is_open}")
        print(f"  - Window Type: {status.window_type.value}")
        print(f"  - Weeks Until Opens: {status.weeks_until_opens}")
        print(f"  - Can Make Emergency Loans: {status.can_make_emergency_loans}")
        print()
    
    # Test free agents (always available)
    print("\n5. FREE AGENT AVAILABILITY TEST")
    print("-" * 60)
    all_weeks_allow_free_agents = all(
        service.can_sign_free_agent(week) for week in range(1, 53)
    )
    print(f"Free agents available all 52 weeks: {all_weeks_allow_free_agents}")
    print()
    
    # Test window coverage
    print("\n6. FULL SEASON COVERAGE TEST")
    print("-" * 60)
    summer_weeks = sum(1 for week in range(1, 53) 
                      if service.get_window_type(week) == WindowType.SUMMER)
    winter_weeks = sum(1 for week in range(1, 53) 
                      if service.get_window_type(week) == WindowType.WINTER)
    closed_weeks = sum(1 for week in range(1, 53) 
                      if service.get_window_type(week) == WindowType.CLOSED)
    
    print(f"Summer window weeks: {summer_weeks} (expected: 8)")
    print(f"Winter window weeks: {winter_weeks} (expected: 5)")
    print(f"Closed weeks: {closed_weeks} (expected: 39)")
    print(f"Total weeks: {summer_weeks + winter_weeks + closed_weeks} (expected: 52)")
    print()
    
    # Test comprehensive window info
    print("\n7. COMPREHENSIVE WINDOW INFO TEST")
    print("-" * 60)
    info = service.get_window_info(current_week=5)
    print(f"Summer Window: Weeks {info['summer_window']['start']}-{info['summer_window']['end']} ({info['summer_window']['duration']} weeks)")
    print(f"Winter Window: Weeks {info['winter_window']['start']}-{info['winter_window']['end']} ({info['winter_window']['duration']} weeks)")
    print()
    
    # Validation summary
    print("\n8. VALIDATION SUMMARY")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Summer window is 8 weeks
    tests_total += 1
    if summer_weeks == 8:
        print("✓ Summer window is 8 weeks")
        tests_passed += 1
    else:
        print(f"✗ Summer window is {summer_weeks} weeks (expected 8)")
    
    # Test 2: Winter window is 5 weeks
    tests_total += 1
    if winter_weeks == 5:
        print("✓ Winter window is 5 weeks")
        tests_passed += 1
    else:
        print(f"✗ Winter window is {winter_weeks} weeks (expected 5)")
    
    # Test 3: Closed period is 39 weeks
    tests_total += 1
    if closed_weeks == 39:
        print("✓ Closed period is 39 weeks")
        tests_passed += 1
    else:
        print(f"✗ Closed period is {closed_weeks} weeks (expected 39)")
    
    # Test 4: Free agents always available
    tests_total += 1
    if all_weeks_allow_free_agents:
        print("✓ Free agents available all 52 weeks")
        tests_passed += 1
    else:
        print("✗ Free agents not available all weeks")
    
    # Test 5: Week 1 is in summer window
    tests_total += 1
    if service.is_window_open(1) and service.get_window_type(1) == WindowType.SUMMER:
        print("✓ Week 1 is in summer window")
        tests_passed += 1
    else:
        print("✗ Week 1 is not in summer window")
    
    # Test 6: Week 26 is in winter window
    tests_total += 1
    if service.is_window_open(26) and service.get_window_type(26) == WindowType.WINTER:
        print("✓ Week 26 is in winter window")
        tests_passed += 1
    else:
        print("✗ Week 26 is not in winter window")
    
    # Test 7: Week 15 is closed
    tests_total += 1
    if not service.is_window_open(15) and service.get_window_type(15) == WindowType.CLOSED:
        print("✓ Week 15 is closed")
        tests_passed += 1
    else:
        print("✗ Week 15 is not closed")
    
    # Test 8: Emergency loans only outside windows
    tests_total += 1
    emergency_loan_correct = (
        not service.can_make_emergency_loan(5) and  # Summer window
        service.can_make_emergency_loan(15) and     # Closed period
        not service.can_make_emergency_loan(28) and # Winter window
        service.can_make_emergency_loan(40)         # Closed period
    )
    if emergency_loan_correct:
        print("✓ Emergency loans only available outside windows")
        tests_passed += 1
    else:
        print("✗ Emergency loan availability incorrect")
    
    print()
    print("=" * 60)
    print(f"TESTS PASSED: {tests_passed}/{tests_total}")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n✓ ALL TESTS PASSED! Transfer window system is working correctly.")
        return 0
    else:
        print(f"\n✗ {tests_total - tests_passed} TEST(S) FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = test_transfer_window()
    sys.exit(exit_code)
