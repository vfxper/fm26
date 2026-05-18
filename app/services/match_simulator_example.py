"""
Match Simulator Example

Demonstrates how to use the MatchSimulator class to simulate a match.
This example shows the basic usage without requiring a database connection.
"""

from app.services.match_simulator import MatchSimulator
from app.models.match import WeatherCondition, PitchCondition
from app.models.match_event import EventType
from unittest.mock import Mock


def create_example_player(player_id, name, position, ca=100):
    """Create an example player for demonstration"""
    player = Mock()
    player.id = player_id
    player.name = name
    player.position = position
    player.ca = ca
    player.pa = ca + 20
    
    # Set attributes (1-20 scale)
    player.passing = 12
    player.vision = 12
    player.technique = 12
    player.finishing = 12
    player.composure = 12
    player.dribbling = 12
    player.agility = 12
    player.tackling = 12
    player.positioning = 12
    player.work_rate = 12
    player.stamina = 15
    player.pace = 12
    player.anticipation = 12
    
    return player


def create_example_squad(team_name, start_id=1):
    """Create an example squad of 11 players"""
    squad = []
    
    # Goalkeeper
    squad.append((
        create_example_player(start_id, f"{team_name} Goalkeeper", "GK", ca=85),
        1,   # squad number
        75   # morale
    ))
    
    # Defenders (4)
    for i in range(4):
        squad.append((
            create_example_player(start_id + i + 1, f"{team_name} Defender {i+1}", "D C", ca=80),
            i + 2,
            75
        ))
    
    # Midfielders (4)
    for i in range(4):
        squad.append((
            create_example_player(start_id + i + 5, f"{team_name} Midfielder {i+1}", "M C", ca=90),
            i + 6,
            75
        ))
    
    # Forwards (2)
    for i in range(2):
        squad.append((
            create_example_player(start_id + i + 9, f"{team_name} Forward {i+1}", "ST C", ca=95),
            i + 10,
            75
        ))
    
    return squad


def main():
    """Run an example match simulation"""
    print("=" * 80)
    print("MATCH SIMULATOR EXAMPLE")
    print("=" * 80)
    print()
    
    # Create simulator
    simulator = MatchSimulator()
    
    # Create squads
    print("Creating squads...")
    home_squad = create_example_squad("Manchester", start_id=1)
    away_squad = create_example_squad("Liverpool", start_id=100)
    
    print(f"Home squad: {len(home_squad)} players")
    print(f"Away squad: {len(away_squad)} players")
    print()
    
    # Simulate match
    print("Simulating match...")
    print("Match: Manchester FC vs Liverpool FC")
    print("Weather: Clear")
    print("Pitch: Good")
    print("Home advantage: Applied (+5% CA)")
    print()
    
    result = simulator.simulate_match(
        home_club_id=1,
        home_club_name="Manchester FC",
        home_players=home_squad,
        away_club_id=2,
        away_club_name="Liverpool FC",
        away_players=away_squad,
        weather=WeatherCondition.CLEAR,
        pitch_condition=PitchCondition.GOOD,
        home_advantage=True
    )
    
    # Display results
    print("=" * 80)
    print("MATCH RESULT")
    print("=" * 80)
    print()
    print(f"Final Score: Manchester FC {result.home_score} - {result.away_score} Liverpool FC")
    print(f"Match Duration: {result.match_duration} minutes")
    print(f"Processing Time: {result.processing_time:.3f} seconds")
    print()
    
    # Display statistics
    print("=" * 80)
    print("MATCH STATISTICS")
    print("=" * 80)
    print()
    print(f"{'Statistic':<25} {'Manchester FC':>15} {'Liverpool FC':>15}")
    print("-" * 80)
    print(f"{'Possession':<25} {result.home_statistics['possession']:>14}% {result.away_statistics['possession']:>14}%")
    print(f"{'Shots':<25} {result.home_statistics['shots']:>15} {result.away_statistics['shots']:>15}")
    print(f"{'Shots on Target':<25} {result.home_statistics['shots_on_target']:>15} {result.away_statistics['shots_on_target']:>15}")
    print(f"{'Passes':<25} {result.home_statistics['passes']:>15} {result.away_statistics['passes']:>15}")
    print(f"{'Pass Accuracy':<25} {result.home_statistics['pass_accuracy']:>14}% {result.away_statistics['pass_accuracy']:>14}%")
    print(f"{'Tackles':<25} {result.home_statistics['tackles']:>15} {result.away_statistics['tackles']:>15}")
    print(f"{'Fouls':<25} {result.home_statistics['fouls']:>15} {result.away_statistics['fouls']:>15}")
    print(f"{'Yellow Cards':<25} {result.home_statistics['yellow_cards']:>15} {result.away_statistics['yellow_cards']:>15}")
    print(f"{'Red Cards':<25} {result.home_statistics['red_cards']:>15} {result.away_statistics['red_cards']:>15}")
    print()
    
    # Display key events
    print("=" * 80)
    print("KEY EVENTS")
    print("=" * 80)
    print()
    
    # Filter for important events (goals, cards)
    key_events = [
        e for e in result.events
        if e['event_type'] in [EventType.GOAL.value, EventType.YELLOW_CARD.value, EventType.RED_CARD.value]
    ]
    
    if key_events:
        for event in key_events:
            minute = event['minute']
            event_type = event['event_type']
            team = "Manchester FC" if event['team'] == 'home' else "Liverpool FC"
            player_id = event['player_id']
            
            print(f"{minute:>3}' - {event_type.upper():<15} - {team} (Player #{player_id})")
    else:
        print("No goals or cards in this match.")
    
    print()
    
    # Display event summary
    print("=" * 80)
    print("EVENT SUMMARY")
    print("=" * 80)
    print()
    
    event_counts = {}
    for event in result.events:
        event_type = event['event_type']
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    print(f"Total Events: {len(result.events)}")
    print()
    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {event_type:<20} {count:>5}")
    
    print()
    print("=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
