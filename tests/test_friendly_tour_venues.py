# Feature: friendly-matches, Unit test for get_tour_venue_by_id
"""Unit tests for ``app.data.tour_venues.get_tour_venue_by_id``.

Validates Requirements 4.1, 4.2:
    * Each of the 8 venues defined in ``TOUR_VENUES`` is retrievable by id.
    * An unknown id returns ``None``.
"""

from __future__ import annotations

from app.data.tour_venues import (
    TOUR_VENUES,
    get_tour_venue_by_id,
    get_tour_venues,
)


def test_tour_venues_has_exactly_eight_entries() -> None:
    """Requirement 4.2 specifies 8 commercial tour venues."""
    assert len(TOUR_VENUES) == 8


def test_get_tour_venue_by_id_returns_each_known_venue() -> None:
    """Every entry in ``TOUR_VENUES`` must be retrievable via lookup."""
    for vid, city, country, stadium in TOUR_VENUES:
        result = get_tour_venue_by_id(vid)
        assert result is not None, f"venue id {vid} should be retrievable"
        assert result == {
            "id": vid,
            "city": city,
            "country": country,
            "stadium_name": stadium,
        }


def test_get_tour_venue_by_id_matches_get_tour_venues_listing() -> None:
    """Single-id lookup must agree with the bulk ``get_tour_venues`` listing."""
    listing = get_tour_venues()
    for venue in listing:
        assert get_tour_venue_by_id(venue["id"]) == venue


def test_get_tour_venue_by_id_zero_returns_none() -> None:
    """Id 0 is not a valid venue id (ids are 1-based)."""
    assert get_tour_venue_by_id(0) is None


def test_get_tour_venue_by_id_unknown_id_returns_none() -> None:
    """Id 99 is well above the 8 known venues and must return ``None``."""
    assert get_tour_venue_by_id(99) is None
