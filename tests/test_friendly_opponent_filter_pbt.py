# Feature: friendly-matches, Property 2: Client-side opponent filter is the intersection of search query and league filter
"""
Property-based test for the frontend ``filterOpponents`` helper.

**Validates: Requirements 2.2, 2.4, 2.5**

The opponent filter in the Friendly_Dialog combines a free-text search query
with a league dropdown. Per Property 2, the visible opponents must equal the
*intersection* of the two predicates:

    { c ∈ clubs : query.lower() ⊆ c.name.lower()
                 ∧ (leagueFilter == "Все лиги" ∨ c.league == leagueFilter) }

This test is intentionally written in Python: there is no JavaScript test
runner configured in this repository, and the task brief explicitly allows a
Python re-implementation that mirrors the JS spec. The reference JS lives in
``frontend/index.html`` (search for ``function filterOpponents``); a snapshot
of that implementation is reproduced below as a comment so any drift between
the two is easy to spot during code review.

Reference JS implementation (snapshot from ``frontend/index.html``):

    function filterOpponents(clubs, query, leagueFilter) {
      const q = (query || '').toLowerCase();
      return clubs.filter(c => {
        const matchQuery = !q || c.name.toLowerCase().includes(q);
        const matchLeague = !leagueFilter
                            || leagueFilter === 'Все лиги'
                            || c.league === leagueFilter;
        return matchQuery && matchLeague;
      });
    }

The Python ``filter_opponents`` below mirrors the JS semantics exactly:

  * ``query`` is folded to lower-case and used as a substring needle against
    ``name.lower()``. Empty / falsy ``query`` matches every club.
  * ``league_filter`` either equals ``"Все лиги"`` (the "all leagues" sentinel)
    or matches an exact league. Empty / falsy ``league_filter`` matches every
    club too, mirroring the JS short-circuit ``!leagueFilter``.

If the JS file is updated, update both the snapshot above and the Python
mirror to keep this property test meaningful.
"""

from __future__ import annotations

from typing import Optional

from hypothesis import given, settings, strategies as st


ALL_LEAGUES_SENTINEL = "Все лиги"


def filter_opponents(
    clubs: list[dict],
    query: Optional[str],
    league_filter: Optional[str],
) -> list[dict]:
    """Python mirror of the JS ``filterOpponents`` helper.

    The behaviour MUST match ``frontend/index.html`` exactly. See module
    docstring for the reference JS source.
    """
    q = (query or "").lower()
    result = []
    for c in clubs:
        match_query = (not q) or (q in c["name"].lower())
        match_league = (
            (not league_filter)
            or league_filter == ALL_LEAGUES_SENTINEL
            or c["league"] == league_filter
        )
        if match_query and match_league:
            result.append(c)
    return result


# --- Hypothesis strategies -------------------------------------------------

# A small but representative pool of league names. Including the sentinel
# in the league strategy is deliberate — clubs cannot legitimately belong to
# the sentinel league, so the test will exercise the case where the filter
# matches "Все лиги" but no real club has that league string.
_LEAGUES = ["La Liga", "Premier League", "Serie A", "Bundesliga", "Ligue 1", "RPL"]

_clubs = st.lists(
    st.fixed_dictionaries(
        {
            "id": st.integers(min_value=1, max_value=10_000),
            # Names mix Cyrillic, Latin, digits and whitespace so case-folding
            # behaviour is exercised across alphabets.
            "name": st.text(
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Lt", "Lo", "Nd", "Zs"),
                ),
                min_size=1,
                max_size=20,
            ),
            "league": st.sampled_from(_LEAGUES),
        }
    ),
    max_size=30,
)

# Queries can be empty, whitespace, single chars, or multi-word. Allow None
# so the JS short-circuit branch (``!q``) is exercised.
_queries = st.one_of(
    st.none(),
    st.text(max_size=10),
)

# League filter values: the sentinel, a real league, an unknown league, or
# None / empty (mirrors the JS ``!leagueFilter`` short-circuit).
_league_filters = st.one_of(
    st.just(ALL_LEAGUES_SENTINEL),
    st.sampled_from(_LEAGUES),
    st.just("Unknown League"),
    st.none(),
    st.just(""),
)


# --- Property test ---------------------------------------------------------


@given(clubs=_clubs, query=_queries, league_filter=_league_filters)
@settings(max_examples=100, deadline=None)
def test_filter_opponents_is_intersection_of_query_and_league(
    clubs: list[dict],
    query: Optional[str],
    league_filter: Optional[str],
) -> None:
    """**Validates: Requirements 2.2, 2.4, 2.5**

    The output of ``filter_opponents`` SHALL equal exactly the set of clubs
    that satisfy BOTH the case-insensitive name-contains-query predicate AND
    the league-filter predicate. Equivalently, this is a two-way containment
    proof:

      * Every returned club satisfies both predicates (soundness).
      * Every input club that satisfies both predicates appears in the
        output, in the original order, with no duplicates (completeness).
    """
    output = filter_opponents(clubs, query, league_filter)

    q_norm = (query or "").lower()

    def name_matches(club: dict) -> bool:
        # Empty query matches every club, mirroring the JS ``!q`` short-circuit.
        if not q_norm:
            return True
        return q_norm in club["name"].lower()

    def league_matches(club: dict) -> bool:
        # Empty / sentinel filter matches every club.
        if not league_filter or league_filter == ALL_LEAGUES_SENTINEL:
            return True
        return club["league"] == league_filter

    # 1. Soundness: every returned club satisfies BOTH predicates.
    for club in output:
        assert name_matches(club), (
            f"club {club!r} returned by filter but its name does not contain "
            f"query={query!r} (case-insensitive)"
        )
        assert league_matches(club), (
            f"club {club!r} returned by filter but its league does not match "
            f"league_filter={league_filter!r}"
        )

    # 2. Completeness: every input club satisfying BOTH predicates is returned.
    expected = [c for c in clubs if name_matches(c) and league_matches(c)]
    assert output == expected, (
        "filter_opponents output does not equal the intersection of the two "
        "predicates.\n"
        f"  clubs={clubs!r}\n"
        f"  query={query!r}\n"
        f"  league_filter={league_filter!r}\n"
        f"  expected={expected!r}\n"
        f"  got={output!r}"
    )

    # 3. Order preservation and no duplicates: output is a subsequence of the
    #    input list. This guards against accidental sorting or de-duplication
    #    that would still satisfy soundness + completeness as sets but break
    #    UI ordering.
    input_ids_in_order = [c["id"] for c in clubs]
    output_ids_in_order = [c["id"] for c in output]
    # Walk through the input ids and confirm the output ids appear in the
    # same relative order. Note: ids may collide because Hypothesis can
    # generate duplicates; we compare by reference position, not by id alone.
    j = 0
    for c in clubs:
        if j < len(output) and c is output[j]:
            j += 1
    assert j == len(output), (
        "filter_opponents reordered or duplicated entries; output must be a "
        "subsequence (by reference) of the input list.\n"
        f"  input_ids={input_ids_in_order!r}\n"
        f"  output_ids={output_ids_in_order!r}"
    )


# --- Targeted edge-case checks --------------------------------------------
#
# These deterministic cases pin down the corner behaviours the property test
# implies but does not name explicitly: empty query, sentinel league, and
# combined filters. They double as living documentation for Requirements 2.2,
# 2.4 and 2.5 and run instantly alongside the property test.


def test_empty_query_returns_all_clubs_filtered_by_league_only() -> None:
    """**Validates: Requirement 2.4** — empty query keeps every name."""
    clubs = [
        {"id": 1, "name": "Барселона", "league": "La Liga"},
        {"id": 2, "name": "Милан", "league": "Serie A"},
        {"id": 3, "name": "Реал Мадрид", "league": "La Liga"},
    ]
    assert filter_opponents(clubs, "", "La Liga") == [clubs[0], clubs[2]]
    assert filter_opponents(clubs, None, "La Liga") == [clubs[0], clubs[2]]


def test_all_leagues_sentinel_returns_all_clubs_filtered_by_query_only() -> None:
    """**Validates: Requirement 2.5** — sentinel disables the league filter."""
    clubs = [
        {"id": 1, "name": "Барселона", "league": "La Liga"},
        {"id": 2, "name": "Милан", "league": "Serie A"},
        {"id": 3, "name": "Барселона B", "league": "La Liga 2"},
    ]
    assert filter_opponents(clubs, "барс", ALL_LEAGUES_SENTINEL) == [
        clubs[0],
        clubs[2],
    ]


def test_query_and_league_combined_is_the_intersection() -> None:
    """**Validates: Requirement 2.2** — both predicates apply together."""
    clubs = [
        {"id": 1, "name": "Барселона", "league": "La Liga"},
        {"id": 2, "name": "Барселона B", "league": "La Liga 2"},
        {"id": 3, "name": "Реал Мадрид", "league": "La Liga"},
    ]
    # Only Barcelona (1) satisfies both predicates.
    assert filter_opponents(clubs, "барс", "La Liga") == [clubs[0]]


def test_case_insensitive_substring_match() -> None:
    """**Validates: Requirement 2.2** — the search is case-insensitive."""
    clubs = [
        {"id": 1, "name": "BARCELONA", "league": "La Liga"},
        {"id": 2, "name": "Real Madrid", "league": "La Liga"},
    ]
    assert filter_opponents(clubs, "BaRcE", ALL_LEAGUES_SENTINEL) == [clubs[0]]
    assert filter_opponents(clubs, "real", ALL_LEAGUES_SENTINEL) == [clubs[1]]
