"""Check how many valid players we have after cleaning"""
import sys
sys.path.insert(0, '.')

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
    for error_type, count in report['error_summary'].items():
        print(f'  {error_type}: {count}')

# Show some invalid players
if report['validation_errors']:
    print(f'\nFirst 5 invalid players:')
    for i, error_entry in enumerate(report['validation_errors'][:5]):
        print(f"\n{i+1}. {error_entry['player_name']} (row {error_entry['row_index']}):")
        for error in error_entry['errors'][:3]:  # Show first 3 errors
            print(f"   - {error}")
