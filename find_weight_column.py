"""Find the correct weight column"""
import csv
import io

csv_path = '2600球员属性.csv'

with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

if content.startswith('\ufeff'):
    content = content[1:]

csv_reader = csv.reader(io.StringIO(content))
rows = list(csv_reader)

# Look at Lamine Yamal's row (we know his data from earlier)
# He should have height=180, weight around 65-70
for i, row in enumerate(rows[1:241], start=1):
    if 'Lamine Yamal' in row[0]:
        print(f"Found Lamine Yamal at row {i}")
        print(f"Row has {len(row)} columns")
        
        # We know from earlier search that:
        # - Column 90 should be height (180)
        # - We need to find weight
        
        print(f"\nColumn 90 (height): {row[90]}")
        print(f"Column 93 (current weight mapping): {row[93]}")
        
        # Search for weight in nearby columns
        print(f"\nSearching columns 80-100 for weight (~65-75):")
        for col_idx in range(80, min(100, len(row))):
            try:
                val = int(row[col_idx])
                if 60 <= val <= 80:
                    print(f"  Column {col_idx}: {val}")
            except:
                pass
        
        # Show all columns 85-100
        print(f"\nAll columns 85-100:")
        for col_idx in range(85, min(100, len(row))):
            val = row[col_idx]
            if len(val) > 50:
                val = val[:50] + "..."
            print(f"  Column {col_idx}: {val}")
        
        break
