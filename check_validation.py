import sys
sys.path.insert(0, '.')

from app.services.player_loader import PlayerCSVParser

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()

# Find a player that fails validation
print('Checking validation for players...')
for i in range(min(100, len(df))):
    is_valid, errors = parser.validate_row(df.iloc[i], log_details=False)
    if not is_valid:
        print(f'\nFound invalid player at index {i}:')
        print(f'Player: {df.iloc[i]["name"]}')
        print(f'\nPlayer data:')
        for col in ['name', 'position', 'age', 'ca', 'pa', 'club', 'uid', 'wage', 'height', 'weight', 'left_foot', 'right_foot']:
            print(f'  {col}: {df.iloc[i][col]}')
        print(f'\nErrors ({len(errors)}):')
        for error in errors[:5]:  # Show first 5 errors
            print(f'  - {error}')
        break
else:
    print('All first 100 players are valid!')
