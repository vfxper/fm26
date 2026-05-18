# Feature: friendly-matches, Property 7: Friendly creation round-trip preserves request data
"""
Property-based test for ``FriendlyMatchService.create_friendly``.

**Validates: Requirements 4.3, 6.1, 6.8, 11.1, 11.2, 11.3, 11.4, 13.3**

Universal round-trip property under test: for every valid
``FriendlyCreateRequest`` Hypothesis can synthesise, calling
``FriendlyMatchService.create_friendly(career_id, request)`` writes exactly
one row into ``calendar_events`` whose stored fields agree with the request
and the resolved match-type mapping.

Specifically, the persisted row satisfies:

  * ``event_type='match'``                            (Req 6.1, 11.3)
  * ``priority=2``                                    (Req 6.1, 11.2)
  * ``is_locked=0``                                   (Req 6.1)
  * ``is_cancelled=0``                                (Req 6.1)
  * ``event_date == request.event_date``              (Req 6.1, 6.8)
  * ``kick_off_time == request.kick_off_time``        (Req 6.1, 13.3)
  * ``description`` starts with the documented
    ``"Товарищеский матч: <home> – <away>"`` prefix   (Req 6.8)
  * ``travel_data`` JSON-decodes back to the dict the
    service exposes via :class:`FriendlyCreateResult`  (Req 4.3, 6.8)
  * ``home_club_id`` and ``away_club_id`` reflect the
    match-type mapping (``away`` swaps the player and
    the opponent; everything else keeps the player home) (Req 11.1, 11.4)

The test spins up a fresh in-memory SQLite (via ``aiosqlite``) per
Hypothesis example, executes the minimal ``CREATE TABLE`` statements
required by the service (``careers`` + ``calendar_events`` — copied from
``run_local.py`` and the existing UCL DB-backed test), pre-seeds a
``careers`` row plus a single non-cancelled ``calendar_events`` row that
fixes the season window so the ``_resolve_season_window`` helper has
deterministic bounds, then exercises the full ``create_friendly`` flow.
"""

from __future__ import annotations

import asyncio
import json
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

from app.data.club_budgets import CLUBS
from app.services.friendly_match_service import (
    FriendlyCreateRequest,
    FriendlyMatchService,
)


# ──────────────────────────────────────────────────────────────────────────
# Schema DDL — minimal subset of run_local.py create_tables() needed for
# the FriendlyMatchService.create_friendly flow. We deliberately leave FK
# enforcement OFF so this test stays focused on the round-trip invariant.
# ──────────────────────────────────────────────────────────────────────────
DDL_STATEMENTS: List[str] = [
    """
    CREATE TABLE careers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        club_id INTEGER,
        manager_name VARCHAR(100),
        current_season INTEGER DEFAULT 1,
        current_week INTEGER DEFAULT 1
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
]


# ──────────────────────────────────────────────────────────────────────────
# Constants for the Hypothesis-generated scenarios
# ──────────────────────────────────────────────────────────────────────────

# A small, deterministic season window. The pre-seeded sentinel events at
# SEASON_START / SEASON_END frame ``_resolve_season_window``; the friendly
# is scheduled within (SEASON_START + 30, SEASON_END - 30) so we never trip
# the window-validation rule from Requirement 5.1.
SEASON_START = date(2025, 7, 15)
SEASON_END = date(2026, 6, 14)

# Player's career id and club id are fixed; opponents are drawn from a
# small, valid 1-based range that excludes the player's club.
PLAYER_CAREER_ID = 1
PLAYER_CLUB_ID = 1
# CLUBS[0] is "Manchester City" → id=1 belongs to the player.
# Opponent ids 2..MAX_OPPONENT_ID stay well within ``len(CLUBS)``.
MAX_OPPONENT_ID = 8


# ──────────────────────────────────────────────────────────────────────────
# Async helpers
# ──────────────────────────────────────────────────────────────────────────


async def _create_schema(engine) -> None:
    async with engine.begin() as conn:
        for stmt in DDL_STATEMENTS:
            await conn.execute(text(stmt))


async def _seed_career_and_window(session: AsyncSession) -> None:
    """Insert one ``careers`` row and two sentinel ``calendar_events`` rows
    that pin the season window to ``[SEASON_START, SEASON_END]``.

    The sentinel events are training rows (priority 3, ``is_locked=False``)
    placed on SEASON_START and SEASON_END exactly. They are far enough from
    the friendly's ±2-day conflict window (the friendly date is bracketed
    well inside the season) that ``_check_conflicts`` never sees them.
    """
    await session.execute(
        text(
            "INSERT INTO careers (id, user_id, club_id, manager_name) "
            "VALUES (:id, 1, :club_id, 'Test Manager')"
        ),
        {"id": PLAYER_CAREER_ID, "club_id": PLAYER_CLUB_ID},
    )
    for sentinel_date in (SEASON_START, SEASON_END):
        await session.execute(
            text(
                """
                INSERT INTO calendar_events
                (career_id, event_date, event_type, priority,
                 is_locked, is_cancelled, description)
                VALUES
                (:cid, :ed, 'training', 3, 0, 0, 'season-window sentinel')
                """
            ),
            {"cid": PLAYER_CAREER_ID, "ed": str(sentinel_date)},
        )
    await session.commit()


async def _create_friendly_and_read_back(
    request: FriendlyCreateRequest,
) -> Tuple[dict, dict]:
    """Spin up an in-memory SQLite, create one friendly via the service,
    and return ``(result_dict, db_row_dict)`` for assertion in the caller.

    ``result_dict`` is a plain ``dict`` view of the
    :class:`FriendlyCreateResult` so we can compare it against the
    persisted row without crossing the engine boundary.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        await _create_schema(engine)

        async with SessionLocal() as session:
            await _seed_career_and_window(session)

            service = FriendlyMatchService(session=session)
            result = await service.create_friendly(PLAYER_CAREER_ID, request)

            row = await session.execute(
                text(
                    """
                    SELECT id, career_id, event_date, event_type, priority,
                           is_locked, is_cancelled, kick_off_time,
                           home_club_id, away_club_id, description,
                           travel_data
                    FROM calendar_events
                    WHERE id = :eid
                    """
                ),
                {"eid": result.event_id},
            )
            r = row.fetchone()
            assert r is not None, (
                f"calendar_events row id={result.event_id} was not persisted"
            )
            db_row = {
                "id": int(r[0]),
                "career_id": int(r[1]),
                "event_date": str(r[2]),
                "event_type": r[3],
                "priority": int(r[4]),
                "is_locked": int(r[5]),
                "is_cancelled": int(r[6]),
                "kick_off_time": r[7],
                "home_club_id": int(r[8]),
                "away_club_id": int(r[9]),
                "description": r[10],
                "travel_data_raw": r[11],
            }

            result_dict = {
                "event_id": result.event_id,
                "event_date": result.event_date,
                "kick_off_time": result.kick_off_time,
                "home_club_id": result.home_club_id,
                "away_club_id": result.away_club_id,
                "description": result.description,
                "travel_data": result.travel_data,
            }
        return result_dict, db_row
    finally:
        await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────
# Hypothesis strategies
# ──────────────────────────────────────────────────────────────────────────

# Friendly date strategy: any day inside the season, but at least 5 days
# away from the sentinel events at SEASON_START / SEASON_END. The 5-day
# buffer keeps us out of the ±2-day conflict-check radius.
_friendly_date_strategy = st.dates(
    min_value=SEASON_START + timedelta(days=5),
    max_value=SEASON_END - timedelta(days=5),
)

# Kick-off times: any valid HH:MM string accepted by KICK_OFF_REGEX.
_kick_off_strategy = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    st.integers(min_value=0, max_value=23),
    st.integers(min_value=0, max_value=59),
)

_match_type_strategy = st.sampled_from(
    ["home", "away", "closed_door", "commercial_tour"]
)

_opponent_strategy = st.integers(min_value=2, max_value=MAX_OPPONENT_ID)

# Tour venue ids are 1..8 per app.data.tour_venues.TOUR_VENUES.
_tour_venue_strategy = st.integers(min_value=1, max_value=8)


@st.composite
def _friendly_request_strategy(draw) -> FriendlyCreateRequest:
    """Compose a :class:`FriendlyCreateRequest` that always passes
    ``create_friendly``'s validators.

    A ``tour_venue_id`` is drawn unconditionally and only attached when
    ``match_type == "commercial_tour"`` — for the other three match types
    Hypothesis still gets variety on the unused field but the service
    ignores it (per ``_validate_tour_venue``'s early return).
    """
    match_type = draw(_match_type_strategy)
    tour_venue_id = draw(_tour_venue_strategy) if match_type == "commercial_tour" else None
    return FriendlyCreateRequest(
        event_date=draw(_friendly_date_strategy),
        opponent_club_id=draw(_opponent_strategy),
        match_type=match_type,
        kick_off_time=draw(_kick_off_strategy),
        tour_venue_id=tour_venue_id,
        description_suffix=None,
    )


# ──────────────────────────────────────────────────────────────────────────
# Property 7 — Friendly creation round-trip preserves request data
# ──────────────────────────────────────────────────────────────────────────


@given(request=_friendly_request_strategy())
@settings(max_examples=20, deadline=None)
def test_friendly_creation_roundtrip_preserves_request_data(
    request: FriendlyCreateRequest,
) -> None:
    """**Validates: Requirements 4.3, 6.1, 6.8, 11.1, 11.2, 11.3, 11.4, 13.3**

    For every valid ``FriendlyCreateRequest``, exactly one row is written
    into ``calendar_events`` whose fields agree with the request and the
    resolved match-type mapping.
    """
    result, db_row = asyncio.run(_create_friendly_and_read_back(request))

    # ── Constants required by Req 6.1 / 11.2 / 11.3 ────────────────────
    assert db_row["event_type"] == "match", (
        f"event_type={db_row['event_type']!r}, expected 'match'"
    )
    assert db_row["priority"] == 2, (
        f"priority={db_row['priority']}, expected 2"
    )
    assert db_row["is_locked"] == 0, (
        f"is_locked={db_row['is_locked']}, expected 0"
    )
    assert db_row["is_cancelled"] == 0, (
        f"is_cancelled={db_row['is_cancelled']}, expected 0"
    )
    assert db_row["career_id"] == PLAYER_CAREER_ID, (
        f"career_id={db_row['career_id']}, expected {PLAYER_CAREER_ID}"
    )

    # ── Date / kick-off pass through unchanged (Req 6.1, 6.8, 13.3) ────
    assert db_row["event_date"] == str(request.event_date), (
        f"event_date={db_row['event_date']!r}, "
        f"expected {str(request.event_date)!r}"
    )
    assert db_row["kick_off_time"] == request.kick_off_time, (
        f"kick_off_time={db_row['kick_off_time']!r}, "
        f"expected {request.kick_off_time!r}"
    )

    # The service's returned result agrees with the request on the
    # user-facing scalars too (Req 6.8).
    assert result["event_date"] == request.event_date
    assert result["kick_off_time"] == request.kick_off_time

    # ── Home/away mapping (Req 11.1, 11.4 — Property 3 cross-check) ────
    if request.match_type == "away":
        expected_home = request.opponent_club_id
        expected_away = PLAYER_CLUB_ID
    else:
        expected_home = PLAYER_CLUB_ID
        expected_away = request.opponent_club_id
    assert db_row["home_club_id"] == expected_home, (
        f"home_club_id={db_row['home_club_id']}, expected {expected_home} "
        f"for match_type={request.match_type!r}"
    )
    assert db_row["away_club_id"] == expected_away, (
        f"away_club_id={db_row['away_club_id']}, expected {expected_away} "
        f"for match_type={request.match_type!r}"
    )
    # Cross-check: the resolved ids are always exactly the inputs.
    assert {db_row["home_club_id"], db_row["away_club_id"]} == {
        PLAYER_CLUB_ID,
        request.opponent_club_id,
    }

    # ── Description follows the documented "Товарищеский матч: …" form
    #    (Req 6.8) and uses the resolved home/away CLUB names. ──────────
    home_name = CLUBS[db_row["home_club_id"] - 1][0]
    away_name = CLUBS[db_row["away_club_id"] - 1][0]
    base_prefix = f"Товарищеский матч: {home_name} – {away_name}"
    assert db_row["description"].startswith(base_prefix), (
        f"description={db_row['description']!r} does not start with "
        f"{base_prefix!r}"
    )
    if request.match_type == "closed_door":
        assert db_row["description"].endswith(" (закрытый)"), (
            f"closed_door description must end with ' (закрытый)', "
            f"got {db_row['description']!r}"
        )
    elif request.match_type == "commercial_tour":
        # The city marker " — {city}" is the only suffix when no
        # description_suffix is provided.
        assert " — " in db_row["description"], (
            f"commercial_tour description must include city marker, "
            f"got {db_row['description']!r}"
        )

    # The service's returned description matches the persisted one.
    assert result["description"] == db_row["description"]

    # ── travel_data round-trip (Req 4.3, 6.8) ──────────────────────────
    assert db_row["travel_data_raw"] is not None, (
        "travel_data was not persisted"
    )
    decoded = json.loads(db_row["travel_data_raw"])
    assert decoded == result["travel_data"], (
        f"travel_data round-trip mismatch: stored={decoded!r}, "
        f"returned={result['travel_data']!r}"
    )

    # The match_subtype always echoes the request.
    assert decoded.get("match_subtype") == request.match_type, (
        f"travel_data.match_subtype={decoded.get('match_subtype')!r}, "
        f"expected {request.match_type!r}"
    )
    if request.match_type == "commercial_tour":
        # Per Req 4.3: city, country, stadium_name persisted verbatim.
        for key in ("city", "country", "stadium_name"):
            assert key in decoded, (
                f"travel_data missing {key!r} for commercial_tour: "
                f"{decoded!r}"
            )
    elif request.match_type == "closed_door":
        assert decoded.get("venue") == "training_ground", (
            f"closed_door travel_data.venue={decoded.get('venue')!r}, "
            f"expected 'training_ground'"
        )
