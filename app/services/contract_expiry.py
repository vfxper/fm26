"""
Contract expiry service.

Two responsibilities:

1. Players whose contract ends within ~6 months and who haven't been
   renewed yet (no recent renewal) get a tier-based chance to demand
   a renewal — same code path as `player_requests.run_weekly_player_requests`,
   but separated out so it's clearer.

2. Players whose contract has ALREADY ended (`contract_years <= 0`
   AND/OR `contract_expiry < today`) leave the club as free agents
   on the season-rollover date. We post a news item to the inbox.

Called weekly from advance_day (every Monday).

`run_weekly_contract_expiry(db, career_id, on_date)` returns a count
of players who left this week.
"""
from __future__ import annotations

import json
from typing import Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _months_between(today_iso: str, expiry_iso: str) -> int:
    """Return whole months between today and expiry. Negative if past."""
    try:
        from datetime import date
        ty, tm, td = (int(p) for p in today_iso.split("-"))
        ey, em, ed = (int(p) for p in expiry_iso.split("-"))
        return (ey - ty) * 12 + (em - tm) - (1 if ed < td else 0)
    except Exception:
        return 999


async def run_weekly_contract_expiry(
    db: AsyncSession, *, career_id: int, on_date: str
) -> Tuple[int, int]:
    """
    Each Monday:
      1. Find players whose contract has run out (`contract_expiry < on_date`).
         Those leave the club as free agents — squad row deleted, `players.club`
         cleared, news pushed.
      2. Find players with < 6 months remaining who haven't been offered
         renewal — push a 'demand renewal' inbox item ONCE per player.

    Returns ``(left_count, demand_count)``.
    """
    # ─── 1. Already-expired contracts → leave on free transfer ─────
    rows = await db.execute(text(
        "SELECT sp.id, sp.player_id, p.name, p.ca, sp.contract_expiry "
        "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
        "WHERE sp.career_id = :c "
        "  AND sp.contract_expiry IS NOT NULL "
        "  AND sp.contract_expiry < :d "
        "  AND COALESCE(sp.is_loaned, 0) = 0"
    ), {"c": career_id, "d": on_date})
    expired = rows.fetchall()
    left_count = 0
    for r in expired:
        sp_id, pid, pname, ca, expiry = r
        await db.execute(text(
            "DELETE FROM squad_players WHERE id = :i AND career_id = :c"
        ), {"i": sp_id, "c": career_id})
        # Mark player as a free agent.
        await db.execute(text(
            "UPDATE players SET club = '' WHERE id = :p"
        ), {"p": pid})
        # Inbox news.
        try:
            from app.api.routes.inbox import push_inbox_message
            await push_inbox_message(
                db, career_id,
                category="contract",
                subject=f"{pname or 'Игрок'} ушёл из клуба",
                body=(
                    f"Контракт {pname or 'игрока'} (CA {ca or '—'}) истёк "
                    f"{expiry}, и он покинул команду на правах свободного "
                    f"агента. Подписать его сейчас можно через поиск игроков."
                ),
                on_date=on_date,
            )
        except Exception:
            pass
        left_count += 1

    # ─── 2. Players with < 6 months left → demand renewal ─────────────
    rows = await db.execute(text(
        "SELECT sp.id, sp.player_id, p.name, p.ca, sp.contract_expiry, "
        "       sp.contract_years, sp.wage "
        "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
        "WHERE sp.career_id = :c "
        "  AND COALESCE(sp.is_loaned, 0) = 0 "
        "  AND sp.contract_expiry IS NOT NULL "
        "  AND sp.contract_expiry >= :d"
    ), {"c": career_id, "d": on_date})
    candidates = rows.fetchall()
    demand_count = 0
    for r in candidates:
        sp_id, pid, pname, ca, expiry, years, wage = r
        months = _months_between(on_date, expiry)
        if months > 6 or months < 0:
            continue

        # Has the user already been told? Skip if a contract-related
        # inbox row exists for this player in the last 30 days.
        already = await db.execute(text(
            "SELECT 1 FROM inbox_messages "
            "WHERE career_id = :c "
            "  AND category IN ('contract', 'player_request') "
            "  AND subject LIKE :pat "
            "  AND created_date >= :since LIMIT 1"
        ), {"c": career_id, "pat": f"%{pname or ''}%",
            "since": _shift_iso_days(on_date, -30)})
        if already.fetchone():
            continue

        # Push demand.
        from random import randint
        new_wage = max(1_000, int((wage or 50_000) * 1.25))
        try:
            from app.api.routes.inbox import push_inbox_message
            payload = json.dumps({
                "actions": [
                    {"id": "renew_contract",
                     "label": f"Продлить (£{new_wage:,}/нед)",
                     "params": {"player_id": pid, "new_wage": new_wage,
                                "new_years": 4}},
                    {"id": "let_run_out",
                     "label": "Пусть уйдёт по истечении"},
                ],
                "linked_player_id": pid,
                "deadline_date": _shift_iso_days(on_date, max(7, months * 30)),
                "priority": "important",
            }, ensure_ascii=False)
            await push_inbox_message(
                db, career_id,
                category="contract",
                subject=(
                    f"Контракт {pname or 'игрока'} истекает {expiry} — "
                    f"осталось {max(0, months)} мес."
                ),
                body=(
                    f"Игрок (CA {ca or '—'}) хочет ясности по будущему. "
                    f"Если ничего не предложить, он уйдёт свободным агентом "
                    f"когда закончится контракт."
                ),
                on_date=on_date,
                payload=payload,
            )
            demand_count += 1
        except Exception:
            pass

    if expired or demand_count:
        await db.commit()
    return (left_count, demand_count)


def _shift_iso_days(iso: str, days: int) -> str:
    from datetime import date, timedelta
    try:
        y, m, d = (int(p) for p in iso.split("-"))
        return str(date(y, m, d) + timedelta(days=days))
    except Exception:
        return iso
