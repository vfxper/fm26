"""
Demo: Player Search + Match Simulation
=======================================
This script demonstrates:
1. Loading players from the CSV file (2600球员属性.csv)
2. Searching for any player by name
3. Simulating a match between two teams

Usage:
    python demo_search_and_simulate.py
"""

import csv
import random
import os
import sys

# ─── Player Database ─────────────────────────────────────────────────────────

class PlayerDB:
    """Simple in-memory player database loaded from CSV."""
    
    def __init__(self, csv_path):
        self.players = []
        self._load(csv_path)
    
    def _load(self, csv_path):
        """Load players from CSV file."""
        print(f"📂 Loading players from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header row
            
            for row in reader:
                if len(row) < 50:
                    continue
                try:
                    player = {
                        'name': row[0],
                        'club': row[3] if len(row) > 3 else '',
                        'nationality': row[4] if len(row) > 4 else '',
                        'position': row[2] if len(row) > 2 else '',
                        'age': int(row[1]) if len(row) > 1 and row[1].isdigit() else 0,
                        'ca': int(row[5]) if len(row) > 5 and row[5].isdigit() else 100,
                        'pa': int(row[6]) if len(row) > 6 and row[6].isdigit() else 100,
                        # Technical attributes (columns 7-20)
                        'corners': int(row[7]) if len(row) > 7 and row[7].isdigit() else 10,
                        'crossing': int(row[8]) if len(row) > 8 and row[8].isdigit() else 10,
                        'dribbling': int(row[9]) if len(row) > 9 and row[9].isdigit() else 10,
                        'finishing': int(row[10]) if len(row) > 10 and row[10].isdigit() else 10,
                        'first_touch': int(row[11]) if len(row) > 11 and row[11].isdigit() else 10,
                        'heading': int(row[13]) if len(row) > 13 and row[13].isdigit() else 10,
                        'passing': int(row[17]) if len(row) > 17 and row[17].isdigit() else 10,
                        'tackling': int(row[19]) if len(row) > 19 and row[19].isdigit() else 10,
                        'technique': int(row[20]) if len(row) > 20 and row[20].isdigit() else 10,
                        # Mental attributes
                        'composure': int(row[24]) if len(row) > 24 and row[24].isdigit() else 10,
                        'decisions': int(row[26]) if len(row) > 26 and row[26].isdigit() else 10,
                        'determination': int(row[27]) if len(row) > 27 and row[27].isdigit() else 10,
                        'vision': int(row[33]) if len(row) > 33 and row[33].isdigit() else 10,
                        # Physical attributes
                        'pace': int(row[40]) if len(row) > 40 and row[40].isdigit() else 10,
                        'stamina': int(row[39]) if len(row) > 39 and row[39].isdigit() else 10,
                        'strength': int(row[42]) if len(row) > 42 and row[42].isdigit() else 10,
                    }
                    self.players.append(player)
                except (ValueError, IndexError):
                    continue
        
        print(f"✅ Loaded {len(self.players):,} players")
    
    def search(self, query, limit=10):
        """Search players by name (case-insensitive partial match)."""
        query_lower = query.lower()
        results = []
        for p in self.players:
            if query_lower in p['name'].lower():
                results.append(p)
                if len(results) >= limit:
                    break
        return results
    
    def search_by_club(self, club_name, limit=25):
        """Search players by club name."""
        club_lower = club_name.lower()
        return [p for p in self.players if club_lower in p['club'].lower()][:limit]
    
    def search_by_position(self, position, min_ca=0, limit=20):
        """Search players by position with minimum CA."""
        pos_lower = position.lower()
        results = [p for p in self.players 
                   if pos_lower in p['position'].lower() and p['ca'] >= min_ca]
        results.sort(key=lambda x: x['ca'], reverse=True)
        return results[:limit]
    
    def get_top_players(self, limit=20):
        """Get top players by CA."""
        sorted_players = sorted(self.players, key=lambda x: x['ca'], reverse=True)
        return sorted_players[:limit]


# ─── Match Simulator ─────────────────────────────────────────────────────────

class SimpleMatchSimulator:
    """Simplified match simulator for demonstration."""
    
    def __init__(self):
        self.events = []
        self.home_score = 0
        self.away_score = 0
    
    def simulate(self, home_team, away_team):
        """Simulate a match between two teams."""
        self.events = []
        self.home_score = 0
        self.away_score = 0
        
        # Calculate team strengths
        home_strength = sum(p['ca'] for p in home_team) / len(home_team)
        away_strength = sum(p['ca'] for p in away_team) / len(away_team)
        
        # Home advantage (+5%)
        home_strength *= 1.05
        
        # Simulate 90 minutes
        for minute in range(1, 91):
            # Chance of event each minute (~15% chance)
            if random.random() < 0.15:
                event = self._generate_event(minute, home_team, away_team, 
                                            home_strength, away_strength)
                if event:
                    self.events.append(event)
        
        return {
            'home_score': self.home_score,
            'away_score': self.away_score,
            'events': self.events,
            'home_possession': round(home_strength / (home_strength + away_strength) * 100),
            'away_possession': round(away_strength / (home_strength + away_strength) * 100),
        }
    
    def _generate_event(self, minute, home_team, away_team, home_str, away_str):
        """Generate a match event."""
        total_str = home_str + away_str
        is_home = random.random() < (home_str / total_str)
        team = home_team if is_home else away_team
        team_name = "HOME" if is_home else "AWAY"
        
        # Event type probabilities
        roll = random.random()
        
        if roll < 0.03:  # 3% chance of goal
            scorer = random.choice(team)
            if is_home:
                self.home_score += 1
            else:
                self.away_score += 1
            return {
                'minute': minute,
                'type': '⚽ GOAL',
                'team': team_name,
                'player': scorer['name'],
                'detail': f"Score: {self.home_score}-{self.away_score}"
            }
        elif roll < 0.15:  # 12% chance of shot
            shooter = random.choice(team)
            on_target = random.random() < 0.4
            return {
                'minute': minute,
                'type': '🎯 Shot' if on_target else '💨 Shot (off target)',
                'team': team_name,
                'player': shooter['name'],
                'detail': 'On target' if on_target else 'Wide'
            }
        elif roll < 0.35:  # 20% chance of pass/chance
            passer = random.choice(team)
            return {
                'minute': minute,
                'type': '🔑 Key Pass',
                'team': team_name,
                'player': passer['name'],
                'detail': 'Creates chance'
            }
        elif roll < 0.45:  # 10% chance of tackle
            tackler = random.choice(team)
            return {
                'minute': minute,
                'type': '🦶 Tackle',
                'team': team_name,
                'player': tackler['name'],
                'detail': 'Ball won'
            }
        elif roll < 0.50:  # 5% chance of foul/card
            fouler = random.choice(team)
            is_yellow = random.random() < 0.3
            return {
                'minute': minute,
                'type': '🟡 Yellow Card' if is_yellow else '⚠️ Foul',
                'team': team_name,
                'player': fouler['name'],
                'detail': 'Cautioned' if is_yellow else 'Free kick awarded'
            }
        
        return None


# ─── Demo Functions ──────────────────────────────────────────────────────────

def print_player(player, index=None):
    """Print a player's info in a nice format."""
    prefix = f"  {index}." if index else "  •"
    ca_bar = "█" * (player['ca'] // 10) + "░" * (20 - player['ca'] // 10)
    print(f"{prefix} {player['name']:<25} | {player['position']:<10} | Age: {player['age']:>2} | "
          f"CA: {player['ca']:>3} [{ca_bar}] | Club: {player['club']}")


def demo_search(db):
    """Demonstrate player search functionality."""
    print("\n" + "=" * 80)
    print("🔍 PLAYER SEARCH DEMO")
    print("=" * 80)
    
    # Search by name
    searches = ["Messi", "Ronaldo", "Haaland", "Mbappe", "Pedri", "Bellingham", "Vinicius"]
    
    for query in searches:
        results = db.search(query, limit=3)
        print(f"\n  Search: '{query}' → {len(results)} result(s)")
        for r in results:
            print_player(r)
    
    # Search by club
    print(f"\n{'─' * 80}")
    print("  🏟️  Players from 'Barcelona':")
    barcelona = db.search_by_club("Barcelona", limit=5)
    for p in barcelona:
        print_player(p)
    
    # Top strikers
    print(f"\n{'─' * 80}")
    print("  ⚽ Top Strikers (CA > 150):")
    strikers = db.search_by_position("ST", min_ca=150, limit=5)
    for p in strikers:
        print_player(p)
    
    # Top players overall
    print(f"\n{'─' * 80}")
    print("  🏆 Top 10 Players Overall:")
    top = db.get_top_players(10)
    for i, p in enumerate(top, 1):
        print_player(p, i)


def demo_simulation(db):
    """Demonstrate match simulation."""
    print("\n" + "=" * 80)
    print("⚽ MATCH SIMULATION DEMO")
    print("=" * 80)
    
    # Get two teams
    home_players = db.search_by_club("Manchester City", limit=11)
    away_players = db.search_by_club("Real Madrid", limit=11)
    
    if len(home_players) < 11:
        home_players = db.get_top_players(11)
    if len(away_players) < 11:
        away_players = db.players[11:22]
    
    home_name = home_players[0]['club'] if home_players else "Home FC"
    away_name = away_players[0]['club'] if away_players else "Away FC"
    
    print(f"\n  🏟️  {home_name} vs {away_name}")
    print(f"  {'─' * 50}")
    
    # Show lineups
    print(f"\n  📋 {home_name} Lineup:")
    for p in home_players[:11]:
        print(f"     {p['name']:<25} ({p['position']}) CA: {p['ca']}")
    
    print(f"\n  📋 {away_name} Lineup:")
    for p in away_players[:11]:
        print(f"     {p['name']:<25} ({p['position']}) CA: {p['ca']}")
    
    # Simulate
    print(f"\n  ⏱️  KICK OFF!")
    print(f"  {'─' * 50}")
    
    simulator = SimpleMatchSimulator()
    result = simulator.simulate(home_players[:11], away_players[:11])
    
    # Print events
    for event in result['events']:
        team_indicator = "🔵" if event['team'] == "HOME" else "🔴"
        print(f"  {event['minute']:>3}' {team_indicator} {event['type']:<20} {event['player']:<25} {event['detail']}")
    
    # Final result
    print(f"\n  {'═' * 50}")
    print(f"  🏁 FULL TIME: {home_name} {result['home_score']} - {result['away_score']} {away_name}")
    print(f"  📊 Possession: {result['home_possession']}% - {result['away_possession']}%")
    print(f"  {'═' * 50}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    csv_path = os.path.join(os.path.dirname(__file__), '2600球员属性.csv')
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Load database
    db = PlayerDB(csv_path)
    
    # Run demos
    demo_search(db)
    demo_simulation(db)
    
    print("\n✅ Demo complete!")
