# Home Advantage Implementation

## Overview

This document describes the implementation of home advantage in the match simulation engine. Home advantage gives the home team a **+5% boost to Current Ability (CA)** for all players during match simulation.

## Implementation Details

### 1. Initial Application (Match Initialization)

When a match is initialized, home team players receive a +5% CA boost:

```python
# In _initialize_match() method
if home_advantage:
    player_state.effective_ca = player.ca * 1.05
else:
    player_state.effective_ca = float(player.ca)
```

**Location**: `match_simulator.py`, lines 237-239

### 2. Persistent Application (Fatigue Updates)

The home advantage boost is reapplied during fatigue updates to ensure it persists throughout the match:

```python
# In _update_fatigue() method
base_ca = player_state.player.ca

# Apply home advantage
if team.team_side == TeamSide.HOME and self.home_advantage_applied:
    base_ca *= 1.05
```

**Location**: `match_simulator.py`, lines 318-322

### 3. Modifier Stacking

Home advantage is correctly combined with other modifiers:

#### Morale Penalty (< 40 morale)
```python
# Expected CA: base_ca * 1.05 (home) * 0.95 (morale)
if morale < 40:
    base_ca *= 0.95
```

#### Fatigue Penalty (< 50% stamina)
```python
# Expected CA: base_ca * 1.05 (home) * 0.90 (fatigue)
if player_state.stamina < 50.0:
    base_ca *= 0.90
```

#### All Modifiers Combined
```python
# Expected CA: base_ca * 1.05 (home) * 0.95 (morale) * 0.90 (fatigue)
# = base_ca * 0.89775
```

### 4. Impact on Match Simulation

The home advantage boost affects:

1. **Possession Calculation**: Home team's average CA is higher, increasing possession probability
2. **Event Probabilities**: Higher effective CA improves success rates for passes, shots, tackles
3. **Event Resolution**: Better attributes lead to more successful actions
4. **Match Outcomes**: Over multiple simulations, home teams win more often with identical squads

## Configuration

Home advantage can be enabled or disabled per match:

```python
result = simulator.simulate_match(
    home_club_id=1,
    home_club_name="Home FC",
    home_players=home_squad,
    away_club_id=2,
    away_club_name="Away FC",
    away_players=away_squad,
    home_advantage=True  # Set to False to disable
)
```

## Testing

Comprehensive tests verify:

1. ✅ Initial application of +5% boost
2. ✅ Ability to disable home advantage
3. ✅ Correct combination with fatigue penalty
4. ✅ Correct combination with morale penalty
5. ✅ Correct combination with all modifiers
6. ✅ Impact on possession calculation
7. ✅ Impact on match outcomes
8. ✅ Persistence throughout match
9. ✅ Reflection in team average CA

**Test File**: `app/services/test_home_advantage.py`

## Requirements Validation

This implementation satisfies **Requirement 3.11** from the requirements document:

> THE Game_Engine SHALL calculate home advantage by applying a 5% boost to the home team's effective CA in all match calculations.

### Acceptance Criteria Met:
- ✅ +5% CA boost applied to home team players
- ✅ Boost applied during match initialization
- ✅ Boost persists throughout match simulation
- ✅ Boost affects possession calculations
- ✅ Boost affects event probabilities
- ✅ Boost affects event resolution
- ✅ Boost correctly combines with other modifiers (fatigue, morale)
- ✅ Home advantage can be enabled/disabled per match

## Performance Impact

The home advantage calculation has **negligible performance impact**:
- Simple multiplication operation (1.05x)
- Applied once during initialization
- Reapplied during fatigue updates (once per minute per player)
- No additional database queries or complex calculations

## Future Enhancements

Potential improvements for future versions:

1. **Variable Home Advantage**: Different boost percentages based on:
   - Stadium capacity and atmosphere
   - Club reputation
   - Recent home form
   - Weather conditions

2. **Crowd Pressure**: Negative effects on away team:
   - Increased pressure on away players
   - Higher chance of mistakes
   - Referee bias simulation

3. **Neutral Venue**: Special handling for cup finals and neutral ground matches

## Related Files

- **Implementation**: `app/services/match_simulator.py`
- **Tests**: `app/services/test_home_advantage.py`
- **Models**: `app/models/match.py` (home_advantage_applied field)
- **Requirements**: `fm26/.kiro/specs/telegram-football-manager/requirements.md` (Requirement 3.11)
- **Design**: `fm26/.kiro/specs/telegram-football-manager/design.md`

## Changelog

### 2025-01-XX - Task 4.7 Completion
- ✅ Verified home advantage implementation
- ✅ Created comprehensive test suite (9 tests)
- ✅ Documented implementation details
- ✅ Validated against requirements
