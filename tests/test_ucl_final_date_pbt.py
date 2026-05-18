# Feature: uefa-champions-league, Property 10: Final scheduled on last Saturday of May
"""
Property-based test for UCL final-match scheduling.

**Validates: Requirement 6.2** — "WHEN the Final is scheduled, the
UCL_Generator SHALL place it on the last Saturday of May of the season's
end-year (`season_start_year + 1`)."

Properties tested:
  P10a — `get_final_date(year)` returns a date whose `weekday() == 5`
         (Saturday).
  P10b — `get_final_date(year)` returns a date in May (`month == 5`)
         of the requested `year`.
  P10c — Adding 7 days to the returned date pushes it into June, proving
         it is the *last* Saturday of May rather than any earlier Saturday.
"""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given, settings, strategies as st

from app.data.ucl_config import get_final_date


@settings(max_examples=100, deadline=None)
@given(year=st.integers(min_value=2020, max_value=2050))
def test_final_date_is_last_saturday_of_may(year: int) -> None:
    """P10 — `get_final_date(year)` is always the last Saturday of May."""
    final = get_final_date(year)

    # P10a: must be a Saturday.
    assert final.weekday() == 5, (
        f"get_final_date({year}) returned {final} with weekday="
        f"{final.weekday()}, expected 5 (Saturday)"
    )

    # P10b: must be in May of the requested year.
    assert final.year == year, (
        f"get_final_date({year}) returned {final}, expected year={year}"
    )
    assert final.month == 5, (
        f"get_final_date({year}) returned {final}, expected month=5 (May)"
    )

    # P10c: adding 7 days must overflow into June, proving this is the
    # LAST Saturday of May (no later Saturday exists in May).
    next_week = final + timedelta(days=7)
    assert next_week.month == 6, (
        f"get_final_date({year}) returned {final}, but {final} + 7 days = "
        f"{next_week} is still in May — not the last Saturday"
    )

    # Sanity: also verify the date is within May's bounds.
    assert date(year, 5, 1) <= final <= date(year, 5, 31), (
        f"get_final_date({year}) returned {final}, outside May bounds"
    )
