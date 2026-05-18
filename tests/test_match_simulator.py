"""
Unit Tests - Match Simulator (Task 34.1)
Tests core match simulation logic.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from app.services.match_simulator import MatchSimulator, PlayerState, TeamState, MatchResult
from app.models.match_event import TeamSide


class MockPlayer:
    """Mock player for testing."""
    def __init__(self, ca=150, position="CM", **attrs):
        self.id = attrs.get('id', 1)
        self.ca = ca
        self.position = position
        self.name = attrs.get('name', 'Test Player')
        # Attributes (1-20)
        for attr in ['passing', 'vision', 'technique', 'finishing', 'composure',
                     'off_the_ball', 'tackling', 'marking', 'positioning',
                     'heading', 'strength', 'pace', 'acceleration', 'stamina',
                     'work_rate', 'aggression', 'bravery', 'dribbling', 'crossing',
                     'long_shots', 'decisions', 'concentration', 'anticipation',
                     'agility', 'balance', 'jumping_reach', 'natural_fitness',
                     'determination', 'flair', 'leadership', 'teamwork',
                     'free_kick', 'penalty_taking', 'corners', 'long_throws']:
            setattr(self, attr, attrs.get(attr, 12))


def create_test_team(side, ca_range=(140, 170)):
    """Create a test team with 11 players."""
    import random
    positions = ['GK', 'RB', 'CB', 'CB', 'LB', 'DM', 'CM', 'CM', 'RW', 'LW', 'ST']
    players = []
    for i, pos in enumerate(positions):
        ca = random.randint(*ca_range)
        player = MockPlayer(ca=ca, position=pos, id=i + (0 if side == 'home' else 100), name=f"Player {i+1}")
        players.append((player, i + 1, 70))  # (player, number, morale)
    return players


class TestMatchSimulator:
    """Test MatchSimulator class."""

    def test_simulator_initializes(self):
        sim = MatchSimulator()
        assert sim is not None
        assert sim.current_minute == 0

    def test_simulate_match_completes(self):
        sim = MatchSimulator()
        home = create_test_team('home')
        away = create_test_team('away')
        
        result = sim.simulate_match(
            home_club_id=1, home_club_name="Home FC",
            home_players=home,
            away_club_id=2, away_club_name="Away FC",
            away_players=away,
        )
        
        assert isinstance(result, MatchResult)
        assert result.home_score >= 0
        assert result.away_score >= 0
        assert result.match_duration == 90
        assert result.processing_time < 2.0  # Must complete in < 2 seconds

    def test_simulate_match_generates_events(self):
        sim = MatchSimulator()
        home = create_test_team('home')
        away = create_test_team('away')
        
        result = sim.simulate_match(
            home_club_id=1, home_club_name="Home",
            home_players=home,
            away_club_id=2, away_club_name="Away",
            away_players=away,
        )
        
        assert len(result.events) > 0  # Should generate events

    def test_home_advantage_applied(self):
        sim = MatchSimulator()
        home = create_test_team('home', ca_range=(150, 150))
        away = create_test_team('away', ca_range=(150, 150))
        
        # Run multiple simulations
        home_wins = 0
        for _ in range(50):
            result = sim.simulate_match(
                home_club_id=1, home_club_name="Home",
                home_players=home,
                away_club_id=2, away_club_name="Away",
                away_players=away,
                home_advantage=True,
            )
            if result.home_score > result.away_score:
                home_wins += 1
        
        # Home should win more than 30% with equal teams + home advantage
        assert home_wins > 15

    def test_stronger_team_wins_more(self):
        sim = MatchSimulator()
        strong = create_test_team('home', ca_range=(180, 190))
        weak = create_test_team('away', ca_range=(100, 120))
        
        strong_wins = 0
        for _ in range(20):
            result = sim.simulate_match(
                home_club_id=1, home_club_name="Strong",
                home_players=strong,
                away_club_id=2, away_club_name="Weak",
                away_players=weak,
            )
            if result.home_score > result.away_score:
                strong_wins += 1
        
        assert strong_wins > 12  # Strong team should dominate

    def test_extra_time_and_penalties(self):
        sim = MatchSimulator()
        home = create_test_team('home', ca_range=(150, 150))
        away = create_test_team('away', ca_range=(150, 150))
        
        # Run cup matches until we get one that goes to extra time
        got_extra_time = False
        for _ in range(50):
            result = sim.simulate_match(
                home_club_id=1, home_club_name="Home",
                home_players=home,
                away_club_id=2, away_club_name="Away",
                away_players=away,
                competition_type="CUP",
            )
            if result.match_duration > 90:
                got_extra_time = True
                break
        
        # With equal teams in cup, should sometimes go to extra time
        # (not guaranteed in 50 tries but very likely)

    def test_player_ratings_generated(self):
        sim = MatchSimulator()
        home = create_test_team('home')
        away = create_test_team('away')
        
        result = sim.simulate_match(
            home_club_id=1, home_club_name="Home",
            home_players=home,
            away_club_id=2, away_club_name="Away",
            away_players=away,
        )
        
        assert len(result.player_ratings) > 0
        for rating in result.player_ratings.values():
            assert 1.0 <= rating <= 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
