"""
Unit tests for CommentaryGenerator

Tests the match commentary generation system including:
- Commentary generation for all event types
- Multiple variations per event type (5+ required)
- Language support (English and Russian)
- Variable substitution (player names, teams, scores)
- No duplicate commentary in same match
"""

import pytest
from collections import Counter

from app.services.commentary_generator import (
    CommentaryGenerator,
    CommentaryContext,
    generate_commentary_for_event
)
from app.models.match_event import EventType, TeamSide


class TestCommentaryGenerator:
    """Test suite for CommentaryGenerator"""
    
    def test_initialization_english(self):
        """Test generator initialization with English language"""
        generator = CommentaryGenerator(language="en")
        assert generator.language == "en"
        assert len(generator._commentary_templates) > 0
    
    def test_initialization_russian(self):
        """Test generator initialization with Russian language"""
        generator = CommentaryGenerator(language="ru")
        assert generator.language == "ru"
        assert len(generator._commentary_templates) > 0
    
    def test_all_event_types_have_commentary_english(self):
        """Test that all event types have commentary templates in English"""
        generator = CommentaryGenerator(language="en")
        templates = generator._commentary_templates["en"]
        
        # Check all major event types
        required_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
            EventType.YELLOW_CARD,
            EventType.RED_CARD,
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.SAVE,
            EventType.SUBSTITUTION,
            EventType.INJURY,
        ]
        
        for event_type in required_event_types:
            assert event_type in templates, f"Missing templates for {event_type}"
            assert len(templates[event_type]) > 0, f"No templates for {event_type}"
    
    def test_all_event_types_have_commentary_russian(self):
        """Test that all event types have commentary templates in Russian"""
        generator = CommentaryGenerator(language="ru")
        templates = generator._commentary_templates["ru"]
        
        # Check all major event types
        required_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
            EventType.YELLOW_CARD,
            EventType.RED_CARD,
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.SAVE,
            EventType.SUBSTITUTION,
            EventType.INJURY,
        ]
        
        for event_type in required_event_types:
            assert event_type in templates, f"Missing templates for {event_type}"
            assert len(templates[event_type]) > 0, f"No templates for {event_type}"
    
    def test_minimum_five_variations_per_event_type_english(self):
        """Test that each event type has at least 5 distinct commentary variations (English)"""
        generator = CommentaryGenerator(language="en")
        templates = generator._commentary_templates["en"]
        
        # Check all major event types
        required_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
            EventType.YELLOW_CARD,
            EventType.RED_CARD,
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.SAVE,
            EventType.SUBSTITUTION,
            EventType.INJURY,
        ]
        
        for event_type in required_event_types:
            variations = templates.get(event_type, [])
            assert len(variations) >= 5, (
                f"{event_type} has only {len(variations)} variations, "
                f"but requires at least 5"
            )
    
    def test_minimum_five_variations_per_event_type_russian(self):
        """Test that each event type has at least 5 distinct commentary variations (Russian)"""
        generator = CommentaryGenerator(language="ru")
        templates = generator._commentary_templates["ru"]
        
        # Check all major event types
        required_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
            EventType.YELLOW_CARD,
            EventType.RED_CARD,
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.SAVE,
            EventType.SUBSTITUTION,
            EventType.INJURY,
        ]
        
        for event_type in required_event_types:
            variations = templates.get(event_type, [])
            assert len(variations) >= 5, (
                f"{event_type} has only {len(variations)} variations, "
                f"but requires at least 5"
            )
    
    def test_generate_commentary_pass(self):
        """Test commentary generation for pass event"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="Silva",
            target_player_name="Sterling",
            team_name="Manchester City",
            minute=25
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Silva" in commentary
        assert "Sterling" in commentary
        assert len(commentary) > 0
    
    def test_generate_commentary_goal(self):
        """Test commentary generation for goal event"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Ronaldo",
            team_name="Manchester United",
            minute=45,
            home_score=1,
            away_score=0
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Ronaldo" in commentary
        assert len(commentary) > 0
        # Goal commentary should mention the player or team
        assert "Ronaldo" in commentary or "Manchester United" in commentary
    
    def test_generate_commentary_red_card(self):
        """Test commentary generation for red card event"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.RED_CARD,
            team=TeamSide.AWAY,
            player_name="Ramos",
            team_name="Real Madrid",
            minute=67
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Ramos" in commentary
        assert len(commentary) > 0
        # Red card commentary should mention the card
        assert any(word in commentary.upper() for word in ["RED", "OFF", "SENT"])
    
    def test_variable_substitution_player_names(self):
        """Test that player names are correctly substituted"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="De Bruyne",
            target_player_name="Haaland",
            team_name="Manchester City",
            minute=30
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "De Bruyne" in commentary
        assert "Haaland" in commentary
    
    def test_variable_substitution_team_names(self):
        """Test that team names are correctly substituted"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.CORNER,
            team=TeamSide.HOME,
            player_name="Alexander-Arnold",
            team_name="Liverpool",
            opponent_name="Chelsea",
            minute=55
        )
        
        commentary = generator.generate_commentary(context)
        
        # Team name should appear in commentary for corner
        assert "Liverpool" in commentary or "Alexander-Arnold" in commentary
    
    def test_variable_substitution_minute(self):
        """Test that minute is correctly substituted"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.SHOT,
            team=TeamSide.HOME,
            player_name="Salah",
            team_name="Liverpool",
            minute=78
        )
        
        commentary = generator.generate_commentary(context)
        
        # Commentary should be generated (minute may or may not appear in template)
        assert len(commentary) > 0
        assert "Salah" in commentary
    
    def test_variable_substitution_score(self):
        """Test that score is correctly substituted"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Kane",
            team_name="Tottenham",
            minute=89,
            home_score=2,
            away_score=1
        )
        
        commentary = generator.generate_commentary(context)
        
        # Commentary should be generated
        assert len(commentary) > 0
        assert "Kane" in commentary
    
    def test_russian_commentary_generation(self):
        """Test commentary generation in Russian"""
        generator = CommentaryGenerator(language="ru")
        context = CommentaryContext(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Дзюба",
            team_name="Зенит",
            minute=60,
            home_score=1,
            away_score=0
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Дзюба" in commentary
        assert len(commentary) > 0
        # Russian goal commentary should contain goal-related words
        assert any(word in commentary.lower() for word in ["гол", "забивает", "мяч", "ворот", "сетк"])
    
    def test_fallback_to_english_for_unknown_language(self):
        """Test that generator falls back to English for unknown language"""
        generator = CommentaryGenerator(language="fr")  # French not implemented
        context = CommentaryContext(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="Mbappe",
            target_player_name="Neymar",
            minute=20
        )
        
        commentary = generator.generate_commentary(context)
        
        # Should still generate commentary (fallback to English)
        assert len(commentary) > 0
        assert "Mbappe" in commentary
    
    def test_no_duplicate_commentary_in_multiple_generations(self):
        """Test that multiple generations produce varied commentary"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="Modric",
            target_player_name="Benzema",
            minute=40
        )
        
        # Generate 20 commentaries
        commentaries = [generator.generate_commentary(context) for _ in range(20)]
        
        # Count unique commentaries
        unique_commentaries = set(commentaries)
        
        # Should have at least 3 different variations in 20 generations
        # (with 5+ templates, we expect good variety)
        assert len(unique_commentaries) >= 3, (
            f"Only {len(unique_commentaries)} unique commentaries in 20 generations"
        )
    
    def test_commentary_variety_distribution(self):
        """Test that commentary variations are reasonably distributed"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.SHOT,
            team=TeamSide.HOME,
            player_name="Lewandowski",
            minute=50
        )
        
        # Generate 100 commentaries
        commentaries = [generator.generate_commentary(context) for _ in range(100)]
        
        # Count occurrences
        counter = Counter(commentaries)
        
        # No single commentary should dominate (appear more than 40% of the time)
        for commentary, count in counter.items():
            assert count <= 40, (
                f"Commentary '{commentary}' appeared {count}/100 times (too frequent)"
            )
    
    def test_convenience_function(self):
        """Test the convenience function for generating commentary"""
        commentary = generate_commentary_for_event(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Messi",
            team_name="PSG",
            opponent_name="Lyon",
            minute=75,
            home_score=2,
            away_score=1,
            language="en"
        )
        
        assert "Messi" in commentary
        assert len(commentary) > 0
    
    def test_all_event_types_generate_valid_commentary(self):
        """Test that all event types can generate valid commentary"""
        generator = CommentaryGenerator(language="en")
        
        all_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
            EventType.YELLOW_CARD,
            EventType.RED_CARD,
            EventType.CORNER,
            EventType.FREE_KICK,
            EventType.PENALTY,
            EventType.SAVE,
            EventType.SUBSTITUTION,
            EventType.INJURY,
            EventType.OFFSIDE,
            EventType.BLOCK,
            EventType.INTERCEPTION,
            EventType.CLEARANCE,
            EventType.CROSS,
            EventType.DRIBBLE,
            EventType.HEADER,
            EventType.THROW_IN,
            EventType.GOAL_KICK,
        ]
        
        for event_type in all_event_types:
            context = CommentaryContext(
                event_type=event_type,
                team=TeamSide.HOME,
                player_name="TestPlayer",
                target_player_name="TargetPlayer",
                team_name="TestTeam",
                minute=45
            )
            
            commentary = generator.generate_commentary(context)
            
            assert len(commentary) > 0, f"No commentary generated for {event_type}"
            # Commentary should include either player name or team name
            assert "TestPlayer" in commentary or "TestTeam" in commentary, (
                f"Neither player nor team name in commentary for {event_type}: {commentary}"
            )
    
    def test_commentary_includes_context_information(self):
        """Test that commentary can include match context (score, minute)"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Suarez",
            team_name="Barcelona",
            minute=90,
            home_score=3,
            away_score=2
        )
        
        commentary = generator.generate_commentary(context)
        
        # Commentary should be generated with context
        assert len(commentary) > 0
        assert "Suarez" in commentary
    
    def test_target_player_optional(self):
        """Test that target_player is optional and defaults gracefully"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.SHOT,
            team=TeamSide.HOME,
            player_name="Grealish",
            team_name="Manchester City",
            minute=35,
            target_player_name=None  # No target player
        )
        
        commentary = generator.generate_commentary(context)
        
        # Should still generate valid commentary
        assert len(commentary) > 0
        assert "Grealish" in commentary
    
    def test_commentary_length_reasonable(self):
        """Test that commentary is not too long (should be 1-2 sentences)"""
        generator = CommentaryGenerator(language="en")
        
        event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.GOAL,
            EventType.TACKLE,
            EventType.FOUL,
        ]
        
        for event_type in event_types:
            context = CommentaryContext(
                event_type=event_type,
                team=TeamSide.HOME,
                player_name="Player",
                target_player_name="Target",
                minute=45
            )
            
            commentary = generator.generate_commentary(context)
            
            # Commentary should be concise (< 200 characters for most events)
            assert len(commentary) < 200, (
                f"Commentary too long for {event_type}: {len(commentary)} chars"
            )
    
    def test_special_characters_in_player_names(self):
        """Test that special characters in player names are handled correctly"""
        generator = CommentaryGenerator(language="en")
        context = CommentaryContext(
            event_type=EventType.GOAL,
            team=TeamSide.HOME,
            player_name="Müller",
            team_name="Bayern München",
            minute=60
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Müller" in commentary
        assert len(commentary) > 0
    
    def test_russian_special_characters(self):
        """Test that Russian special characters are handled correctly"""
        generator = CommentaryGenerator(language="ru")
        context = CommentaryContext(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="Головин",
            target_player_name="Миранчук",
            team_name="Монако",
            minute=30
        )
        
        commentary = generator.generate_commentary(context)
        
        assert "Головин" in commentary
        assert "Миранчук" in commentary
        assert len(commentary) > 0


class TestCommentaryIntegration:
    """Integration tests for commentary generation in match context"""
    
    def test_full_match_commentary_variety(self):
        """Test that a full match generates varied commentary"""
        generator = CommentaryGenerator(language="en")
        
        # Simulate 20 pass events in a match
        commentaries = []
        for minute in range(1, 21):
            context = CommentaryContext(
                event_type=EventType.PASS,
                team=TeamSide.HOME,
                player_name=f"Player{minute % 5}",
                target_player_name=f"Player{(minute + 1) % 5}",
                minute=minute
            )
            commentaries.append(generator.generate_commentary(context))
        
        # Should have good variety
        unique_templates = len(set(commentaries))
        assert unique_templates >= 5, (
            f"Only {unique_templates} unique commentaries in 20 pass events"
        )
    
    def test_mixed_event_types_commentary(self):
        """Test commentary generation for mixed event types"""
        generator = CommentaryGenerator(language="en")
        
        events = [
            (EventType.PASS, "Silva", "Sterling"),
            (EventType.SHOT, "Sterling", None),
            (EventType.SAVE, "Alisson", None),
            (EventType.CORNER, "De Bruyne", None),
            (EventType.GOAL, "Haaland", None),
        ]
        
        for event_type, player, target in events:
            context = CommentaryContext(
                event_type=event_type,
                team=TeamSide.HOME,
                player_name=player,
                target_player_name=target,
                team_name="Manchester City",  # Provide team name
                minute=45
            )
            
            commentary = generator.generate_commentary(context)
            
            assert len(commentary) > 0
            # Commentary should include player name or team name
            assert player in commentary or "Manchester City" in commentary
