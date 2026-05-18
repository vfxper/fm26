# Task 9.4: Relevance Scoring - Verification Guide

## Quick Verification

Task 9.4 implements relevance scoring for player search results. Here's how to verify it works:

### 1. Code Verification ✅

**Check `Player.search_rank_expression()` exists:**
```bash
# File: app/models/player.py
# Line: ~450-480
# Method: search_rank_expression(search_text: str)
```

**Check `PlayerSearchService` uses relevance scoring:**
```bash
# File: app/services/player_search.py
# Line: ~180-190
# Code: if filters.order_by == "relevance" and filters.search_text:
```

### 2. Test Verification

**Run the unit tests:**
```bash
# Run all player search tests (includes relevance tests)
pytest app/services/test_player_search.py -v

# Run only relevance tests
pytest app/services/test_player_search.py::test_relevance_scoring -v
pytest app/services/test_player_search.py::test_relevance_scoring_club -v
pytest app/services/test_player_search.py::test_relevance_vs_ca_sorting -v
```

**Run the comprehensive relevance test suite:**
```bash
# Run the dedicated relevance scoring tests
python test_relevance_scoring.py
```

### 3. Manual Verification

**Test with Python REPL:**
```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.services.player_search import PlayerSearchService, PlayerSearchFilters

async def test_relevance():
    # Connect to database
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/fm26")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        service = PlayerSearchService(session)
        
        # Test 1: Search by name with relevance
        filters = PlayerSearchFilters(search_text="Messi", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"Search 'Messi' with relevance:")
        for i, player in enumerate(results['players'][:5], 1):
            print(f"  {i}. {player.name} (Club: {player.club})")
        
        # Test 2: Search by club with relevance
        filters = PlayerSearchFilters(search_text="Barcelona", order_by="relevance")
        results = await service.search_players(filters)
        
        print(f"\nSearch 'Barcelona' with relevance:")
        for i, player in enumerate(results['players'][:5], 1):
            print(f"  {i}. {player.name} (Club: {player.club})")
        
        # Test 3: Compare relevance vs CA sorting
        filters_rel = PlayerSearchFilters(search_text="Manchester", order_by="relevance")
        results_rel = await service.search_players(filters_rel)
        
        filters_ca = PlayerSearchFilters(search_text="Manchester", order_by="ca")
        results_ca = await service.search_players(filters_ca)
        
        print(f"\nSearch 'Manchester' - Relevance order:")
        for i, player in enumerate(results_rel['players'][:3], 1):
            print(f"  {i}. {player.name} (CA: {player.ca})")
        
        print(f"\nSearch 'Manchester' - CA order:")
        for i, player in enumerate(results_ca['players'][:3], 1):
            print(f"  {i}. {player.name} (CA: {player.ca})")
    
    await engine.dispose()

# Run the test
asyncio.run(test_relevance())
```

### 4. Expected Behavior

**✅ Correct Behavior:**

1. **Name matches rank highest:**
   - Search "Messi" → Lionel Messi appears first
   - Search "Ronaldo" → Cristiano Ronaldo appears first

2. **Club matches rank high:**
   - Search "Barcelona" → Barcelona players appear first
   - Search "Manchester" → Manchester United/City players appear first

3. **Multi-word searches work:**
   - Search "Manchester United" → Manchester United players rank higher than Manchester City

4. **Validation works:**
   - `order_by="relevance"` without `search_text` → ValueError
   - `order_by="relevance"` with `search_text` → Works correctly

5. **Integration works:**
   - Relevance sorting works with filters (position, age, CA, PA)
   - Relevance sorting works with pagination
   - Results are ordered by ts_rank() descending

**❌ Incorrect Behavior:**

1. Random order when using relevance sorting
2. Same order as CA/PA sorting
3. No error when using relevance without search_text
4. Relevance sorting doesn't work with filters

### 5. Database Query Verification

**Check that ts_rank() is used:**
```sql
-- Enable query logging in PostgreSQL
SET log_statement = 'all';

-- Run a search with relevance sorting
-- Check logs for ts_rank() in ORDER BY clause
```

**Expected query pattern:**
```sql
SELECT players.*
FROM players
WHERE to_tsvector('simple', ...) @@ plainto_tsquery('simple', 'search_term')
ORDER BY ts_rank(to_tsvector('simple', ...), plainto_tsquery('simple', 'search_term')) DESC
LIMIT 50;
```

### 6. Performance Verification

**Check that GIN index is used:**
```sql
EXPLAIN ANALYZE
SELECT * FROM players
WHERE to_tsvector('simple', 
    COALESCE(name, '') || ' ' || 
    COALESCE(position, '') || ' ' || 
    COALESCE(club, '') || ' ' || 
    COALESCE(nationality, '')
) @@ plainto_tsquery('simple', 'Messi')
ORDER BY ts_rank(
    to_tsvector('simple', 
        COALESCE(name, '') || ' ' || 
        COALESCE(position, '') || ' ' || 
        COALESCE(club, '') || ' ' || 
        COALESCE(nationality, '')
    ),
    plainto_tsquery('simple', 'Messi')
) DESC
LIMIT 50;
```

**Expected output should include:**
- `Bitmap Index Scan on idx_players_fts` (GIN index usage)
- `Sort` operation for ts_rank()
- Fast execution time (< 100ms for 34,000+ players)

## Verification Checklist

- [ ] `Player.search_rank_expression()` method exists
- [ ] `PlayerSearchService.search_players()` uses relevance scoring
- [ ] Validation prevents relevance without search_text
- [ ] Unit tests pass (test_relevance_scoring*)
- [ ] Manual testing shows correct ordering
- [ ] Name matches rank highest
- [ ] Club matches rank high
- [ ] Multi-word searches work
- [ ] Integration with filters works
- [ ] Integration with pagination works
- [ ] GIN index is used (check EXPLAIN ANALYZE)
- [ ] Performance is acceptable (< 100ms)

## Common Issues

### Issue 1: "order_by='relevance' requires search_text"
**Cause:** Trying to use relevance sorting without providing search_text
**Solution:** Always provide search_text when using order_by="relevance"

### Issue 2: Relevance sorting returns same order as CA sorting
**Cause:** Not using search_text, or search_text doesn't match any players
**Solution:** Verify search_text is provided and matches some players

### Issue 3: Slow performance
**Cause:** GIN index not being used, or ts_rank() calculation is slow
**Solution:** 
- Check that GIN index exists: `\d players` in psql
- Run EXPLAIN ANALYZE to verify index usage
- Consider limiting result set with filters

### Issue 4: Tests fail with "No module named 'pytest'"
**Cause:** Test dependencies not installed
**Solution:** `pip install pytest pytest-asyncio aiosqlite`

## Success Criteria

Task 9.4 is complete when:

1. ✅ `Player.search_rank_expression()` exists and returns correct SQLAlchemy expression
2. ✅ `PlayerSearchService.search_players()` uses relevance scoring when `order_by="relevance"`
3. ✅ Validation prevents relevance sorting without search_text
4. ✅ Unit tests pass and cover relevance scoring scenarios
5. ✅ Manual testing shows correct result ordering
6. ✅ Integration with filters and pagination works
7. ✅ Performance is acceptable (< 100ms for typical searches)
8. ✅ Documentation is complete

## Conclusion

Task 9.4 is **COMPLETE**. The relevance scoring system:

- ✅ Uses PostgreSQL `ts_rank()` for intelligent result ordering
- ✅ Integrates with GIN index (Task 9.1)
- ✅ Works with search filters (Task 9.2)
- ✅ Works with pagination (Task 9.3)
- ✅ Has comprehensive tests
- ✅ Has complete documentation

The implementation provides a solid foundation for the player search system, enabling users to find the most relevant players based on their search queries.
