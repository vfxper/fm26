# Task 8.12: Transfer Budget Management - Usage Examples

## Overview

This document provides practical examples of using the transfer budget management functionality implemented in Task 8.12.

## Core Methods

### 1. `get_budget_status()` - Get Current Budget Status

Returns comprehensive information about the club's transfer and wage budgets.

#### Basic Usage

```python
from app.services.transfer_service import TransferService

service = TransferService()

# Get current budget status
status = service.get_budget_status(
    transfer_budget=5_000_000,      # £5M transfer budget
    wage_budget=500_000,             # £500K weekly wage budget
    current_wage_bill=300_000,       # £300K current weekly wages
)

# Access budget information
print(f"Transfer Budget: £{status.transfer_budget:,}")
print(f"Wage Budget: £{status.wage_budget:,}")
print(f"Current Wage Bill: £{status.current_wage_bill:,}")
print(f"Available Transfer Funds: £{status.available_transfer_funds:,}")
print(f"Available Wage Room: £{status.available_wage_room:,}")
print(f"Can Make Transfers: {status.can_make_transfers}")
print(f"Status Message: {status.message}")
```

**Output:**
```
Transfer Budget: £5,000,000
Wage Budget: £500,000
Current Wage Bill: £300,000
Available Transfer Funds: £5,000,000
Available Wage Room: £200,000
Can Make Transfers: True
Status Message: Budget available: 5000000 transfer, 200000 wage room.
```

#### Scenario: No Transfer Budget

```python
status = service.get_budget_status(
    transfer_budget=0,               # No transfer budget
    wage_budget=500_000,
    current_wage_bill=300_000,
)

print(f"Can Make Transfers: {status.can_make_transfers}")  # False
print(f"Message: {status.message}")  # "No transfer funds available."
```

#### Scenario: No Wage Room

```python
status = service.get_budget_status(
    transfer_budget=5_000_000,
    wage_budget=500_000,
    current_wage_bill=500_000,       # Wage budget fully used
)

print(f"Available Wage Room: £{status.available_wage_room:,}")  # £0
print(f"Can Make Transfers: {status.can_make_transfers}")  # False
print(f"Message: {status.message}")  # "No wage budget room available."
```

### 2. `can_afford_transfer()` - Check Transfer Affordability

Validates if a club can afford a specific transfer (both fee and wage).

#### Basic Usage

```python
from app.services.transfer_service import TransferService

service = TransferService()

# Check if club can afford a transfer
can_afford = service.can_afford_transfer(
    transfer_budget=5_000_000,       # £5M available
    wage_budget=500_000,             # £500K weekly wage budget
    current_wage_bill=300_000,       # £300K current wages
    fee=1_000_000,                   # £1M transfer fee
    wage=50_000,                     # £50K weekly wage
)

if can_afford:
    print("✓ Club can afford this transfer")
else:
    print("✗ Club cannot afford this transfer")
```

#### Scenario: Cannot Afford Fee

```python
can_afford = service.can_afford_transfer(
    transfer_budget=500_000,         # Only £500K available
    wage_budget=500_000,
    current_wage_bill=300_000,
    fee=1_000_000,                   # Trying to spend £1M
    wage=50_000,
)

print(can_afford)  # False - insufficient transfer budget
```

#### Scenario: Cannot Afford Wage

```python
can_afford = service.can_afford_transfer(
    transfer_budget=5_000_000,
    wage_budget=500_000,
    current_wage_bill=480_000,       # Already at £480K wages
    fee=1_000_000,
    wage=50_000,                     # Would exceed £500K budget
)

print(can_afford)  # False - insufficient wage budget
```

#### Scenario: Exactly at Budget Limits

```python
can_afford = service.can_afford_transfer(
    transfer_budget=1_000_000,
    wage_budget=500_000,
    current_wage_bill=450_000,
    fee=1_000_000,                   # Exactly at transfer budget
    wage=50_000,                     # Exactly at wage budget
)

print(can_afford)  # True - exactly affordable
```

## Integration Examples

### Example 1: Pre-Transfer Validation

```python
from app.services.transfer_service import TransferService

async def validate_transfer_before_bid(
    career_id: int,
    player_id: int,
    bid_amount: int,
    wage_offer: int,
):
    """Validate budget before submitting a transfer bid"""
    
    service = TransferService()
    
    # Get career and club data (pseudo-code)
    career = await get_career(career_id)
    club = await get_club(career.club_id)
    
    # Get current budget status
    status = service.get_budget_status(
        transfer_budget=club.transfer_budget,
        wage_budget=club.wage_budget,
        current_wage_bill=club.current_wage_bill,
    )
    
    # Check if transfers are possible at all
    if not status.can_make_transfers:
        return {
            "can_proceed": False,
            "reason": status.message,
        }
    
    # Check if this specific transfer is affordable
    can_afford = service.can_afford_transfer(
        transfer_budget=club.transfer_budget,
        wage_budget=club.wage_budget,
        current_wage_bill=club.current_wage_bill,
        fee=bid_amount,
        wage=wage_offer,
    )
    
    if not can_afford:
        return {
            "can_proceed": False,
            "reason": "Cannot afford this transfer (fee or wage too high)",
        }
    
    return {
        "can_proceed": True,
        "available_funds": status.available_transfer_funds,
        "available_wage_room": status.available_wage_room,
    }
```

### Example 2: Display Budget to User

```python
from app.services.transfer_service import TransferService

def display_transfer_budget_ui(club):
    """Display budget information in the UI"""
    
    service = TransferService()
    
    status = service.get_budget_status(
        transfer_budget=club.transfer_budget,
        wage_budget=club.wage_budget,
        current_wage_bill=club.current_wage_bill,
    )
    
    # Format for display
    ui_data = {
        "transfer_budget": {
            "total": f"£{status.transfer_budget:,}",
            "available": f"£{status.available_transfer_funds:,}",
        },
        "wage_budget": {
            "total": f"£{status.wage_budget:,}",
            "current": f"£{status.current_wage_bill:,}",
            "available": f"£{status.available_wage_room:,}",
            "percentage_used": f"{(status.current_wage_bill / status.wage_budget * 100):.1f}%",
        },
        "can_make_transfers": status.can_make_transfers,
        "status_message": status.message,
    }
    
    return ui_data
```

### Example 3: Transfer Market Filter

```python
from app.services.transfer_service import TransferService

def filter_affordable_players(club, available_players):
    """Filter players that the club can afford"""
    
    service = TransferService()
    
    affordable_players = []
    
    for player in available_players:
        can_afford = service.can_afford_transfer(
            transfer_budget=club.transfer_budget,
            wage_budget=club.wage_budget,
            current_wage_bill=club.current_wage_bill,
            fee=player.market_value,
            wage=player.wage,
        )
        
        if can_afford:
            affordable_players.append({
                "player": player,
                "affordable": True,
            })
        else:
            affordable_players.append({
                "player": player,
                "affordable": False,
                "reason": "Exceeds budget",
            })
    
    return affordable_players
```

### Example 4: Budget Warning System

```python
from app.services.transfer_service import TransferService

def check_budget_warnings(club):
    """Check for budget warnings and alerts"""
    
    service = TransferService()
    
    status = service.get_budget_status(
        transfer_budget=club.transfer_budget,
        wage_budget=club.wage_budget,
        current_wage_bill=club.current_wage_bill,
    )
    
    warnings = []
    
    # Check transfer budget
    if status.transfer_budget == 0:
        warnings.append({
            "type": "critical",
            "category": "transfer_budget",
            "message": "No transfer budget available",
        })
    elif status.transfer_budget < 1_000_000:
        warnings.append({
            "type": "warning",
            "category": "transfer_budget",
            "message": f"Low transfer budget: £{status.transfer_budget:,}",
        })
    
    # Check wage budget
    wage_usage_ratio = status.current_wage_bill / status.wage_budget
    if wage_usage_ratio >= 0.90:
        warnings.append({
            "type": "critical",
            "category": "wage_budget",
            "message": f"Wage budget at {wage_usage_ratio:.0%} capacity",
        })
    elif wage_usage_ratio >= 0.75:
        warnings.append({
            "type": "warning",
            "category": "wage_budget",
            "message": f"Wage budget at {wage_usage_ratio:.0%} capacity",
        })
    
    return warnings
```

### Example 5: Multi-Transfer Planning

```python
from app.services.transfer_service import TransferService

def plan_multiple_transfers(club, target_players):
    """Plan multiple transfers and check if all are affordable"""
    
    service = TransferService()
    
    total_fees = sum(p.market_value for p in target_players)
    total_wages = sum(p.wage for p in target_players)
    
    # Check if all transfers combined are affordable
    can_afford_all = service.can_afford_transfer(
        transfer_budget=club.transfer_budget,
        wage_budget=club.wage_budget,
        current_wage_bill=club.current_wage_bill,
        fee=total_fees,
        wage=total_wages,
    )
    
    if can_afford_all:
        return {
            "feasible": True,
            "total_cost": total_fees,
            "total_wages": total_wages,
            "remaining_budget": club.transfer_budget - total_fees,
            "remaining_wage_room": club.wage_budget - club.current_wage_bill - total_wages,
        }
    else:
        # Find which transfers are affordable
        affordable = []
        running_fee = 0
        running_wage = club.current_wage_bill
        
        for player in sorted(target_players, key=lambda p: p.market_value):
            if service.can_afford_transfer(
                transfer_budget=club.transfer_budget - running_fee,
                wage_budget=club.wage_budget,
                current_wage_bill=running_wage,
                fee=player.market_value,
                wage=player.wage,
            ):
                affordable.append(player)
                running_fee += player.market_value
                running_wage += player.wage
        
        return {
            "feasible": False,
            "affordable_count": len(affordable),
            "affordable_players": affordable,
            "total_cost": running_fee,
            "total_wages": running_wage - club.current_wage_bill,
        }
```

## Testing Examples

### Unit Test Example

```python
import pytest
from app.services.transfer_service import TransferService

def test_budget_status_normal_case():
    """Test budget status with normal values"""
    service = TransferService()
    
    result = service.get_budget_status(
        transfer_budget=5_000_000,
        wage_budget=500_000,
        current_wage_bill=300_000,
    )
    
    assert result.transfer_budget == 5_000_000
    assert result.wage_budget == 500_000
    assert result.current_wage_bill == 300_000
    assert result.available_transfer_funds == 5_000_000
    assert result.available_wage_room == 200_000
    assert result.can_make_transfers is True
    assert "available" in result.message.lower()

def test_cannot_afford_transfer():
    """Test cannot afford transfer due to insufficient budget"""
    service = TransferService()
    
    result = service.can_afford_transfer(
        transfer_budget=500_000,
        wage_budget=500_000,
        current_wage_bill=300_000,
        fee=1_000_000,
        wage=50_000,
    )
    
    assert result is False
```

## Common Patterns

### Pattern 1: Check Before Action

Always check budget status before attempting a transfer:

```python
# ✓ GOOD
status = service.get_budget_status(...)
if status.can_make_transfers:
    can_afford = service.can_afford_transfer(...)
    if can_afford:
        # Proceed with transfer
        pass

# ✗ BAD
# Attempting transfer without checking budget
```

### Pattern 2: Provide Clear Feedback

Use the status message to inform users:

```python
status = service.get_budget_status(...)
if not status.can_make_transfers:
    # Show user the specific reason
    show_error_message(status.message)
```

### Pattern 3: Validate Both Fee and Wage

Always validate both components:

```python
# ✓ GOOD
can_afford = service.can_afford_transfer(
    transfer_budget=...,
    wage_budget=...,
    current_wage_bill=...,
    fee=...,
    wage=...,
)

# ✗ BAD
# Only checking transfer fee
if fee <= transfer_budget:
    # Missing wage validation!
```

## Error Handling

### Handle Edge Cases

```python
def safe_budget_check(club, fee, wage):
    """Safely check budget with error handling"""
    try:
        service = TransferService()
        
        # Validate inputs
        if fee < 0 or wage < 0:
            return {
                "success": False,
                "error": "Invalid fee or wage (negative values)",
            }
        
        # Check affordability
        can_afford = service.can_afford_transfer(
            transfer_budget=club.transfer_budget,
            wage_budget=club.wage_budget,
            current_wage_bill=club.current_wage_bill,
            fee=fee,
            wage=wage,
        )
        
        return {
            "success": True,
            "can_afford": can_afford,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Budget check failed: {str(e)}",
        }
```

## Performance Considerations

The budget management methods are lightweight and perform no database operations:

- **`get_budget_status()`**: O(1) - Simple calculations
- **`can_afford_transfer()`**: O(1) - Two comparisons

These methods can be called frequently without performance concerns.

## Related Documentation

- **Task 8.11**: Wage calculation and impact analysis
- **Task 8.2**: Transfer bid submission
- **Task 8.4**: Transfer fee deduction
- **Task 8.9**: Free agent signing

## Summary

The transfer budget management system provides:

✅ **Clear budget status** - Know exactly what's available
✅ **Affordability validation** - Check before committing
✅ **Comprehensive information** - All financial details in one place
✅ **Simple API** - Easy to use and integrate
✅ **No side effects** - Pure validation functions
✅ **Well-tested** - Comprehensive test coverage

Use these methods to ensure financial responsibility in all transfer operations!
