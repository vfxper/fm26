"""Analyze weight column issue"""
import csv
import io

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

# Check first 10 players
print("Analyzing first 10 players:")
print("Looking for weight in columns 80-100\n")

for i in range(1, min(11, len(rows))):
    row = rows[i]
    name = row[0]
    
    print(f"{i}. {name}:")
    print(f"   Column 90 (height): {row[90]}")
    print(f"   Column 93 (weight?): {row[93]}")
    
    # Find potential weight values (50-120)
    potential_weights = []
    for col_idx in range(80, min(100, len(row))):
        try:
            val = int(row[col_idx])
            if 50 <= val <= 120:
                potential_weights.append((col_idx, val))
        except:
            pass
    
    if potential_weights:
        print(f"   Potential weights: {potential_weights}")
    else:
        print(f"   No valid weight found in columns 80-100!")
    print()
