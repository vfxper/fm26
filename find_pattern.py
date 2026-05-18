"""Find pattern in weight data"""
import csv
import io

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

# Find players with valid weight in column 93
valid_in_93 = []
invalid_in_93 = []

for i in range(1, min(100, len(rows))):
    row = rows[i]
    name = row[0]
    
    try:
        weight_93 = int(row[93])
        if 50 <= weight_93 <= 120:
            valid_in_93.append((i, name, weight_93))
        else:
            invalid_in_93.append((i, name, weight_93))
    except:
        invalid_in_93.append((i, name, row[93]))

print(f"Valid weights in column 93: {len(valid_in_93)}")
print(f"Invalid weights in column 93: {len(invalid_in_93)}")

print(f"\nFirst 10 valid:")
for i, name, weight in valid_in_93[:10]:
    print(f"  Row {i}: {name} - {weight} kg")

print(f"\nFirst 10 invalid:")
for i, name, weight in invalid_in_93[:10]:
    print(f"  Row {i}: {name} - {weight}")

# Check if there's a pattern - maybe column 93 has age instead of weight?
print(f"\nChecking if column 93 might be age:")
for i in range(1, min(20, len(rows))):
    row = rows[i]
    name = row[0]
    age_col2 = row[2]  # Age should be in column 2
    val_col93 = row[93]
    
    print(f"  {name}: age={age_col2}, col93={val_col93}")
