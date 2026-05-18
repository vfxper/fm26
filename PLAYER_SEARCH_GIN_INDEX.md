# Player Full-Text Search with PostgreSQL GIN Index

## Overview

This document describes the implementation of full-text search functionality for the players table using PostgreSQL's GIN (Generalized Inverted Index) index.

## What is a GIN Index?

A GIN (Generalized Inverted Index) is a PostgreSQL index type optimized for indexing composite values, such as arrays, full-text search documents, and JSONB data. For full-text search, GIN indexes are significantly faster than sequential scans or B-tree indexes.

### Benefits of GIN Index for Player Search

1. **Fast Full-Text Search**: Enables sub-second search across 2600+ players
2. **Multi-Field Search**: Searches across name, position, club, and nationality simultaneously
3. **Language-Agnostic**: Uses 'simple' configuration to support multiple languages
4. **Relevance Ranking**: Supports ts_rank for ordering results by relevance
5. **Scalable**: Performance remains consistent even with large datasets

## Implementation Details

### Database Schema

The GIN index is created on a `tsvector` expression that combines four searchable fields:

```sql
CREATE INDEX idx_players_fts ON players 
USING GIN(
    to_tsvector('simple', 
        COALESCE(name, '') || ' ' || 
        COALESCE(position, '') || ' ' || 
        COALESCE(club, '') || ' ' || 
        COALESCE(nationality, '')
    )
)
```

### Indexed Fields

- **name**: Player name (e.g., "Lionel Messi")
- **position**: Player position(s) (e.g., "AM/ST RL")
- **club**: Current club name (e.g., "FC Barcelona")
- **nationality**: Player nationality (e.g., "Argentina")

### Text Search Configuration

The index uses PostgreSQL's `'simple'` text search configuration, which:
- Does not perform stemming (e.g., "running" ≠ "run")
- Does not remove stop words (e.g., "the", "and" are indexed)
- Is language-agnostic (works with any language)
- Provides exact and predictable matching behavior

This is ideal for player names, clubs, and nationalities which should not be stemmed.

## Usage

### Basic Search Query

```python
from sqlalchemy import select
from app.models.player import Player

# Search for players
stmt = select(Player).where(
    Player.search_query_expression("Messi")
).limit(50)

# Execute query
async with session_factory() as session:
    result = await session.execute(stmt)
    players = result.scalars().all()
```

### Search with Relevance Ranking

```python
from sqlalchemy import select
from app.models.player import Player

# Search and order by relevance
rank = Player.search_rank_expression("midfielder")
stmt = select(
    Player,
    rank.label('relevance')
).where(
    Player.search_query_expression("midfielder")
).order_by(
    rank.desc()
).limit(50)

# Execute query
async with session_factory() as session:
    result = await session.execute(stmt)
    rows = result.all()
    for player, relevance in rows:
        print(f"{player.name} - Relevance: {relevance}")
```

### Complex Multi-Term Search

```python
# Search for "Portugal forward" - matches players who are Portuguese forwards
stmt = select(Player).where(
    Player.search_query_expression("Portugal forward")
).limit(50)
```

### Raw SQL Query (for reference)

```sql
-- Basic search
SELECT * FROM players
WHERE to_tsvector('simple', 
    COALESCE(name, '') || ' ' || 
    COALESCE(position, '') || ' ' || 
    COALESCE(club, '') || ' ' || 
    COALESCE(nationality, '')
) @@ plainto_tsquery('simple', 'search text')
LIMIT 50;

-- Search with relevance ranking
SELECT 
    *,
    ts_rank(
        to_tsvector('simple', 
            COALESCE(name, '') || ' ' || 
            COALESCE(position, '') || ' ' || 
            COALESCE(club, '') || ' ' || 
            COALESCE(nationality, '')
        ),
        plainto_tsquery('simple', 'search text')
    ) AS relevance
FROM players
WHERE to_tsvector('simple', 
    COALESCE(name, '') || ' ' || 
    COALESCE(position, '') || ' ' || 
    COALESCE(club, '') || ' ' || 
    COALESCE(nationality, '')
) @@ plainto_tsquery('simple', 'search text')
ORDER BY relevance DESC
LIMIT 50;
```

## Helper Methods

The `Player` model provides two static helper methods for full-text search:

### 1. `search_query_expression(search_text: str)`

Creates a boolean expression for filtering players by search text.

**Parameters:**
- `search_text` (str): The search query (e.g., "Messi Barcelona")

**Returns:**
- SQLAlchemy boolean expression that can be used in `.where()` clauses

**Example:**
```python
stmt = select(Player).where(
    Player.search_query_expression("Ronaldo Portugal")
)
```

### 2. `search_rank_expression(search_text: str)`

Creates a relevance score expression for ordering search results.

**Parameters:**
- `search_text` (str): The search query

**Returns:**
- SQLAlchemy expression for relevance ranking (higher = more relevant)

**Example:**
```python
rank = Player.search_rank_expression("striker")
stmt = select(Player, rank.label('rank')).where(
    Player.search_query_expression("striker")
).order_by(rank.desc())
```

## Installation

### Option 1: Using Alembic Migration (Recommended)

```bash
# Run the migration
alembic upgrade head
```

The migration file is located at:
`alembic/versions/20260514_1925-add_player_fts_gin_index.py`

### Option 2: Manual Application

If Alembic has issues, use the manual application script:

```bash
python apply_gin_index.py
```

This script will:
1. Check if the index already exists
2. Create the GIN index if needed
3. Verify the index was created successfully
4. Test the index with a sample query

## Testing

Run the comprehensive test suite to verify the GIN index:

```bash
python test_gin_index.py
```

The test suite includes:
1. Index existence verification
2. Player count check
3. Search by player name
4. Search by position
5. Search by club
6. Relevance ranking test
7. Complex multi-term search
8. Performance benchmark

## Performance Characteristics

### Query Performance

With the GIN index, full-text search queries typically complete in:
- **< 10ms**: Small result sets (< 100 players)
- **< 50ms**: Medium result sets (100-1000 players)
- **< 100ms**: Large result sets (1000+ players)

### Index Size

The GIN index adds approximately:
- **5-10 MB** for 2,600 players
- **50-100 MB** for 26,000 players
- **500 MB - 1 GB** for 260,000 players

### Index Maintenance

GIN indexes are automatically maintained by PostgreSQL:
- **INSERT**: Slightly slower than without index (~10-20% overhead)
- **UPDATE**: Only affected if indexed fields change
- **DELETE**: Minimal overhead
- **VACUUM**: Recommended periodically to optimize index

## Search Examples

### Example 1: Find all strikers
```python
stmt = select(Player).where(
    Player.search_query_expression("striker")
).limit(50)
```

### Example 2: Find Barcelona players
```python
stmt = select(Player).where(
    Player.search_query_expression("Barcelona")
).limit(50)
```

### Example 3: Find Portuguese midfielders
```python
stmt = select(Player).where(
    Player.search_query_expression("Portugal midfielder")
).limit(50)
```

### Example 4: Find specific player by name
```python
stmt = select(Player).where(
    Player.search_query_expression("Cristiano Ronaldo")
).limit(10)
```

### Example 5: Search with filters
```python
# Combine full-text search with attribute filters
stmt = select(Player).where(
    Player.search_query_expression("midfielder"),
    Player.ca >= 150,
    Player.age <= 25
).limit(50)
```

## Troubleshooting

### Index Not Found

If you get an error about the index not existing:

1. Check if the index exists:
```sql
SELECT indexname FROM pg_indexes 
WHERE tablename = 'players' AND indexname = 'idx_players_fts';
```

2. Create the index manually:
```bash
python apply_gin_index.py
```

### Slow Query Performance

If queries are slow:

1. Verify the index is being used:
```sql
EXPLAIN ANALYZE
SELECT * FROM players
WHERE to_tsvector('simple', name || ' ' || position || ' ' || club || ' ' || nationality)
      @@ plainto_tsquery('simple', 'search text');
```

Look for "Index Scan using idx_players_fts" in the output.

2. Run VACUUM ANALYZE to update statistics:
```sql
VACUUM ANALYZE players;
```

### No Results Found

If searches return no results:

1. Check if players exist in the database:
```sql
SELECT COUNT(*) FROM players;
```

2. Try a broader search term:
```python
# Instead of exact match
stmt = select(Player).where(Player.name == "Messi")

# Use full-text search (more flexible)
stmt = select(Player).where(
    Player.search_query_expression("Messi")
)
```

## Best Practices

1. **Use Pagination**: Always limit results to avoid loading too many players
   ```python
   stmt = select(Player).where(
       Player.search_query_expression(query)
   ).limit(50).offset(page * 50)
   ```

2. **Combine with Filters**: Use full-text search with attribute filters for precise results
   ```python
   stmt = select(Player).where(
       Player.search_query_expression(query),
       Player.ca >= min_ca,
       Player.position.like(f"%{position}%")
   )
   ```

3. **Order by Relevance**: Use relevance ranking for better user experience
   ```python
   rank = Player.search_rank_expression(query)
   stmt = select(Player).where(
       Player.search_query_expression(query)
   ).order_by(rank.desc())
   ```

4. **Cache Results**: For frequently searched terms, cache results in Redis
   ```python
   cache_key = f"player_search:{query}"
   cached = await redis.get(cache_key)
   if cached:
       return json.loads(cached)
   # ... perform search and cache results
   ```

## API Integration

### REST API Endpoint Example

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.models.player import Player

router = APIRouter()

@router.get("/players/search")
async def search_players(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Search players using full-text search.
    
    - **q**: Search query (searches name, position, club, nationality)
    - **limit**: Maximum number of results (default: 50, max: 100)
    - **offset**: Pagination offset (default: 0)
    """
    # Build query with relevance ranking
    rank = Player.search_rank_expression(q)
    stmt = select(
        Player,
        rank.label('relevance')
    ).where(
        Player.search_query_expression(q)
    ).order_by(
        rank.desc()
    ).limit(limit).offset(offset)
    
    # Execute query
    result = await session.execute(stmt)
    rows = result.all()
    
    # Format response
    players = [
        {
            **player.to_dict(),
            "relevance": float(relevance)
        }
        for player, relevance in rows
    ]
    
    return {
        "query": q,
        "total": len(players),
        "limit": limit,
        "offset": offset,
        "results": players
    }
```

## References

- [PostgreSQL Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch.html)
- [PostgreSQL GIN Indexes](https://www.postgresql.org/docs/current/gin.html)
- [SQLAlchemy Full-Text Search](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#full-text-search)

## Changelog

### 2026-05-14
- Initial implementation of GIN index for player full-text search
- Created migration file: `20260514_1925-add_player_fts_gin_index.py`
- Added helper methods to Player model: `search_query_expression()` and `search_rank_expression()`
- Created manual application script: `apply_gin_index.py`
- Created comprehensive test suite: `test_gin_index.py`
- Documented usage and best practices
