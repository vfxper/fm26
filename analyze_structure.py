"""Analyze CSV structure to understand column mapping"""
import csv
import io

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

header = rows[0]
first_row = rows[1]

print("Expected header (50 columns):")
for i, col in enumerate(header):
    print(f"  {i}: {col}")

print(f"\n\nFirst data row (116 columns) - showing first 50:")
for i in range(min(50, len(first_row))):
    val = first_row[i]
    if len(val) > 30:
        val = val[:30] + "..."
    print(f"  {i}: {val}")

# Try to match header to data
print(f"\n\nMatching header to data (first 45 columns):")
for i in range(min(45, len(header))):
    header_name = header[i]
    data_val = first_row[i] if i < len(first_row) else "N/A"
    if len(data_val) > 30:
        data_val = data_val[:30] + "..."
    print(f"  {i}: {header_name:20s} = {data_val}")
