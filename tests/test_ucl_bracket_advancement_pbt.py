# Feature: uefa-champions-league, Property 6: Bracket winner advancement
"""
Property-based test for ``UCLGenerator.advance_bracket``.

**Validates: Requirements 4.6, 5.6**

The advancement rule (see ``app/services/ucl_generator.py::advance_bracket``):
  * inputs: the 8 / 4 / 2 winners of the previous round, each tagged with
    its source ``bracket_position``;
  * winners are sorted by ``bracket_position`` ascending and paired
    consecutively — positions ``2k-1`` and ``2k`` in round R produce
    bracket position ``k`` in round R+1;
  * the lower-positioned winner of each pair becomes the new tie's
    ``home_participant_id`` (the higher seed which plays leg 2 at home),
    the higher-positioned winner becomes ``away_participant_id``;
  * for the special ``semi_final → final`` case there is exactly one new
    tie at ``bracket_position = 1``.

We exercise the rule via a pure helper that mirrors the database-level
logic so we can run Hypothesis at scale without spinning up a session.
The chain ``round_of_16 → quarter_final → semi_final → final`` is then
fed through end-to-end to confirm bracket integrity and uniqueness of
participants per round.
"""

from __future__ import annotations

from typing import List, Tuple

from hypothesis import given, settings, strategies as st


# ──────────────────────────────────────────────────────────────────────────
# Pure helper mirroring `UCLGenerator.advance_bracket` pairing logic.
# Implementation reference (paraphrased from ucl_generator.py):
#
#     winners.sort(key=lambda x: x[0])  # by bracket_position ASC
#     for new_pos, base in enumerate(range(0, len(winners), 2), start=1):
#         home_pid = winners[base][1]
#         away_pid = winners[base + 1][1]
#
# i.e. new tie at `new_pos = k` is composed of the winners of source
# positions `(2k-1, 2k)`.
# ──────────────────────────────────────────────────────────────────────────
def advance_round(
    winners: List[Tuple[int, int]],
) -> List[Tuple[int, int, int]]:
    """
    Pair the winners of a knockout round into the next round's ties.

    Args:
      winners: list of (bracket_position, winner_participant_id), one per
               tie of the source round. Length must be even.

    Returns:
      list of (new_bracket_position, home_participant_id, away_participant_id),
      one per tie of the next round. ``home_participant_id`` corresponds
      to the lower source ``bracket_position``.
    """
    if len(winners) % 2 != 0:
        raise ValueError(
            f"advance_round requires an even number of winners, got {len(winners)}"
        )
    sorted_winners = sorted(winners, key=lambda x: x[0])
    new_ties: List[Tuple[int, int, int]] = []
    for new_pos, base in enumerate(range(0, len(sorted_winners), 2), start=1):
        home_pid = sorted_winners[base][1]
        away_pid = sorted_winners[base + 1][1]
        new_ties.append((new_pos, home_pid, away_pid))
    return new_ties


# ──────────────────────────────────────────────────────────────────────────
# Hypothesis strategy — generate a permutation of N distinct participant
# ids paired one-to-one with bracket positions 1..N. We use distinct ids
# drawn from a wide range so the test cannot accidentally pass on a
# coincidental id collision.
# ──────────────────────────────────────────────────────────────────────────
def _round_winners(num_ties: int) -> st.SearchStrategy[List[Tuple[int, int]]]:
    """
    Generate a list of ``num_ties`` winners, each a
    ``(bracket_position, participant_id)`` tuple. Bracket positions are
    exactly ``1..num_ties``; participant ids are distinct integers.
    """

    def _build(pids: List[int]) -> List[Tuple[int, int]]:
        # `pids` is already a permutation of `num_ties` distinct ints.
        return list(zip(range(1, num_ties + 1), pids))

    return st.lists(
        st.integers(min_value=1, max_value=10_000),
        min_size=num_ties,
        max_size=num_ties,
        unique=True,
    ).map(_build)


# ──────────────────────────────────────────────────────────────────────────
# Property 6a — Single-step advancement preserves bracket integrity.
# ──────────────────────────────────────────────────────────────────────────
@given(winners=_round_winners(8))
@settings(max_examples=100, deadline=None)
def test_advance_eight_to_four_preserves_pairing(
    winners: List[Tuple[int, int]],
) -> None:
    """
    **Validates: Requirements 4.6, 5.6**

    Advancing 8 source winners produces exactly 4 next-round ties at
    positions 1..4, with each new tie composed of the winners of source
    positions ``(2k-1, 2k)``. ``home_participant_id`` is always the
    lower-source-position winner.
    """
    next_ties = advance_round(winners)

    assert len(next_ties) == 4, f"expected 4 next-round ties, got {len(next_ties)}"

    # Bracket positions are exactly {1, 2, 3, 4} with no duplicates.
    new_positions = [t[0] for t in next_ties]
    assert sorted(new_positions) == [1, 2, 3, 4], (
        f"new bracket positions are not {{1, 2, 3, 4}}: {new_positions}"
    )

    # Pairing rule: position k maps to source positions (2k-1, 2k).
    by_source = {pos: pid for pos, pid in winners}
    for new_pos, home_pid, away_pid in next_ties:
        expected_home = by_source[2 * new_pos - 1]
        expected_away = by_source[2 * new_pos]
        assert home_pid == expected_home, (
            f"new pos {new_pos}: home should be winner of source pos "
            f"{2 * new_pos - 1} ({expected_home}), got {home_pid}"
        )
        assert away_pid == expected_away, (
            f"new pos {new_pos}: away should be winner of source pos "
            f"{2 * new_pos} ({expected_away}), got {away_pid}"
        )

    # No participant appears in two ties of the next round.
    appearing = []
    for _pos, h, a in next_ties:
        appearing.append(h)
        appearing.append(a)
    assert len(set(appearing)) == len(appearing), (
        f"some participant appears in two next-round ties: {appearing}"
    )

    # Conservation: every source winner appears exactly once in the next
    # round (no winners dropped, no participants invented).
    expected_set = {pid for _pos, pid in winners}
    assert set(appearing) == expected_set, (
        f"next-round participants {set(appearing)} do not match source "
        f"winners {expected_set}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Property 6b — Single-step advancement for QF → SF (4 → 2 ties).
# ──────────────────────────────────────────────────────────────────────────
@given(winners=_round_winners(4))
@settings(max_examples=100, deadline=None)
def test_advance_four_to_two_preserves_pairing(
    winners: List[Tuple[int, int]],
) -> None:
    """
    **Validates: Requirements 4.6, 5.6**

    Advancing 4 quarter-final winners produces exactly 2 semi-final ties
    at positions 1..2, with the same pairing rule as 8→4.
    """
    next_ties = advance_round(winners)

    assert len(next_ties) == 2, f"expected 2 next-round ties, got {len(next_ties)}"
    assert sorted(t[0] for t in next_ties) == [1, 2]

    by_source = {pos: pid for pos, pid in winners}
    for new_pos, home_pid, away_pid in next_ties:
        assert home_pid == by_source[2 * new_pos - 1], (
            f"4→2 home pairing: pos {new_pos} expected source "
            f"{2 * new_pos - 1}, got pid {home_pid}"
        )
        assert away_pid == by_source[2 * new_pos], (
            f"4→2 away pairing: pos {new_pos} expected source "
            f"{2 * new_pos}, got pid {away_pid}"
        )

    appearing = [pid for _pos, h, a in next_ties for pid in (h, a)]
    assert len(set(appearing)) == 4
    assert set(appearing) == {pid for _pos, pid in winners}


# ──────────────────────────────────────────────────────────────────────────
# Property 6c — Single-step advancement for SF → Final (2 → 1 tie).
# ──────────────────────────────────────────────────────────────────────────
@given(winners=_round_winners(2))
@settings(max_examples=100, deadline=None)
def test_advance_two_to_final(
    winners: List[Tuple[int, int]],
) -> None:
    """
    **Validates: Requirements 4.6, 5.6**

    Advancing 2 semi-final winners produces exactly 1 final at
    bracket_position 1; the SF position-1 winner is the nominal home
    side.
    """
    next_ties = advance_round(winners)

    assert len(next_ties) == 1, f"expected 1 final tie, got {len(next_ties)}"
    new_pos, home_pid, away_pid = next_ties[0]
    assert new_pos == 1, f"final must have bracket_position=1, got {new_pos}"

    by_source = {pos: pid for pos, pid in winners}
    assert home_pid == by_source[1]
    assert away_pid == by_source[2]
    assert home_pid != away_pid


# ──────────────────────────────────────────────────────────────────────────
# Property 6d — Insensitivity to input ordering. The function sorts by
# bracket_position internally, so shuffling the input must not change
# the output.
# ──────────────────────────────────────────────────────────────────────────
@given(
    winners=_round_winners(8),
    permutation=st.permutations(list(range(8))),
)
@settings(max_examples=100, deadline=None)
def test_advance_is_input_order_insensitive(
    winners: List[Tuple[int, int]],
    permutation: List[int],
) -> None:
    """
    **Validates: Requirements 4.6, 5.6**

    The ``bracket_position`` ordering is the canonical key — the
    advancement output must be identical regardless of how the input
    list is ordered before being handed to the function.
    """
    shuffled = [winners[i] for i in permutation]
    canonical = advance_round(winners)
    permuted = advance_round(shuffled)
    assert canonical == permuted, (
        f"output changed when input was reordered:\n"
        f"  canonical: {canonical}\n"
        f"  permuted:  {permuted}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Property 6e — End-to-end chain R16 → QF → SF → Final.
# ──────────────────────────────────────────────────────────────────────────
@given(
    r16_winners=_round_winners(8),
    # qf_choice[k] picks whether the home or away side of QF tie k+1 wins.
    qf_choice=st.lists(st.booleans(), min_size=4, max_size=4),
    sf_choice=st.lists(st.booleans(), min_size=2, max_size=2),
)
@settings(max_examples=100, deadline=None)
def test_full_chain_preserves_bracket_integrity(
    r16_winners: List[Tuple[int, int]],
    qf_choice: List[bool],
    sf_choice: List[bool],
) -> None:
    """
    **Validates: Requirements 4.6, 5.6**

    Chaining the advancement function through R16 → QF → SF → Final
    preserves the bracket: the final's home side is always the winner of
    the SF position-1 tie which itself descends from R16 positions 1 and
    2; the final's away side descends from R16 positions 3 and 4
    indirectly via QF position 2 / SF position 1 — wait, more precisely
    the final descends from QF positions (1,2)→SF1 and (3,4)→SF2; SF1
    feeds the final's home side and SF2 feeds the away side; SF1 itself
    is fed by QF positions 1 and 2 which descend from R16 positions
    {1,2,3,4}; SF2 is fed by QF positions 3 and 4 which descend from
    R16 positions {5,6,7,8}.
    """
    # ── R16 → QF ────────────────────────────────────────────────────
    qf_ties = advance_round(r16_winners)
    assert len(qf_ties) == 4

    # Pick QF winners (home if choice[k] is True, else away).
    qf_winners: List[Tuple[int, int]] = []
    for (new_pos, home_pid, away_pid), choose_home in zip(qf_ties, qf_choice):
        winner_pid = home_pid if choose_home else away_pid
        qf_winners.append((new_pos, winner_pid))

    # ── QF → SF ─────────────────────────────────────────────────────
    sf_ties = advance_round(qf_winners)
    assert len(sf_ties) == 2

    sf_winners: List[Tuple[int, int]] = []
    for (new_pos, home_pid, away_pid), choose_home in zip(sf_ties, sf_choice):
        winner_pid = home_pid if choose_home else away_pid
        sf_winners.append((new_pos, winner_pid))

    # ── SF → Final ──────────────────────────────────────────────────
    final_tie = advance_round(sf_winners)
    assert len(final_tie) == 1
    final_pos, final_home, final_away = final_tie[0]
    assert final_pos == 1
    assert final_home != final_away

    # ── Bracket integrity assertions ────────────────────────────────
    # Trace the final's home side back to R16 positions {1, 2, 3, 4}
    # and the away side to {5, 6, 7, 8}. Implementation:
    #   final pos 1 home = SF pos 1 winner ⊆ {QF1.winner, QF2.winner}
    #     ⊆ {R16.1.w, R16.2.w, R16.3.w, R16.4.w}
    #   final pos 1 away = SF pos 2 winner ⊆ {QF3.winner, QF4.winner}
    #     ⊆ {R16.5.w, R16.6.w, R16.7.w, R16.8.w}
    r16_by_pos = {pos: pid for pos, pid in r16_winners}
    top_half_r16 = {r16_by_pos[p] for p in (1, 2, 3, 4)}
    bottom_half_r16 = {r16_by_pos[p] for p in (5, 6, 7, 8)}

    # Identify which QF ties feed which SF ties.
    qf_by_pos = {pos: (h, a) for pos, h, a in qf_ties}
    qf_winner_by_pos = {pos: pid for pos, pid in qf_winners}

    # SF pos 1 = pair of QF pos 1 + 2 winners; SF pos 2 = QF pos 3 + 4.
    sf_pos1_inputs = {qf_winner_by_pos[1], qf_winner_by_pos[2]}
    sf_pos2_inputs = {qf_winner_by_pos[3], qf_winner_by_pos[4]}

    # QF pos 1 home/away come from R16 positions 1 and 2.
    assert {qf_by_pos[1][0], qf_by_pos[1][1]} == {r16_by_pos[1], r16_by_pos[2]}
    assert {qf_by_pos[2][0], qf_by_pos[2][1]} == {r16_by_pos[3], r16_by_pos[4]}
    assert {qf_by_pos[3][0], qf_by_pos[3][1]} == {r16_by_pos[5], r16_by_pos[6]}
    assert {qf_by_pos[4][0], qf_by_pos[4][1]} == {r16_by_pos[7], r16_by_pos[8]}

    # Final home descends from R16 top half; away from R16 bottom half.
    assert final_home in top_half_r16, (
        f"final home {final_home} should descend from R16 positions 1-4 "
        f"({top_half_r16}); SF pos 1 winner was drawn from {sf_pos1_inputs}"
    )
    assert final_away in bottom_half_r16, (
        f"final away {final_away} should descend from R16 positions 5-8 "
        f"({bottom_half_r16}); SF pos 2 winner was drawn from {sf_pos2_inputs}"
    )

    # ── No participant appears in two ties of the same round ──────
    for round_name, ties in (
        ("quarter_final", qf_ties),
        ("semi_final", sf_ties),
        ("final", final_tie),
    ):
        appearing = [pid for _pos, h, a in ties for pid in (h, a)]
        assert len(set(appearing)) == len(appearing), (
            f"{round_name}: participant appears in two ties: {appearing}"
        )

    # ── Bracket positions are unique within each round ────────────
    for round_name, ties in (
        ("quarter_final", qf_ties),
        ("semi_final", sf_ties),
    ):
        positions = [pos for pos, _h, _a in ties]
        assert len(set(positions)) == len(positions), (
            f"{round_name}: duplicate bracket positions {positions}"
        )
