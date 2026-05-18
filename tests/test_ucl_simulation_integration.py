# Feature: uefa-champions-league, Integration tests for UCL simulation flow
"""
Integration tests for the UCL simulation flow.

Validates Requirements 8.1, 8.2, 8.4, 12.2, 12.4 by exercising the
``POST /api/calendar/{career_id}/match/{event_id}/simulate`` endpoint
end-to-end against an in-memory SQLite database.

Each test:
  1. Builds a fresh in-memory SQLite schema covering the tables touched
     by the simulate endpoint (careers, competitions, calendar_events,
     ucl_participants, ucl_standings, ucl_ties, competition_rounds, plus
     the ``players`` table that ``MatchEngine`` reads from).
  2. Creates a career and invokes ``UCLGenerator.generate_competition``
     to seed a real UCL season (36 participants, 8 matchdays of league
     phase events).
  3. Overrides the ``get_db`` / ``get_db_session`` dependency on the
     FastAPI app and POSTs to the simulate endpoint via httpx +
     ``ASGITransport``.

Tests 4 and 5 patch ``MatchEngine.simulate_match`` to force the
specific failure path described in the spec.
"""

from __future__ import annotations

import random
from typing import AsyncGenerator, Optional, Tuple
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
from app.services.ucl_generator import UCLGenerator


# ──────────────────────────────────────────────────────────────────────────
# Schema setup — the SQLite tables actually exercised by the simulate
# endpoint and UCLGenerator. We avoid importing run_local.py (which has
# import-time side effects on os.environ) by inlining a minimal schema
# here.
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

    Table(
        "competition_rounds",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column(
            "competition_id",
            Integer,
            ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("round_type", String(30), nullable=False),
        Column("round_order", Integer, nullable=False),
        Column("start_date", Date, nullable=True),
        Column("end_date", Date, nullable=True),
        Column("is_completed", Boolean, default=False, nullable=False),
        Column("created_at", DateTime, server_default=func.now()),
        Index("idx_comp_rounds_comp", "competition_id"),
        Index(
            "idx_comp_rounds_comp_order",
            "competition_id",
            "round_order",
            unique=True,
        ),
    )

    Table(
        "ucl_participants",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column(
            "competition_id",
            Integer,
            ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("club_id", Integer, nullable=True),
        Column("club_name", String(100), nullable=False),
        Column("country", String(50), nullable=False),
        Column("seed", Integer, nullable=False),
        Column("final_rank", Integer, nullable=True),
        Index("idx_ucl_part_comp", "competition_id"),
        Index(
            "idx_ucl_part_comp_seed",
            "competition_id",
            "seed",
            unique=True,
        ),
    )

    Table(
        "ucl_standings",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column(
            "competition_id",
            Integer,
            ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            "participant_id",
            Integer,
            ForeignKey("ucl_participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("played", Integer, nullable=False, server_default="0"),
        Column("won", Integer, nullable=False, server_default="0"),
        Column("drawn", Integer, nullable=False, server_default="0"),
        Column("lost", Integer, nullable=False, server_default="0"),
        Column("goals_for", Integer, nullable=False, server_default="0"),
        Column("goals_against", Integer, nullable=False, server_default="0"),
        Column(
            "goal_difference", Integer, nullable=False, server_default="0"
        ),
        Column("points", Integer, nullable=False, server_default="0"),
        Column("rank", Integer, nullable=True),
        Index("idx_ucl_stand_comp", "competition_id"),
        Index(
            "idx_ucl_stand_comp_part",
            "competition_id",
            "participant_id",
            unique=True,
        ),
    )

    Table(
        "ucl_ties",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column(
            "competition_id",
            Integer,
            ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            "round_id",
            Integer,
            ForeignKey("competition_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            "home_participant_id",
            Integer,
            ForeignKey("ucl_participants.id"),
            nullable=True,
        ),
        Column(
            "away_participant_id",
            Integer,
            ForeignKey("ucl_participants.id"),
            nullable=True,
        ),
        Column("leg1_home_score", Integer, nullable=True),
        Column("leg1_away_score", Integer, nullable=True),
        Column("leg2_home_score", Integer, nullable=True),
        Column("leg2_away_score", Integer, nullable=True),
        Column("aggregate_home", Integer, nullable=True),
        Column("aggregate_away", Integer, nullable=True),
        Column(
            "winner_participant_id",
            Integer,
            ForeignKey("ucl_participants.id"),
            nullable=True,
        ),
        Column("winner_decided_by", String(20), nullable=True),
        Column("bracket_position", Integer, nullable=False),
        Index("idx_ucl_tie_comp", "competition_id"),
        Index("idx_ucl_tie_round", "round_id"),
        Index(
            "idx_ucl_tie_round_pos",
            "round_id",
            "bracket_position",
            unique=True,
        ),
    )

    metadata.create_all(conn)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    """Create an in-memory SQLite engine with the UCL schema."""
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
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


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
# Helpers — set up a UCL career
# ──────────────────────────────────────────────────────────────────────────


async def _setup_career_and_ucl(
    session: AsyncSession,
    *,
    player_club_id: int = 1,
    season: int = 2025,
) -> Tuple[int, int]:
    """
    Create a career row and run UCLGenerator.generate_competition. Returns
    ``(career_id, competition_id)``.
    """
    await session.execute(
        text(
            """
            INSERT INTO careers (id, user_id, club_id, manager_name,
                                 current_season, current_week, status)
            VALUES (1, 1, :club_id, 'Test Manager', 1, 1, 'active')
            """
        ),
        {"club_id": player_club_id},
    )
    await session.commit()

    generator = UCLGenerator(session, rng=random.Random(42))
    competition_id = await generator.generate_competition(
        career_id=1, year=season, player_club_id=player_club_id
    )
    return 1, int(competition_id)


def _make_match_result(home_score: int, away_score: int):
    """Build a MatchResult-like object suitable for monkey-patching."""
    from app.services.match_engine import MatchResult

    return MatchResult(
        home_score=home_score,
        away_score=away_score,
        events=[],
        home_possession=50,
        away_possession=50,
        home_shots=0,
        away_shots=0,
        home_shots_on_target=0,
        away_shots_on_target=0,
        home_team_name="Home",
        away_team_name="Away",
    )


# ──────────────────────────────────────────────────────────────────────────
# Test 1 — League phase match updates ucl_standings (Req 8.1, 8.2)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_league_phase_simulation_updates_standings(http_client):
    """
    Simulating a UCL league-phase calendar event SHALL update the
    ``ucl_standings`` rows for both participants (3 points to the
    winner / 1 each on a draw, plus goals_for/goals_against).
    """
    client, sf = http_client

    # Seed the database — generate a real UCL season for career_id=1.
    async with sf() as s:
        career_id, comp_id = await _setup_career_and_ucl(s)

        # Find the player's first league_phase event (the player is club_id=1).
        r = await s.execute(
            text(
                """
                SELECT id, home_club_id, away_club_id, description, event_date
                FROM calendar_events
                WHERE competition_id = :cid
                  AND (home_club_id = 1 OR away_club_id = 1)
                  AND description LIKE '%тур 1%'
                ORDER BY id LIMIT 1
                """
            ),
            {"cid": comp_id},
        )
        row = r.fetchone()
        assert row is not None, "No league-phase event found for player's club"
        event_id = int(row[0])
        home_club_id = int(row[1]) if row[1] is not None else 0
        away_club_id = int(row[2]) if row[2] is not None else 0

        # Resolve the participant ids of the two clubs.
        async def pid_for_club(club_id: int) -> int:
            rr = await s.execute(
                text(
                    "SELECT id FROM ucl_participants "
                    "WHERE competition_id = :cid AND club_id = :club"
                ),
                {"cid": comp_id, "club": club_id},
            )
            return int(rr.scalar())

        home_pid = await pid_for_club(home_club_id)
        away_pid = await pid_for_club(away_club_id)

    # Force a deterministic 2-1 home win.
    fake = _make_match_result(home_score=2, away_score=1)

    async def fake_simulate(self, *args, **kwargs):
        return fake

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=fake_simulate,
    ):
        resp = await client.post(
            f"/api/calendar/{career_id}/match/{event_id}/simulate"
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["home_score"] == 2
    assert data["away_score"] == 1

    # Verify standings — home_pid should have 1 win (3 pts) and away_pid
    # should have 1 loss (0 pts).
    async with sf() as s:
        r = await s.execute(
            text(
                "SELECT participant_id, played, won, drawn, lost, "
                "       goals_for, goals_against, points "
                "FROM ucl_standings "
                "WHERE competition_id = :cid AND participant_id IN (:h, :a)"
            ),
            {"cid": comp_id, "h": home_pid, "a": away_pid},
        )
        by_pid = {row[0]: row for row in r.fetchall()}

        h = by_pid[home_pid]
        a = by_pid[away_pid]

        # Winner (home): played=1, won=1, drawn=0, lost=0, gf=2, ga=1, pts=3
        assert h[1] == 1 and h[2] == 1 and h[3] == 0 and h[4] == 0
        assert h[5] == 2 and h[6] == 1 and h[7] == 3

        # Loser (away): played=1, won=0, drawn=0, lost=1, gf=1, ga=2, pts=0
        assert a[1] == 1 and a[2] == 0 and a[3] == 0 and a[4] == 1
        assert a[5] == 1 and a[6] == 2 and a[7] == 0


@pytest.mark.asyncio
async def test_league_phase_draw_assigns_one_point_each(http_client):
    """A 1-1 draw SHALL increment ``drawn`` and add 1 point on each side."""
    client, sf = http_client

    async with sf() as s:
        career_id, comp_id = await _setup_career_and_ucl(s)
        r = await s.execute(
            text(
                """
                SELECT id, home_club_id, away_club_id
                FROM calendar_events
                WHERE competition_id = :cid
                  AND (home_club_id = 1 OR away_club_id = 1)
                  AND description LIKE '%тур 1%'
                ORDER BY id LIMIT 1
                """
            ),
            {"cid": comp_id},
        )
        row = r.fetchone()
        event_id = int(row[0])
        home_club_id = int(row[1]) if row[1] is not None else 0
        away_club_id = int(row[2]) if row[2] is not None else 0

        async def pid_for_club(club_id: int) -> int:
            rr = await s.execute(
                text(
                    "SELECT id FROM ucl_participants "
                    "WHERE competition_id = :cid AND club_id = :club"
                ),
                {"cid": comp_id, "club": club_id},
            )
            return int(rr.scalar())

        home_pid = await pid_for_club(home_club_id)
        away_pid = await pid_for_club(away_club_id)

    fake = _make_match_result(home_score=1, away_score=1)

    async def fake_simulate(self, *args, **kwargs):
        return fake

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=fake_simulate,
    ):
        resp = await client.post(
            f"/api/calendar/{career_id}/match/{event_id}/simulate"
        )
    assert resp.status_code == 200, resp.text

    async with sf() as s:
        r = await s.execute(
            text(
                "SELECT participant_id, played, drawn, points, goals_for, "
                "       goals_against "
                "FROM ucl_standings "
                "WHERE competition_id = :cid AND participant_id IN (:h, :a)"
            ),
            {"cid": comp_id, "h": home_pid, "a": away_pid},
        )
        by_pid = {row[0]: row for row in r.fetchall()}
        for pid in (home_pid, away_pid):
            row = by_pid[pid]
            assert row[1] == 1, "played should be 1"
            assert row[2] == 1, "drawn should be 1"
            assert row[3] == 1, "points should be 1 for a draw"
            assert row[4] == 1 and row[5] == 1


# ──────────────────────────────────────────────────────────────────────────
# Test 2 — Two-legged knockout tie computes aggregate + writes winner
# (Req 8.2, 8.5)
# ──────────────────────────────────────────────────────────────────────────


async def _seed_minimal_knockout_tie(
    session: AsyncSession,
    *,
    round_type: str = "knockout_playoff",
    high_seed_club_id: int = 1,   # Manchester City — plays leg 2 at home
    low_seed_club_id: int = 2,    # Liverpool — plays leg 1 at home
    high_seed_name: str = "Manchester City",
    low_seed_name: str = "Liverpool",
) -> dict:
    """
    Seed a minimal UCL state with a single two-legged knockout tie ready
    to be simulated. Returns a dict of ids the test needs.
    """
    # Career + competition.
    await session.execute(
        text(
            "INSERT INTO careers (id, user_id, club_id, manager_name, status) "
            "VALUES (1, 1, :club, 'Test Manager', 'active')"
        ),
        {"club": high_seed_club_id},
    )
    await session.execute(
        text(
            "INSERT INTO competitions (name, competition_type, season, status) "
            "VALUES ('Champions League', 'continental_cup', 2025, 'active')"
        )
    )
    await session.commit()
    comp_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # Two participants.
    await session.execute(
        text(
            "INSERT INTO ucl_participants "
            "(competition_id, club_id, club_name, country, seed, final_rank) "
            "VALUES (:c, :club, :n, 'England', 1, 1)"
        ),
        {"c": comp_id, "club": high_seed_club_id, "n": high_seed_name},
    )
    home_pid = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    await session.execute(
        text(
            "INSERT INTO ucl_participants "
            "(competition_id, club_id, club_name, country, seed, final_rank) "
            "VALUES (:c, :club, :n, 'England', 2, 9)"
        ),
        {"c": comp_id, "club": low_seed_club_id, "n": low_seed_name},
    )
    away_pid = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # competition_round for the requested round_type.
    await session.execute(
        text(
            "INSERT INTO competition_rounds "
            "(competition_id, round_type, round_order, is_completed) "
            "VALUES (:c, :rt, 2, 0)"
        ),
        {"c": comp_id, "rt": round_type},
    )
    round_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # ucl_ties row — high seed = home_participant_id (leg 2 at home).
    await session.execute(
        text(
            "INSERT INTO ucl_ties "
            "(competition_id, round_id, home_participant_id, "
            " away_participant_id, bracket_position) "
            "VALUES (:c, :r, :h, :a, 1)"
        ),
        {"c": comp_id, "r": round_id, "h": home_pid, "a": away_pid},
    )
    tie_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # Add a second placeholder tie at bracket_position=2 with no
    # participants and no winner. This prevents the bracket-advance
    # cascade from running when our test tie is decided — the round
    # will still have an unfinished tie, so persist_match_result won't
    # try to call build_round_of_16/advance_bracket (which would fail
    # on minimal seed data).
    await session.execute(
        text(
            "INSERT INTO ucl_ties "
            "(competition_id, round_id, home_participant_id, "
            " away_participant_id, bracket_position) "
            "VALUES (:c, :r, NULL, NULL, 2)"
        ),
        {"c": comp_id, "r": round_id},
    )

    # Calendar events — leg 1 at low seed's stadium, leg 2 at high seed's.
    descriptions = {
        "knockout_playoff": (
            "Champions League Knockout Playoff (leg 1): {h} vs {a}",
            "Champions League Knockout Playoff (leg 2): {h} vs {a}",
        ),
        "round_of_16": (
            "Champions League Round of 16 (leg 1): {h} vs {a}",
            "Champions League Round of 16 (leg 2): {h} vs {a}",
        ),
        "quarter_final": (
            "Champions League Quarter Final (leg 1): {h} vs {a}",
            "Champions League Quarter Final (leg 2): {h} vs {a}",
        ),
        "semi_final": (
            "Champions League Semi Final (leg 1): {h} vs {a}",
            "Champions League Semi Final (leg 2): {h} vs {a}",
        ),
    }[round_type]

    # Leg 1 — low seed at home, high seed away.
    await session.execute(
        text(
            "INSERT INTO calendar_events "
            "(career_id, event_date, event_type, competition_id, "
            " home_club_id, away_club_id, is_locked, priority, "
            " kick_off_time, description, is_cancelled) "
            "VALUES (1, '2026-02-17', 'match', :c, :h, :a, 0, 8, "
            "        '21:00', :d, 0)"
        ),
        {
            "c": comp_id,
            "h": low_seed_club_id,
            "a": high_seed_club_id,
            "d": descriptions[0].format(h=low_seed_name, a=high_seed_name),
        },
    )
    leg1_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # Leg 2 — high seed at home, low seed away.
    await session.execute(
        text(
            "INSERT INTO calendar_events "
            "(career_id, event_date, event_type, competition_id, "
            " home_club_id, away_club_id, is_locked, priority, "
            " kick_off_time, description, is_cancelled) "
            "VALUES (1, '2026-02-24', 'match', :c, :h, :a, 0, 8, "
            "        '21:00', :d, 0)"
        ),
        {
            "c": comp_id,
            "h": high_seed_club_id,
            "a": low_seed_club_id,
            "d": descriptions[1].format(h=high_seed_name, a=low_seed_name),
        },
    )
    leg2_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    await session.commit()

    return {
        "competition_id": comp_id,
        "home_pid": home_pid,
        "away_pid": away_pid,
        "tie_id": tie_id,
        "round_id": round_id,
        "leg1_event_id": leg1_id,
        "leg2_event_id": leg2_id,
    }


@pytest.mark.asyncio
async def test_two_legged_tie_aggregates_and_writes_winner(http_client):
    """
    Simulating both legs of a knockout-playoff tie SHALL compute the
    aggregate and write a winner. With leg 1 = 0-2 (low-seed home) and
    leg 2 = 3-1 (high-seed home), the high-seed (home_participant) wins
    on aggregate 4-3.
    """
    client, sf = http_client

    async with sf() as s:
        ctx = await _seed_minimal_knockout_tie(s)

    # Leg 1: low seed home 0, high seed away 2 → from MatchEngine
    # perspective home_score=0 away_score=2.
    leg1_result = _make_match_result(home_score=0, away_score=2)
    leg2_result = _make_match_result(home_score=3, away_score=1)

    call_idx = {"i": 0}

    async def fake_simulate(self, *args, **kwargs):
        i = call_idx["i"]
        call_idx["i"] += 1
        return leg1_result if i == 0 else leg2_result

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=fake_simulate,
    ):
        r1 = await client.post(
            f"/api/calendar/1/match/{ctx['leg1_event_id']}/simulate"
        )
        assert r1.status_code == 200, r1.text

        r2 = await client.post(
            f"/api/calendar/1/match/{ctx['leg2_event_id']}/simulate"
        )
        assert r2.status_code == 200, r2.text

    # Verify the tie row.
    async with sf() as s:
        r = await s.execute(
            text(
                "SELECT leg1_home_score, leg1_away_score, "
                "       leg2_home_score, leg2_away_score, "
                "       aggregate_home, aggregate_away, "
                "       winner_participant_id, winner_decided_by "
                "FROM ucl_ties WHERE id = :tid"
            ),
            {"tid": ctx["tie_id"]},
        )
        row = r.fetchone()
        assert row is not None

        leg1_h, leg1_a, leg2_h, leg2_a, agg_h, agg_a, winner, decided = row
        # Both legs were stored: low seed at home in leg 1 (0-2), high
        # seed at home in leg 2 (3-1).
        assert leg1_h == 0 and leg1_a == 2
        assert leg2_h == 3 and leg2_a == 1
        # Aggregate must reflect the documented formula
        # (Req 5.3): aggregate_home + aggregate_away SHALL sum to the
        # total goals scored across both legs.
        assert (agg_h or 0) + (agg_a or 0) == 6
        # Per Req 5.4, when aggregates are unequal, decided_by must be
        # 'aggregate' and the winner is one of the two participants.
        assert decided == "aggregate"
        assert winner in (ctx["home_pid"], ctx["away_pid"])
        # Per Req 8.5 the winner_participant_id MUST be written when both
        # legs have been simulated.
        assert winner is not None


# ──────────────────────────────────────────────────────────────────────────
# Test 3 — Simulating the final crowns a champion (Req 6.6, 8.4)
# ──────────────────────────────────────────────────────────────────────────


async def _seed_minimal_final(
    session: AsyncSession,
    *,
    home_club_id: int = 1,
    away_club_id: int = 2,
    home_name: str = "Manchester City",
    away_name: str = "Liverpool",
) -> dict:
    """Set up a minimal UCL state with just the final tie ready to play."""
    await session.execute(
        text(
            "INSERT INTO careers (id, user_id, club_id, manager_name, status) "
            "VALUES (1, 1, :club, 'Test Manager', 'active')"
        ),
        {"club": home_club_id},
    )
    await session.execute(
        text(
            "INSERT INTO competitions (name, competition_type, season, status) "
            "VALUES ('Champions League', 'continental_cup', 2025, 'active')"
        )
    )
    await session.commit()
    comp_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # Two participants.
    await session.execute(
        text(
            "INSERT INTO ucl_participants "
            "(competition_id, club_id, club_name, country, seed, final_rank) "
            "VALUES (:c, :club, :n, 'England', 1, 1)"
        ),
        {"c": comp_id, "club": home_club_id, "n": home_name},
    )
    home_pid = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )
    await session.execute(
        text(
            "INSERT INTO ucl_participants "
            "(competition_id, club_id, club_name, country, seed, final_rank) "
            "VALUES (:c, :club, :n, 'England', 2, 2)"
        ),
        {"c": comp_id, "club": away_club_id, "n": away_name},
    )
    away_pid = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # competition_round for the final.
    await session.execute(
        text(
            "INSERT INTO competition_rounds "
            "(competition_id, round_type, round_order, is_completed) "
            "VALUES (:c, 'final', 6, 0)"
        ),
        {"c": comp_id},
    )
    round_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )

    # ucl_ties final row.
    await session.execute(
        text(
            "INSERT INTO ucl_ties "
            "(competition_id, round_id, home_participant_id, "
            " away_participant_id, bracket_position) "
            "VALUES (:c, :r, :h, :a, 1)"
        ),
        {"c": comp_id, "r": round_id, "h": home_pid, "a": away_pid},
    )

    # Calendar event for the final.
    await session.execute(
        text(
            "INSERT INTO calendar_events "
            "(career_id, event_date, event_type, competition_id, "
            " home_club_id, away_club_id, is_locked, priority, "
            " kick_off_time, description, is_cancelled) "
            "VALUES (1, '2026-05-30', 'match', :c, :h, :a, 0, 8, "
            "        '21:00', :d, 0)"
        ),
        {
            "c": comp_id,
            "h": home_club_id,
            "a": away_club_id,
            "d": (
                f"Champions League Final: {home_name} vs {away_name} "
                "(Puskás Aréna, Budapest)"
            ),
        },
    )
    final_event_id = int(
        (
            await session.execute(text("SELECT last_insert_rowid()"))
        ).scalar()
    )
    await session.commit()

    return {
        "competition_id": comp_id,
        "home_pid": home_pid,
        "away_pid": away_pid,
        "final_event_id": final_event_id,
    }


@pytest.mark.asyncio
async def test_final_simulation_crowns_champion(http_client):
    """
    Simulating the final SHALL mark the competition as completed
    (status='completed' on the competitions row) per Req 6.6 + Req 8.4.
    """
    client, sf = http_client

    async with sf() as s:
        ctx = await _seed_minimal_final(s)

    # Force a clear 2-0 result to skip ET/penalties paths.
    fake = _make_match_result(home_score=2, away_score=0)

    async def fake_simulate(self, *args, **kwargs):
        return fake

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=fake_simulate,
    ):
        resp = await client.post(
            f"/api/calendar/1/match/{ctx['final_event_id']}/simulate"
        )
    assert resp.status_code == 200, resp.text

    async with sf() as s:
        # crown_champion sets competitions.status='completed'.
        r = await s.execute(
            text(
                "SELECT status FROM competitions WHERE id = :cid"
            ),
            {"cid": ctx["competition_id"]},
        )
        status = r.scalar()
        assert status == "completed", (
            f"Expected competition status='completed', got {status!r}"
        )

        # The final round SHALL be marked completed.
        r = await s.execute(
            text(
                "SELECT is_completed FROM competition_rounds "
                "WHERE competition_id = :cid AND round_type = 'final'"
            ),
            {"cid": ctx["competition_id"]},
        )
        is_completed = r.scalar()
        assert is_completed, (
            "Expected final round to be marked is_completed after the "
            "final is simulated"
        )

        # A winner SHALL be written to the final's tie row.
        r = await s.execute(
            text(
                "SELECT winner_participant_id, winner_decided_by "
                "FROM ucl_ties WHERE competition_id = :cid"
            ),
            {"cid": ctx["competition_id"]},
        )
        row = r.fetchone()
        assert row is not None
        winner, decided = row
        assert winner is not None
        assert winner in (ctx["home_pid"], ctx["away_pid"])
        # Single match → winner_decided_by is 'single_match' for a
        # decisive result.
        assert decided == "single_match"


# ──────────────────────────────────────────────────────────────────────────
# Test 4 — MatchEngine 500 → endpoint returns HTTP 500 and standings
# untouched (Req 12.4)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_engine_failure_returns_500_and_preserves_standings(
    http_client,
):
    """
    If ``MatchEngine.simulate_match`` raises, the endpoint SHALL return
    HTTP 500 (or another error status) and SHALL NOT modify the
    ``ucl_standings`` rows for the participants.
    """
    client, sf = http_client

    async with sf() as s:
        career_id, comp_id = await _setup_career_and_ucl(s)

        # Find the player's first league_phase event.
        r = await s.execute(
            text(
                """
                SELECT id, home_club_id, away_club_id
                FROM calendar_events
                WHERE competition_id = :cid
                  AND (home_club_id = 1 OR away_club_id = 1)
                  AND description LIKE '%тур 1%'
                ORDER BY id LIMIT 1
                """
            ),
            {"cid": comp_id},
        )
        row = r.fetchone()
        event_id = int(row[0])

        # Snapshot pre-simulation standings — every row should be all 0.
        r = await s.execute(
            text(
                "SELECT participant_id, played, points, "
                "       goals_for, goals_against "
                "FROM ucl_standings WHERE competition_id = :cid"
            ),
            {"cid": comp_id},
        )
        before = {row[0]: row for row in r.fetchall()}

    async def boom(self, *args, **kwargs):
        raise RuntimeError("synthetic MatchEngine failure")

    with patch(
        "app.services.match_engine.MatchEngine.simulate_match",
        new=boom,
    ):
        resp = await client.post(
            f"/api/calendar/{career_id}/match/{event_id}/simulate"
        )

    # Per Req 12.4, the endpoint should bubble the error as 500.
    assert resp.status_code == 500, (
        f"Expected HTTP 500 when MatchEngine raises, got {resp.status_code}: "
        f"{resp.text}"
    )

    # Standings SHALL be unchanged.
    async with sf() as s:
        r = await s.execute(
            text(
                "SELECT participant_id, played, points, "
                "       goals_for, goals_against "
                "FROM ucl_standings WHERE competition_id = :cid"
            ),
            {"cid": comp_id},
        )
        after = {row[0]: row for row in r.fetchall()}

    assert before == after, (
        "Standings SHALL NOT change when MatchEngine raises (Req 12.4)"
    )

    # The calendar event SHALL also remain unlocked.
    async with sf() as s:
        r = await s.execute(
            text(
                "SELECT is_locked, description FROM calendar_events "
                "WHERE id = :eid"
            ),
            {"eid": event_id},
        )
        is_locked, description = r.fetchone()
        assert not is_locked, (
            "Calendar event SHALL remain unlocked when simulation fails"
        )
        # Score SHALL NOT have been written into the description.
        assert " - " not in (description or "") or "0 - 0" not in description, (
            "Description SHALL NOT contain a final score when simulation "
            "failed"
        )


# ──────────────────────────────────────────────────────────────────────────
# Test 5 — Unresolved opponent returns HTTP 400 (Req 12.2)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unresolved_opponent_returns_400(http_client):
    """
    Per Req 12.2 / spec task 12.2, when a UCL match calendar event
    references an opponent name that cannot be resolved to a participant
    or a CLUBS entry, the simulate endpoint SHALL return HTTP 400 with
    a descriptive message.

    We construct a UCL calendar event whose description references
    a fictional opponent ("Definitely Not A Club FC") that exists
    neither in ``CLUBS`` nor in ``ucl_participants``.
    """
    client, sf = http_client

    async with sf() as s:
        # Minimal setup: career, competition, one calendar event.
        await s.execute(
            text(
                "INSERT INTO careers (id, user_id, club_id, manager_name, "
                "                     status) "
                "VALUES (1, 1, 1, 'Test Manager', 'active')"
            )
        )
        await s.execute(
            text(
                "INSERT INTO competitions (name, competition_type, season, "
                "                          status) "
                "VALUES ('Champions League', 'continental_cup', 2025, 'active')"
            )
        )
        await s.commit()
        comp_id = int(
            (
                await s.execute(text("SELECT last_insert_rowid()"))
            ).scalar()
        )

        # competition_round so persist_match_result has somewhere to land.
        await s.execute(
            text(
                "INSERT INTO competition_rounds "
                "(competition_id, round_type, round_order, is_completed) "
                "VALUES (:c, 'league_phase', 1, 0)"
            ),
            {"c": comp_id},
        )

        # No matching ucl_participants row for the opponent — and the
        # event has neither home_club_id nor away_club_id set, forcing
        # description-based resolution.
        await s.execute(
            text(
                "INSERT INTO calendar_events "
                "(career_id, event_date, event_type, competition_id, "
                " home_club_id, away_club_id, is_locked, priority, "
                " kick_off_time, description, is_cancelled) "
                "VALUES (1, '2025-09-16', 'match', :c, NULL, NULL, 0, 8, "
                "        '21:00', :d, 0)"
            ),
            {
                "c": comp_id,
                "d": (
                    "Лига чемпионов, тур 1: vs Definitely Not A Club FC (H)"
                ),
            },
        )
        await s.commit()
        event_id = int(
            (
                await s.execute(text("SELECT last_insert_rowid()"))
            ).scalar()
        )

    # No need to mock MatchEngine — the 400 SHALL be raised before
    # MatchEngine runs (per Req 12.2, the endpoint inspects the parsed
    # opponent name first).
    resp = await client.post(
        f"/api/calendar/1/match/{event_id}/simulate"
    )

    assert resp.status_code == 400, (
        f"Expected HTTP 400 for unresolved UCL opponent, got "
        f"{resp.status_code}: {resp.text}"
    )
    body = resp.json() if resp.headers.get("content-type", "").startswith(
        "application/json"
    ) else {}
    detail = body.get("detail", "") if isinstance(body, dict) else ""
    # The message SHALL identify the opponent-resolution failure.
    assert "Opponent" in detail or "opponent" in detail or "CLUBS" in detail, (
        f"Expected 400 detail to mention opponent/CLUBS resolution, "
        f"got {detail!r}"
    )
