"""Test traits extraction from CSV"""
import sys
sys.path.insert(0, '.')

# Force module reload
for module_name in list(sys.modules.keys()):
    if 'app.services.player_loader' in module_name:
        del sys.modules[module_name]

from app.services.player_loader import PlayerCSVParser

print("Testing traits extraction...\n")

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()

print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}\n")

# Check if traits column exists
if 'traits' in df.columns:
    print("✓ Traits column found!")
    
    # Show first 10 players with traits
    players_with_traits = df[df['traits'].notna() & (df['traits'] != '')]
    print(f"\nPlayers with traits: {len(players_with_traits)} / {len(df)}")
    
    print(f"\nFirst 10 players with traits:")
    for i, (idx, row) in enumerate(players_with_traits.head(10).iterrows()):
        print(f"\n{i+1}. {row['name']}")
        print(f"   Traits: {row['traits'][:100]}...")  # Show first 100 chars
else:
    print("✗ Traits column NOT found!")

# Test with Lamine Yamal
print(f"\n{'='*60}")
print("Lamine Yamal's traits:")
print('='*60)
yamal = df[df['name'].str.contains('Lamine Yamal', na=False)]
if not yamal.empty:
    traits = yamal.iloc[0]['traits']
    print(f"Traits: {traits}")
else:
    print("Lamine Yamal not found!")
