# Player Search Service Documentation

## Overview

The Player Search Service provides comprehensive search and filtering functionality for the Player_DB (2600+ players from CSV). It implements Task 9.2: Create search filters (position, age, CA, PA, nationality, club).

## Features

### Search Filters

The service supports the following filter criteria:

1. **Full-Text Search** (`search_text`)
   - Searches across player name, position, club, and nationality
   - Uses PostgreSQL GIN index for efficient full-text search
   - Supports relevance-based sorting

2. **Position Filter** (`position`)
   - Partial match support (e.g., "ST" matches "AM/ST RL", "ST C", etc.)
   - Case-insensitive matching

3. **Age Range** (`min_age`, `max_age`)
   - Filter players by age range
   - Both bounds are inclusive
   - Valid range: 15-50 years

4. **Current Ability (CA) Range** (`min_ca`, `max_ca`)
   - Filter by Current Ability score
   - Both bounds are inclusive
   - Valid range: 1-200

5. **Potential Ability (PA) Range** (`min_pa`, `max_pa`)
   - Filter by Potential Ability score
   - Both bounds are inclusive
   - Valid range: -200 to 200 (negative values indicate random potential ranges in FM)

6. **Nationality Filter** (`nationality`)
   - Exact match on player nationality
   - Case-sensitive

7. **Club Filter** (`club`)
   - Exact match on player club
   - Case-sensitive

### Sorting Options

Results can be sorted by:
- `relevance` - Relevance score (requires `search_text`, default)
- `ca` - Current Ability (descending)
- `pa` - Potential Ability (descending)
- `age` - Age (ascending)
- `name` - Name (alphabetical, ascending)

### Pagination

- `limit` - Maximum number of results per page (1-200, default: 50)
- `offset` - Number of results to skip (default: 0)
- Returns `has_more` flag indicating if more results exist

## Usage Examples

### Basic Search

```python
from app.services.player_search import PlayerSearchService, PlayerSearchFilters

# Create service with database session
service = PlayerSearchService(db_session)

# Search by name
filters = PlayerSearchFilters(search_text="Messi")
results = await service.search_players(filters)

print(f"Found {results['total']} players")
for player in results['players']:
    print(f"{player.name} - CA: {player.ca}")
```

### Filter by Position

```python
# Find all strikers
filters = PlayerSearchFilters(position="ST")
results = await service.search_players(filters)
```

### Filter by Age Range

```python
# Find young players (18-25 years old)
filters = PlayerSearchFilters(min_age=18, max_age=25)
results = await service.search_players(filters)
```

### Filter by Current Ability

```python
# Find high CA players (CA >= 180)
filters = PlayerSearchFilters(min_ca=180, order_by="ca")
results = await service.search_players(filters)
```

### Filter by Nationality

```python
# Find all Portuguese players
filters = PlayerSearchFilters(nationality="Portugal")
results = await service.search_players(filters)
```

### Filter by Club

```python
# Find all Barcelona players
filters = PlayerSearchFilters(club="Barcelona")
results = await service.search_players(filters)
```

### Combined Filters

```python
# Find high CA strikers aged 30+
filters = PlayerSearchFilters(
    position="ST",
    min_ca=180,
    min_age=30,
    order_by="ca"
)
results = await service.search_players(filters)
```

### Pagination

```python
# Get first page (50 results)
filters = PlayerSearchFilters(limit=50, offset=0, order_by="name")
page1 = await service.search_players(filters)

# Get second page
filters = PlayerSearchFilters(limit=50, offset=50, order_by="name")
page2 = await service.search_players(filters)

# Check if more results exist
if page1['has_more']:
    print("More results available")
```

### Simplified API

For simpler use cases, use the `search_players_simple` method:

```python
results = await service.search_players_simple(
    search_text="Ronaldo",
    position="ST",
    min_ca=180,
    nationality="Portugal",
    limit=20
)
```

### Get Filter Options

Get available filter values for building UI dropdowns:

```python
options = await service.get_filter_options()

print(f"Available positions: {options['positions']}")
print(f"Available nationalities: {options['nationalities']}")
print(f"Available clubs: {options['clubs']}")
print(f"Age range: {options['age_range']['min']} - {options['age_range']['max']}")
print(f"CA range: {options['ca_range']['min']} - {options['ca_range']['max']}")
print(f"PA range: {options['pa_range']['min']} - {options['pa_range']['max']}")
```

## API Response Format

The `search_players` method returns a dictionary with:

```python
{
    "players": [Player, Player, ...],  # List of Player objects
    "total": 150,                       # Total matching players (before pagination)
    "limit": 50,                        # Applied limit
    "offset": 0,                        # Applied offset
    "has_more": True                    # More results available?
}
```

## Filter Validation

All filters are validated before execution. Invalid filters raise `ValueError`:

- Age: min_age >= 15, max_age <= 50, min_age <= max_age
- CA: 1 <= min_ca <= max_ca <= 200
- PA: -200 <= min_pa <= max_pa <= 200
- Limit: 1 <= limit <= 200
- Offset: offset >= 0
- Order by: Must be one of: relevance, ca, pa, age, name
- Relevance sorting requires search_text

## Performance Considerations

### Indexes

The Player model includes the following indexes for efficient filtering:

- `idx_players_fts` - GIN index for full-text search
- `idx_players_position` - Position filter
- `idx_players_age` - Age filter
- `idx_players_ca` - CA filter
- `idx_players_pa` - PA filter
- `idx_players_nationality` - Nationality filter
- `idx_players_club` - Club filter
- `idx_players_position_ca` - Composite index for position + CA
- `idx_players_club_position` - Composite index for club + position

### Query Optimization

- Full-text search uses PostgreSQL's GIN index for fast text matching
- Filters are combined with AND logic for efficient query execution
- Pagination is applied after filtering to minimize data transfer
- Count query uses a subquery to avoid loading all data

### Best Practices

1. **Use specific filters** - More specific filters reduce result set size
2. **Limit results** - Use pagination with reasonable limits (50-100)
3. **Avoid open-ended searches** - Combine search_text with other filters
4. **Use appropriate sorting** - Relevance sorting requires search_text

## Integration with Task 9.1

This implementation builds on Task 9.1 (GIN index and helper methods):

- Uses `Player.search_query_expression()` for full-text search
- Uses `Player.search_rank_expression()` for relevance scoring
- Leverages the GIN index created in Task 9.1 migration

## Testing

Comprehensive tests are provided in:
- `test_player_search.py` - Unit tests with pytest
- `test_player_search_manual.py` - Manual test script

Run tests:
```bash
# Unit tests
pytest app/services/test_player_search.py -v

# Manual tests
python test_player_search_manual.py
```

## Future Enhancements

Potential improvements for future tasks:

1. **Advanced text search** - Support for phrase matching, wildcards
2. **Attribute filters** - Filter by specific technical/mental/physical attributes
3. **Trait filters** - Filter by player traits/characteristics
4. **Saved searches** - Save and reuse common search criteria
5. **Search history** - Track user search history
6. **Autocomplete** - Suggest players/clubs/nationalities as user types
7. **Fuzzy matching** - Handle typos in search text
8. **Multi-language support** - Search in multiple languages

## Related Files

- `app/models/player.py` - Player model with GIN index
- `app/services/player_search.py` - Search service implementation
- `app/services/test_player_search.py` - Unit tests
- `test_player_search_manual.py` - Manual test script
- `alembic/versions/20260514_1925-add_player_fts_gin_index.py` - GIN index migration

## Task Completion

✅ Task 9.2: Create search filters (position, age, CA, PA, nationality, club)

All required filters have been implemented:
- ✅ Position filter (partial match)
- ✅ Age range filter (min_age, max_age)
- ✅ Current Ability (CA) range filter (min_ca, max_ca)
- ✅ Potential Ability (PA) range filter (min_pa, max_pa)
- ✅ Nationality filter (exact match)
- ✅ Club filter (exact match)

Additional features:
- ✅ Full-text search integration (from Task 9.1)
- ✅ Multiple sorting options
- ✅ Pagination support
- ✅ Filter validation
- ✅ Combined filter support (AND logic)
- ✅ Filter options API
- ✅ Comprehensive test coverage
