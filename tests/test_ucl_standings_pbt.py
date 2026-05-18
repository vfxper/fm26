# Feature: uefa-champions-league, Property 3: Standings consistency
"""
Property-based tests for ``UCLGenerator.update_standing`` and
``UCLGenerator.get_league_phase_table``.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

For any random sequence of league-phase match results applied through
``update_standing``, the following invariants SHALL hold across the 36
``ucl_standings`` rows:

  * Per-row arithmetic:
      - ``played == won + drawn + lost``
      - ``points == 3 * won + drawn``
      - ``goal_difference == goals_for - goals_against``
  * Cross-row totals:
      - ``Σ goals_for == Σ goals_against``  (every goal is also conceded)
      - ``Σ played == 2 * n_matches``       (each match counts for two clubs)
  * Ranking (Requirement 3.4 / 3.5):
      - Ranks 1..36 are assigned without duplicates.
      - ``get_league_phase_table`` returns rows ordered by
        ``(points DESC, goal_difference DESC, goals_for DESC, club_name ASC)``.

The test wires up a fresh in-memory SQLite database per Hypothesis example
via ``aiosqlite``, generates the full UCL competition shell with
``UCLGenerator.generate_competition`` (36 participants, 36 standings, 144
league-phase calendar events), then deterministically applies
``n_matches`` randomly-chosen match results via ``update_standing`` and
asserts every invariant on the resulting standings table.

Each Hypothesis example owns its own engine, so cases are fully isolated.
The DB-backed setup is slower than pure in-memory PBT, hence
``max_examples=20``.
"""

from __future__ import annotations

import asyncio
import random
from typing import List, Tuple

import pytest
from hypothesis import given, settings, strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.services.ucl_generator import UCLGenerator


# ──────────────────────────────────────────────────────────────────────────
# Minimal schema for the tables touched by UCLGenerator. Mirrors the
# definitions in ``run_local.py:create_tables()`` for the four UCL tables
# plus ``competitions`` and ``calendar_events``. Foreign keys are declared
# but SQLite does not enforce them by default — that suits the test, which
# never creates orphaned rows anyway.
# ──────────────────────────────────────────────────────────────────────────
_SCHEMA_SQL: List[str] = [
    """
    CREATE TABLE competitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        competition_type TEXT DEFAULT 'league',
        season INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        created_at TEXT
    )
    """,
    """
    CREATE TABLE competition_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        round_type TEXT NOT NULL,
        round_order INTEGER NOT NULL,
        start_date TEXT,
        end_date TEXT,
        is_completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE ucl_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        club_id INTEGER,
        club_name TEXT NOT NULL,
        country TEXT NOT NULL,
        seed INTEGER NOT NULL,
        final_rank INTEGER
    )
    """,
    """
    CREATE TABLE ucl_standings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        participant_id INTEGER NOT NULL,
        played INTEGER NOT NULL DEFAULT 0,
        won INTEGER NOT NULL DEFAULT 0,
        drawn INTEGER NOT NULL DEFAULT 0,
        lost INTEGER NOT NULL DEFAULT 0,
        goals_for INTEGER NOT NULL DEFAULT 0,
        goals_against INTEGER NOT NULL DEFAULT 0,
        goal_difference INTEGER NOT NULL DEFAULT 0,
        points INTEGER NOT NULL DEFAULT 0,
        rank INTEGER
    )
    """,
    """
    CREATE TABLE ucl_ties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        round_id INTEGER NOT NULL,
        home_participant_id INTEGER,
        away_participant_id INTEGER,
        leg1_home_score INTEGER,
        leg1_away_score INTEGER,
        leg2_home_score INTEGER,
        leg2_away_score INTEGER,
        aggregate_home INTEGER,
        aggregate_away INTEGER,
        winner_participant_id INTEGER,
        winner_decided_by TEXT,
        bracket_position INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        career_id INTEGER,
        event_date TEXT,
        event_type TEXT,
        competition_id INTEGER,
        home_club_id INTEGER,
        away_club_id INTEGER,
        is_locked INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 5,
        kick_off_time TEXT,
        description TEXT,
        is_cancelled INTEGER DEFAULT 0
    )
    """,
]


async def _setup_database() -> Tuple:
    """Create an in-memory SQLite engine + session-factory for one example."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        for ddl in _SCHEMA_SQL:
            await conn.execute(text(ddl))
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_factory


async def _list_participant_ids(session: AsyncSession, competition_id: int) -> List[int]:
    rows = await session.execute(
        text(
            "SELECT id FROM ucl_participants "
            "WHERE competition_id = :cid ORDER BY seed ASC"
        ),
        {"cid": competition_id},
    )
    return [int(r[0]) for r in rows.fetchall()]


async def _run_property_check(
    n_matches: int,
    seed: int,
    scores: List[Tuple[int, int]],
) -> None:
    """
    Set up a fresh DB, generate the UCL competition, apply ``n_matches``
    random results, and assert every Property 3 invariant.
    """
    engine, session_factory = await _setup_database()
    try:
        async with session_factory() as session:
            generator = UCLGenerator(session, rng=random.Random(seed))
            # career_id=1, year=2025, no player club so we don't trigger
            # the locked-date lookup branch.
            competition_id = await generator.generate_competition(
                career_id=1,
                year=2025,
                player_club_id=None,
            )
            participant_ids = await _list_participant_ids(session, competition_id)
            assert len(participant_ids) == 36, (
                f"Expected 36 participants, got {len(participant_ids)}"
            )

            # Pick deterministic match-up sequence using a separate
            # `random.Random` so the choices are independent of any RNG
            # state consumed by `generate_competition`.
            picker = random.Random(seed ^ 0xA5A5)
            for i in range(n_matches):
                home_pid, away_pid = picker.sample(participant_ids, 2)
                home_score, away_score = scores[i]
                await generator.update_standing(
                    competition_id=competition_id,
                    home_participant_id=home_pid,
                    away_participant_id=away_pid,
                    home_score=home_score,
                    away_score=away_score,
                )
            await session.commit()

            # ── Read back the full standings table ──────────────────
            table = await generator.get_league_phase_table(competition_id)
            assert len(table) == 36, f"Expected 36 standings rows, got {len(table)}"

            # ── Per-row arithmetic invariants ───────────────────────
            for row in table:
                assert row.played == row.won + row.drawn + row.lost, (
                    f"played != won + drawn + lost for participant_id="
                    f"{row.participant_id}: played={row.played}, "
                    f"won={row.won}, drawn={row.drawn}, lost={row.lost}"
                )
                assert row.points == 3 * row.won + row.drawn, (
                    f"points != 3*won + drawn for participant_id="
                    f"{row.participant_id}: points={row.points}, "
                    f"won={row.won}, drawn={row.drawn}"
                )
                assert row.goal_difference == row.goals_for - row.goals_against, (
                    f"goal_difference != goals_for - goals_against for "
                    f"participant_id={row.participant_id}: "
                    f"gd={row.goal_difference}, gf={row.goals_for}, "
                    f"ga={row.goals_against}"
                )

            # ── Cross-row totals ────────────────────────────────────
            total_gf = sum(r.goals_for for r in table)
            total_ga = sum(r.goals_against for r in table)
            assert total_gf == total_ga, (
                f"Σ goals_for ({total_gf}) != Σ goals_against ({total_ga}); "
                f"every goal scored must also be conceded somewhere"
            )

            total_played = sum(r.played for r in table)
            assert total_played == 2 * n_matches, (
                f"Σ played ({total_played}) != 2 * n_matches "
                f"({2 * n_matches}); each match must contribute one "
                f"appearance to each of the two participating clubs"
            )

            expected_total_pts = sum(r.points for r in table)
            # Each match awards 3 points (decisive) or 2 points (draw)
            # in total. We validate that the per-row sum equals the
            # match-by-match expected total.
            match_pts = 0
            for h, a in scores[:n_matches]:
                match_pts += 3 if h != a else 2
            assert expected_total_pts == match_pts, (
                f"Σ points ({expected_total_pts}) != expected total "
                f"({match_pts}) computed from match outcomes"
            )

            # ── Ranking invariants (Req 3.4, 3.5) ──────────────────
            ranks = [r.rank for r in table]
            assert sorted(ranks) == list(range(1, 37)), (
                f"Ranks are not 1..36 without duplicates: {ranks}"
            )
            # The order returned by get_league_phase_table is the
            # canonical sort order, so rank should equal index+1.
            for idx, row in enumerate(table, start=1):
                assert row.rank == idx, (
                    f"row at index {idx} has rank {row.rank}; "
                    f"get_league_phase_table must return rows in rank order"
                )
            # Sort order is (points DESC, goal_difference DESC,
            # goals_for DESC, club_name ASC).
            for i in range(1, len(table)):
                a = table[i - 1]
                b = table[i]
                a_key = (-a.points, -a.goal_difference, -a.goals_for, a.club_name)
                b_key = (-b.points, -b.goal_difference, -b.goals_for, b.club_name)
                assert a_key <= b_key, (
                    f"Rows not in canonical sort order at index {i}: "
                    f"prev=(pts={a.points}, gd={a.goal_difference}, "
                    f"gf={a.goals_for}, name={a.club_name!r}) vs "
                    f"curr=(pts={b.points}, gd={b.goal_difference}, "
                    f"gf={b.goals_for}, name={b.club_name!r})"
                )
    finally:
        await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────
# Hypothesis composite strategy: a list of (home_score, away_score) tuples
# whose length is the number of matches to simulate. Sizes are bounded to
# keep DB-backed runs reasonably fast (max_examples=20 amplifies cost).
# ──────────────────────────────────────────────────────────────────────────
@st.composite
def _matches_strategy(draw):
    n = draw(st.integers(min_value=0, max_value=50))
    return [
        (
            draw(st.integers(min_value=0, max_value=5)),
            draw(st.integers(min_value=0, max_value=5)),
        )
        for _ in range(n)
    ]


@given(
    seed=st.integers(min_value=0, max_value=1000),
    scores=_matches_strategy(),
)
@settings(max_examples=20, deadline=None)
def test_property3_standings_consistency(seed: int, scores: List[Tuple[int, int]]) -> None:
    """
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

    For all (seed, scores) combinations, applying the score sequence via
    ``update_standing`` preserves every per-row, cross-row, and ranking
    invariant required of the league-phase standings table.
    """
    n_matches = len(scores)
    asyncio.run(_run_property_check(n_matches=n_matches, seed=seed, scores=scores))
