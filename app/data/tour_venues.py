"""
Tour venues for user-arranged friendly matches (commercial tour subtype).

Static list of internationally recognised stadiums used for pre-season
commercial tours. Each entry follows the shape:
    (id, city, country, stadium_name)

The list is used by:
    - GET /api/calendar/tour-venues to populate the dialog selector
    - FriendlyMatchService when the player picks `match_type="commercial_tour"`
      to look up venue metadata that is persisted into the
      ``calendar_events.travel_data`` JSON column.

See: .kiro/specs/friendly-matches/requirements.md (Requirement 4)
     .kiro/specs/friendly-matches/design.md (section "Tour venues data")
"""

from __future__ import annotations


# (id, city, country, stadium_name)
TOUR_VENUES: list[tuple[int, str, str, str]] = [
    (1, "Майами", "США", "Hard Rock Stadium"),
    (2, "Нью-Йорк", "США", "MetLife Stadium"),
    (3, "Лос-Анджелес", "США", "SoFi Stadium"),
    (4, "Токио", "Япония", "National Stadium"),
    (5, "Сингапур", "Сингапур", "National Stadium"),
    (6, "Эр-Рияд", "Саудовская Аравия", "King Fahd International Stadium"),
    (7, "Сидней", "Австралия", "Stadium Australia"),
    (8, "Мехико", "Мексика", "Estadio Azteca"),
]


def get_tour_venues() -> list[dict]:
    """Return the tour venues as a list of JSON-friendly dicts.

    The returned shape matches the ``GET /api/calendar/tour-venues`` API
    response (each item has ``id``, ``city``, ``country``, ``stadium_name``).
    """
    return [
        {
            "id": vid,
            "city": city,
            "country": country,
            "stadium_name": stadium,
        }
        for vid, city, country, stadium in TOUR_VENUES
    ]


def get_tour_venue_by_id(venue_id: int) -> dict | None:
    """Look up a single venue by its 1-based id.

    Returns the venue as a JSON-friendly dict, or ``None`` when the id
    does not match any known venue.
    """
    for vid, city, country, stadium in TOUR_VENUES:
        if vid == venue_id:
            return {
                "id": vid,
                "city": city,
                "country": country,
                "stadium_name": stadium,
            }
    return None
