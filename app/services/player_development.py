"""
CA/PA progression and aging system.

Hooked into advance_day. Each game day:
1. Birthday rollover: any player whose birthday is "today" ages +1.
   We lazily synthesize a birth_date if the player only has `age`.
2. CA tick: for every player in the player's career squad (and ~50
   sampled AI players for world progression), compute daily CA gain
   using the formula:

   daily_gain = base * age_modifier * training_modifier *
                morale_modifier * (PA - CA) / PA

   The accumulated fractional gains are stored per player in
   `player_dev_progress` (lazy-created column on player_hidden_attrs).
3. When accumulated >= 1.0, CA increases by 1 (capped at PA).
4. After 30+, daily_gain becomes negative — physical attributes drop
   first.

This service is intentionally decoupled from the match engine. The
match engine reads CA at match time, but does NOT itself advance CA.

Public API:
- run_daily_progression(db, career_id, on_date)
- get_player_dev_summary(db, player_id) -> {ca, pa, recent_delta}
"""

from __future__ import annotations
import json
import random
from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Age modifier curve. Keys are age, values are multipliers per the spec.
def _age_modifier(age: int) -> float:
    if age <= 16: return 2.2
    if age <= 17: return 2.0
    if age <= 19: return 1.8
    if age <= 20: return 1.6
    if age <= 22: return 1.2
    if age <= 23: return 1.0
    if age <= 25: return 0.8
    if age <= 26: return 0.6
    if age <= 28: return 0.4
    if age <= 29: return 0.25
    if age <= 30: return 0.05
    if age <= 32: return -0.10   # decline begins
    if age <= 34: return -0.25
    return -0.40


_TRAINING_FACTOR = {
    # No plan picked at all → players still progress, but ~3x slower.
    # This gives the user a real reason to set up a training schedule.
    "none":     0.35,
    "":         0.35,
    "balanced": 1.0,
    "attack":   1.05,
    "defense":  1.05,
    "fitness":  1.10,
    "set_pieces": 0.95,
    "recovery": 0.7,
    "low":      0.7,
    "normal":   1.0,
    "high":     1.2,
}


async def _ensure_progress_column(db: AsyncSession) -> None:
    """player_hidden_attrs may not have the dev_progress column yet —
    add it lazily."""
    try:
        await db.execute(text(
            "ALTER TABLE player_hidden_attrs ADD COLUMN dev_progress REAL DEFAULT 0"
        ))
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute(text(
            "ALTER TABLE player_hidden_attrs ADD COLUMN birth_date VARCHAR(10)"
        ))
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute(text(
            "ALTER TABLE player_hidden_attrs ADD COLUMN morale INTEGER DEFAULT 70"
        ))
        await db.commit()
    except Exception:
        pass


async def _get_or_create_hidden(db: AsyncSession, player_id: int, age: int) -> Dict[str, Any]:
    """Read hidden attrs row, lazily create with deterministic defaults."""
    r = await db.execute(text(
        "SELECT injury_proneness, ambition, professionalism, loyalty, "
        "adaptability, agent_greed, agent_patience, dev_progress, birth_date, morale "
        "FROM player_hidden_attrs WHERE player_id = :p"
    ), {"p": player_id})
    row = r.fetchone()
    if row is not None and row[8]:
        return {
            "injury_proneness": row[0] or 10, "ambition": row[1] or 10,
            "professionalism": row[2] or 10, "loyalty": row[3] or 10,
            "adaptability": row[4] or 10, "agent_greed": row[5] or 10,
            "agent_patience": row[6] or 10, "dev_progress": row[7] or 0.0,
            "birth_date": row[8], "morale": row[9] or 70,
        }

    # Lazy create with deterministic seeds keyed off player_id.
    seed = player_id
    inj = 6 + (seed * 13) % 11
    amb = 6 + (seed * 17) % 11
    prof = 6 + (seed * 23) % 11

    # Synthesize a birth date that fits the age.
    # Pick a deterministic month/day from player_id, year = 2025 - age.
    month = (seed % 12) + 1
    day_max = 28
    day = (seed // 13 % day_max) + 1
    yr = 2025 - max(15, age)
    bdate = f"{yr:04d}-{month:02d}-{day:02d}"

    if row is None:
        try:
            await db.execute(text(
                "INSERT INTO player_hidden_attrs "
                "(player_id, injury_proneness, ambition, professionalism, "
                "loyalty, adaptability, agent_greed, agent_patience, "
                "dev_progress, birth_date, morale) "
                "VALUES (:p, :ip, :a, :pr, 10, 10, 10, 10, 0, :bd, 70)"
            ), {"p": player_id, "ip": inj, "a": amb, "pr": prof, "bd": bdate})
            await db.commit()
        except Exception:
            pass
    else:
        try:
            await db.execute(text(
                "UPDATE player_hidden_attrs SET birth_date = :bd "
                "WHERE player_id = :p AND birth_date IS NULL"
            ), {"p": player_id, "bd": bdate})
            await db.commit()
        except Exception:
            pass

    return {
        "injury_proneness": inj, "ambition": amb,
        "professionalism": prof, "loyalty": 10,
        "adaptability": 10, "agent_greed": 10,
        "agent_patience": 10, "dev_progress": 0.0,
        "birth_date": bdate, "morale": 70,
    }


async def run_daily_progression(
    db: AsyncSession,
    *,
    career_id: int,
    on_date: str,
    training_mode: str = "balanced",
) -> Dict[str, Any]:
    """One-day CA/PA tick + birthday rollover. Returns counters."""
    await _ensure_progress_column(db)

    # Lazy import to avoid circular load
    from app.data.training_roles import TRAINING_ROLES, auto_pick_role

    # 1) Birthdays — for ALL players whose birth_date matches today.
    md = on_date[5:]  # "MM-DD"
    bd_rows = await db.execute(text(
        "SELECT pha.player_id FROM player_hidden_attrs pha "
        "WHERE substr(pha.birth_date, 6, 5) = :md"
    ), {"md": md})
    birthday_pids = [r[0] for r in bd_rows.fetchall()]
    if birthday_pids:
        ph = ",".join(f":p{i}" for i in range(len(birthday_pids)))
        params = {f"p{i}": pid for i, pid in enumerate(birthday_pids)}
        await db.execute(text(
            f"UPDATE players SET age = age + 1 WHERE id IN ({ph})"
        ), params)
        await db.commit()

    # 2) CA tick — only for player's squad + sampled AI players (200 rows
    # to keep the daily cost bounded).
    rows = await db.execute(text(
        "SELECT p.id, p.age, p.ca, p.pa, p.position, sp.morale, sp.is_injured, "
        "sp.individual_intensity, sp.training_role, sp.individual_focus "
        "FROM players p "
        "INNER JOIN squad_players sp ON sp.player_id = p.id "
        "WHERE sp.career_id = :c "
        "UNION ALL "
        "SELECT id, age, ca, pa, position, NULL, NULL, NULL, NULL, NULL FROM players "
        "WHERE id NOT IN (SELECT player_id FROM squad_players WHERE career_id = :c) "
        "ORDER BY RANDOM() LIMIT 250"
    ), {"c": career_id})

    promotions = 0
    declines = 0
    for r in rows.fetchall():
        pid, age, ca, pa, position, morale, is_injured, indiv, training_role, focus = r
        if not pa or not ca or pa <= 0:
            continue
        if is_injured:
            continue   # frozen during injury
        h = await _get_or_create_hidden(db, pid, age or 24)

        amod = _age_modifier(age or 24)
        if amod == 0:
            continue

        tmod = _TRAINING_FACTOR.get(training_mode, 1.0)
        if indiv:
            tmod *= _TRAINING_FACTOR.get(indiv, 1.0)
        morale_use = morale if morale is not None else h["morale"]
        morale_mod = 0.85 + (morale_use / 100) * 0.30   # 0.85..1.15

        # Base daily gain: scaled to "1 CA per ~14 days at age 19, normal".
        base = 0.07
        if amod > 0:
            head = max(0.02, (pa - ca) / pa)
            gain = base * amod * tmod * morale_mod * head
        else:
            # decline path
            gain = base * amod * (1 - 0.02 * (age or 30))

        # Add some jitter
        gain += (random.random() - 0.5) * 0.02

        new_progress = (h["dev_progress"] or 0.0) + gain
        new_ca = ca

        if new_progress >= 1.0 and ca < pa:
            new_ca = ca + 1
            new_progress -= 1.0
            promotions += 1
            # Distribute the +1 CA gain into one of the role's key attributes.
            role_code = training_role or auto_pick_role(position or "")
            role = TRAINING_ROLES.get(role_code) or {}
            key_attrs = list(role.get("key_attributes") or [])
            if focus:
                # weighted: focus appears 3x more often
                key_attrs = key_attrs + [focus] * 3
            if key_attrs:
                pick = random.choice(key_attrs)
                # Bump that attribute, capped at 20.
                try:
                    await db.execute(text(
                        f"UPDATE players SET {pick} = MIN(20, COALESCE({pick}, 10) + 1) "
                        "WHERE id = :p"
                    ), {"p": pid})
                except Exception:
                    pass
        elif new_progress <= -1.0 and ca > 1:
            new_ca = max(1, ca - 1)
            new_progress += 1.0
            declines += 1
            # Decline drops physical attributes first.
            phys = ["pace", "acceleration", "stamina", "agility", "strength"]
            pick = random.choice(phys)
            try:
                await db.execute(text(
                    f"UPDATE players SET {pick} = MAX(1, COALESCE({pick}, 10) - 1) "
                    "WHERE id = :p"
                ), {"p": pid})
            except Exception:
                pass

        await db.execute(text(
            "UPDATE players SET ca = :ca WHERE id = :p"
        ), {"ca": new_ca, "p": pid})
        await db.execute(text(
            "UPDATE player_hidden_attrs SET dev_progress = :pg WHERE player_id = :p"
        ), {"pg": new_progress, "p": pid})

    await db.commit()
    return {
        "promotions": promotions,
        "declines": declines,
        "birthdays": len(birthday_pids),
    }


async def get_player_dev_summary(db: AsyncSession, player_id: int) -> Dict[str, Any]:
    r = await db.execute(text(
        "SELECT p.ca, p.pa, p.age, pha.dev_progress, pha.birth_date "
        "FROM players p LEFT JOIN player_hidden_attrs pha "
        "ON pha.player_id = p.id WHERE p.id = :p"
    ), {"p": player_id})
    row = r.fetchone()
    if not row:
        return {}
    ca, pa, age, prog, bd = row
    return {
        "ca": ca, "pa": pa, "age": age,
        "dev_progress": prog or 0.0,
        "birth_date": bd,
    }
