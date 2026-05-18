# Feature: friendly-matches, Property 11: Cancel friendly is correct under all event states
"""
Property-based test for ``FriendlyMatchService.cancel_friendly``.

**Validates: Requirements 7.5, 8.2, 8.3, 8.4, 8.5, 11.6**

For every pre-seeded ``calendar_events`` row reachable by the API, the
``cancel_friendly(career_id, event_id)`` coroutine satisfies the four
cases listed in the design's Property 11:

    Case A — Cancellable friendly
        Row exists for ``career_id``, ``event_type='match'``,
        ``priority=2``, ``is_locked=0``, ``is_cancelled=0``
        →  ``is_cancelled`` flips to ``1``, the returned id equals the
           input id, and a subsequent SELECT excludes the row.

    Case B — Already played friendly
        Row exists, ``priority=2``, ``event_type='match'``,
        ``is_locked=1``
        →  ``ValidationError("Нельзя отменить уже сыгранный матч",
           http_status=409)``; the row is left untouched.

    Case C — Not a friendly
        Row exists for the career but ``event_type != 'match'`` OR
        ``priority != 2``
        →  ``ValidationError("Это не товарищеский матч",
           http_status=400)``; the row is left untouched.

    Case D — Missing or already-cancelled row
        Row does not exist (wrong id or wrong career_id) OR
        ``is_cancelled = 1``
        →  ``ValidationError("Товарищеский матч не найден",
           http_status=404)``; no other row is mutated.

The test wires up a fresh in-memory SQLite database (via ``aiosqlite``)
per Hypothesis example, INSERTs one or two rows describing the case
under test, runs ``cancel_friendly``, and asserts the post-condition on
both the return value (or raised error) and the persisted row state.

Per the design, cases are enumerated explicitly via
``st.sampled_from`` rather than letting Hypothesis discover them
randomly — this keeps the DB-backed test small and deterministic
(``max_examples=20``).
"""

from __future__ import annotations

import asyncio
from typing import Tuple

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.services.friendly_match_service import (
    FriendlyMatchService,
    ValidationError,
)


# ──────────────────────────────────────────────────────────────────────────
# Minimal schema. Only the columns ``cancel_friendly`` reads / writes are
# required: ``id``, ``career_id``, ``event_type``, ``priority``,
# ``is_locked``, ``is_cancelled``. Other columns are present so the row
# shape matches production but are not asserted on.
# ──────────────────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER,
    event_date TEXT,
    event_type TEXT,
    home_club_id INTEGER,
    away_club_id INTEGER,
    is_locked INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 5,
    kick_off_time TEXT,
    description TEXT,
    travel_data TEXT,
    is_cancelled INTEGER DEFAULT 0
)
"""


async def _setup_database() -> Tuple:
    """Create an in-memory SQLite engine + session-factory for one example."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.execute(text(_SCHEMA_SQL))
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_factory


async def _insert_event(
    session: AsyncSession,
    *,
    career_id: int,
    event_type: str,
    priority: int,
    is_locked: int,
    is_cancelled: int,
) -> int:
    """Insert one calendar_events row and return its id."""
    await session.execute(
        text(
            """
            INSERT INTO calendar_events
            (career_id, event_date, event_type, home_club_id, away_club_id,
             is_locked, priority, kick_off_time, description, travel_data,
             is_cancelled)
            VALUES
            (:career_id, '2025-07-20', :event_type, 1, 2,
             :is_locked, :priority, '18:00', 'Test event', NULL,
             :is_cancelled)
            """
        ),
        {
            "career_id": career_id,
            "event_type": event_type,
            "is_locked": is_locked,
            "priority": priority,
            "is_cancelled": is_cancelled,
        },
    )
    await session.commit()
    row = await session.execute(text("SELECT last_insert_rowid()"))
    return int(row.scalar() or 0)


async def _read_event(
    session: AsyncSession, event_id: int
) -> Tuple[int, int, int, int, str]:
    """Read (priority, is_locked, is_cancelled, career_id, event_type)."""
    row = await session.execute(
        text(
            "SELECT priority, is_locked, is_cancelled, career_id, event_type "
            "FROM calendar_events WHERE id = :eid"
        ),
        {"eid": event_id},
    )
    r = row.fetchone()
    assert r is not None, f"event {event_id} unexpectedly missing"
    return (int(r[0]), int(r[1]), int(r[2]), int(r[3]), str(r[4]))


# ──────────────────────────────────────────────────────────────────────────
# Case enumeration. Each entry is a fully-specified scenario; hypothesis
# samples uniformly over the list so every case is exercised.
# ──────────────────────────────────────────────────────────────────────────
# (label, event_type, priority, is_locked, is_cancelled,
#  use_wrong_career_id, use_nonexistent_id)
CASES = [
    # ── Case A — cancellable friendly (success). ──────────────────────
    ("A_friendly_open", "match", 2, 0, 0, False, False),
    # ── Case B — locked friendly → 409 "Нельзя отменить уже сыгранный матч". ─
    ("B_friendly_locked", "match", 2, 1, 0, False, False),
    # ── Case C — wrong event_type → 400 "Это не товарищеский матч". ──
    ("C_wrong_type_international", "international", 2, 0, 0, False, False),
    ("C_wrong_type_holiday", "holiday", 2, 0, 0, False, False),
    # ── Case C — wrong priority (league=4, cup=5, etc.) → 400. ───────
    ("C_wrong_priority_league", "match", 4, 0, 0, False, False),
    ("C_wrong_priority_cup", "match", 5, 0, 0, False, False),
    ("C_wrong_priority_zero", "match", 0, 0, 0, False, False),
    # ── Case D — already cancelled → 404 "Товарищеский матч не найден". ─
    ("D_already_cancelled", "match", 2, 0, 1, False, False),
    # ── Case D — nonexistent id → 404. ───────────────────────────────
    ("D_nonexistent_id", "match", 2, 0, 0, False, True),
    # ── Case D — wrong career_id → 404 (row exists but for someone else). ─
    ("D_wrong_career", "match", 2, 0, 0, True, False),
]


CALLER_CAREER_ID = 1
OTHER_CAREER_ID = 999


async def _run_one_case(case: tuple) -> None:
    """Execute one case: seed DB, call cancel_friendly, assert the outcome."""
    (
        label,
        event_type,
        priority,
        is_locked,
        is_cancelled,
        use_wrong_career_id,
        use_nonexistent_id,
    ) = case

    engine, session_factory = await _setup_database()
    try:
        async with session_factory() as session:
            # Seed the event under either the caller's career or someone
            # else's, depending on the case.
            seeded_career_id = (
                OTHER_CAREER_ID if use_wrong_career_id else CALLER_CAREER_ID
            )
            event_id = await _insert_event(
                session,
                career_id=seeded_career_id,
                event_type=event_type,
                priority=priority,
                is_locked=is_locked,
                is_cancelled=is_cancelled,
            )

            # For the "nonexistent id" case, target an id that was never
            # inserted (event_id + 1000 is guaranteed to be free in a
            # fresh DB with one row).
            target_id = event_id + 1000 if use_nonexistent_id else event_id

            service = FriendlyMatchService(session=session)

            if label == "A_friendly_open":
                # Case A: success path.
                returned_id = await service.cancel_friendly(
                    CALLER_CAREER_ID, target_id
                )
                assert returned_id == target_id, (
                    f"[{label}] expected returned id {target_id}, "
                    f"got {returned_id}"
                )
                # The row is now soft-cancelled.
                _, _, post_cancelled, _, _ = await _read_event(
                    session, event_id
                )
                assert post_cancelled == 1, (
                    f"[{label}] expected is_cancelled=1 after cancel, "
                    f"got {post_cancelled}"
                )

            elif label == "B_friendly_locked":
                # Case B: locked → 409 "Нельзя отменить уже сыгранный матч".
                with pytest.raises(ValidationError) as exc_info:
                    await service.cancel_friendly(CALLER_CAREER_ID, target_id)
                err = exc_info.value
                assert err.http_status == 409, (
                    f"[{label}] expected http_status=409, "
                    f"got {err.http_status}"
                )
                assert err.message == "Нельзя отменить уже сыгранный матч", (
                    f"[{label}] unexpected message: {err.message!r}"
                )
                # Row state is untouched.
                p, lk, c, _, _ = await _read_event(session, event_id)
                assert (p, lk, c) == (priority, is_locked, is_cancelled), (
                    f"[{label}] row mutated: got priority={p}, "
                    f"is_locked={lk}, is_cancelled={c}"
                )

            elif label.startswith("C_"):
                # Case C: wrong type/priority → 400 "Это не товарищеский матч".
                with pytest.raises(ValidationError) as exc_info:
                    await service.cancel_friendly(CALLER_CAREER_ID, target_id)
                err = exc_info.value
                assert err.http_status == 400, (
                    f"[{label}] expected http_status=400, "
                    f"got {err.http_status}"
                )
                assert err.message == "Это не товарищеский матч", (
                    f"[{label}] unexpected message: {err.message!r}"
                )
                p, lk, c, _, _ = await _read_event(session, event_id)
                assert (p, lk, c) == (priority, is_locked, is_cancelled), (
                    f"[{label}] row mutated: got priority={p}, "
                    f"is_locked={lk}, is_cancelled={c}"
                )

            elif label.startswith("D_"):
                # Case D: missing / already cancelled / wrong career →
                # 404 "Товарищеский матч не найден".
                with pytest.raises(ValidationError) as exc_info:
                    await service.cancel_friendly(CALLER_CAREER_ID, target_id)
                err = exc_info.value
                assert err.http_status == 404, (
                    f"[{label}] expected http_status=404, "
                    f"got {err.http_status}"
                )
                assert err.message == "Товарищеский матч не найден", (
                    f"[{label}] unexpected message: {err.message!r}"
                )
                # The seeded row is still there with its original state
                # (the service must not touch unrelated rows).
                p, lk, c, cid, et = await _read_event(session, event_id)
                assert (p, lk, c, cid, et) == (
                    priority,
                    is_locked,
                    is_cancelled,
                    seeded_career_id,
                    event_type,
                ), (
                    f"[{label}] seeded row mutated: priority={p}, "
                    f"is_locked={lk}, is_cancelled={c}, career_id={cid}, "
                    f"event_type={et}"
                )

            else:  # pragma: no cover — defensive
                pytest.fail(f"unhandled case label: {label!r}")
    finally:
        await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────
# Property 11 — Cancel friendly is correct under all event states.
# ──────────────────────────────────────────────────────────────────────────
@given(case=st.sampled_from(CASES))
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_cancel_friendly_correct_under_all_event_states(case: tuple) -> None:
    """**Validates: Requirements 7.5, 8.2, 8.3, 8.4, 8.5, 11.6**

    For every pre-seeded ``calendar_events`` configuration in
    :data:`CASES`, the result of ``cancel_friendly`` matches the case's
    expected outcome — either success (Case A) or a ``ValidationError``
    with the exact ``message`` and ``http_status`` mandated by
    Requirements 7.5 / 8.2-8.5.
    """
    asyncio.run(_run_one_case(case))
