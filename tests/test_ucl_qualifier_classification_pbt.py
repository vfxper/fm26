# Feature: uefa-champions-league, Property 4: Qualifier classification by rank
"""
Property-based test for the post-league-phase qualifier classification.

**Validates: Requirements 4.1, 4.2, 4.3**

After the league phase, every UCL participant falls into exactly one of
three buckets based on their final rank (1..36):

  * ranks 1-8   -> direct qualifiers to the Round of 16
  * ranks 9-24  -> Knockout Playoff participants
  * ranks 25-36 -> eliminated

The bucketing is performed inside ``UCLGenerator.finalize_league_phase``
via SQL ``WHERE rank BETWEEN ...`` clauses and is therefore not exposed
as a pure helper. Per the task guidelines, this test mirrors the
specification rules in a small in-test helper (``classify_by_rank``) and
asserts the partitioning invariants on randomly generated rank arrays.

Properties checked on every example:
  1. Each bucket has the exact expected size (8, 16, 12).
  2. The buckets are pairwise disjoint.
  3. The union of the three buckets is exactly {1..36} (exhaustive).
  4. Every individual rank in 1..36 maps to its expected bucket
     according to the cut-offs in Requirements 4.1 / 4.2 / 4.3.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from hypothesis import given, settings, strategies as st


# ──────────────────────────────────────────────────────────────────────
# In-test helper mirroring the spec's bucketing rules.
# Equivalent to the SQL clauses inside finalize_league_phase /
# build_round_of_16 in app/services/ucl_generator.py.
# ──────────────────────────────────────────────────────────────────────
DIRECT = "direct_to_r16"
PLAYOFF = "knockout_playoff"
ELIMINATED = "eliminated"


def classify_by_rank(rank: int) -> str:
    """Return the bucket name for a given final rank (1..36)."""
    if 1 <= rank <= 8:
        return DIRECT
    if 9 <= rank <= 24:
        return PLAYOFF
    if 25 <= rank <= 36:
        return ELIMINATED
    raise ValueError(f"rank out of range: {rank}")


def partition_ranks(
    rank_by_participant: Dict[int, int],
) -> Tuple[List[int], List[int], List[int]]:
    """Split a {participant_id -> rank} mapping into the three UCL buckets."""
    direct: List[int] = []
    playoff: List[int] = []
    eliminated: List[int] = []
    for pid, rank in rank_by_participant.items():
        bucket = classify_by_rank(rank)
        if bucket == DIRECT:
            direct.append(pid)
        elif bucket == PLAYOFF:
            playoff.append(pid)
        else:
            eliminated.append(pid)
    return direct, playoff, eliminated


# ──────────────────────────────────────────────────────────────────────
# Hypothesis strategy: a permutation of ranks 1..36 assigned to
# participant ids 1..36. We build it as `st.lists(...).map(...)` then
# materialise it as a {pid -> rank} dict.
# ──────────────────────────────────────────────────────────────────────
def _ranks_strategy() -> st.SearchStrategy[Dict[int, int]]:
    return st.permutations(list(range(1, 37))).map(
        lambda perm: {pid: perm[pid - 1] for pid in range(1, 37)}
    )


# ──────────────────────────────────────────────────────────────────────
# Property 4 — qualifier classification by rank
# ──────────────────────────────────────────────────────────────────────
@given(rank_by_participant=_ranks_strategy())
@settings(max_examples=100, deadline=None)
def test_qualifier_classification_by_rank(
    rank_by_participant: Dict[int, int],
) -> None:
    """**Validates: Requirements 4.1, 4.2, 4.3**

    For any permutation of ranks 1..36 assigned to 36 participants,
    classifying each participant by rank produces three buckets that
    are exhaustive, disjoint, and of the expected sizes (8 / 16 / 12).
    """
    direct, playoff, eliminated = partition_ranks(rank_by_participant)

    # 1. Bucket sizes match the spec cut-offs.
    assert len(direct) == 8, (
        f"expected 8 direct qualifiers (Req 4.1), got {len(direct)}"
    )
    assert len(playoff) == 16, (
        f"expected 16 playoff participants (Req 4.2), got {len(playoff)}"
    )
    assert len(eliminated) == 12, (
        f"expected 12 eliminated clubs (Req 4.3), got {len(eliminated)}"
    )

    # 2. The three buckets are pairwise disjoint.
    s_direct = set(direct)
    s_playoff = set(playoff)
    s_eliminated = set(eliminated)
    assert s_direct.isdisjoint(s_playoff), (
        f"direct & playoff overlap: {s_direct & s_playoff}"
    )
    assert s_direct.isdisjoint(s_eliminated), (
        f"direct & eliminated overlap: {s_direct & s_eliminated}"
    )
    assert s_playoff.isdisjoint(s_eliminated), (
        f"playoff & eliminated overlap: {s_playoff & s_eliminated}"
    )

    # 3. Exhaustive: union covers exactly the 36 participants.
    union = s_direct | s_playoff | s_eliminated
    assert union == set(range(1, 37)), (
        f"buckets do not cover all 36 participants; missing: "
        f"{set(range(1, 37)) - union}, extra: {union - set(range(1, 37))}"
    )

    # 4. Each participant in a bucket has the expected rank range.
    for pid in direct:
        rank = rank_by_participant[pid]
        assert 1 <= rank <= 8, (
            f"direct qualifier {pid} has rank {rank}, expected 1..8 (Req 4.1)"
        )
    for pid in playoff:
        rank = rank_by_participant[pid]
        assert 9 <= rank <= 24, (
            f"playoff participant {pid} has rank {rank}, expected 9..24 (Req 4.2)"
        )
    for pid in eliminated:
        rank = rank_by_participant[pid]
        assert 25 <= rank <= 36, (
            f"eliminated participant {pid} has rank {rank}, expected 25..36 (Req 4.3)"
        )

    # 5. Every rank 1..36 falls into exactly one bucket — i.e. the
    # union of ranks (rather than participant ids) is also exhaustive.
    rank_union = (
        {rank_by_participant[pid] for pid in direct}
        | {rank_by_participant[pid] for pid in playoff}
        | {rank_by_participant[pid] for pid in eliminated}
    )
    assert rank_union == set(range(1, 37)), (
        f"ranks do not cover 1..36 exhaustively; missing: "
        f"{set(range(1, 37)) - rank_union}"
    )


# ──────────────────────────────────────────────────────────────────────
# Property 4 (boundary check) — bucket cut-offs are sharp.
# Verifies the boundary ranks (8/9, 24/25) classify into the correct
# bucket, locking in Requirements 4.1, 4.2, 4.3 against off-by-one
# regressions in the helper or in any future re-implementation.
# ──────────────────────────────────────────────────────────────────────
@given(rank=st.integers(min_value=1, max_value=36))
@settings(max_examples=100, deadline=None)
def test_classify_by_rank_individual(rank: int) -> None:
    """**Validates: Requirements 4.1, 4.2, 4.3**

    Per-rank classification matches the spec cut-offs exactly:
    1..8 -> direct, 9..24 -> playoff, 25..36 -> eliminated.
    """
    bucket = classify_by_rank(rank)
    if rank <= 8:
        assert bucket == DIRECT, f"rank {rank} -> {bucket}, expected {DIRECT}"
    elif rank <= 24:
        assert bucket == PLAYOFF, f"rank {rank} -> {bucket}, expected {PLAYOFF}"
    else:
        assert bucket == ELIMINATED, (
            f"rank {rank} -> {bucket}, expected {ELIMINATED}"
        )
