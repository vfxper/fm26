import sys
sys.path.insert(0, '.')

from app.services.player_loader import PlayerCSVParser

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()

print('UID column sample (first 10):')
for i, uid in enumerate(df['uid'].head(10)):
    print(f'  [{i}] {uid[:100] if len(str(uid)) > 100 else uid}')

print(f'\nUnique UIDs: {df["uid"].nunique()}')
print(f'Total rows: {len(df)}')

# Check for most common UIDs
print('\nMost common UIDs:')
uid_counts = df['uid'].value_counts().head(10)
for uid, count in uid_counts.items():
    print(f'  {uid[:50]}: {count} occurrences')
