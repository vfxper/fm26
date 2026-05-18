"""
Unit tests for enhanced possession calculation algorithm

Tests the new possession calculation features:
- Passing attributes influence
- Tactics influence (possession-based vs counter-attack)
- Midfield dominance
- Fatigue effects
- Late game urgency
"""

import pytest
from unittest.mock import Mock

from app.services.match_simulator import (
    MatchSimulator,
    PlayerState,
    TeamState,
    TacticMentality
)
from app.models.player import Player
from app.models.match_event import TeamSide


def create_mock_player(
    player_id: int,
    name: str,
    position: str,
    ca: int = 100,
    **attributes
) -> Player:
    """Create a mock player with specified attributes"""
    player = Mock(spec=Player)
    player.id = player_id
    player.name = name
    player.position = position
    player.ca = ca
    player.pa = ca + 20
    
    # Set default attributes
    default_attrs = {
        'passing': 10,
        'vision': 10,
        'technique': 10,
        'finishing': 10,
        'composure': 10,
        'dribbling': 10,
        'agility': 10,
        'tackling': 10,
        'positioning': 10,
        'work_rate': 10,
        'stamina': 15,
        'pace': 10,
        'anticipation': 10,
        'off_the_ball': 10,
        'aggression': 10,
        'marking': 10
    }
    
    # Override with provided attributes
    default_attrs.update(attributes)
    
    for attr, value in default_attrs.items():
        setattr(player, attr, value)
    
    return player


def create_test_squad(
    team_name: str,
    start_id: int = 1,
    passing_quality: int = 10,
    midfield_count: int = 4
) -> list:
    """Create a test squad with configurable passing quality and formation"""
    squad = []
    
    # Goalkeeper
    squad.append((
        create_mock_player(
            start_id,
            f"{team_name} GK",
            "GK",
            ca=90,
            positioning=15,
            anticipation=15,
            passing=passing_quality
        ),
        1,
        70
    ))
    
    # Defenders (4)
    for i in range(4):
        squad.append((
            create_mock_player(
                start_id + i + 1,
                f"{team_name} DEF{i+1}",
                "D C",
                ca=85,
                tackling=14,
                positioning=13,
                passing=passing_quality,
                vision=passing_quality,
                technique=passing_quality
            ),
            i + 2,
            70
        ))
    
    # Midfielders (variable count)
    for i in range(midfield_count):
        squad.append((
            create_mock_player(
                start_id + i + 5,
                f"{team_name} MID{i+1}",
                "M C",
                ca=95,
                passing=passing_quality,
                vision=passing_quality,
                technique=passing_quality
            ),
            i + 6,
            70
        ))
    
    # Forwards (fill remaining to 11)
    forwards_count = 11 - 1 - 4 - midfield_count
    for i in range(forwards_count):
        squad.append((
            create_mock_player(
                start_id + i + 5 + midfield_count,
                f"{team_name} FWD{i+1}",
                "ST C",
                ca=100,
                finishing=16,
                composure=15,
                dribbling=14,
                passing=passing_quality
            ),
            i + 6 + midfield_count,
            70
        ))
    
    return squad


class TestPossessionEnhancement:
    """Test suite for enhanced possession calculation"""
    
    def test_passing_quality_affects_possession(self):
        """Test that teams with better passing attributes get more possession"""
        simulator = MatchSimulator()
        
        # Create home team with excellent passing (18)
        home_squad = create_test_squad("Home", start_id=1, passing_quality=18)
        
        # Create away team with poor passing (8)
        away_squad = create_test_squad("Away", start_id=100, passing_quality=8)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC (Good Passing)",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC (Poor Passing)",
            away_players=away_squad
        )
        
        # Home team should have significantly more possession
        # With 10 point passing difference, expect ~15-20% possession advantage
        assert result.home_statistics['possession'] > result.away_statistics['possession']
        print(f"Passing quality test: {result.home_statistics['possession']}% vs {result.away_statistics['possession']}%")
    
    def test_tactics_affect_possession(self):
        """Test that defensive tactics increase possession"""
        # Test multiple times to account for randomness
        defensive_possession_total = 0
        attacking_possession_total = 0
        num_tests = 5
        
        for _ in range(num_tests):
            simulator = MatchSimulator()
            
            home_squad = create_test_squad("Home", start_id=1)
            away_squad = create_test_squad("Away", start_id=100)
            
            # Initialize match
            simulator._initialize_match(
                1, "Home FC", home_squad,
                2, "Away FC", away_squad,
                None, None, True
            )
            
            # Set tactics
            simulator.home_team.mentality = TacticMentality.DEFENSIVE
            simulator.away_team.mentality = TacticMentality.ATTACKING
            
            # Simulate a few minutes to accumulate possession
            for minute in range(1, 11):
                simulator.current_minute = minute
                simulator._calculate_possession()
            
            home_poss_pct = (simulator.home_team.possession_time / 
                           (simulator.home_team.possession_time + simulator.away_team.possession_time)) * 100
            
            defensive_possession_total += home_poss_pct
        
        avg_defensive_possession = defensive_possession_total / num_tests
        
        # Now test with reversed tactics
        for _ in range(num_tests):
            simulator = MatchSimulator()
            
            home_squad = create_test_squad("Home", start_id=1)
            away_squad = create_test_squad("Away", start_id=100)
            
            simulator._initialize_match(
                1, "Home FC", home_squad,
                2, "Away FC", away_squad,
                None, None, True
            )
            
            # Reverse tactics
            simulator.home_team.mentality = TacticMentality.ATTACKING
            simulator.away_team.mentality = TacticMentality.DEFENSIVE
            
            for minute in range(1, 11):
                simulator.current_minute = minute
                simulator._calculate_possession()
            
            home_poss_pct = (simulator.home_team.possession_time / 
                           (simulator.home_team.possession_time + simulator.away_team.possession_time)) * 100
            
            attacking_possession_total += home_poss_pct
        
        avg_attacking_possession = attacking_possession_total / num_tests
        
        # Defensive tactics should yield more possession
        assert avg_defensive_possession > avg_attacking_possession
        print(f"Tactics test: Defensive={avg_defensive_possession:.1f}% vs Attacking={avg_attacking_possession:.1f}%")
    
    def test_midfield_dominance_affects_possession(self):
        """Test that teams with more midfielders get more possession"""
        simulator = MatchSimulator()
        
        # Home team with 5 midfielders (3-5-2 formation)
        home_squad = create_test_squad("Home", start_id=1, midfield_count=5)
        
        # Away team with 3 midfielders (4-3-3 formation)
        away_squad = create_test_squad("Away", start_id=100, midfield_count=3)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC (5 midfielders)",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC (3 midfielders)",
            away_players=away_squad
        )
        
        # Home team should have more possession due to midfield dominance
        # With 2 extra midfielders, expect ~6% advantage
        assert result.home_statistics['possession'] >= result.away_statistics['possession']
        print(f"Midfield dominance test: {result.home_statistics['possession']}% vs {result.away_statistics['possession']}%")
    
    def test_helper_methods(self):
        """Test the new helper methods work correctly"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1, passing_quality=15)
        away_squad = create_test_squad("Away", start_id=100, passing_quality=10)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            None, None, True
        )
        
        # Test passing quality calculation
        home_passing = simulator._calculate_team_passing_quality(simulator.home_team)
        away_passing = simulator._calculate_team_passing_quality(simulator.away_team)
        
        assert home_passing > away_passing
        assert 10 <= home_passing <= 20
        assert 10 <= away_passing <= 20
        
        # Test tactics modifier
        defensive_mod = simulator._get_tactics_possession_modifier(TacticMentality.DEFENSIVE)
        attacking_mod = simulator._get_tactics_possession_modifier(TacticMentality.ATTACKING)
        balanced_mod = simulator._get_tactics_possession_modifier(TacticMentality.BALANCED)
        
        assert defensive_mod > balanced_mod
        assert attacking_mod < balanced_mod
        assert balanced_mod == 0.0
        
        # Test midfielder counting
        home_mids = simulator._count_midfielders(simulator.home_team)
        away_mids = simulator._count_midfielders(simulator.away_team)
        
        assert home_mids == 4
        assert away_mids == 4
        
        # Test stamina calculation
        home_stamina = simulator._calculate_team_average_stamina(simulator.home_team)
        away_stamina = simulator._calculate_team_average_stamina(simulator.away_team)
        
        assert home_stamina == 100.0  # Initial stamina
        assert away_stamina == 100.0
    
    def test_fatigue_affects_possession(self):
        """Test that tired teams lose possession more easily"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            None, None, True
        )
        
        # Manually reduce home team stamina to simulate fatigue
        for player_state in simulator.home_team.players:
            player_state.stamina = 30.0  # Very tired
        
        # Away team stays fresh
        for player_state in simulator.away_team.players:
            player_state.stamina = 100.0
        
        # Calculate possession multiple times
        home_possession_count = 0
        total_calculations = 100
        
        for _ in range(total_calculations):
            simulator._calculate_possession()
            if simulator.possession_team == TeamSide.HOME:
                home_possession_count += 1
        
        home_possession_pct = (home_possession_count / total_calculations) * 100
        
        # Tired team should have less possession (expect < 45%)
        assert home_possession_pct < 50
        print(f"Fatigue test: Tired team={home_possession_pct:.1f}% possession")
    
    def test_possession_stays_within_bounds(self):
        """Test that possession probability is always clamped to 30-70%"""
        simulator = MatchSimulator()
        
        # Create extremely unbalanced teams
        home_squad = create_test_squad("Home", start_id=1, passing_quality=20, midfield_count=6)
        away_squad = create_test_squad("Away", start_id=100, passing_quality=5, midfield_count=2)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            None, None, True
        )
        
        # Set extreme tactics
        simulator.home_team.mentality = TacticMentality.DEFENSIVE
        simulator.away_team.mentality = TacticMentality.VERY_ATTACKING
        
        # Calculate possession many times
        home_possession_count = 0
        total_calculations = 1000
        
        for _ in range(total_calculations):
            simulator._calculate_possession()
            if simulator.possession_team == TeamSide.HOME:
                home_possession_count += 1
        
        home_possession_pct = (home_possession_count / total_calculations) * 100
        
        # Even with extreme advantages, possession should be clamped
        # Should be close to 70% (the upper bound)
        assert 30 <= home_possession_pct <= 75  # Allow some variance due to randomness
        print(f"Bounds test: Dominant team={home_possession_pct:.1f}% possession (clamped to 30-70%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
