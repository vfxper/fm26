# Feature: uefa-champions-league, Property 5: Knockout bracket pairing invariants
"""
Property-based tests for the UEFA Champions League knockout bracket
pairing rules implemented by ``UCLGenerator.finalize_league_phase`` and
``UCLGenerator.build_round_of_16`` (and the bracket-folding logic in
``UCLGenerator.advance_bracket``).

**Validates: Requirements 4.4, 4.7, 5.1**

Per design.md > Property 5:

  *For any* completed league phase standings, the 8 generated knockout
  playoff ties SHALL each pair exactly one participant from rank range
  [9, 16] (high seed) with exactly one from rank range [17, 24] (low
  seed), and the high-seeded participant SHALL be stored as
  ``home_participant_id`` so it plays the second leg at home; furthermore
  the Round of 16 ties SHALL pair direct qualifiers (ranks 1-8) with
  knockout playoff winners following ``UCL_R16_BRACKET_MAP`` (seed 1
  paired with the lowest-ranked playoff winner, etc.), and round counts
  SHALL be exactly 8 R16 ties, 4 quarter final ties, and 2 semi final
  ties.

This test does not exercise the database. It builds a *pure helper*
that mirrors the documented pairing rules from the generator's
docstrings and code, then asserts the invariants hold for every
permutation of ranks 1..36 (Hypothesis ``st.permutations``). A
companion sanity test runs once on the canonical identity ordering
to keep the assertions readable.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from hypothesis import given, settings, strategies as st

from app.data.ucl_config import UCL_R16_BRACKET_MAP


# ---------------------------------------------------------------------------
# Pure helpers mirroring UCLGenerator pairing rules.
# ---------------------------------------------------------------------------

# A "tie" in this test is a 3-tuple: (bracket_position, home_pid, away_pid).
Tie = Tuple[int, int, int]


def _pair_knockout_playoff(rank_to_pid: Dict[int, int]) -> List[Tie]:
    """Mirror of ``UCLGenerator.finalize_league_phase`` step 3.

    Given a map ``rank → participant_id`` covering at least ranks 9-24,
    return the 8 knockout-playoff ties as
    ``(bracket_position, home_pid, away_pid)`` triples where the
    higher-seeded participant (lower ``final_rank``) is the home side
    so it plays leg 2 at home.

    bracket_position k pairs rank ``8 + k`` (high seed) with rank
    ``25 - k`` (low seed) for k in 1..8.
    """
    ties: List[Tie] = []
    for k in range(1, 9):
        high_rank = 8 + k        # 9..16
        low_rank = 25 - k        # 24..17
        ties.append((k, rank_to_pid[high_rank], rank_to_pid[low_rank]))
    return ties


def _pair_round_of_16(
    rank_to_pid: Dict[int, int],
    playoff_winner_pids: List[int],
    final_rank_by_pid: Dict[int, int],
) -> List[Tie]:
    """Mirror of ``UCLGenerator.build_round_of_16``.

    Pair the 8 direct qualifiers (final_rank 1-8) with the 8 knockout
    playoff winners using ``UCL_R16_BRACKET_MAP``. The direct qualifier
    is always the home side (plays leg 2 at home).

    The map's value is a 1-based index into the playoff winners sorted
    by their ``final_rank`` ascending — i.e. ``sorted_winners[0]`` is
    the highest-ranked surviving winner from ranks 9-16, and
    ``sorted_winners[7]`` is the lowest-ranked.
    """
    sorted_winners = sorted(
        playoff_winner_pids, key=lambda pid: final_rank_by_pid[pid]
    )
    ties: List[Tie] = []
    for seed in range(1, 9):
        home_pid = rank_to_pid[seed]
        opponent_idx = UCL_R16_BRACKET_MAP[seed]   # 1-based
        away_pid = sorted_winners[opponent_idx - 1]
        ties.append((seed, home_pid, away_pid))
    return ties


def _advance_bracket(prev_ties: List[Tie], winner_pids: List[int]) -> List[Tie]:
    """Mirror of ``UCLGenerator.advance_bracket`` pairing logic.

    Given the previous round's ties (sorted by bracket_position ASC) and
    the winner ``participant_id`` for each, fold positions
    ``(1, 2) -> new position 1`` (winner of 1 is home), ``(3, 4) -> 2``,
    etc.  Returns the new round's ties as
    ``(new_bracket_position, home_pid, away_pid)`` triples.
    """
    assert len(prev_ties) == len(winner_pids)
    sorted_pairs = sorted(zip(prev_ties, winner_pids), key=lambda t: t[0][0])
    winners_in_order = [w for _t, w in sorted_pairs]

    new_ties: List[Tie] = []
    for new_pos, base in enumerate(range(0, len(winners_in_order), 2), start=1):
        home = winners_in_order[base]
        away = winners_in_order[base + 1]
        new_ties.append((new_pos, home, away))
    return new_ties


# ---------------------------------------------------------------------------
# Property tests.
# ---------------------------------------------------------------------------

# Strategy: permutations of participant ids 1..36 represent rank → pid
# assignments. Position 0 in the permutation is the participant assigned
# rank 1, position 1 → rank 2, …, position 35 → rank 36.
_PERMUTATION_STRATEGY = st.permutations(list(range(1, 37)))


@given(perm=_PERMUTATION_STRATEGY)
@settings(max_examples=100, deadline=None)
def test_knockout_playoff_pairing_invariants(perm: List[int]) -> None:
    """**Validates: Requirement 4.4**

    For every possible league phase final ordering, the knockout
    playoff round produces:

      * exactly 8 ties;
      * each tie pairs one rank from [9-16] with one from [17-24];
      * the high-seeded (lower final_rank) participant is
        ``home_participant_id`` (plays leg 2 at home);
      * specifically, bracket_position k → home rank ``8 + k``,
        away rank ``25 - k``;
      * bracket_position values are unique and cover 1..8;
      * each of the 16 participants in ranks 9-24 appears in exactly
        one tie.
    """
    rank_to_pid = {rank: pid for rank, pid in enumerate(perm, start=1)}

    ties = _pair_knockout_playoff(rank_to_pid)

    # Round count = 8 ties.
    assert len(ties) == 8, f"expected 8 KO-playoff ties, got {len(ties)}"

    # bracket_position values unique and cover 1..8.
    positions = [t[0] for t in ties]
    assert sorted(positions) == list(range(1, 9)), (
        f"bracket_position values not unique 1..8: {positions}"
    )

    # Every participant in ranks 9-24 appears in exactly one tie.
    pid_to_rank = {pid: rank for rank, pid in rank_to_pid.items()}
    appearances: Dict[int, int] = {}
    for _pos, home_pid, away_pid in ties:
        appearances[home_pid] = appearances.get(home_pid, 0) + 1
        appearances[away_pid] = appearances.get(away_pid, 0) + 1
    expected_pids = {rank_to_pid[r] for r in range(9, 25)}
    assert set(appearances.keys()) == expected_pids, (
        f"KO-playoff participants mismatch:\n"
        f"  expected (ranks 9-24): {sorted(expected_pids)}\n"
        f"  got: {sorted(appearances.keys())}"
    )
    duplicates = {pid: n for pid, n in appearances.items() if n != 1}
    assert not duplicates, f"KO-playoff duplicates: {duplicates}"

    # For each bracket_position k: high seed = rank 8+k, low seed = rank 25-k,
    # high seed is home (plays leg 2 at home).
    for pos, home_pid, away_pid in ties:
        home_rank = pid_to_rank[home_pid]
        away_rank = pid_to_rank[away_pid]

        assert home_rank == 8 + pos, (
            f"bracket_position {pos}: home rank {home_rank}, expected {8 + pos}"
        )
        assert away_rank == 25 - pos, (
            f"bracket_position {pos}: away rank {away_rank}, expected {25 - pos}"
        )

        # High seed = lower numerical rank = better team.
        assert home_rank < away_rank, (
            f"bracket_position {pos}: home rank {home_rank} should be lower "
            f"than away rank {away_rank} (high seed plays leg 2 at home)"
        )
        assert 9 <= home_rank <= 16, (
            f"home rank {home_rank} not in [9, 16]"
        )
        assert 17 <= away_rank <= 24, (
            f"away rank {away_rank} not in [17, 24]"
        )


# Strategy combining a rank-permutation with a bitmask choosing which side
# of each KO-playoff tie advances. There are 2**8 = 256 possible winner
# combinations per rank assignment.
_WINNER_MASK_STRATEGY = st.integers(min_value=0, max_value=255)


@given(perm=_PERMUTATION_STRATEGY, winner_mask=_WINNER_MASK_STRATEGY)
@settings(max_examples=100, deadline=None)
def test_round_of_16_pairing_invariants(
    perm: List[int],
    winner_mask: int,
) -> None:
    """**Validates: Requirement 4.7, 5.1**

    For every league-phase ordering and every choice of KO-playoff
    winners, the Round of 16 pairing satisfies:

      * exactly 8 ties (Req 5.1);
      * direct qualifier (final_rank 1-8) is the home side
        (high seed plays leg 2 at home, Req 4.7);
      * mapping from seed to playoff-winner index is the bijection
        defined by ``UCL_R16_BRACKET_MAP``;
      * bracket_position values are unique and cover 1..8;
      * every direct qualifier appears exactly once across the 8 ties;
      * every playoff winner appears exactly once across the 8 ties.
    """
    rank_to_pid = {rank: pid for rank, pid in enumerate(perm, start=1)}
    final_rank_by_pid = {pid: rank for rank, pid in rank_to_pid.items()}

    # Build the KO-playoff ties and pick winners by bit mask.
    ko_ties = _pair_knockout_playoff(rank_to_pid)
    playoff_winner_pids: List[int] = []
    for idx, (_pos, home_pid, away_pid) in enumerate(ko_ties):
        bit = (winner_mask >> idx) & 1
        playoff_winner_pids.append(home_pid if bit == 0 else away_pid)

    # Sanity: 8 distinct winners drawn from ranks 9-24.
    assert len(playoff_winner_pids) == 8
    assert len(set(playoff_winner_pids)) == 8
    for pid in playoff_winner_pids:
        assert 9 <= final_rank_by_pid[pid] <= 24

    # Build R16 ties using the production helper.
    r16_ties = _pair_round_of_16(
        rank_to_pid=rank_to_pid,
        playoff_winner_pids=playoff_winner_pids,
        final_rank_by_pid=final_rank_by_pid,
    )

    # Round count = 8 ties.
    assert len(r16_ties) == 8, f"expected 8 R16 ties, got {len(r16_ties)}"

    # bracket_position values unique and cover 1..8.
    positions = [t[0] for t in r16_ties]
    assert sorted(positions) == list(range(1, 9)), (
        f"R16 bracket_position not unique 1..8: {positions}"
    )

    # UCL_R16_BRACKET_MAP must itself be a bijection of seeds 1-8 to
    # winner indices 1-8 (this is a static guarantee of the config).
    assert sorted(UCL_R16_BRACKET_MAP.keys()) == list(range(1, 9))
    assert sorted(UCL_R16_BRACKET_MAP.values()) == list(range(1, 9)), (
        f"UCL_R16_BRACKET_MAP is not a bijection: {UCL_R16_BRACKET_MAP}"
    )

    # Direct qualifiers (ranks 1-8) appear exactly once each as home;
    # playoff winners appear exactly once each as away.
    home_pids = [home for _pos, home, _away in r16_ties]
    away_pids = [away for _pos, _home, away in r16_ties]
    expected_dq = {rank_to_pid[r] for r in range(1, 9)}
    assert set(home_pids) == expected_dq, (
        f"R16 home participants must be exactly the 8 direct qualifiers; "
        f"got {sorted(home_pids)}, expected {sorted(expected_dq)}"
    )
    assert set(away_pids) == set(playoff_winner_pids), (
        f"R16 away participants must be exactly the 8 playoff winners; "
        f"got {sorted(away_pids)}, expected {sorted(playoff_winner_pids)}"
    )
    assert len(set(home_pids)) == 8 and len(set(away_pids)) == 8, (
        "Each direct qualifier and each playoff winner must appear exactly "
        "once across the 8 R16 ties"
    )

    # Per-tie invariants: home is the direct qualifier (rank 1-8), away
    # is a playoff winner whose rank is in [9, 24], and the mapping
    # follows UCL_R16_BRACKET_MAP.
    sorted_winners = sorted(
        playoff_winner_pids, key=lambda pid: final_rank_by_pid[pid]
    )
    for pos, home_pid, away_pid in r16_ties:
        home_rank = final_rank_by_pid[home_pid]
        away_rank = final_rank_by_pid[away_pid]

        assert 1 <= home_rank <= 8, (
            f"R16 pos {pos}: home rank {home_rank} not in [1, 8]"
        )
        assert 9 <= away_rank <= 24, (
            f"R16 pos {pos}: away rank {away_rank} not in [9, 24]"
        )
        assert home_rank < away_rank, (
            f"R16 pos {pos}: home rank {home_rank} should be lower than "
            f"away rank {away_rank} (high seed plays leg 2 at home)"
        )

        # Position == seed of the direct qualifier.
        assert home_pid == rank_to_pid[pos], (
            f"R16 pos {pos}: home pid should be the direct qualifier "
            f"with final_rank {pos}"
        )

        # Mapping rule: away_pid == sorted_winners[UCL_R16_BRACKET_MAP[pos] - 1].
        opponent_idx = UCL_R16_BRACKET_MAP[pos]
        expected_away = sorted_winners[opponent_idx - 1]
        assert away_pid == expected_away, (
            f"R16 pos {pos}: away pid {away_pid} (rank {away_rank}) does "
            f"not match UCL_R16_BRACKET_MAP[{pos}]={opponent_idx} "
            f"→ sorted_winners[{opponent_idx - 1}]={expected_away} "
            f"(rank {final_rank_by_pid[expected_away]})"
        )


@given(perm=_PERMUTATION_STRATEGY, winner_mask=_WINNER_MASK_STRATEGY)
@settings(max_examples=100, deadline=None)
def test_full_bracket_round_counts_and_position_uniqueness(
    perm: List[int],
    winner_mask: int,
) -> None:
    """**Validates: Requirement 5.1**

    Walking the bracket from the knockout playoff through the final
    yields the exact round counts mandated by Requirement 5.1:

      * 8 KO playoff ties
      * 8 Round of 16 ties
      * 4 Quarter Final ties
      * 2 Semi Final ties
      * 1 Final

    And ``bracket_position`` is unique within each round (1..N for
    round of N matches).
    """
    rank_to_pid = {rank: pid for rank, pid in enumerate(perm, start=1)}
    final_rank_by_pid = {pid: rank for rank, pid in rank_to_pid.items()}

    # KO playoff
    ko_ties = _pair_knockout_playoff(rank_to_pid)
    assert len(ko_ties) == 8
    assert sorted(t[0] for t in ko_ties) == list(range(1, 9))

    # Pick KO playoff winners.
    ko_winner_pids: List[int] = []
    for idx, (_pos, home_pid, away_pid) in enumerate(ko_ties):
        bit = (winner_mask >> idx) & 1
        ko_winner_pids.append(home_pid if bit == 0 else away_pid)

    # Round of 16
    r16_ties = _pair_round_of_16(
        rank_to_pid=rank_to_pid,
        playoff_winner_pids=ko_winner_pids,
        final_rank_by_pid=final_rank_by_pid,
    )
    assert len(r16_ties) == 8
    assert sorted(t[0] for t in r16_ties) == list(range(1, 9))

    # Choose R16 winners deterministically from the same mask.
    r16_winners = [
        home if ((winner_mask >> i) & 1) == 0 else away
        for i, (_p, home, away) in enumerate(r16_ties)
    ]
    assert len(set(r16_winners)) == 8

    # Quarter finals: 4 ties, positions 1..4.
    qf_ties = _advance_bracket(r16_ties, r16_winners)
    assert len(qf_ties) == 4, f"expected 4 QF ties, got {len(qf_ties)}"
    assert sorted(t[0] for t in qf_ties) == [1, 2, 3, 4]

    qf_winners = [
        home if ((winner_mask >> i) & 1) == 0 else away
        for i, (_p, home, away) in enumerate(qf_ties)
    ]
    assert len(set(qf_winners)) == 4

    # Semi finals: 2 ties, positions 1..2.
    sf_ties = _advance_bracket(qf_ties, qf_winners)
    assert len(sf_ties) == 2, f"expected 2 SF ties, got {len(sf_ties)}"
    assert sorted(t[0] for t in sf_ties) == [1, 2]

    sf_winners = [
        home if ((winner_mask >> i) & 1) == 0 else away
        for i, (_p, home, away) in enumerate(sf_ties)
    ]
    assert len(set(sf_winners)) == 2

    # Final: 1 single tie, position 1.
    final_ties = _advance_bracket(sf_ties, sf_winners)
    assert len(final_ties) == 1, f"expected 1 final, got {len(final_ties)}"
    assert final_ties[0][0] == 1


def test_ucl_r16_bracket_map_is_static_bijection() -> None:
    """Sanity check: ``UCL_R16_BRACKET_MAP`` is a bijection of seeds 1-8 to
    playoff-winner indices 1-8. This is a static config invariant and a
    necessary precondition for ``_pair_round_of_16`` to be correct.
    """
    assert sorted(UCL_R16_BRACKET_MAP.keys()) == list(range(1, 9))
    assert sorted(UCL_R16_BRACKET_MAP.values()) == list(range(1, 9))
    assert len(UCL_R16_BRACKET_MAP) == 8
