# Duplicate Detection and Handling Implementation

## Task 3.9: Implement duplicate detection and handling

**Status**: ✅ COMPLETE

## Overview

The duplicate detection and handling system is fully implemented in `fm26/app/services/player_loader.py`. It provides comprehensive duplicate detection at two levels:

1. **CSV-level duplicate detection** - Detects and removes duplicate UIDs within the CSV file itself
2. **Database-level duplicate detection** - Detects and skips players that already exist in the database

## Implementation Details

### 1. CSV Duplicate Detection

**Location**: `PlayerCSVParser.clean_data()` method (lines 527-532)

**Implementation**:
```python
# Remove duplicates based on UID
if 'uid' in df.columns:
    df = df.drop_duplicates(subset=['uid'], keep='first')
    duplicates_removed = original_count - len(df)
    validation_report['duplicates_removed'] = duplicates_removed
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate UIDs")
```

**Features**:
- Uses pandas `drop_duplicates()` with `keep='first'` strategy
- Preserves the first occurrence of each duplicate UID
- Logs the number of duplicates removed
- Reports duplicate count in validation report

### 2. Database Duplicate Detection

**Location**: `load_players_from_csv()` function (lines 825-862)

**Implementation**:
```python
# Detect database duplicates if session is provided and detection is enabled
db_duplicates_skipped = 0
db_duplicate_uids = []

if db_session is not None and detect_db_duplicates:
    logger.info("Checking for existing players in database...")
    csv_uids = set(df['uid'].tolist())
    
    try:
        # Query database for existing UIDs in batches to avoid memory issues
        existing_uids = set()
        batch_size = 1000
        uid_list = list(csv_uids)
        
        for i in range(0, len(uid_list), batch_size):
            batch_uids = uid_list[i:i + batch_size]
            existing_batch = db_session.query(Player.uid).filter(
                Player.uid.in_(batch_uids)
            ).all()
            existing_uids.update([uid[0] for uid in existing_batch])
        
        # Filter out players that already exist in database
        if existing_uids:
            db_duplicate_uids = list(existing_uids)
            db_duplicates_skipped = len(existing_uids)
            df = df[~df['uid'].isin(existing_uids)]
            
            logger.info(
                f"Found {db_duplicates_skipped} players already in database. "
                f"Skipping these to avoid duplicates. "
                f"Sample UIDs: {db_duplicate_uids[:5]}"
            )
    except Exception as e:
        logger.warning(
            f"Failed to check database for duplicates: {str(e)}. "
            f"Proceeding without database duplicate detection."
        )
```

**Features**:
- Batch querying (1000 UIDs per batch) for performance with large datasets
- Configurable via `detect_db_duplicates` parameter (default: True)
- Graceful error handling - continues without DB duplicate detection if query fails
- Filters out existing players from the DataFrame before creating Player objects
- Logs detailed information about duplicates found
- Reports sample UIDs for debugging

### 3. Duplicate Reporting

**Location**: `load_players_from_csv()` function (lines 864-870)

**Validation Report Fields**:
```python
validation_report['csv_duplicates_removed'] = validation_report.get('duplicates_removed', 0)
validation_report['db_duplicates_skipped'] = db_duplicates_skipped
validation_report['db_duplicate_uids'] = db_duplicate_uids[:100]  # Keep first 100 for reference
validation_report['total_duplicates_handled'] = (
    validation_report['csv_duplicates_removed'] + db_duplicates_skipped
)
```

**Report Fields**:
- `csv_duplicates_removed`: Number of duplicate UIDs removed from CSV
- `db_duplicates_skipped`: Number of players skipped because they exist in database
- `db_duplicate_uids`: List of UIDs that were skipped (first 100 for reference)
- `total_duplicates_handled`: Total count of all duplicates handled

## Usage Examples

### Example 1: Load with database duplicate detection (default)

```python
from app.core.database import get_db
from app.services.player_loader import load_players_from_csv

db = next(get_db())
players, report = load_players_from_csv('fm26/2600球员属性.csv', db)

print(f"Loaded {len(players)} players")
print(f"CSV duplicates removed: {report['csv_duplicates_removed']}")
print(f"Database duplicates skipped: {report['db_duplicates_skipped']}")
print(f"Total duplicates handled: {report['total_duplicates_handled']}")
```

### Example 2: Load without database duplicate detection

```python
# Useful for initial database seeding or when you know the database is empty
players, report = load_players_from_csv(
    'fm26/2600球员属性.csv', 
    db_session=db,
    detect_db_duplicates=False
)
```

### Example 3: Load without database session

```python
# Only CSV duplicate detection will be performed
players, report = load_players_from_csv('fm26/2600球员属性.csv', db_session=None)
```

## Performance Characteristics

### CSV Duplicate Detection
- **Time Complexity**: O(n) where n is the number of rows
- **Space Complexity**: O(n) for the DataFrame
- **Performance**: Very fast, uses pandas optimized operations

### Database Duplicate Detection
- **Time Complexity**: O(n/b) where n is number of UIDs, b is batch size (1000)
- **Space Complexity**: O(n) for storing existing UIDs
- **Performance**: Efficient batch queries minimize database round trips
- **Scalability**: Handles large datasets (2600+ players) efficiently

## Error Handling

### Database Query Failures
- Catches all exceptions during database duplicate detection
- Logs warning message with error details
- Continues processing without database duplicate detection
- Does not fail the entire load operation

### CSV Parsing Errors
- Handled by `PlayerCSVParser.load()` method
- Raises appropriate exceptions (CSVNotFoundError, CSVParseError, etc.)
- Provides detailed error messages for debugging

## Logging

The implementation provides comprehensive logging:

1. **Info Level**:
   - "Checking for existing players in database..."
   - "Removed {n} duplicate UIDs"
   - "Found {n} players already in database. Skipping these to avoid duplicates."
   - "Successfully loaded {n} Player objects from CSV..."

2. **Warning Level**:
   - "Failed to check database for duplicates: {error}. Proceeding without database duplicate detection."
   - "Filtering out {n} invalid rows"

## Testing

Comprehensive test suite exists in `fm26/tests/services/test_duplicate_detection.py`:

### Test Coverage:
1. **CSV Duplicate Detection Tests** (TestCSVDuplicateDetection)
   - Detect duplicate UIDs in CSV
   - Remove duplicate UIDs keeping first occurrence
   - Handle multiple sets of duplicates
   - Handle CSV with no duplicates
   - Log warnings for duplicates
   - Include duplicate info in validation report

2. **Database Duplicate Detection Tests** (TestDatabaseDuplicateDetection)
   - Load without database session
   - Load with database session (no duplicates)
   - Load with database session (with duplicates)
   - Load when all players are duplicates
   - Disable database duplicate detection
   - Handle database errors gracefully
   - Use batch queries for large datasets

3. **Duplicate Handling Strategy Tests** (TestDuplicateHandlingStrategies)
   - Handle both CSV and database duplicates
   - Preserve first occurrence
   - Comprehensive validation report

4. **Performance Tests** (TestDuplicateDetectionPerformance)
   - Efficient for large CSV files (1000+ players)
   - Complete in reasonable time (< 5 seconds)

## Integration with Player Model

The duplicate detection uses the `uid` field from the Player model as the unique identifier:

```python
# From app/models/player.py
uid: Mapped[str] = mapped_column(
    String(255),
    unique=True,
    nullable=False,
    index=True,
    comment="Unique identifier from CSV"
)
```

The database enforces uniqueness at the schema level, providing an additional layer of protection against duplicates.

## Requirements Satisfied

From **Task 3.9: Implement duplicate detection and handling**:

✅ **Duplicate detection logic implemented** - Both CSV and database level
✅ **Use uid field (column 97) as primary unique identifier** - Implemented
✅ **Handle duplicates by skipping existing records** - Implemented (keep='first' for CSV, filter for DB)
✅ **Log duplicate detections for monitoring** - Comprehensive logging implemented
✅ **Ensure data integrity during batch inserts** - Duplicates removed before Player object creation

## Conclusion

The duplicate detection and handling system is fully implemented, tested, and production-ready. It provides:

- **Robust duplicate detection** at both CSV and database levels
- **Efficient performance** with batch querying for large datasets
- **Comprehensive reporting** with detailed validation reports
- **Graceful error handling** that doesn't fail the entire operation
- **Extensive logging** for monitoring and debugging
- **Full test coverage** with 15+ test cases

**Task 3.9 Status: ✅ COMPLETE**
