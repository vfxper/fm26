"""
Manual test script for player listing system (Task 8.6)
This script tests the player listing functionality without requiring pytest.
"""

import sys
from datetime import date

# Add the app directory to the path
sys.path.insert(0, '.')

from app.services.transfer_service import TransferService
from app.models.squad_player import SquadPlayer


class MockSquadPlayer:
    """Mock SquadPlayer for testing"""
    
    def __init__(self, player_id, wage, is_listed_for_sale=False, asking_price=None):
        self.player_id = player_id
        self.wage = wage
        self.is_listed_for_sale = is_listed_for_sale
        self.asking_price = asking_price
    
    def list_for_sale(self, asking_price):
        if asking_price < 0:
            raise ValueError("Asking price cannot be negative")
        self.is_listed_for_sale = True
        self.asking_price = asking_price
    
    def unlist_from_sale(self):
        self.is_listed_for_sale = False
        self.asking_price = None


def test_list_player_for_sale():
    """Test listing a player for sale"""
    print("Test 1: List player for sale")
    service = TransferService()
    player = MockSquadPlayer(1, 5000)
    
    result = service.list_player_for_sale(player, 1000000)
    
    assert result["player_id"] == 1
    assert result["asking_price"] == 1000000
    assert result["wage"] == 5000
    assert result["listed"] is True
    assert player.is_listed_for_sale is True
    assert player.asking_price == 1000000
    print("✓ PASSED")


def test_list_with_negative_price():
    """Test that negative asking price raises error"""
    print("\nTest 2: List with negative price (should fail)")
    service = TransferService()
    player = MockSquadPlayer(1, 5000)
    
    try:
        service.list_player_for_sale(player, -100000)
        print("✗ FAILED - Should have raised ValueError")
    except ValueError as e:
        if "negative" in str(e).lower():
            print("✓ PASSED - Correctly raised ValueError")
        else:
            print(f"✗ FAILED - Wrong error message: {e}")


def test_list_already_listed_player():
    """Test that listing an already listed player raises error"""
    print("\nTest 3: List already listed player (should fail)")
    service = TransferService()
    player = MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000)
    
    try:
        service.list_player_for_sale(player, 2000000)
        print("✗ FAILED - Should have raised ValueError")
    except ValueError as e:
        if "already listed" in str(e).lower():
            print("✓ PASSED - Correctly raised ValueError")
        else:
            print(f"✗ FAILED - Wrong error message: {e}")


def test_unlist_player():
    """Test unlisting a player"""
    print("\nTest 4: Unlist player from sale")
    service = TransferService()
    player = MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000)
    
    result = service.unlist_player_from_sale(player)
    
    assert result["player_id"] == 1
    assert result["listed"] is False
    assert player.is_listed_for_sale is False
    assert player.asking_price is None
    print("✓ PASSED")


def test_get_listed_players():
    """Test getting listed players from a squad"""
    print("\nTest 5: Get listed players")
    service = TransferService()
    
    players = [
        MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000),
        MockSquadPlayer(2, 6000, is_listed_for_sale=False),
        MockSquadPlayer(3, 7000, is_listed_for_sale=True, asking_price=2000000),
    ]
    
    listed = service.get_listed_players(players)
    
    assert len(listed) == 2
    assert all(p.is_listed_for_sale for p in listed)
    assert {p.player_id for p in listed} == {1, 3}
    print("✓ PASSED")


def test_get_listing_details():
    """Test getting listing details"""
    print("\nTest 6: Get listing details")
    service = TransferService()
    
    # Listed player
    listed_player = MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000)
    details = service.get_listing_details(listed_player)
    
    assert details is not None
    assert details["player_id"] == 1
    assert details["asking_price"] == 1000000
    assert details["listed"] is True
    
    # Not listed player
    not_listed_player = MockSquadPlayer(2, 6000, is_listed_for_sale=False)
    details = service.get_listing_details(not_listed_player)
    
    assert details is None
    print("✓ PASSED")


def test_validate_player_listing():
    """Test listing validation"""
    print("\nTest 7: Validate player listing")
    service = TransferService()
    
    # Valid listing
    player = MockSquadPlayer(1, 5000)
    is_valid, error = service.validate_player_listing(player, 1000000)
    assert is_valid is True
    assert error == ""
    
    # Negative price
    is_valid, error = service.validate_player_listing(player, -100000)
    assert is_valid is False
    assert "negative" in error.lower()
    
    # Already listed
    listed_player = MockSquadPlayer(2, 6000, is_listed_for_sale=True, asking_price=1000000)
    is_valid, error = service.validate_player_listing(listed_player, 2000000)
    assert is_valid is False
    assert "already listed" in error.lower()
    
    print("✓ PASSED")


def test_list_and_unlist_workflow():
    """Test complete workflow"""
    print("\nTest 8: Complete list and unlist workflow")
    service = TransferService()
    player = MockSquadPlayer(1, 5000)
    
    # Initially not listed
    assert player.is_listed_for_sale is False
    
    # List the player
    service.list_player_for_sale(player, 1500000)
    assert player.is_listed_for_sale is True
    assert player.asking_price == 1500000
    
    # Verify in listed players
    listed = service.get_listed_players([player])
    assert len(listed) == 1
    
    # Unlist the player
    service.unlist_player_from_sale(player)
    assert player.is_listed_for_sale is False
    assert player.asking_price is None
    
    # Verify not in listed players
    listed = service.get_listed_players([player])
    assert len(listed) == 0
    
    print("✓ PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Player Listing System Tests (Task 8.6)")
    print("=" * 60)
    
    try:
        test_list_player_for_sale()
        test_list_with_negative_price()
        test_list_already_listed_player()
        test_unlist_player()
        test_get_listed_players()
        test_get_listing_details()
        test_validate_player_listing()
        test_list_and_unlist_workflow()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
