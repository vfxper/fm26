"""
Track player promises. Daily check sets status=broken when deadline
passes without the condition being met, or status=fulfilled if it was.

Currently we support these promise_types:
- playing_time: details_json {"min_minutes_per_5": int}.  Fulfilled if
  squad_players.match_minutes_last5 >= threshold by deadline.
- sell_at_end: marker; we don't auto-fulfill, just expire.
- new_contract: marker; manual fulfillment when manager extends.

Broken promises drop morale by 25 and create a reaction inbox row.
"""
from __future__ import annotations
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def evaluate_promises(db: AsyncSession, *, career_id: int, on_date: str) -> int:
    """Resolve any active promise whose deadline has passed.
    Returns the number of broken promises (for inbox surfacing)."""
    rows = await db.execute(text(
        "SELECT pp.id, pp.player_id, pp.promise_type, pp.details_json, "
        "pp.deadline_date, sp.match_minutes_last5, p.name "
        "FROM player_promises pp "
        "LEFT JOIN squad_players sp ON sp.player_id = pp.player_id "
        "AND sp.career_id = pp.career_id "
        "JOIN players p ON p.id = pp.player_id "
        "WHERE pp.career_id = :c AND pp.status = 'active' "
        "AND pp.deadline_date <= :d"
    ), {"c": career_id, "d": on_date})
    broken = 0
    for r in rows.fetchall():
        promise_id, pid, ptype, details, deadline, mins5, pname = r
        try:
            d = json.loads(details) if details else {}
        except Exception:
            d = {}
        fulfilled = False
        if ptype == "playing_time":
            need = int(d.get("min_minutes_per_5") or 200)
            if (mins5 or 0) >= need:
                fulfilled = True
        elif ptype == "sell_at_end":
            # auto-expire as fulfilled if the player is no longer in squad
            chk = await db.execute(text(
                "SELECT 1 FROM squad_players WHERE career_id=:c AND player_id=:p"
            ), {"c": career_id, "p": pid})
            if chk.fetchone() is None:
                fulfilled = True

        if fulfilled:
            await db.execute(text(
                "UPDATE player_promises SET status='fulfilled' WHERE id=:i"
            ), {"i": promise_id})
        else:
            await db.execute(text(
                "UPDATE player_promises SET status='broken' WHERE id=:i"
            ), {"i": promise_id})
            await db.execute(text(
                "UPDATE squad_players SET morale = MAX(0, COALESCE(morale,70) - 25) "
                "WHERE career_id=:c AND player_id=:p"
            ), {"c": career_id, "p": pid})
            broken += 1
            try:
                from app.api.routes.inbox import push_inbox_message
                await push_inbox_message(
                    db, career_id,
                    category="promise_broken",
                    subject=f"💢 Обещание нарушено: {pname}",
                    body=f"Игрок недоволен. Мораль резко упала. Возможен запрос на трансфер.",
                    on_date=on_date,
                )
            except Exception:
                pass
    if broken:
        await db.commit()
    return broken
