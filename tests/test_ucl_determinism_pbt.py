# Feature: uefa-champions-league, Property 12: Schedule determinism
"""
Property-based test for UCLGenerator schedule determinism.

**Validates: Requirement 10.3** — "THE UCL_Generator SHALL produce a
deterministic schedule for the same career_id, year, and seed inputs,
supporting reproducible test execution."

The two scheduling methods on `UCLGenerator` that consume randomness are
`build_swiss_pairings` (uses `self.rng.shuffle`) and
`assign_matchdays_to_dates` (currently deterministic on inputs but covered
here as a regression guard). Both are pure functions with no database
access, so we instantiate `UCLGenerator` with `session=None` and only
exercise the in-memory scheduling logic.

Properties tested:
  P12a — Two `build_swiss_pairings` calls with separate `random.Random(seed)`
         instances seeded identically produce byte-identical pairings.
  P12b — Two `assign_matchdays_to_dates` calls with separate
         `random.Random(seed)` instances and identical inputs produce
         identical date lists.
  P12c — Different seeds produce *different* Swiss pairings for at least
         one of several distinct seed pairs (sanity check, not strict —
         performed once outside the property loop).
"""

from __future__ import annotations

import random
from typing import List

from hypothesis import given, settings, strategies as st

from app.data.ucl_config import UCL_PARTICIPANTS
from app.services.ucl_generator import Participant, UCLGenerator


def _build_participants() -> List[Participant]:
    """Construct the canonical 36-participant list from UCL_PARTICIPANTS."""
    return [
        Participant(
            id=idx + 1,
            club_id=club_id,
            club_name=display_name,
            country=country,
            seed=idx + 1,
        )
        for idx, (display_name, club_id, country) in enumerate(UCL_PARTICIPANTS)
    ]


# Pre-build the 36 participants once. Participants are immutable from the
# test's point of view — `build_swiss_pairings` only reads the `id` field.
_PARTICIPANTS = _build_participants()


# ──────────────────────────────────────────────────────────────────────────
# P12a — build_swiss_pairings is deterministic for the same seed
# ──────────────────────────────────────────────────────────────────────────
@given(seed=st.integers(min_value=0, max_value=10000))
@settings(max_examples=100, deadline=None)
def test_build_swiss_pairings_is_deterministic(seed: int) -> None:
    """
    **Validates: Requirement 10.3**

    Two `build_swiss_pairings` calls seeded with `random.Random(seed)`
    produce byte-identical 8-matchday pairings.
    """
    gen_a = UCLGenerator(session=None, rng=random.Random(seed))  # type: ignore[arg-type]
    gen_b = UCLGenerator(session=None, rng=random.Random(seed))  # type: ignore[arg-type]

    pairings_a = gen_a.build_swiss_pairings(_PARTICIPANTS)
    pairings_b = gen_b.build_swiss_pairings(_PARTICIPANTS)

    assert pairings_a == pairings_b, (
        f"Swiss pairings differ for seed={seed}:\n"
        f"  A[0][:3]={pairings_a[0][:3]}\n"
        f"  B[0][:3]={pairings_b[0][:3]}"
    )

    # Structural sanity: 8 matchdays × 18 pairs each.
    assert len(pairings_a) == 8
    assert all(len(day) == 18 for day in pairings_a)


# ──────────────────────────────────────────────────────────────────────────
# P12b — assign_matchdays_to_dates is deterministic for the same seed
# ──────────────────────────────────────────────────────────────────────────
@given(seed=st.integers(min_value=0, max_value=10000))
@settings(max_examples=100, deadline=None)
def test_assign_matchdays_to_dates_is_deterministic(seed: int) -> None:
    """
    **Validates: Requirement 10.3**

    Given identical pairings, year, and `blocked_ranges`, two calls to
    `assign_matchdays_to_dates` (each with its own freshly-seeded
    `random.Random(seed)`) produce identical 8-date lists.
    """
    # First, build pairings once with a fixed seed so the input to
    # assign_matchdays_to_dates is identical across both calls.
    pairings = UCLGenerator(
        session=None,  # type: ignore[arg-type]
        rng=random.Random(seed),
    ).build_swiss_pairings(_PARTICIPANTS)

    gen_a = UCLGenerator(session=None, rng=random.Random(seed))  # type: ignore[arg-type]
    gen_b = UCLGenerator(session=None, rng=random.Random(seed))  # type: ignore[arg-type]

    dates_a = gen_a.assign_matchdays_to_dates(pairings, year=2025, blocked_ranges=[])
    dates_b = gen_b.assign_matchdays_to_dates(pairings, year=2025, blocked_ranges=[])

    assert dates_a == dates_b, (
        f"Matchday dates differ for seed={seed}:\n  A={dates_a}\n  B={dates_b}"
    )
    assert len(dates_a) == 8
    # Every assigned date must be a Tuesday (1) or Wednesday (2) per the
    # Requirement 2.5 contract that `assign_matchdays_to_dates` upholds.
    assert all(d.weekday() in (1, 2) for d in dates_a)


# ──────────────────────────────────────────────────────────────────────────
# P12c — Different seeds produce different schedules (sanity, not strict)
# ──────────────────────────────────────────────────────────────────────────
def test_different_seeds_produce_different_pairings_sanity() -> None:
    """
    Sanity check (not strict per the spec): across a handful of distinct
    seed pairs, at least one pair yields different Swiss pairings. This
    guards against an accidental constant-output regression in
    `build_swiss_pairings`.
    """
    seed_pairs = [(0, 1), (1, 2), (42, 1337), (100, 200), (10, 9999)]
    differing = 0
    for s1, s2 in seed_pairs:
        p1 = UCLGenerator(
            session=None,  # type: ignore[arg-type]
            rng=random.Random(s1),
        ).build_swiss_pairings(_PARTICIPANTS)
        p2 = UCLGenerator(
            session=None,  # type: ignore[arg-type]
            rng=random.Random(s2),
        ).build_swiss_pairings(_PARTICIPANTS)
        if p1 != p2:
            differing += 1

    assert differing >= 1, (
        f"Expected at least one of {seed_pairs} to yield different pairings, "
        f"but all {len(seed_pairs)} pairs produced identical schedules — "
        f"`build_swiss_pairings` may have lost its dependence on `self.rng`."
    )
