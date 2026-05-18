"""
Tests for Transfer Service - Player Listing System (Task 8.6)

Tests the player listing functionality including:
- Listing players for sale with asking price
- Unlisting players from sale
- Validating listing constraints
- Retrieving listed players
- Getting listing details
"""

import pytest
from datetime import date, timedelta
from app.services.transfer_service import TransferService
from app.models.squad_player import SquadPlayer, SquadStatus


class MockSquadPlayer:
    """Mock SquadPlayer for testing without database"""
    
    def __init__(
        self,
        player_id: int,
        wage: int,
        is_listed_for_sale: bool = False,
        asking_price: int = None
    ):
        self.player_id = player_id
        self.wage = wage
        self.is_listed_for_sale = is_listed_for_sale
        self.asking_price = asking_price
    
    def list_for_sale(self, asking_price: int) -> None:
        """List player for sale"""
        if asking_price < 0:
            raise ValueError("Asking price cannot be negative")
        self.is_listed_for_sale = True
        self.asking_price = asking_price
    
    def unlist_from_sale(self) -> None:
        """Unlist player from sale"""
        self.is_listed_for_sale = False
        self.asking_price = None


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


@pytest.fixture
def squad_player():
    """Create a mock squad player for testing"""
    return MockSquadPlayer(player_id=1, wage=5000)


@pytest.fixture
def listed_squad_player():
    """Create a mock squad player that is already listed"""
    return MockSquadPlayer(
        player_id=2,
        wage=8000,
        is_listed_for_sale=True,
        asking_price=1000000
    )


class TestPlayerListing:
    """Test player listing functionality"""
    
    def test_list_player_for_sale_success(self, transfer_service, squad_player):
        """Test successfully listing a player for sale"""
        asking_price = 1000000
        
        result = transfer_service.list_player_for_sale(squad_player, asking_price)
        
        assert result["player_id"] == squad_player.player_id
        assert result["asking_price"] == asking_price
        assert result["wage"] == squad_player.wage
        assert result["listed"] is True
        assert squad_player.is_listed_for_sale is True
        assert squad_player.asking_price == asking_price
    
    def test_list_player_with_zero_asking_price(self, transfer_service, squad_player):
        """Test listing a player with zero asking price (free transfer)"""
        asking_price = 0
        
        result = transfer_service.list_player_for_sale(squad_player, asking_price)
        
        assert result["asking_price"] == 0
        assert result["listed"] is True
        assert squad_player.is_listed_for_sale is True
        assert squad_player.asking_price == 0
    
    def test_list_player_with_negative_asking_price_fails(
        self, transfer_service, squad_player
    ):
        """Test that listing with negative asking price raises ValueError"""
        asking_price = -100000
        
        with pytest.raises(ValueError, match="Asking price cannot be negative"):
            transfer_service.list_player_for_sale(squad_player, asking_price)
        
        # Player should not be listed
        assert squad_player.is_listed_for_sale is False
    
    def test_list_already_listed_player_fails(
        self, transfer_service, listed_squad_player
    ):
        """Test that listing an already listed player raises ValueError"""
        new_asking_price = 2000000
        
        with pytest.raises(ValueError, match="already listed"):
            transfer_service.list_player_for_sale(listed_squad_player, new_asking_price)
        
        # Original asking price should remain unchanged
        assert listed_squad_player.asking_price == 1000000
    
    def test_list_player_with_high_asking_price(self, transfer_service, squad_player):
        """Test listing a player with a very high asking price"""
        asking_price = 100000000  # 100 million
        
        result = transfer_service.list_player_for_sale(squad_player, asking_price)
        
        assert result["asking_price"] == asking_price
        assert squad_player.asking_price == asking_price


class TestPlayerUnlisting:
    """Test player unlisting functionality"""
    
    def test_unlist_player_from_sale_success(
        self, transfer_service, listed_squad_player
    ):
        """Test successfully unlisting a player from sale"""
        result = transfer_service.unlist_player_from_sale(listed_squad_player)
        
        assert result["player_id"] == listed_squad_player.player_id
        assert result["listed"] is False
        assert "removed from sale" in result["message"].lower()
        assert listed_squad_player.is_listed_for_sale is False
        assert listed_squad_player.asking_price is None
    
    def test_unlist_not_listed_player(self, transfer_service, squad_player):
        """Test unlisting a player that is not listed (should succeed)"""
        result = transfer_service.unlist_player_from_sale(squad_player)
        
        assert result["listed"] is False
        assert squad_player.is_listed_for_sale is False
        assert squad_player.asking_price is None


class TestGetListedPlayers:
    """Test retrieving listed players"""
    
    def test_get_listed_players_with_multiple_players(self, transfer_service):
        """Test getting listed players from a squad with mixed listing status"""
        squad_players = [
            MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000),
            MockSquadPlayer(2, 6000, is_listed_for_sale=False, asking_price=None),
            MockSquadPlayer(3, 7000, is_listed_for_sale=True, asking_price=2000000),
            MockSquadPlayer(4, 8000, is_listed_for_sale=False, asking_price=None),
            MockSquadPlayer(5, 9000, is_listed_for_sale=True, asking_price=3000000),
        ]
        
        listed = transfer_service.get_listed_players(squad_players)
        
        assert len(listed) == 3
        assert all(sp.is_listed_for_sale for sp in listed)
        assert {sp.player_id for sp in listed} == {1, 3, 5}
    
    def test_get_listed_players_with_no_listed_players(self, transfer_service):
        """Test getting listed players when none are listed"""
        squad_players = [
            MockSquadPlayer(1, 5000, is_listed_for_sale=False),
            MockSquadPlayer(2, 6000, is_listed_for_sale=False),
        ]
        
        listed = transfer_service.get_listed_players(squad_players)
        
        assert len(listed) == 0
    
    def test_get_listed_players_with_all_listed(self, transfer_service):
        """Test getting listed players when all are listed"""
        squad_players = [
            MockSquadPlayer(1, 5000, is_listed_for_sale=True, asking_price=1000000),
            MockSquadPlayer(2, 6000, is_listed_for_sale=True, asking_price=2000000),
        ]
        
        listed = transfer_service.get_listed_players(squad_players)
        
        assert len(listed) == 2
    
    def test_get_listed_players_with_empty_squad(self, transfer_service):
        """Test getting listed players from an empty squad"""
        squad_players = []
        
        listed = transfer_service.get_listed_players(squad_players)
        
        assert len(listed) == 0


class TestGetListingDetails:
    """Test getting listing details for a player"""
    
    def test_get_listing_details_for_listed_player(
        self, transfer_service, listed_squad_player
    ):
        """Test getting listing details for a listed player"""
        details = transfer_service.get_listing_details(listed_squad_player)
        
        assert details is not None
        assert details["player_id"] == listed_squad_player.player_id
        assert details["asking_price"] == listed_squad_player.asking_price
        assert details["wage"] == listed_squad_player.wage
        assert details["listed"] is True
    
    def test_get_listing_details_for_not_listed_player(
        self, transfer_service, squad_player
    ):
        """Test getting listing details for a player not listed"""
        details = transfer_service.get_listing_details(squad_player)
        
        assert details is None


class TestValidatePlayerListing:
    """Test player listing validation"""
    
    def test_validate_listing_with_valid_data(self, transfer_service, squad_player):
        """Test validation with valid listing data"""
        is_valid, error_msg = transfer_service.validate_player_listing(
            squad_player, 1000000
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_listing_with_negative_price(
        self, transfer_service, squad_player
    ):
        """Test validation with negative asking price"""
        is_valid, error_msg = transfer_service.validate_player_listing(
            squad_player, -100000
        )
        
        assert is_valid is False
        assert "negative" in error_msg.lower()
    
    def test_validate_listing_with_already_listed_player(
        self, transfer_service, listed_squad_player
    ):
        """Test validation with already listed player"""
        is_valid, error_msg = transfer_service.validate_player_listing(
            listed_squad_player, 2000000
        )
        
        assert is_valid is False
        assert "already listed" in error_msg.lower()
    
    def test_validate_listing_with_zero_price(self, transfer_service, squad_player):
        """Test validation with zero asking price (should be valid)"""
        is_valid, error_msg = transfer_service.validate_player_listing(
            squad_player, 0
        )
        
        assert is_valid is True
        assert error_msg == ""


class TestListingWorkflow:
    """Test complete listing workflows"""
    
    def test_list_and_unlist_workflow(self, transfer_service, squad_player):
        """Test complete workflow of listing and then unlisting a player"""
        # Initially not listed
        assert squad_player.is_listed_for_sale is False
        
        # List the player
        asking_price = 1500000
        list_result = transfer_service.list_player_for_sale(squad_player, asking_price)
        assert list_result["listed"] is True
        assert squad_player.is_listed_for_sale is True
        assert squad_player.asking_price == asking_price
        
        # Verify player appears in listed players
        listed = transfer_service.get_listed_players([squad_player])
        assert len(listed) == 1
        
        # Unlist the player
        unlist_result = transfer_service.unlist_player_from_sale(squad_player)
        assert unlist_result["listed"] is False
        assert squad_player.is_listed_for_sale is False
        assert squad_player.asking_price is None
        
        # Verify player no longer appears in listed players
        listed = transfer_service.get_listed_players([squad_player])
        assert len(listed) == 0
    
    def test_list_multiple_players_workflow(self, transfer_service):
        """Test listing multiple players with different asking prices"""
        players = [
            MockSquadPlayer(1, 5000),
            MockSquadPlayer(2, 6000),
            MockSquadPlayer(3, 7000),
        ]
        
        asking_prices = [1000000, 2000000, 3000000]
        
        # List all players
        for player, price in zip(players, asking_prices):
            transfer_service.list_player_for_sale(player, price)
        
        # Verify all are listed
        listed = transfer_service.get_listed_players(players)
        assert len(listed) == 3
        
        # Verify asking prices
        for player, expected_price in zip(players, asking_prices):
            assert player.asking_price == expected_price
        
        # Unlist one player
        transfer_service.unlist_player_from_sale(players[1])
        
        # Verify only 2 are listed now
        listed = transfer_service.get_listed_players(players)
        assert len(listed) == 2
        assert players[1] not in listed


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_list_player_with_very_low_wage(self, transfer_service):
        """Test listing a player with very low wage"""
        player = MockSquadPlayer(1, 100)  # Very low wage
        asking_price = 50000
        
        result = transfer_service.list_player_for_sale(player, asking_price)
        
        assert result["listed"] is True
        assert result["wage"] == 100
    
    def test_list_player_with_zero_wage(self, transfer_service):
        """Test listing a player with zero wage"""
        player = MockSquadPlayer(1, 0)
        asking_price = 100000
        
        result = transfer_service.list_player_for_sale(player, asking_price)
        
        assert result["listed"] is True
        assert result["wage"] == 0
    
    def test_multiple_list_unlist_cycles(self, transfer_service, squad_player):
        """Test multiple cycles of listing and unlisting"""
        for i in range(3):
            # List
            asking_price = 1000000 * (i + 1)
            transfer_service.list_player_for_sale(squad_player, asking_price)
            assert squad_player.is_listed_for_sale is True
            assert squad_player.asking_price == asking_price
            
            # Unlist
            transfer_service.unlist_player_from_sale(squad_player)
            assert squad_player.is_listed_for_sale is False
            assert squad_player.asking_price is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
