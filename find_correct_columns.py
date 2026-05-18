"""Find correct column indices for height, weight, and uid"""
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
print(f"Header has {len(header)} columns")
print(f"Header columns: {header}")

# Look at first data row (Kylian Mbappé or similar)
if len(rows) > 1:
    first_row = rows[1]
    print(f"\nFirst data row has {len(first_row)} columns")
    try:
        print(f"First row name: {first_row[0]}")
    except:
        print(f"First row name: (encoding error)")
    
    # Expected values for first player (based on previous data):
    # height should be around 180-185 cm
    # weight should be around 70-80 kg
    # uid should be a long number
    
    print(f"\nSearching for height (should be ~180-185):")
    for i, val in enumerate(first_row):
        try:
            num_val = int(val)
            if 175 <= num_val <= 190:
                print(f"  Column {i}: {val}")
        except:
            pass
    
    print(f"\nSearching for weight (should be ~70-80):")
    for i, val in enumerate(first_row):
        try:
            num_val = int(val)
            if 65 <= num_val <= 85:
                print(f"  Column {i}: {val}")
        except:
            pass
    
    print(f"\nSearching for UID (should be long number like 29179241):")
    for i, val in enumerate(first_row):
        try:
            num_val = int(val)
            if num_val > 1000000:
                print(f"  Column {i}: {val}")
        except:
            pass
    
    # Show columns around position 45-50 (where we expect height/weight)
    print(f"\nColumns 40-55:")
    for i in range(40, min(56, len(first_row))):
        print(f"  Column {i}: {first_row[i][:50] if len(first_row[i]) > 50 else first_row[i]}")
    
    # Show columns around position 90-100
    print(f"\nColumns 85-105:")
    for i in range(85, min(106, len(first_row))):
        print(f"  Column {i}: {first_row[i][:50] if len(first_row[i]) > 50 else first_row[i]}")
