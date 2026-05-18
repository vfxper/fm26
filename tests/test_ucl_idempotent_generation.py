# Feature: uefa-champions-league, Unit test for idempotent generation
"""
Unit test for ``UCLGenerator.generate_competition`` idempotency.

**Validates: Requirement 10.4**

Calling ``generate_competition`` a second time for the same
``(career_id, year)`` SHALL be a no-op: it must NOT create a duplicate
``competitions`` row, MUST return the existing ``competition_id``, and MUST
leave the dependent tables (``ucl_participants``, ``ucl_standings``,
``competition_rounds``) at their original row counts.

The test wires up a fresh in-memory SQLite database (via ``aiosqlite``),
runs ``generate_competition`` twice with identical inputs, and asserts:

  * Only one ``competitions`` row exists with
    ``name='Champions League'`` and ``season=2025``.
  * The same ``competition_id`` is returned by both calls.
  * ``ucl_participants``       has 36 rows and is unchanged after call 2.
  * ``ucl_standings``          has 36 rows and is unchanged after call 2.
  * ``competition_rounds``     has  6 rows and is unchanged after call 2.

Schema setup follows the DDL pattern used in
``tests/test_ucl_calendar_event_invariants_pbt.py`` and
``tests/test_ucl_standings_pbt.py``.
"""

from __future__ import annotations

import random
from typing import List

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.services.ucl_generator import UCLGenerator


# ──────────────────────────────────────────────────────────────────────────
# Minimal schema for the tables touched by ``generate_competition``.
# Mirrors the definitions in ``run_local.py:create_tables()``. Foreign keys
# are declared but SQLite does not enforce them by default — that is fine
# here because the test never creates orphaned rows.
# ──────────────────────────────────────────────────────────────────────────
_SCHEMA_SQL: List[str] = [
    """
    CREATE TABLE competitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255),
        competition_type VARCHAR(50) DEFAULT 'league',
        season INTEGER DEFAULT 1,
        status VARCHAR(20) DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        career_id INTEGER,
        event_date VARCHAR(10),
        event_type VARCHAR(30),
        competition_id INTEGER,
        home_club_id INTEGER,
        away_club_id INTEGER,
        is_locked BOOLEAN DEFAULT 0,
        priority INTEGER DEFAULT 5,
        kick_off_time VARCHAR(5),
        weather_data TEXT,
        description TEXT,
        travel_data TEXT,
        original_date VARCHAR(10),
        reschedule_reason VARCHAR(255),
        is_cancelled BOOLEAN DEFAULT 0,
        template_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE competition_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        round_type VARCHAR(30) NOT NULL,
        round_order INTEGER NOT NULL,
        start_date DATE,
        end_date DATE,
        is_completed BOOLEAN DEFAULT 0 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE ucl_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        club_id INTEGER,
        club_name VARCHAR(100) NOT NULL,
        country VARCHAR(50) NOT NULL,
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
        winner_decided_by VARCHAR(20),
        bracket_position INTEGER NOT NULL
    )
    """,
]


async def _setup_database():
    """Create an in-memory SQLite engine + session factory for one test."""
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


async def _count(session: AsyncSession, sql: str, **params) -> int:
    row = await session.execute(text(sql), params)
    return int(row.scalar() or 0)


@pytest.mark.asyncio
async def test_generate_competition_is_idempotent() -> None:
    """
    **Validates: Requirement 10.4**

    Calling ``generate_competition(career_id=1, year=2025, player_club_id=1)``
    twice MUST:

      * Return the same ``competition_id`` both times.
      * Leave exactly one ``competitions`` row with
        ``name='Champions League'`` and ``season=2025``.
      * Leave dependent tables unchanged at their original row counts:
          - ``ucl_participants``     == 36
          - ``ucl_standings``        == 36
          - ``competition_rounds``   ==  6
    """
    engine, session_factory = await _setup_database()
    try:
        async with session_factory() as session:
            # Use a deterministic RNG so the two calls would produce the
            # same schedule if either ever ran twice — that way any
            # behavioural difference signals a real idempotency bug rather
            # than RNG drift.
            generator_first = UCLGenerator(session, rng=random.Random(42))
            first_id = await generator_first.generate_competition(
                career_id=1,
                year=2025,
                player_club_id=1,
            )

            # Snapshot dependent-table row counts after the first call.
            participants_before = await _count(
                session,
                "SELECT COUNT(*) FROM ucl_participants WHERE competition_id = :cid",
                cid=first_id,
            )
            standings_before = await _count(
                session,
                "SELECT COUNT(*) FROM ucl_standings WHERE competition_id = :cid",
                cid=first_id,
            )
            rounds_before = await _count(
                session,
                "SELECT COUNT(*) FROM competition_rounds WHERE competition_id = :cid",
                cid=first_id,
            )
            calendar_events_before = await _count(
                session,
                "SELECT COUNT(*) FROM calendar_events WHERE competition_id = :cid",
                cid=first_id,
            )

            assert participants_before == 36, (
                f"Expected 36 ucl_participants rows after first call, "
                f"got {participants_before}"
            )
            assert standings_before == 36, (
                f"Expected 36 ucl_standings rows after first call, "
                f"got {standings_before}"
            )
            assert rounds_before == 6, (
                f"Expected 6 competition_rounds rows after first call, "
                f"got {rounds_before}"
            )

            # Second call with identical inputs — fresh generator instance
            # to mirror how `careers.py` constructs UCLGenerator per call.
            generator_second = UCLGenerator(session, rng=random.Random(42))
            second_id = await generator_second.generate_competition(
                career_id=1,
                year=2025,
                player_club_id=1,
            )

            # ── Assertion 1: same competition_id returned ─────────────
            assert second_id == first_id, (
                f"generate_competition is not idempotent: returned "
                f"{second_id} on the second call but {first_id} on the first"
            )

            # ── Assertion 2: exactly one competitions row ─────────────
            comp_count = await _count(
                session,
                """
                SELECT COUNT(*) FROM competitions
                WHERE name = :name AND season = :season
                """,
                name="Champions League",
                season=2025,
            )
            assert comp_count == 1, (
                f"Expected exactly 1 competitions row for "
                f"(name='Champions League', season=2025), got {comp_count}"
            )

            # ── Assertion 3: dependent table counts unchanged ─────────
            participants_after = await _count(
                session,
                "SELECT COUNT(*) FROM ucl_participants WHERE competition_id = :cid",
                cid=first_id,
            )
            standings_after = await _count(
                session,
                "SELECT COUNT(*) FROM ucl_standings WHERE competition_id = :cid",
                cid=first_id,
            )
            rounds_after = await _count(
                session,
                "SELECT COUNT(*) FROM competition_rounds WHERE competition_id = :cid",
                cid=first_id,
            )
            calendar_events_after = await _count(
                session,
                "SELECT COUNT(*) FROM calendar_events WHERE competition_id = :cid",
                cid=first_id,
            )

            assert participants_after == participants_before == 36, (
                f"ucl_participants row count changed after second call: "
                f"before={participants_before}, after={participants_after}"
            )
            assert standings_after == standings_before == 36, (
                f"ucl_standings row count changed after second call: "
                f"before={standings_before}, after={standings_after}"
            )
            assert rounds_after == rounds_before == 6, (
                f"competition_rounds row count changed after second call: "
                f"before={rounds_before}, after={rounds_after}"
            )
            # Calendar events for the league phase should also be stable;
            # this is a stricter sanity check beyond the task's named
            # assertions but keeps the idempotency guarantee end-to-end.
            assert calendar_events_after == calendar_events_before, (
                f"calendar_events row count for competition_id={first_id} "
                f"changed after second call: before={calendar_events_before}, "
                f"after={calendar_events_after}"
            )
    finally:
        await engine.dispose()
