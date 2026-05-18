"""
ReminderService — Generates and manages in-game reminders for upcoming events.
MVP implementation using in-memory storage (dict keyed by career_id).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class Reminder:
    """A single reminder notification."""
    event_id: int
    reminder_type: str  # "match_prep", "transfer_deadline", "draw", "promise"
    message: str
    trigger_date: date
    is_dismissed: bool = False


# In-memory storage: career_id -> list of reminders
_reminders_store: Dict[int, List[Reminder]] = {}

# Auto-increment ID counter
_next_reminder_id: int = 1


def _get_reminder_id() -> int:
    """Get next unique reminder ID."""
    global _next_reminder_id
    rid = _next_reminder_id
    _next_reminder_id += 1
    return rid


class ReminderService:
    """Generates and manages in-game reminders."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_reminders_for_week(
        self,
        career_id: int,
        current_date: date,
    ) -> List[Reminder]:
        """
        Check events in next 7 days and generate applicable reminders.
        - 2 days before match: "Review tactics" (match_prep)
        - 7 days before transfer deadline: "Transfer window closing" (transfer_deadline)
        - 1 day before draw: "Competition draw tomorrow" (draw)
        No duplicates for same event + reminder_type.
        """
        global _reminders_store

        if career_id not in _reminders_store:
            _reminders_store[career_id] = []

        existing = _reminders_store[career_id]
        new_reminders: List[Reminder] = []

        # Query events in the next 7 days
        end_date = current_date + timedelta(days=7)
        result = await self.session.execute(
            text("""
                SELECT id, event_date, event_type, description
                FROM calendar_events
                WHERE career_id = :career_id
                  AND event_date >= :start
                  AND event_date <= :end
                  AND is_cancelled = 0
            """),
            {
                "career_id": career_id,
                "start": str(current_date),
                "end": str(end_date),
            },
        )
        events = result.fetchall()

        for row in events:
            event_id = row[0]
            event_date_str = row[1]
            event_type = row[2]
            description = row[3] or ""

            # Parse event_date
            if isinstance(event_date_str, str):
                parts = event_date_str.split("-")
                ev_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                ev_date = event_date_str

            # Match: 2 days before → "Review tactics"
            if event_type == "match":
                trigger = ev_date - timedelta(days=2)
                if trigger >= current_date:
                    if not self._has_duplicate(existing, event_id, "match_prep"):
                        reminder = Reminder(
                            event_id=event_id,
                            reminder_type="match_prep",
                            message=f"Review tactics for: {description}",
                            trigger_date=trigger,
                            is_dismissed=False,
                        )
                        new_reminders.append(reminder)

            # Transfer deadline: 7 days before
            if event_type == "deadline" or (
                event_type == "milestone" and "transfer" in description.lower() and "close" in description.lower()
            ):
                trigger = ev_date - timedelta(days=7)
                if trigger >= current_date:
                    if not self._has_duplicate(existing, event_id, "transfer_deadline"):
                        reminder = Reminder(
                            event_id=event_id,
                            reminder_type="transfer_deadline",
                            message=f"Transfer window closing soon: {description}",
                            trigger_date=trigger,
                            is_dismissed=False,
                        )
                        new_reminders.append(reminder)

            # Draw: 1 day before
            if "draw" in description.lower() or event_type == "draw":
                trigger = ev_date - timedelta(days=1)
                if trigger >= current_date:
                    if not self._has_duplicate(existing, event_id, "draw"):
                        reminder = Reminder(
                            event_id=event_id,
                            reminder_type="draw",
                            message=f"Competition draw tomorrow: {description}",
                            trigger_date=trigger,
                            is_dismissed=False,
                        )
                        new_reminders.append(reminder)

        # Add new reminders to store (no duplicates)
        _reminders_store[career_id].extend(new_reminders)
        return new_reminders

    def dismiss_reminder(self, career_id: int, reminder_id: int) -> bool:
        """Mark a reminder as dismissed by index (0-based)."""
        if career_id not in _reminders_store:
            return False
        reminders = _reminders_store[career_id]
        if 0 <= reminder_id < len(reminders):
            reminders[reminder_id].is_dismissed = True
            return True
        return False

    def get_active_reminders(self, career_id: int) -> List[Reminder]:
        """Get all undismissed reminders for a career."""
        if career_id not in _reminders_store:
            return []
        return [r for r in _reminders_store[career_id] if not r.is_dismissed]

    def _has_duplicate(
        self,
        existing: List[Reminder],
        event_id: int,
        reminder_type: str,
    ) -> bool:
        """Check if a reminder already exists for this event + type."""
        return any(
            r.event_id == event_id and r.reminder_type == reminder_type
            for r in existing
        )
