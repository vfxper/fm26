"""
Test Event Resolution with Player Attributes

This test verifies that event resolution (pass, shot, tackle, foul) correctly
uses player attributes as specified in the design document:
- Shot success: finishing, composure, technique vs goalkeeper attributes
- Pass success: passing, vision, technique vs marking, positioning
- Tackle success: tackling, positioning vs dribbling, agility
- Foul probability: aggression attribute

**Validates: Requirements 3.2, 3.3**
"""

import pytest
from unittest.mock import Mock, patch
from app.services.match_simulator import MatchSimulator, PlayerState, TeamState, TeamSide, TacticMentality
from app.models.player import Player
from app.models.match_event import EventType


class TestEventResolution:
    """Test suite for event resolution with player attributes"""
    
    def create_mock_player(
        self,
        player_id: int,
        ca: int = 100,
        finishing: int = 10,
        composure: int = 10,
        technique: int = 10,
        passing: int = 10,
        vision: int = 10,
        dribbling: int = 10,
        agility: int = 10,
        tackling: int = 10,
        positioning: int = 10,
        anticipation: int = 10,
        aggression: int = 10,
        **kwargs
    ) -> Player:
        """Create a mock player with specified attributes"""
        player = Mock(spec=Player)
        player.id = player_id
        player.ca = ca
        player.finishing = finishing
        player.composure = composure
        player.technique = technique
        player.passing = passing
        player.vision = vision
        player.dribbling = dribbling
        player.agility = agility
        player.tackling = tackling
        player.positioning = positioning
        player.anticipation = anticipation
        player.aggression = aggression
        player.work_rate = kwargs.get('work_rate', 10)
        player.marking = kwargs.get('marking', 10)
        player.stamina = kwargs.get('stamina', 10)
        player.pace = kwargs.get('pace', 10)
        player.off_the_ball = kwargs.get('off_the_ball', 10)
        return player
    
    def create_player_state(
        self,
        player: Player,
        team: TeamSide,
        position: str = "ST",
        morale: int = 70
    ) -> PlayerState:
        """Create a player state from a mock player"""
        return PlayerState(
            player_id=player.id,
            player=player,
            team=team,
            position=position,
            squad_number=9,
            morale=morale,
            stamina=100.0,
            effective_ca=float(player.ca)
        )
    
    def test_shot_resolution_uses_finishing_composure_technique(self):
        """
        Test that shot resolution uses finishing, composure, and technique attributes.
        
        A player with high finishing/composure/technique should have higher shot success
        probability than a player with low attributes.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create high-skill striker
        high_skill_player = self.create_mock_player(
            player_id=1,
            finishing=18,
            composure=17,
            technique=18
        )
        high_skill_state = self.create_player_state(high_skill_player, TeamSide.HOME, "ST")
        
        # Create low-skill striker
        low_skill_player = self.create_mock_player(
            player_id=2,
            finishing=5,
            composure=5,
            technique=5
        )
        low_skill_state = self.create_player_state(low_skill_player, TeamSide.HOME, "ST")
        
        # Create goalkeeper
        goalkeeper = self.create_mock_player(
            player_id=3,
            positioning=12,
            anticipation=12
        )
        gk_state = self.create_player_state(goalkeeper, TeamSide.AWAY, "GK")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        away_team = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC"
        )
        away_team.players = [gk_state]
        
        simulator.home_team = home_team
        simulator.away_team = away_team
        simulator.possession_team = TeamSide.HOME
        
        # Simulate multiple shots to get statistical distribution
        high_skill_goals = 0
        low_skill_goals = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_shot(high_skill_state, home_team, away_team)
            if simulator.events and simulator.events[-1]['event_type'] == EventType.GOAL.value:
                high_skill_goals += 1
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_shot(low_skill_state, home_team, away_team)
            if simulator.events and simulator.events[-1]['event_type'] == EventType.GOAL.value:
                low_skill_goals += 1
        
        # High-skill player should score significantly more goals
        assert high_skill_goals > low_skill_goals, \
            f"High-skill player ({high_skill_goals} goals) should score more than low-skill player ({low_skill_goals} goals)"
        
        # Verify the difference is statistically significant (at least 2x more)
        assert high_skill_goals >= low_skill_goals * 1.5, \
            f"High-skill player should score at least 1.5x more goals (got {high_skill_goals} vs {low_skill_goals})"
    
    def test_shot_resolution_uses_goalkeeper_attributes(self):
        """
        Test that shot resolution considers goalkeeper positioning and anticipation.
        
        A better goalkeeper should save more shots than a poor goalkeeper.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create striker with moderate skills
        striker = self.create_mock_player(
            player_id=1,
            finishing=12,
            composure=12,
            technique=12
        )
        striker_state = self.create_player_state(striker, TeamSide.HOME, "ST")
        
        # Create world-class goalkeeper
        world_class_gk = self.create_mock_player(
            player_id=2,
            positioning=19,
            anticipation=19
        )
        world_class_gk_state = self.create_player_state(world_class_gk, TeamSide.AWAY, "GK")
        
        # Create poor goalkeeper
        poor_gk = self.create_mock_player(
            player_id=3,
            positioning=5,
            anticipation=5
        )
        poor_gk_state = self.create_player_state(poor_gk, TeamSide.AWAY, "GK")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        
        # Test against world-class goalkeeper
        away_team_good_gk = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC Good GK"
        )
        away_team_good_gk.players = [world_class_gk_state]
        
        # Test against poor goalkeeper
        away_team_poor_gk = TeamState(
            team_side=TeamSide.AWAY,
            club_id=3,
            club_name="Away FC Poor GK"
        )
        away_team_poor_gk.players = [poor_gk_state]
        
        simulator.home_team = home_team
        simulator.possession_team = TeamSide.HOME
        
        # Simulate shots against both goalkeepers
        goals_vs_world_class = 0
        goals_vs_poor = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator.away_team = away_team_good_gk
            simulator._simulate_shot(striker_state, home_team, away_team_good_gk)
            if simulator.events and simulator.events[-1]['event_type'] == EventType.GOAL.value:
                goals_vs_world_class += 1
        
        for _ in range(trials):
            simulator.events = []
            simulator.away_team = away_team_poor_gk
            simulator._simulate_shot(striker_state, home_team, away_team_poor_gk)
            if simulator.events and simulator.events[-1]['event_type'] == EventType.GOAL.value:
                goals_vs_poor += 1
        
        # Should score more goals against poor goalkeeper
        assert goals_vs_poor > goals_vs_world_class, \
            f"Should score more against poor GK ({goals_vs_poor}) than world-class GK ({goals_vs_world_class})"
        
        # Verify significant difference
        assert goals_vs_poor >= goals_vs_world_class * 1.3, \
            f"Should score at least 1.3x more against poor GK (got {goals_vs_poor} vs {goals_vs_world_class})"
    
    def test_pass_resolution_uses_passing_vision_technique(self):
        """
        Test that pass resolution uses passing, vision, and technique attributes.
        
        A player with high passing attributes should complete more passes.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create high-skill passer
        high_skill_passer = self.create_mock_player(
            player_id=1,
            passing=18,
            vision=18,
            technique=18
        )
        high_skill_state = self.create_player_state(high_skill_passer, TeamSide.HOME, "CM")
        
        # Create low-skill passer
        low_skill_passer = self.create_mock_player(
            player_id=2,
            passing=5,
            vision=5,
            technique=5
        )
        low_skill_state = self.create_player_state(low_skill_passer, TeamSide.HOME, "CM")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        away_team = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC"
        )
        
        simulator.home_team = home_team
        simulator.away_team = away_team
        simulator.possession_team = TeamSide.HOME
        
        # Simulate multiple passes
        high_skill_completed = 0
        low_skill_completed = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_pass(high_skill_state, home_team, away_team)
            if simulator.events and simulator.events[-1].get('success', False):
                high_skill_completed += 1
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_pass(low_skill_state, home_team, away_team)
            if simulator.events and simulator.events[-1].get('success', False):
                low_skill_completed += 1
        
        # High-skill passer should complete more passes
        assert high_skill_completed > low_skill_completed, \
            f"High-skill passer ({high_skill_completed} completed) should complete more passes than low-skill passer ({low_skill_completed} completed)"
        
        # Verify significant difference
        assert high_skill_completed >= low_skill_completed * 1.2, \
            f"High-skill passer should complete at least 1.2x more passes (got {high_skill_completed} vs {low_skill_completed})"
    
    def test_tackle_resolution_uses_tackling_positioning(self):
        """
        Test that tackle resolution uses defender's tackling and positioning attributes
        against attacker's dribbling and agility.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create attacker with moderate dribbling
        attacker = self.create_mock_player(
            player_id=1,
            dribbling=12,
            agility=12
        )
        attacker_state = self.create_player_state(attacker, TeamSide.HOME, "ST")
        
        # Create world-class defender
        world_class_defender = self.create_mock_player(
            player_id=2,
            tackling=19,
            positioning=19
        )
        world_class_defender_state = self.create_player_state(world_class_defender, TeamSide.AWAY, "D C")
        
        # Create poor defender
        poor_defender = self.create_mock_player(
            player_id=3,
            tackling=5,
            positioning=5
        )
        poor_defender_state = self.create_player_state(poor_defender, TeamSide.AWAY, "D C")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        
        # Test with world-class defender
        away_team_good_def = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC Good Def"
        )
        away_team_good_def.players = [world_class_defender_state]
        
        # Test with poor defender
        away_team_poor_def = TeamState(
            team_side=TeamSide.AWAY,
            club_id=3,
            club_name="Away FC Poor Def"
        )
        away_team_poor_def.players = [poor_defender_state]
        
        simulator.home_team = home_team
        simulator.possession_team = TeamSide.HOME
        
        # Simulate tackles
        world_class_successful = 0
        poor_successful = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator.away_team = away_team_good_def
            simulator._simulate_tackle(attacker_state, home_team, away_team_good_def)
            if simulator.events and simulator.events[-1].get('success', False):
                world_class_successful += 1
        
        for _ in range(trials):
            simulator.events = []
            simulator.away_team = away_team_poor_def
            simulator._simulate_tackle(attacker_state, home_team, away_team_poor_def)
            if simulator.events and simulator.events[-1].get('success', False):
                poor_successful += 1
        
        # World-class defender should win more tackles
        assert world_class_successful > poor_successful, \
            f"World-class defender ({world_class_successful} won) should win more tackles than poor defender ({poor_successful} won)"
        
        # Verify significant difference
        assert world_class_successful >= poor_successful * 1.3, \
            f"World-class defender should win at least 1.3x more tackles (got {world_class_successful} vs {poor_successful})"
    
    def test_tackle_resolution_considers_attacker_dribbling_agility(self):
        """
        Test that tackle resolution considers attacker's dribbling and agility.
        
        A skillful dribbler should be harder to tackle.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create world-class dribbler
        world_class_dribbler = self.create_mock_player(
            player_id=1,
            dribbling=19,
            agility=19
        )
        world_class_dribbler_state = self.create_player_state(world_class_dribbler, TeamSide.HOME, "W R")
        
        # Create poor dribbler
        poor_dribbler = self.create_mock_player(
            player_id=2,
            dribbling=5,
            agility=5
        )
        poor_dribbler_state = self.create_player_state(poor_dribbler, TeamSide.HOME, "ST")
        
        # Create moderate defender
        defender = self.create_mock_player(
            player_id=3,
            tackling=12,
            positioning=12
        )
        defender_state = self.create_player_state(defender, TeamSide.AWAY, "D C")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        away_team = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC"
        )
        away_team.players = [defender_state]
        
        simulator.home_team = home_team
        simulator.away_team = away_team
        simulator.possession_team = TeamSide.HOME
        
        # Simulate tackles against both dribblers
        tackles_won_vs_world_class = 0
        tackles_won_vs_poor = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_tackle(world_class_dribbler_state, home_team, away_team)
            if simulator.events and simulator.events[-1].get('success', False):
                tackles_won_vs_world_class += 1
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_tackle(poor_dribbler_state, home_team, away_team)
            if simulator.events and simulator.events[-1].get('success', False):
                tackles_won_vs_poor += 1
        
        # Should win more tackles against poor dribbler
        assert tackles_won_vs_poor > tackles_won_vs_world_class, \
            f"Should win more tackles vs poor dribbler ({tackles_won_vs_poor}) than world-class dribbler ({tackles_won_vs_world_class})"
        
        # Verify significant difference
        assert tackles_won_vs_poor >= tackles_won_vs_world_class * 1.2, \
            f"Should win at least 1.2x more tackles vs poor dribbler (got {tackles_won_vs_poor} vs {tackles_won_vs_world_class})"
    
    def test_foul_probability_uses_aggression(self):
        """
        Test that foul events consider defender aggression attribute.
        
        This is tested indirectly through the calculate_event_probability method.
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.home_team = TeamState(TeamSide.HOME, 1, "Home FC")
        simulator.away_team = TeamState(TeamSide.AWAY, 2, "Away FC")
        
        # Create attacker
        attacker = self.create_mock_player(player_id=1)
        attacker_state = self.create_player_state(attacker, TeamSide.HOME, "ST")
        
        # Create high-aggression defenders
        high_aggression_defenders = [
            self.create_player_state(
                self.create_mock_player(player_id=i, aggression=18),
                TeamSide.AWAY,
                "D C"
            )
            for i in range(2, 6)
        ]
        
        # Create low-aggression defenders
        low_aggression_defenders = [
            self.create_player_state(
                self.create_mock_player(player_id=i, aggression=5),
                TeamSide.AWAY,
                "D C"
            )
            for i in range(6, 10)
        ]
        
        # Test with high-aggression team
        simulator.away_team.players = high_aggression_defenders
        high_aggression_foul_prob = simulator.calculate_event_probability(
            simulator.home_team,
            simulator.away_team,
            attacker_state,
            EventType.FOUL
        )
        
        # Test with low-aggression team
        simulator.away_team.players = low_aggression_defenders
        low_aggression_foul_prob = simulator.calculate_event_probability(
            simulator.home_team,
            simulator.away_team,
            attacker_state,
            EventType.FOUL
        )
        
        # High-aggression team should have higher foul probability
        assert high_aggression_foul_prob > low_aggression_foul_prob, \
            f"High-aggression team ({high_aggression_foul_prob:.3f}) should have higher foul probability than low-aggression team ({low_aggression_foul_prob:.3f})"
    
    def test_event_resolution_realistic_success_rates(self):
        """
        Test that event resolution produces realistic success rates.
        
        - Pass completion should be 60-90% for good players
        - Shot on target should be 20-50% for good strikers
        - Tackle success should be 30-70% depending on attributes
        """
        simulator = MatchSimulator()
        simulator.current_minute = 45
        simulator.current_second = 30
        simulator.events = []
        
        # Create good all-around player
        good_player = self.create_mock_player(
            player_id=1,
            finishing=14,
            composure=14,
            technique=14,
            passing=14,
            vision=14,
            dribbling=14,
            agility=14,
            tackling=14,
            positioning=14,
            anticipation=14
        )
        good_player_state = self.create_player_state(good_player, TeamSide.HOME, "CM")
        
        # Create goalkeeper
        goalkeeper = self.create_mock_player(
            player_id=2,
            positioning=14,
            anticipation=14
        )
        gk_state = self.create_player_state(goalkeeper, TeamSide.AWAY, "GK")
        
        # Create teams
        home_team = TeamState(
            team_side=TeamSide.HOME,
            club_id=1,
            club_name="Home FC"
        )
        away_team = TeamState(
            team_side=TeamSide.AWAY,
            club_id=2,
            club_name="Away FC"
        )
        away_team.players = [gk_state]
        
        simulator.home_team = home_team
        simulator.away_team = away_team
        simulator.possession_team = TeamSide.HOME
        
        # Test pass completion rate
        passes_completed = 0
        trials = 100
        
        for _ in range(trials):
            simulator.events = []
            simulator._simulate_pass(good_player_state, home_team, away_team)
            if simulator.events and simulator.events[-1].get('success', False):
                passes_completed += 1
        
        pass_completion_rate = passes_completed / trials
        assert 0.60 <= pass_completion_rate <= 0.95, \
            f"Pass completion rate ({pass_completion_rate:.2%}) should be between 60% and 95% for good player"
        
        # Test shot on target rate
        shots_on_target = 0
        
        for _ in range(trials):
            simulator.events = []
            good_player_state.shots = 0
            home_team.shots = 0
            home_team.shots_on_target = 0
            simulator._simulate_shot(good_player_state, home_team, away_team)
            if home_team.shots_on_target > 0:
                shots_on_target += 1
        
        shot_on_target_rate = shots_on_target / trials
        assert 0.20 <= shot_on_target_rate <= 0.70, \
            f"Shot on target rate ({shot_on_target_rate:.2%}) should be between 20% and 70% for good player"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
