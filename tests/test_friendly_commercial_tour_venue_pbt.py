# Feature: friendly-matches, Property 4: commercial_tour requires a tour venue
"""
Property-based test for ``FriendlyMatchService._validate_tour_venue``.

**Validates: Requirements 3.8**

The commercial-tour subtype of a user-arranged friendly match requires
a valid ``tour_venue_id`` pointing at a row in
:data:`app.data.tour_venues.TOUR_VENUES`. Conversely, the other three
subtypes (``home``, ``away``, ``closed_door``) ignore the
``tour_venue_id`` argument entirely.

The four cases checked for every Hypothesis example:

  1. ``match_type == "commercial_tour"`` and ``tour_venue_id is None``
     SHALL raise ``ValidationError(http_status=422,
     message="Для коммерческого тура необходимо выбрать площадку")``.
  2. ``match_type == "commercial_tour"`` and ``tour_venue_id`` not
     present in ``TOUR_VENUES`` SHALL raise the same
     ``ValidationError``.
  3. ``match_type == "commercial_tour"`` and ``tour_venue_id`` present
     in ``TOUR_VENUES`` SHALL return the venue dict with matching id.
  4. ``match_type != "commercial_tour"`` SHALL return ``None`` for any
     value of ``tour_venue_id`` (including ``None``, valid ids, and
     invalid ids).
"""

from __future__ import annotations

from typing import Optional

from hypothesis import given, settings, strategies as st

from app.data.tour_venues import TOUR_VENUES
from app.services.friendly_match_service import (
    FriendlyMatchService,
    ValidationError,
)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────
VALID_VENUE_IDS = {vid for vid, *_ in TOUR_VENUES}
EXPECTED_MESSAGE = "Для коммерческого тура необходимо выбрать площадку"

# The service's __init__ accepts an AsyncSession and stores it on
# ``self.session``; ``_validate_tour_venue`` is a pure helper that does
# not touch the database, so we can pass ``None`` here.
_service = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────
# Property 4 — commercial_tour requires a tour venue
# ──────────────────────────────────────────────────────────────────────
@given(
    match_type=st.sampled_from(["home", "away", "closed_door", "commercial_tour"]),
    tour_venue_id=st.one_of(st.none(), st.integers(min_value=-5, max_value=100)),
)
@settings(max_examples=100, deadline=None)
def test_validate_tour_venue_property(
    match_type: str, tour_venue_id: Optional[int]
) -> None:
    """**Validates: Requirements 3.8**

    The four-way case analysis above SHALL hold for every combination
    of ``match_type`` and ``tour_venue_id``.
    """
    if match_type != "commercial_tour":
        # Case 4: non-tour subtypes ignore tour_venue_id entirely and
        # always return None — even when the id would otherwise be
        # invalid, the helper must not raise.
        result = _service._validate_tour_venue(match_type, tour_venue_id)
        assert result is None, (
            f"match_type={match_type!r} with tour_venue_id={tour_venue_id!r} "
            f"should return None, got {result!r}"
        )
        return

    # match_type == "commercial_tour" from here on
    if tour_venue_id is None or tour_venue_id not in VALID_VENUE_IDS:
        # Cases 1 & 2: missing or unknown id -> ValidationError.
        try:
            _service._validate_tour_venue(match_type, tour_venue_id)
        except ValidationError as ve:
            assert ve.http_status == 422, (
                f"expected http_status=422, got {ve.http_status}"
            )
            assert ve.message == EXPECTED_MESSAGE, (
                f"expected message={EXPECTED_MESSAGE!r}, got {ve.message!r}"
            )
        else:
            raise AssertionError(
                f"expected ValidationError for commercial_tour with "
                f"tour_venue_id={tour_venue_id!r}, but no exception was raised"
            )
        return

    # Case 3: valid id for commercial_tour -> returns the venue dict.
    result = _service._validate_tour_venue(match_type, tour_venue_id)
    assert isinstance(result, dict), (
        f"expected dict for valid venue id={tour_venue_id}, got {result!r}"
    )
    assert result["id"] == tour_venue_id, (
        f"venue dict id mismatch: expected {tour_venue_id}, got {result['id']}"
    )
    # Sanity check: the dict shape matches get_tour_venues() shape.
    assert set(result.keys()) == {"id", "city", "country", "stadium_name"}, (
        f"unexpected keys in venue dict: {sorted(result.keys())}"
    )
