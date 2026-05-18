"""Test final fix with default values for invalid weight"""
import sys
sys.path.insert(0, '.')

# Force module reload
import importlib
for module_name in list(sys.modules.keys()):
    if 'app.services.player_loader' in module_name:
        del sys.modules[module_name]

from app.services.player_loader import PlayerCSVParser

print("Testing CSV parser with fixed column mapping and default values...\n")

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()
print(f"Loaded {len(df)} rows from CSV")

clean_df, report = parser.clean_data(df)

print(f"\n{'='*60}")
print("VALIDATION REPORT")
print('='*60)
print(f"Original rows: {report['original_count']}")
print(f"Valid rows: {report['valid_count']}")
print(f"Invalid rows: {report['invalid_count']}")
print(f"Duplicates removed: {report['duplicates_removed']}")
print(f"Weight defaults applied: {report['default_values_applied']['weight']}")
print(f"Height defaults applied: {report['default_values_applied']['height']}")
print(f"\nSuccess rate: {report['valid_count'] / report['original_count'] * 100:.1f}%")

if report['error_summary']:
    print(f"\nRemaining errors:")
    for error_type, count in sorted(report['error_summary'].items(), key=lambda x: -x[1])[:5]:
        print(f"  {error_type}: {count}")

print(f"\n{'='*60}")
print("SAMPLE PLAYERS")
print('='*60)

# Show first 5 players
for i in range(min(5, len(clean_df))):
    player = clean_df.iloc[i]
    print(f"\n{i+1}. {player['name']}")
    print(f"   Position: {player['position']}, Age: {player['age']}")
    print(f"   Club: {player['club']}")
    print(f"   CA: {player['ca']}, PA: {player['pa']}")
    print(f"   Height: {player['height']} cm, Weight: {player['weight']} kg")
    print(f"   Wage: {player['wage']}, Price: {player['price']}")

print(f"\n{'='*60}")
print(f"✓ Ready to load {len(clean_df)} players into database!")
print('='*60)
