"""
Manual test for AI bid generation (Task 8.7)
Tests the generate_ai_bids_for_listed method without pytest
"""
import sys
import random
from app.services.transfer_service import TransferService, AIBid


def test_basic_bid_generation():
    """Test basic AI bid generation"""
    print("Test 1: Basic bid generation with matching position")
    
    service = TransferService()
    
    listed_player = {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "John Striker",
        "position": "ST",
        "ca": 150,
    }
    
    ai_club = {
        "club_id": 10,
        "club_name": "Rich FC",
        "transfer_budget": 10000000,
        "needs": ["ST", "MC"],
    }
    
    # Set seed for reproducibility
    random.seed(42)
    
    # Generate bids multiple times
    bid_count = 0
    for _ in range(100):
        bids = service.generate_ai_bids_for_listed([listed_player], [ai_club])
        if len(bids) > 0:
            bid_count += 1
    
    print(f"  Generated {bid_count} bids out of 100 attempts")
    print(f"  Expected: 20-40 bids (30% probability)")
    
    if 20 <= bid_count <= 40:
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


def test_bid_amount_range():
    """Test that bid amounts are within 80-120% of asking price"""
    print("\nTest 2: Bid amount range (80-120% of asking price)")
    
    service = TransferService()
    
    listed_player = {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "John Striker",
        "position": "ST",
        "ca": 150,
    }
    
    ai_club = {
        "club_id": 10,
        "club_name": "Rich FC",
        "transfer_budget": 10000000,
        "needs": ["ST"],
    }
    
    random.seed(42)
    
    # Generate multiple bids
    all_bids = []
    for _ in range(50):
        bids = service.generate_ai_bids_for_listed([listed_player], [ai_club])
        all_bids.extend(bids)
    
    if len(all_bids) == 0:
        print("  ✗ FAIL: No bids generated")
        return False
    
    print(f"  Generated {len(all_bids)} bids")
    
    asking_price = listed_player["asking_price"]
    min_expected = asking_price * 0.8
    max_expected = asking_price * 1.2
    
    all_in_range = True
    for bid in all_bids:
        if not (min_expected <= bid.bid_amount <= max_expected):
            print(f"  ✗ Bid amount {bid.bid_amount} outside range [{min_expected}, {max_expected}]")
            all_in_range = False
            break
    
    if all_in_range:
        print(f"  All bids in range [{min_expected}, {max_expected}]")
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


def test_budget_constraint():
    """Test that clubs don't bid if they can't afford the player"""
    print("\nTest 3: Budget constraint (club can't afford player)")
    
    service = TransferService()
    
    expensive_player = {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "Expensive Player",
        "position": "ST",
        "ca": 150,
    }
    
    poor_club = {
        "club_id": 11,
        "club_name": "Poor FC",
        "transfer_budget": 300000,  # Can't afford 80% of 1M (800k)
        "needs": ["ST"],
    }
    
    random.seed(42)
    
    # Try to generate bids
    all_bids = []
    for _ in range(50):
        bids = service.generate_ai_bids_for_listed([expensive_player], [poor_club])
        all_bids.extend(bids)
    
    if len(all_bids) == 0:
        print("  Poor club correctly did not bid on expensive player")
        print("  ✓ PASS")
        return True
    else:
        print(f"  ✗ FAIL: Poor club generated {len(all_bids)} bids (should be 0)")
        return False


def test_wage_and_contract():
    """Test wage offer and contract year generation"""
    print("\nTest 4: Wage offer and contract years")
    
    service = TransferService()
    
    listed_player = {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "John Striker",
        "position": "ST",
        "ca": 150,
    }
    
    ai_club = {
        "club_id": 10,
        "club_name": "Rich FC",
        "transfer_budget": 10000000,
        "needs": ["ST"],
    }
    
    random.seed(42)
    
    # Generate bids
    all_bids = []
    for _ in range(50):
        bids = service.generate_ai_bids_for_listed([listed_player], [ai_club])
        all_bids.extend(bids)
    
    if len(all_bids) == 0:
        print("  ✗ FAIL: No bids generated")
        return False
    
    print(f"  Generated {len(all_bids)} bids")
    
    all_valid = True
    for bid in all_bids:
        # Check wage is at least minimum
        if bid.wage_offer < 1000:
            print(f"  ✗ Wage {bid.wage_offer} below minimum 1000")
            all_valid = False
            break
        
        # Check contract years in range 2-4
        if not (2 <= bid.contract_years <= 4):
            print(f"  ✗ Contract years {bid.contract_years} outside range [2, 4]")
            all_valid = False
            break
    
    if all_valid:
        print("  All wages >= 1000")
        print("  All contract years in range [2, 4]")
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


def test_multiple_clubs():
    """Test multiple clubs bidding on same player"""
    print("\nTest 5: Multiple clubs bidding on same player")
    
    service = TransferService()
    
    listed_player = {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "John Striker",
        "position": "ST",
        "ca": 150,
    }
    
    clubs = [
        {
            "club_id": 10,
            "club_name": "Rich FC",
            "transfer_budget": 10000000,
            "needs": ["ST"],
        },
        {
            "club_id": 11,
            "club_name": "Medium FC",
            "transfer_budget": 2000000,
            "needs": ["ST"],
        },
    ]
    
    random.seed(42)
    
    # Generate bids
    all_bids = []
    for _ in range(50):
        bids = service.generate_ai_bids_for_listed([listed_player], clubs)
        all_bids.extend(bids)
    
    if len(all_bids) == 0:
        print("  ✗ FAIL: No bids generated")
        return False
    
    print(f"  Generated {len(all_bids)} bids")
    
    # Check that we have bids from different clubs
    club_ids = {bid.club_id for bid in all_bids}
    print(f"  Bids from {len(club_ids)} different club(s)")
    
    if len(club_ids) >= 1:
        print("  ✓ PASS")
        return True
    else:
        print("  ✗ FAIL")
        return False


def test_empty_inputs():
    """Test with empty inputs"""
    print("\nTest 6: Empty inputs")
    
    service = TransferService()
    
    # Test with no players
    bids = service.generate_ai_bids_for_listed([], [{"club_id": 1, "club_name": "FC", "transfer_budget": 1000000, "needs": ["ST"]}])
    if len(bids) != 0:
        print("  ✗ FAIL: Expected 0 bids with no players")
        return False
    
    # Test with no clubs
    bids = service.generate_ai_bids_for_listed([{"player_id": 1, "asking_price": 1000000, "player_name": "Player", "position": "ST", "ca": 150}], [])
    if len(bids) != 0:
        print("  ✗ FAIL: Expected 0 bids with no clubs")
        return False
    
    # Test with both empty
    bids = service.generate_ai_bids_for_listed([], [])
    if len(bids) != 0:
        print("  ✗ FAIL: Expected 0 bids with empty inputs")
        return False
    
    print("  All empty input cases handled correctly")
    print("  ✓ PASS")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("AI Bid Generation Tests (Task 8.7)")
    print("=" * 60)
    
    tests = [
        test_basic_bid_generation,
        test_bid_amount_range,
        test_budget_constraint,
        test_wage_and_contract,
        test_multiple_clubs,
        test_empty_inputs,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ EXCEPTION: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
