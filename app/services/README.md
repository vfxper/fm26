# Services Module

This module contains business logic services for the Telegram Football Manager application.

## Player Loader Service

The Player Loader Service (`player_loader.py`) provides functionality to load player data from the CSV file `2600球员属性.csv` into the PostgreSQL database.

### Features

- **CSV Parsing**: Uses pandas to efficiently parse large CSV files with 2600+ players
- **Data Validation**: Validates all player attributes (age, CA, PA, technical/mental/physical attributes)
- **Data Cleaning**: Removes duplicates, handles missing values, converts data types
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Database Integration**: Creates Player model objects ready for bulk database insertion
- **Encoding Support**: Handles multiple character encodings (UTF-8, GBK, GB2312, GB18030) for Chinese characters

### Usage

#### Basic Usage

```python
from app.services.player_loader import load_players_from_csv
from app.core.database import SessionLocal

# Load players from CSV
db = SessionLocal()
players = load_players_from_csv('2600球员属性.csv', db_session=db)

print(f"Loaded {len(players)} players")

# Bulk insert into database
db.bulk_save_objects(players)
db.commit()
db.close()
```

#### Using the CSV Parser Directly

```python
from app.services.player_loader import PlayerCSVParser

# Initialize parser
parser = PlayerCSVParser('2600球员属性.csv')

# Load and parse CSV
df = parser.load()

# Clean data
clean_df = parser.clean_data(df)

# Validate data
report = parser.validate_player_data(clean_df)
print(f"Valid rows: {report['valid_rows']}/{report['total_rows']}")
```

#### Database Seeding Script

Use the provided seeding script to load all players into the database:

```bash
# Basic usage
python scripts/seed_players.py

# Specify custom CSV path
python scripts/seed_players.py --csv-path path/to/players.csv

# Dry run (parse CSV but don't insert)
python scripts/seed_players.py --dry-run

# Force re-seed (delete existing players)
python scripts/seed_players.py --force

# Custom batch size
python scripts/seed_players.py --batch-size 1000

# Verbose logging
python scripts/seed_players.py --verbose
```

### CSV File Format

The CSV file must contain the following columns:

**Basic Information:**
- `uid` - Unique identifier (required, unique)
- `name` - Player name (required)
- `position` - Player position(s) (e.g., "AM/ST RL")
- `age` - Player age (15-45)
- `ca` - Current Ability (1-200)
- `pa` - Potential Ability (1-200)
- `nationality` - Player nationality
- `club` - Current club name

**Technical Attributes (1-20 each):**
- `corners`, `crossing`, `dribbling`, `finishing`, `first_touch`, `free_kicks`
- `heading`, `long_shots`, `long_throws`, `marking`, `passing`, `penalty`
- `tackling`, `technique`

**Mental Attributes (1-20 each):**
- `aggression`, `anticipation`, `bravery`, `composure`, `concentration`
- `decisions`, `determination`, `flair`, `leadership`, `off_the_ball`
- `positioning`, `teamwork`, `vision`, `work_rate`

**Physical Attributes (1-20 each):**
- `acceleration`, `agility`, `balance`, `jumping`, `stamina`, `pace`
- `endurance`, `strength`

**Financial & Physical Stats:**
- `price` - Market value (string with currency symbols, e.g., "£149,602,800")
- `wage` - Weekly wage (integer)
- `height` - Height in cm (150-220)
- `weight` - Weight in kg (50-120)
- `left_foot` - Left foot ability (1-20)
- `right_foot` - Right foot ability (1-20)

### Data Validation

The parser performs the following validations:

1. **Required Fields**: All required fields must be present and non-empty
2. **Age Range**: Age must be between 15 and 45
3. **CA/PA Range**: Current Ability and Potential Ability must be between 1 and 200
4. **Attribute Range**: All technical, mental, and physical attributes must be between 1 and 20
5. **Height Range**: Height must be between 150 and 220 cm
6. **Weight Range**: Weight must be between 50 and 120 kg
7. **Unique UIDs**: Each player must have a unique UID

### Error Handling

The module defines custom exceptions for different error scenarios:

- `PlayerLoaderError` - Base exception for all player loader errors
- `CSVNotFoundError` - Raised when CSV file is not found
- `CSVEncodingError` - Raised when CSV encoding cannot be handled
- `CSVParseError` - Raised when CSV parsing fails
- `CSVValidationError` - Raised when CSV data validation fails

### Performance

- **CSV Parsing**: Uses pandas for efficient parsing of large CSV files
- **Batch Insertion**: Supports batch insertion with configurable batch size (default: 500)
- **Memory Efficient**: Processes data in chunks to minimize memory usage
- **Progress Tracking**: Provides progress updates during large imports

### Testing

Run the test suite:

```bash
# Run all player loader tests
pytest tests/services/test_player_loader.py -v

# Run specific test class
pytest tests/services/test_player_loader.py::TestPlayerCSVParser -v

# Run with coverage
pytest tests/services/test_player_loader.py --cov=app.services.player_loader
```

### API Reference

#### `load_players_from_csv(csv_path: str, db_session) -> List[Player]`

Load players from CSV file and return Player model objects ready for database insertion.

**Parameters:**
- `csv_path` (str): Path to the CSV file
- `db_session`: SQLAlchemy database session (for API compatibility, not used during loading)

**Returns:**
- `List[Player]`: List of Player model objects

**Raises:**
- `PlayerLoaderError`: If loading, validation, or mapping fails

#### `PlayerCSVParser`

Main CSV parser class.

**Methods:**
- `__init__(csv_path: str, encoding: str = 'utf-8')` - Initialize parser
- `load() -> DataFrame` - Load and parse CSV file
- `clean_data(df: DataFrame) -> DataFrame` - Clean and normalize data
- `validate_row(row: Series) -> bool` - Validate a single player row
- `validate_player_data(df: DataFrame) -> Dict` - Perform detailed validation
- `parse_csv(csv_path: str) -> DataFrame` - Convenience method combining load and clean
- `get_column_info() -> Dict` - Get CSV column information

### Implementation Notes

1. **Encoding Handling**: The parser automatically tries multiple encodings (UTF-8, UTF-8-sig, GBK, GB2312, GB18030) to handle Chinese characters in the CSV file.

2. **Data Cleaning**: The `clean_data` method:
   - Removes duplicate UIDs (keeps first occurrence)
   - Strips whitespace from string fields
   - Converts numeric fields to appropriate types
   - Filters out invalid rows
   - Selects only required columns

3. **Database Insertion**: The `load_players_from_csv` function returns Player model objects that can be inserted using SQLAlchemy's `bulk_save_objects` for efficient batch insertion.

4. **Price Field**: The price field is kept as a string to preserve currency symbols (e.g., "£149,602,800") as specified in the Player model.

### Future Enhancements

- [ ] Add support for incremental updates (update existing players)
- [ ] Add support for CSV export
- [ ] Add support for multiple CSV formats
- [ ] Add data transformation pipelines
- [ ] Add support for player traits parsing
- [ ] Add support for player history tracking
