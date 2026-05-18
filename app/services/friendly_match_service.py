"""
FriendlyMatchService — Validation + orchestration for user-arranged friendly matches.

This service validates user-arranged friendly match requests, persists them into
``calendar_events`` via :class:`CalendarEngine.add_friendly_match`, and supports
soft-cancelling existing friendlies.

Architecture: pure helpers + DB-aware helpers + two public coroutines
(``create_friendly``, ``cancel_friendly``). All errors raised by validation
helpers are :class:`ValidationError` instances carrying a Russian-language
message and an HTTP status code, intended to be re-raised as
``HTTPException`` by the FastAPI route layer.

See: .kiro/specs/friendly-matches/requirements.md
     .kiro/specs/friendly-matches/design.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.club_budgets import CLUBS
from app.data.tour_venues import get_tour_venue_by_id


# ─── Module constants ─────────────────────────────────────────────────────────

KICK_OFF_REGEX = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
VALID_MATCH_TYPES = {"home", "away", "commercial_tour", "closed_door"}
PRESEASON_START_MMDD = (7, 15)
PRESEASON_END_MMDD = (8, 10)


# ─── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class FriendlyCreateRequest:
    """Validated input for creating a friendly match."""

    event_date: date
    opponent_club_id: int
    match_type: str  # "home" | "away" | "commercial_tour" | "closed_door"
    kick_off_time: str = "18:00"
    tour_venue_id: Optional[int] = None
    description_suffix: Optional[str] = None  # extra free-form text


@dataclass
class FriendlyCreateResult:
    """Result of a successful friendly creation."""

    event_id: int
    event_date: date
    kick_off_time: str
    home_club_id: int
    away_club_id: int
    description: str
    travel_data: dict
    warnings: List[str] = field(default_factory=list)


# ─── Errors ───────────────────────────────────────────────────────────────────


class ValidationError(Exception):
    """Raised when a friendly cannot be created or cancelled.

    Carries a Russian-language ``message`` intended to be surfaced directly to
    the user, and an ``http_status`` used by the route layer to choose the
    right HTTP response code.
    """

    def __init__(self, message: str, http_status: int = 422):
        super().__init__(message)
        self.message = message
        self.http_status = http_status


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _parse_event_date(value) -> date:
    """Coerce a DB ``event_date`` value to a ``date`` instance.

    The ``calendar_events.event_date`` column is declared as ``Date`` in the
    SQLAlchemy model but stored by the existing CalendarEngine as a
    ``"YYYY-MM-DD"`` string (see ``calendar_engine.py`` — ``str(event_date)``).
    SQLite returns it as a string; other drivers may return a ``date`` already.
    """
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


# ─── Service ──────────────────────────────────────────────────────────────────


class FriendlyMatchService:
    """Validates user-arranged friendly matches and persists them."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Pure validation helpers ───────────────────────────────────────────

    def _validate_match_type(self, match_type: str) -> None:
        """Raise ``ValidationError`` if ``match_type`` is not in
        :data:`VALID_MATCH_TYPES`.
        """
        if match_type not in VALID_MATCH_TYPES:
            raise ValidationError("Неверный тип матча", http_status=422)

    def _validate_kick_off(self, kick_off_time: str) -> None:
        """Raise ``ValidationError`` when ``kick_off_time`` does not match
        :data:`KICK_OFF_REGEX` (``HH:MM`` 24-hour format).
        """
        if not isinstance(kick_off_time, str) or not KICK_OFF_REGEX.match(kick_off_time):
            raise ValidationError("Неверный формат времени начала", http_status=422)

    def _validate_opponent(self, opponent_club_id: int, player_club_id: int) -> None:
        """Raise ``ValidationError`` if the opponent id is out of range or
        equals the player's own club id.
        """
        if opponent_club_id < 1 or opponent_club_id > len(CLUBS):
            raise ValidationError("Неверный соперник", http_status=422)
        if opponent_club_id == player_club_id:
            raise ValidationError("Нельзя играть против самого себя", http_status=422)

    def _validate_tour_venue(
        self, match_type: str, tour_venue_id: Optional[int]
    ) -> Optional[dict]:
        """Look up the venue for a commercial-tour friendly.

        Returns the venue dict when ``match_type == "commercial_tour"``; raises
        ``ValidationError`` if the id is missing or unknown. Returns ``None``
        for all other match types.
        """
        if match_type != "commercial_tour":
            return None
        if tour_venue_id is None:
            raise ValidationError(
                "Для коммерческого тура необходимо выбрать площадку",
                http_status=422,
            )
        venue = get_tour_venue_by_id(tour_venue_id)
        if venue is None:
            raise ValidationError(
                "Для коммерческого тура необходимо выбрать площадку",
                http_status=422,
            )
        return venue

    def _resolve_home_away(
        self,
        match_type: str,
        player_club_id: int,
        opponent_club_id: int,
    ) -> tuple[int, int]:
        """Resolve ``(home_club_id, away_club_id)`` from match_type.

        - ``"away"`` → ``(opponent, player)``
        - everything else → ``(player, opponent)``
        """
        if match_type == "away":
            return (opponent_club_id, player_club_id)
        return (player_club_id, opponent_club_id)

    def _build_description(
        self,
        match_type: str,
        home_name: str,
        away_name: str,
        venue: Optional[dict],
        suffix: Optional[str],
    ) -> str:
        """Compose the event description per Requirements 6.2-6.4."""
        description = f"Товарищеский матч: {home_name} – {away_name}"
        if match_type == "closed_door":
            description += " (закрытый)"
        elif match_type == "commercial_tour" and venue is not None:
            description += f" — {venue['city']}"
        if suffix:
            description += f" [{suffix}]"
        return description

    def _build_travel_data(
        self,
        match_type: str,
        venue: Optional[dict],
    ) -> dict:
        """Build the JSON-serialisable ``travel_data`` per Requirements 6.5-6.7."""
        if match_type == "closed_door":
            return {"match_subtype": "closed_door", "venue": "training_ground"}
        if match_type == "commercial_tour" and venue is not None:
            return {
                "match_subtype": "commercial_tour",
                "city": venue["city"],
                "country": venue["country"],
                "stadium_name": venue["stadium_name"],
            }
        # home / away
        return {"match_subtype": match_type}

    # ── DB-aware helpers ──────────────────────────────────────────────────

    async def _get_player_club_id(self, career_id: int) -> int:
        """Read ``careers.club_id`` for the given career.

        Raises ``ValidationError(422, "Карьера не найдена")`` when the row
        does not exist.
        """
        result = await self.session.execute(
            text("SELECT club_id FROM careers WHERE id = :cid"),
            {"cid": career_id},
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            raise ValidationError("Карьера не найдена", http_status=422)
        return int(row[0])

    async def _resolve_season_window(self, career_id: int) -> tuple[date, date]:
        """Return ``(season_start, season_end)`` for the career.

        Reads MIN/MAX of ``calendar_events.event_date`` (excluding cancelled
        rows). Falls back to ``(today, today + 365 days)`` when the calendar
        is empty.

        We pad the window AT LEAST to (July 1 .. June 30) of the relevant
        season year because:
        - league fixtures don't start until mid-August, but pre-season
          friendlies typically start July 1-15. Without the pad, scheduling
          a friendly on July 3 would fail with "Дата вне игрового сезона"
          even though that's literally pre-season.
        - the latest official fixture (UCL final) is usually late May, but
          some career timelines extend to end of June — the pad keeps that
          window valid too.
        """
        result = await self.session.execute(
            text(
                """
                SELECT MIN(event_date), MAX(event_date)
                FROM calendar_events
                WHERE career_id = :cid AND is_cancelled = 0
                """
            ),
            {"cid": career_id},
        )
        row = result.fetchone()
        if row is None or row[0] is None or row[1] is None:
            today = date.today()
            return (today, today + timedelta(days=365))
        s_start = _parse_event_date(row[0])
        s_end = _parse_event_date(row[1])
        # Pad to the "natural" season bounds (July 1 .. June 30 of next year).
        natural_start = date(s_start.year, 7, 1)
        natural_end = date(s_start.year + 1, 6, 30)
        if s_start > natural_start:
            s_start = natural_start
        if s_end < natural_end:
            s_end = natural_end
        return (s_start, s_end)

    async def _existing_events_around(
        self,
        career_id: int,
        event_date: date,
    ) -> list[dict]:
        """Return non-cancelled events for this career within ±2 days of
        ``event_date``.

        Each item is a dict with ``id``, ``event_date`` (as ``date``),
        ``event_type``, ``priority``, ``is_locked``.
        """
        d1 = event_date - timedelta(days=2)
        d2 = event_date + timedelta(days=2)
        result = await self.session.execute(
            text(
                """
                SELECT id, event_date, event_type, priority, is_locked
                FROM calendar_events
                WHERE career_id = :cid
                  AND is_cancelled = 0
                  AND event_date BETWEEN :d1 AND :d2
                """
            ),
            {"cid": career_id, "d1": str(d1), "d2": str(d2)},
        )
        rows = result.fetchall()
        events: list[dict] = []
        for r in rows:
            events.append(
                {
                    "id": int(r[0]),
                    "event_date": _parse_event_date(r[1]),
                    "event_type": r[2],
                    "priority": int(r[3]) if r[3] is not None else 0,
                    "is_locked": bool(r[4]),
                }
            )
        return events

    def _check_window(
        self,
        event_date: date,
        season_start: date,
        season_end: date,
    ) -> List[str]:
        """Validate the date is inside the season; emit pre-season warning.

        Raises ``ValidationError`` when the date is outside ``[season_start,
        season_end]``. Appends ``"Дата вне предсезонного окна"`` to warnings
        when the date is outside July 15 – August 10 of the season's start
        year.
        """
        if event_date < season_start or event_date > season_end:
            raise ValidationError("Дата вне игрового сезона", http_status=422)

        warnings: List[str] = []
        preseason_start = date(season_start.year, *PRESEASON_START_MMDD)
        preseason_end = date(season_start.year, *PRESEASON_END_MMDD)
        if event_date < preseason_start or event_date > preseason_end:
            warnings.append("Дата вне предсезонного окна")
        return warnings

    def _check_conflicts(
        self,
        event_date: date,
        existing: list[dict],
    ) -> List[str]:
        """Apply blocking rules (Property 9) in order; return soft warnings.

        Hard conflicts raise ``ValidationError(422)`` with the matching
        Russian-language message. Rules are checked in the listed order
        across all existing events; the first matching rule wins.
        """
        warnings: List[str] = []

        # Rule 1: same-day official match (priority >= 4).
        for ev in existing:
            if (
                ev["event_date"] == event_date
                and ev["event_type"] == "match"
                and ev["priority"] >= 4
            ):
                raise ValidationError(
                    "На эту дату уже запланирован официальный матч",
                    http_status=422,
                )

        # Rule 2: same-day locked event of any kind.
        for ev in existing:
            if ev["event_date"] == event_date and ev["is_locked"]:
                raise ValidationError(
                    "Дата заблокирована (международный перерыв или мандатный матч)",
                    http_status=422,
                )

        # Rule 3: same-day international event.
        for ev in existing:
            if (
                ev["event_date"] == event_date
                and ev["event_type"] == "international"
            ):
                raise ValidationError(
                    "Дата попадает на международный перерыв",
                    http_status=422,
                )

        # Rule 4: any match within 48 hours (different day).
        for ev in existing:
            if (
                ev["event_type"] == "match"
                and abs((ev["event_date"] - event_date).days) < 2
                and ev["event_date"] != event_date
            ):
                raise ValidationError(
                    "Между матчами должно быть не менее 48 часов",
                    http_status=422,
                )

        # Rule 5: same-day non-cancelled friendly (priority 2).
        for ev in existing:
            if (
                ev["event_date"] == event_date
                and ev["event_type"] == "match"
                and ev["priority"] == 2
            ):
                raise ValidationError(
                    "На эту дату уже запланирован товарищеский матч",
                    http_status=422,
                )

        # Soft warning: target date overlaps an international event.
        for ev in existing:
            if (
                ev["event_type"] == "international"
                and ev["event_date"] == event_date
            ):
                warnings.append("Часть игроков на международных матчах")
                break

        return warnings

    # ── Public API ────────────────────────────────────────────────────────

    async def create_friendly(
        self,
        career_id: int,
        request: FriendlyCreateRequest,
    ) -> FriendlyCreateResult:
        """Validate and persist a user-arranged friendly match."""
        # 1. Format-level validation (cheap, fail-fast).
        self._validate_match_type(request.match_type)
        self._validate_kick_off(request.kick_off_time)

        # 2. Player club + opponent.
        player_club_id = await self._get_player_club_id(career_id)
        self._validate_opponent(request.opponent_club_id, player_club_id)

        # 3. Tour venue (commercial_tour only).
        venue = self._validate_tour_venue(request.match_type, request.tour_venue_id)

        # 4. Season window + nearby events.
        season_start, season_end = await self._resolve_season_window(career_id)
        existing = await self._existing_events_around(career_id, request.event_date)

        # 5. Window check (may raise) + conflict check (may raise).
        warnings: List[str] = []
        warnings.extend(self._check_window(request.event_date, season_start, season_end))
        warnings.extend(self._check_conflicts(request.event_date, existing))

        # 6. Resolve home/away ids and human-readable names.
        home_club_id, away_club_id = self._resolve_home_away(
            request.match_type, player_club_id, request.opponent_club_id
        )
        # CLUBS is 0-indexed; ids are 1-based.
        home_name = CLUBS[home_club_id - 1][0]
        away_name = CLUBS[away_club_id - 1][0]

        # 7. Build description and travel_data.
        description = self._build_description(
            request.match_type,
            home_name,
            away_name,
            venue,
            request.description_suffix,
        )
        travel_data = self._build_travel_data(request.match_type, venue)

        # 8. Persist via CalendarEngine. Imported lazily to avoid any
        #    unintended import cycles.
        from app.services.calendar_engine import CalendarEngine

        engine = CalendarEngine(self.session)
        event = await engine.add_friendly_match(
            career_id=career_id,
            event_date=request.event_date,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            kick_off_time=request.kick_off_time,
            description=description,
            travel_data=travel_data,
        )

        return FriendlyCreateResult(
            event_id=int(event["id"]),
            event_date=request.event_date,
            kick_off_time=request.kick_off_time,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            description=description,
            travel_data=travel_data,
            warnings=warnings,
        )

    async def cancel_friendly(
        self,
        career_id: int,
        event_id: int,
    ) -> int:
        """Soft-cancel a user-arranged friendly. See Property 11."""
        result = await self.session.execute(
            text(
                """
                SELECT id, event_type, priority, is_locked
                FROM calendar_events
                WHERE id = :eid AND career_id = :cid AND is_cancelled = 0
                """
            ),
            {"eid": event_id, "cid": career_id},
        )
        row = result.fetchone()
        if row is None:
            raise ValidationError("Товарищеский матч не найден", http_status=404)

        ev_type = row[1]
        ev_priority = int(row[2]) if row[2] is not None else 0
        ev_locked = bool(row[3])

        if ev_type != "match" or ev_priority != 2:
            raise ValidationError("Это не товарищеский матч", http_status=400)
        if ev_locked:
            raise ValidationError(
                "Нельзя отменить уже сыгранный матч", http_status=409
            )

        await self.session.execute(
            text("UPDATE calendar_events SET is_cancelled = 1 WHERE id = :eid"),
            {"eid": event_id},
        )
        await self.session.commit()
        return event_id
