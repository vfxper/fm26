# Feature: uefa-champions-league, Property 9: Description round-trip
"""
Property-based test for round-tripping UCL calendar event descriptions
through `UCLGenerator._build_event_description` and an inline parser
that mirrors the parsing logic invoked by the simulate endpoint
(`app.api.routes.calendar._parse_ucl_round_from_description` plus the
inline opponent/team-name extraction performed inside
`simulate_match_event`).

**Validates: Requirements 7.4, 7.5, 7.6, 7.7**

For matches involving the player's club, parsing the produced description
recovers ``round_type``, the ``matchday``/``leg`` index, the opponent
name, and the home/away tag.

For matches not involving the player's club, parsing recovers
``round_type``, the ``matchday``/``leg`` index, and both club names.

For the final, parsing additionally recovers the neutral venue.

All Russian (player-facing) and English (non-player) variants round-trip
correctly across many randomly generated inputs.
"""

from __future__ import annotations

import re
from typing import Optional

from hypothesis import given, settings, strategies as st

from app.api.routes.calendar import _parse_ucl_round_from_description
from app.services.ucl_generator import UCLGenerator


# ──────────────────────────────────────────────────────────────────────────
# Sample data — all picked to avoid characters that would break a simple
# regex parser (no " vs ", no unbalanced parentheses inside names).
# ──────────────────────────────────────────────────────────────────────────
SAMPLE_CLUB_NAMES = [
    "Arsenal",
    "Liverpool",
    "Manchester City",
    "R. Madrid",
    "A. Madrid",
    "Barcelona",
    "Bayern Munich",
    "Bayer Leverkusen",
    "Borussia Dortmund",
    "Inter Milan",
    "Juventus",
    "Paris Saint-Germain",
    "Ajax",
    "PSV Eindhoven",
    "Benfica",
    "Sporting CP",
    "Club Brugge",
    "Union Saint-Gilloise",
    "Bodø/Glimt",
    "Galatasaray",
    "Qarabağ",
    "Slavia Prague",
]

SAMPLE_VENUES = [
    "Puskás Aréna, Budapest",
    "Wembley Stadium, London",
    "Allianz Arena, Munich",
    "Santiago Bernabéu, Madrid",
    "San Siro, Milan",
]

ROUND_TYPES = [
    "league_phase",
    "knockout_playoff",
    "round_of_16",
    "quarter_final",
    "semi_final",
    "final",
]

KNOCKOUT_TIE_ROUNDS = [
    "knockout_playoff",
    "round_of_16",
    "quarter_final",
    "semi_final",
]

# The shared generator instance; `_build_event_description` is a pure
# helper that touches no database state.
_GEN = UCLGenerator(session=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────
# Inline parser — recovers the full set of fields the simulate endpoint
# needs from a UCL calendar-event description.
#
# The parser is intentionally written here (rather than added to
# `app.api.routes.calendar`) because Requirement 7.4–7.6 only mandate
# what `_build_event_description` *produces*; the simulate endpoint reads
# the same description back via `_parse_ucl_round_from_description` plus
# the inline string-splitting logic in `simulate_match_event`. We mirror
# that combined behaviour here so the test exercises the full round-trip
# contract.
# ──────────────────────────────────────────────────────────────────────────
def parse_description(
    description: str,
) -> dict:
    """
    Parse a UCL calendar-event description into a dict containing the
    fields produced by `UCLGenerator._build_event_description`.

    Returned keys (all optional except ``round_type``):
      ``round_type``     — one of the 6 round types, or ``None`` on parse
                            failure.
      ``is_player_match``— True when the description is in the Russian
                            player-facing format.
      ``matchday``       — int 1..8 for ``league_phase``, else ``None``.
      ``leg``            — int 1..2 for the four two-legged knockout
                            rounds, else ``None``.
      ``opponent_name``  — present for player matches.
      ``is_player_home`` — True/False for player matches (derived from
                            the (H)/(A) tag).
      ``home_club_name`` — present for non-player matches.
      ``away_club_name`` — present for non-player matches.
      ``venue``          — present for final matches (player and
                            non-player variants).
    """
    out: dict = {
        "round_type": None,
        "is_player_match": None,
        "matchday": None,
        "leg": None,
        "opponent_name": None,
        "is_player_home": None,
        "home_club_name": None,
        "away_club_name": None,
        "venue": None,
    }

    # ── Russian (player-facing) variants ──────────────────────────────
    # Player league phase: "Лига чемпионов, тур N: vs Opp (H|A)"
    m = re.match(
        r"^Лига чемпионов,\s*тур\s*(\d+):\s*vs\s+(.+?)\s+\((H|A)\)\s*$",
        description,
    )
    if m:
        out["round_type"] = "league_phase"
        out["is_player_match"] = True
        out["matchday"] = int(m.group(1))
        out["opponent_name"] = m.group(2)
        out["is_player_home"] = m.group(3) == "H"
        return out

    # Player knockout (KO playoff / R16 / QF / SF):
    #   "Лига чемпионов, <русский раунд> (матч N): vs Opp (H|A)"
    ru_round_to_type = {
        "квалификация плей-офф": "knockout_playoff",
        "1/8 финала": "round_of_16",
        "1/4 финала": "quarter_final",
        "1/2 финала": "semi_final",
    }
    m = re.match(
        r"^Лига чемпионов,\s*(квалификация плей-офф|1/8 финала|1/4 финала|1/2 финала)\s*"
        r"\(матч\s*(\d+)\):\s*vs\s+(.+?)\s+\((H|A)\)\s*$",
        description,
    )
    if m:
        out["round_type"] = ru_round_to_type[m.group(1)]
        out["is_player_match"] = True
        out["leg"] = int(m.group(2))
        out["opponent_name"] = m.group(3)
        out["is_player_home"] = m.group(4) == "H"
        return out

    # Player final: "Лига чемпионов, финал: vs Opp (H|A) (Venue)"
    m = re.match(
        r"^Лига чемпионов,\s*финал:\s*vs\s+(.+?)\s+\((H|A)\)\s+\((.+)\)\s*$",
        description,
    )
    if m:
        out["round_type"] = "final"
        out["is_player_match"] = True
        out["opponent_name"] = m.group(1)
        out["is_player_home"] = m.group(2) == "H"
        out["venue"] = m.group(3)
        return out

    # ── English (non-player) variants ─────────────────────────────────
    # Non-player league phase: "Champions League Matchday N: A vs B"
    m = re.match(
        r"^Champions League\s+Matchday\s+(\d+):\s+(.+?)\s+vs\s+(.+?)\s*$",
        description,
    )
    if m:
        out["round_type"] = "league_phase"
        out["is_player_match"] = False
        out["matchday"] = int(m.group(1))
        out["home_club_name"] = m.group(2)
        out["away_club_name"] = m.group(3)
        return out

    # Non-player knockout: "Champions League <En round> (leg N): A vs B"
    en_round_to_type = {
        "Knockout Playoff": "knockout_playoff",
        "Round of 16": "round_of_16",
        "Quarter Final": "quarter_final",
        "Semi Final": "semi_final",
    }
    m = re.match(
        r"^Champions League\s+(Knockout Playoff|Round of 16|Quarter Final|Semi Final)\s+"
        r"\(leg\s+(\d+)\):\s+(.+?)\s+vs\s+(.+?)\s*$",
        description,
    )
    if m:
        out["round_type"] = en_round_to_type[m.group(1)]
        out["is_player_match"] = False
        out["leg"] = int(m.group(2))
        out["home_club_name"] = m.group(3)
        out["away_club_name"] = m.group(4)
        return out

    # Non-player final: "Champions League Final: A vs B (Venue)"
    m = re.match(
        r"^Champions League\s+Final:\s+(.+?)\s+vs\s+(.+?)\s+\((.+)\)\s*$",
        description,
    )
    if m:
        out["round_type"] = "final"
        out["is_player_match"] = False
        out["home_club_name"] = m.group(1)
        out["away_club_name"] = m.group(2)
        out["venue"] = m.group(3)
        return out

    return out


# ──────────────────────────────────────────────────────────────────────────
# Property 9a — Player league-phase description round-trip
# ──────────────────────────────────────────────────────────────────────────
@given(
    matchday=st.integers(min_value=1, max_value=8),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    is_player_home=st.booleans(),
)
@settings(max_examples=100, deadline=None)
def test_player_league_phase_description_roundtrip(
    matchday: int,
    home_name: str,
    away_name: str,
    is_player_home: bool,
) -> None:
    """
    **Validates: Requirements 7.4, 7.7**

    For player league_phase matches the description recovers
    ``round_type``, ``matchday``, opponent name, and home/away tag.
    """
    player_name = home_name if is_player_home else away_name
    opponent = away_name if is_player_home else home_name

    desc = _GEN._build_event_description(
        round_type="league_phase",
        matchday=matchday,
        leg=None,
        player_club_id=99,  # any non-None id triggers the player branch
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=is_player_home,
        opponent_name=opponent,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == "league_phase", desc
    assert parsed["is_player_match"] is True, desc
    assert parsed["matchday"] == matchday, desc
    assert parsed["opponent_name"] == opponent, desc
    assert parsed["is_player_home"] is is_player_home, desc

    # Cross-check: the existing helper used by simulate_match_event also
    # recovers the round_type (it returns leg=None for league_phase).
    rt, leg = _parse_ucl_round_from_description(desc)
    assert rt == "league_phase"
    assert leg is None


# ──────────────────────────────────────────────────────────────────────────
# Property 9b — Player two-legged-knockout description round-trip
# ──────────────────────────────────────────────────────────────────────────
@given(
    round_type=st.sampled_from(KNOCKOUT_TIE_ROUNDS),
    leg=st.integers(min_value=1, max_value=2),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    is_player_home=st.booleans(),
)
@settings(max_examples=100, deadline=None)
def test_player_knockout_description_roundtrip(
    round_type: str,
    leg: int,
    home_name: str,
    away_name: str,
    is_player_home: bool,
) -> None:
    """
    **Validates: Requirements 7.4, 7.7**

    For player knockout-playoff / R16 / QF / SF matches the description
    recovers ``round_type``, ``leg``, opponent name, and home/away tag.
    """
    opponent = away_name if is_player_home else home_name

    desc = _GEN._build_event_description(
        round_type=round_type,
        matchday=None,
        leg=leg,
        player_club_id=99,
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=is_player_home,
        opponent_name=opponent,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == round_type, desc
    assert parsed["is_player_match"] is True, desc
    assert parsed["leg"] == leg, desc
    assert parsed["opponent_name"] == opponent, desc
    assert parsed["is_player_home"] is is_player_home, desc

    rt, parsed_leg = _parse_ucl_round_from_description(desc)
    assert rt == round_type
    assert parsed_leg == leg


# ──────────────────────────────────────────────────────────────────────────
# Property 9c — Player final description round-trip (incl. venue)
# ──────────────────────────────────────────────────────────────────────────
@given(
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    is_player_home=st.booleans(),
    venue=st.sampled_from(SAMPLE_VENUES),
)
@settings(max_examples=100, deadline=None)
def test_player_final_description_roundtrip(
    home_name: str,
    away_name: str,
    is_player_home: bool,
    venue: str,
) -> None:
    """
    **Validates: Requirements 7.6, 7.7**

    For the final involving the player's club, parsing recovers
    ``round_type='final'``, opponent name, home/away tag, and the
    neutral venue.
    """
    opponent = away_name if is_player_home else home_name

    desc = _GEN._build_event_description(
        round_type="final",
        matchday=None,
        leg=None,
        player_club_id=99,
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=is_player_home,
        opponent_name=opponent,
        neutral_venue=venue,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == "final", desc
    assert parsed["is_player_match"] is True, desc
    assert parsed["opponent_name"] == opponent, desc
    assert parsed["is_player_home"] is is_player_home, desc
    assert parsed["venue"] == venue, desc

    rt, parsed_leg = _parse_ucl_round_from_description(desc)
    assert rt == "final"
    assert parsed_leg is None


# ──────────────────────────────────────────────────────────────────────────
# Property 9d — Non-player league-phase description round-trip
# ──────────────────────────────────────────────────────────────────────────
@given(
    matchday=st.integers(min_value=1, max_value=8),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
)
@settings(max_examples=100, deadline=None)
def test_nonplayer_league_phase_description_roundtrip(
    matchday: int,
    home_name: str,
    away_name: str,
) -> None:
    """
    **Validates: Requirements 7.5, 7.7**

    For non-player league_phase matches the description recovers
    ``round_type``, ``matchday``, and both club names.
    """
    desc = _GEN._build_event_description(
        round_type="league_phase",
        matchday=matchday,
        leg=None,
        player_club_id=None,
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=None,
        opponent_name=None,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == "league_phase", desc
    assert parsed["is_player_match"] is False, desc
    assert parsed["matchday"] == matchday, desc
    assert parsed["home_club_name"] == home_name, desc
    assert parsed["away_club_name"] == away_name, desc

    rt, leg = _parse_ucl_round_from_description(desc)
    assert rt == "league_phase"
    assert leg is None


# ──────────────────────────────────────────────────────────────────────────
# Property 9e — Non-player knockout description round-trip
# ──────────────────────────────────────────────────────────────────────────
@given(
    round_type=st.sampled_from(KNOCKOUT_TIE_ROUNDS),
    leg=st.integers(min_value=1, max_value=2),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
)
@settings(max_examples=100, deadline=None)
def test_nonplayer_knockout_description_roundtrip(
    round_type: str,
    leg: int,
    home_name: str,
    away_name: str,
) -> None:
    """
    **Validates: Requirements 7.5, 7.7**

    For non-player knockout matches (KO playoff / R16 / QF / SF) the
    description recovers ``round_type``, ``leg``, and both club names.
    """
    desc = _GEN._build_event_description(
        round_type=round_type,
        matchday=None,
        leg=leg,
        player_club_id=None,
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=None,
        opponent_name=None,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == round_type, desc
    assert parsed["is_player_match"] is False, desc
    assert parsed["leg"] == leg, desc
    assert parsed["home_club_name"] == home_name, desc
    assert parsed["away_club_name"] == away_name, desc

    rt, parsed_leg = _parse_ucl_round_from_description(desc)
    assert rt == round_type
    assert parsed_leg == leg


# ──────────────────────────────────────────────────────────────────────────
# Property 9f — Non-player final description round-trip (incl. venue)
# ──────────────────────────────────────────────────────────────────────────
@given(
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    venue=st.sampled_from(SAMPLE_VENUES),
)
@settings(max_examples=100, deadline=None)
def test_nonplayer_final_description_roundtrip(
    home_name: str,
    away_name: str,
    venue: str,
) -> None:
    """
    **Validates: Requirements 7.6, 7.7**

    For the final between two non-player clubs, parsing recovers
    ``round_type='final'``, both club names, and the neutral venue.
    """
    desc = _GEN._build_event_description(
        round_type="final",
        matchday=None,
        leg=None,
        player_club_id=None,
        home_club_name=home_name,
        away_club_name=away_name,
        is_player_home=None,
        opponent_name=None,
        neutral_venue=venue,
    )

    parsed = parse_description(desc)
    assert parsed["round_type"] == "final", desc
    assert parsed["is_player_match"] is False, desc
    assert parsed["home_club_name"] == home_name, desc
    assert parsed["away_club_name"] == away_name, desc
    assert parsed["venue"] == venue, desc

    rt, parsed_leg = _parse_ucl_round_from_description(desc)
    assert rt == "final"
    assert parsed_leg is None


# ──────────────────────────────────────────────────────────────────────────
# Property 9g — Combined round-trip across every supported variant
# ──────────────────────────────────────────────────────────────────────────
@given(
    round_type=st.sampled_from(ROUND_TYPES),
    matchday=st.integers(min_value=1, max_value=8),
    leg=st.integers(min_value=1, max_value=2),
    home_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    away_name=st.sampled_from(SAMPLE_CLUB_NAMES),
    venue=st.sampled_from(SAMPLE_VENUES),
    is_player_home=st.booleans(),
    is_player_involved=st.booleans(),
)
@settings(max_examples=100, deadline=None)
def test_description_roundtrip_combined(
    round_type: str,
    matchday: int,
    leg: int,
    home_name: str,
    away_name: str,
    venue: str,
    is_player_home: bool,
    is_player_involved: bool,
) -> None:
    """
    **Validates: Requirements 7.4, 7.5, 7.6, 7.7**

    Universal round-trip property — every (round_type × player/non-player
    × Russian/English) variant of `_build_event_description` produces a
    description from which the parser recovers ``round_type`` and the
    leg index (where applicable). For player variants the opponent name
    and (H)/(A) tag round-trip; for non-player variants both team names
    round-trip; for the final the venue round-trips.
    """
    if is_player_involved:
        opponent = away_name if is_player_home else home_name
        desc = _GEN._build_event_description(
            round_type=round_type,
            matchday=matchday if round_type == "league_phase" else None,
            leg=leg if round_type in KNOCKOUT_TIE_ROUNDS else None,
            player_club_id=99,
            home_club_name=home_name,
            away_club_name=away_name,
            is_player_home=is_player_home,
            opponent_name=opponent,
            neutral_venue=venue if round_type == "final" else None,
        )
        parsed = parse_description(desc)
        assert parsed["round_type"] == round_type, desc
        assert parsed["is_player_match"] is True, desc
        assert parsed["opponent_name"] == opponent, desc
        assert parsed["is_player_home"] is is_player_home, desc
        if round_type == "league_phase":
            assert parsed["matchday"] == matchday, desc
        elif round_type in KNOCKOUT_TIE_ROUNDS:
            assert parsed["leg"] == leg, desc
        elif round_type == "final":
            assert parsed["venue"] == venue, desc
    else:
        desc = _GEN._build_event_description(
            round_type=round_type,
            matchday=matchday if round_type == "league_phase" else None,
            leg=leg if round_type in KNOCKOUT_TIE_ROUNDS else None,
            player_club_id=None,
            home_club_name=home_name,
            away_club_name=away_name,
            is_player_home=None,
            opponent_name=None,
            neutral_venue=venue if round_type == "final" else None,
        )
        parsed = parse_description(desc)
        assert parsed["round_type"] == round_type, desc
        assert parsed["is_player_match"] is False, desc
        assert parsed["home_club_name"] == home_name, desc
        assert parsed["away_club_name"] == away_name, desc
        if round_type == "league_phase":
            assert parsed["matchday"] == matchday, desc
        elif round_type in KNOCKOUT_TIE_ROUNDS:
            assert parsed["leg"] == leg, desc
        elif round_type == "final":
            assert parsed["venue"] == venue, desc

    # The shared `_parse_ucl_round_from_description` helper agrees on the
    # round_type and (where present) leg value across every variant.
    rt, parsed_leg = _parse_ucl_round_from_description(desc)
    assert rt == round_type
    if round_type in KNOCKOUT_TIE_ROUNDS:
        assert parsed_leg == leg
    else:
        assert parsed_leg is None
