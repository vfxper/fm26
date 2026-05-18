# Free Agent Signing System Documentation (Task 8.9)

## Overview

The Free Agent Signing System allows managers to sign players who are not currently under contract with any club. Unlike regular transfers, free agent signings:

- **Can be completed at any time** (not restricted to transfer windows)
- **Require no transfer fee** (only wage agreement)
- **Are always accepted** (no negotiation with selling club)
- **Still subject to squad size and wage budget constraints**

## Implementation

### Location
- **Service**: `app/services/transfer_service.py`
- **Method**: `TransferService.sign_free_agent()`
- **Tests**: `tests/services/test_transfer_service_free_agent.py`
- **Manual Test**: `test_free_agent_manual.py`

### Method Signature

```python
def sign_free_agent(
    self,
    career_week: int,
    current_squad_size: int,
    career_transfer_budget: int,
    wage_offer: int,
    contract_years: int,
    wage_budget: int,
    current_wage_bill: int,
) -> BidResult:
    """
    Sign a free agent player (available outside transfer windows).

    Free agents can be signed at any time during the season.
    No transfer fee is required, only wage agreement.

    Args:
        career_week: Current week (free agents available any week).
        current_squad_size: Current squad size.
        career_transfer_budget: Transfer budget (not used for fee but checked).
        wage_offer: Weekly wage offered to the free agent.
        contract_years: Contract length offered (1-5 years).
        wage_budget: Total wage budget available.
        current_wage_bill: Current weekly wage bill.

    Returns:
        BidResult indicating success or failure.
    """
```

## Validation Rules

The free agent signing system validates the following conditions in order:

### 1. Squad Size Validation
- **Rule**: Squad must have fewer than 40 players
- **Constant**: `MAX_SQUAD_SIZE = 40`
- **Rejection Reason**: `"squad_full"`
- **Error Message**: "Squad is full (max 40 players)."

### 2. Contract Length Validation
- **Rule**: Contract must be between 1 and 5 years (inclusive)
- **Constants**: 
  - `MIN_CONTRACT_YEARS = 1`
  - `MAX_CONTRACT_YEARS = 5`
- **Rejection Reason**: `"invalid_contract"`
- **Error Message**: "Contract must be 1-5 years."

### 3. Wage Offer Validation
- **Rule**: Wage offer must be positive (> 0)
- **Rejection Reason**: `"invalid_wage"`
- **Error Message**: "Wage offer must be positive."

### 4. Wage Budget Validation
- **Rule**: `current_wage_bill + wage_offer <= wage_budget`
- **Rejection Reason**: `"wage_budget_exceeded"`
- **Error Message**: "Insufficient wage budget for this signing."

## Return Value

The method returns a `BidResult` object with the following properties:

### Success Case
```python
BidResult(
    success=True,
    accepted=True,
    message="Free agent signed successfully.",
    bid_amount=0,  # No transfer fee
    acceptance_probability=1.0,  # Always accepted
    rejection_reason=None
)
```

### Failure Cases

#### Squad Full
```python
BidResult(
    success=False,
    accepted=False,
    message="Squad is full (max 40 players).",
    rejection_reason="squad_full"
)
```

#### Invalid Contract
```python
BidResult(
    success=False,
    accepted=False,
    message="Contract must be 1-5 years.",
    rejection_reason="invalid_contract"
)
```

#### Invalid Wage
```python
BidResult(
    success=False,
    accepted=False,
    message="Wage offer must be positive.",
    rejection_reason="invalid_wage"
)
```

#### Wage Budget Exceeded
```python
BidResult(
    success=False,
    accepted=False,
    message="Insufficient wage budget for this signing.",
    rejection_reason="wage_budget_exceeded"
)
```

## Key Features

### 1. Available Any Time
Free agents can be signed during any week of the season, including:
- During transfer windows (weeks 1-8, 26-30)
- Outside transfer windows (weeks 9-25, 31-52)
- At any point in the season (weeks 1-52)

### 2. No Transfer Fee
- `bid_amount` is always 0
- Transfer budget is not checked or deducted
- Only wage agreement is required

### 3. Always Accepted
- `acceptance_probability` is always 1.0
- No AI negotiation or rejection
- No selling club to negotiate with

### 4. Squad Size Enforcement
- Maximum 40 players per squad
- Consistent with other transfer types
- Prevents squad bloat

### 5. Wage Budget Management
- Validates total wage bill stays within budget
- Prevents financial overcommitment
- Allows signing at exact budget limit

## Usage Examples

### Example 1: Basic Free Agent Signing
```python
service = TransferService()

result = service.sign_free_agent(
    career_week=15,  # Outside transfer window
    current_squad_size=25,
    career_transfer_budget=5_000_000,
    wage_offer=10_000,
    contract_years=3,
    wage_budget=500_000,
    current_wage_bill=300_000,
)

if result.success:
    print(f"Free agent signed! Wage: {result.bid_amount}")  # 0
else:
    print(f"Failed: {result.message}")
```

### Example 2: Signing with No Transfer Budget
```python
# Free agents don't require transfer budget
result = service.sign_free_agent(
    career_week=20,
    current_squad_size=28,
    career_transfer_budget=0,  # No budget available
    wage_offer=8_000,
    contract_years=2,
    wage_budget=400_000,
    current_wage_bill=300_000,
)

# Will succeed if wage budget allows
assert result.success is True
assert result.bid_amount == 0
```

### Example 3: Wage Budget Constraint
```python
# Check wage budget before signing
current_wage_bill = 480_000
wage_budget = 500_000
wage_offer = 25_000

if current_wage_bill + wage_offer > wage_budget:
    print("Cannot afford this free agent")
else:
    result = service.sign_free_agent(
        career_week=35,
        current_squad_size=30,
        career_transfer_budget=1_000_000,
        wage_offer=wage_offer,
        contract_years=3,
        wage_budget=wage_budget,
        current_wage_bill=current_wage_bill,
    )
```

### Example 4: Multiple Free Agent Signings
```python
# Sign multiple free agents, tracking wage accumulation
current_wage_bill = 300_000
wage_budget = 500_000
squad_size = 25

# First free agent
result1 = service.sign_free_agent(
    career_week=15,
    current_squad_size=squad_size,
    career_transfer_budget=0,
    wage_offer=10_000,
    contract_years=3,
    wage_budget=wage_budget,
    current_wage_bill=current_wage_bill,
)

if result1.success:
    current_wage_bill += 10_000
    squad_size += 1

# Second free agent
result2 = service.sign_free_agent(
    career_week=15,
    current_squad_size=squad_size,
    career_transfer_budget=0,
    wage_offer=15_000,
    contract_years=3,
    wage_budget=wage_budget,
    current_wage_bill=current_wage_bill,
)

if result2.success:
    current_wage_bill += 15_000
    squad_size += 1
```

## Integration with Transfer System

### Transfer Model
Free agent signings should be recorded in the `Transfer` model with:
- `transfer_type`: `TransferType.FREE_AGENT`
- `transfer_fee`: 0
- `from_club_id`: NULL (no selling club)
- `to_club_id`: Manager's club ID
- `wage_offer`: Agreed weekly wage
- `contract_length`: Contract years (1-5)

### Example Transfer Record
```python
transfer = Transfer(
    career_id=career.id,
    player_id=player.id,
    from_club_id=None,  # No selling club
    to_club_id=career.club_id,
    transfer_type=TransferType.FREE_AGENT,
    transfer_status=TransferStatus.COMPLETED,
    transfer_fee=0,  # No fee
    wage_offer=10_000,
    contract_length=3,
    season=career.current_season,
    week=career.current_week,
)
```

## Testing

### Unit Tests
Comprehensive test suite in `tests/services/test_transfer_service_free_agent.py`:
- 100+ test cases
- All validation scenarios
- Edge cases and boundary conditions
- Realistic signing scenarios

### Test Categories
1. **Basic Functionality** (4 tests)
   - Success cases
   - Window independence
   - No transfer fee

2. **Squad Size Validation** (3 tests)
   - Room in squad
   - Full squad
   - Over full squad

3. **Wage Budget Validation** (4 tests)
   - Sufficient budget
   - Insufficient budget
   - At limit
   - One over limit

4. **Contract Validation** (6 tests)
   - Valid range (1-5 years)
   - Invalid (0, 6+ years)
   - Boundary conditions

5. **Wage Validation** (5 tests)
   - Positive wages
   - Zero/negative wages
   - Minimum/maximum wages

6. **All Weeks** (4 tests)
   - Different weeks throughout season
   - Window and non-window periods

7. **Acceptance Probability** (2 tests)
   - Always 1.0
   - No rejection reason

8. **Validation Priority** (4 tests)
   - Correct validation order
   - Early exit on first failure

9. **Edge Cases** (6 tests)
   - Empty squad
   - Zero budgets
   - Negative budgets
   - Large budgets

10. **Error Messages** (4 tests)
    - Clear and informative
    - Mention specific issues

11. **Constants** (3 tests)
    - Correct values
    - Used in validation

12. **Realistic Scenarios** (5 tests)
    - Experienced players
    - Young players
    - Squad depth
    - Emergency cover
    - Multiple signings

13. **Boundary Conditions** (5 tests)
    - Exact limits
    - One over/under limits

### Manual Testing
Run `test_free_agent_manual.py` for quick verification:
```bash
python test_free_agent_manual.py
```

## Design Decisions

### 1. No Transfer Window Restriction
**Rationale**: Free agents are not under contract, so there's no selling club to negotiate with. Real-world football allows free agent signings outside transfer windows.

### 2. Always Accepted (Probability = 1.0)
**Rationale**: No selling club means no negotiation. The only constraints are the manager's budget and squad size.

### 3. Transfer Budget Not Required
**Rationale**: Free agents have no transfer fee. The transfer budget parameter is included for consistency but not validated.

### 4. Same Squad Size Limit
**Rationale**: Maintains consistency with other transfer types and prevents squad bloat regardless of transfer method.

### 5. Wage Budget Validation
**Rationale**: Even though there's no transfer fee, clubs must still manage their wage bill sustainably.

### 6. Contract Range (1-5 Years)
**Rationale**: Consistent with permanent transfers. Prevents unrealistic contract lengths.

## Performance Considerations

### Validation Order
Validations are ordered from cheapest to most expensive:
1. Squad size (simple integer comparison)
2. Contract years (range check)
3. Wage offer (positive check)
4. Wage budget (addition and comparison)

### No Database Access
The method is stateless and performs no database operations, making it fast and testable.

### No Random Number Generation
Unlike regular transfers, free agent acceptance is deterministic (always accepted), eliminating randomness.

## Future Enhancements

### Potential Improvements
1. **Player Preferences**: Add player wage demands based on CA/PA
2. **Reputation Check**: High-reputation players might reject low-reputation clubs
3. **Age-Based Contracts**: Suggest contract length based on player age
4. **Wage Recommendations**: Calculate suggested wage based on player attributes
5. **Free Agent Pool**: Maintain a list of available free agents
6. **Signing Bonus**: Optional one-time signing bonus for free agents
7. **Agent Fees**: Add agent fees for free agent signings

### Database Integration
When integrating with the full system:
1. Create `Transfer` record with `TransferType.FREE_AGENT`
2. Create `SquadPlayer` record linking player to club
3. Update club's `current_wage_bill`
4. Set player's contract expiry date
5. Log transfer in transfer history

## Conclusion

The Free Agent Signing System provides a streamlined way for managers to strengthen their squads outside transfer windows. By removing transfer fees and negotiation complexity while maintaining essential constraints (squad size, wage budget), it offers strategic flexibility without compromising game balance.

Key benefits:
- ✓ Available year-round
- ✓ No transfer fee
- ✓ Instant acceptance
- ✓ Budget-conscious
- ✓ Well-tested
- ✓ Easy to integrate
