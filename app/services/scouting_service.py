"""
Scouting service: assignments with delivery delays.

Modes:
- search_by_filter: scout searches the database for players matching
  filter criteria (min_pa, max_age, min_age, position, max_value, min_ca).
  Result delivered after 21 days.
- individual: scout one specific player. detail_level 'short' = 7 days,
  'full' = 14 days. Short report shows position, age, club, CA-band.
  Full report shows everything including PA, attribute strengths and
  weaknesses, recommendation grade.
- region_youth: find 15-19 year-old prospects matching min_pa filter.
  Delivered after 21 days, returns up to 20 candidates.

Delivery is checked every advance_day; complete assignments push their
result into inbox + scout_knowledge.
"""

from __future__ import annotations
import json
import random
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _add_days(d: str, days: int) -> str:
    y, m, dd = (int(p) for p in d.split("-"))
    return str(date(y, m, dd) + timedelta(days=days))


async def create_assignment(
    db: AsyncSession,
    *,
    career_id: int,
    mode: str,
    on_date: str,
    player_id: Optional[int] = None,
    detail_level: str = "full",
    filter_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a new scout assignment. Returns assignment id.

    All scout assignments take 21 days (3 weeks). Use the
    ``/scouting/instant-report`` endpoint for an instant report.
    """
    days = 21
    due = _add_days(on_date, days)

    await db.execute(text(
        "INSERT INTO scout_assignments "
        "(career_id, mode, player_id, filter_json, detail_level, "
        "start_date, due_date, status) "
        "VALUES (:c, :m, :p, :f, :dl, :s, :d, 'in_progress')"
    ), {
        "c": career_id, "m": mode, "p": player_id,
        "f": json.dumps(filter_payload or {}, ensure_ascii=False),
        "dl": detail_level, "s": on_date, "d": due,
    })
    await db.commit()
    r = await db.execute(text("SELECT last_insert_rowid()"))
    return int(r.scalar() or 0)


async def list_assignments(db: AsyncSession, career_id: int) -> List[Dict[str, Any]]:
    rows = await db.execute(text(
        "SELECT id, mode, player_id, filter_json, detail_level, "
        "start_date, due_date, status, result_json "
        "FROM scout_assignments WHERE career_id = :c "
        "ORDER BY id DESC LIMIT 100"
    ), {"c": career_id})
    out = []
    for r in rows.fetchall():
        out.append({
            "id": r[0], "mode": r[1], "player_id": r[2],
            "filter": json.loads(r[3]) if r[3] else {},
            "detail_level": r[4], "start_date": r[5], "due_date": r[6],
            "status": r[7],
            "result": json.loads(r[8]) if r[8] else None,
        })
    return out


async def _build_filter_sql(flt: Dict[str, Any]) -> tuple[str, dict]:
    where = ["1=1"]
    params: dict = {}
    if flt.get("min_pa") is not None:
        where.append("pa >= :min_pa")
        params["min_pa"] = int(flt["min_pa"])
    if flt.get("min_ca") is not None:
        where.append("ca >= :min_ca")
        params["min_ca"] = int(flt["min_ca"])
    if flt.get("max_age") is not None:
        where.append("age <= :max_age")
        params["max_age"] = int(flt["max_age"])
    if flt.get("min_age") is not None:
        where.append("age >= :min_age")
        params["min_age"] = int(flt["min_age"])
    if flt.get("position"):
        where.append("position LIKE :pos")
        params["pos"] = f"%{flt['position']}%"
    return " AND ".join(where), params


async def _resolve_assignment(db: AsyncSession, assignment: Dict[str, Any]) -> Dict[str, Any]:
    """Build the result payload for a completed assignment."""
    mode = assignment["mode"]
    if mode == "individual":
        pid = assignment["player_id"]
        if not pid:
            return {"players": []}
        return {"players": [pid]}

    if mode == "region_youth":
        flt = dict(assignment.get("filter") or {})
        flt.setdefault("min_age", 15)
        flt.setdefault("max_age", 19)
        sql, params = await _build_filter_sql(flt)
        rows = await db.execute(text(
            f"SELECT id FROM players WHERE {sql} "
            "ORDER BY pa DESC, ca DESC LIMIT 20"
        ), params)
        return {"players": [r[0] for r in rows.fetchall()]}

    # default: search_by_filter
    flt = dict(assignment.get("filter") or {})
    sql, params = await _build_filter_sql(flt)
    rows = await db.execute(text(
        f"SELECT id FROM players WHERE {sql} "
        "ORDER BY pa DESC, ca DESC LIMIT 30"
    ), params)
    return {"players": [r[0] for r in rows.fetchall()]}


async def deliver_due_assignments(
    db: AsyncSession,
    *,
    career_id: int,
    on_date: str,
) -> List[Dict[str, Any]]:
    """For every scout assignment whose due_date has been reached,
    compute the result, store it, push to inbox, and return the list."""
    rows = await db.execute(text(
        "SELECT id, mode, player_id, filter_json, detail_level, "
        "start_date, due_date, status FROM scout_assignments "
        "WHERE career_id = :c AND status = 'in_progress' "
        "AND due_date <= :d"
    ), {"c": career_id, "d": on_date})
    pending = rows.fetchall()
    delivered = []

    for r in pending:
        a = {
            "id": r[0], "mode": r[1], "player_id": r[2],
            "filter": json.loads(r[3]) if r[3] else {},
            "detail_level": r[4], "start_date": r[5], "due_date": r[6],
        }
        result = await _resolve_assignment(db, a)
        await db.execute(text(
            "UPDATE scout_assignments SET status='completed', result_json=:rj "
            "WHERE id=:id"
        ), {"id": a["id"], "rj": json.dumps(result, ensure_ascii=False)})

        # Update scout_knowledge for each delivered player
        level = 1 if a["detail_level"] == "short" else 2
        for pid in result.get("players", []):
            ex = await db.execute(text(
                "SELECT level FROM scout_knowledge WHERE career_id=:c AND player_id=:p"
            ), {"c": career_id, "p": pid})
            existing = ex.scalar()
            if existing is None:
                await db.execute(text(
                    "INSERT INTO scout_knowledge (career_id, player_id, level, last_seen_date) "
                    "VALUES (:c, :p, :l, :d)"
                ), {"c": career_id, "p": pid, "l": level, "d": on_date})
            elif existing < level:
                await db.execute(text(
                    "UPDATE scout_knowledge SET level=:l, last_seen_date=:d "
                    "WHERE career_id=:c AND player_id=:p"
                ), {"c": career_id, "p": pid, "l": level, "d": on_date})

        delivered.append({**a, "result": result})

    if pending:
        await db.commit()
        # Push inbox messages
        try:
            from app.api.routes.inbox import push_inbox_message
            for d in delivered:
                count = len(d["result"].get("players", []))
                if d["mode"] == "individual":
                    subj = "🔍 Скаут завершил наблюдение"
                    body = f"Доступен {('краткий' if d['detail_level']=='short' else 'полный')} отчёт по игроку. Откройте профиль."
                elif d["mode"] == "region_youth":
                    subj = f"🔎 Скаутинг молодёжи: найдено {count} игроков"
                    body = "Открой вкладку «Переговоры → Скаутинг» чтобы увидеть отчёт."
                else:
                    subj = f"🔎 Скаутинг по фильтру: найдено {count} игроков"
                    body = "Открой вкладку «Переговоры → Скаутинг» чтобы увидеть отчёт."
                await push_inbox_message(
                    db, career_id,
                    category="scouting_done",
                    subject=subj,
                    body=body,
                    on_date=on_date,
                )
        except Exception:
            pass
    return delivered


def build_short_report(player_row: dict) -> dict:
    """Subset visible after 7-day individual scouting."""
    ca = player_row.get("ca") or 0
    band = "★" * min(5, max(1, ca // 35))
    return {
        "name": player_row.get("name"),
        "age": player_row.get("age"),
        "position": player_row.get("position"),
        "club": player_row.get("club"),
        "ca_band": band,
        "potential": "примерный",
        "level": "short",
    }


def build_full_report(player_row: dict, attrs: Optional[Dict[str, int]] = None) -> dict:
    """Full FM-style scout report."""
    a = attrs or {}
    strengths = []
    weaknesses = []

    # Pick top 3 / bottom 3 attributes
    items = [(k, v) for k, v in a.items() if isinstance(v, (int, float))]
    items.sort(key=lambda x: x[1], reverse=True)
    for k, v in items[:5]:
        if v >= 14:
            strengths.append(_attr_label(k, v))
    for k, v in items[-5:]:
        if v <= 8:
            weaknesses.append(_attr_label(k, v))

    ca = player_row.get("ca") or 0
    pa = player_row.get("pa") or 0
    age = player_row.get("age") or 0
    rec = _grade(ca, pa, age)

    return {
        "name": player_row.get("name"),
        "age": player_row.get("age"),
        "position": player_row.get("position"),
        "club": player_row.get("club"),
        "nationality": player_row.get("nationality"),
        "ca": ca,
        "pa": pa,
        "wage": player_row.get("wage"),
        "strengths": strengths or ["Сбалансированный игрок без ярко выраженных сильных сторон"],
        "weaknesses": weaknesses or ["Без явных провалов"],
        "recommendation": rec,
        "level": "full",
    }


def _attr_label(k: str, v: int) -> str:
    rus = {
        "finishing": "Завершение",
        "passing": "Пас",
        "dribbling": "Дриблинг",
        "tackling": "Отбор",
        "marking": "Маркировка",
        "heading": "Игра головой",
        "first_touch": "Первое касание",
        "vision": "Видение",
        "decisions": "Решения",
        "composure": "Хладнокровие",
        "concentration": "Концентрация",
        "anticipation": "Предвидение",
        "off_the_ball": "Игра без мяча",
        "positioning": "Позиционирование",
        "work_rate": "Работа",
        "stamina": "Выносливость",
        "pace": "Скорость",
        "acceleration": "Ускорение",
        "agility": "Ловкость",
        "balance": "Баланс",
        "strength": "Сила",
        "jumping_reach": "Прыгучесть",
        "natural_fitness": "Натуральная форма",
        "long_shots": "Дальние удары",
        "crossing": "Навесы",
        "technique": "Техника",
        "flair": "Креатив",
        "leadership": "Лидерство",
        "teamwork": "Командная игра",
        "aggression": "Агрессия",
        "bravery": "Храбрость",
        "determination": "Целеустремлённость",
    }
    label = rus.get(k, k.replace("_", " "))
    return f"{label} ({v})"


def _grade(ca: int, pa: int, age: int = 0) -> str:
    """Recommendation letter. PA matters far less for old players —
    a 40-year-old with PA 180 is not a future signing.

    Age penalty:
      <30  : full grade
      30-32: cap at A
      33-34: cap at B
      35-36: cap at C
      37+  : cap at D (legend / rotation only)
    """
    # Compute base grade letter from CA/PA.
    base = "D"
    if ca >= 165 or pa >= 175:
        base = "S"
    elif ca >= 150 or pa >= 165:
        base = "A"
    elif ca >= 130 or pa >= 150:
        base = "B"
    elif ca >= 110:
        base = "C"

    # Apply age cap.
    order = ["D", "C", "B", "A", "S"]
    if age >= 37:
        cap = "D"
    elif age >= 35:
        cap = "C"
    elif age >= 33:
        cap = "B"
    elif age >= 30:
        cap = "A"
    else:
        cap = "S"
    final = base if order.index(base) <= order.index(cap) else cap

    labels = {
        "S": "S — мировой класс",
        "A": "A — топ",
        "B": "B — крепкий",
        "C": "C — рабочая лошадка",
        "D": "D — резерв",
    }
    return labels[final]
