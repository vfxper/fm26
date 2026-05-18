# Feature: friendly-matches, Property 5: Description format covers all match subtypes
"""
Property-based test for ``FriendlyMatchService._build_description``.

**Validates: Requirements 6.2, 6.3, 6.4**

For every ``match_type ∈ {"home", "away", "closed_door", "commercial_tour"}``,
home/away club names, optional commercial-tour venue, and optional free-form
suffix, the description produced by ``_build_description`` satisfies:

- starts with ``f"Товарищеский матч: {home_name} – {away_name}"``;
- has the marker ``" (закрытый)"`` appended iff ``match_type == "closed_door"``;
- has the marker ``f" — {venue['city']}"`` appended iff
  ``match_type == "commercial_tour"``;
- has the suffix ``f" [{suffix}]"`` appended iff ``suffix`` is non-empty.

The marker (when present) precedes the suffix (when present), and the
helper is purely functional — it touches no database state.

The public ``_build_description`` lives on :class:`FriendlyMatchService` but
does not access ``self.session``; passing ``None`` as the session is therefore
safe for this property test.
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from app.services.friendly_match_service import FriendlyMatchService


# ──────────────────────────────────────────────────────────────────────────
# Sample inputs.
# ──────────────────────────────────────────────────────────────────────────
SAMPLE_CLUB_NAMES = [
    "Арсенал",
    "Барселона",
    "Реал Мадрид",
    "Бавария",
    "Манчестер Сити",
    "Ливерпуль",
    "Ювентус",
    "Милан",
    "Интер",
    "ПСЖ",
    "Аякс",
    "Боруссия Дортмунд",
]

MATCH_TYPES = ["home", "away", "closed_door", "commercial_tour"]

# A representative tour venue. For commercial_tour matches the implementation
# only reads ``venue["city"]``; the other keys are present so the dict matches
# the shape returned by ``app.data.tour_venues.get_tour_venue_by_id``.
FAKE_VENUE = {
    "id": 1,
    "city": "Miami",
    "country": "USA",
    "stadium_name": "Hard Rock Stadium",
}

# A single shared service instance — ``_build_description`` is a pure helper
# that does not touch ``self.session``.
_SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────
# Property 5 — Description format covers all match subtypes.
# ──────────────────────────────────────────────────────────────────────────
@given(
    match_type=st.sampled_from(MATCH_TYPES),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    suffix=st.text(max_size=20),
)
@settings(max_examples=100, deadline=None)
def test_build_description_covers_all_match_subtypes(
    match_type: str,
    home_name: str,
    away_name: str,
    suffix: str,
) -> None:
    """**Validates: Requirements 6.2, 6.3, 6.4**

    For every (match_type × home × away × suffix), the produced description
    matches the canonical concatenation of base + subtype marker + suffix.
    """
    venue = FAKE_VENUE if match_type == "commercial_tour" else None

    description = _SERVICE._build_description(
        match_type,
        home_name,
        away_name,
        venue,
        suffix,
    )

    base = f"Товарищеский матч: {home_name} – {away_name}"

    # Build the canonical expected description from the specification.
    expected = base
    if match_type == "closed_door":
        expected += " (закрытый)"
    elif match_type == "commercial_tour":
        expected += f" — {venue['city']}"
    if suffix:
        expected += f" [{suffix}]"

    # Exact equality: the description matches the canonical form bit-for-bit.
    assert description == expected, (
        "Description mismatch.\n"
        f"  match_type: {match_type!r}\n"
        f"  home: {home_name!r} away: {away_name!r}\n"
        f"  suffix: {suffix!r}\n"
        f"  got:      {description!r}\n"
        f"  expected: {expected!r}"
    )

    # ── Structural sub-properties (Requirements 6.2-6.4) ──────────────

    # 6.2 (and base): every description starts with the canonical base.
    assert description.startswith(base), (
        f"Description must start with base. Got: {description!r}"
    )

    # 6.2: closed_door appends " (закрытый)" exactly once, immediately
    # after the base (and before any optional user suffix).
    if match_type == "closed_door":
        assert (base + " (закрытый)") in description, description

    # 6.3: commercial_tour appends f" — {venue['city']}" immediately
    # after the base.
    if match_type == "commercial_tour":
        assert (base + f" — {venue['city']}") in description, description

    # 6.4: when the user-supplied suffix is non-empty, the description
    # ends with f" [{suffix}]"; otherwise no trailing bracketed segment
    # is appended.
    if suffix:
        assert description.endswith(f" [{suffix}]"), description
    else:
        assert description == expected  # i.e. no " [...]" segment was added
