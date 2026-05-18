"""Direct test without module import"""
import csv
import io
import pandas as pd

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

header = rows[0]
data_rows = rows[1:]

print(f"Total rows: {len(data_rows)}")
print(f"Header columns: {len(header)}")

# Apply NEW mapping
processed_rows = []
for row in data_rows:
    if len(row) >= 98:
        new_row = (
            row[:43] +  # Columns 0-42: name through strength
            [row[85]] +  # Column 85: price
            [row[86]] +  # Column 86: wage
            [row[90]] +  # Column 90: height
            [row[93]] +  # Column 93: weight
            [row[83]] +  # Column 83: left_foot
            [row[84]] +  # Column 84: right_foot
            [row[97]]  # Column 97: uid
        )
        processed_rows.append(new_row)

print(f"Processed rows: {len(processed_rows)}")

# Create DataFrame
df = pd.DataFrame(processed_rows, columns=header)

# Check first player
print(f"\nFirst player:")
print(f"  Name: {df.iloc[0]['name']}")
print(f"  Height: {df.iloc[0]['height']}")
print(f"  Weight: {df.iloc[0]['weight']}")
print(f"  Wage: {df.iloc[0]['wage']}")

# Check Haaland
print(f"\nHaaland (row 4):")
print(f"  Name: {df.iloc[4]['name']}")
print(f"  Height: {df.iloc[4]['height']}")
print(f"  Weight: {df.iloc[4]['weight']}")

# Count valid weights
df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
valid_weights = ((df['weight'] >= 50) & (df['weight'] <= 120)).sum()
print(f"\nValid weights (50-120): {valid_weights} / {len(df)}")
