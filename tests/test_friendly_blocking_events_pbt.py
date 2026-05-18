# Feature: friendly-matches, Property 9: Conflicting blocking events cause rejection
"""
Property-based test for ``FriendlyMatchService._check_conflicts``.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

The implementation iterates over the list of existing non-cancelled events and
applies five blocking rules. Each rule is evaluated against ALL events before
moving to the next rule, so the order is rule-major / event-minor:

  Rule 1: same-day match with ``priority >= 4``
          → ``"На эту дату уже запланирован официальный матч"``
  Rule 2: same-day event with ``is_locked = True`` (any type)
          → ``"Дата заблокирована (международный перерыв или мандатный матч)"``
  Rule 3: same-day event with ``event_type = "international"``
          → ``"Дата попадает на международный перерыв"``
  Rule 4: any ``event_type = "match"`` event on a *different* day within
          ±1 day of the target date (i.e. ``|delta| < 2`` AND
          ``delta != 0``)
          → ``"Между матчами должно быть не менее 48 часов"``
  Rule 5: same-day match with ``priority == 2`` (existing friendly)
          → ``"На эту дату уже запланирован товарищеский матч"``

The first matching rule wins; ``ValidationError`` carries ``http_status=422``.
When no rule fires, the helper returns the warnings list (empty in practice
because the only soft-warning branch — international event on the same date
— is preempted by Rule 3 and is therefore unreachable from this helper).

The helper is purely synchronous and does not touch ``self.session``;
constructing the service with ``session=None`` is sufficient.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pytest
from hypothesis import given, settings, strategies as st

from app.services.friendly_match_service import (
    FriendlyMatchService,
    ValidationError,
)


# ──────────────────────────────────────────────────────────────────────────
# Constants and oracle messages.
# ──────────────────────────────────────────────────────────────────────────

ANCHOR_DATE = date(2025, 7, 22)  # arbitrary; ``_check_conflicts`` is date-agnostic.

MSG_OFFICIAL = "На эту дату уже запланирован официальный матч"
MSG_LOCKED = "Дата заблокирована (международный перерыв или мандатный матч)"
MSG_INTERNATIONAL = "Дата попадает на международный перерыв"
MSG_48H = "Между матчами должно быть не менее 48 часов"
MSG_FRIENDLY = "На эту дату уже запланирован товарищеский матч"

# The service's ``__init__`` only stores the session; ``_check_conflicts``
# never reads it, so passing ``None`` is safe for property testing.
_SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────
# Hypothesis strategies.
# ──────────────────────────────────────────────────────────────────────────

# Wide enough to cover all five rules:
#   - ``event_date`` offsets in [-3, 3] cover "same day" (0), "within 48h"
#     (±1), and "outside 48h" (±2, ±3).
#   - ``event_type`` covers all categories Rules 1-5 inspect, plus an
#     unrelated type ("training") that should never trigger any rule.
#   - ``priority`` ranges from 1 (low) to 10 (high) to span Rules 1, 4, 5.
#   - ``is_locked`` flips Rule 2.

EVENT_TYPES = st.sampled_from(["match", "international", "training", "media"])


@st.composite
def _existing_event(draw) -> dict:
    """Generate a single non-cancelled existing calendar event.

    The shape matches what ``_existing_events_around`` returns: ``id``,
    ``event_date``, ``event_type``, ``priority``, ``is_locked``.
    """
    offset = draw(st.integers(min_value=-3, max_value=3))
    return {
        "id": draw(st.integers(min_value=1, max_value=10_000)),
        "event_date": ANCHOR_DATE + timedelta(days=offset),
        "event_type": draw(EVENT_TYPES),
        "priority": draw(st.integers(min_value=1, max_value=10)),
        "is_locked": draw(st.booleans()),
    }


# ──────────────────────────────────────────────────────────────────────────
# Oracle: re-implement the rule order to compute the expected outcome.
# ──────────────────────────────────────────────────────────────────────────


def _expected_message(events: list[dict], target: date) -> Optional[str]:
    """Re-implement ``_check_conflicts`` rule-order semantics.

    Returns the expected ``ValidationError.message`` for the supplied
    list of existing events, or ``None`` when no rule fires (in which
    case the helper returns a warnings list rather than raising).
    """
    # Rule 1 — same-day high-priority official match (priority >= 4).
    for ev in events:
        if (
            ev["event_date"] == target
            and ev["event_type"] == "match"
            and ev["priority"] >= 4
        ):
            return MSG_OFFICIAL

    # Rule 2 — same-day locked event of any kind.
    for ev in events:
        if ev["event_date"] == target and ev["is_locked"]:
            return MSG_LOCKED

    # Rule 3 — same-day international event.
    for ev in events:
        if ev["event_date"] == target and ev["event_type"] == "international":
            return MSG_INTERNATIONAL

    # Rule 4 — match within 48 hours but not on the same day.
    for ev in events:
        if (
            ev["event_type"] == "match"
            and abs((ev["event_date"] - target).days) < 2
            and ev["event_date"] != target
        ):
            return MSG_48H

    # Rule 5 — same-day non-cancelled friendly (priority == 2).
    for ev in events:
        if (
            ev["event_date"] == target
            and ev["event_type"] == "match"
            and ev["priority"] == 2
        ):
            return MSG_FRIENDLY

    return None


# ──────────────────────────────────────────────────────────────────────────
# Property 9 — Conflicting blocking events cause rejection.
# ──────────────────────────────────────────────────────────────────────────


@given(events=st.lists(_existing_event(), min_size=0, max_size=6))
@settings(max_examples=100, deadline=None)
def test_check_conflicts_applies_blocking_rules_in_order(
    events: list[dict],
) -> None:
    """**Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

    For any list of existing non-cancelled events, ``_check_conflicts`` either
    raises ``ValidationError(http_status=422)`` with the message of the first
    matching blocking rule, or — when no rule applies — returns a list of
    soft warnings (which is empty in practice because Rule 3 preempts the
    only soft-warning branch).
    """
    expected = _expected_message(events, ANCHOR_DATE)

    if expected is None:
        # No blocking rule fires → no exception, returns a list.
        warnings = _SERVICE._check_conflicts(ANCHOR_DATE, events)
        assert isinstance(warnings, list), (
            f"_check_conflicts must return a list; got {type(warnings).__name__}"
        )
    else:
        with pytest.raises(ValidationError) as excinfo:
            _SERVICE._check_conflicts(ANCHOR_DATE, events)
        assert excinfo.value.http_status == 422, (
            f"expected http_status=422, got {excinfo.value.http_status}"
        )
        assert excinfo.value.message == expected, (
            f"\n  events:   {events!r}"
            f"\n  expected: {expected!r}"
            f"\n  got:      {excinfo.value.message!r}"
        )


# ──────────────────────────────────────────────────────────────────────────
# Targeted property tests — one per blocking rule. Each test plants exactly
# one matching event into ``existing`` to assert the rule fires in isolation
# (and to make the rule traceability obvious in test output).
# ──────────────────────────────────────────────────────────────────────────


@given(priority=st.integers(min_value=4, max_value=10))
@settings(max_examples=100, deadline=None)
def test_rule1_same_day_official_match_blocks(priority: int) -> None:
    """Rule 1 — Requirement 5.2: same-day match with priority>=4 raises."""
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE,
        "event_type": "match",
        "priority": priority,
        "is_locked": False,
    }
    with pytest.raises(ValidationError) as excinfo:
        _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert excinfo.value.http_status == 422
    assert excinfo.value.message == MSG_OFFICIAL


@given(
    event_type=st.sampled_from(["match", "training", "media"]),
    priority=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100, deadline=None)
def test_rule2_same_day_locked_event_blocks(event_type: str, priority: int) -> None:
    """Rule 2 — Requirement 5.3: any same-day locked event raises.

    ``event_type`` and ``priority`` are deliberately chosen so Rule 1 does
    NOT fire (no priority>=4 match) and ``event_type != "international"``
    so Rule 3 does NOT fire — only Rule 2 should trigger.
    """
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE,
        "event_type": event_type,
        "priority": priority,
        "is_locked": True,
    }
    with pytest.raises(ValidationError) as excinfo:
        _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert excinfo.value.http_status == 422
    assert excinfo.value.message == MSG_LOCKED


@given(priority=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, deadline=None)
def test_rule3_same_day_international_event_blocks(priority: int) -> None:
    """Rule 3 — Requirement 5.4: same-day international event raises."""
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE,
        "event_type": "international",
        "priority": priority,
        "is_locked": False,
    }
    with pytest.raises(ValidationError) as excinfo:
        _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert excinfo.value.http_status == 422
    assert excinfo.value.message == MSG_INTERNATIONAL


@given(
    offset=st.sampled_from([-1, 1]),
    priority=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100, deadline=None)
def test_rule4_match_within_48h_blocks(offset: int, priority: int) -> None:
    """Rule 4 — Requirement 5.5: a match within ±1 day raises.

    ``priority`` is kept below 4 so Rule 1 does NOT fire on the same-day
    branch (this rule fires regardless of priority for non-same-day matches).
    """
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE + timedelta(days=offset),
        "event_type": "match",
        "priority": priority,
        "is_locked": False,
    }
    with pytest.raises(ValidationError) as excinfo:
        _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert excinfo.value.http_status == 422
    assert excinfo.value.message == MSG_48H


@given(unused=st.integers(min_value=0, max_value=0))
@settings(max_examples=10, deadline=None)
def test_rule5_same_day_friendly_blocks(unused: int) -> None:
    """Rule 5 — Requirement 5.6: same-day non-cancelled friendly raises."""
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE,
        "event_type": "match",
        "priority": 2,
        "is_locked": False,
    }
    with pytest.raises(ValidationError) as excinfo:
        _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert excinfo.value.http_status == 422
    assert excinfo.value.message == MSG_FRIENDLY


@given(
    offset=st.integers(min_value=2, max_value=10).flatmap(
        lambda n: st.sampled_from([n, -n])
    ),
    event_type=st.sampled_from(["training", "media"]),
)
@settings(max_examples=100, deadline=None)
def test_no_blocking_event_returns_warnings_list(
    offset: int, event_type: str
) -> None:
    """No rule fires → returns a list (empty in practice).

    Constructed event is far enough away (|offset| >= 2) and not a match,
    international, or locked event, so all five rules miss.
    """
    event = {
        "id": 1,
        "event_date": ANCHOR_DATE + timedelta(days=offset),
        "event_type": event_type,
        "priority": 1,
        "is_locked": False,
    }
    result = _SERVICE._check_conflicts(ANCHOR_DATE, [event])
    assert isinstance(result, list), (
        f"expected list, got {type(result).__name__}"
    )
