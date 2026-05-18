# Feature: friendly-matches, Integration test for create-then-list flow
"""
Integration test for the user-arranged friendly create-then-list flow.

Validates Requirement 11.4 by exercising
``POST /api/calendar/{career_id}/friendly`` to create a friendly match,
then ``GET /api/calendar/{career_id}/month?year=YYYY&month=M`` to list
the events for the matching month, end-to-end against an in-memory
SQLite database.

The test:
  1. Builds a fresh in-memory SQLite schema covering the tables touched
     by both endpoints (careers, competitions, calendar_events, players).
  2. Pre-seeds a career (career_id=1, club_id=1 → Manchester City) and a
     pair of calendar_events to establish a wide season window.
  3. Overrides the ``get_db``/``get_db_session`` dependency on the
     FastAPI app and POSTs to the friendly endpoint via httpx +
     ``ASGITransport``, then GETs ``/month`` for July 2025.
  4. Verifies the new event appears in the response with
     ``priority=2`` and ``event_type='match'`` and that its id matches
     the one returned by the create endpoint.
"""

from __future__ import annotations

from typing import AsyncGenerator, Tuple

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
# and month-listing endpoints. We avoid importing run_local.py (which has
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

    # Kept as a safety net in case any code path touches it.
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
# Fixtures (mirror the pattern used by
# tests/test_friendly_create_simulate_integration.py)
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


# ──────────────────────────────────────────────────────────────────────────
# Test — Create a friendly, list the month, verify it appears
# (Requirement 11.4)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_friendly_then_list_month(http_client):
    """
    POST /api/calendar/{career_id}/friendly with a valid payload SHALL
    return 201 with the new event id. A subsequent
    GET /api/calendar/{career_id}/month?year=2025&month=7 SHALL include
    the newly created event with ``priority=2`` and
    ``event_type='match'``.

    Validates Requirement 11.4.
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
    assert "id" in create_data and isinstance(create_data["id"], int)
    new_event_id = int(create_data["id"])
    assert create_data["event_date"] == "2025-07-22"

    # ── Step 2: list the month via GET /month?year=2025&month=7 ────────
    list_resp = await client.get(
        f"/api/calendar/{career_id}/month",
        params={"year": 2025, "month": 7},
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()

    assert list_data["year"] == 2025
    assert list_data["month"] == 7
    assert "events" in list_data and isinstance(list_data["events"], list)

    # ── Verify the new friendly appears in the listing with the correct
    #    priority and event_type (Requirement 11.4) ────────────────────
    matching = [e for e in list_data["events"] if e.get("id") == new_event_id]
    assert len(matching) == 1, (
        "The newly created friendly SHALL appear in "
        "GET /month exactly once (Requirement 11.4); "
        f"events returned: {list_data['events']!r}"
    )
    new_event = matching[0]
    assert new_event["priority"] == 2, (
        "User-arranged friendlies SHALL have priority=2 "
        f"(Requirement 11.4); got {new_event['priority']!r}"
    )
    assert new_event["event_type"] == "match", (
        "User-arranged friendlies SHALL have event_type='match' "
        f"(Requirement 11.4); got {new_event['event_type']!r}"
    )
    assert new_event["event_date"] == "2025-07-22"
    assert new_event["home_club_id"] == 1
    assert new_event["away_club_id"] == 2
    assert new_event["is_locked"] is False
