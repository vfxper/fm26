"""
Unit tests for event probability calculation system in MatchSimulator.

Tests verify that event probabilities are correctly calculated based on:
- Player attributes (CA, position-specific attributes)
- Team tactics (mentality)
- Player position (attackers shoot more, defenders tackle more)
- Fatigue level
- Morale
- Match minute (urgency)
"""

import pytest
from app.services.match_simulator import (
    MatchSimulator, PlayerState, TeamState, TacticMentality, EventType, TeamSide
)
from app.models.player import Player
from app.models.match import WeatherCondition, PitchCondition


def create_test_player(
    name: str,
    position: str,
    ca: int = 100,
    finishing: int = 10,
    composure: int = 10,
    passing: int = 10,
    vision: int = 10,
    tackling: int = 10,
    aggression: int = 10,
    off_the_ball: int = 10
) -> Player:
    """Create a test player with specified attributes"""
    player = Player(
        uid=f"test_{name}",
        name=name,
        position=position,
        age=25,
        ca=ca,
        pa=120,
        nationality="Test",
        club="Test FC",
        # Technical
        corners=10, crossing=10, dribbling=10, finishing=finishing,
        first_touch=10, free_kicks=10, heading=10, long_shots=10,
        long_throws=10, marking=10, passing=passing, penalty=10,
        tackling=tackling, technique=10,
        # Mental
        aggression=aggression, anticipation=10, bravery=10, composure=composure,
        concentration=10, decisions=10, determination=10, flair=10,
        leadership=10, off_the_ball=off_the_ball, positioning=10,
        teamwork=10, vision=vision, work_rate=10,
        # Physical
        acceleration=10, agility=10, balance=10, jumping=10,
        stamina=10, pace=10, endurance=10, strength=10,
        # Financial
        price="1M", wage=10000,
        # Physical stats
        height=180, weight=75, left_foot=10, right_foot=10,
        traits=None
    )
    return player


def create_player_state(player: Player, team: TeamSide, morale: int = 70, stamina: float = 100.0) -> PlayerState:
    """Create a PlayerState for testing"""
    state = PlayerState(
        player_id=1,
        player=player,
        team=team,
        position=player.position,
        squad_number=10,
        morale=morale,
        stamina=stamina
    )
    return state


def create_team_state(
    team_side: TeamSide,
    mentality: TacticMentality = TacticMentality.BALANCED,
    num_players: int = 11
) -> TeamState:
    """Create a TeamState with test players"""
    team = TeamState(
        team_side=team_side,
        club_id=1,
        club_name="Test FC",
        mentality=mentality
    )
    
    # Add test players
    for i in range(num_players):
        player = create_test_player(f"Player{i}", "CM")
        player_state = create_player_state(player, team_side)
        team.players.append(player_state)
    
    return team


class TestEventProbabilityCalculation:
    """Test suite for calculate_event_probability method"""
    
    def test_base_probabilities(self):
        """Test that base probabilities are returned for balanced setup"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        # Create balanced teams
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Create average player
        player = create_test_player("Average", "CM", ca=100)
        attacker = create_player_state(player, TeamSide.HOME, morale=70, stamina=100.0)
        
        # Calculate probabilities
        prob_pass = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.PASS)
        prob_shot = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.SHOT)
        prob_tackle = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.TACKLE)
        prob_foul = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.FOUL)
        
        # Base probabilities should be close to defaults (with minor position adjustments)
        assert 0.60 <= prob_pass <= 0.75, f"Pass probability {prob_pass} out of expected range"
        assert 0.05 <= prob_shot <= 0.15, f"Shot probability {prob_shot} out of expected range"
        assert 0.10 <= prob_tackle <= 0.20, f"Tackle probability {prob_tackle} out of expected range"
        assert 0.02 <= prob_foul <= 0.08, f"Foul probability {prob_foul} out of expected range"
    
    def test_mentality_attacking_increases_shots(self):
        """Test that attacking mentality increases shot probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        # Create teams with different mentalities
        balanced_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        attacking_team = create_team_state(TeamSide.HOME, TacticMentality.VERY_ATTACKING)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        player = create_test_player("Striker", "ST", finishing=15)
        attacker = create_player_state(player, TeamSide.HOME)
        
        # Calculate probabilities for both mentalities
        prob_shot_balanced = simulator.calculate_event_probability(balanced_team, away_team, attacker, EventType.SHOT)
        prob_shot_attacking = simulator.calculate_event_probability(attacking_team, away_team, attacker, EventType.SHOT)
        
        # Attacking mentality should increase shot probability
        assert prob_shot_attacking > prob_shot_balanced, \
            f"Attacking mentality ({prob_shot_attacking}) should have higher shot probability than balanced ({prob_shot_balanced})"
    
    def test_mentality_defensive_increases_passes(self):
        """Test that defensive mentality increases pass probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        # Create teams with different mentalities
        balanced_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        defensive_team = create_team_state(TeamSide.HOME, TacticMentality.DEFENSIVE)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        player = create_test_player("Midfielder", "CM")
        attacker = create_player_state(player, TeamSide.HOME)
        
        # Calculate probabilities
        prob_pass_balanced = simulator.calculate_event_probability(balanced_team, away_team, attacker, EventType.PASS)
        prob_pass_defensive = simulator.calculate_event_probability(defensive_team, away_team, attacker, EventType.PASS)
        
        # Defensive mentality should increase pass probability
        assert prob_pass_defensive > prob_pass_balanced, \
            f"Defensive mentality ({prob_pass_defensive}) should have higher pass probability than balanced ({prob_pass_balanced})"
    
    def test_striker_shoots_more_than_defender(self):
        """Test that strikers have higher shot probability than defenders"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Create striker and defender with same attributes
        striker = create_test_player("Striker", "ST", finishing=15)
        defender = create_test_player("Defender", "DC", finishing=15)
        
        striker_state = create_player_state(striker, TeamSide.HOME)
        defender_state = create_player_state(defender, TeamSide.HOME)
        
        # Calculate shot probabilities
        prob_shot_striker = simulator.calculate_event_probability(home_team, away_team, striker_state, EventType.SHOT)
        prob_shot_defender = simulator.calculate_event_probability(home_team, away_team, defender_state, EventType.SHOT)
        
        # Striker should have higher shot probability
        assert prob_shot_striker > prob_shot_defender, \
            f"Striker ({prob_shot_striker}) should have higher shot probability than defender ({prob_shot_defender})"
    
    def test_defender_passes_more_than_striker(self):
        """Test that defenders have higher pass probability than strikers"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Create striker and defender with same attributes
        striker = create_test_player("Striker", "ST", passing=12)
        defender = create_test_player("Defender", "DC", passing=12)
        
        striker_state = create_player_state(striker, TeamSide.HOME)
        defender_state = create_player_state(defender, TeamSide.HOME)
        
        # Calculate pass probabilities
        prob_pass_striker = simulator.calculate_event_probability(home_team, away_team, striker_state, EventType.PASS)
        prob_pass_defender = simulator.calculate_event_probability(home_team, away_team, defender_state, EventType.PASS)
        
        # Defender should have higher pass probability
        assert prob_pass_defender > prob_pass_striker, \
            f"Defender ({prob_pass_defender}) should have higher pass probability than striker ({prob_pass_striker})"
    
    def test_high_finishing_increases_shot_probability(self):
        """Test that high finishing attribute increases shot probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Create players with different finishing
        low_finishing = create_test_player("LowFinish", "ST", finishing=5, composure=10, off_the_ball=10)
        high_finishing = create_test_player("HighFinish", "ST", finishing=18, composure=18, off_the_ball=18)
        
        low_state = create_player_state(low_finishing, TeamSide.HOME)
        high_state = create_player_state(high_finishing, TeamSide.HOME)
        
        # Calculate shot probabilities
        prob_shot_low = simulator.calculate_event_probability(home_team, away_team, low_state, EventType.SHOT)
        prob_shot_high = simulator.calculate_event_probability(home_team, away_team, high_state, EventType.SHOT)
        
        # High finishing should increase shot probability
        assert prob_shot_high > prob_shot_low, \
            f"High finishing ({prob_shot_high}) should have higher shot probability than low finishing ({prob_shot_low})"
    
    def test_high_passing_increases_pass_probability(self):
        """Test that high passing attribute increases pass probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Create players with different passing
        low_passing = create_test_player("LowPass", "CM", passing=5, vision=5)
        high_passing = create_test_player("HighPass", "CM", passing=18, vision=18)
        
        low_state = create_player_state(low_passing, TeamSide.HOME)
        high_state = create_player_state(high_passing, TeamSide.HOME)
        
        # Calculate pass probabilities
        prob_pass_low = simulator.calculate_event_probability(home_team, away_team, low_state, EventType.PASS)
        prob_pass_high = simulator.calculate_event_probability(home_team, away_team, high_state, EventType.PASS)
        
        # High passing should increase pass probability
        assert prob_pass_high > prob_pass_low, \
            f"High passing ({prob_pass_high}) should have higher pass probability than low passing ({prob_pass_low})"
    
    def test_fatigue_reduces_shot_probability(self):
        """Test that low stamina reduces shot probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 80
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        player = create_test_player("Striker", "ST", finishing=15)
        
        # Create states with different stamina levels
        fresh_state = create_player_state(player, TeamSide.HOME, stamina=100.0)
        tired_state = create_player_state(player, TeamSide.HOME, stamina=30.0)
        
        # Calculate shot probabilities
        prob_shot_fresh = simulator.calculate_event_probability(home_team, away_team, fresh_state, EventType.SHOT)
        prob_shot_tired = simulator.calculate_event_probability(home_team, away_team, tired_state, EventType.SHOT)
        
        # Tired player should have lower shot probability
        assert prob_shot_tired < prob_shot_fresh, \
            f"Tired player ({prob_shot_tired}) should have lower shot probability than fresh player ({prob_shot_fresh})"
    
    def test_late_game_losing_team_shoots_more(self):
        """Test that losing team shoots more in late game"""
        simulator = MatchSimulator()
        simulator.current_minute = 85
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Set scores (home team losing)
        home_team.score = 0
        away_team.score = 1
        
        player = create_test_player("Striker", "ST", finishing=15)
        attacker = create_player_state(player, TeamSide.HOME)
        
        # Calculate shot probability at minute 85 vs minute 45
        simulator.current_minute = 45
        prob_shot_early = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.SHOT)
        
        simulator.current_minute = 85
        prob_shot_late = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.SHOT)
        
        # Late game losing team should shoot more
        assert prob_shot_late > prob_shot_early, \
            f"Late game losing team ({prob_shot_late}) should have higher shot probability than early game ({prob_shot_early})"
    
    def test_late_game_winning_team_passes_more(self):
        """Test that winning team passes more in late game"""
        simulator = MatchSimulator()
        simulator.current_minute = 85
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        # Set scores (home team winning)
        home_team.score = 2
        away_team.score = 0
        
        player = create_test_player("Midfielder", "CM", passing=15)
        attacker = create_player_state(player, TeamSide.HOME)
        
        # Calculate pass probability at minute 85 vs minute 45
        simulator.current_minute = 45
        prob_pass_early = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.PASS)
        
        simulator.current_minute = 85
        prob_pass_late = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.PASS)
        
        # Late game winning team should pass more
        assert prob_pass_late > prob_pass_early, \
            f"Late game winning team ({prob_pass_late}) should have higher pass probability than early game ({prob_pass_early})"
    
    def test_high_morale_increases_shot_probability(self):
        """Test that high morale increases shot probability"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        player = create_test_player("Striker", "ST", finishing=15)
        
        # Create states with different morale levels
        low_morale_state = create_player_state(player, TeamSide.HOME, morale=30)
        high_morale_state = create_player_state(player, TeamSide.HOME, morale=85)
        
        # Calculate shot probabilities
        prob_shot_low = simulator.calculate_event_probability(home_team, away_team, low_morale_state, EventType.SHOT)
        prob_shot_high = simulator.calculate_event_probability(home_team, away_team, high_morale_state, EventType.SHOT)
        
        # High morale should increase shot probability
        assert prob_shot_high > prob_shot_low, \
            f"High morale ({prob_shot_high}) should have higher shot probability than low morale ({prob_shot_low})"
    
    def test_probabilities_sum_to_reasonable_range(self):
        """Test that all event probabilities sum to a reasonable range"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        home_team = create_team_state(TeamSide.HOME, TacticMentality.BALANCED)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.BALANCED)
        
        player = create_test_player("Player", "CM")
        attacker = create_player_state(player, TeamSide.HOME)
        
        # Calculate all probabilities
        prob_pass = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.PASS)
        prob_shot = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.SHOT)
        prob_tackle = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.TACKLE)
        prob_foul = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.FOUL)
        
        total = prob_pass + prob_shot + prob_tackle + prob_foul
        
        # Total should be reasonable (not too far from 1.0 before normalization)
        assert 0.8 <= total <= 1.2, f"Total probability {total} is outside reasonable range"
    
    def test_probabilities_are_clamped(self):
        """Test that probabilities are clamped to [0.0, 1.0]"""
        simulator = MatchSimulator()
        simulator.current_minute = 45
        
        # Create extreme scenario
        home_team = create_team_state(TeamSide.HOME, TacticMentality.VERY_ATTACKING)
        away_team = create_team_state(TeamSide.AWAY, TacticMentality.DEFENSIVE)
        
        # Extreme striker
        player = create_test_player("SuperStriker", "ST", finishing=20, composure=20, off_the_ball=20)
        attacker = create_player_state(player, TeamSide.HOME, morale=100, stamina=100.0)
        
        # Calculate probabilities
        prob_pass = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.PASS)
        prob_shot = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.SHOT)
        prob_tackle = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.TACKLE)
        prob_foul = simulator.calculate_event_probability(home_team, away_team, attacker, EventType.FOUL)
        
        # All probabilities should be in valid range
        assert 0.0 <= prob_pass <= 1.0, f"Pass probability {prob_pass} out of valid range"
        assert 0.0 <= prob_shot <= 1.0, f"Shot probability {prob_shot} out of valid range"
        assert 0.0 <= prob_tackle <= 1.0, f"Tackle probability {prob_tackle} out of valid range"
        assert 0.0 <= prob_foul <= 1.0, f"Foul probability {prob_foul} out of valid range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
