"""Test if the column mapping fix worked"""
import sys
sys.path.insert(0, '.')

# Force reload
import importlib
if 'app.services.player_loader' in sys.modules:
    importlib.reload(sys.modules['app.services.player_loader'])

from app.services.player_loader import PlayerCSVParser

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()

print(f'Loaded: {len(df)} rows')
print(f'\nFirst player (Kylian Mbappé):')
print(f'  Name: {df.iloc[0]["name"]}')
print(f'  Height: {df.iloc[0]["height"]}')
print(f'  Weight: {df.iloc[0]["weight"]}')
print(f'  Wage: {df.iloc[0]["wage"]}')
print(f'  Price: {df.iloc[0]["price"]}')
print(f'  Left foot: {df.iloc[0]["left_foot"]}')
print(f'  Right foot: {df.iloc[0]["right_foot"]}')

print(f'\nHaaland (row 4):')
print(f'  Name: {df.iloc[4]["name"]}')
print(f'  Height: {df.iloc[4]["height"]}')
print(f'  Weight: {df.iloc[4]["weight"]}')

# Validate
is_valid, errors = parser.validate_row(df.iloc[0])
print(f'\nFirst player validation: {is_valid}')
if errors:
    for error in errors[:5]:
        print(f'  - {error}')
