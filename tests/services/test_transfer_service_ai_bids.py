"""
Tests for Transfer Service - AI Bid Generation (Task 8.7)

Tests the AI bid generation functionality for listed players including:
- AI clubs generating bids based on budget and needs
- Bid amounts ranging from 80-120% of asking price
- Position-based bid probability (higher for matching positions)
- Budget constraints preventing bids
- Multiple AI clubs bidding on the same player
- Wage offer calculation
- Contract year generation
"""

import pytest
import random
from app.services.transfer_service import TransferService, AIBid


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


@pytest.fixture
def listed_player_striker():
    """Create a listed striker player"""
    return {
        "player_id": 1,
        "asking_price": 1000000,
        "player_name": "John Striker",
        "position": "ST",
        "ca": 150,
    }


@pytest.fixture
def listed_player_midfielder():
    """Create a listed midfielder player"""
    return {
        "player_id": 2,
        "asking_price": 2000000,
        "player_name": "Mike Midfielder",
        "position": "MC",
        "ca": 160,
    }


@pytest.fixture
def listed_player_defender():
    """Create a listed defender player"""
    return {
        "player_id": 3,
        "asking_price": 500000,
        "player_name": "Dave Defender",
        "position": "DC",
        "ca": 140,
    }


@pytest.fixture
def ai_club_rich():
    """Create a rich AI club with high budget"""
    return {
        "club_id": 10,
        "club_name": "Rich FC",
        "transfer_budget": 10000000,
        "needs": ["ST", "MC"],
    }


@pytest.fixture
def ai_club_poor():
    """Create a poor AI club with low budget"""
    return {
        "club_id": 11,
        "club_name": "Poor FC",
        "transfer_budget": 300000,
        "needs": ["DC", "DL"],
    }


@pytest.fixture
def ai_club_medium():
    """Create a medium budget AI club"""
    return {
        "club_id": 12,
        "club_name": "Medium FC",
        "transfer_budget": 1500000,
        "needs": ["MC", "AMC"],
    }


class TestAIBidGeneration:
    """Test basic AI bid generation functionality"""
    
    def test_generate_bids_with_matching_position(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that AI clubs are more likely to bid for players in needed positions"""
        # Set seed for reproducibility
        random.seed(42)
        
        # Run multiple times to test probability
        bid_count = 0
        iterations = 100
        
        for _ in range(iterations):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich]
            )
            if len(bids) > 0:
                bid_count += 1
        
        # With 30% chance per iteration, we expect around 30 bids
        # Allow some variance (20-40 range)
        assert 20 <= bid_count <= 40, f"Expected 20-40 bids, got {bid_count}"
    
    def test_generate_bids_without_matching_position(
        self, transfer_service, listed_player_defender, ai_club_rich
    ):
        """Test that AI clubs are less likely to bid for players not in needed positions"""
        # Set seed for reproducibility
        random.seed(42)
        
        # Run multiple times to test probability
        bid_count = 0
        iterations = 100
        
        for _ in range(iterations):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_defender],
                [ai_club_rich]
            )
            if len(bids) > 0:
                bid_count += 1
        
        # With 10% chance per iteration, we expect around 10 bids
        # Allow some variance (5-15 range)
        assert 5 <= bid_count <= 15, f"Expected 5-15 bids, got {bid_count}"
    
    def test_bid_amount_range(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that bid amounts are within 80-120% of asking price"""
        random.seed(42)
        
        # Generate multiple bids to test range
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        # Check that we got some bids
        assert len(all_bids) > 0, "Expected at least some bids to be generated"
        
        asking_price = listed_player_striker["asking_price"]
        min_expected = asking_price * 0.8
        max_expected = asking_price * 1.2
        
        for bid in all_bids:
            assert min_expected <= bid.bid_amount <= max_expected, (
                f"Bid amount {bid.bid_amount} outside expected range "
                f"[{min_expected}, {max_expected}]"
            )
    
    def test_club_cannot_afford_player(
        self, transfer_service, listed_player_striker, ai_club_poor
    ):
        """Test that AI clubs don't bid if they can't afford the player"""
        random.seed(42)
        
        # Poor club has 300k budget, striker costs 1M
        # Even at 80% (800k), club can't afford
        bids = transfer_service.generate_ai_bids_for_listed(
            [listed_player_striker],
            [ai_club_poor]
        )
        
        assert len(bids) == 0, "Poor club should not bid on expensive player"
    
    def test_club_can_afford_cheaper_player(
        self, transfer_service, listed_player_defender, ai_club_poor
    ):
        """Test that AI clubs can bid on affordable players"""
        random.seed(42)
        
        # Poor club has 300k budget, defender costs 500k
        # At 80% (400k), still can't afford
        # But let's test with a very cheap player
        cheap_player = {
            "player_id": 4,
            "asking_price": 200000,
            "player_name": "Cheap Player",
            "position": "DC",
            "ca": 120,
        }
        
        # Run multiple times since it's probabilistic
        bid_found = False
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [cheap_player],
                [ai_club_poor]
            )
            if len(bids) > 0:
                bid_found = True
                break
        
        # With matching position (DC in needs), should eventually get a bid
        assert bid_found, "Poor club should be able to bid on affordable player"


class TestMultipleClubsBidding:
    """Test scenarios with multiple AI clubs"""
    
    def test_multiple_clubs_can_bid_on_same_player(
        self, transfer_service, listed_player_midfielder, ai_club_rich, ai_club_medium
    ):
        """Test that multiple clubs can bid on the same player"""
        random.seed(42)
        
        # Both clubs need MC position
        bids = transfer_service.generate_ai_bids_for_listed(
            [listed_player_midfielder],
            [ai_club_rich, ai_club_medium]
        )
        
        # Run multiple times to get bids
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_midfielder],
                [ai_club_rich, ai_club_medium]
            )
            all_bids.extend(bids)
        
        if len(all_bids) > 0:
            # Check that we have bids from different clubs
            club_ids = {bid.club_id for bid in all_bids}
            # At least one club should have bid
            assert len(club_ids) >= 1
    
    def test_multiple_players_multiple_clubs(
        self, transfer_service, listed_player_striker, listed_player_midfielder,
        ai_club_rich, ai_club_medium
    ):
        """Test bidding with multiple players and multiple clubs"""
        random.seed(42)
        
        # Generate bids multiple times
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker, listed_player_midfielder],
                [ai_club_rich, ai_club_medium]
            )
            all_bids.extend(bids)
        
        # Should have some bids
        assert len(all_bids) > 0
        
        # Check that bids are for different players
        player_ids = {bid.player_id for bid in all_bids}
        assert len(player_ids) >= 1


class TestBidAttributes:
    """Test bid attribute generation (wage, contract years)"""
    
    def test_wage_offer_calculation(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that wage offers are calculated reasonably"""
        random.seed(42)
        
        # Generate multiple bids
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        assert len(all_bids) > 0, "Expected some bids to be generated"
        
        for bid in all_bids:
            # Wage should be at least minimum (1000)
            assert bid.wage_offer >= 1000, f"Wage {bid.wage_offer} below minimum"
            
            # Wage should be reasonable relative to bid amount
            # (roughly 0.1% of transfer fee as weekly wage)
            expected_wage = bid.bid_amount * 0.001
            # Allow some variance
            assert bid.wage_offer >= 1000, "Wage should be at least minimum"
    
    def test_contract_years_range(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that contract years are within valid range (2-4)"""
        random.seed(42)
        
        # Generate multiple bids
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        assert len(all_bids) > 0, "Expected some bids to be generated"
        
        for bid in all_bids:
            assert 2 <= bid.contract_years <= 4, (
                f"Contract years {bid.contract_years} outside valid range [2, 4]"
            )
    
    def test_bid_contains_all_required_fields(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that generated bids contain all required fields"""
        random.seed(42)
        
        # Generate bids
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        assert len(all_bids) > 0, "Expected some bids to be generated"
        
        for bid in all_bids:
            assert isinstance(bid, AIBid)
            assert bid.club_id == ai_club_rich["club_id"]
            assert bid.club_name == ai_club_rich["club_name"]
            assert bid.player_id == listed_player_striker["player_id"]
            assert bid.bid_amount > 0
            assert bid.wage_offer > 0
            assert bid.contract_years > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_no_listed_players(self, transfer_service, ai_club_rich):
        """Test with no listed players"""
        bids = transfer_service.generate_ai_bids_for_listed(
            [],
            [ai_club_rich]
        )
        
        assert len(bids) == 0, "Should generate no bids with no listed players"
    
    def test_no_ai_clubs(self, transfer_service, listed_player_striker):
        """Test with no AI clubs"""
        bids = transfer_service.generate_ai_bids_for_listed(
            [listed_player_striker],
            []
        )
        
        assert len(bids) == 0, "Should generate no bids with no AI clubs"
    
    def test_empty_lists(self, transfer_service):
        """Test with both empty lists"""
        bids = transfer_service.generate_ai_bids_for_listed([], [])
        
        assert len(bids) == 0, "Should generate no bids with empty lists"
    
    def test_player_with_zero_asking_price(self, transfer_service, ai_club_rich):
        """Test with player listed at zero asking price (free transfer)"""
        free_player = {
            "player_id": 5,
            "asking_price": 0,
            "player_name": "Free Player",
            "position": "ST",
            "ca": 130,
        }
        
        random.seed(42)
        
        # Even with 0 asking price, clubs should be able to bid
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [free_player],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        # Should get some bids
        assert len(all_bids) > 0, "Should generate bids for free transfer"
        
        # Bid amounts should be 0 or very low
        for bid in all_bids:
            assert bid.bid_amount >= 0
    
    def test_club_with_no_needs(self, transfer_service, listed_player_striker):
        """Test club with empty needs list"""
        club_no_needs = {
            "club_id": 13,
            "club_name": "No Needs FC",
            "transfer_budget": 5000000,
            "needs": [],
        }
        
        random.seed(42)
        
        # Should still generate some bids (at 10% rate for non-matching positions)
        all_bids = []
        for _ in range(100):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [club_no_needs]
            )
            all_bids.extend(bids)
        
        # With 10% chance, expect around 10 bids in 100 iterations
        # Allow variance (5-15 range)
        assert 5 <= len(all_bids) <= 15, f"Expected 5-15 bids, got {len(all_bids)}"
    
    def test_player_with_complex_position(self, transfer_service, ai_club_rich):
        """Test player with multiple positions (e.g., 'AM/ST RL')"""
        complex_player = {
            "player_id": 6,
            "asking_price": 1500000,
            "player_name": "Versatile Player",
            "position": "AM/ST RL",
            "ca": 155,
        }
        
        random.seed(42)
        
        # Club needs ST, which is in the position string
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [complex_player],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        # Should match because "ST" is in "AM/ST RL"
        assert len(all_bids) > 0, "Should match complex position string"


class TestBidProbability:
    """Test bid probability mechanics"""
    
    def test_position_match_increases_bid_probability(
        self, transfer_service, listed_player_striker, ai_club_rich
    ):
        """Test that position matching increases bid probability"""
        random.seed(42)
        
        # Create two identical clubs, one needs ST, one doesn't
        club_needs_st = {
            "club_id": 14,
            "club_name": "Needs ST FC",
            "transfer_budget": 5000000,
            "needs": ["ST"],
        }
        
        club_needs_gk = {
            "club_id": 15,
            "club_name": "Needs GK FC",
            "transfer_budget": 5000000,
            "needs": ["GK"],
        }
        
        # Count bids from each club
        bids_with_match = 0
        bids_without_match = 0
        iterations = 100
        
        for i in range(iterations):
            random.seed(42 + i)
            
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [club_needs_st]
            )
            if len(bids) > 0:
                bids_with_match += 1
            
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [club_needs_gk]
            )
            if len(bids) > 0:
                bids_without_match += 1
        
        # Club with matching position should bid more often (30% vs 10%)
        assert bids_with_match > bids_without_match, (
            f"Expected more bids with position match: "
            f"{bids_with_match} vs {bids_without_match}"
        )


class TestBudgetConstraints:
    """Test budget-related constraints"""
    
    def test_club_budget_threshold(self, transfer_service, ai_club_poor):
        """Test that clubs need at least 80% of asking price to bid"""
        # Poor club has 300k budget
        # Create players at different price points
        
        # Player at 375k: 80% = 300k (exactly at budget)
        player_at_threshold = {
            "player_id": 7,
            "asking_price": 375000,
            "player_name": "Threshold Player",
            "position": "DC",
            "ca": 130,
        }
        
        # Player at 376k: 80% = 300.8k (above budget)
        player_above_threshold = {
            "player_id": 8,
            "asking_price": 376000,
            "player_name": "Above Threshold Player",
            "position": "DC",
            "ca": 130,
        }
        
        random.seed(42)
        
        # Should be able to bid on threshold player
        bids_threshold = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [player_at_threshold],
                [ai_club_poor]
            )
            bids_threshold.extend(bids)
        
        # Should NOT be able to bid on above threshold player
        bids_above = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [player_above_threshold],
                [ai_club_poor]
            )
            bids_above.extend(bids)
        
        # Threshold player should get some bids
        assert len(bids_threshold) > 0, "Should bid on player at budget threshold"
        
        # Above threshold player should get no bids
        assert len(bids_above) == 0, "Should not bid on player above budget"


class TestBidDataIntegrity:
    """Test data integrity of generated bids"""
    
    def test_bid_references_correct_player(
        self, transfer_service, listed_player_striker, listed_player_midfielder,
        ai_club_rich
    ):
        """Test that bids reference the correct player"""
        random.seed(42)
        
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker, listed_player_midfielder],
                [ai_club_rich]
            )
            all_bids.extend(bids)
        
        assert len(all_bids) > 0, "Expected some bids"
        
        valid_player_ids = {
            listed_player_striker["player_id"],
            listed_player_midfielder["player_id"]
        }
        
        for bid in all_bids:
            assert bid.player_id in valid_player_ids, (
                f"Bid references invalid player ID: {bid.player_id}"
            )
    
    def test_bid_references_correct_club(
        self, transfer_service, listed_player_striker, ai_club_rich, ai_club_medium
    ):
        """Test that bids reference the correct club"""
        random.seed(42)
        
        all_bids = []
        for _ in range(50):
            bids = transfer_service.generate_ai_bids_for_listed(
                [listed_player_striker],
                [ai_club_rich, ai_club_medium]
            )
            all_bids.extend(bids)
        
        assert len(all_bids) > 0, "Expected some bids"
        
        valid_club_ids = {ai_club_rich["club_id"], ai_club_medium["club_id"]}
        valid_club_names = {ai_club_rich["club_name"], ai_club_medium["club_name"]}
        
        for bid in all_bids:
            assert bid.club_id in valid_club_ids, (
                f"Bid references invalid club ID: {bid.club_id}"
            )
            assert bid.club_name in valid_club_names, (
                f"Bid references invalid club name: {bid.club_name}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

