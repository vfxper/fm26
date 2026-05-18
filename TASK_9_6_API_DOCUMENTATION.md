# Task 9.6: Player Search API Endpoint - Implementation Documentation

## Overview

This document describes the implementation of the REST API endpoint for the player search system, completing Task 9.6 of the Telegram Football Manager project.

## Implementation Summary

### Files Created

1. **`app/schemas/player.py`** - Pydantic schemas for request/response models
   - `PlayerSearchRequest` - Request model for search endpoint
   - `PlayerResponse` - Response model for individual player data
   - `PlayerSearchResponse` - Response model for search results with pagination
   - `FilterOptionsResponse` - Response model for available filter options

2. **`app/api/routes/players.py`** - FastAPI route handlers
   - `POST /api/players/search` - Main search endpoint (JSON body)
   - `GET /api/players/search` - Alternative search endpoint (query parameters)
   - `GET /api/players/filter-options` - Get available filter options

3. **`tests/test_player_search_api.py`** - Comprehensive test suite
   - 20+ test cases covering all functionality
   - Tests for filters, pagination, sorting, validation, and error handling

### Files Modified

1. **`app/api/routes/__init__.py`** - Registered player routes
2. **`app/schemas/__init__.py`** - Exported player schemas

## API Endpoints

### 1. POST /api/players/search

Search for players using comprehensive filters with JSON request body.

**Request Body:**
```json
{
  "search_text": "Messi",
  "position": "ST",
  "min_age": 18,
  "max_age": 30,
  "min_ca": 150,
  "max_ca": 200,
  "min_pa": 160,
  "max_pa": 200,
  "nationality": "Argentina",
  "club": "Barcelona",
  "limit": 50,
  "offset": 0,
  "order_by": "ca"
}
```

**All fields are optional.**

**Response:**
```json
{
  "players": [
    {
      "uid": "player_001",
      "name": "Lionel Messi",
      "position": "AM/ST RL",
      "age": 36,
      "nationality": "Argentina",
      "club": "Inter Miami",
      "ca": 180,
      "pa": 200,
      "corners": 18,
      "crossing": 17,
      "dribbling": 20,
      "finishing": 19,
      "first_touch": 20,
      "free_kicks": 19,
      "heading": 10,
      "long_shots": 18,
      "long_throws": 8,
      "marking": 8,
      "passing": 19,
      "penalty": 18,
      "tackling": 7,
      "technique": 20,
      "aggression": 12,
      "anticipation": 19,
      "bravery": 14,
      "composure": 20,
      "concentration": 18,
      "decisions": 19,
      "determination": 18,
      "flair": 20,
      "leadership": 16,
      "off_the_ball": 19,
      "positioning": 18,
      "teamwork": 17,
      "vision": 20,
      "work_rate": 15,
      "acceleration": 16,
      "agility": 18,
      "balance": 19,
      "jumping": 10,
      "stamina": 15,
      "pace": 16,
      "endurance": 16,
      "strength": 11,
      "price": "50M",
      "wage": 500000,
      "height": 170,
      "weight": 67,
      "left_foot": 20,
      "right_foot": 12,
      "traits": "Dribbles Often, Finesse Shot, Playmaker"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

**Status Codes:**
- `200 OK` - Successful search
- `400 Bad Request` - Invalid filter parameters
- `422 Unprocessable Entity` - Request validation failed
- `500 Internal Server Error` - Database error

### 2. GET /api/players/search

Alternative search endpoint using query parameters (useful for bookmarkable URLs).

**Query Parameters:**
- `search_text` (optional) - Full-text search query
- `position` (optional) - Filter by position (partial match)
- `min_age` (optional) - Minimum age (15-50)
- `max_age` (optional) - Maximum age (15-50)
- `min_ca` (optional) - Minimum Current Ability (1-200)
- `max_ca` (optional) - Maximum Current Ability (1-200)
- `min_pa` (optional) - Minimum Potential Ability (-200 to 200)
- `max_pa` (optional) - Maximum Potential Ability (-200 to 200)
- `nationality` (optional) - Filter by nationality (exact match)
- `club` (optional) - Filter by club (exact match)
- `limit` (optional, default: 50) - Maximum results per page (1-200)
- `offset` (optional, default: 0) - Number of results to skip
- `order_by` (optional, default: "relevance") - Sort order

**Example:**
```
GET /api/players/search?search_text=Messi&min_ca=150&order_by=ca&limit=20
```

**Response:** Same as POST endpoint

### 3. GET /api/players/filter-options

Get available filter options from the database to build dynamic filter UIs.

**Response:**
```json
{
  "positions": ["GK", "DC", "DL", "DR", "DM", "MC", "ML", "MR", "AM", "ST"],
  "nationalities": ["Argentina", "Brazil", "England", "France", "Germany", "Italy", "Spain"],
  "clubs": ["Barcelona", "Real Madrid", "Manchester United", "Bayern Munich"],
  "age_range": {
    "min": 16,
    "max": 42
  },
  "ca_range": {
    "min": 50,
    "max": 200
  },
  "pa_range": {
    "min": -200,
    "max": 200
  }
}
```

**Status Codes:**
- `200 OK` - Successful retrieval
- `500 Internal Server Error` - Database error

## Filter Details

### Full-Text Search (`search_text`)
- Searches across player name, position, club, and nationality
- Uses PostgreSQL full-text search with GIN index
- Case-insensitive
- Supports partial matches
- Example: "Messi" finds "Lionel Messi"

### Position Filter (`position`)
- Supports partial matching
- Case-insensitive
- Example: "ST" matches "AM/ST RL", "ST C", "ST"

### Age Filters (`min_age`, `max_age`)
- Range: 15-50
- Inclusive bounds
- Both filters are optional
- Can use one or both

### Current Ability Filters (`min_ca`, `max_ca`)
- Range: 1-200
- Inclusive bounds
- Both filters are optional
- Can use one or both

### Potential Ability Filters (`min_pa`, `max_pa`)
- Range: -200 to 200
- Inclusive bounds
- Both filters are optional
- Can use one or both
- Note: Negative PA values indicate hidden potential

### Nationality Filter (`nationality`)
- Exact match (case-sensitive)
- Example: "Argentina" (not "argentina")

### Club Filter (`club`)
- Exact match (case-sensitive)
- Example: "Barcelona" (not "barcelona")

## Sorting Options

The `order_by` parameter supports the following values:

1. **`relevance`** (default) - Sort by search relevance score
   - **Requires `search_text` to be provided**
   - Uses PostgreSQL `ts_rank` function
   - Most relevant results first

2. **`ca`** - Sort by Current Ability (descending)
   - Highest CA first
   - Good for finding the best players

3. **`pa`** - Sort by Potential Ability (descending)
   - Highest PA first
   - Good for finding young talents

4. **`age`** - Sort by age (ascending)
   - Youngest first
   - Good for finding young players

5. **`name`** - Sort by name (ascending)
   - Alphabetical order
   - Good for browsing

## Pagination

The API supports pagination using `limit` and `offset` parameters:

- **`limit`**: Maximum number of results per page (1-200, default: 50)
- **`offset`**: Number of results to skip (0+, default: 0)

The response includes:
- `total`: Total number of matching players (before pagination)
- `has_more`: Boolean indicating if more results exist beyond this page

**Example - Paginating through results:**

```javascript
// Page 1
POST /api/players/search
{
  "position": "ST",
  "limit": 20,
  "offset": 0
}
// Returns players 1-20, has_more: true

// Page 2
POST /api/players/search
{
  "position": "ST",
  "limit": 20,
  "offset": 20
}
// Returns players 21-40, has_more: true

// Page 3
POST /api/players/search
{
  "position": "ST",
  "limit": 20,
  "offset": 40
}
// Returns players 41-60, has_more: false (if total is 55)
```

## Validation Rules

The API validates all input parameters:

### Age Validation
- `min_age` must be at least 15
- `max_age` must be at most 50
- `min_age` cannot be greater than `max_age`

### CA Validation
- `min_ca` must be between 1 and 200
- `max_ca` must be between 1 and 200
- `min_ca` cannot be greater than `max_ca`

### PA Validation
- `min_pa` must be between -200 and 200
- `max_pa` must be between -200 and 200
- `min_pa` cannot be greater than `max_pa`

### Pagination Validation
- `limit` must be between 1 and 200
- `offset` must be non-negative (0+)

### Sorting Validation
- `order_by` must be one of: "relevance", "ca", "pa", "age", "name"
- If `order_by` is "relevance", `search_text` must be provided

## Error Handling

### 400 Bad Request
Returned when filter validation fails:
```json
{
  "error": "ValidationError",
  "message": "min_ca cannot be greater than max_ca"
}
```

### 422 Unprocessable Entity
Returned when request body validation fails:
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": [
    {
      "loc": ["body", "min_ca"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
Returned when an unexpected error occurs:
```json
{
  "error": "InternalServerError",
  "message": "An error occurred while searching players"
}
```

## Usage Examples

### Example 1: Find all strikers with CA > 150
```bash
curl -X POST http://localhost:8000/api/players/search \
  -H "Content-Type: application/json" \
  -d '{
    "position": "ST",
    "min_ca": 150,
    "order_by": "ca"
  }'
```

### Example 2: Search for "Messi"
```bash
curl -X POST http://localhost:8000/api/players/search \
  -H "Content-Type: application/json" \
  -d '{
    "search_text": "Messi",
    "order_by": "relevance"
  }'
```

### Example 3: Find young talents (age 18-21, PA > 160)
```bash
curl -X POST http://localhost:8000/api/players/search \
  -H "Content-Type: application/json" \
  -d '{
    "min_age": 18,
    "max_age": 21,
    "min_pa": 160,
    "order_by": "pa"
  }'
```

### Example 4: Find Barcelona players
```bash
curl -X POST http://localhost:8000/api/players/search \
  -H "Content-Type: application/json" \
  -d '{
    "club": "Barcelona",
    "order_by": "ca"
  }'
```

### Example 5: Complex search with multiple filters
```bash
curl -X POST http://localhost:8000/api/players/search \
  -H "Content-Type: application/json" \
  -d '{
    "position": "ST",
    "min_age": 20,
    "max_age": 25,
    "min_ca": 170,
    "nationality": "France",
    "order_by": "ca",
    "limit": 10
  }'
```

### Example 6: Using GET endpoint with query parameters
```bash
curl "http://localhost:8000/api/players/search?position=ST&min_ca=180&order_by=ca&limit=10"
```

### Example 7: Get filter options
```bash
curl http://localhost:8000/api/players/filter-options
```

## Integration with PlayerSearchService

The API endpoints use the `PlayerSearchService` implemented in Task 9.2:

```python
from app.services.player_search import PlayerSearchService, PlayerSearchFilters

# Create service with database session
search_service = PlayerSearchService(db_session)

# Create filters
filters = PlayerSearchFilters(
    search_text="Messi",
    min_ca=150,
    order_by="relevance"
)

# Execute search
results = await search_service.search_players(filters)

# Results contain:
# - players: List[Player] - SQLAlchemy models
# - total: int - Total count
# - limit: int - Applied limit
# - offset: int - Applied offset
# - has_more: bool - More results available
```

## Pydantic Schema Validation

The API uses Pydantic for request/response validation:

### PlayerSearchRequest
- Validates all input parameters
- Provides field-level validation with constraints
- Generates OpenAPI documentation automatically

### PlayerResponse
- Converts SQLAlchemy Player model to JSON
- Includes all 50+ player attributes
- Uses `model_validate()` for conversion

### PlayerSearchResponse
- Wraps search results with pagination metadata
- Ensures consistent response format

## Testing

The implementation includes comprehensive tests in `tests/test_player_search_api.py`:

### Test Coverage
- ✅ Search with no filters
- ✅ Search with text search
- ✅ Search with position filter
- ✅ Search with age filter
- ✅ Search with CA filter
- ✅ Search with PA filter
- ✅ Search with nationality filter
- ✅ Search with club filter
- ✅ Search with pagination
- ✅ Search with multiple filters combined
- ✅ Invalid age range validation
- ✅ Invalid CA range validation
- ✅ Invalid order_by validation
- ✅ Relevance without search_text validation
- ✅ GET endpoint with query parameters
- ✅ Filter options endpoint
- ✅ Player response contains all attributes

### Running Tests
```bash
# Run all player search API tests
pytest tests/test_player_search_api.py -v

# Run specific test
pytest tests/test_player_search_api.py::TestPlayerSearchAPI::test_search_players_post_with_text_search -v

# Run with coverage
pytest tests/test_player_search_api.py --cov=app.api.routes.players --cov=app.schemas.player
```

### Manual Testing
A manual test script is provided for quick verification:
```bash
python test_player_search_api_manual.py
```

## Performance Considerations

### Database Optimization
- Uses PostgreSQL GIN index for full-text search (created in Task 9.4)
- Efficient query construction with SQLAlchemy
- Pagination limits result set size
- Count query optimized with subquery

### Response Size
- Player objects include all 50+ attributes
- Consider implementing field selection in future if needed
- Current approach provides complete player data

### Caching Opportunities
- Filter options could be cached (rarely change)
- Popular searches could be cached
- Consider Redis caching for high-traffic scenarios

## API Documentation

The API is fully documented with:
- OpenAPI/Swagger documentation at `/docs` (when DEBUG=True)
- ReDoc documentation at `/redoc` (when DEBUG=True)
- Detailed docstrings in route handlers
- Request/response examples in schemas

## Future Enhancements

Potential improvements for future tasks:

1. **Field Selection**: Allow clients to specify which fields to return
2. **Saved Searches**: Allow users to save and reuse search filters
3. **Search History**: Track user search history
4. **Advanced Filters**: Add more filter options (e.g., specific attributes)
5. **Bulk Operations**: Support bulk player retrieval by IDs
6. **Export**: Allow exporting search results to CSV/JSON
7. **Caching**: Implement Redis caching for popular searches
8. **Rate Limiting**: Add rate limiting to prevent abuse

## Conclusion

Task 9.6 is complete. The player search API endpoint is fully implemented with:

✅ REST API endpoints (POST and GET)
✅ Comprehensive request/response models
✅ Full integration with PlayerSearchService
✅ Extensive test coverage
✅ Proper error handling and validation
✅ Complete API documentation
✅ FastAPI best practices followed

The API is ready for integration with the frontend and provides a robust, scalable solution for player search functionality.
