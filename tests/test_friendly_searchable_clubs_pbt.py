# Feature: friendly-matches, Property 1: Searchable clubs API excludes the player's own club
"""
Property-based test for ``GET /api/clubs/searchable``.

**Validates: Requirements 2.1, 2.6**

Property 1 (design.md):
    *For any* career id with a valid ``club_id`` in the ``careers`` table,
    the response of ``GET /api/clubs/searchable?exclude_career_id=<career_id>``
    SHALL contain a ``clubs`` array where no element has ``id`` equal to
    that career's ``club_id``. When ``exclude_career_id`` is omitted, the
    response SHALL contain all clubs in ``CLUBS``.

Implementation notes
--------------------
The task brief allows either driving ``app.main:app`` over httpx +
``ASGITransport`` or calling the route function directly with an
overridden ``AsyncSession``. We pick the second path: it exercises the
exact code under test (``app.api.routes.clubs.list_searchable_clubs``)
and avoids the lifespan / Redis startup machinery in ``app.main``,
which is irrelevant for this property.

Each Hypothesis example builds a fresh in-memory SQLite database with
a minimal ``careers`` table, inserts a single career row whose
``club_id`` ranges over ``[1, len(CLUBS)]``, then invokes the route
function twice — once with ``exclude_career_id=<career_id>`` and once
without — and asserts:

  * the ``exclude_career_id`` response omits the career's club exactly
    once and contains every other club from ``CLUBS``;
  * every returned club has the expected ``id`` (1-based), ``name``,
    and ``league`` fields;
  * the no-filter response contains all ``len(CLUBS)`` clubs.
"""

from __future__ import annotations

import asyncio
from typing import Tuple

from hypothesis import given, settings, strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.routes.clubs import list_searchable_clubs
from app.data.club_budgets import CLUBS


# ──────────────────────────────────────────────────────────────────────────
# In-memory SQLite helpers
# ──────────────────────────────────────────────────────────────────────────

# Minimal schema: only the ``careers`` table is read by the route.
_CAREERS_SCHEMA = """
CREATE TABLE careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL
)
"""


async def _build_engine_with_career(player_club_id: int) -> Tuple[
    "async_sessionmaker[AsyncSession]", int, "object"
]:
    """Create a fresh in-memory engine, seed one career, return factory + ids.

    Returns ``(session_factory, career_id, engine)`` so the caller can dispose
    of the engine after the test example finishes.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.execute(text(_CAREERS_SCHEMA))

    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with factory() as session:
        await session.execute(
            text("INSERT INTO careers (club_id) VALUES (:cid)"),
            {"cid": player_club_id},
        )
        await session.commit()
        result = await session.execute(text("SELECT id FROM careers"))
        career_id = int(result.scalar() or 0)

    return factory, career_id, engine


async def _exercise_endpoint(player_club_id: int) -> Tuple[dict, dict, int]:
    """Run both endpoint calls (with and without exclude_career_id).

    Returns ``(excluded_response, all_response, career_id)``.
    """
    factory, career_id, engine = await _build_engine_with_career(player_club_id)
    try:
        # Call with exclude_career_id — fresh session for isolation.
        async with factory() as session:
            excluded_response = await list_searchable_clubs(
                exclude_career_id=career_id,
                db=session,
            )

        # Call without any filter — fresh session.
        async with factory() as session:
            all_response = await list_searchable_clubs(
                exclude_career_id=None,
                db=session,
            )

        return excluded_response, all_response, career_id
    finally:
        await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────
# Property test
# ──────────────────────────────────────────────────────────────────────────


@given(player_club_id=st.integers(min_value=1, max_value=len(CLUBS)))
@settings(max_examples=20, deadline=None)
def test_searchable_clubs_excludes_player_club(player_club_id: int) -> None:
    """**Validates: Requirements 2.1, 2.6**

    For every ``player_club_id`` in ``[1, len(CLUBS)]``:
      1. With ``exclude_career_id`` set, the response SHALL omit exactly
         that one club and SHALL include every other club from ``CLUBS``
         in 1-based order, with ``id``, ``name``, and ``league`` fields.
      2. With ``exclude_career_id`` omitted, the response SHALL contain
         all ``len(CLUBS)`` clubs.
    """
    excluded_response, all_response, career_id = asyncio.run(
        _exercise_endpoint(player_club_id)
    )

    # ── 1. exclude_career_id response ─────────────────────────────────────

    assert "clubs" in excluded_response, (
        "Response missing 'clubs' key when exclude_career_id is set"
    )
    excluded_clubs = excluded_response["clubs"]

    # Property 1 core: the player's own club is never present.
    excluded_ids = [c["id"] for c in excluded_clubs]
    assert player_club_id not in excluded_ids, (
        f"Player's club id={player_club_id} appeared in the excluded "
        f"response: {excluded_ids!r}"
    )

    # Cardinality: exactly one club is removed.
    assert len(excluded_clubs) == len(CLUBS) - 1, (
        f"Expected {len(CLUBS) - 1} clubs after excluding id={player_club_id}, "
        f"got {len(excluded_clubs)}"
    )

    # Every other club from CLUBS is present, in 1-based id order.
    expected_ids = [i for i in range(1, len(CLUBS) + 1) if i != player_club_id]
    assert excluded_ids == expected_ids, (
        f"Excluded response club ids do not match expected.\n"
        f"  expected={expected_ids!r}\n"
        f"  got={excluded_ids!r}"
    )

    # Each entry has the required fields with the right types and values.
    for entry in excluded_clubs:
        assert set(entry.keys()) >= {"id", "name", "league"}, (
            f"Club entry missing required fields: {entry!r}"
        )
        assert isinstance(entry["id"], int) and 1 <= entry["id"] <= len(CLUBS)
        assert isinstance(entry["name"], str) and entry["name"]
        assert isinstance(entry["league"], str) and entry["league"]
        # Cross-check name & league with the source-of-truth CLUBS tuple.
        expected_name, _scout, _trans, expected_league = CLUBS[entry["id"] - 1]
        assert entry["name"] == expected_name, (
            f"Name mismatch for id={entry['id']}: "
            f"got {entry['name']!r}, expected {expected_name!r}"
        )
        assert entry["league"] == expected_league, (
            f"League mismatch for id={entry['id']}: "
            f"got {entry['league']!r}, expected {expected_league!r}"
        )

    # ── 2. no-filter response ────────────────────────────────────────────

    assert "clubs" in all_response, (
        "Response missing 'clubs' key when exclude_career_id is omitted"
    )
    all_clubs = all_response["clubs"]

    assert len(all_clubs) == len(CLUBS), (
        f"Expected all {len(CLUBS)} clubs when exclude_career_id is None, "
        f"got {len(all_clubs)}"
    )
    all_ids = [c["id"] for c in all_clubs]
    assert all_ids == list(range(1, len(CLUBS) + 1)), (
        "No-filter response club ids must be the full 1-based range"
    )
    # Every club in CLUBS must appear in the no-filter response.
    for idx, (name, _scout, _trans, league) in enumerate(CLUBS, start=1):
        entry = all_clubs[idx - 1]
        assert entry["id"] == idx
        assert entry["name"] == name
        assert entry["league"] == league
