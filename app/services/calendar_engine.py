"""
CalendarEngine — Core generation, conflict detection, and rescheduling
for the club season calendar.
"""

import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.league_configs import get_league_config_for_club, FIFA_INTERNATIONAL_WINDOWS
from app.data.club_budgets import CLUBS


# ─── Supporting Dataclasses ───────────────────────────────────────────────────


@dataclass
class SeasonBlock:
    """A structural block of the season."""
    name: str
    start_date: date
    end_date: date


@dataclass
class Conflict:
    """Represents a scheduling conflict between events."""
    existing_event_id: int
    new_event_date: date
    conflict_type: str  # "same_date", "48h_rule", "overload"
    suggested_date: Optional[date]


@dataclass
class ConflictReport:
    """Report of a conflict and its resolution status."""
    event_date: date
    conflict: Conflict
    resolved: bool
    resolution: Optional[str]


@dataclass
class OverloadWarning:
    """Warning when 3+ matches fall within a 7-day window."""
    club_id: int
    start_date: date
    end_date: date
    match_count: int
    lowest_priority_event_id: int


@dataclass
class RecalculationResult:
    """Result of a weekly calendar recalculation."""
    new_events: List[dict] = field(default_factory=list)
    rescheduled_events: List[dict] = field(default_factory=list)
    cancelled_events: List[dict] = field(default_factory=list)
    warnings: List[OverloadWarning] = field(default_factory=list)
    reminders: List[dict] = field(default_factory=list)


@dataclass
class KickOffSlot:
    """A kick-off time slot with TV and revenue info."""
    day_of_week: str  # "saturday", "sunday", "friday", "monday"
    time: str  # "15:00", "12:30", "16:30", "20:00"
    is_tv_slot: bool
    revenue_multiplier: float  # 1.0 default, 1.3-1.5 for TV slots


# ─── Kick-off slot definitions ────────────────────────────────────────────────

KICK_OFF_SLOTS = [
    KickOffSlot(day_of_week="saturday", time="15:00", is_tv_slot=False, revenue_multiplier=1.0),
    KickOffSlot(day_of_week="saturday", time="12:30", is_tv_slot=True, revenue_multiplier=1.3),
    KickOffSlot(day_of_week="friday", time="20:00", is_tv_slot=True, revenue_multiplier=1.4),
    KickOffSlot(day_of_week="sunday", time="16:30", is_tv_slot=True, revenue_multiplier=1.5),
    KickOffSlot(day_of_week="monday", time="20:00", is_tv_slot=True, revenue_multiplier=1.3),
]


# ─── CalendarEngine ───────────────────────────────────────────────────────────


class CalendarEngine:
    """Generates, manages, and updates the club season calendar."""

    def __init__(self, session: AsyncSession):
        self.session = session
        # Lazy imports to avoid circular dependencies at module load
        try:
            from app.services.weather_generator import WeatherGenerator
            self.weather = WeatherGenerator()
        except ImportError:
            self.weather = None
        try:
            from app.services.travel_planner import TravelPlanner
            self.travel = TravelPlanner()
        except ImportError:
            self.travel = None

    # ─── Season Generation ────────────────────────────────────────────────────

    async def generate_season(
        self,
        career_id: int,
        club_id: int,
        club_name: str,
        year: int,
    ) -> List[dict]:
        """
        Generate a full season calendar for a career.
        Called once on career creation.

        Steps:
        1. Get league config for the club
        2. Create season blocks (5 blocks)
        3. Generate milestone events
        4. Place international windows (priority 10, locked)
        5. Generate league matchdays every Saturday, skipping intl windows & winter break
        6. Place pre-season events (medical, training camp, friendlies)
        7. Generate pre-match day events for each match
        8. Assign kick-off times
        9. Insert all events into DB via raw SQL

        Returns: List of all created event dicts.
        """
        # 1. Get league config
        league_config = get_league_config_for_club(club_name)
        if not league_config:
            # Fallback to England/Premier League defaults
            league_config = {
                "country": "England",
                "league_name": "Premier League",
                "has_winter_break": False,
                "winter_break_start": None,
                "winter_break_end": None,
                "mandatory_fixture_dates": [],
                "blackout_dates": ["12-25"],
                "custom_milestones": [],
                "season_start_date": "08-10",
                "season_end_date": "05-19",
                "european_competition": None,
            }

        # Parse season dates
        season_start_str = league_config.get("season_start_date", "08-10")
        season_end_str = league_config.get("season_end_date", "05-19")
        season_start = date(year, int(season_start_str.split("-")[0]), int(season_start_str.split("-")[1]))
        season_end = date(year + 1, int(season_end_str.split("-")[0]), int(season_end_str.split("-")[1]))

        # 2. Create season blocks
        blocks = [
            SeasonBlock(name="pre_season", start_date=date(year, 7, 15), end_date=date(year, 8, 10)),
            SeasonBlock(name="first_half", start_date=date(year, 8, 10), end_date=date(year, 12, 31)),
            SeasonBlock(name="winter_break", start_date=date(year + 1, 1, 1), end_date=date(year + 1, 1, 31)),
            SeasonBlock(name="second_half", start_date=date(year + 1, 2, 1), end_date=date(year + 1, 5, 31)),
            SeasonBlock(name="season_finish", start_date=date(year + 1, 6, 1), end_date=date(year + 1, 6, 14)),
        ]

        all_events: List[dict] = []

        # 3. Generate milestone events
        # Milestones (transfer windows, season start) are NOT shown on the
        # calendar — they were too noisy. Internal logic that depends on
        # transfer-window dates can be re-introduced via a separate panel.
        # Custom milestones from league_config are also skipped here.
        # (Block intentionally left blank.)

        # 4. Place international windows (priority 10, locked)
        intl_blocked_ranges: List[Tuple[date, date]] = []
        for window in FIFA_INTERNATIONAL_WINDOWS:
            w_start_str = window["start"]  # "MM-DD"
            w_end_str = window["end"]
            w_start_month = int(w_start_str.split("-")[0])
            w_start_day = int(w_start_str.split("-")[1])
            w_end_month = int(w_end_str.split("-")[0])
            w_end_day = int(w_end_str.split("-")[1])

            # Determine year for this window
            w_year = year if w_start_month >= 7 else year + 1
            w_start_date = date(w_year, w_start_month, w_start_day)
            w_end_date = date(w_year, w_end_month, w_end_day)
            intl_blocked_ranges.append((w_start_date, w_end_date))

            all_events.append({
                "career_id": career_id,
                "event_date": w_start_date,
                "event_type": "international",
                "competition_id": None,
                "home_club_id": club_id,
                "away_club_id": None,
                "is_locked": True,
                "priority": 10,
                "kick_off_time": None,
                "weather_data": None,
                "description": window.get("name", "International break"),
                "travel_data": None,
                "original_date": None,
                "reschedule_reason": None,
                "is_cancelled": False,
                "template_id": None,
            })

        # Helper: check if a date falls within an international window
        def _is_in_intl_window(d: date) -> bool:
            for start, end in intl_blocked_ranges:
                if start <= d <= end:
                    return True
            return False

        # Helper: check if a date falls within winter break
        def _is_in_winter_break(d: date) -> bool:
            if not league_config.get("has_winter_break"):
                return False
            wb_start_str = league_config.get("winter_break_start")
            wb_end_str = league_config.get("winter_break_end")
            if not wb_start_str or not wb_end_str:
                return False
            wb_start_month = int(wb_start_str.split("-")[0])
            wb_start_day = int(wb_start_str.split("-")[1])
            wb_end_month = int(wb_end_str.split("-")[0])
            wb_end_day = int(wb_end_str.split("-")[1])
            wb_start = date(year + 1, wb_start_month, wb_start_day)
            wb_end = date(year + 1, wb_end_month, wb_end_day)
            return wb_start <= d <= wb_end

        # Helper: check if a date is a blackout date
        def _is_blackout(d: date) -> bool:
            for bd_str in league_config.get("blackout_dates", []):
                bd_month = int(bd_str.split("-")[0])
                bd_day = int(bd_str.split("-")[1])
                bd_year = year if bd_month >= 7 else year + 1
                if d == date(bd_year, bd_month, bd_day):
                    return True
            return False

        # 5. Generate league matchdays with REAL opponents via round-robin schedule
        #    Get all clubs from the same league
        league_matches: List[dict] = []

        # Find the player's league from CLUBS list
        player_league = None
        for cname, _, _, cleague in CLUBS:
            if cname.lower() == club_name.lower():
                player_league = cleague
                break
        # Fuzzy fallback
        if not player_league:
            for cname, _, _, cleague in CLUBS:
                if club_name.lower() in cname.lower() or cname.lower() in club_name.lower():
                    player_league = cleague
                    break

        # Get all teams in the same league
        league_teams = [cname for cname, _, _, cleague in CLUBS if cleague == player_league]

        # Generate round-robin schedule
        def _generate_round_robin(teams):
            """Generate round-robin pairs for all teams. Returns list of matchday lists."""
            n = len(teams)
            teams = list(teams)  # copy
            if n % 2 == 1:
                teams.append(None)  # bye
                n += 1
            matchdays = []
            for round_num in range(n - 1):
                pairs = []
                for i in range(n // 2):
                    home = teams[i]
                    away = teams[n - 1 - i]
                    if home and away:
                        pairs.append((home, away))
                matchdays.append(pairs)
                # Rotate: fix first team, rotate rest
                teams = [teams[0]] + [teams[-1]] + teams[1:-1]
            # Second half: reverse home/away
            second_half = []
            for md in matchdays:
                second_half.append([(away, home) for home, away in md])
            return matchdays + second_half

        all_matchdays = _generate_round_robin(league_teams)

        # Extract the player's club matches from the full schedule
        player_schedule = []  # list of (matchday_num, opponent, is_home)
        for md_idx, md_pairs in enumerate(all_matchdays):
            for home, away in md_pairs:
                if home.lower() == club_name.lower():
                    player_schedule.append((md_idx + 1, away, True))
                elif away.lower() == club_name.lower():
                    player_schedule.append((md_idx + 1, home, False))

        # Get league name for description (strip emoji prefix)
        league_display = player_league.split(" ", 1)[-1] if player_league and " " in player_league else (player_league or "League")

        # Place matchdays on Saturdays from season_start to season_end,
        # skipping international windows, winter break, and blackout dates
        current = season_start
        # Align to first Saturday on or after season_start
        days_until_saturday = (5 - current.weekday()) % 7
        if days_until_saturday == 0 and current.weekday() != 5:
            days_until_saturday = 7
        current = current + timedelta(days=days_until_saturday)
        if current.weekday() != 5:
            current = current + timedelta(days=(5 - current.weekday()) % 7)

        available_saturdays = []
        while current <= season_end:
            if not _is_in_intl_window(current) and not _is_in_winter_break(current) and not _is_blackout(current):
                available_saturdays.append(current)
            current += timedelta(days=7)

        # Assign player's matches to available Saturdays
        for i, (md_num, opponent, is_home) in enumerate(player_schedule):
            if i >= len(available_saturdays):
                break  # Not enough Saturdays (shouldn't happen for 38 matchdays)
            match_date = available_saturdays[i]
            home_away_tag = "(H)" if is_home else "(A)"
            description = f"{league_display} Matchday {md_num}: vs {opponent} {home_away_tag}"
            match_event = {
                "career_id": career_id,
                "event_date": match_date,
                "event_type": "match",
                "competition_id": None,
                "home_club_id": club_id if is_home else None,
                "away_club_id": club_id if not is_home else None,
                "is_locked": False,
                "priority": 6,
                "kick_off_time": "15:00",
                "weather_data": None,
                "description": description,
                "travel_data": None,
                "original_date": None,
                "reschedule_reason": None,
                "is_cancelled": False,
                "template_id": None,
            }
            league_matches.append(match_event)

        # Mark mandatory fixture dates as locked, priority 9
        mandatory_dates = league_config.get("mandatory_fixture_dates", [])
        for mf_str in mandatory_dates:
            mf_month = int(mf_str.split("-")[0])
            mf_day = int(mf_str.split("-")[1])
            mf_year = year if mf_month >= 7 else year + 1
            mf_date = date(mf_year, mf_month, mf_day)
            # Check if there's already a league match on this date
            found = False
            for lm in league_matches:
                if lm["event_date"] == mf_date:
                    lm["is_locked"] = True
                    lm["priority"] = 9
                    lm["description"] = f"Mandatory fixture - {mf_str}"
                    found = True
                    break
            if not found:
                # Add a mandatory fixture if not already scheduled
                league_matches.append({
                    "career_id": career_id,
                    "event_date": mf_date,
                    "event_type": "match",
                    "competition_id": None,
                    "home_club_id": club_id,
                    "away_club_id": None,
                    "is_locked": True,
                    "priority": 9,
                    "kick_off_time": "15:00",
                    "weather_data": None,
                    "description": f"Mandatory fixture - {mf_str}",
                    "travel_data": None,
                    "original_date": None,
                    "reschedule_reason": None,
                    "is_cancelled": False,
                    "template_id": None,
                })

        all_events.extend(league_matches)

        # 6. Pre-season auxiliary events (medical, training camp,
        #    pre-match warmups/meetings/hotel) used to bloat the
        #    calendar with low-value rows. These are now disabled —
        #    the calendar only shows real matches and international
        #    windows. The user-arranged friendly dialog covers
        #    everything that used to live here.

        # 7. (skipped) Pre-match training/meeting/travel events — see
        #    note in section 6.

        # 8. Assign kick-off times
        # TV slot selection: ~20% of league matches get a TV slot
        for ev in all_events:
            if ev["event_type"] != "match":
                continue
            priority = ev["priority"]
            if priority == 6:
                # League match — default Saturday 15:00, some get TV slots
                if ev["kick_off_time"] == "15:00" and random.random() < 0.2:
                    tv_slot = random.choice([
                        ("12:30", "saturday"),
                        ("20:00", "friday"),
                        ("16:30", "sunday"),
                    ])
                    ev["kick_off_time"] = tv_slot[0]
            elif priority == 8:
                # European match
                ev["kick_off_time"] = "21:00"
            elif priority == 4:
                # Domestic cup
                ev["kick_off_time"] = "20:00"
            elif priority == 2:
                # Friendly — keep 18:00
                pass
            elif priority == 9:
                # Mandatory fixture — keep 15:00
                pass

        # 9. Insert all events into DB via raw SQL (SQLite compat)
        for ev in all_events:
            await self.session.execute(
                text("""
                    INSERT INTO calendar_events
                    (career_id, event_date, event_type, competition_id,
                     home_club_id, away_club_id, is_locked, priority,
                     kick_off_time, weather_data, description, travel_data,
                     original_date, reschedule_reason, is_cancelled, template_id)
                    VALUES
                    (:career_id, :event_date, :event_type, :competition_id,
                     :home_club_id, :away_club_id, :is_locked, :priority,
                     :kick_off_time, :weather_data, :description, :travel_data,
                     :original_date, :reschedule_reason, :is_cancelled, :template_id)
                """),
                {
                    "career_id": ev["career_id"],
                    "event_date": str(ev["event_date"]),
                    "event_type": ev["event_type"],
                    "competition_id": ev.get("competition_id"),
                    "home_club_id": ev.get("home_club_id"),
                    "away_club_id": ev.get("away_club_id"),
                    "is_locked": 1 if ev.get("is_locked") else 0,
                    "priority": ev.get("priority", 5),
                    "kick_off_time": ev.get("kick_off_time"),
                    "weather_data": ev.get("weather_data"),
                    "description": ev.get("description"),
                    "travel_data": ev.get("travel_data"),
                    "original_date": str(ev["original_date"]) if ev.get("original_date") else None,
                    "reschedule_reason": ev.get("reschedule_reason"),
                    "is_cancelled": 1 if ev.get("is_cancelled") else 0,
                    "template_id": ev.get("template_id"),
                },
            )
        await self.session.commit()

        return all_events

    # ─── Priority-Based Event Placement ───────────────────────────────────────

    async def place_events_by_priority(
        self,
        career_id: int,
        events: List[dict],
    ) -> Tuple[List[dict], List[ConflictReport]]:
        """
        Place events respecting priority ordering.
        Returns (placed_events, conflict_reports).
        """
        # Sort events by priority descending (highest first)
        sorted_events = sorted(events, key=lambda e: e.get("priority", 0), reverse=True)
        placed: List[dict] = []
        conflicts: List[ConflictReport] = []

        for event in sorted_events:
            conflict = self.detect_conflict(placed, event)
            if conflict is None:
                placed.append(event)
            else:
                report = ConflictReport(
                    event_date=event["event_date"],
                    conflict=conflict,
                    resolved=conflict.suggested_date is not None,
                    resolution=f"Suggested move to {conflict.suggested_date}" if conflict.suggested_date else None,
                )
                conflicts.append(report)
                # Try to place on suggested date
                if conflict.suggested_date:
                    event["event_date"] = conflict.suggested_date
                    event["original_date"] = event.get("event_date")
                    event["reschedule_reason"] = f"Conflict with event {conflict.existing_event_id}"
                    placed.append(event)

        return placed, conflicts

    # ─── Conflict Detection ───────────────────────────────────────────────────

    def detect_conflict(
        self,
        existing_events: List[dict],
        new_event: dict,
    ) -> Optional[Conflict]:
        """
        Check if new_event conflicts with any existing event.
        Conflict = same club, same date, or within 48h of another match.
        Returns Conflict object or None.
        """
        new_date = new_event["event_date"]
        new_club_id = new_event.get("home_club_id") or new_event.get("away_club_id")

        for existing in existing_events:
            ex_date = existing["event_date"]
            ex_club_id = existing.get("home_club_id") or existing.get("away_club_id")

            # Only check conflicts for same club
            if new_club_id and ex_club_id and new_club_id != ex_club_id:
                continue

            # Same date conflict
            if ex_date == new_date:
                suggested = self._find_free_date(existing_events, new_date)
                return Conflict(
                    existing_event_id=existing.get("id", 0),
                    new_event_date=new_date,
                    conflict_type="same_date",
                    suggested_date=suggested,
                )

            # 48-hour rule for matches
            if (new_event.get("event_type") == "match"
                    and existing.get("event_type") == "match"):
                diff = abs((new_date - ex_date).days)
                if diff < 2:
                    suggested = self._find_free_date(existing_events, new_date)
                    return Conflict(
                        existing_event_id=existing.get("id", 0),
                        new_event_date=new_date,
                        conflict_type="48h_rule",
                        suggested_date=suggested,
                    )

        return None

    def _find_free_date(
        self,
        existing_events: List[dict],
        target_date: date,
        max_search_days: int = 7,
    ) -> Optional[date]:
        """Find the nearest free date within max_search_days of target."""
        occupied_dates = {e["event_date"] for e in existing_events if e.get("event_type") == "match"}
        for offset in range(1, max_search_days + 1):
            for direction in (1, -1):
                candidate = target_date + timedelta(days=offset * direction)
                if candidate not in occupied_dates:
                    return candidate
        return None

    def detect_overload(
        self,
        events: List[dict],
        club_id: int,
        window_days: int = 7,
    ) -> List[OverloadWarning]:
        """
        Detect 3+ matches within a 7-day window for a club.
        Returns list of overload warnings.
        """
        # Filter to match events for this club
        club_matches = [
            e for e in events
            if e.get("event_type") == "match"
            and (e.get("home_club_id") == club_id or e.get("away_club_id") == club_id)
            and not e.get("is_cancelled")
        ]
        club_matches.sort(key=lambda e: e["event_date"])

        warnings: List[OverloadWarning] = []
        for i, match in enumerate(club_matches):
            window_start = match["event_date"]
            window_end = window_start + timedelta(days=window_days)
            matches_in_window = [
                m for m in club_matches
                if window_start <= m["event_date"] <= window_end
            ]
            if len(matches_in_window) >= 3:
                # Find lowest priority match in window
                lowest = min(matches_in_window, key=lambda m: m.get("priority", 0))
                warning = OverloadWarning(
                    club_id=club_id,
                    start_date=window_start,
                    end_date=window_end,
                    match_count=len(matches_in_window),
                    lowest_priority_event_id=lowest.get("id", 0),
                )
                # Avoid duplicate warnings for overlapping windows
                if not any(
                    w.start_date == warning.start_date and w.end_date == warning.end_date
                    for w in warnings
                ):
                    warnings.append(warning)

        return warnings

    # ─── Rescheduling ─────────────────────────────────────────────────────────

    async def reschedule_event(
        self,
        event_id: int,
        reason: str,
        max_search_days: int = 7,
    ) -> Optional[dict]:
        """
        Find nearest free slot and move event.
        Logs original_date, new_date, reason.
        Returns updated event dict or None if no slot found or event is locked.
        """
        # Fetch the event
        result = await self.session.execute(
            text("SELECT * FROM calendar_events WHERE id = :eid AND is_cancelled = 0"),
            {"eid": event_id},
        )
        row = result.fetchone()
        if not row:
            return None

        # Map row to dict
        columns = result.keys()
        event = dict(zip(columns, row))

        # Refuse to reschedule locked events
        if event.get("is_locked"):
            return None

        career_id = event["career_id"]
        original_date = event["event_date"]

        # Get existing events for this career around the date
        result2 = await self.session.execute(
            text("""
                SELECT event_date FROM calendar_events
                WHERE career_id = :cid AND is_cancelled = 0
                AND event_type = 'match'
                AND event_date BETWEEN :start AND :end
            """),
            {
                "cid": career_id,
                "start": str(date.fromisoformat(str(original_date)) - timedelta(days=max_search_days)),
                "end": str(date.fromisoformat(str(original_date)) + timedelta(days=max_search_days)),
            },
        )
        occupied = {row[0] for row in result2.fetchall()}

        # Find free slot
        target = date.fromisoformat(str(original_date))
        new_date = None
        for offset in range(1, max_search_days + 1):
            for direction in (1, -1):
                candidate = target + timedelta(days=offset * direction)
                if str(candidate) not in occupied and candidate not in occupied:
                    new_date = candidate
                    break
            if new_date:
                break

        if not new_date:
            return None

        # Update the event
        await self.session.execute(
            text("""
                UPDATE calendar_events
                SET event_date = :new_date, original_date = :orig_date, reschedule_reason = :reason
                WHERE id = :eid
            """),
            {
                "new_date": str(new_date),
                "orig_date": str(original_date),
                "reason": reason,
                "eid": event_id,
            },
        )
        await self.session.commit()

        event["event_date"] = new_date
        event["original_date"] = original_date
        event["reschedule_reason"] = reason
        return event

    async def handle_european_thursday_shift(
        self,
        career_id: int,
        european_match_date: date,
    ) -> Optional[dict]:
        """
        When European match is on Thursday, move next league match to Sun/Mon.
        Returns the rescheduled event dict or None.
        """
        # Find the next league match after the European match
        result = await self.session.execute(
            text("""
                SELECT id, event_date FROM calendar_events
                WHERE career_id = :cid AND event_type = 'match' AND priority = 6
                AND is_cancelled = 0 AND is_locked = 0
                AND event_date > :eu_date
                ORDER BY event_date ASC LIMIT 1
            """),
            {"cid": career_id, "eu_date": str(european_match_date)},
        )
        row = result.fetchone()
        if not row:
            return None

        event_id = row[0]
        current_date = date.fromisoformat(str(row[1]))

        # Move to Sunday or Monday after the European match
        # Sunday = 2 days after Thursday (if European match is Thursday)
        sunday = european_match_date + timedelta(days=3)  # Thu + 3 = Sun
        monday = european_match_date + timedelta(days=4)  # Thu + 4 = Mon

        # Prefer Sunday
        new_date = sunday

        await self.session.execute(
            text("""
                UPDATE calendar_events
                SET event_date = :new_date, original_date = :orig_date,
                    reschedule_reason = :reason
                WHERE id = :eid
            """),
            {
                "new_date": str(new_date),
                "orig_date": str(current_date),
                "reason": "European Thursday shift - moved to Sunday",
                "eid": event_id,
            },
        )
        await self.session.commit()

        return {
            "id": event_id,
            "event_date": new_date,
            "original_date": current_date,
            "reschedule_reason": "European Thursday shift - moved to Sunday",
        }

    # ─── Competition Updates ──────────────────────────────────────────────────

    async def on_cup_elimination(
        self,
        career_id: int,
        competition_id: int,
    ) -> List[dict]:
        """
        Remove future cup fixtures, free dates.
        Returns list of cancelled events.
        """
        today = date.today()
        result = await self.session.execute(
            text("""
                SELECT id, event_date, description FROM calendar_events
                WHERE career_id = :cid AND competition_id = :comp_id
                AND event_date > :today AND is_cancelled = 0
            """),
            {"cid": career_id, "comp_id": competition_id, "today": str(today)},
        )
        rows = result.fetchall()
        cancelled = []

        for row in rows:
            await self.session.execute(
                text("UPDATE calendar_events SET is_cancelled = 1 WHERE id = :eid"),
                {"eid": row[0]},
            )
            cancelled.append({
                "id": row[0],
                "event_date": row[1],
                "description": row[2],
            })

        if cancelled:
            await self.session.commit()

        return cancelled

    async def on_new_round_qualified(
        self,
        career_id: int,
        competition_id: int,
        round_dates: List[date],
        opponent_id: Optional[int],
    ) -> List[dict]:
        """
        Add new fixture dates for next round.
        Returns list of created events.
        """
        created = []
        for rd in round_dates:
            await self.session.execute(
                text("""
                    INSERT INTO calendar_events
                    (career_id, event_date, event_type, competition_id,
                     home_club_id, away_club_id, is_locked, priority,
                     kick_off_time, description, is_cancelled)
                    VALUES
                    (:cid, :edate, 'match', :comp_id,
                     :home, :away, 0, 4,
                     '20:00', :desc, 0)
                """),
                {
                    "cid": career_id,
                    "edate": str(rd),
                    "comp_id": competition_id,
                    "home": opponent_id,
                    "away": None,
                    "desc": f"Cup round - {rd}",
                },
            )
            created.append({
                "career_id": career_id,
                "event_date": rd,
                "event_type": "match",
                "competition_id": competition_id,
                "description": f"Cup round - {rd}",
            })

        if created:
            await self.session.commit()

        return created

    # ─── Weekly Recalculation ─────────────────────────────────────────────────

    async def recalculate_week(
        self,
        career_id: int,
        current_date: date,
    ) -> RecalculationResult:
        """
        Called on advance_week. Checks for:
        - Overload warnings
        - Weather updates for upcoming matches
        Returns RecalculationResult.
        """
        result = RecalculationResult()

        # Get events for the next 14 days
        end_date = current_date + timedelta(days=14)
        db_result = await self.session.execute(
            text("""
                SELECT id, career_id, event_date, event_type, competition_id,
                       home_club_id, away_club_id, is_locked, priority,
                       kick_off_time, weather_data, description, is_cancelled
                FROM calendar_events
                WHERE career_id = :cid AND is_cancelled = 0
                AND event_date BETWEEN :start AND :end
            """),
            {"cid": career_id, "start": str(current_date), "end": str(end_date)},
        )
        rows = db_result.fetchall()
        columns = db_result.keys()
        events = [dict(zip(columns, row)) for row in rows]

        # Detect overloads
        # Get club_id from events
        club_ids = set()
        for ev in events:
            if ev.get("home_club_id"):
                club_ids.add(ev["home_club_id"])
            if ev.get("away_club_id"):
                club_ids.add(ev["away_club_id"])

        for cid in club_ids:
            warnings = self.detect_overload(events, cid)
            result.warnings.extend(warnings)

        return result

    # ─── Query Helpers ────────────────────────────────────────────────────────

    async def get_events_for_month(
        self,
        career_id: int,
        year: int,
        month: int,
        event_types: Optional[List[str]] = None,
        team_filter: Optional[str] = None,
    ) -> List[dict]:
        """Get all events for a given month with optional filtering."""
        # Calculate month date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        query = """
            SELECT id, career_id, event_date, event_type, competition_id,
                   home_club_id, away_club_id, is_locked, priority,
                   kick_off_time, weather_data, description, travel_data,
                   original_date, reschedule_reason, is_cancelled, template_id
            FROM calendar_events
            WHERE career_id = :cid AND is_cancelled = 0
            AND event_date BETWEEN :start AND :end
        """
        params: dict = {"cid": career_id, "start": str(start_date), "end": str(end_date)}

        if event_types:
            placeholders = ", ".join(f":type_{i}" for i in range(len(event_types)))
            query += f" AND event_type IN ({placeholders})"
            for i, et in enumerate(event_types):
                params[f"type_{i}"] = et

        query += " ORDER BY event_date ASC, priority DESC"

        result = await self.session.execute(text(query), params)
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]

    async def get_events_for_date(
        self,
        career_id: int,
        event_date: date,
    ) -> List[dict]:
        """Get all events for a specific date."""
        result = await self.session.execute(
            text("""
                SELECT id, career_id, event_date, event_type, competition_id,
                       home_club_id, away_club_id, is_locked, priority,
                       kick_off_time, weather_data, description, travel_data,
                       original_date, reschedule_reason, is_cancelled, template_id
                FROM calendar_events
                WHERE career_id = :cid AND event_date = :edate AND is_cancelled = 0
                ORDER BY priority DESC
            """),
            {"cid": career_id, "edate": str(event_date)},
        )
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]

    async def get_next_milestone(
        self,
        career_id: int,
        after_date: date,
    ) -> Optional[dict]:
        """Get the next upcoming milestone event."""
        result = await self.session.execute(
            text("""
                SELECT id, career_id, event_date, event_type, description
                FROM calendar_events
                WHERE career_id = :cid AND event_type = 'milestone'
                AND event_date > :after AND is_cancelled = 0
                ORDER BY event_date ASC LIMIT 1
            """),
            {"cid": career_id, "after": str(after_date)},
        )
        row = result.fetchone()
        if not row:
            return None
        columns = result.keys()
        return dict(zip(columns, row))

    async def apply_template(
        self,
        career_id: int,
        template_id: int,
        year: int,
        month: int,
    ) -> List[dict]:
        """
        Apply a recurring template to a month.
        Generates individual events for each applicable day that does not
        already have a higher-priority or locked event.
        """
        # Fetch template
        result = await self.session.execute(
            text("SELECT day_assignments FROM recurring_templates WHERE id = :tid AND career_id = :cid"),
            {"tid": template_id, "cid": career_id},
        )
        row = result.fetchone()
        if not row:
            return []

        import json
        day_assignments = json.loads(row[0])

        # Get existing events for the month
        existing = await self.get_events_for_month(career_id, year, month)
        locked_dates = {
            e["event_date"] for e in existing
            if e.get("is_locked") or e.get("event_type") in ("match", "international")
        }

        # Generate events for each day of the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        created: List[dict] = []
        current = start_date

        while current <= end_date:
            day_name = day_names[current.weekday()]
            assignment = day_assignments.get(day_name)

            if assignment and str(current) not in locked_dates and current not in locked_dates:
                event = {
                    "career_id": career_id,
                    "event_date": current,
                    "event_type": "training",
                    "description": assignment,
                    "template_id": template_id,
                    "priority": 1,
                    "is_locked": False,
                    "is_cancelled": False,
                }
                await self.session.execute(
                    text("""
                        INSERT INTO calendar_events
                        (career_id, event_date, event_type, description,
                         template_id, priority, is_locked, is_cancelled)
                        VALUES
                        (:career_id, :event_date, :event_type, :description,
                         :template_id, :priority, :is_locked, :is_cancelled)
                    """),
                    {
                        "career_id": career_id,
                        "event_date": str(current),
                        "event_type": "training",
                        "description": assignment,
                        "template_id": template_id,
                        "priority": 1,
                        "is_locked": 0,
                        "is_cancelled": 0,
                    },
                )
                created.append(event)

            current += timedelta(days=1)

        if created:
            await self.session.commit()

        return created

    # ─── User-arranged friendly matches ───────────────────────────────────

    async def add_friendly_match(
        self,
        career_id: int,
        event_date: date,
        home_club_id: int,
        away_club_id: int,
        kick_off_time: str,
        description: str,
        travel_data: dict,
    ) -> dict:
        """Insert a single user-arranged friendly into ``calendar_events``.

        Validation is the responsibility of :class:`FriendlyMatchService`;
        this method only persists the row and reads the new id back. The
        ``travel_data`` dict is JSON-serialised with ``ensure_ascii=False``
        so Cyrillic city names round-trip cleanly.

        Returns the created event as a dict matching the shape used by
        ``/api/calendar/{career_id}/day``.
        """
        travel_json = (
            json.dumps(travel_data, ensure_ascii=False) if travel_data else None
        )

        await self.session.execute(
            text(
                """
                INSERT INTO calendar_events
                (career_id, event_date, event_type, home_club_id, away_club_id,
                 is_locked, priority, kick_off_time, description, travel_data,
                 is_cancelled)
                VALUES
                (:career_id, :event_date, 'match', :home_club_id, :away_club_id,
                 0, 2, :kick_off_time, :description, :travel_data, 0)
                """
            ),
            {
                "career_id": career_id,
                "event_date": str(event_date),
                "home_club_id": home_club_id,
                "away_club_id": away_club_id,
                "kick_off_time": kick_off_time,
                "description": description,
                "travel_data": travel_json,
            },
        )
        await self.session.commit()

        id_row = await self.session.execute(text("SELECT last_insert_rowid()"))
        new_id = id_row.scalar() or 0

        return {
            "id": int(new_id),
            "career_id": career_id,
            "event_date": str(event_date),
            "event_type": "match",
            "home_club_id": home_club_id,
            "away_club_id": away_club_id,
            "is_locked": False,
            "priority": 2,
            "kick_off_time": kick_off_time,
            "description": description,
            "travel_data": travel_data,
            "is_cancelled": False,
        }
