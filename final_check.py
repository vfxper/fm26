"""Final validation check after fixing column mapping"""
import sys
sys.path.insert(0, '.')

import importlib
if 'app.services.player_loader' in sys.modules:
    importlib.reload(sys.modules['app.services.player_loader'])

from app.services.player_loader import PlayerCSVParser

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()
clean_df, report = parser.clean_data(df)

print(f'Original rows: {report["original_count"]}')
print(f'Valid rows: {report["valid_count"]}')
print(f'Invalid rows: {report["invalid_count"]}')
print(f'Duplicates removed: {report["duplicates_removed"]}')

if report['error_summary']:
    print(f'\nError summary:')
    for error_type, count in sorted(report['error_summary'].items(), key=lambda x: -x[1])[:10]:
        print(f'  {error_type}: {count}')

print(f'\nSuccess rate: {report["valid_count"] / report["original_count"] * 100:.1f}%')
