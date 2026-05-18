"""
Commentary Generator Example

This script demonstrates the commentary generation system with examples
of all event types in both English and Russian.
"""

from app.services.commentary_generator import (
    CommentaryGenerator,
    CommentaryContext,
    generate_commentary_for_event
)
from app.models.match_event import EventType, TeamSide


def demonstrate_commentary_generation():
    """Demonstrate commentary generation for various event types"""
    
    print("=" * 80)
    print("MATCH COMMENTARY GENERATOR - DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Example match context
    home_team = "Manchester United"
    away_team = "Liverpool"
    home_player = "Rashford"
    away_player = "Salah"
    
    # English commentary examples
    print("ENGLISH COMMENTARY EXAMPLES")
    print("-" * 80)
    print()
    
    events = [
        (EventType.PASS, home_player, "Fernandes", 15, 0, 0),
        (EventType.SHOT, home_player, None, 23, 0, 0),
        (EventType.GOAL, home_player, None, 25, 1, 0),
        (EventType.SAVE, away_player, None, 30, 1, 0),
        (EventType.CORNER, home_player, None, 32, 1, 0),
        (EventType.TACKLE, away_player, home_player, 40, 1, 0),
        (EventType.FOUL, away_player, home_player, 42, 1, 0),
        (EventType.YELLOW_CARD, away_player, None, 42, 1, 0),
        (EventType.FREE_KICK, home_player, None, 43, 1, 0),
        (EventType.GOAL, away_player, None, 55, 1, 1),
        (EventType.SUBSTITUTION, "Martial", "Rashford", 60, 1, 1),
        (EventType.RED_CARD, away_player, None, 75, 1, 1),
        (EventType.PENALTY, home_player, None, 80, 1, 1),
        (EventType.GOAL, home_player, None, 81, 2, 1),
    ]
    
    for event_type, player, target, minute, home_score, away_score in events:
        team = TeamSide.HOME if player in [home_player, "Fernandes", "Martial"] else TeamSide.AWAY
        team_name = home_team if team == TeamSide.HOME else away_team
        
        commentary = generate_commentary_for_event(
            event_type=event_type,
            team=team,
            player_name=player,
            target_player_name=target,
            team_name=team_name,
            opponent_name=away_team if team == TeamSide.HOME else home_team,
            minute=minute,
            home_score=home_score,
            away_score=away_score,
            language="en"
        )
        
        print(f"{minute}' - {commentary}")
    
    print()
    print("=" * 80)
    print()
    
    # Russian commentary examples
    print("RUSSIAN COMMENTARY EXAMPLES (ПРИМЕРЫ РУССКОГО КОММЕНТАРИЯ)")
    print("-" * 80)
    print()
    
    home_team_ru = "Зенит"
    away_team_ru = "Спартак"
    home_player_ru = "Дзюба"
    away_player_ru = "Промес"
    
    events_ru = [
        (EventType.PASS, home_player_ru, "Малком", 10, 0, 0),
        (EventType.SHOT, home_player_ru, None, 18, 0, 0),
        (EventType.GOAL, home_player_ru, None, 20, 1, 0),
        (EventType.CORNER, away_player_ru, None, 28, 1, 0),
        (EventType.TACKLE, away_player_ru, home_player_ru, 35, 1, 0),
        (EventType.FOUL, home_player_ru, away_player_ru, 38, 1, 0),
        (EventType.YELLOW_CARD, home_player_ru, None, 38, 1, 0),
        (EventType.GOAL, away_player_ru, None, 50, 1, 1),
        (EventType.SUBSTITUTION, "Азмун", home_player_ru, 65, 1, 1),
        (EventType.PENALTY, "Азмун", None, 85, 1, 1),
        (EventType.GOAL, "Азмун", None, 86, 2, 1),
    ]
    
    for event_type, player, target, minute, home_score, away_score in events_ru:
        team = TeamSide.HOME if player in [home_player_ru, "Малком", "Азмун"] else TeamSide.AWAY
        team_name = home_team_ru if team == TeamSide.HOME else away_team_ru
        
        commentary = generate_commentary_for_event(
            event_type=event_type,
            team=team,
            player_name=player,
            target_player_name=target,
            team_name=team_name,
            opponent_name=away_team_ru if team == TeamSide.HOME else home_team_ru,
            minute=minute,
            home_score=home_score,
            away_score=away_score,
            language="ru"
        )
        
        print(f"{minute}' - {commentary}")
    
    print()
    print("=" * 80)
    print()


def demonstrate_commentary_variety():
    """Demonstrate commentary variety for the same event type"""
    
    print("COMMENTARY VARIETY DEMONSTRATION")
    print("-" * 80)
    print()
    print("Generating 10 pass events to show variety:")
    print()
    
    for i in range(10):
        commentary = generate_commentary_for_event(
            event_type=EventType.PASS,
            team=TeamSide.HOME,
            player_name="De Bruyne",
            target_player_name="Haaland",
            team_name="Manchester City",
            minute=30 + i,
            language="en"
        )
        print(f"{i+1}. {commentary}")
    
    print()
    print("=" * 80)
    print()


def demonstrate_all_event_types():
    """Demonstrate commentary for all event types"""
    
    print("ALL EVENT TYPES COVERAGE")
    print("-" * 80)
    print()
    
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
            player_name="Silva",
            target_player_name="Sterling",
            team_name="Manchester City",
            opponent_name="Chelsea",
            minute=45,
            home_score=1,
            away_score=0
        )
        
        commentary = generator.generate_commentary(context)
        print(f"{event_type.value:20s} - {commentary}")
    
    print()
    print(f"Total event types covered: {len(all_event_types)}")
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_commentary_generation()
    demonstrate_commentary_variety()
    demonstrate_all_event_types()
    
    print()
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
