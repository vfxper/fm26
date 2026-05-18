"""
Comprehensive tests for the fatigue simulation system.

Tests cover:
- Stamina loss calculation based on work rate
- CA reduction when stamina < 50%
- Fatigue impact on event probabilities
- Fatigue accumulation over match duration
- Work rate influence on stamina loss
"""

import pytest
from app.services.match_simulator import (
    MatchSimulator,
    PlayerState,
    TeamState,
    TeamSide,
    TacticMentality,
    EventType
)
from app.models.player import Player
from app.models.match import WeatherCondition, PitchCondition


def create_test_player(
    name: str,
    position: str,
    ca: int = 100,
    work_rate: int = 10,
    stamina: int = 15,
    finishing: int = 10,
    passing: int = 10,
    vision: int = 10,
    technique: int = 10,
    tackling: int = 10,
    positioning: int = 10,
    dribbling: int = 10,
    agility: int = 10,
    aggression: int = 10,
    anticipation: int = 10
) -> Player:
    """Create a test player with specified attributes"""
    player = Player(
        id=1,
        uid=f"test_{name}",
        name=name,
        position=position,
        age=25,
        nationality="Test",
        club="Test FC",
        ca=ca,
        pa=ca + 10,
        # Technical
        corners=10,
        crossing=10,
        dribbling=dribbling,
        finishing=finishing,
        first_touch=10,
        free_kicks=10,
        heading=10,
        long_shots=10,
        long_throws=10,
        marking=10,
        passing=passing,
        penalty=10,
        tackling=tackling,
        technique=technique,
        # Mental
        aggression=aggression,
        anticipation=anticipation,
        bravery=10,
        composure=10,
        concentration=10,
        decisions=10,
        determination=10,
        flair=10,
        leadership=10,
        off_the_ball=10,
        positioning=positioning,
        teamwork=10,
        vision=vision,
        work_rate=work_rate,
        # Physical
        acceleration=10,
        agility=agility,
        balance=10,
        jumping=10,
        stamina=stamina,
        pace=10,
        endurance=10,
        strength=10,
        # Financial
        price="1M",
        wage=10000,
        # Physical stats
        height=180,
        weight=75,
        left_foot=10,
        right_foot=10,
        traits=""
    )
    return player


def create_player_state(
    player: Player,
    team: TeamSide,
    stamina: float = 100.0,
    morale: int = 70
) -> PlayerState:
    """Create a player state for testing"""
    return PlayerState(
        player_id=player.id,
        player=player,
        team=team,
        position=player.position,
        squad_number=10,
        morale=morale,
        stamina=stamina
    )


def create_team_state(
    team_side: TeamSide,
    mentality: TacticMentality = TacticMentality.BALANCED,
    num_players: int = 11
) -> TeamState:
    """Create a team state with test players"""
    team = TeamState(
        team_side=team_side,
        club_id=1 if team_side == TeamSide.HOME else 2,
        club_name="Home FC" if team_side == TeamSide.HOME else "Away FC",
        mentality=mentality
    )
    
    for i in range(num_players):
        player = create_test_player(f"Player{i}", "M C")
        player_state = create_player_state(player, team_side)
        team.players.append(player_state)
    
    return team


def create_test_squad(team_name: str, start_id: int = 1):
    """Create a test squad of 11 players"""
    squad = []
    positions = ["GK"] + ["D C"] * 4 + ["M C"] * 4 + ["ST"] * 2
    
    for i, position in enumerate(positions):
        player = create_test_player(
            f"{team_name} Player {i+1}",
            position,
            ca=100,
            work_rate=10
        )
        player.id = start_id + i
        squad.append((player, i+1, 70))  # (player, squad_number, morale)
    
    return squad


class TestFatigueStaminaLoss:
    """Tests for stamina loss calculation"""
    
    def test_stamina_decreases_over_time(self):
        """Test that stamina decreases as match progresses"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, True
        )
        
        # Record initial stamina
        initial_stamina = {p.player_id: p.stamina for p in simulator.home_team.players}
        
        # Simulate 10 minutes
        for _ in range(10):
            simulator._update_fatigue()
        
        # Check that stamina has decreased for all players
        for player_state in simulator.home_team.players:
            assert player_state.stamina < initial_stamina[player_state.player_id], \
                f"Player {player_state.player_id} stamina should decrease over time"
    
    def test_work_rate_affects_stamina_loss(self):
        """Test that higher work rate leads to faster stamina loss"""
        simulator = MatchSimulator()
        
        # Create two players with different work rates
        low_work_rate_player = create_test_player("Low WR", "M C", work_rate=5)
        high_work_rate_player = create_test_player("High WR", "M C", work_rate=20)
        
        low_work_rate_player.id = 1
        high_work_rate_player.id = 2
        
        home_squad = [
            (low_work_rate_player, 1, 70),
            (high_work_rate_player, 2, 70)
        ] + create_test_squad("Home", start_id=3)[2:]
        
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, True
        )
        
        # Simulate 30 minutes
        for _ in range(30):
            simulator._update_fatigue()
        
        # Find the two test players
        low_wr_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        high_wr_state = next(p for p in simulator.home_team.players if p.player_id == 2)
        
        # High work rate player should have lost more stamina
        assert high_wr_state.stamina < low_wr_state.stamina, \
            f"High work rate player (stamina={high_wr_state.stamina}) should be more tired than low work rate player (stamina={low_wr_state.stamina})"
    
    def test_stamina_never_goes_negative(self):
        """Test that stamina is clamped at 0"""
        simulator = MatchSimulator()
        
        home_squad = create_test_squad("Home", start_id=1)
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, True
        )
        
        # Simulate full 90 minutes
        for _ in range(90):
            simulator._update_fatigue()
        
        # Check that no player has negative stamina
        all_players = simulator.home_team.players + simulator.away_team.players
        for player_state in all_players:
            assert player_state.stamina >= 0.0, \
                f"Player {player_state.player_id} has negative stamina: {player_state.stamina}"


class TestFatigueCAReduction:
    """Tests for CA reduction when stamina < 50%"""
    
    def test_ca_reduced_when_stamina_below_50(self):
        """Test that effective CA is reduced by 10% when stamina < 50%"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100)
        player.id = 1
        
        home_squad = [(player, 1, 70)] + create_test_squad("Home", start_id=2)[1:]
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, False  # No home advantage for clearer testing
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Manually set stamina to 49% (below threshold)
        test_player_state.stamina = 49.0
        
        # Update fatigue to recalculate effective CA
        simulator._update_fatigue()
        
        # Expected CA: 100 * 0.90 = 90 (10% reduction)
        expected_ca = 100 * 0.90
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"Expected CA ~{expected_ca}, got {test_player_state.effective_ca}"
    
    def test_no_ca_reduction_when_stamina_above_50(self):
        """Test that effective CA is NOT reduced when stamina >= 50%"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100)
        player.id = 1
        
        home_squad = [(player, 1, 70)] + create_test_squad("Home", start_id=2)[1:]
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, False
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Manually set stamina to 51% (above threshold)
        test_player_state.stamina = 51.0
        
        # Update fatigue to recalculate effective CA
        simulator._update_fatigue()
        
        # Expected CA: 100 (no reduction)
        expected_ca = 100.0
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"Expected CA ~{expected_ca}, got {test_player_state.effective_ca}"
    
    def test_ca_reduction_with_home_advantage(self):
        """Test that fatigue penalty applies correctly with home advantage"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100)
        player.id = 1
        
        home_squad = [(player, 1, 70)] + create_test_squad("Home", start_id=2)[1:]
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, True  # Home advantage enabled
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Manually set stamina to 40% (below threshold)
        test_player_state.stamina = 40.0
        
        # Update fatigue to recalculate effective CA
        simulator._update_fatigue()
        
        # Expected CA: 100 * 1.05 (home advantage) * 0.90 (fatigue) = 94.5
        expected_ca = 100 * 1.05 * 0.90
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"Expected CA ~{expected_ca}, got {test_player_state.effective_ca}"
    
    def test_ca_reduction_with_low_morale(self):
        """Test that fatigue penalty stacks with morale penalty"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100)
        player.id = 1
        
        home_squad = [(player, 1, 35)] + create_test_squad("Home", start_id=2)[1:]  # Low morale (35)
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, False
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Manually set stamina to 40% (below threshold)
        test_player_state.stamina = 40.0
        
        # Update fatigue to recalculate effective CA
        simulator._update_fatigue()
        
        # Expected CA: 100 * 0.95 (low morale) * 0.90 (fatigue) = 85.5
        expected_ca = 100 * 0.95 * 0.90
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"Expected CA ~{expected_ca}, got {test_player_state.effective_ca}"


class TestFatigueImpactOnEvents:
    """Tests for fatigue impact on event probabilities"""
    
    def test_tired_players_shoot_less(self):
        """Test that tired players have reduced shot probability"""
        simulator = MatchSimulator()
        
        home_team = create_team_state(TeamSide.HOME)
        away_team = create_team_state(TeamSide.AWAY)
        
        player = create_test_player("Striker", "ST", finishing=15)
        
        fresh_state = create_player_state(player, TeamSide.HOME, stamina=100.0)
        tired_state = create_player_state(player, TeamSide.HOME, stamina=30.0)
        
        prob_shot_fresh = simulator.calculate_event_probability(home_team, away_team, fresh_state, EventType.SHOT)
        prob_shot_tired = simulator.calculate_event_probability(home_team, away_team, tired_state, EventType.SHOT)
        
        assert prob_shot_tired < prob_shot_fresh, \
            f"Tired player shot probability ({prob_shot_tired}) should be less than fresh player ({prob_shot_fresh})"
    
    def test_tired_players_pass_more(self):
        """Test that tired players have increased pass probability"""
        simulator = MatchSimulator()
        
        home_team = create_team_state(TeamSide.HOME)
        away_team = create_team_state(TeamSide.AWAY)
        
        player = create_test_player("Midfielder", "M C", passing=15)
        
        fresh_state = create_player_state(player, TeamSide.HOME, stamina=100.0)
        tired_state = create_player_state(player, TeamSide.HOME, stamina=30.0)
        
        prob_pass_fresh = simulator.calculate_event_probability(home_team, away_team, fresh_state, EventType.PASS)
        prob_pass_tired = simulator.calculate_event_probability(home_team, away_team, tired_state, EventType.PASS)
        
        assert prob_pass_tired > prob_pass_fresh, \
            f"Tired player pass probability ({prob_pass_tired}) should be greater than fresh player ({prob_pass_fresh})"


class TestFatigueFullMatch:
    """Integration tests for fatigue over full match"""
    
    def test_fatigue_accumulates_over_90_minutes(self):
        """Test that fatigue accumulates realistically over a full match"""
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
        
        # After 90 minutes, all players should have reduced stamina
        all_players = simulator.home_team.players + simulator.away_team.players
        
        for player_state in all_players:
            assert player_state.stamina < 100.0, \
                f"Player {player_state.player_id} should have reduced stamina after 90 minutes"
            assert player_state.stamina >= 0.0, \
                f"Player {player_state.player_id} should not have negative stamina"
            assert player_state.minutes_played == 90, \
                f"Player {player_state.player_id} should have played 90 minutes"
    
    def test_some_players_reach_fatigue_threshold(self):
        """Test that some players reach the 50% stamina threshold"""
        simulator = MatchSimulator()
        
        # Create players with high work rate to ensure fatigue
        high_work_rate_squad = []
        positions = ["GK"] + ["D C"] * 4 + ["M C"] * 4 + ["ST"] * 2
        
        for i, position in enumerate(positions):
            player = create_test_player(
                f"Home Player {i+1}",
                position,
                ca=100,
                work_rate=18  # High work rate
            )
            player.id = i + 1
            high_work_rate_squad.append((player, i+1, 70))
        
        away_squad = create_test_squad("Away", start_id=100)
        
        result = simulator.simulate_match(
            home_club_id=1,
            home_club_name="Home FC",
            home_players=high_work_rate_squad,
            away_club_id=2,
            away_club_name="Away FC",
            away_players=away_squad
        )
        
        # At least some players should have stamina < 50%
        fatigued_players = [p for p in simulator.home_team.players if p.stamina < 50.0]
        
        assert len(fatigued_players) > 0, \
            "At least some high work rate players should reach fatigue threshold (stamina < 50%)"
    
    def test_fatigue_affects_match_statistics(self):
        """Test that fatigue impacts overall match statistics"""
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
        
        # Match should complete successfully
        assert result.match_duration == 90
        assert result.processing_time < 2.0  # Performance requirement
        
        # Statistics should be generated
        assert 'possession' in result.home_statistics
        assert 'shots' in result.home_statistics
        assert 'passes' in result.home_statistics
        
        # Events should be generated
        assert len(result.events) > 0


class TestFatigueEdgeCases:
    """Tests for edge cases in fatigue system"""
    
    def test_stamina_exactly_50_percent(self):
        """Test behavior when stamina is exactly 50%"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100, work_rate=10)
        player.id = 1
        
        home_squad = [(player, 1, 70)] + create_test_squad("Home", start_id=2)[1:]
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, False
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Set stamina to 51% so after stamina loss it will be around 50%
        # Work rate 10 means stamina loss = 1.0 * (0.8 + 10/20 * 0.4) = 1.0 per minute
        test_player_state.stamina = 51.0
        
        # Update fatigue (will reduce stamina by ~1.0, bringing it to ~50.0)
        simulator._update_fatigue()
        
        # After update, stamina should be around 50%, and no penalty should apply (threshold is < 50%)
        # The stamina should be exactly 50.0 or very close
        assert test_player_state.stamina >= 49.9 and test_player_state.stamina <= 50.1, \
            f"Stamina should be around 50%, got {test_player_state.stamina}"
        
        # At exactly 50% or above, no penalty should apply
        expected_ca = 100.0
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"At exactly 50% stamina, no penalty should apply. Expected {expected_ca}, got {test_player_state.effective_ca}"
    
    def test_stamina_at_zero(self):
        """Test behavior when stamina reaches 0"""
        simulator = MatchSimulator()
        
        player = create_test_player("Test Player", "M C", ca=100)
        player.id = 1
        
        home_squad = [(player, 1, 70)] + create_test_squad("Home", start_id=2)[1:]
        away_squad = create_test_squad("Away", start_id=100)
        
        simulator._initialize_match(
            1, "Home FC", home_squad,
            2, "Away FC", away_squad,
            WeatherCondition.CLEAR, PitchCondition.GOOD, False
        )
        
        test_player_state = next(p for p in simulator.home_team.players if p.player_id == 1)
        
        # Set stamina to 0
        test_player_state.stamina = 0.0
        
        # Update fatigue
        simulator._update_fatigue()
        
        # CA should be reduced by 10%
        expected_ca = 100 * 0.90
        
        assert abs(test_player_state.effective_ca - expected_ca) < 0.1, \
            f"At 0% stamina, 10% penalty should apply. Expected {expected_ca}, got {test_player_state.effective_ca}"
        
        # Stamina should not go below 0
        assert test_player_state.stamina >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
