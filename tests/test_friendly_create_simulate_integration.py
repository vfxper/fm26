# Feature: friendly-matches, Integration test for create-then-simulate flow
"""
Integration test for the user-arranged friendly create-then-simulate flow.

Validates Requirements 7.1, 7.2, 7.3, 7.4 by exercising the
``POST /api/calendar/{career_id}/friendly`` endpoint to create a
friendly match, then ``POST /api/calendar/{career_id}/match/{event_id}/simulate``
to simulate it, end-to-end against an in-memory SQLite database.

The test:
  1. Builds a fresh in-memory SQLite schema covering the tables touched
     by both endpoints (careers, competitions, calendar_events, players).
  2. Pre-seeds a career (career_id=1, club_id=1 → Manchester City) and a
     pair of calendar_events to establish a wide season window.
  3. Overrides the ``get_db``/``get_db_session`` dependency on the
     FastAPI app and POSTs to the friendly endpoint via httpx +
     ``ASGITransport``, then patches ``MatchEngine.simulate_match`` for a
     deterministic 3-1 result and POSTs to the simulate endpoint.
  4. Verifies the simulate response carries home/away scores and an
     ``events`` array, the calendar row's ``is_locked`` flips to ``1``,
     and the description is rewritten with the score.
"""

from __future__ import annotations

from typing import AsyncGenerator, Tuple
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.main import app


# ──────────────────────────────────────────────────────────────────────────
# Schema setup — minimal subset of tables needed by the friendly-create
# and simulate endpoints. We avoid importing run_local.py (which has
# import-time side effects on os.environ) by inlining the schema.
# ──────────────────────────────────────────────────────────────────────────


def _build_schema(conn):
    metadata = MetaData()

    Table(
        "careers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer),
        Column("club_id", Integer),
        Column("manager_name", String(100)),
        Column("current_season", Integer, default=1),
        Column("current_week", Integer, default=1),
        Column("budget", Float, default=50000000),
        Column("status", String(20), default="active"),
        Column("created_at", DateTime, server_default=func.now()),
    )

    Table(
        "competitions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(255)),
        Column("competition_type", String(50), default="league"),
        Column("season", Integer, default=1),
        Column("status", String(20), default="active"),
        Column("created_at", DateTime, server_default=func.now()),
    )

    Table(
        "calendar_events",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("career_id", Integer),
        Column("event_date", String(10)),
        Column("event_type", String(30)),
        Column("competition_id", Integer, nullable=True),
        Column("home_club_id", Integer, nullable=True),
        Column("away_club_id", Integer, nullable=True),
        Column("is_locked", Boolean, default=False),
        Column("priority", Integer, default=5),
        Column("kick_off_time", String(5), nullable=True),
        Column("weather_data", Text, nullable=True),
        Column("description", Text, nullable=True),
        Column("travel_data", Text, nullable=True),
        Column("original_date", String(10), nullable=True),
        Column("reschedule_reason", String(255), nullable=True),
        Column("is_cancelled", Boolean, default=False),
        Column("template_id", Integer, nullable=True),
        Column("created_at", DateTime, server_default=func.now()),
        Column("updated_at", DateTime, server_default=func.now()),
    )

    # Required by MatchEngine even though we patch simulate_match — kept
    # as a safety net in case the real method ever gets called.
    Table(
        "players",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("uid", String(255), unique=True, nullable=True),
        Column("name", String(200)),
        Column("age", Integer),
        Column("nationality", String(100)),
        Column("club", String(200)),
        Column("position", String(50)),
        Column("ca", Integer),
        Column("pa", Integer),
    )

    metadata.create_all(conn)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures (mirror the pattern used by tests/test_ucl_simulation_integration.py)
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    """Create an in-memory SQLite engine with the minimal schema."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with eng.begin() as conn:
        await conn.run_sync(_build_schema)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture
async def http_client(
    session_factory,
) -> AsyncGenerator[Tuple[AsyncClient, async_sessionmaker], None]:
    """
    Build an httpx ASGI client that talks to ``app.main:app`` with the
    database dependency overridden to use our in-memory SQLite engine.

    We disable lifespan startup (no production init_db, no Redis ping)
    by using ``ASGITransport`` directly.
    """
    from app.core.database import get_db, get_db_session

    async def override_get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client, session_factory

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


async def _setup_career_and_window(session: AsyncSession) -> int:
    """
    Seed a career row (career_id=1, club_id=1 → Manchester City) plus two
    placeholder calendar events that bracket the season window so the
    friendly-create endpoint accepts a date in late July.

    Returns the career id.
    """
    await session.execute(
        text(
            """
            INSERT INTO careers (id, user_id, club_id, manager_name,
                                 current_season, current_week, status)
            VALUES (1, 1, 1, 'Test Manager', 1, 1, 'active')
            """
        )
    )

    # Two season-anchor events: one well before the friendly date and one
    # well after, so the resolved season window contains 2025-07-22 with
    # no ±2-day conflicts.
    await session.execute(
        text(
            """
            INSERT INTO calendar_events
            (career_id, event_date, event_type, priority,
             is_locked, is_cancelled, description)
            VALUES (1, '2025-07-01', 'training', 1, 0, 0, 'Season start anchor')
            """
        )
    )
    await session.execute(
        text(
            """
            INSERT INTO calendar_events
            (career_id, event_date, event_type, priority,
             is_locked, is_cancelled, description)
            VALUES (1, '2026-06-30', 'training', 1, 0, 0, 'Season end anchor')
            """
        )
    )
    await session.commit()
    return 1


def _make_match_result(home_score: int, away_score: int):
    """Build a MatchResult-like object suitable for monkey-patching."""
    from app.services.match_engine import MatchResult

    return MatchResult(
        home_score=home_score,
        away_score=away_score,
        events=[],
        home_possession=55,
        away_possession=45,
        home_shots=12,
        away_shots=8,
        home_shots_on_target=5,
        away_shots_on_target=3,
        home_team_name="Manchester City",
        away_team_name="Liverpool",
    )


# ──────────────────────────────────────────────────────────────────────────
# Test — Create a friendly, simulate it, verify the round-trip
# (Requirements 7.1, 7.2, 7.3, 7.4)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_friendly_then_simulate(http_client):
    """
    POST /api/calendar/{career_id}/friendly with a valid payload SHALL
    return 201 with the new event id; POSTing the same id to
    /api/calendar/{career_id}/match/{event_id}/simulate SHALL return 200
    with home/away scores and an events array; the calendar row SHALL
    flip to ``is_locked=1`` and its description SHALL be rewritten with
    the final score.

    Validates Requirements 7.1, 7.2, 7.3, 7.4.
    """
    client, sf = http_client

    # ── Seed: career + season-window anchor events ─────────────────────
    async with sf() as s:
        career_id = await _setup_career_and_window(s)

    # ── Step 1: create the friendly via POST /friendly ─────────────────
    payload = {
        "event_date": "2025-07-22",
        "opponent_club_id": 2,  # Liverpool
        "match_type": "home",
        "kick_off_time": "18:00",
    }
    create_resp = await client.post(
        f"/api/calendar/{career_id}/friendly", json=payload
    )
    assert create_resp.status_code == 201, create_resp.text
    create_data = create_resp.json()

    # Sanity-check the create response shape (Requirement 6.8).
    assert "id" in create_data and isinstance(create_data["id"], int)
    event_id = int(create_data["id"])
    assert create_data["event_date"] == "2025-07-22"
    assert create_data["kick_off_time"] == "18:00"
    assert create_data["home_club_id"] == 1
    assert create_data["away_club_id"] == 2
    assert "Товарищеский матч" in create_data["description"]

    # ── Step 2: simulate the friendly with a deterministic 3-1 result ──
    fake = _make_match_result(home_score=3, away_score=1)

    async def fake_simulate(self, *args, **kwargs):
        return fake

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=fake_simulate,
    ):
        sim_resp = await client.post(
            f"/api/calendar/{career_id}/match/{event_id}/simulate"
        )

    # ── Verify the simulate response (Requirement 7.1, 7.2) ────────────
    assert sim_resp.status_code == 200, sim_resp.text
    sim_data = sim_resp.json()
    assert sim_data["home_score"] == 3
    assert sim_data["away_score"] == 1
    assert "events" in sim_data and isinstance(sim_data["events"], list)
    # Both club names from CLUBS should appear in the simulate response.
    assert sim_data["home_team"] == "Manchester City"
    assert sim_data["away_team"] == "Liverpool"

    # ── Verify the calendar row is now locked + the description is the
    #    final scoreline (Requirement 7.3, 7.4) ────────────────────────
    async with sf() as s:
        r = await s.execute(
            text(
                """
                SELECT is_locked, description
                FROM calendar_events
                WHERE id = :eid
                """
            ),
            {"eid": event_id},
        )
        row = r.fetchone()
    assert row is not None, "Friendly event row missing after simulation"

    # SQLite returns the boolean column as 0/1 — coerce defensively.
    assert int(bool(row[0])) == 1, (
        "Friendly event SHALL be locked after simulation (Requirement 7.4)"
    )
    assert row[1] is not None and "3" in row[1] and "1" in row[1], (
        "Description SHALL be rewritten with the final score after simulation "
        f"(Requirement 7.4); got {row[1]!r}"
    )
    assert "Manchester City" in row[1] and "Liverpool" in row[1], (
        "Description SHALL contain both club names; "
        f"got {row[1]!r}"
    )
