# Task 8.5: Loan Deal System Implementation Summary

## Overview
Implemented a comprehensive loan deal system supporting both season-long and emergency loans with async database integration, following the patterns established in tasks 8.1 and 8.2.

## Implementation Details

### 1. Core Functionality

#### Season-Long Loans
- **Availability**: Only during transfer windows (weeks 1-8 summer, 26-30 winter)
- **Duration**: Automatically calculated until end of season (week 52)
- **Use Case**: Standard loan deals for player development

#### Emergency Loans
- **Availability**: Outside transfer windows (weeks 9-25, 31-52)
- **Duration**: Specified by manager (maximum 12 weeks)
- **Use Case**: Short-term cover for injuries or squad depth

### 2. Async Database Methods

#### `submit_loan_offer_async()`
Main method for submitting loan offers with full database integration:

```python
async def submit_loan_offer_async(
    db: AsyncSession,
    career_id: int,
    player_id: int,
    loan_type: str,  # "season_long" or "emergency"
    wage_contribution: float,  # 0.0-1.0
    loan_duration_weeks: Optional[int] = None,  # Required for emergency loans
) -> dict
```

**Features**:
- Validates loan type and transfer window status
- Validates squad size (max 40 players)
- Validates wage contribution (0.0-1.0 range)
- Checks player not already in squad
- Creates Transfer record with loan details
- Calculates AI acceptance probability
- Creates SquadPlayer record if accepted
- Tracks loan return date via contract_end_date

**Return Value**:
```python
{
    "success": bool,
    "accepted": bool,
    "message": str,
    "transfer_id": int,
    "squad_player_id": int,  # If accepted
    "loan_type": str,
    "loan_duration_weeks": int,
    "loan_return_date": str,  # ISO format
    "wage_contribution": float,
    "wage_cost_per_week": int,
    "total_wage_cost": int,
    "squad_number": int,  # If accepted
    "player": dict,
}
```

#### `get_active_loans()`
Retrieves all active loan players in the squad:

```python
async def get_active_loans(
    db: AsyncSession,
    career_id: int,
) -> List[dict]
```

**Returns**: List of active loan players with:
- Player details (name, position, CA, PA)
- Parent club name
- Loan type and return date
- Wage contribution and costs
- Squad number and morale

### 3. Database Integration

#### Transfer Record
Loan deals create Transfer records with:
- `transfer_type`: `TransferType.LOAN` or `TransferType.EMERGENCY_LOAN`
- `transfer_fee`: 0 (no fee for loans)
- `loan_duration`: Duration in weeks
- `wage_contribution`: Percentage paid by borrowing club (0.0-1.0)
- `wage_offer`: Full player wage (from Player model)

#### Squad Player Record
Accepted loans create SquadPlayer records with:
- `contract_start_date`: Current date
- `contract_end_date`: Loan return date (calculated from duration)
- `wage`: Actual wage cost (player_wage * wage_contribution)
- `squad_status`: `SquadStatus.FIRST_TEAM`
- `morale`: 70 (default)

### 4. Loan Return Date Tracking

Loan return dates are tracked via the SquadPlayer `contract_end_date` field:

**Season-Long Loan**:
```python
loan_duration = 52 - current_week
loan_return_date = today + relativedelta(weeks=loan_duration)
```

**Emergency Loan**:
```python
loan_duration = loan_duration_weeks  # Max 12 weeks
loan_return_date = today + relativedelta(weeks=loan_duration)
```

The `contract_end_date` serves as the loan expiry date, after which the player should be returned to their parent club.

### 5. Wage Contribution System

The wage contribution determines how much of the player's wage the borrowing club pays:

- **0.0 (0%)**: Parent club pays all wages (less likely to be accepted)
- **0.5 (50%)**: Split wages equally
- **1.0 (100%)**: Borrowing club pays all wages (more likely to be accepted)

**Wage Cost Calculation**:
```python
player_wage = player.wage  # From Player model
wage_cost = int(player_wage * wage_contribution)
total_cost = wage_cost * loan_duration
```

**AI Acceptance Probability**:
```python
acceptance_base = 0.4
acceptance_base += wage_contribution * 0.4  # Up to +0.4 for full wage
if loan_type == "emergency":
    acceptance_base += 0.1  # Emergency loans slightly easier
```

### 6. Validation Rules

#### Transfer Window Validation
- **Season-long loans**: Require open transfer window
- **Emergency loans**: Can be done outside windows

#### Squad Size Validation
- Maximum 40 players in squad
- Loan adds to squad count

#### Wage Contribution Validation
- Must be between 0.0 and 1.0
- Invalid values rejected immediately

#### Contract Length Validation
- Player must have > 6 months on contract
- Short contracts rejected to avoid complications

#### Player Availability
- Cannot loan player already in squad
- Cannot loan free agents (must have parent club)

### 7. Test Coverage

Created comprehensive test suite (`test_loan_deal_system.py`) covering:

1. **Season-Long Loans**
   - During open window (success)
   - During closed window (rejection)
   - Duration calculation
   - Return date tracking

2. **Emergency Loans**
   - Outside transfer window (success)
   - Without duration parameter (rejection)
   - Duration exceeding 12 weeks (rejection)
   - Duration calculation

3. **Wage Contribution**
   - Negative contribution (rejection)
   - Over 1.0 contribution (rejection)
   - 0% contribution (valid)
   - 100% contribution (valid)
   - Cost calculation

4. **Squad Validation**
   - Full squad (40 players) rejection
   - Player already in squad rejection

5. **Database Integration**
   - Transfer record creation
   - Squad player creation
   - Loan return date tracking
   - Active loans retrieval

6. **AI Acceptance**
   - High wage contribution probability
   - Low wage contribution probability
   - Emergency loan bonus

7. **Edge Cases**
   - Invalid loan type
   - Short contract rejection
   - Free agent rejection

## Files Modified

### 1. `app/services/transfer_service.py`
Added async methods:
- `submit_loan_offer_async()`: Main loan submission method
- `get_active_loans()`: Retrieve active loan players

### 2. `app/services/test_loan_deal_system.py` (NEW)
Comprehensive test suite with 20+ test cases covering all loan scenarios.

### 3. `test_loan_manual.py` (NEW)
Manual test script demonstrating:
- Season-long loan during transfer window
- Emergency loan outside transfer window
- Active loans retrieval

### 4. `TASK_8_5_LOAN_SYSTEM_SUMMARY.md` (NEW)
This documentation file.

## Integration with Existing System

The loan system integrates seamlessly with:

1. **Transfer Window System (Task 8.1)**
   - Uses `TransferWindowService` for window validation
   - Season-long loans respect transfer windows
   - Emergency loans bypass window restrictions

2. **Transfer Bid System (Task 8.2)**
   - Follows same async pattern
   - Uses same validation methods
   - Creates Transfer records consistently
   - Creates SquadPlayer records on acceptance

3. **Database Models**
   - Uses existing `Transfer` model with loan-specific fields
   - Uses existing `SquadPlayer` model for loan players
   - Leverages `TransferType.LOAN` and `TransferType.EMERGENCY_LOAN` enums

4. **Squad Management (Task 7)**
   - Respects squad size limits (40 players)
   - Creates squad players with proper status
   - Tracks loan return dates via contract dates

## Usage Example

```python
from app.services.transfer_service import TransferService

service = TransferService()

# Submit season-long loan during transfer window
result = await service.submit_loan_offer_async(
    db=session,
    career_id=1,
    player_id=123,
    loan_type="season_long",
    wage_contribution=0.6,  # Pay 60% of wages
)

if result["accepted"]:
    print(f"Loan completed! Return date: {result['loan_return_date']}")
    print(f"Weekly cost: £{result['wage_cost_per_week']:,}")

# Submit emergency loan outside window
result = await service.submit_loan_offer_async(
    db=session,
    career_id=1,
    player_id=456,
    loan_type="emergency",
    wage_contribution=0.8,  # Pay 80% of wages
    loan_duration_weeks=10,
)

# Get all active loans
active_loans = await service.get_active_loans(
    db=session,
    career_id=1,
)

for loan in active_loans:
    print(f"{loan['player']['name']} - Returns: {loan['loan_return_date']}")
```

## Future Enhancements

Potential improvements for future tasks:

1. **Loan Recall System**
   - Allow parent club to recall player early
   - Implement recall clauses in loan agreements

2. **Option to Buy**
   - Add optional purchase clause to loans
   - Automatic conversion to permanent transfer

3. **Loan Performance Tracking**
   - Track player performance during loan
   - Affect parent club's willingness to loan again

4. **Loan Fees**
   - Add optional loan fees (currently all loans are free)
   - Negotiate loan fee separate from wages

5. **Automatic Loan Returns**
   - Weekly job to return players when loan expires
   - Notification system for expiring loans

## Testing

Run the test suite:
```bash
pytest app/services/test_loan_deal_system.py -v
```

Run manual demonstration:
```bash
python test_loan_manual.py
```

## Conclusion

Task 8.5 is complete with:
- ✅ Season-long loan system implemented
- ✅ Emergency loan system implemented
- ✅ Wage contribution negotiation working
- ✅ Loan duration management implemented
- ✅ Loan return date tracking via contract dates
- ✅ Async database integration following task 8.2 patterns
- ✅ Transfer record creation for loans
- ✅ Squad player creation for loan players
- ✅ Comprehensive test coverage (20+ tests)
- ✅ Manual test script for demonstration
- ✅ Full documentation

The loan system is production-ready and fully integrated with the existing transfer engine.
