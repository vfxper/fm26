# Feature: uefa-champions-league, Property 8: Calendar event invariants
"""
Property-based tests for the calendar events created by ``UCLGenerator``.

Validates: Requirements 7.1, 7.2, 7.3

Universal invariant under test: every UCL ``calendar_events`` row produced
by ``generate_competition`` (and the subsequent ``finalize_league_phase``
seeding of the knockout playoff round) satisfies:

  * ``event_type='match'``
  * ``priority=8``
  * ``kick_off_time='21:00'``
  * ``is_locked=0``
  * ``is_cancelled=0``
  * ``competition_id`` is set (NOT NULL) and equals the competition that
    was just generated
  * ``event_date`` parses as a valid Tuesday/Wednesday calendar date

Additional structural invariants we can verify cheaply once both generation
phases have run:

  * exactly 144 league-phase events spread across exactly 8 distinct dates
    that match the dates returned by ``assign_matchdays_to_dates``;
  * exactly 16 knockout-playoff events spread across exactly 2 distinct
    dates that are exactly 7 days apart (Requirement 4.5 — ``leg 1`` and
    ``leg 2`` separated by 7 days), with 8 events per date.

The test spins up a fresh in-memory SQLite (via ``aiosqlite``) per
Hypothesis example, executes the relevant ``CREATE TABLE`` statements
copied from ``run_local.py`` ``create_tables()``, runs the generator, then
queries ``calendar_events WHERE competition_id = …`` and asserts the
invariants.
"""

from __future__ import annotations

import asyncio
import random
from collections import Counter
from datetime import date, timedelta
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
# Schema DDL — minimal subset of run_local.py create_tables() needed for
# the UCL generation flow. We deliberately leave FK enforcement OFF (the
# default in SQLite) so this test stays focused on the calendar-event
# invariants without policing referential integrity.
# ──────────────────────────────────────────────────────────────────────────
DDL_STATEMENTS: List[str] = [
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


# ──────────────────────────────────────────────────────────────────────────
# Async helpers
# ──────────────────────────────────────────────────────────────────────────
async def _create_schema(engine) -> None:
    async with engine.begin() as conn:
        for stmt in DDL_STATEMENTS:
            await conn.execute(text(stmt))


async def _generate_full_schedule(
    seed: int,
    year: int,
) -> Tuple[List[tuple], List[date], int]:
    """
    Spin up an in-memory SQLite, run ``generate_competition`` (which
    inserts the 144 league-phase events) and ``finalize_league_phase``
    (which inserts the 16 knockout-playoff events), then return:

      * all calendar_events rows for the new competition (as raw tuples),
      * the 8 league-phase dates returned by ``assign_matchdays_to_dates``
        — i.e. the schedule the events SHOULD land on,
      * the new ``competition_id`` (verifies the rows reference it).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        await _create_schema(engine)

        async with SessionLocal() as session:
            # Capture the expected league-phase dates by running the same
            # deterministic schedule resolver the generator uses, with the
            # SAME seed. This lets us cross-check `event_date` matches.
            preview_gen = UCLGenerator(
                session=None,  # type: ignore[arg-type]
                rng=random.Random(seed),
            )
            # Reuse the canonical 36 participants — seeds 1..36 in
            # `UCL_PARTICIPANTS` order. We only need the right shape
            # for `assign_matchdays_to_dates` (which checks length).
            preview_pairings = preview_gen.build_swiss_pairings(
                _build_preview_participants()
            )
            expected_dates = preview_gen.assign_matchdays_to_dates(
                preview_pairings, year=year, blocked_ranges=[]
            )

            # Now run the real generator — it consumes the same RNG seed
            # so the schedule should match `expected_dates`.
            generator = UCLGenerator(session=session, rng=random.Random(seed))
            competition_id = await generator.generate_competition(
                career_id=1,
                year=year,
                player_club_id=1,
            )

            # Seed deterministic standings: each participant's points =
            # 37 - seed → after `_recompute_ranks` (sort by points DESC,
            # then GD DESC, GF DESC, club_name ASC) every rank exactly
            # equals the participant's seed. Ranks 9..24 then map cleanly
            # onto the 16 knockout-playoff participants.
            await session.execute(
                text(
                    """
                    UPDATE ucl_standings
                    SET points = 37 - (
                        SELECT seed FROM ucl_participants
                        WHERE ucl_participants.id = ucl_standings.participant_id
                    )
                    WHERE competition_id = :cid
                    """
                ),
                {"cid": competition_id},
            )
            await session.commit()

            # Insert 16 knockout-playoff calendar_events.
            await generator.finalize_league_phase(
                competition_id, career_id=1, player_club_id=1
            )
            await session.commit()

            rows = await session.execute(
                text(
                    """
                    SELECT id, event_date, event_type, competition_id,
                           is_locked, priority, kick_off_time,
                           description, is_cancelled
                    FROM calendar_events
                    WHERE competition_id = :cid
                    ORDER BY event_date, id
                    """
                ),
                {"cid": competition_id},
            )
            events = list(rows.fetchall())

        return events, list(expected_dates), competition_id
    finally:
        await engine.dispose()


def _build_preview_participants():
    """Construct the canonical 36-participant list (seeds 1..36)."""
    from app.data.ucl_config import UCL_PARTICIPANTS
    from app.services.ucl_generator import Participant

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


def _classify_event(description: str) -> str:
    """
    Classify a calendar event by inspecting its description.

    Returns one of: ``"league_phase"``, ``"knockout_playoff"`` or
    ``"unknown"``. The classification keys off the round-label substrings
    produced by ``UCLGenerator._build_event_description`` for both the
    Russian (player-facing) and English (non-player) variants.
    """
    desc = description or ""
    if "тур " in desc or "Matchday " in desc:
        return "league_phase"
    if "квалификация плей-офф" in desc or "Knockout Playoff" in desc:
        return "knockout_playoff"
    return "unknown"


# ──────────────────────────────────────────────────────────────────────────
# Property 8 — Calendar event invariants
# ──────────────────────────────────────────────────────────────────────────
@given(
    seed=st.integers(min_value=0, max_value=100),
    year=st.integers(min_value=2024, max_value=2030),
)
@settings(max_examples=10, deadline=None)
def test_ucl_calendar_event_invariants(seed: int, year: int) -> None:
    """
    **Validates: Requirements 7.1, 7.2, 7.3**

    For every (seed, year) Hypothesis sample, the calendar_events rows
    produced by ``generate_competition`` + ``finalize_league_phase`` all
    satisfy the per-row invariants (event_type, priority, kick_off_time,
    is_locked, is_cancelled, competition_id, valid event_date), and the
    aggregate structural invariants (144 league-phase events on the 8
    matchday dates, 16 knockout-playoff events on 2 dates exactly 7 days
    apart).
    """
    events, expected_league_dates, competition_id = asyncio.run(
        _generate_full_schedule(seed, year)
    )

    # Total: 144 league-phase + 16 knockout playoff = 160 UCL events.
    assert len(events) == 160, (
        f"Expected 160 UCL calendar events, got {len(events)} "
        f"(seed={seed}, year={year})"
    )

    league_dates: List[date] = []
    knockout_dates: List[date] = []

    for ev in events:
        (
            ev_id,
            event_date_s,
            event_type,
            ev_comp_id,
            is_locked,
            priority,
            kick_off_time,
            description,
            is_cancelled,
        ) = ev

        # ── Per-row invariants (Requirements 7.1, 7.2, 7.3) ───────────
        assert event_type == "match", (
            f"event {ev_id}: event_type={event_type!r}, expected 'match'"
        )
        assert priority == 8, (
            f"event {ev_id}: priority={priority}, expected 8"
        )
        assert kick_off_time == "21:00", (
            f"event {ev_id}: kick_off_time={kick_off_time!r}, expected '21:00'"
        )
        # SQLite returns 0/1 for BOOLEAN; accept both forms.
        assert is_locked in (0, False), (
            f"event {ev_id}: is_locked={is_locked!r}, expected 0/False"
        )
        assert is_cancelled in (0, False), (
            f"event {ev_id}: is_cancelled={is_cancelled!r}, expected 0/False"
        )
        assert ev_comp_id == competition_id, (
            f"event {ev_id}: competition_id={ev_comp_id}, "
            f"expected {competition_id}"
        )

        # event_date is a valid YYYY-MM-DD date on Tuesday or Wednesday.
        try:
            d = date.fromisoformat(str(event_date_s))
        except (TypeError, ValueError) as exc:
            pytest.fail(
                f"event {ev_id}: invalid event_date={event_date_s!r}: {exc}"
            )
        assert d.weekday() in (1, 2), (
            f"event {ev_id}: {d} is {d.strftime('%A')}, expected Tue/Wed"
        )

        # Bucket by round for the structural assertions below.
        kind = _classify_event(description)
        if kind == "league_phase":
            league_dates.append(d)
        elif kind == "knockout_playoff":
            knockout_dates.append(d)
        else:
            pytest.fail(
                f"event {ev_id}: description {description!r} did not match any "
                f"expected UCL round label"
            )

    # ── League phase: 144 events on the 8 expected matchday dates ───
    assert len(league_dates) == 144, (
        f"Expected 144 league-phase events, got {len(league_dates)}"
    )
    distinct_league_dates = sorted(set(league_dates))
    assert len(distinct_league_dates) == 8, (
        f"Expected 8 distinct league-phase dates, got {distinct_league_dates}"
    )
    expected_sorted = sorted(expected_league_dates)
    assert distinct_league_dates == expected_sorted, (
        f"League-phase event_dates do not match assign_matchdays_to_dates "
        f"output:\n  events: {distinct_league_dates}\n  expected: "
        f"{expected_sorted}"
    )
    league_counts = Counter(league_dates)
    for d, n in league_counts.items():
        assert n == 18, (
            f"League-phase date {d} has {n} events, expected 18 "
            f"(36 participants ÷ 2)"
        )

    # ── Knockout playoff: 16 events on 2 dates exactly 7 days apart ─
    assert len(knockout_dates) == 16, (
        f"Expected 16 knockout-playoff events, got {len(knockout_dates)}"
    )
    distinct_ko_dates = sorted(set(knockout_dates))
    assert len(distinct_ko_dates) == 2, (
        f"Expected exactly 2 knockout-playoff dates, got {distinct_ko_dates}"
    )
    leg1_date, leg2_date = distinct_ko_dates
    assert (leg2_date - leg1_date) == timedelta(days=7), (
        f"Knockout-playoff legs must be exactly 7 days apart, "
        f"got leg1={leg1_date}, leg2={leg2_date} "
        f"(diff={leg2_date - leg1_date})"
    )
    ko_counts = Counter(knockout_dates)
    assert ko_counts[leg1_date] == 8, (
        f"Knockout playoff leg-1 date {leg1_date} has "
        f"{ko_counts[leg1_date]} events, expected 8 (one per tie)"
    )
    assert ko_counts[leg2_date] == 8, (
        f"Knockout playoff leg-2 date {leg2_date} has "
        f"{ko_counts[leg2_date]} events, expected 8 (one per tie)"
    )
