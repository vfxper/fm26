"""
Transfer Window Service - Usage Example

This example demonstrates how to use the TransferWindowService
to check transfer window status and validate transfer eligibility.
"""

from transfer_window import TransferWindowService


def main():
    """Demonstrate transfer window service usage"""
    
    # Initialize the service
    service = TransferWindowService()
    
    print("=" * 70)
    print("TRANSFER WINDOW SERVICE - USAGE EXAMPLE")
    print("=" * 70)
    
    # Example 1: Check if window is open at start of season
    print("\nExample 1: Start of Season (Week 1)")
    print("-" * 70)
    current_week = 1
    status = service.get_window_status(current_week)
    
    print(f"Current Week: {current_week}")
    print(f"Window Open: {status.is_open}")
    print(f"Window Type: {status.window_type.value}")
    print(f"Weeks Until Closes: {status.weeks_until_closes}")
    print(f"\nTransfer Options:")
    print(f"  - Permanent Transfers: {'✓ Allowed' if status.can_make_permanent_transfers else '✗ Not Allowed'}")
    print(f"  - Loan Transfers: {'✓ Allowed' if status.can_make_loan_transfers else '✗ Not Allowed'}")
    print(f"  - Emergency Loans: {'✓ Allowed' if status.can_make_emergency_loans else '✗ Not Allowed'}")
    print(f"  - Free Agents: {'✓ Allowed' if status.can_sign_free_agents else '✗ Not Allowed'}")
    
    # Example 2: Check status mid-season (window closed)
    print("\n\nExample 2: Mid-Season (Week 15)")
    print("-" * 70)
    current_week = 15
    status = service.get_window_status(current_week)
    
    print(f"Current Week: {current_week}")
    print(f"Window Open: {status.is_open}")
    print(f"Window Type: {status.window_type.value}")
    print(f"Weeks Until Opens: {status.weeks_until_opens}")
    print(f"\nTransfer Options:")
    print(f"  - Permanent Transfers: {'✓ Allowed' if status.can_make_permanent_transfers else '✗ Not Allowed'}")
    print(f"  - Loan Transfers: {'✓ Allowed' if status.can_make_loan_transfers else '✗ Not Allowed'}")
    print(f"  - Emergency Loans: {'✓ Allowed' if status.can_make_emergency_loans else '✗ Not Allowed'}")
    print(f"  - Free Agents: {'✓ Allowed' if status.can_sign_free_agents else '✗ Not Allowed'}")
    
    # Example 3: Check status during winter window
    print("\n\nExample 3: Winter Window (Week 28)")
    print("-" * 70)
    current_week = 28
    status = service.get_window_status(current_week)
    
    print(f"Current Week: {current_week}")
    print(f"Window Open: {status.is_open}")
    print(f"Window Type: {status.window_type.value}")
    print(f"Weeks Until Closes: {status.weeks_until_closes}")
    print(f"\nTransfer Options:")
    print(f"  - Permanent Transfers: {'✓ Allowed' if status.can_make_permanent_transfers else '✗ Not Allowed'}")
    print(f"  - Loan Transfers: {'✓ Allowed' if status.can_make_loan_transfers else '✗ Not Allowed'}")
    print(f"  - Emergency Loans: {'✓ Allowed' if status.can_make_emergency_loans else '✗ Not Allowed'}")
    print(f"  - Free Agents: {'✓ Allowed' if status.can_sign_free_agents else '✗ Not Allowed'}")
    
    # Example 4: Get comprehensive window information
    print("\n\nExample 4: Comprehensive Window Information")
    print("-" * 70)
    info = service.get_window_info(current_week=5)
    
    print("Summer Window:")
    print(f"  - Weeks: {info['summer_window']['start']}-{info['summer_window']['end']}")
    print(f"  - Duration: {info['summer_window']['duration']} weeks")
    
    print("\nWinter Window:")
    print(f"  - Weeks: {info['winter_window']['start']}-{info['winter_window']['end']}")
    print(f"  - Duration: {info['winter_window']['duration']} weeks")
    
    print("\nTransfer Rules:")
    for rule_type, rule_desc in info['rules'].items():
        print(f"  - {rule_type.replace('_', ' ').title()}: {rule_desc}")
    
    # Example 5: Validate specific transfer types
    print("\n\nExample 5: Transfer Type Validation")
    print("-" * 70)
    
    test_weeks = [1, 5, 9, 15, 26, 30, 40, 52]
    
    print(f"{'Week':<6} {'Window':<10} {'Permanent':<12} {'Loan':<12} {'Emergency':<12} {'Free Agent':<12}")
    print("-" * 70)
    
    for week in test_weeks:
        window_type = service.get_window_type(week).value
        permanent = "✓" if service.can_make_permanent_transfer(week) else "✗"
        loan = "✓" if service.can_make_loan_transfer(week) else "✗"
        emergency = "✓" if service.can_make_emergency_loan(week) else "✗"
        free_agent = "✓" if service.can_sign_free_agent(week) else "✗"
        
        print(f"{week:<6} {window_type:<10} {permanent:<12} {loan:<12} {emergency:<12} {free_agent:<12}")
    
    # Example 6: Integration with Career System
    print("\n\nExample 6: Integration with Career System")
    print("-" * 70)
    print("Usage in career advancement:")
    print("""
    from app.services.transfer_window import TransferWindowService
    from app.models.career import Career
    
    # In your career service or transfer service:
    def can_submit_transfer_bid(career: Career, transfer_type: str) -> bool:
        service = TransferWindowService()
        current_week = career.current_week
        
        if transfer_type == "permanent":
            return service.can_make_permanent_transfer(current_week)
        elif transfer_type == "loan":
            return service.can_make_loan_transfer(current_week)
        elif transfer_type == "emergency_loan":
            return service.can_make_emergency_loan(current_week)
        elif transfer_type == "free_agent":
            return service.can_sign_free_agent(current_week)
        
        return False
    
    # Example usage:
    career = Career(current_season=1, current_week=15)
    
    if can_submit_transfer_bid(career, "permanent"):
        print("Can make permanent transfer")
    else:
        status = service.get_window_status(career.current_week)
        print(f"Cannot make permanent transfer. Window opens in {status.weeks_until_opens} weeks")
    """)
    
    print("\n" + "=" * 70)
    print("END OF EXAMPLES")
    print("=" * 70)


if __name__ == "__main__":
    main()
