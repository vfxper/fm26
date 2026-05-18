"""
Injury system. Implements the model the user spec'd:
- Injury catalogue with severity, body_part, ca_impact, attribute_drops.
- player_injuries: active + historical injuries per career.
- Risk computation for matches and training.
- Recovery progression on advance_day.
- Inbox news on serious injuries to player's club.

Public API:
- ensure_catalogue_seeded(db): seed injury_types if empty
- maybe_inflict_match_injury(db, career_id, player_id, intensity, on_date)
- run_daily_training_check(db, career_id, on_date, training_intensity)
- progress_recoveries(db, career_id, on_date) -> list of returners
- get_active_injuries(db, career_id) -> list of dicts for UI
"""

from __future__ import annotations
import json
import random
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_CATALOGUE = [
    # name, body_part, severity, min, max, reocc, ca_impact, attr_drops, surgery, surgery_days
    ("Лёгкий ушиб", "Нога", "minor", 2, 5, 1.0, 0.02, {}, False, 0),
    ("Растяжение мышцы", "Бедро", "minor", 7, 14, 1.1, 0.03, {"pace": 1, "stamina": 1}, False, 0),
    ("Подколенное растяжение", "Бедро", "minor", 10, 18, 1.2, 0.04, {"acceleration": 1}, False, 0),
    ("Растяжение икры", "Икра", "minor", 7, 16, 1.1, 0.04, {"pace": 1}, False, 0),
    ("Удар по голове", "Голова", "minor", 2, 7, 1.0, 0.03, {"concentration": 1}, False, 0),
    ("Растяжение лодыжки", "Лодыжка", "moderate", 14, 28, 1.2, 0.06, {"agility": 2}, False, 0),
    ("Разрыв мышцы бедра", "Бедро", "moderate", 21, 42, 1.3, 0.10, {"pace": 2, "acceleration": 2}, False, 0),
    ("Перелом пальца ноги", "Ступня", "moderate", 18, 30, 1.1, 0.05, {}, False, 0),
    ("Перелом носа", "Голова", "moderate", 7, 14, 1.0, 0.04, {}, False, 0),
    ("Перелом ребра", "Туловище", "moderate", 21, 42, 1.0, 0.07, {"strength": 2}, False, 0),
    ("Сотрясение", "Голова", "moderate", 10, 21, 1.0, 0.06, {"concentration": 2}, False, 0),
    ("Травма колена", "Колено", "major", 60, 120, 1.5, 0.15, {"pace": 3, "acceleration": 3}, True, 14),
    ("Перелом ноги", "Нога", "major", 90, 150, 1.4, 0.18, {"pace": 3, "stamina": 2}, True, 21),
    ("Травма ахилла", "Ахилл", "major", 120, 180, 1.6, 0.20, {"acceleration": 4}, True, 14),
    ("Разрыв крестов", "Колено", "career_threatening", 240, 360, 2.0, 0.25, {"pace": 5, "acceleration": 5, "agility": 4}, True, 30),
    ("Двойной перелом ноги", "Нога", "career_threatening", 240, 365, 2.0, 0.25, {"pace": 5, "stamina": 3}, True, 30),
    ("Простуда", "Общее", "minor", 2, 5, 1.0, 0.01, {}, False, 0),
    ("Грипп", "Общее", "minor", 4, 8, 1.0, 0.02, {"stamina": 1}, False, 0),
    # GK-specific
    ("Травма пальца", "Кисть", "minor", 7, 14, 1.0, 0.04, {}, False, 0),
    ("Вывих плеча", "Плечо", "moderate", 21, 35, 1.3, 0.08, {"strength": 2}, False, 0),
]


async def ensure_catalogue_seeded(db: AsyncSession) -> None:
    """Insert injury_types rows once. No-op if already seeded."""
    try:
        r = await db.execute(text("SELECT COUNT(*) FROM injury_types"))
        if (r.scalar() or 0) > 0:
            return
        for row in _CATALOGUE:
            name, body, sev, mn, mx, reocc, ca, drops, surg, surg_days = row
            await db.execute(
                text(
                    "INSERT INTO injury_types "
                    "(name, body_part, severity, min_days, max_days, reoccurrence_risk, "
                    "ca_impact, attribute_drops, requires_surgery, surgery_days) "
                    "VALUES (:n, :b, :s, :mn, :mx, :r, :c, :a, :sg, :sd)"
                ),
                {
                    "n": name, "b": body, "s": sev,
                    "mn": mn, "mx": mx, "r": reocc, "c": ca,
                    "a": json.dumps(drops, ensure_ascii=False),
                    "sg": 1 if surg else 0,
                    "sd": surg_days,
                },
            )
        await db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"  Injury catalogue seed warning: {e}")


async def _get_proneness(db: AsyncSession, player_id: int) -> int:
    r = await db.execute(
        text("SELECT injury_proneness FROM player_hidden_attrs WHERE player_id = :pid"),
        {"pid": player_id},
    )
    v = r.scalar()
    if v is not None:
        return int(v)
    # Lazy-create with deterministic value keyed off player_id (1-20 range).
    val = 6 + (player_id * 13) % 11   # 6-16 typical
    try:
        await db.execute(
            text("INSERT INTO player_hidden_attrs (player_id, injury_proneness) VALUES (:p, :v)"),
            {"p": player_id, "v": val},
        )
        await db.commit()
    except Exception:
        pass
    return val


def _weight_severity(proneness: int) -> Dict[str, float]:
    """Skew distribution: more proneness -> heavier injuries more likely."""
    bias = (proneness - 10) * 0.02   # -0.2..+0.2
    return {
        "minor": max(0.05, 0.60 - bias),
        "moderate": 0.30,
        "major": min(0.40, 0.09 + bias),
        "career_threatening": min(0.10, 0.01 + max(0, bias) * 0.5),
    }


async def _select_injury_type(db: AsyncSession, source: str, position: str, proneness: int) -> Optional[Dict[str, Any]]:
    """Pick an injury_types row, weighted by severity bias and source pool."""
    # Load full catalogue
    r = await db.execute(text(
        "SELECT id, name, body_part, severity, min_days, max_days, "
        "reoccurrence_risk, ca_impact, attribute_drops, requires_surgery, "
        "surgery_days FROM injury_types"
    ))
    rows = r.fetchall()
    if not rows:
        return None

    # Filter by source
    pool = []
    for row in rows:
        # training -> mostly minor/moderate muscle/joint, exclude career_threatening
        sev = row[3]
        body = row[2]
        if source == "training" and sev in ("major", "career_threatening") and random.random() > 0.05:
            continue
        # Position bias
        if position and "GK" in position:
            if "пальц" in row[1].lower() or "плеч" in row[1].lower() or row[1] == "Удар по голове":
                pool.extend([row] * 3)
            else:
                pool.append(row)
        else:
            pool.append(row)

    if not pool:
        pool = list(rows)

    # Weight by severity
    weights = _weight_severity(proneness)
    weighted = [(row, weights.get(row[3], 0.1)) for row in pool]
    total = sum(w for _, w in weighted)
    if total <= 0:
        chosen = random.choice(pool)
    else:
        r2 = random.random() * total
        acc = 0.0
        chosen = pool[-1]
        for row, w in weighted:
            acc += w
            if r2 <= acc:
                chosen = row
                break

    return {
        "id": chosen[0],
        "name": chosen[1],
        "body_part": chosen[2],
        "severity": chosen[3],
        "min_days": chosen[4],
        "max_days": chosen[5],
        "reocc": chosen[6],
        "ca_impact": chosen[7],
        "attribute_drops": json.loads(chosen[8]) if chosen[8] else {},
        "requires_surgery": bool(chosen[9]),
        "surgery_days": chosen[10] or 0,
    }


def _add_days(date_str: str, days: int) -> str:
    from datetime import date, timedelta
    y, m, d = (int(p) for p in date_str.split("-"))
    new = date(y, m, d) + timedelta(days=days)
    return str(new)


async def _push_injury_news(db: AsyncSession, career_id: int, player_name: str, injury: Dict[str, Any], return_date: str, source: str) -> None:
    try:
        from app.api.routes.inbox import push_inbox_message
        sev_ru = {
            "minor": "лёгкая",
            "moderate": "средней тяжести",
            "major": "серьёзная",
            "career_threatening": "карьероугрожающая",
        }.get(injury["severity"], injury["severity"])
        ctx = "в матче" if source == "match" else "на тренировке"
        await push_inbox_message(
            db, career_id,
            category="injury",
            subject=f"⚕ Травма: {player_name} — {injury['name']}",
            body=(
                f"Получил повреждение {ctx}. Тяжесть: {sev_ru}. "
                f"Часть тела: {injury['body_part']}. "
                f"Ожидаемое возвращение: {return_date}."
            ),
            on_date=return_date,
            is_pinned=injury["severity"] in ("major", "career_threatening"),
        )
    except Exception:
        pass


async def maybe_inflict_match_injury(
    db: AsyncSession,
    *,
    career_id: int,
    player_id: int,
    player_name: str,
    position: str,
    on_date: str,
    intensity: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """Roll an injury during/after a match. Returns the inflicted injury dict
    or None. Saves to player_injuries + flips squad_players.is_injured."""
    proneness = await _get_proneness(db, player_id)
    base = 0.012 * intensity  # ~1.2% per match per "risk slot"
    risk = base * (1 + (proneness - 10) * 0.10)
    if random.random() > risk:
        return None
    injury = await _select_injury_type(db, "match", position or "", proneness)
    if not injury:
        return None
    days = random.randint(injury["min_days"], injury["max_days"])
    return_date = _add_days(on_date, days)
    await db.execute(
        text(
            "INSERT INTO player_injuries "
            "(career_id, player_id, injury_type_id, start_date, "
            "estimated_return_date, treatment_type, source, is_active) "
            "VALUES (:c, :p, :i, :s, :r, 'physio', 'match', 1)"
        ),
        {"c": career_id, "p": player_id, "i": injury["id"],
         "s": on_date, "r": return_date},
    )
    await db.execute(
        text("UPDATE squad_players SET is_injured = 1 "
             "WHERE career_id = :c AND player_id = :p"),
        {"c": career_id, "p": player_id},
    )
    await db.commit()
    await _push_injury_news(db, career_id, player_name, injury, return_date, "match")
    return injury


async def run_daily_training_check(
    db: AsyncSession,
    *,
    career_id: int,
    on_date: str,
    training_intensity: str = "normal",
) -> int:
    """Once per day check every fit squad player for a training injury.
    Returns the count of new injuries inflicted."""
    intensity_factor = {"low": 0.5, "normal": 1.0, "balanced": 1.0,
                        "fitness": 1.4, "attack": 1.1, "defense": 1.1,
                        "set_pieces": 0.9, "recovery": 0.4,
                        "high": 1.6}.get(training_intensity, 1.0)

    rows = await db.execute(text(
        "SELECT sp.player_id, sp.fatigue, p.name, p.position FROM squad_players sp "
        "JOIN players p ON p.id = sp.player_id "
        "WHERE sp.career_id = :c AND sp.is_injured = 0"
    ), {"c": career_id})
    inflicted = 0
    for row in rows.fetchall():
        pid, fatigue, name, pos = row
        proneness = await _get_proneness(db, pid)
        base = 0.0008 * intensity_factor   # ~0.08% per player per day at normal
        risk = base * (1 + (proneness - 10) * 0.08) * (1 + (fatigue or 0) / 100)
        if random.random() > risk:
            continue
        injury = await _select_injury_type(db, "training", pos or "", proneness)
        if not injury:
            continue
        days = random.randint(injury["min_days"], injury["max_days"])
        return_date = _add_days(on_date, days)
        await db.execute(
            text(
                "INSERT INTO player_injuries "
                "(career_id, player_id, injury_type_id, start_date, "
                "estimated_return_date, treatment_type, source, is_active) "
                "VALUES (:c, :p, :i, :s, :r, 'physio', 'training', 1)"
            ),
            {"c": career_id, "p": pid, "i": injury["id"],
             "s": on_date, "r": return_date},
        )
        await db.execute(
            text("UPDATE squad_players SET is_injured = 1 "
                 "WHERE career_id = :c AND player_id = :p"),
            {"c": career_id, "p": pid},
        )
        await _push_injury_news(db, career_id, name, injury, return_date, "training")
        inflicted += 1
    await db.commit()
    return inflicted


async def progress_recoveries(db: AsyncSession, *, career_id: int, on_date: str) -> List[str]:
    """Move injuries that have hit their estimated_return_date to 'returned'.
    Returns the names of the players that recovered today."""
    rows = await db.execute(text(
        "SELECT pi.id, pi.player_id, p.name "
        "FROM player_injuries pi JOIN players p ON p.id = pi.player_id "
        "WHERE pi.career_id = :c AND pi.is_active = 1 "
        "AND pi.estimated_return_date <= :d"
    ), {"c": career_id, "d": on_date})
    recovered = []
    for row in rows.fetchall():
        pi_id, pid, name = row
        await db.execute(
            text("UPDATE player_injuries SET is_active = 0, actual_return_date = :d "
                 "WHERE id = :id"),
            {"id": pi_id, "d": on_date},
        )
        # Only flip is_injured back to 0 if no other active injury.
        rem = await db.execute(text(
            "SELECT COUNT(*) FROM player_injuries "
            "WHERE career_id = :c AND player_id = :p AND is_active = 1"
        ), {"c": career_id, "p": pid})
        if (rem.scalar() or 0) == 0:
            await db.execute(
                text("UPDATE squad_players SET is_injured = 0, match_fitness = 60 "
                     "WHERE career_id = :c AND player_id = :p"),
                {"c": career_id, "p": pid},
            )
        recovered.append(name)
    await db.commit()

    # Push recovery news
    if recovered:
        try:
            from app.api.routes.inbox import push_inbox_message
            for nm in recovered:
                await push_inbox_message(
                    db, career_id,
                    category="recovery",
                    subject=f"✅ {nm} вернулся в строй",
                    body="Игрок прошёл реабилитацию. Match fitness низкий — нагружай постепенно.",
                    on_date=on_date,
                )
        except Exception:
            pass
    return recovered


async def get_active_injuries(db: AsyncSession, career_id: int) -> List[Dict[str, Any]]:
    rows = await db.execute(text(
        "SELECT pi.id, p.id, p.name, p.position, it.name, it.body_part, "
        "it.severity, pi.start_date, pi.estimated_return_date, pi.treatment_type, pi.source "
        "FROM player_injuries pi JOIN players p ON p.id = pi.player_id "
        "JOIN injury_types it ON it.id = pi.injury_type_id "
        "WHERE pi.career_id = :c AND pi.is_active = 1 "
        "ORDER BY pi.estimated_return_date"
    ), {"c": career_id})
    out = []
    for r in rows.fetchall():
        out.append({
            "injury_id": r[0],
            "player_id": r[1],
            "player_name": r[2],
            "position": r[3],
            "injury_name": r[4],
            "body_part": r[5],
            "severity": r[6],
            "start_date": r[7],
            "return_date": r[8],
            "treatment": r[9],
            "source": r[10],
        })
    return out
