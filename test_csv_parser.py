"""
Test script for CSV parser - Task 3.1
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.player_loader import PlayerCSVParser

def test_csv_parser():
    """Test the CSV parser implementation"""
    print("=" * 60)
    print("Testing CSV Parser - Task 3.1")
    print("=" * 60)
    
    csv_path = "2600球员属性.csv"
    
    try:
        # Initialize parser
        print(f"\n1. Initializing parser for: {csv_path}")
        parser = PlayerCSVParser(csv_path)
        print("   ✓ Parser initialized successfully")
        
        # Load CSV
        print("\n2. Loading CSV file...")
        df = parser.load()
        print(f"   ✓ CSV loaded successfully")
        print(f"   - Rows: {len(df)}")
        print(f"   - Columns: {len(df.columns)}")
        
        # Display first few rows
        print("\n3. Sample data (first 3 players):")
        print(df[['name', 'position', 'age', 'ca', 'pa', 'club']].head(3).to_string())
        
        # Validate data
        print("\n4. Validating data...")
        validation_report = parser.validate_player_data(df)
        print(f"   - Total rows: {validation_report['total_rows']}")
        print(f"   - Valid rows: {validation_report['valid_rows']}")
        print(f"   - Issues found: {len(validation_report['issues'])}")
        
        if validation_report['issues']:
            print("\n   Issues:")
            for issue in validation_report['issues'][:5]:  # Show first 5 issues
                print(f"   - {issue}")
        
        # Clean data
        print("\n5. Cleaning data...")
        clean_df, clean_report = parser.clean_data(df)
        print(f"   ✓ Data cleaned successfully")
        print(f"   - Original count: {clean_report['original_count']}")
        print(f"   - Valid count: {clean_report['valid_count']}")
        print(f"   - Invalid count: {clean_report['invalid_count']}")
        print(f"   - Duplicates removed: {clean_report['duplicates_removed']}")
        
        # Show column info
        print("\n6. Column information:")
        col_info = parser.get_column_info()
        print(f"   - Total columns: {col_info['column_count']}")
        print(f"   - Columns: {', '.join(col_info['columns'][:10])}...")
        
        print("\n" + "=" * 60)
        print("✓ CSV Parser Test PASSED")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ CSV Parser Test FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_csv_parser()
    sys.exit(0 if success else 1)
