"""Diagnose CSV file to find why only 34k rows are loaded instead of 65k"""
import csv
import io

csv_path = '2600球员属性.csv'

# Try different encodings
for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']:
    try:
        print(f"\n{'='*60}")
        print(f"Testing encoding: {encoding}")
        print('='*60)
        
        with open(csv_path, 'r', encoding=encoding, newline='') as f:
            content = f.read()
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            print("BOM detected and removed")
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        print(f"Total rows read: {len(rows)}")
        print(f"Header columns: {len(rows[0]) if rows else 0}")
        
        # Analyze column counts
        if len(rows) > 1:
            col_counts = {}
            for i, row in enumerate(rows[1:], start=1):
                col_count = len(row)
                if col_count not in col_counts:
                    col_counts[col_count] = []
                col_counts[col_count].append(i)
            
            print(f"\nColumn count distribution:")
            for col_count in sorted(col_counts.keys()):
                row_indices = col_counts[col_count]
                print(f"  {col_count} columns: {len(row_indices)} rows")
                if len(row_indices) <= 5:
                    print(f"    Row indices: {row_indices}")
                else:
                    print(f"    First 5 rows: {row_indices[:5]}")
                    print(f"    Last 5 rows: {row_indices[-5:]}")
            
            # Check rows with < 98 columns
            rows_below_98 = sum(1 for row in rows[1:] if len(row) < 98)
            print(f"\nRows with < 98 columns: {rows_below_98}")
            print(f"Rows with >= 98 columns: {len(rows) - 1 - rows_below_98}")
            
            # Show first few rows with < 98 columns
            if rows_below_98 > 0:
                print(f"\nFirst 5 rows with < 98 columns:")
                count = 0
                for i, row in enumerate(rows[1:], start=1):
                    if len(row) < 98:
                        print(f"  Row {i}: {len(row)} columns - {row[0] if row else 'empty'}")
                        count += 1
                        if count >= 5:
                            break
        
        print(f"\nSuccess with {encoding}!")
        break
        
    except UnicodeDecodeError as e:
        print(f"Failed with {encoding}: {e}")
        continue
    except Exception as e:
        print(f"Error with {encoding}: {type(e).__name__}: {e}")
        continue
