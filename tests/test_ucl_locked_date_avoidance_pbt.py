# Feature: uefa-champions-league, Property 11: Locked-date avoidance
"""
Property-based test for locked-date avoidance during UCL league phase
calendar event insertion.

Validates: Requirement 12.5

The property under test (design.md → Property 11):
  *For all* random years and any pre-existing locked or international
  calendar events for the player's club (events with ``priority >= 10``),
  no UCL calendar event involving the player's club SHALL be generated
  on a date that already has such a ``priority >= 10`` event for that
  career.

The reschedule fallback used by
``UCLGenerator._insert_league_phase_events`` (per task 5.2) attempts to
shift a player-involving fixture by ±1, ±2, ..., ±7 days while still
landing on a Tuesday or Wednesday. The implementation delegates the
slot search to ``UCLGenerator._find_available_slot``; this test is a
pure-helper test exercising that primitive directly, which is cleaner
than spinning up an in-memory SQLite database and exercises the exact
code path responsible for the locked-date avoidance.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Tuple

from hypothesis import given, settings, strategies as st

from app.data.ucl_config import UCL_LEAGUE_PHASE_TARGETS
from app.services.ucl_generator import UCLGenerator


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


def _resolve_target(year: int, month: int, week: int, weekday_num: int) -> date:
    """
    Resolve a ``UCL_LEAGUE_PHASE_TARGETS`` entry to a concrete date for a
    given season-start year. September-December targets land in ``year``;
    January targets land in ``year + 1``.
    """
    target_year = year if month >= 9 else year + 1
    return UCLGenerator._compute_target_date(target_year, month, week, weekday_num)


# ──────────────────────────────────────────────────────────────────────────
# Property 11 — single locked target date
# ──────────────────────────────────────────────────────────────────────────


@given(
    year=st.integers(min_value=2024, max_value=2030),
    target_idx=st.integers(min_value=0, max_value=7),
)
@settings(max_examples=10, deadline=None)
def test_property11_locked_target_date_is_avoided(
    year: int,
    target_idx: int,
) -> None:
    """
    Validates: Requirement 12.5

    For every season year in [2024, 2030] and every UCL league phase target
    slot (MD1-MD8), if the resolved target date is itself blocked (i.e.
    a ``priority >= 10`` calendar event already sits there for the
    player's club), ``_find_available_slot`` SHALL return:

      * a non-``None`` date;
      * a date different from the blocked target;
      * a date within ±7 days of the target;
      * a Tuesday (``weekday() == 1``) or Wednesday (``weekday() == 2``).
    """
    month, week, weekday_num = UCL_LEAGUE_PHASE_TARGETS[target_idx]
    target = _resolve_target(year, month, week, weekday_num)

    # Single-day block on the target itself — mirrors how
    # ``_insert_league_phase_events`` builds ``blocked_ranges`` from
    # ``player_locked`` (one ``(d, d)`` tuple per locked date).
    blocked: List[Tuple[date, date]] = [(target, target)]

    fallback = UCLGenerator._find_available_slot(target, blocked)

    assert fallback is not None, (
        f"No fallback slot found for target {target} with blocked={blocked}"
    )
    assert fallback != target, (
        f"Fallback {fallback} equals the blocked target {target}; "
        f"locked-date avoidance failed (Requirement 12.5)"
    )
    assert abs((fallback - target).days) <= 7, (
        f"Fallback {fallback} is outside ±7 days of target {target}"
    )
    assert fallback.weekday() in (1, 2), (
        f"Fallback {fallback} is not a Tuesday/Wednesday "
        f"(weekday={fallback.weekday()})"
    )


# ──────────────────────────────────────────────────────────────────────────
# Property 11 — multiple consecutive locked dates around the target
# ──────────────────────────────────────────────────────────────────────────


@given(
    year=st.integers(min_value=2024, max_value=2030),
    target_idx=st.integers(min_value=0, max_value=7),
    extra_blocks=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=10, deadline=None)
def test_property11_locked_target_with_adjacent_blocks_is_avoided(
    year: int,
    target_idx: int,
    extra_blocks: int,
) -> None:
    """
    Validates: Requirement 12.5

    Same property as the single-block case, with up to 3 additional
    blocked dates positioned at ±1 day around the target. The fallback
    SHALL still land on a Tuesday/Wednesday outside every blocked range
    and within ±7 days of the target — confirming the reschedule
    fallback handles multi-day locked-event clusters around a UCL
    matchday for the player's club.
    """
    month, week, weekday_num = UCL_LEAGUE_PHASE_TARGETS[target_idx]
    target = _resolve_target(year, month, week, weekday_num)

    # Always block the target; then add up to 3 adjacent days as
    # additional locked events for the player's club.
    blocked: List[Tuple[date, date]] = [(target, target)]
    offsets = [1, -1, 2, -2]
    for i in range(extra_blocks):
        d = target + timedelta(days=offsets[i])
        blocked.append((d, d))

    fallback = UCLGenerator._find_available_slot(target, blocked)

    assert fallback is not None, (
        f"No fallback slot found for target {target} with blocked={blocked}"
    )
    # Fallback must not be inside any blocked range.
    for start, end in blocked:
        assert not (start <= fallback <= end), (
            f"Fallback {fallback} falls inside blocked range [{start}, {end}]; "
            f"locked-date avoidance failed (Requirement 12.5)"
        )
    assert abs((fallback - target).days) <= 7, (
        f"Fallback {fallback} is outside ±7 days of target {target}"
    )
    assert fallback.weekday() in (1, 2), (
        f"Fallback {fallback} is not a Tuesday/Wednesday "
        f"(weekday={fallback.weekday()})"
    )
