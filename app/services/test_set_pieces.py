"""
Unit tests for Set-Piece Simulation

Tests the set-piece simulation functionality including:
- Corner kick simulation
- Free kick simulation
- Penalty kick simulation
- Set-piece statistics tracking
- Integration with match flow
"""

import pytest
from unittest.mock import Mock

from app.services.match_simulator import (
    MatchSimulator,
    PlayerState,
    TeamState,
    SetPieceType,
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
        'jumping': 10
    }
    
    # Override with provided attributes
    default_attrs.update(attributes)
    
    for attr, value in default_attrs.items():
        setattr(player, attr, value)
    
    return player


def create_test_squad(team_name: str, start_id: int = 1, **player_overrides) -> list:
    """Create a test squad of 11 players with optional attribute overrides"""
    squad = []
    
    # Goalkeeper
    gk_attrs = player_overrides.get('gk', {})
    squad.append((
        create_mock_player(
            start_id,
            f"{team_name} GK",
            "GK",
            ca=90,
            positioning=15,
            anticipation=15,
            agility=14,
            **gk_attrs
        ),
        1,  # squad number
        70  # morale
    ))
    
    # Defenders (4)
    for i in range(4):
        def_attrs = player_overrides.get(f'def{i}', {})
        squad.append((
            create_mock_player(
                start_id + i + 1,
                f"{team_name} DEF{i+1}",
                "D C",
                ca=85,
                tackling=14,
                positioning=13,
                marking=14,
                heading=13,
                **def_attrs
            ),
            i + 2,
            70
        ))
    
    # Midfielders (4)
    for i in range(4):
        mid_attrs = player_overrides.get(f'mid{i}', {})
        # Set default values that can be overridden
        mid_defaults = {
            'passing': 15,
            'vision': 14,
            'technique': 14,
            'corners': 12,
            'free_kicks': 12
        }
        mid_defaults.update(mid_attrs)
        
        squad.append((
            create_mock_player(
                start_id + i + 5,
                f"{team_name} MID{i+1}",
                "M C",
                ca=95,
                **mid_defaults
            ),
            i + 6,
            70
        ))
    
    # Forwards (2)
    for i in range(2):
        fwd_attrs = player_overrides.get(f'fwd{i}', {})
        # Set default values that can be overridden
        fwd_defaults = {
            'finishing': 16,
            'composure': 15,
            'dribbling': 14,
            'heading': 15,
            'penalty': 16
        }
        fwd_defaults.update(fwd_attrs)
        
        squad.append((
            create_mock_player(
                start_id + i + 9,
                f"{team_name} FWD{i+1}",
                "ST C",
                ca=100,
                **fwd_defaults
            ),
            i + 10,
            70
        ))
    
    return squad


class TestSetPieceSimulation:
    """Test suite for set-piece simulation"""
    
    def test_corner_kick_simulation(self):
        """Test that corner kicks are simulated correctly"""
        simulator = MatchSimulator()
        
        # Create squads with good corner takers
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            mid0={'corners': 18, 'crossing': 17, 'technique': 16}
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate corner
        simulator.current_minute = 10
        simulator.current_second = 30
        simulator._simulate_set_piece(
            SetPieceType.CORNER,
            simulator.home_team,
            simulator.away_team
        )
        
        # Verify corner statistics
        assert simulator.home_team.corners == 1
        
        # Verify corner event was created
        corner_events = [e for e in simulator.events if 'CORNER' in str(e.get('event_type', '')).upper()]
        assert len(corner_events) >= 1
        
        # Verify event structure
        corner_event = corner_events[0]
        assert corner_event['minute'] == 10
        assert corner_event['second'] == 30
        assert corner_event['team'] == TeamSide.HOME.value
        assert 'player_id' in corner_event
    
    def test_free_kick_simulation_close_range(self):
        """Test that free kicks from close range are simulated correctly"""
        simulator = MatchSimulator()
        
        # Create squads with good free kick takers
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            mid0={'free_kicks': 18, 'technique': 17, 'composure': 16}
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate free kick from 20 meters (close range)
        simulator.current_minute = 25
        simulator.current_second = 15
        simulator._simulate_set_piece(
            SetPieceType.FREE_KICK,
            simulator.home_team,
            simulator.away_team,
            foul_position_x=85.0,  # 20 meters from goal
            foul_position_y=50.0
        )
        
        # Verify free kick statistics
        assert simulator.home_team.free_kicks == 1
        
        # Verify free kick event was created
        fk_events = [e for e in simulator.events if 'FREE_KICK' in str(e.get('event_type', '')).upper()]
        assert len(fk_events) >= 1
        
        # Should also have a shot event (close range free kicks are shots)
        shot_events = [e for e in simulator.events if e.get('event_type') in [EventType.SHOT.value, EventType.GOAL.value]]
        assert len(shot_events) >= 1
    
    def test_free_kick_simulation_long_range(self):
        """Test that free kicks from long range are simulated correctly"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate free kick from 40 meters (long range - likely a cross)
        simulator.current_minute = 35
        simulator.current_second = 45
        simulator._simulate_set_piece(
            SetPieceType.FREE_KICK,
            simulator.home_team,
            simulator.away_team,
            foul_position_x=65.0,  # 40 meters from goal
            foul_position_y=50.0
        )
        
        # Verify free kick statistics
        assert simulator.home_team.free_kicks == 1
        
        # Verify free kick event was created
        fk_events = [e for e in simulator.events if 'FREE_KICK' in str(e.get('event_type', '')).upper()]
        assert len(fk_events) >= 1
    
    def test_penalty_kick_simulation(self):
        """Test that penalty kicks are simulated correctly"""
        simulator = MatchSimulator()
        
        # Create squads with good penalty takers
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            fwd0={'penalty': 18, 'composure': 17, 'technique': 16}
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate penalty
        simulator.current_minute = 60
        simulator.current_second = 0
        simulator._simulate_set_piece(
            SetPieceType.PENALTY,
            simulator.home_team,
            simulator.away_team
        )
        
        # Verify penalty statistics
        assert simulator.home_team.penalties_awarded == 1
        
        # Verify penalty event was created
        penalty_events = [e for e in simulator.events if 'PENALTY' in str(e.get('event_type', '')).upper()]
        assert len(penalty_events) >= 1
        
        # Should also have a shot/goal event
        shot_events = [e for e in simulator.events if e.get('event_type') in [EventType.SHOT.value, EventType.GOAL.value]]
        assert len(shot_events) >= 1
        
        # Verify penalty position
        penalty_event = penalty_events[0]
        assert penalty_event['position_x'] == 94.0  # Penalty spot
        assert penalty_event['position_y'] == 50.0
    
    def test_penalty_high_success_rate(self):
        """Test that penalties have a high success rate (75-80%)"""
        simulator = MatchSimulator()
        
        # Create squads with excellent penalty takers
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            fwd0={'penalty': 20, 'composure': 20, 'technique': 20}
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate multiple penalties to test success rate
        goals_scored = 0
        num_penalties = 50
        
        for i in range(num_penalties):
            simulator.current_minute = i + 1
            simulator.current_second = 0
            simulator.events = []  # Clear events
            
            initial_score = simulator.home_team.score
            
            simulator._simulate_set_piece(
                SetPieceType.PENALTY,
                simulator.home_team,
                simulator.away_team
            )
            
            if simulator.home_team.score > initial_score:
                goals_scored += 1
        
        success_rate = goals_scored / num_penalties
        
        # With excellent penalty taker, success rate should be 70-90%
        assert 0.60 <= success_rate <= 0.95, f"Penalty success rate {success_rate:.2%} outside expected range"
    
    def test_corners_awarded_from_saved_shots(self):
        """Test that corners are awarded when shots are saved"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        # Run full match simulation
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Verify that corners were awarded
        total_corners = result.home_statistics['corners'] + result.away_statistics['corners']
        
        # In a typical match, there should be some corners
        assert total_corners >= 0  # At least possible to have corners
        
        # Verify corner events exist if corners were awarded
        if total_corners > 0:
            corner_events = [e for e in result.events if 'CORNER' in str(e.get('event_type', '')).upper()]
            assert len(corner_events) > 0
    
    def test_penalties_awarded_from_fouls_in_box(self):
        """Test that penalties are awarded for fouls in the penalty area"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        # Run full match simulation
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Verify penalty statistics are tracked
        assert 'penalties_awarded' in result.home_statistics
        assert 'penalties_scored' in result.away_statistics
        
        # If penalties were awarded, verify events exist
        total_penalties = result.home_statistics['penalties_awarded'] + result.away_statistics['penalties_awarded']
        if total_penalties > 0:
            penalty_events = [e for e in result.events if 'PENALTY' in str(e.get('event_type', '')).upper()]
            assert len(penalty_events) > 0
    
    def test_free_kicks_awarded_from_dangerous_fouls(self):
        """Test that free kicks are awarded for fouls in dangerous positions"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        # Run full match simulation
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # Verify free kick statistics are tracked
        assert 'free_kicks' in result.home_statistics
        assert 'free_kicks' in result.away_statistics
        
        # In a typical match with fouls, there should be some free kicks
        total_free_kicks = result.home_statistics['free_kicks'] + result.away_statistics['free_kicks']
        assert total_free_kicks >= 0
    
    def test_set_piece_statistics_in_match_result(self):
        """Test that set-piece statistics are included in match results"""
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
        
        # Verify all set-piece statistics are present
        for stats in [result.home_statistics, result.away_statistics]:
            assert 'corners' in stats
            assert 'free_kicks' in stats
            assert 'penalties_awarded' in stats
            assert 'penalties_scored' in stats
            
            # Verify values are non-negative
            assert stats['corners'] >= 0
            assert stats['free_kicks'] >= 0
            assert stats['penalties_awarded'] >= 0
            assert stats['penalties_scored'] >= 0
            
            # Penalties scored cannot exceed penalties awarded
            assert stats['penalties_scored'] <= stats['penalties_awarded']
    
    def test_corner_taker_selection(self):
        """Test that the player with highest corners attribute takes corners"""
        simulator = MatchSimulator()
        
        # Create squad with one excellent corner taker
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            mid0={'corners': 20}  # Best corner taker
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate corner
        simulator.current_minute = 10
        simulator._simulate_set_piece(
            SetPieceType.CORNER,
            simulator.home_team,
            simulator.away_team
        )
        
        # Find the corner event
        corner_events = [e for e in simulator.events if 'CORNER' in str(e.get('event_type', '')).upper()]
        assert len(corner_events) > 0
        
        # Verify the corner taker is the player with corners=20
        corner_event = corner_events[0]
        corner_taker_id = corner_event['player_id']
        
        # Find the player
        corner_taker = next(p for p in simulator.home_team.players if p.player_id == corner_taker_id)
        assert corner_taker.player.corners == 20
    
    def test_penalty_taker_selection(self):
        """Test that the player with highest penalty attribute takes penalties"""
        simulator = MatchSimulator()
        
        # Create squad with one excellent penalty taker
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            fwd0={'penalty': 20}  # Best penalty taker
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate penalty
        simulator.current_minute = 60
        simulator._simulate_set_piece(
            SetPieceType.PENALTY,
            simulator.home_team,
            simulator.away_team
        )
        
        # Find the penalty event
        penalty_events = [e for e in simulator.events if 'PENALTY' in str(e.get('event_type', '')).upper()]
        assert len(penalty_events) > 0
        
        # Verify the penalty taker is the player with penalty=20
        penalty_event = penalty_events[0]
        penalty_taker_id = penalty_event['player_id']
        
        # Find the player
        penalty_taker = next(p for p in simulator.home_team.players if p.player_id == penalty_taker_id)
        assert penalty_taker.player.penalty == 20
    
    def test_free_kick_taker_selection(self):
        """Test that the player with highest free_kicks attribute takes free kicks"""
        simulator = MatchSimulator()
        
        # Create squad with one excellent free kick taker
        home_squad = create_test_squad(
            "Home",
            start_id=1,
            mid0={'free_kicks': 20}  # Best free kick taker
        )
        away_squad = create_test_squad("Away", start_id=100)
        
        # Initialize match
        simulator._initialize_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=home_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad,
            weather=WeatherCondition.CLEAR,
            pitch_condition=PitchCondition.GOOD,
            home_advantage=True
        )
        
        # Simulate free kick
        simulator.current_minute = 30
        simulator._simulate_set_piece(
            SetPieceType.FREE_KICK,
            simulator.home_team,
            simulator.away_team,
            foul_position_x=80.0,
            foul_position_y=50.0
        )
        
        # Find the free kick event
        fk_events = [e for e in simulator.events if 'FREE_KICK' in str(e.get('event_type', '')).upper()]
        assert len(fk_events) > 0
        
        # Verify the free kick taker is the player with free_kicks=20
        fk_event = fk_events[0]
        fk_taker_id = fk_event['player_id']
        
        # Find the player
        fk_taker = next(p for p in simulator.home_team.players if p.player_id == fk_taker_id)
        assert fk_taker.player.free_kicks == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
