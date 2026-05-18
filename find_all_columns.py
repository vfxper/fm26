"""Find correct positions for price, wage, height, weight, left_foot, right_foot, uid"""
import csv
import io

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

first_row = rows[1]

print("Looking for specific patterns in first row (Kylian Mbappé):")
print("Expected values:")
print("  - price: should contain '£' or 'M' or large number")
print("  - wage: should be 4-5 digits (like 8000-9000)")
print("  - height: should be 175-185 cm")
print("  - weight: should be 70-80 kg")
print("  - left_foot: 1-20")
print("  - right_foot: 1-20")
print("  - uid: large number (8-10 digits)")

print(f"\nSearching in columns 43-115:")
for i in range(43, len(first_row)):
    val = first_row[i]
    
    # Check for price (contains £ or very large number)
    if '£' in val or 'M' in val:
        print(f"  Column {i}: {val[:50]} <- Likely PRICE")
        continue
    
    # Check for wage (4-5 digit number)
    try:
        num_val = int(val)
        if 1000 <= num_val <= 20000:
            print(f"  Column {i}: {val} <- Likely WAGE")
        elif 150 <= num_val <= 220:
            print(f"  Column {i}: {val} <- Likely HEIGHT")
        elif 50 <= num_val <= 120:
            print(f"  Column {i}: {val} <- Likely WEIGHT")
        elif num_val >= 1000000:
            print(f"  Column {i}: {val} <- Likely UID")
        elif 1 <= num_val <= 20 and i >= 80:
            # Only show 1-20 values after column 80 (to avoid attributes)
            print(f"  Column {i}: {val} <- Likely FOOT")
    except:
        if len(val) > 0 and len(val) < 50:
            print(f"  Column {i}: {val}")
