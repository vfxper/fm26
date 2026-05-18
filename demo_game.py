"""
🎮 Football Manager 26 - Game Demo
====================================
Demonstrates:
1. Player search (find any of 34,644 players)
2. Match simulation between real teams
"""
import csv, random, os

CSV_PATH = os.path.join(os.path.dirname(__file__), '2600球员属性.csv')

def load_players():
    players = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                players.append({
                    'name': row['name'],
                    'position': row['position'],
                    'age': int(row['age']),
                    'ca': int(row['ca']),
                    'pa': int(row['pa']),
                    'nationality': row['nationality'],
                    'club': row['club'],
                    'finishing': int(row['finishing']),
                    'dribbling': int(row['dribbling']),
                    'passing': int(row['passing']),
                    'pace': int(row['pace']),
                    'stamina': int(row['stamina']),
                    'strength': int(row['strength']),
                    'tackling': int(row['tackling']),
                    'heading': int(row['heading']),
                    'composure': int(row['composure']),
                    'vision': int(row['vision']),
                    'determination': int(row['determination']),
                })
            except (ValueError, KeyError):
                continue
    return players

def search(players, query, limit=10):
    q = query.lower()
    return [p for p in players if q in p['name'].lower()][:limit]

def get_club(players, club, limit=11):
    c = club.lower()
    team = [p for p in players if c in p['club'].lower()]
    team.sort(key=lambda x: x['ca'], reverse=True)
    return team[:limit]

def print_player(p, i=None):
    bar = "█" * (p['ca'] // 10) + "░" * (20 - p['ca'] // 10)
    prefix = f"  {i:>2}." if i else "   •"
    print(f"{prefix} {p['name']:<30} {p['position']:<10} Age:{p['age']:>2}  CA:{p['ca']:>3} [{bar}]  {p['club']}")

def simulate_match(home, away, home_name, away_name):
    home_str = sum(p['ca'] for p in home) / max(len(home), 1) * 1.05  # home advantage
    away_str = sum(p['ca'] for p in away) / max(len(away), 1)
    
    home_goals, away_goals = 0, 0
    events = []
    
    for minute in range(1, 91):
        if random.random() < 0.12:
            is_home = random.random() < (home_str / (home_str + away_str))
            team = home if is_home else away
            team_label = home_name if is_home else away_name
            player = random.choice(team)
            
            roll = random.random()
            if roll < 0.04:
                if is_home: home_goals += 1
                else: away_goals += 1
                events.append(f"  {minute:>2}' ⚽ GOAL! {player['name']} ({team_label}) [{home_goals}-{away_goals}]")
            elif roll < 0.18:
                events.append(f"  {minute:>2}' 🎯 Shot by {player['name']} ({team_label})")
            elif roll < 0.30:
                events.append(f"  {minute:>2}' 🔑 Key pass by {player['name']} ({team_label})")
            elif roll < 0.38:
                events.append(f"  {minute:>2}' 🦶 Tackle by {player['name']} ({team_label})")
            elif roll < 0.42:
                events.append(f"  {minute:>2}' 🟡 Yellow card: {player['name']} ({team_label})")
    
    return home_goals, away_goals, events, round(home_str/(home_str+away_str)*100)

# ─── MAIN ────────────────────────────────────────────────────────────────────

print("📂 Loading 34,644 players...")
players = load_players()
print(f"✅ Loaded {len(players):,} players\n")

# ═══ SEARCH DEMO ═══
print("=" * 80)
print("🔍 PLAYER SEARCH")
print("=" * 80)

for query in ["Messi", "Haaland", "Mbappe", "Bellingham", "Vinicius Jr"]:
    results = search(players, query, 3)
    print(f"\n  Search: '{query}'")
    for p in results:
        print_player(p)

print(f"\n{'─' * 80}")
print("  🏟️  Real Madrid squad:")
rm = get_club(players, "R. Madrid")
for i, p in enumerate(rm, 1):
    print_player(p, i)

print(f"\n  🏟️  Manchester City squad:")
mc = get_club(players, "Manchester City")
for i, p in enumerate(mc, 1):
    print_player(p, i)

# ═══ TOP PLAYERS ═══
print(f"\n{'─' * 80}")
print("  🏆 TOP 15 PLAYERS IN THE WORLD:")
top = sorted(players, key=lambda x: x['ca'], reverse=True)[:15]
for i, p in enumerate(top, 1):
    print_player(p, i)

# ═══ MATCH SIMULATION ═══
print("\n" + "=" * 80)
print("⚽ MATCH SIMULATION: Real Madrid vs Manchester City")
print("=" * 80)

home_team = get_club(players, "R. Madrid", 11)
away_team = get_club(players, "Manchester City", 11)

print(f"\n  📋 Real Madrid ({len(home_team)} players):")
for p in home_team:
    print(f"     {p['name']:<28} {p['position']:<10} CA: {p['ca']}")

print(f"\n  📋 Manchester City ({len(away_team)} players):")
for p in away_team:
    print(f"     {p['name']:<28} {p['position']:<10} CA: {p['ca']}")

print(f"\n  ⏱️  KICK OFF!\n")
hg, ag, events, poss = simulate_match(home_team, away_team, "Real Madrid", "Man City")

for e in events:
    print(e)

print(f"\n  {'═' * 60}")
print(f"  🏁 FULL TIME: Real Madrid {hg} - {ag} Manchester City")
print(f"  📊 Possession: Real Madrid {poss}% - {100-poss}% Man City")
print(f"  {'═' * 60}")
print("\n✅ Demo complete!")
