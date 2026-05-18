"""
Integration tests for the Medical API endpoint (Task 14.4).

Covers GET /api/careers/{career_id}/injuries which exposes
MedicalService.get_injury_list to the frontend medical centre screen.

Validates Requirement 11.4 (injury list screen).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import AsyncGenerator, Tuple

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db, get_db_session
from app.main import app
from app.models.career import Career
from app.models.club import Club
from app.models.injury import Injury, InjurySeverity, InjuryStatus
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.user import User


# ─────────────────────────── Schema bootstrap ──────────────────────────


def _build_schema(sync_conn):
    """Create the subset of tables touched by the route under test.

    Filters out PostgreSQL-only indexes (FTS / tsvector) so the schema
    can be created against an in-memory SQLite engine.
    """
    for table in Base.metadata.sorted_tables:
        pg_indexes = [
            idx
            for idx in table.indexes
            if "fts" in idx.name or "tsvector" in str(idx.expressions)
        ]
        for idx in pg_indexes:
            table.indexes.discard(idx)

        table.create(sync_conn, checkfirst=True)

        for idx in pg_indexes:
            table.indexes.add(idx)


@pytest.fixture
async def engine():
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
    """Build an ASGI test client with DB + auth dependencies overridden."""
    from app.api.dependencies import get_current_user as dep_get_current_user

    async def override_get_db():
        async with session_factory() as s:
            yield s

    # Stand-in user matching the seeded career.user_id.
    class _StubUser:
        id = 1

    async def override_get_current_user():
        return _StubUser()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[dep_get_current_user] = override_get_current_user

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client, session_factory

    app.dependency_overrides.clear()


# ─────────────────────────── Seed helpers ──────────────────────────────


async def _seed_career(session: AsyncSession) -> Tuple[int, int, int]:
    """
    Seed a user, club, career, player and squad_player. Returns
    (career_id, player_id, squad_player_id).
    """
    user = User(
        id=1,
        telegram_user_id=987654321,
        username="medic_test",
        first_name="Med",
        last_name="Tester",
    )
    session.add(user)
    await session.flush()

    club = Club(
        name="Medic FC",
        league="Premier League",
        country="England",
        reputation=70,
    )
    session.add(club)
    await session.flush()

    career = Career(
        user_id=user.id,
        club_id=club.id,
        manager_name="Med Manager",
        current_season=1,
        current_week=10,
    )
    session.add(career)
    await session.flush()

    player = Player(
        uid="MED_TEST_001",
        name="Bruno Tester",
        position="ST",
        age=27,
        nationality="England",
        club="Medic FC",
        ca=140,
        pa=160,
        # Required attribute columns (model NOT NULL).
        corners=10, crossing=10, dribbling=12, finishing=14, first_touch=12,
        free_kicks=8, heading=11, long_shots=11, long_throws=5, marking=6,
        passing=12, penalty=12, tackling=7, technique=13,
        aggression=12, anticipation=12, bravery=12, composure=12,
        concentration=12, decisions=12, determination=14, flair=11,
        leadership=10, off_the_ball=13, positioning=8, teamwork=12,
        vision=11, work_rate=14,
        acceleration=14, agility=13, balance=12, jumping=11,
        stamina=15, pace=14, endurance=14, strength=12,
        price="£10M", wage=80000, height=180, weight=75,
        left_foot=15, right_foot=10,
    )
    session.add(player)
    await session.flush()

    sp = SquadPlayer(
        career_id=career.id,
        player_id=player.id,
        squad_number=9,
        squad_status="FIRST_TEAM",
        wage=80000,
        contract_start_date=date.today(),
        contract_end_date=date.today() + timedelta(days=365 * 3),
    )
    session.add(sp)
    await session.flush()
    await session.commit()

    return career.id, player.id, sp.id


# ──────────────────────────── Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_injury_list_endpoint_empty(http_client):
    """When no injuries exist the endpoint returns an empty list."""
    client, sf = http_client
    async with sf() as s:
        career_id, _, _ = await _seed_career(s)

    resp = await client.get(f"/api/careers/{career_id}/injuries")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["career_id"] == career_id
    assert body["count"] == 0
    assert body["injuries"] == []


@pytest.mark.asyncio
async def test_injury_list_endpoint_returns_active_and_recovering(http_client):
    """
    Active and recovering injuries should be returned with the player's
    name, position, severity, status and expected return date.
    Recovered injuries must NOT appear (Requirement 11.4).
    """
    client, sf = http_client

    async with sf() as s:
        career_id, player_id, sp_id = await _seed_career(s)

    now = datetime.now()

    async with sf() as s:
        s.add_all(
            [
                Injury(
                    career_id=career_id,
                    player_id=player_id,
                    squad_player_id=sp_id,
                    injury_type="Hamstring Strain",
                    severity=InjurySeverity.MODERATE,
                    status=InjuryStatus.ACTIVE,
                    injury_date=now - timedelta(days=7),
                    expected_recovery_date=now + timedelta(days=14),
                    recovery_weeks=3,
                    season=1,
                    week=10,
                    sharpness_penalty=10,
                ),
                Injury(
                    career_id=career_id,
                    player_id=player_id,
                    squad_player_id=sp_id,
                    injury_type="Ankle Sprain",
                    severity=InjurySeverity.MINOR,
                    status=InjuryStatus.RECOVERING,
                    injury_date=now - timedelta(days=20),
                    expected_recovery_date=now - timedelta(days=2),
                    actual_recovery_date=now - timedelta(days=2),
                    recovery_weeks=2,
                    season=1,
                    week=8,
                    sharpness_penalty=10,
                ),
                Injury(
                    career_id=career_id,
                    player_id=player_id,
                    squad_player_id=sp_id,
                    injury_type="Common Cold",
                    severity=InjurySeverity.MINOR,
                    status=InjuryStatus.RECOVERED,
                    injury_date=now - timedelta(days=40),
                    expected_recovery_date=now - timedelta(days=33),
                    actual_recovery_date=now - timedelta(days=33),
                    full_recovery_date=now - timedelta(days=20),
                    recovery_weeks=1,
                    season=1,
                    week=5,
                    sharpness_penalty=0,
                ),
            ]
        )
        await s.commit()

    resp = await client.get(f"/api/careers/{career_id}/injuries")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["career_id"] == career_id
    assert body["count"] == 2
    statuses = {row["status"] for row in body["injuries"]}
    assert statuses == {"active", "recovering"}

    types = {row["injury_type"] for row in body["injuries"]}
    assert types == {"Hamstring Strain", "Ankle Sprain"}

    # Each row must carry the screen fields the frontend renders.
    for row in body["injuries"]:
        assert row["player_name"] == "Bruno Tester"
        assert row["position"] == "ST"
        assert row["severity"] in {"minor", "moderate", "severe"}
        assert "expected_recovery_date" in row


@pytest.mark.asyncio
async def test_injury_list_endpoint_404_for_unknown_career(http_client):
    """Requesting a non-existent career returns 404."""
    client, _ = http_client
    resp = await client.get("/api/careers/9999/injuries")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_injury_list_endpoint_403_for_wrong_user(http_client, session_factory):
    """A career belonging to another user returns 403."""
    # Seed a career owned by user_id=2 (the stub user is id=1).
    async with session_factory() as s:
        other_user = User(
            id=2,
            telegram_user_id=111222333,
            username="other",
            first_name="Other",
            last_name="User",
        )
        s.add(other_user)
        await s.flush()

        club = Club(name="Other FC", league="L1", country="France", reputation=60)
        s.add(club)
        await s.flush()

        career = Career(
            user_id=other_user.id,
            club_id=club.id,
            manager_name="Other Manager",
            current_season=1,
            current_week=1,
        )
        s.add(career)
        await s.flush()
        await s.commit()
        career_id = career.id

    client, _ = http_client
    resp = await client.get(f"/api/careers/{career_id}/injuries")
    assert resp.status_code == 403
