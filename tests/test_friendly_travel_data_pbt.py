# Feature: friendly-matches, Property 6: travel_data round-trip preserves match subtype data
"""
Property-based test for ``FriendlyMatchService._build_travel_data``.

**Validates: Requirements 6.5, 6.6, 6.7**

The ``travel_data`` dict produced by ``_build_travel_data`` must be a pure
JSON-serialisable structure whose keys depend only on ``match_type``:

  * ``home`` / ``away``     → ``{"match_subtype": match_type}``                       (Req 6.7)
  * ``closed_door``         → ``{"match_subtype": "closed_door",
                                 "venue": "training_ground"}``                        (Req 6.6)
  * ``commercial_tour``     → ``{"match_subtype": "commercial_tour",
                                 "city": ..., "country": ...,
                                 "stadium_name": ...}``                               (Req 6.5)

This property checks that the dict survives a ``json.dumps`` /
``json.loads`` round-trip with ``ensure_ascii=False`` — important because
real venue cities (``"Майами"``, ``"São Paulo"``, ``"Токио"``, ...) contain
non-ASCII characters that must reach the SQLite ``travel_data`` column
intact and reappear unchanged on the API.
"""

from __future__ import annotations

import json

from hypothesis import given, settings, strategies as st

from app.services.friendly_match_service import FriendlyMatchService


# A FriendlyMatchService with no DB session is fine here: ``_build_travel_data``
# is a pure synchronous helper that does not touch ``self.session``.
_SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# Realistic cities/countries/stadium names with explicit Unicode so the
# ``ensure_ascii=False`` contract is exercised by every example.
SAMPLE_CITIES = [
    "Майами",
    "Нью-Йорк",
    "Лос-Анджелес",
    "Токио",
    "Сингапур",
    "Эр-Рияд",
    "Сидней",
    "Мехико",
    "São Paulo",
    "México",
    "Zürich",
    "København",
    "Tokyo",
    "Москва",
    "İstanbul",
    "Köln",
]

SAMPLE_COUNTRIES = [
    "США",
    "Япония",
    "Сингапур",
    "Саудовская Аравия",
    "Австралия",
    "Мексика",
    "Brasil",
    "Türkiye",
    "España",
    "Россия",
    "Deutschland",
]

SAMPLE_STADIUMS = [
    "Hard Rock Stadium",
    "MetLife Stadium",
    "SoFi Stadium",
    "National Stadium",
    "King Fahd International Stadium",
    "Stadium Australia",
    "Estadio Azteca",
    "Estádio do Maracanã",
    "Allianz Arena",
    "Stade Vélodrome",
]


# Strategy: a venue dict shaped exactly like ``get_tour_venue_by_id``
# returns. ``id`` is unused by ``_build_travel_data`` for round-trip
# purposes but keeping it here matches what the orchestrator passes in.
_venue_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=1, max_value=999),
        "city": st.sampled_from(SAMPLE_CITIES),
        "country": st.sampled_from(SAMPLE_COUNTRIES),
        "stadium_name": st.sampled_from(SAMPLE_STADIUMS),
    }
)


# ──────────────────────────────────────────────────────────────────────────
# Property 6 — travel_data JSON round-trip preserves match subtype data
# ──────────────────────────────────────────────────────────────────────────
@given(
    match_type=st.sampled_from(
        ["home", "away", "closed_door", "commercial_tour"]
    ),
    venue=_venue_strategy,
)
@settings(max_examples=100, deadline=None)
def test_travel_data_json_roundtrip(
    match_type: str,
    venue: dict,
) -> None:
    """**Validates: Requirements 6.5, 6.6, 6.7**

    For every supported ``match_type``, ``_build_travel_data`` produces a
    dict whose JSON encoding is a fixed point under ``json.dumps`` (with
    ``ensure_ascii=False``) followed by ``json.loads`` — i.e. no Unicode
    mangling, no key reordering surprises, no type drift — and whose
    required keys match the contract in Requirements 6.5 / 6.6 / 6.7.
    """
    # Only commercial_tour consults the venue; the other branches ignore
    # it and must yield the same shape regardless.
    venue_for_call = venue if match_type == "commercial_tour" else None

    travel_data = _SERVICE._build_travel_data(match_type, venue_for_call)

    # ── 1. JSON round-trip is a fixed point ─────────────────────────────
    encoded = json.dumps(travel_data, ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded == travel_data, (
        f"travel_data did not survive json round-trip: "
        f"original={travel_data!r}, decoded={decoded!r}"
    )

    # And the encoded string must not contain any escaped \uXXXX sequence
    # for a Unicode character — that would defeat ensure_ascii=False and
    # is the mangling this property guards against.
    assert "\\u" not in encoded, (
        f"json.dumps produced \\u-escaped output despite ensure_ascii=False: "
        f"{encoded!r}"
    )

    # ── 2. Required-keys contract per match_type ────────────────────────
    if match_type in ("home", "away"):
        # Req 6.7
        assert travel_data == {"match_subtype": match_type}, (
            f"home/away travel_data must be exactly "
            f'{{"match_subtype": {match_type!r}}}; got {travel_data!r}'
        )
    elif match_type == "closed_door":
        # Req 6.6
        assert travel_data == {
            "match_subtype": "closed_door",
            "venue": "training_ground",
        }, (
            f"closed_door travel_data must be exactly "
            f'{{"match_subtype": "closed_door", "venue": "training_ground"}}; '
            f"got {travel_data!r}"
        )
    else:  # commercial_tour
        # Req 6.5
        assert set(travel_data.keys()) == {
            "match_subtype",
            "city",
            "country",
            "stadium_name",
        }, (
            f"commercial_tour travel_data must contain exactly the keys "
            f"match_subtype/city/country/stadium_name; got "
            f"keys={sorted(travel_data.keys())!r}"
        )
        assert travel_data["match_subtype"] == "commercial_tour"
        assert travel_data["city"] == venue["city"]
        assert travel_data["country"] == venue["country"]
        assert travel_data["stadium_name"] == venue["stadium_name"]
