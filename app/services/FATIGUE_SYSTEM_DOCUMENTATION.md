# Fatigue Simulation System Documentation

## Overview

The fatigue simulation system is a core component of the match simulator that models player stamina loss during matches and its impact on performance. This system ensures realistic match dynamics where players become tired over time, affecting their effectiveness on the pitch.

## Requirements Validation

This implementation satisfies **Requirement 3.6** from the requirements document:

> "THE Game_Engine SHALL simulate player fatigue: WHILE a player's stamina attribute is below 50% of maximum, THE Game_Engine SHALL reduce that player's effective CA by 10%"

## System Components

### 1. Stamina Loss Calculation

**Location**: `MatchSimulator._update_fatigue()` method

**Mechanism**:
- Stamina decreases every minute of match time
- Base stamina loss: 1.0 per minute
- Work rate factor: Higher work rate = faster stamina loss
- Formula: `stamina_loss = 1.0 * (0.8 + (work_rate / 20.0) * 0.4)`

**Work Rate Impact**:
- Work rate 5: Loss = 1.0 * (0.8 + 0.25 * 0.4) = 0.9 per minute
- Work rate 10: Loss = 1.0 * (0.8 + 0.5 * 0.4) = 1.0 per minute
- Work rate 15: Loss = 1.0 * (0.8 + 0.75 * 0.4) = 1.1 per minute
- Work rate 20: Loss = 1.0 * (0.8 + 1.0 * 0.4) = 1.2 per minute

**Stamina Range**:
- Initial: 100.0 (full stamina)
- Minimum: 0.0 (completely exhausted)
- Clamped using `max(0.0, stamina - stamina_loss)`

### 2. Effective CA Reduction

**Location**: `MatchSimulator._update_fatigue()` method

**Threshold**: Stamina < 50.0%

**Penalty**: 10% reduction in effective CA

**Calculation Order**:
1. Start with base CA from player attributes
2. Apply home advantage modifier (+5% if applicable)
3. Apply morale modifier (-5% if morale < 40)
4. Apply fatigue penalty (-10% if stamina < 50%)
5. Result = effective CA used in all match calculations

**Example**:
```python
# Player with CA=100, home team, good morale (70), stamina=40%
base_ca = 100
base_ca *= 1.05  # Home advantage: 105
# Morale >= 40, no penalty
base_ca *= 0.90  # Fatigue penalty: 94.5
effective_ca = 94.5
```

### 3. Fatigue Impact on Events

**Location**: `MatchSimulator.calculate_event_probability()` method

**Shot Probability**:
- When stamina < 50%: -3% shot probability
- Tired players are less likely to attempt shots

**Pass Probability**:
- When stamina < 50%: +2% pass probability
- Tired players prefer safer passing options

**Rationale**: Fatigued players play more conservatively, avoiding high-risk actions like shooting.

### 4. Fatigue Impact on Possession

**Location**: `MatchSimulator._calculate_possession()` method

**Mechanism**:
- Team average stamina affects possession probability
- Formula: `stamina_diff / 2000.0` (±5% swing for ±100 stamina difference)
- Tired teams lose possession more easily

**Example**:
```python
# Home team average stamina: 40%
# Away team average stamina: 80%
stamina_diff = 40 - 80 = -40
possession_modifier = -40 / 2000 = -0.02  # -2% possession probability for home team
```

## Implementation Details

### Stamina Update Flow

```
For each minute of match time:
  1. _simulate_minute() is called
  2. _update_fatigue() is called first
     a. Calculate stamina loss based on work rate
     b. Reduce stamina (clamped at 0)
     c. Recalculate effective CA with all modifiers
     d. Increment minutes_played counter
  3. _calculate_possession() uses updated stamina
  4. _generate_event() uses updated effective CA
```

### Key Data Structures

**PlayerState**:
```python
@dataclass
class PlayerState:
    stamina: float = 100.0          # Current stamina (0-100)
    effective_ca: float = 0.0       # Calculated CA with all modifiers
    minutes_played: int = 0         # Minutes played in match
```

**Player Attributes** (from Player model):
```python
class Player:
    ca: int                         # Base Current Ability (1-200)
    work_rate: int                  # Work rate attribute (1-20)
    stamina: int                    # Base stamina attribute (1-20, not used in simulation)
```

## Testing Coverage

### Test Suite: `test_fatigue_system.py`

**Test Classes**:

1. **TestFatigueStaminaLoss**
   - `test_stamina_decreases_over_time`: Verifies stamina decreases during match
   - `test_work_rate_affects_stamina_loss`: Confirms higher work rate = faster loss
   - `test_stamina_never_goes_negative`: Ensures stamina is clamped at 0

2. **TestFatigueCAReduction**
   - `test_ca_reduced_when_stamina_below_50`: Verifies 10% penalty when stamina < 50%
   - `test_no_ca_reduction_when_stamina_above_50`: Confirms no penalty when stamina >= 50%
   - `test_ca_reduction_with_home_advantage`: Tests penalty stacking with home advantage
   - `test_ca_reduction_with_low_morale`: Tests penalty stacking with morale penalty

3. **TestFatigueImpactOnEvents**
   - `test_tired_players_shoot_less`: Verifies reduced shot probability
   - `test_tired_players_pass_more`: Verifies increased pass probability

4. **TestFatigueFullMatch**
   - `test_fatigue_accumulates_over_90_minutes`: Integration test for full match
   - `test_some_players_reach_fatigue_threshold`: Confirms players reach < 50% stamina
   - `test_fatigue_affects_match_statistics`: Verifies impact on match outcome

5. **TestFatigueEdgeCases**
   - `test_stamina_exactly_50_percent`: Tests boundary condition at 50%
   - `test_stamina_at_zero`: Tests behavior at 0% stamina

**Test Results**: All 14 tests pass ✓

## Performance Characteristics

### Computational Cost

- **Per-minute overhead**: O(n) where n = number of active players (typically 22)
- **Operations per player**: 
  - 1 stamina calculation
  - 1 effective CA recalculation
  - 3-4 conditional checks
- **Total overhead**: ~0.001 seconds per minute (negligible)

### Match Simulation Impact

- Full 90-minute match: ~0.09 seconds for fatigue calculations
- Well within the < 2 second performance requirement
- No noticeable impact on overall simulation speed

## Realistic Behavior

### Expected Stamina Levels

**After 45 minutes** (half-time):
- Low work rate (5): ~60% stamina remaining
- Medium work rate (10): ~55% stamina remaining
- High work rate (15): ~50% stamina remaining
- Very high work rate (20): ~46% stamina remaining

**After 90 minutes** (full-time):
- Low work rate (5): ~20% stamina remaining
- Medium work rate (10): ~10% stamina remaining
- High work rate (15): ~1% stamina remaining
- Very high work rate (20): ~0% stamina remaining (exhausted)

### Match Impact

**Early game (0-30 minutes)**:
- All players at high stamina
- Full effective CA
- Normal event probabilities

**Mid game (30-60 minutes)**:
- Some high work rate players approaching 50% threshold
- Slight reduction in team performance
- Possession shifts toward fresher team

**Late game (60-90 minutes)**:
- Many players below 50% stamina
- Significant CA reductions (10% penalty)
- Tired teams lose possession more easily
- Fewer shots, more conservative play
- Fresh substitutes have significant advantage

## Integration with Other Systems

### Home Advantage
- Applied before fatigue penalty
- Both modifiers stack multiplicatively
- Example: 100 CA * 1.05 (home) * 0.90 (fatigue) = 94.5 effective CA

### Morale System
- Applied before fatigue penalty
- Both penalties stack multiplicatively
- Example: 100 CA * 0.95 (morale) * 0.90 (fatigue) = 85.5 effective CA

### Possession Calculation
- Team average stamina affects possession probability
- Tired teams lose possession more easily
- Creates realistic late-game dynamics

### Event Generation
- Effective CA used in all event probability calculations
- Tired players less likely to shoot
- Tired players more likely to pass

## Future Enhancements

### Potential Improvements

1. **Match Intensity Factor**
   - High-intensity matches (derbies, finals) increase stamina loss
   - Low-intensity matches (friendly, dead rubber) decrease stamina loss

2. **Pace Attribute Integration**
   - Players with high pace lose stamina faster
   - Reflects real-world sprinting fatigue

3. **Position-Based Fatigue**
   - Midfielders lose stamina faster (more running)
   - Goalkeepers lose stamina slower (less movement)

4. **Weather Impact**
   - Hot weather increases stamina loss
   - Cold weather decreases stamina loss

5. **Fitness Attribute**
   - Players with high fitness (stamina attribute) lose stamina slower
   - Currently not implemented (stamina attribute unused)

6. **Substitution Impact**
   - Fresh substitutes start with 100% stamina
   - Provides tactical advantage in late game

7. **Injury Risk**
   - Very low stamina (< 20%) increases injury probability
   - Reflects real-world fatigue-related injuries

## Maintenance Notes

### Code Locations

- **Core implementation**: `fm26/app/services/match_simulator.py`
  - `_update_fatigue()` method (lines 298-333)
  - `calculate_event_probability()` method (lines 636-640)
  - `_calculate_possession()` method (lines 390-395)

- **Tests**: `fm26/app/services/test_fatigue_system.py`
  - 14 comprehensive tests covering all aspects

- **Documentation**: `fm26/app/services/FATIGUE_SYSTEM_DOCUMENTATION.md`

### Modification Guidelines

**To adjust stamina loss rate**:
- Modify the formula in `_update_fatigue()` line 313
- Current: `stamina_loss = base_loss * (0.8 + work_rate_factor * 0.4)`
- Increase multiplier for faster fatigue
- Decrease multiplier for slower fatigue

**To adjust CA penalty threshold**:
- Modify the condition in `_update_fatigue()` line 328
- Current: `if player_state.stamina < 50.0:`
- Change 50.0 to desired threshold

**To adjust CA penalty amount**:
- Modify the multiplier in `_update_fatigue()` line 329
- Current: `base_ca *= 0.90` (10% reduction)
- Change 0.90 to desired penalty (e.g., 0.85 for 15% reduction)

### Testing After Modifications

Always run the full test suite after any modifications:

```bash
cd fm26
python -m pytest app/services/test_fatigue_system.py -v
```

Expected result: All 14 tests pass

## Conclusion

The fatigue simulation system is fully implemented, tested, and documented. It meets all requirements from the specification and provides realistic match dynamics. The system is performant, well-tested, and ready for production use.

**Status**: ✅ Complete and verified
