"""
Unit tests for event generation logic in MatchSimulator

Tests Task 4.4: Create event generation logic (pass, shot, tackle, foul)

Validates:
- Event type distribution matches design specifications
- All event types are generated (pass, shot, tackle, foul)
- Events include required fields (position, success, players)
- Event probabilities are realistic and dynamic
"""

import pytest
from unittest.mock import Mock
from collections import Counter

from app.services.match_simulator import (
    MatchSimulator,
    PlayerState,
    TeamState,
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
        'marking': 10
    }
    
    # Override with provided attributes
    default_attrs.update(attributes)
    
    for attr, value in default_attrs.items():
        setattr(player, attr, value)
    
    return player


def create_test_squad(team_name: str, start_id: int = 1) -> list:
    """Create a test squad of 11 players"""
    squad = []
    
    # Goalkeeper
    squad.append((
        create_mock_player(start_id, f"{team_name} GK", "GK", ca=90, positioning=15, anticipation=15),
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
                positioning=13
            ),
            i + 2,
            70
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
            70
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
            70
        ))
    
    return squad


class TestEventGeneration:
    """Test suite for event generation logic (Task 4.4)"""
    
    def test_all_event_types_generated(self):
        """Test that all four event types (pass, shot, tackle, foul) are generated"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Collect all event types
        event_types = set(event['event_type'] for event in result.events)
        
        # Verify all four core event types are present
        assert EventType.PASS.value in event_types, "Pass events should be generated"
        assert EventType.SHOT.value in event_types or EventType.GOAL.value in event_types, \
            "Shot or goal events should be generated"
        assert EventType.TACKLE.value in event_types, "Tackle events should be generated"
        assert EventType.FOUL.value in event_types, "Foul events should be generated"
    
    def test_event_distribution_realistic(self):
        """Test that event distribution follows design specifications"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Count event types
        event_counter = Counter(event['event_type'] for event in result.events)
        total_events = len(result.events)
        
        # Calculate percentages
        pass_pct = (event_counter[EventType.PASS.value] / total_events) * 100
        shot_pct = ((event_counter[EventType.SHOT.value] + event_counter.get(EventType.GOAL.value, 0)) / total_events) * 100
        tackle_pct = (event_counter[EventType.TACKLE.value] / total_events) * 100
        foul_pct = (event_counter[EventType.FOUL.value] / total_events) * 100
        
        # Verify distributions are within reasonable ranges
        # Design specs: pass 60-70%, shot 5-15%, tackle 10-20%, foul 2-5%
        # Allow some variance due to dynamic probability system
        assert 50 <= pass_pct <= 80, f"Pass percentage {pass_pct:.1f}% should be roughly 60-70%"
        assert 3 <= shot_pct <= 25, f"Shot percentage {shot_pct:.1f}% should be roughly 5-15%"
        assert 5 <= tackle_pct <= 30, f"Tackle percentage {tackle_pct:.1f}% should be roughly 10-20%"
        assert 1 <= foul_pct <= 10, f"Foul percentage {foul_pct:.1f}% should be roughly 2-5%"
    
    def test_event_structure_complete(self):
        """Test that all events include required fields"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Verify each event has required fields
        required_fields = ['minute', 'second', 'event_type', 'team', 'player_id', 'success', 'position_x', 'position_y']
        
        for event in result.events:
            for field in required_fields:
                assert field in event, f"Event missing required field: {field}"
            
            # Validate field values
            assert 1 <= event['minute'] <= 90, "Minute should be 1-90"
            assert 0 <= event['second'] <= 59, "Second should be 0-59"
            assert event['team'] in [TeamSide.HOME.value, TeamSide.AWAY.value], "Team should be HOME or AWAY"
            assert isinstance(event['player_id'], int), "Player ID should be integer"
            assert isinstance(event['success'], bool), "Success should be boolean"
            assert 0 <= event['position_x'] <= 100, "Position X should be 0-100"
            assert 0 <= event['position_y'] <= 100, "Position Y should be 0-100"
    
    def test_pass_events_have_success_rate(self):
        """Test that pass events have realistic success/failure rates"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Filter pass events
        pass_events = [e for e in result.events if e['event_type'] == EventType.PASS.value]
        
        if len(pass_events) > 0:
            successful_passes = sum(1 for e in pass_events if e['success'])
            pass_success_rate = (successful_passes / len(pass_events)) * 100
            
            # Pass success rate should be realistic (50-95%)
            assert 50 <= pass_success_rate <= 95, \
                f"Pass success rate {pass_success_rate:.1f}% should be realistic (50-95%)"
    
    def test_shot_events_have_on_target_rate(self):
        """Test that shot events have realistic on-target rates"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Filter shot and goal events
        shot_events = [e for e in result.events if e['event_type'] in [EventType.SHOT.value, EventType.GOAL.value]]
        
        if len(shot_events) > 0:
            # Goals are always on target, shots may or may not be
            # The implementation tracks shots_on_target in team statistics
            total_shots = result.home_statistics['shots'] + result.away_statistics['shots']
            shots_on_target = result.home_statistics['shots_on_target'] + result.away_statistics['shots_on_target']
            
            if total_shots > 0:
                on_target_rate = (shots_on_target / total_shots) * 100
                
                # On-target rate should be realistic (20-70%)
                assert 10 <= on_target_rate <= 80, \
                    f"Shot on-target rate {on_target_rate:.1f}% should be realistic (20-70%)"
    
    def test_tackle_events_have_target_player(self):
        """Test that tackle events include target player information"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Filter tackle events
        tackle_events = [e for e in result.events if e['event_type'] == EventType.TACKLE.value]
        
        # Verify tackle events have target player
        for event in tackle_events:
            assert 'target_player_id' in event, "Tackle events should include target_player_id"
            assert isinstance(event['target_player_id'], int), "Target player ID should be integer"
    
    def test_foul_events_have_target_player(self):
        """Test that foul events include target player information"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Filter foul events
        foul_events = [e for e in result.events if e['event_type'] == EventType.FOUL.value]
        
        # Verify foul events have target player
        for event in foul_events:
            assert 'target_player_id' in event, "Foul events should include target_player_id"
            assert isinstance(event['target_player_id'], int), "Target player ID should be integer"
    
    def test_event_positions_realistic(self):
        """Test that event positions are realistic for event types"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Check shot positions (should be in attacking third, near goal)
        shot_events = [e for e in result.events if e['event_type'] in [EventType.SHOT.value, EventType.GOAL.value]]
        for event in shot_events:
            # Shots should generally be in attacking areas (x > 60)
            # Current implementation uses x: 70-95
            assert event['position_x'] >= 60, f"Shot at x={event['position_x']} should be in attacking area"
        
        # Check pass positions (can be anywhere)
        pass_events = [e for e in result.events if e['event_type'] == EventType.PASS.value]
        for event in pass_events:
            # Passes can be anywhere on pitch
            assert 0 <= event['position_x'] <= 100
            assert 0 <= event['position_y'] <= 100
    
    def test_cards_generated_from_fouls(self):
        """Test that cards (yellow/red) can be generated from fouls"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Check if any cards were given
        card_events = [e for e in result.events if e['event_type'] in [EventType.YELLOW_CARD.value, EventType.RED_CARD.value]]
        
        # Cards should be relatively rare but possible
        # With ~10-20 fouls per match and 10% yellow card rate, we expect 1-2 cards on average
        # This is probabilistic, so we just verify the structure if cards exist
        for event in card_events:
            assert 'player_id' in event
            assert 'team' in event
            assert event['success'] == True, "Card events should always have success=True"
    
    def test_event_timing_sequential(self):
        """Test that events are generated in chronological order"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Verify events are in chronological order
        for i in range(1, len(result.events)):
            prev_event = result.events[i-1]
            curr_event = result.events[i]
            
            prev_time = prev_event['minute'] * 60 + prev_event['second']
            curr_time = curr_event['minute'] * 60 + curr_event['second']
            
            # Current event should be at same time or later
            assert curr_time >= prev_time, "Events should be in chronological order"
    
    def test_tactics_affect_event_distribution(self):
        """Test that different tactics affect event type distribution"""
        # Create attacking team
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        # Simulate with attacking mentality
        simulator_attacking = MatchSimulator()
        simulator_attacking.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Set attacking mentality
        simulator_attacking.home_team.mentality = TacticMentality.VERY_ATTACKING
        
        # Generate some events manually to test probability calculation
        attacking_team = simulator_attacking.home_team
        defending_team = simulator_attacking.away_team
        attacker = attacking_team.get_active_players()[0]
        
        # Calculate probabilities for attacking team
        prob_shot_attacking = simulator_attacking.calculate_event_probability(
            attacking_team, defending_team, attacker, EventType.SHOT
        )
        prob_pass_attacking = simulator_attacking.calculate_event_probability(
            attacking_team, defending_team, attacker, EventType.PASS
        )
        
        # Create defensive team
        simulator_defensive = MatchSimulator()
        simulator_defensive.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        simulator_defensive.home_team.mentality = TacticMentality.DEFENSIVE
        
        attacking_team_def = simulator_defensive.home_team
        defending_team_def = simulator_defensive.away_team
        attacker_def = attacking_team_def.get_active_players()[0]
        
        prob_shot_defensive = simulator_defensive.calculate_event_probability(
            attacking_team_def, defending_team_def, attacker_def, EventType.SHOT
        )
        prob_pass_defensive = simulator_defensive.calculate_event_probability(
            attacking_team_def, defending_team_def, attacker_def, EventType.PASS
        )
        
        # Attacking teams should have higher shot probability
        assert prob_shot_attacking > prob_shot_defensive, \
            "Attacking mentality should increase shot probability"
        
        # Defensive teams should have higher pass probability
        assert prob_pass_defensive > prob_pass_attacking, \
            "Defensive mentality should increase pass probability"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
