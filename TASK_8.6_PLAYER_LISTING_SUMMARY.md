# Task 8.6: Player Listing System Implementation Summary

## Overview
Implemented a comprehensive player listing system that allows clubs to list players for transfer with an asking price, as specified in Requirement 6.6 of the Telegram Football Manager specification.

## Implementation Details

### 1. Database Schema Changes

#### Added Fields to `squad_players` Table
- **`is_listed_for_sale`** (Boolean, NOT NULL, default: false)
  - Indicates whether a player is currently listed for sale
  - Indexed for efficient queries of listed players
  
- **`asking_price`** (BigInteger, NULL)
  - The asking price set by the manager when listing a player
  - NULL when player is not listed
  - Constrained to be non-negative when set

#### Database Migration
Created migration file: `alembic/versions/20260514_1621-add_player_listing_fields.py`
- Adds the two new columns to squad_players table
- Creates check constraint for non-negative asking_price
- Creates index on is_listed_for_sale for performance
- Includes downgrade path for rollback

### 2. Model Updates

#### SquadPlayer Model (`app/models/squad_player.py`)

**New Fields:**
```python
is_listed_for_sale: Mapped[bool] = mapped_column(
    nullable=False,
    default=False,
    server_default="false",
    comment="Whether player is listed for sale"
)

asking_price: Mapped[Optional[int]] = mapped_column(
    BigInteger,
    nullable=True,
    comment="Asking price when listed for sale (NULL if not listed)"
)
```

**New Methods:**
- `list_for_sale(asking_price: int)` - List player for sale with validation
- `unlist_from_sale()` - Remove player from sale listing
- `is_listed()` - Check if player is currently listed

**Updated Methods:**
- `to_dict()` - Now includes transfer_listing section with is_listed_for_sale and asking_price

### 3. Service Layer Updates

#### TransferService (`app/services/transfer_service.py`)

**New/Updated Methods:**

1. **`validate_player_listing(squad_player, asking_price)`**
   - Validates that a player can be listed for sale
   - Checks: non-negative price, not already listed
   - Returns: (is_valid: bool, error_message: str)

2. **`list_player_for_sale(squad_player, asking_price)`**
   - Lists a player for sale with an asking price
   - Validates listing before applying changes
   - Updates squad_player object (caller persists to DB)
   - Returns: Dictionary with listing details
   - Raises: ValueError if validation fails

3. **`unlist_player_from_sale(squad_player)`**
   - Removes a player from sale listing
   - Clears is_listed_for_sale and asking_price
   - Returns: Dictionary with unlisting confirmation

4. **`get_listed_players(squad_players)`**
   - Filters and returns all players currently listed for sale
   - Takes list of SquadPlayer instances
   - Returns: List of listed players

5. **`get_listing_details(squad_player)`**
   - Gets listing details for a specific player
   - Returns: Dictionary with details if listed, None otherwise

### 4. Test Coverage

#### Comprehensive Test Suite (`tests/services/test_transfer_service_listing.py`)

**Test Classes:**

1. **TestPlayerListing** - Core listing functionality
   - ✓ List player for sale successfully
   - ✓ List with zero asking price (free transfer)
   - ✓ Reject negative asking price
   - ✓ Reject listing already listed player
   - ✓ Handle very high asking prices

2. **TestPlayerUnlisting** - Unlisting functionality
   - ✓ Unlist player successfully
   - ✓ Unlist player that isn't listed (idempotent)

3. **TestGetListedPlayers** - Retrieving listed players
   - ✓ Get listed players from mixed squad
   - ✓ Handle squad with no listed players
   - ✓ Handle squad with all players listed
   - ✓ Handle empty squad

4. **TestGetListingDetails** - Getting listing details
   - ✓ Get details for listed player
   - ✓ Return None for non-listed player

5. **TestValidatePlayerListing** - Validation logic
   - ✓ Validate with valid data
   - ✓ Reject negative price
   - ✓ Reject already listed player
   - ✓ Accept zero price

6. **TestListingWorkflow** - Complete workflows
   - ✓ List and unlist workflow
   - ✓ List multiple players with different prices
   - ✓ Partial unlisting

7. **TestEdgeCases** - Edge cases and boundaries
   - ✓ Very low wage players
   - ✓ Zero wage players
   - ✓ Multiple list/unlist cycles

**Total Tests:** 20+ comprehensive test cases

### 5. Key Features Implemented

#### Validation
- ✓ Asking price must be non-negative (can be 0 for free transfers)
- ✓ Cannot list a player who is already listed
- ✓ Only squad players can be listed (enforced by model relationship)

#### Listing Management
- ✓ List player with asking price
- ✓ Unlist player (idempotent operation)
- ✓ Update listing status in database
- ✓ Clear asking price when unlisting

#### Query Operations
- ✓ Get all listed players efficiently (indexed query)
- ✓ Get listing details for specific player
- ✓ Filter listed players from squad

#### Data Integrity
- ✓ Database constraints ensure data validity
- ✓ Check constraint: asking_price >= 0 when set
- ✓ Index on is_listed_for_sale for performance
- ✓ Atomic operations for listing/unlisting

## Integration with Existing System

### Compatibility with Task 8.7 (AI Bid Generation)
The listing system is designed to work seamlessly with AI bid generation:
- Listed players can be queried efficiently using `get_listed_players()`
- Listing details include all information needed for AI bids (player_id, asking_price, wage)
- The existing `generate_ai_bids_for_listed()` method can use these listings

### Database Relationships
- Maintains referential integrity with Player and Career models
- Listing status is part of SquadPlayer (junction table)
- Supports multiple careers with different listing statuses for same player

### Service Layer Design
- Stateless validation and business logic
- Caller responsible for database persistence
- Clear separation of concerns
- Reusable methods for different contexts

## Usage Examples

### Listing a Player
```python
from app.services.transfer_service import TransferService

service = TransferService()

# List a player for 1 million
result = service.list_player_for_sale(squad_player, 1000000)
# result = {"player_id": 1, "asking_price": 1000000, "wage": 5000, "listed": True}

# Persist to database
await session.commit()
```

### Unlisting a Player
```python
# Remove from sale
result = service.unlist_player_from_sale(squad_player)
# result = {"player_id": 1, "listed": False, "message": "Player removed from sale listing."}

# Persist to database
await session.commit()
```

### Getting Listed Players
```python
# Get all listed players in squad
squad_players = await session.execute(
    select(SquadPlayer).where(SquadPlayer.career_id == career_id)
)
squad_players = squad_players.scalars().all()

listed_players = service.get_listed_players(squad_players)
# Returns list of SquadPlayer objects where is_listed_for_sale == True
```

### Validating Before Listing
```python
# Validate before attempting to list
is_valid, error_msg = service.validate_player_listing(squad_player, asking_price)

if is_valid:
    service.list_player_for_sale(squad_player, asking_price)
    await session.commit()
else:
    print(f"Cannot list player: {error_msg}")
```

## Database Migration

To apply the migration:
```bash
# Upgrade to latest version
alembic upgrade head

# Or specifically to this migration
alembic upgrade add_player_listing_fields
```

To rollback:
```bash
# Downgrade one version
alembic downgrade -1

# Or specifically from this migration
alembic downgrade update_pa_constraint
```

## Performance Considerations

### Indexing
- `is_listed_for_sale` column is indexed for efficient filtering
- Queries for listed players use index scan instead of full table scan
- Typical query time: O(log n) for indexed lookup

### Query Optimization
```sql
-- Efficient query for listed players (uses index)
SELECT * FROM squad_players 
WHERE career_id = ? AND is_listed_for_sale = true;

-- Index: idx_squad_players_is_listed_for_sale
```

### Memory Efficiency
- Boolean flag uses minimal storage (1 byte)
- BigInteger for asking_price supports values up to 9,223,372,036,854,775,807
- NULL asking_price when not listed saves space

## Requirements Satisfied

✅ **Requirement 6.6**: "THE Transfer_Engine SHALL allow the player-manager to list players for sale and set an asking price."

**Implementation:**
- ✓ Players can be listed for sale via `list_player_for_sale()`
- ✓ Asking price is set and stored in database
- ✓ Listing status is tracked and queryable
- ✓ Players can be unlisted via `unlist_player_from_sale()`
- ✓ Only squad players can be listed (enforced by model)
- ✓ Validation ensures data integrity

## Next Steps (Task 8.7)

The player listing system is now ready for Task 8.7: "Implement AI bid generation for listed players"

The AI bid generation system can:
1. Query listed players using `get_listed_players()`
2. Access asking_price for each listed player
3. Generate bids based on asking_price and AI club budgets
4. Use existing `generate_ai_bids_for_listed()` method

## Files Modified/Created

### Created:
- `alembic/versions/20260514_1621-add_player_listing_fields.py` - Database migration
- `tests/services/test_transfer_service_listing.py` - Comprehensive test suite
- `test_listing_manual.py` - Manual test script (for verification)
- `TASK_8.6_PLAYER_LISTING_SUMMARY.md` - This summary document

### Modified:
- `app/models/squad_player.py` - Added listing fields and methods
- `app/services/transfer_service.py` - Added/updated listing methods

## Conclusion

Task 8.6 has been successfully implemented with:
- ✅ Database schema changes with migration
- ✅ Model updates with new fields and methods
- ✅ Service layer methods for listing management
- ✅ Comprehensive test coverage (20+ tests)
- ✅ Validation and error handling
- ✅ Integration with existing transfer system
- ✅ Performance optimizations (indexing)
- ✅ Complete documentation

The player listing system is production-ready and fully tested, providing a solid foundation for AI bid generation (Task 8.7) and the complete transfer market functionality.
