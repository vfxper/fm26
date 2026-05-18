import csv
import io

# Read file
with open('2600球员属性.csv', 'r', encoding='utf-8', newline='') as f:
    content = f.read()

# Remove BOM
if content.startswith('\ufeff'):
    content = content[1:]

# Parse CSV
reader = csv.reader(io.StringIO(content))
rows = list(reader)

print('Comparing Mbappé (row 1) and Haaland (row 5):')
print('\nColumns 85-100:')
print('Col | Mbappé          | Haaland')
print('----+-----------------+------------------')
for i in range(85, 101):
    mbappe_val = rows[1][i] if len(rows[1]) > i else ''
    haaland_val = rows[5][i] if len(rows[5]) > i else ''
    print(f'{i:3d} | {mbappe_val:15s} | {haaland_val}')

# Expected values:
# Mbappé: height ~185, weight ~80
# Haaland: height ~195, weight ~88
