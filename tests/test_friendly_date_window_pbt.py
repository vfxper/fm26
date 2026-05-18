# Feature: friendly-matches, Property 8: Date-window classification is exhaustive and consistent
"""
Property-based test for ``FriendlyMatchService._check_window``.

**Validates: Requirements 5.1, 5.7, 5.8, 12.1, 12.4**

The window helper splits any candidate ``event_date`` into three classes
relative to the season window ``[season_start, season_end]`` and the
pre-season window ``[Jul 15, Aug 10]`` of ``season_start.year``:

  1. **Outside the season** → raise
     ``ValidationError("Дата вне игрового сезона", http_status=422)``.
  2. **Inside the season AND inside the pre-season window** →
     return an empty warnings list.
  3. **Inside the season AND outside the pre-season window** →
     return a warnings list containing ``"Дата вне предсезонного окна"``.

These three classes are exhaustive and disjoint; the test exercises all
three branches with Hypothesis-generated dates.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import assume, given, settings, strategies as st

from app.services.friendly_match_service import (
    FriendlyMatchService,
    PRESEASON_END_MMDD,
    PRESEASON_START_MMDD,
    ValidationError,
)


# ──────────────────────────────────────────────────────────────────────────
# ``_check_window`` is a pure helper that does not touch the DB session, so
# passing ``None`` as the session is fine.
# ──────────────────────────────────────────────────────────────────────────
SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# Date strategy bounded to a reasonable range so that ``date(year, 7, 15)``
# and ``date(year, 8, 10)`` are always constructible.
_DATE = st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))


# ──────────────────────────────────────────────────────────────────────────
# Branch 1: ``event_date`` outside ``[season_start, season_end]`` → raise.
# ──────────────────────────────────────────────────────────────────────────
@given(event_date=_DATE, season_start=_DATE, season_end=_DATE)
@settings(max_examples=100, deadline=None)
def test_event_outside_season_raises(
    event_date: date,
    season_start: date,
    season_end: date,
) -> None:
    """**Validates: Requirements 5.1, 12.1, 12.4**

    Any ``event_date`` strictly before ``season_start`` or strictly after
    ``season_end`` SHALL be rejected with ``ValidationError`` carrying
    ``http_status == 422`` and the canonical Russian message.
    """
    assume(season_start <= season_end)
    assume(event_date < season_start or event_date > season_end)

    with pytest.raises(ValidationError) as excinfo:
        SERVICE._check_window(event_date, season_start, season_end)

    assert excinfo.value.http_status == 422
    assert excinfo.value.message == "Дата вне игрового сезона"


# ──────────────────────────────────────────────────────────────────────────
# Branch 2: ``event_date`` inside the season AND inside the pre-season
# window of ``season_start.year`` → no warnings.
#
# Generation strategy: pick a season year and an offset within
# [Jul 15, Aug 10] (≤ 26 days). Build a season window that always contains
# both the pre-season window and the chosen event_date.
# ──────────────────────────────────────────────────────────────────────────
@given(
    year=st.integers(min_value=2000, max_value=2100),
    preseason_offset_days=st.integers(min_value=0, max_value=26),
    pad_before_days=st.integers(min_value=0, max_value=180),
    pad_after_days=st.integers(min_value=0, max_value=180),
)
@settings(max_examples=100, deadline=None)
def test_event_in_preseason_window_has_no_warnings(
    year: int,
    preseason_offset_days: int,
    pad_before_days: int,
    pad_after_days: int,
) -> None:
    """**Validates: Requirements 5.7, 12.1**

    When the event date falls within ``[Jul 15, Aug 10]`` of the season's
    start year and the season window encloses it, ``_check_window`` SHALL
    return an empty warnings list.
    """
    preseason_start = date(year, *PRESEASON_START_MMDD)
    preseason_end = date(year, *PRESEASON_END_MMDD)

    event_date = preseason_start + timedelta(days=preseason_offset_days)
    season_start = preseason_start - timedelta(days=pad_before_days)
    season_end = preseason_end + timedelta(days=pad_after_days)

    # The pre-season window is anchored to ``season_start.year``, so the
    # padding-before must not push ``season_start`` into the previous year.
    assume(season_start.year == year)
    # Self-consistency sanity (always true here, but pin it down explicitly).
    assert preseason_start <= event_date <= preseason_end
    assert season_start <= event_date <= season_end

    warnings = SERVICE._check_window(event_date, season_start, season_end)

    assert warnings == [], (
        f"expected no warnings inside pre-season window, got {warnings!r} "
        f"for event_date={event_date}, season=[{season_start}, {season_end}]"
    )


# ──────────────────────────────────────────────────────────────────────────
# Branch 3: ``event_date`` inside the season but outside the pre-season
# window of ``season_start.year`` → warnings include
# ``"Дата вне предсезонного окна"`` (Requirement 5.8).
# ──────────────────────────────────────────────────────────────────────────
@given(event_date=_DATE, season_start=_DATE, season_end=_DATE)
@settings(max_examples=100, deadline=None)
def test_event_outside_preseason_emits_warning(
    event_date: date,
    season_start: date,
    season_end: date,
) -> None:
    """**Validates: Requirements 5.8, 12.4**

    When the event date lies inside the season but outside ``[Jul 15,
    Aug 10]`` of ``season_start.year``, ``_check_window`` SHALL succeed
    and the returned warnings SHALL contain
    ``"Дата вне предсезонного окна"``.
    """
    assume(season_start <= season_end)
    assume(season_start <= event_date <= season_end)

    preseason_start = date(season_start.year, *PRESEASON_START_MMDD)
    preseason_end = date(season_start.year, *PRESEASON_END_MMDD)
    assume(event_date < preseason_start or event_date > preseason_end)

    warnings = SERVICE._check_window(event_date, season_start, season_end)

    assert "Дата вне предсезонного окна" in warnings, (
        f"expected pre-season warning for event_date={event_date} "
        f"outside preseason=[{preseason_start}, {preseason_end}], "
        f"season=[{season_start}, {season_end}], got {warnings!r}"
    )
