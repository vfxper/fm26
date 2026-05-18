"""
Generate player requests (contract / playing_time / transfer) and push
them to inbox with actionable buttons.

Called weekly from advance_day (every Monday).

Logic:
- Contract: contract_years_remaining < 2 AND ca > 110, ~25% chance/week.
- Playing time: status in (rotation, key_player) AND match_minutes_last5
  is low, ~20% chance/week if morale < 60.
- Transfer demand: morale < 25 OR a previous promise was broken,
  10% chance/week.

Each generated message stores its `actions` JSON in inbox.payload so
the frontend renders buttons. The action handler endpoint
(/careers/{cid}/inbox/{mid}/action) applies the consequence.
"""

from __future__ import annotations
import json
import random
from datetime import date, timedelta
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _add_days(d: str, days: int) -> str:
    y, m, dd = (int(p) for p in d.split("-"))
    return str(date(y, m, dd) + timedelta(days=days))


async def _push_request(db: AsyncSession, career_id: int, on_date: str, *,
                         category: str, subject: str, body: str,
                         actions: List[Dict[str, Any]],
                         linked_player_id: int,
                         deadline_days: int = 7,
                         priority: str = "important") -> None:
    """Push a request-style inbox row with actions JSON in payload."""
    payload = {
        "actions": actions,
        "linked_player_id": linked_player_id,
        "deadline_date": _add_days(on_date, deadline_days),
        "priority": priority,
    }
    try:
        from app.api.routes.inbox import push_inbox_message
        await push_inbox_message(
            db, career_id, category=category,
            subject=subject, body=body, on_date=on_date,
            payload=json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        pass


async def run_weekly_player_requests(
    db: AsyncSession, *, career_id: int, on_date: str,
) -> int:
    """Scan player's squad and emit up to ~3 requests per week.
    Returns the count of generated requests."""
    rows = await db.execute(text(
        "SELECT sp.id, sp.player_id, sp.morale, sp.contract_years, "
        "sp.contract_expiry, sp.status, sp.match_minutes_last5, sp.wage, "
        "p.name, p.ca FROM squad_players sp "
        "JOIN players p ON p.id = sp.player_id "
        "WHERE sp.career_id = :c"
    ), {"c": career_id})
    candidates = rows.fetchall()
    if not candidates:
        return 0

    generated = 0
    random.shuffle(candidates)

    for r in candidates:
        if generated >= 3:
            break
        sp_id, pid, morale, c_years, expiry, status, mins5, wage, name, ca = r
        morale = morale or 70
        c_years = c_years or 2
        ca = ca or 100
        wage = wage or 50_000
        mins5 = mins5 or 0

        # 1) Contract demand
        if c_years < 2 and ca > 110 and random.random() < 0.25:
            fair = int(wage * 1.4)
            await _push_request(
                db, career_id, on_date,
                category="player_request",
                subject=f"📩 {name} хочет новый контракт",
                body=(
                    f"У игрока остаётся {c_years} года по контракту. "
                    f"С учётом его уровня (CA {ca}) он считает справедливой зарплату "
                    f"около £{fair:,}/нед."
                ),
                actions=[
                    {"id": "accept_contract", "label": "Предложить новый контракт",
                     "params": {"new_wage": fair, "new_years": 4}},
                    {"id": "wait", "label": "Подождать до конца сезона"},
                    {"id": "reject", "label": "Отказать"},
                ],
                linked_player_id=pid,
            )
            generated += 1
            continue

        # 2) Playing time complaint — relative to player's role.
        # Stars and important players expect 80+ minutes per match in
        # the last 5 (~400 mins). Starters expect 60+, rotation 30+.
        # Backups don't complain. Prospects only complain if their CA
        # is high enough that they should be playing already.
        ROLE_MIN_MINUTES = {
            "star":      400,
            "important": 350,
            "starter":   300,
            "first_team":300,  # legacy
            "rotation":  150,
            # backup, prospect: no automatic complaint
        }
        threshold = ROLE_MIN_MINUTES.get(status)
        if threshold is not None and mins5 < threshold and morale < 75:
            # Higher-tier roles complain more often.
            chance = {"star": 0.45, "important": 0.35, "starter": 0.25,
                      "first_team": 0.25, "rotation": 0.15}.get(status, 0.0)
            if random.random() < chance:
                role_label = {
                    "star":      "звезда команды",
                    "important": "важный игрок",
                    "starter":   "игрок стартового состава",
                    "first_team":"игрок основы",
                    "rotation":  "игрок ротации",
                }.get(status, "игрок")
                await _push_request(
                    db, career_id, on_date,
                    category="player_request",
                    subject=f"📩 {name}: «Почему я не играю?»",
                    body=(
                        f"Игрок ({role_label}) считает, что мало играет. "
                        f"За последние 5 матчей сыграл {mins5} мин из ~450 возможных. "
                        f"Просит объяснить решение тренера или дать ему шанс. "
                        f"Иначе мораль упадёт ещё."
                    ),
                    actions=[
                        {"id": "promise_playing_time", "label": "Пообещать больше времени"},
                        {"id": "wait_chance", "label": "Сказать ждать своего шанса"},
                        {"id": "list_transfer", "label": "Согласиться продать"},
                        {"id": "reject", "label": "Отказать"},
                    ],
                    linked_player_id=pid,
                )
                generated += 1
                continue

        # 3) Transfer demand on low morale
        if morale < 30 and random.random() < 0.15:
            await _push_request(
                db, career_id, on_date,
                category="player_request",
                subject=f"📩 {name} требует трансфер",
                body=(
                    f"Считает, что не реализует потенциал. Мораль на дне ({morale}). "
                    "Хочет покинуть клуб."
                ),
                actions=[
                    {"id": "list_transfer", "label": "Выставить на трансфер"},
                    {"id": "promise_stay", "label": "Убедить остаться"},
                    {"id": "reject", "label": "Отказать (риск конфликта)"},
                ],
                linked_player_id=pid,
                priority="critical",
            )
            generated += 1
            continue

    if generated:
        await db.commit()
    return generated
