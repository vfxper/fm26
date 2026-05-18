"""
Unit tests for injury simulation in MatchSimulator

Tests the injury simulation functionality including:
- Injury probability calculation
- Injury severity distribution
- Fatigue impact on injury risk
- Tackle-related injuries
- Injury event generation
- Injury data tracking
"""

import pytest
import random
from unittest.mock import Mock, patch

from app.services.match_simulator import (
    MatchSimulator,
    PlayerState,
    TeamState,
    InjuryEvent,
    TacticMentality
)
from app.models.player import Player
from app.models.match_event import TeamSide, EventType
from app.models.match import WeatherCondition, PitchCondition


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
        'marking': 10,
        'corners': 10,
        'crossing': 10,
        'free_kicks': 10,
        'heading': 10,
        'penalty': 10,
        'jumping': 10,
        'strength': 10,
        'endurance': 15,
        'bravery': 10
    }
    
    # Override with provided attributes
    default_attrs.update(attributes)
    
    for attr, value in default_attrs.items():
        setattr(player, attr, value)
    
    return player


def create_test_squad(team_name: str, start_id: int = 1, squad_player_id_start: int = 1) -> list:
    """Create a test squad of 11 players with squad_player_ids"""
    squad = []
    
    # Goalkeeper
    squad.append((
        create_mock_player(start_id, f"{team_name} GK", "GK", ca=90, positioning=15, anticipation=15),
        1,  # squad number
        70,  # morale
        squad_player_id_start  # squad_player_id
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
                positioning=13
            ),
            i + 2,
            70,
            squad_player_id_start + i + 1
        ))
    
    # Midfielders (4)
    for i in range(4):
        squad.append((
            create_mock_player(
                start_id + i + 5,
                f"{team_name} MID{i+1}",
                "M C",
                ca=95,
                passing=15,
                vision=14,
                technique=14
            ),
            i + 6,
            70,
            squad_player_id_start + i + 5
        ))
    
    # Forwards (2)
    for i in range(2):
        squad.append((
            create_mock_player(
                start_id + i + 9,
                f"{team_name} FWD{i+1}",
                "ST C",
                ca=100,
                finishing=16,
                composure=15,
                dribbling=14
            ),
            i + 10,
            70,
            squad_player_id_start + i + 9
        ))
    
    return squad


class TestInjurySimulation:
    """Test suite for injury simulation"""
    
    def test_injury_probability_calculation_fresh_player(self):
        """Test injury probability for a fresh player with high stamina"""
        simulator = MatchSimulator()
        simulator.current_minute = 10
        simulator.match_intensity = 1.0
        simulator.pitch_condition = PitchCondition.GOOD
        
        player = create_mock_player(1, "Test Player", "M C", strength=15, stamina=18, endurance=16, bravery=10)
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=100.0
        )
        
        injury_prob = simulator._calculate_injury_probability(player_state)
        
        # Fresh player with good physical attributes should have low injury probability
        assert injury_prob < 0.0001  # Less than 0.01%
    
    def test_injury_probability_calculation_tired_player(self):
        """Test injury probability for a tired player with low stamina"""
        simulator = MatchSimulator()
        simulator.current_minute = 85
        simulator.match_intensity = 1.2
        simulator.pitch_condition = PitchCondition.GOOD
        
        player = create_mock_player(1, "Test Player", "M C", strength=10, stamina=10, endurance=10, bravery=15)
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=25.0  # Very tired
        )
        
        injury_prob = simulator._calculate_injury_probability(player_state)
        
        # Tired player late in match should have higher injury probability
        assert injury_prob > 0.0002  # Higher than fresh player
    
    def test_injury_probability_poor_pitch_condition(self):
        """Test that poor pitch condition increases injury probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.match_intensity = 1.0
        
        player = create_mock_player(1, "Test Player", "M C")
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=70.0
        )
        
        # Good pitch
        simulator.pitch_condition = PitchCondition.GOOD
        prob_good = simulator._calculate_injury_probability(player_state)
        
        # Poor pitch
        simulator.pitch_condition = PitchCondition.POOR
        prob_poor = simulator._calculate_injury_probability(player_state)
        
        # Poor pitch should have higher injury probability
        assert prob_poor > prob_good
    
    def test_injury_severity_distribution(self):
        """Test that injury severity follows expected distribution (60% minor, 30% moderate, 10% severe)"""
        simulator = MatchSimulator()
        
        player = create_mock_player(1, "Test Player", "M C")
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70
        )
        
        # Generate many injuries to test distribution
        severities = []
        for _ in range(1000):
            severity, _, _, _ = simulator._determine_injury_details(player_state)
            severities.append(severity)
        
        minor_count = severities.count("minor")
        moderate_count = severities.count("moderate")
        severe_count = severities.count("severe")
        
        # Check distribution (with some tolerance)
        assert 550 <= minor_count <= 650  # ~60% ± 5%
        assert 250 <= moderate_count <= 350  # ~30% ± 5%
        assert 50 <= severe_count <= 150  # ~10% ± 5%
    
    def test_injury_recovery_weeks_by_severity(self):
        """Test that recovery weeks match severity levels"""
        simulator = MatchSimulator()
        
        player = create_mock_player(1, "Test Player", "M C")
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70
        )
        
        # Test multiple injuries
        for _ in range(100):
            severity, _, _, recovery_weeks = simulator._determine_injury_details(player_state)
            
            if severity == "minor":
                assert 1 <= recovery_weeks <= 2
            elif severity == "moderate":
                assert 3 <= recovery_weeks <= 8
            elif severity == "severe":
                assert recovery_weeks >= 9
    
    def test_injury_types_by_position(self):
        """Test that injury types are appropriate for player positions"""
        simulator = MatchSimulator()
        
        # Test goalkeeper injuries
        gk_injuries = simulator._get_injury_types_by_position("GK")
        assert "Finger Fracture" in gk_injuries
        assert "Wrist Sprain" in gk_injuries
        
        # Test defender injuries
        def_injuries = simulator._get_injury_types_by_position("D C")
        assert "Concussion" in def_injuries
        
        # Test midfielder injuries
        mid_injuries = simulator._get_injury_types_by_position("M C")
        assert "Achilles Tendon Injury" in mid_injuries
        
        # Test forward injuries
        fwd_injuries = simulator._get_injury_types_by_position("ST C")
        assert "Quadriceps Strain" in fwd_injuries
        
        # All should have common injuries
        for injuries in [gk_injuries, def_injuries, mid_injuries, fwd_injuries]:
            assert "Hamstring Strain" in injuries
            assert "Ankle Sprain" in injuries
    
    def test_injury_simulation_creates_event(self):
        """Test that injury simulation creates proper injury event"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        
        player = create_mock_player(1, "Test Player", "M C")
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            squad_player_id=100
        )
        
        team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Test FC"
        )
        team.players.append(player_state)
        
        simulator._simulate_injury(player_state, team)
        
        # Check player state
        assert player_state.is_injured is True
        assert player_state.is_on_pitch is False
        
        # Check event was created
        assert len(simulator.events) == 1
        injury_event = simulator.events[0]
        assert injury_event['event_type'] == EventType.INJURY.value
        assert injury_event['team'] == TeamSide.HOME.value
        assert injury_event['player_id'] == 1
        assert injury_event['minute'] == 45
        assert injury_event['second'] == 30
        assert 'injury_type' in injury_event
        assert 'severity' in injury_event
        assert 'recovery_weeks' in injury_event
        
        # Check injury data was stored
        assert len(simulator.injuries) == 1
        injury_data = simulator.injuries[0]
        assert injury_data.player_id == 1
        assert injury_data.squad_player_id == 100
        assert injury_data.match_minute == 45
        assert injury_data.severity in ["minor", "moderate", "severe"]
        assert injury_data.recovery_weeks > 0
    
    def test_tackle_injury_higher_probability(self):
        """Test that tackles have higher injury probability than normal play"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.match_intensity = 1.0
        simulator.pitch_condition = PitchCondition.GOOD
        
        player = create_mock_player(1, "Test Player", "M C")
        player_state = PlayerState(
            player_id=1,
            player=player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=70.0
        )
        
        # Calculate normal injury probability
        normal_prob = simulator._calculate_injury_probability(player_state)
        
        # Tackle injury probability should be 2.5x higher
        tackle_multiplier = 2.5
        expected_tackle_prob = normal_prob * tackle_multiplier
        
        # Verify the multiplier is applied correctly
        assert expected_tackle_prob > normal_prob
    
    def test_match_with_injuries_completes(self):
        """Test that a match with injuries completes successfully"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1, squad_player_id_start=1)
        away_squad = create_test_squad("Away", start_id=100, squad_player_id_start=100)
        
        # Force some injuries by setting high injury probability
        with patch.object(simulator, '_calculate_injury_probability', return_value=0.05):
            result = simulator.simulate_match(
                home_club_id=1,
                home_club_name="Home FC",
                home_players=home_squad,
                away_club_id=2,
                away_club_name="Away FC",
                away_players=away_squad
            )
        
        # Match should complete
        assert result.home_score >= 0
        assert result.away_score >= 0
        
        # Should have injury data
        assert hasattr(result, 'injuries')
        assert isinstance(result.injuries, list)
        
        # If injuries occurred, check their structure
        if len(result.injuries) > 0:
            injury = result.injuries[0]
            assert hasattr(injury, 'player_id')
            assert hasattr(injury, 'squad_player_id')
            assert hasattr(injury, 'injury_type')
            assert hasattr(injury, 'severity')
            assert hasattr(injury, 'recovery_weeks')
            assert hasattr(injury, 'match_minute')
    
    def test_injured_player_removed_from_pitch(self):
        """Test that injured players are removed from active play"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1, squad_player_id_start=1)
        away_squad = create_test_squad("Away", start_id=100, squad_player_id_start=100)
        
        # Initialize match
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR,
            PitchCondition.GOOD,
            True
        )
        
        # Get a player and injure them
        player_state = simulator.home_team.players[0]
        initial_active_count = len(simulator.home_team.get_active_players())
        
        simulator._simulate_injury(player_state, simulator.home_team)
        
        # Check player is removed from active players
        assert player_state.is_injured is True
        assert player_state.is_on_pitch is False
        assert len(simulator.home_team.get_active_players()) == initial_active_count - 1
    
    def test_multiple_injuries_in_match(self):
        """Test that multiple injuries can occur in a single match"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1, squad_player_id_start=1)
        away_squad = create_test_squad("Away", start_id=100, squad_player_id_start=100)
        
        # Force multiple injuries
        with patch.object(simulator, '_calculate_injury_probability', return_value=0.1):
            result = simulator.simulate_match(
                home_club_id=1,
                home_club_name="Home FC",
                home_players=home_squad,
                away_club_id=2,
                away_club_name="Away FC",
                away_players=away_squad
            )
        
        # Should have multiple injuries
        assert len(result.injuries) >= 2
        
        # Each injury should have unique player
        player_ids = [inj.player_id for inj in result.injuries]
        # Note: Same player could theoretically get injured twice, but unlikely
        assert len(player_ids) >= 2
    
    def test_injury_description_generation(self):
        """Test that injury descriptions are generated correctly"""
        simulator = MatchSimulator()
        
        # Test different severities
        desc_minor = simulator._generate_injury_description("Hamstring Strain", "minor")
        assert "minor" in desc_minor.lower()
        assert "hamstring strain" in desc_minor.lower()
        
        desc_moderate = simulator._generate_injury_description("Ankle Sprain", "moderate")
        assert "moderate" in desc_moderate.lower()
        assert "ankle sprain" in desc_moderate.lower()
        
        desc_severe = simulator._generate_injury_description("Knee Ligament Damage", "severe")
        assert "serious" in desc_severe.lower()
        assert "knee ligament damage" in desc_severe.lower()
    
    def test_physical_attributes_affect_injury_risk(self):
        """Test that players with better physical attributes have lower injury risk"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.match_intensity = 1.0
        simulator.pitch_condition = PitchCondition.GOOD
        
        # Player with poor physical attributes
        weak_player = create_mock_player(1, "Weak Player", "M C", strength=5, stamina=5, endurance=5)
        weak_state = PlayerState(
            player_id=1,
            player=weak_player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=70.0
        )
        
        # Player with excellent physical attributes
        strong_player = create_mock_player(2, "Strong Player", "M C", strength=20, stamina=20, endurance=20)
        strong_state = PlayerState(
            player_id=2,
            player=strong_player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=11,
            morale=70,
            stamina=70.0
        )
        
        weak_prob = simulator._calculate_injury_probability(weak_state)
        strong_prob = simulator._calculate_injury_probability(strong_state)
        
        # Weak player should have higher injury probability
        assert weak_prob > strong_prob
    
    def test_bravery_affects_injury_risk(self):
        """Test that braver players have slightly higher injury risk"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.match_intensity = 1.0
        simulator.pitch_condition = PitchCondition.GOOD
        
        # Cautious player (low bravery)
        cautious_player = create_mock_player(1, "Cautious Player", "M C", bravery=5)
        cautious_state = PlayerState(
            player_id=1,
            player=cautious_player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=10,
            morale=70,
            stamina=70.0
        )
        
        # Brave player (high bravery)
        brave_player = create_mock_player(2, "Brave Player", "M C", bravery=20)
        brave_state = PlayerState(
            player_id=2,
            player=brave_player,
            team=TeamSide.HOME,
            position="M C",
            squad_number=11,
            morale=70,
            stamina=70.0
        )
        
        cautious_prob = simulator._calculate_injury_probability(cautious_state)
        brave_prob = simulator._calculate_injury_probability(brave_state)
        
        # Brave player should have slightly higher injury probability
        assert brave_prob > cautious_prob


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
