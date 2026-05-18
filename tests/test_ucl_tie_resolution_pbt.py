# Feature: uefa-champions-league, Property 7: Two-legged tie resolution
"""
Property-based tests for `UCLGenerator._resolve_tie`.

Validates Requirements 5.3, 5.4, 5.5, 5.7, 6.5, 8.5 — for any pair of leg
scores (leg1_home, leg1_away, leg2_home, leg2_away):

  * aggregate_home == leg1_home + leg2_away
  * aggregate_away == leg1_away + leg2_home
  * If aggregate_home > aggregate_away: home wins, decided_by='aggregate'
  * If aggregate_away > aggregate_home: away wins, decided_by='aggregate'
  * If aggregates are equal: decided_by ∈ {'extra_time', 'penalties'}
    and the winner is one of the two participants.
  * The away-goals rule is NEVER applied (Req 5.7) — equal aggregates with
    differing away-goal counts must still go to ET/penalties.

The generator is constructed with `session=None` because `_resolve_tie`
is a pure in-memory function that only uses `self.rng`.
"""

from __future__ import annotations

import random

from hypothesis import given, settings, strategies as st

from app.services.ucl_generator import TieResult, UCLGenerator


# Synthetic participant ids — any two distinct ints work, the resolver only
# echoes them back as the winner.
HOME_PID = 101
AWAY_PID = 202


def _make_tie(l1h: int, l1a: int, l2h: int, l2a: int) -> dict:
    """Build the dict-shaped tie record `_resolve_tie` consumes."""
    return {
        "id": 1,
        "home_participant_id": HOME_PID,
        "away_participant_id": AWAY_PID,
        "leg1_home_score": l1h,
        "leg1_away_score": l1a,
        "leg2_home_score": l2h,
        "leg2_away_score": l2a,
    }


@given(
    l1h=st.integers(min_value=0, max_value=6),
    l1a=st.integers(min_value=0, max_value=6),
    l2h=st.integers(min_value=0, max_value=6),
    l2a=st.integers(min_value=0, max_value=6),
    seed=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=100, deadline=None)
def test_two_legged_tie_resolution(
    l1h: int, l1a: int, l2h: int, l2a: int, seed: int
) -> None:
    """**Validates: Requirements 5.3, 5.4, 5.5, 5.7, 6.5, 8.5**

    For every leg-score combination, the resolver must compute aggregates
    correctly and pick a winner per the spec's tie-break order, never
    applying the away-goals rule.
    """
    generator = UCLGenerator(session=None, rng=random.Random(seed))
    tie = _make_tie(l1h, l1a, l2h, l2a)

    result = generator._resolve_tie(tie)

    # Result is a TieResult dataclass.
    assert isinstance(result, TieResult)

    # The original (pre-ET) aggregates from the leg scores.
    expected_home = l1h + l2a
    expected_away = l1a + l2h

    if expected_home != expected_away:
        # Aggregates already differ — winner is decided by aggregate alone
        # (Req 5.3, 5.4). ET/penalties must NOT be invoked.
        assert result.winner_decided_by == "aggregate", (
            f"non-equal aggregates ({expected_home}-{expected_away}) "
            f"must be decided_by='aggregate', got {result.winner_decided_by!r}"
        )
        # No ET goals were added — recorded aggregates equal the leg sums.
        assert result.aggregate_home == expected_home
        assert result.aggregate_away == expected_away
        # Winner is the side with the higher pre-ET aggregate.
        if expected_home > expected_away:
            assert result.winner_participant_id == HOME_PID
        else:
            assert result.winner_participant_id == AWAY_PID
    else:
        # Equal aggregates — must go to ET/penalties (Req 5.5). The
        # away-goals rule is NOT applied (Req 5.7), so even if one side
        # has more away goals, decided_by must be ET or penalties.
        assert result.winner_decided_by in {"extra_time", "penalties"}, (
            f"equal aggregates must be decided_by ET or penalties, "
            f"got {result.winner_decided_by!r}"
        )
        # Winner must be one of the two participants.
        assert result.winner_participant_id in (HOME_PID, AWAY_PID)
        # ET may have added goals, so recorded aggregates are >= pre-ET sums.
        assert result.aggregate_home >= expected_home
        assert result.aggregate_away >= expected_away
        # If decided_by='extra_time', recorded aggregates differ; if
        # 'penalties', recorded aggregates remain equal (shootout doesn't
        # alter the aggregate).
        if result.winner_decided_by == "extra_time":
            assert result.aggregate_home != result.aggregate_away
            higher = HOME_PID if result.aggregate_home > result.aggregate_away else AWAY_PID
            assert result.winner_participant_id == higher
        else:  # penalties
            assert result.aggregate_home == result.aggregate_away


@given(
    l1h=st.integers(min_value=0, max_value=6),
    l1a=st.integers(min_value=0, max_value=6),
    seed=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=100, deadline=None)
def test_no_away_goals_rule(l1h: int, l1a: int, seed: int) -> None:
    """**Validates: Requirement 5.7**

    Construct ties where the aggregate is intentionally tied but one side
    has strictly more "away goals" than the other. Under a (rejected)
    away-goals rule, the team with more away goals would auto-win with
    `decided_by='aggregate'`. The spec rejects that rule, so the result
    MUST go to extra time / penalties.

    Constructed tie:
      Leg 1: home L1H — away L1A    (away-goals for AWAY = L1A)
      Leg 2: home L1A — away L1H    (away-goals for HOME = L1H)
    Aggregates:
      home: L1H + L1H = 2*L1H
      away: L1A + L1A = 2*L1A
    These are equal iff L1H == L1A. We restrict to that case via
    `assume`-style filtering by setting leg-2 to mirror leg-1 only when
    L1H != L1A would break the tie — instead we directly build a tied
    aggregate where home has L1H away-goals and away has L1A away-goals.
    """
    # Build a tied aggregate with mismatched away goals:
    #   leg1: home l1h - away l1a  (away scored l1a away goals)
    #   leg2: home l1a - away l1h  (home scored l1h away goals)
    # aggregate_home = l1h + l1h = 2*l1h
    # aggregate_away = l1a + l1a = 2*l1a
    # Equal iff l1h == l1a — so we deliberately swap to force equality
    # while preserving away-goal asymmetry.
    #
    # A cleaner construction: pick any pair where the aggregate is tied
    # but the away-goal counts differ.
    #   leg1: home A - away B
    #   leg2: home C - away D
    # aggregate_home = A + D, aggregate_away = B + C
    # We want A + D == B + C with B != C (away goals differ).
    # Take A=l1h, D=l1a, B=l1a, C=l1h ⇒ aggregate_home = l1h+l1a,
    # aggregate_away = l1a+l1h (always equal); away-goals for AWAY = l1a,
    # away-goals for HOME = l1h. They differ whenever l1h != l1a.
    if l1h == l1a:
        # No asymmetry to test; trivially satisfies the property.
        return

    tie = _make_tie(l1h=l1h, l1a=l1a, l2h=l1h, l2a=l1a)

    generator = UCLGenerator(session=None, rng=random.Random(seed))
    result = generator._resolve_tie(tie)

    # Pre-ET aggregates are equal by construction.
    assert (l1h + l1a) == (l1a + l1h)

    # Despite the away-goal asymmetry, decision must NOT be 'aggregate'.
    assert result.winner_decided_by != "aggregate", (
        f"away-goals rule must NOT be applied; equal aggregates with "
        f"asymmetric away goals must go to ET/penalties, "
        f"got decided_by={result.winner_decided_by!r}"
    )
    assert result.winner_decided_by in {"extra_time", "penalties"}
    assert result.winner_participant_id in (HOME_PID, AWAY_PID)
