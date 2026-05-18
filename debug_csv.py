import csv
import io
import sys

# Set UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read file
with open('2600球员属性.csv', 'r', encoding='utf-8', newline='') as f:
    content = f.read()

# Remove BOM
if content.startswith('\ufeff'):
    content = content[1:]

# Parse CSV
reader = csv.reader(io.StringIO(content))
rows = list(reader)

# Print header
print('Header columns (indices 40-50):')
for i in range(40, min(50, len(rows[0]))):
    print(f'  [{i}] {rows[0][i]}')

# Print first data row
print('\nFirst data row (indices 40-50):')
for i in range(40, min(50, len(rows[1]))):
    print(f'  [{i}] {rows[1][i]}')

# Check where height and weight actually are
print('\nLooking for height/weight in first data row...')
print('Expected: height ~185, weight ~80')
for i in range(len(rows[1])):
    val = rows[1][i]
    if val.isdigit():
        num = int(val)
        if 180 <= num <= 200:
            print(f'  Column {i}: {val} (could be height)')
        elif 70 <= num <= 90:
            print(f'  Column {i}: {val} (could be weight)')
