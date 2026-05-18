"""
Unified negotiations + scouting API.

Endpoints:
  POST   /careers/{cid}/negotiations/scout/individual  - scout a specific player
  POST   /careers/{cid}/negotiations/scout/filter      - search by criteria (PA, age, etc)
  POST   /careers/{cid}/negotiations/scout/youth       - find 15-19 yo prospects
  GET    /careers/{cid}/negotiations/scout             - list all assignments
  GET    /careers/{cid}/negotiations/scout/{aid}       - assignment detail (with full player report when ready)
  GET    /careers/{cid}/negotiations/transfers/news    - latest AI-vs-AI transfer news
  GET    /careers/{cid}/negotiations/injuries          - injury list (medical center)
  GET    /careers/{cid}/tactics                        - get current tactic + lineup
  POST   /careers/{cid}/tactics                        - persist tactic + lineup + roles
  GET    /careers/{cid}/formations/{name}              - formation slot definitions
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services import scouting_service as scout
from app.services import injury_service as inj
from app.data.formations import FORMATIONS, slots as formation_slots
from app.data.training_roles import TRAINING_ROLES, roles_for_position

router = APIRouter(tags=["negotiations"])


# ─────────── Scouting ────────────────────────────────────────────────────


class ScoutIndividualReq(BaseModel):
    player_id: int
    detail_level: str = Field("full", pattern="^(short|full)$")


class ScoutFilterReq(BaseModel):
    min_pa: Optional[int] = None
    min_ca: Optional[int] = None
    max_age: Optional[int] = None
    min_age: Optional[int] = None
    position: Optional[str] = None


async def _career_date(db: AsyncSession, career_id: int, user_id: int) -> str:
    r = await db.execute(text(
        "SELECT user_id, game_date FROM careers WHERE id=:c"
    ), {"c": career_id})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user_id:
        raise HTTPException(403, "Not your career")
    return row[1] or "2025-07-01"


def _parse_price(raw) -> int:
    """Parse a CSV `price` cell into an integer in £.

    Handles formats like:
      £75M, £3.6M, £425K, £1.5M-1.8M (range -> upper bound),
      £0, Unknown, None, '', plain int, plain float.

    Returns 0 on anything unparseable.
    """
    if raw is None:
        return 0
    if isinstance(raw, (int, float)):
        v = int(raw)
        return v if v > 0 else 0
    s = str(raw).strip()
    if not s or s.lower() in ("unknown", "n/a", "na", "-", "none"):
        return 0
    # Strip currency prefix(es).
    for sym in ("£", "GBP", "$", "€", "EUR", "USD"):
        if s.startswith(sym):
            s = s[len(sym):].strip()
            break
    # Range "1.5M-1.8M" — pick upper bound.
    if "-" in s:
        s = s.split("-")[-1].strip()
        for sym in ("£", "GBP", "$", "€"):
            if s.startswith(sym):
                s = s[len(sym):].strip()
    # Multiplier suffix.
    mul = 1
    if s.endswith(("M", "m")):
        mul = 1_000_000
        s = s[:-1].strip()
    elif s.endswith(("K", "k")):
        mul = 1_000
        s = s[:-1].strip()
    elif s.endswith(("B", "b")):
        mul = 1_000_000_000
        s = s[:-1].strip()
    s = s.replace(",", "").replace(" ", "")
    try:
        v = float(s)
    except ValueError:
        return 0
    if v <= 0:
        return 0
    return int(v * mul)


@router.get("/players/{player_id}/suggested-fee")
async def suggested_fee(
    player_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a recommended starting offer (£) for the buy/loan dialog.

    Anchor on CSV `price` whenever available; fall back to a CA band.
    The frontend uses this to prefill the offer input with a realistic
    number that's specific to THIS player, not just their CA bucket.
    """
    pr = await db.execute(text(
        "SELECT id, name, ca, age, price, wage FROM players WHERE id = :p"
    ), {"p": player_id})
    row = pr.fetchone()
    if not row:
        raise HTTPException(404, "Player not found")
    pid, pname, ca, age, csv_price, wage = row
    fair_high = _parse_price(csv_price)
    # If no CSV price, fall back to CA banding.
    if fair_high <= 0:
        ca = ca or 100
        if ca <= 100:
            fair_high = 1_000_000
        elif ca <= 130:
            fair_high = 10_000_000
        elif ca <= 150:
            fair_high = 35_000_000
        elif ca <= 170:
            fair_high = 80_000_000
        else:
            fair_high = 180_000_000
    # Round to a "human" tier so the field shows a clean number.
    suggested = _round_offer(int(fair_high * 1.05))
    suggested_wage = _round_wage(int(wage or 50_000))
    return {
        "player_id": pid,
        "player_name": pname,
        "csv_price": csv_price,
        "csv_price_parsed": fair_high,
        "suggested_fee": suggested,
        "suggested_wage": suggested_wage,
        "current_wage": wage or 0,
    }


def _round_offer(amount: int) -> int:
    """Round an offer up to a clean tier so 4_278_315 becomes 4_300_000."""
    if amount <= 0:
        return 0
    if amount < 500_000:
        step = 25_000
    elif amount < 5_000_000:
        step = 100_000
    elif amount < 50_000_000:
        step = 500_000
    else:
        step = 1_000_000
    return int(round(amount / step) * step)


def _round_wage(wage: int) -> int:
    """Round a weekly wage to a clean tier (5k / 10k / 25k step)."""
    if wage <= 0:
        return 0
    if wage < 50_000:
        step = 1_000
    elif wage < 200_000:
        step = 5_000
    else:
        step = 10_000
    return int(round(wage / step) * step)


@router.post("/careers/{career_id}/negotiations/scout/individual")
async def scout_individual(
    career_id: int,
    body: ScoutIndividualReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cheap scouting on a single player — €5,000, delivered in 21 days.
    For an instant report use /scouting/instant-report/{player_id}
    (€20,000)."""
    on_date = await _career_date(db, career_id, user.id)

    # Charge €5000 against scouting budget. Refuse if not enough.
    from app.api.routes.scouting import _get_centre
    centre = _get_centre(career_id)
    cost = 5_000
    if centre.budget_spent + cost > centre.scouting_budget:
        raise HTTPException(400, "Недостаточно средств в скаутском бюджете (нужно €5 000)")
    centre.budget_spent += cost

    aid = await scout.create_assignment(
        db, career_id=career_id, mode="individual",
        on_date=on_date, player_id=body.player_id,
        detail_level=body.detail_level,
    )
    return {
        "assignment_id": aid,
        "cost": cost,
        "expected_date": scout._add_days(on_date, 21),
    }


@router.post("/careers/{career_id}/negotiations/scout/filter")
async def scout_filter(
    career_id: int,
    body: ScoutFilterReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search players by filter (min PA, max age, position, ...).
    Costs €15,000 and takes 3 weeks."""
    on_date = await _career_date(db, career_id, user.id)

    from app.api.routes.scouting import _get_centre
    centre = _get_centre(career_id)
    cost = 15_000
    if centre.budget_spent + cost > centre.scouting_budget:
        raise HTTPException(400, "Недостаточно средств в скаутском бюджете (нужно €15 000)")
    centre.budget_spent += cost

    aid = await scout.create_assignment(
        db, career_id=career_id, mode="search_by_filter",
        on_date=on_date, filter_payload=body.model_dump(exclude_none=True),
    )
    return {
        "assignment_id": aid,
        "cost": cost,
        "expected_date": scout._add_days(on_date, 21),
    }


@router.post("/careers/{career_id}/negotiations/scout/youth")
async def scout_youth(
    career_id: int,
    body: ScoutFilterReq = Body(default_factory=ScoutFilterReq),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find 15-19 year-old prospects. €25,000 for 3 weeks of work."""
    on_date = await _career_date(db, career_id, user.id)

    from app.api.routes.scouting import _get_centre
    centre = _get_centre(career_id)
    cost = 25_000
    if centre.budget_spent + cost > centre.scouting_budget:
        raise HTTPException(400, "Недостаточно средств в скаутском бюджете (нужно €25 000)")
    centre.budget_spent += cost

    payload = body.model_dump(exclude_none=True)
    payload.setdefault("min_age", 15)
    payload.setdefault("max_age", 19)
    aid = await scout.create_assignment(
        db, career_id=career_id, mode="region_youth",
        on_date=on_date, filter_payload=payload,
    )
    return {
        "assignment_id": aid,
        "cost": cost,
        "expected_date": scout._add_days(on_date, 21),
    }


@router.get("/careers/{career_id}/negotiations/scout")
async def scout_list(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    return {"assignments": await scout.list_assignments(db, career_id)}


@router.get("/careers/{career_id}/negotiations/scout/{aid}")
async def scout_detail(
    career_id: int,
    aid: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    rows = await db.execute(text(
        "SELECT id, mode, player_id, filter_json, detail_level, "
        "start_date, due_date, status, result_json "
        "FROM scout_assignments WHERE id=:i AND career_id=:c"
    ), {"i": aid, "c": career_id})
    r = rows.fetchone()
    if not r:
        raise HTTPException(404, "Assignment not found")
    a = {
        "id": r[0], "mode": r[1], "player_id": r[2],
        "filter": json.loads(r[3]) if r[3] else {},
        "detail_level": r[4], "start_date": r[5], "due_date": r[6],
        "status": r[7],
        "result": json.loads(r[8]) if r[8] else None,
    }

    # If completed, build full reports for each delivered player.
    reports = []
    if a["status"] == "completed" and a["result"]:
        ids = a["result"].get("players", [])[:30]
        if ids:
            placeholders = ",".join(f":p{i}" for i in range(len(ids)))
            params = {f"p{i}": pid for i, pid in enumerate(ids)}
            prows = await db.execute(text(
                f"SELECT id, name, age, position, club, nationality, ca, pa, wage, "
                f"finishing, dribbling, passing, tackling, marking, heading, "
                f"first_touch, vision, decisions, composure, concentration, "
                f"anticipation, off_the_ball, positioning, work_rate, stamina, "
                f"pace, acceleration, agility, balance, strength, jumping_reach, "
                f"natural_fitness, long_shots, crossing, technique, flair, "
                f"leadership, teamwork, aggression, bravery, determination "
                f"FROM players WHERE id IN ({placeholders})"
            ), params)
            for row in prows.fetchall():
                player_dict = {
                    "id": row[0], "name": row[1], "age": row[2],
                    "position": row[3], "club": row[4], "nationality": row[5],
                    "ca": row[6], "pa": row[7], "wage": row[8],
                }
                attrs = {
                    "finishing": row[9], "dribbling": row[10], "passing": row[11],
                    "tackling": row[12], "marking": row[13], "heading": row[14],
                    "first_touch": row[15], "vision": row[16], "decisions": row[17],
                    "composure": row[18], "concentration": row[19],
                    "anticipation": row[20], "off_the_ball": row[21],
                    "positioning": row[22], "work_rate": row[23],
                    "stamina": row[24], "pace": row[25], "acceleration": row[26],
                    "agility": row[27], "balance": row[28], "strength": row[29],
                    "jumping_reach": row[30], "natural_fitness": row[31],
                    "long_shots": row[32], "crossing": row[33], "technique": row[34],
                    "flair": row[35], "leadership": row[36], "teamwork": row[37],
                    "aggression": row[38], "bravery": row[39], "determination": row[40],
                }
                if a["detail_level"] == "short" and a["mode"] == "individual":
                    reports.append(scout.build_short_report(player_dict))
                else:
                    reports.append(scout.build_full_report(player_dict, attrs))

    return {**a, "reports": reports}


# ─────────── AI transfers news ───────────────────────────────────────────


@router.get("/careers/{career_id}/negotiations/transfers/news")
async def transfer_news(
    career_id: int,
    limit: int = 50,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    rows = await db.execute(text(
        "SELECT player_name, from_club, to_club, fee, is_loan, transfer_date "
        "FROM ai_transfers WHERE career_id=:c "
        "ORDER BY id DESC LIMIT :lim"
    ), {"c": career_id, "lim": limit})
    return {"transfers": [
        {"player": r[0], "from": r[1], "to": r[2],
         "fee": r[3], "is_loan": bool(r[4]), "date": r[5]}
        for r in rows.fetchall()
    ]}


# ─────────── Injuries (medical center) ──────────────────────────────────


@router.get("/careers/{career_id}/negotiations/injuries")
async def injuries_list(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    return {"injuries": await inj.get_active_injuries(db, career_id)}


# ─────────── Tactics + lineup ────────────────────────────────────────────


class TacticsReq(BaseModel):
    """Tactic snapshot. We accept loose types because the frontend can
    send subs as strings or null and we still want to store them."""
    model_config = {"extra": "allow"}

    formation: str = Field("4-3-3")
    mentality: str = "balanced"
    pressing: str = "medium"
    defensive_line: str = "standard"
    tempo: str = "normal"
    width: str = "standard"
    starting_xi: Optional[Dict[str, Any]] = None
    subs: Optional[List[Any]] = None
    player_roles: Optional[Dict[str, Any]] = None


@router.get("/careers/{career_id}/tactics")
async def get_tactics(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    r = await db.execute(text(
        "SELECT formation, mentality, pressing, defensive_line, tempo, width, "
        "starting_xi, subs, player_roles FROM career_tactics WHERE career_id=:c"
    ), {"c": career_id})
    row = r.fetchone()
    if not row:
        return {
            "formation": "4-3-3", "mentality": "balanced",
            "pressing": "medium", "defensive_line": "standard",
            "tempo": "normal", "width": "standard",
            "starting_xi": {}, "subs": [], "player_roles": {},
        }
    return {
        "formation": row[0], "mentality": row[1], "pressing": row[2],
        "defensive_line": row[3], "tempo": row[4], "width": row[5],
        "starting_xi": json.loads(row[6]) if row[6] else {},
        "subs": json.loads(row[7]) if row[7] else [],
        "player_roles": json.loads(row[8]) if row[8] else {},
    }


@router.post("/careers/{career_id}/tactics")
async def post_tactics(
    career_id: int,
    body: TacticsReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _career_date(db, career_id, user.id)
    formation = body.formation if body.formation in FORMATIONS else "4-3-3"
    # Coerce starting_xi values to ints, drop bad keys
    xi: Dict[str, int] = {}
    for k, v in (body.starting_xi or {}).items():
        try:
            xi[str(k)] = int(v)
        except (TypeError, ValueError):
            continue
    subs: list[int] = []
    for v in (body.subs or []):
        try:
            subs.append(int(v))
        except (TypeError, ValueError):
            continue
    player_roles = body.player_roles or {}
    # Upsert
    existing = await db.execute(text(
        "SELECT 1 FROM career_tactics WHERE career_id=:c"
    ), {"c": career_id})
    if existing.fetchone():
        await db.execute(text(
            "UPDATE career_tactics SET "
            "formation=:f, mentality=:m, pressing=:p, defensive_line=:dl, "
            "tempo=:t, width=:w, starting_xi=:xi, subs=:sb, "
            "player_roles=:pr, updated_at=CURRENT_TIMESTAMP "
            "WHERE career_id=:c"
        ), {
            "c": career_id, "f": formation, "m": body.mentality,
            "p": body.pressing, "dl": body.defensive_line, "t": body.tempo,
            "w": body.width,
            "xi": json.dumps(xi),
            "sb": json.dumps(subs),
            "pr": json.dumps(player_roles),
        })
    else:
        await db.execute(text(
            "INSERT INTO career_tactics "
            "(career_id, formation, mentality, pressing, defensive_line, tempo, "
            "width, starting_xi, subs, player_roles) VALUES "
            "(:c, :f, :m, :p, :dl, :t, :w, :xi, :sb, :pr)"
        ), {
            "c": career_id, "f": formation, "m": body.mentality,
            "p": body.pressing, "dl": body.defensive_line, "t": body.tempo,
            "w": body.width,
            "xi": json.dumps(xi),
            "sb": json.dumps(subs),
            "pr": json.dumps(player_roles),
        })
    await db.commit()
    return {"success": True}


@router.get("/formations/{name}")
async def get_formation(name: str):
    if name not in FORMATIONS:
        raise HTTPException(404, "Unknown formation")
    return {"name": name, "slots": formation_slots(name)}


@router.get("/formations")
async def list_formations():
    return {"formations": list(FORMATIONS.keys())}


@router.get("/training-roles")
async def list_training_roles(position: Optional[str] = None):
    if position:
        return {"roles": roles_for_position(position)}
    return {"roles": [{"code": k, **v} for k, v in TRAINING_ROLES.items()]}


# ─────────── Offers (buy / loan) ───────────────────────────────────────


class OfferReq(BaseModel):
    player_id: int
    fee: int = 0
    wage: int = 50000
    contract_years: int = 3
    is_loan: bool = False
    loan_type: Optional[str] = None        # simple | mandatory_buyback | optional_buyback
    loan_buyback_fee: Optional[int] = None
    loan_until: Optional[str] = None       # YYYY-MM-DD


@router.post("/careers/{career_id}/negotiations/offer")
async def make_offer(
    career_id: int,
    body: OfferReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Player issues an offer to buy / loan a foreign player.

    Loans are accepted nearly always (90% if fee is reasonable).
    Permanent transfers go through 1-3 negotiation rounds: club almost
    never accepts the first offer, returns counter at fair_high * 1.05;
    second offer accepted if >= fair_high * 0.95; third offer always
    final.
    """
    on_date = await _career_date(db, career_id, user.id)

    # Validate window
    y, m, _d = (int(p) for p in on_date.split("-"))
    in_window = m in (7, 8) or m == 1
    if not in_window:
        raise HTTPException(400, "Трансферное окно закрыто")

    # Get target player & current club. Pull `price` from CSV
    # (column 85: "£X" or "£X.XM" / "£X-Y" range) so the asking value
    # tracks each player's real CSV market value, not just CA-banding.
    pr = await db.execute(text(
        "SELECT id, name, club, ca, age, price FROM players WHERE id = :p"
    ), {"p": body.player_id})
    row = pr.fetchone()
    if not row:
        raise HTTPException(404, "Игрок не найден")
    pid, pname, current_club, ca, age, csv_price = row

    # Block buying own squad players
    own = await db.execute(text(
        "SELECT 1 FROM squad_players WHERE career_id=:c AND player_id=:p"
    ), {"c": career_id, "p": pid})
    if own.fetchone():
        raise HTTPException(400, "Игрок уже в вашем составе")

    # Fair market value derived primarily from CSV `price`. CA-banding
    # is used as a fallback when the CSV value is missing or
    # unparseable. CSV values look like "£75M", "£3.6M", "£425K",
    # "£1.5M-1.8M" (range), occasionally "£0" or "Unknown".
    fair_high: int = 0
    fair_low: int = 0
    try:
        fair_high = _parse_price(csv_price)
    except Exception:
        fair_high = 0
    if fair_high > 0:
        # Range is +/- 30% around the CSV anchor.
        fair_low = max(50_000, int(fair_high * 0.70))
    else:
        # CSV missing — fall back to CA banding.
        if ca <= 100:
            fair_low, fair_high = 200_000, 2_500_000
        elif ca <= 130:
            fair_low, fair_high = 2_000_000, 18_000_000
        elif ca <= 150:
            fair_low, fair_high = 15_000_000, 60_000_000
        elif ca <= 170:
            fair_low, fair_high = 50_000_000, 110_000_000
        else:
            fair_low, fair_high = 100_000_000, 280_000_000

    # Count prior offer attempts for this player in this career
    prior = await db.execute(text(
        "SELECT COUNT(*) FROM transfer_offers "
        "WHERE career_id=:c AND player_id=:p AND direction='outgoing'"
    ), {"c": career_id, "p": pid})
    attempts = int(prior.scalar() or 0)

    accepted = False
    counter_fee = None
    rejected = False

    if body.is_loan:
        # Loans: accepted 90% of the time
        import random
        accepted = random.random() < 0.90
    else:
        # Permanent transfer negotiation
        threshold_first = int(fair_high * 1.10)   # 10% above fair_high
        threshold_second = int(fair_high * 0.95)
        threshold_third = int(fair_high * 0.85)
        # An offer below 50% of the LOW end of the fair range is
        # insulting — the selling club walks away from the table
        # rather than counter. The user has to come back next window.
        insult_floor = int(fair_low * 0.50)

        if attempts == 0 and body.fee < insult_floor:
            rejected = True
            insult_reject = True
        elif attempts == 0:
            # First offer — almost always counter unless extremely high.
            # Counter must be STRICTLY above the user's offer (otherwise
            # the AI is essentially saying "we want less than you bid",
            # which is nonsense).
            if body.fee >= threshold_first:
                accepted = True
            else:
                counter_fee = max(
                    int(fair_high * 1.05),
                    int(body.fee * 1.10),
                )
            insult_reject = False
        elif attempts == 1:
            # Second offer — accept if at least near fair_high
            if body.fee >= threshold_second:
                accepted = True
            else:
                counter_fee = max(
                    int(fair_high * 0.97),
                    int(body.fee * 1.05),
                )
            insult_reject = False
        elif attempts == 2:
            # Third — final attempt
            if body.fee >= threshold_third:
                accepted = True
            else:
                rejected = True
            insult_reject = False
        else:
            # Spam — auto-reject
            rejected = True
            insult_reject = False

    # Insert offer record (always)
    status_val = (
        "accepted" if accepted
        else "rejected" if rejected
        else "counter"
    )
    await db.execute(text(
        "INSERT INTO transfer_offers "
        "(career_id, direction, player_id, from_club_name, to_club_name, "
        "fee, wage, contract_years, role, sell_on_pct, loan_type, "
        "loan_buyback_fee, loan_until, status, counter_fee, created_date) "
        "VALUES (:c, 'outgoing', :p, :fc, :tc, :fee, :w, :y, "
        "'first_team', 0, :lt, :lb, :lu, :s, :cf, :d)"
    ), {
        "c": career_id, "p": pid, "fc": current_club, "tc": "Player Club",
        "fee": body.fee, "w": body.wage, "y": body.contract_years,
        "lt": body.loan_type if body.is_loan else None,
        "lb": body.loan_buyback_fee, "lu": body.loan_until,
        "s": status_val, "cf": counter_fee, "d": on_date,
    })
    offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
    offer_id = int(offer_id_row.scalar() or 0)

    # If accepted, transfer the player.
    if accepted:
        # Get career club_id + budget
        cr = await db.execute(text(
            "SELECT club_id, budget FROM careers WHERE id=:c"
        ), {"c": career_id})
        cc = cr.fetchone()
        if not cc:
            raise HTTPException(404, "Career not found")
        budget = float(cc[1] or 0)
        if not body.is_loan and budget < body.fee:
            raise HTTPException(400, f"Недостаточно бюджета: £{int(budget):,} < £{body.fee:,}")

        # Pull the player's club name for inbox
        from app.data.club_budgets import CLUBS
        club_name = "your club"
        if cc[0] and 1 <= cc[0] <= len(CLUBS):
            club_name = CLUBS[cc[0] - 1][0]

        # Update player.club + add to squad_players
        if not body.is_loan:
            await db.execute(text(
                "UPDATE players SET club = :nc WHERE id = :p"
            ), {"nc": club_name, "p": pid})
            await db.execute(text(
                "UPDATE careers SET budget = budget - :f WHERE id = :c"
            ), {"f": body.fee, "c": career_id})

        # Find a free squad number
        used = await db.execute(text(
            "SELECT squad_number FROM squad_players WHERE career_id=:c"
        ), {"c": career_id})
        used_nums = {int(r[0]) for r in used.fetchall() if r[0]}
        num = next((n for n in range(1, 100) if n not in used_nums), 99)
        await db.execute(text(
            "INSERT INTO squad_players "
            "(career_id, player_id, squad_number, status, morale, fitness, "
            "wage, contract_years, contract_expiry, is_transfer_listed, "
            "is_loan_listed, is_injured, is_loaned) "
            "VALUES (:c, :p, :n, 'first_team', 75, 100, :w, :y, '2028-06-30', "
            "0, 0, 0, :loaned)"
        ), {
            "c": career_id, "p": pid, "n": num,
            "w": body.wage, "y": body.contract_years,
            "loaned": 1 if body.is_loan else 0,
        })

        # Inbox + AI ledger
        await db.execute(text(
            "INSERT INTO ai_transfers "
            "(career_id, player_id, player_name, from_club, to_club, fee, "
            "is_loan, transfer_date) "
            "VALUES (:c, :p, :pn, :fc, :tc, :f, :l, :d)"
        ), {
            "c": career_id, "p": pid, "pn": pname,
            "fc": current_club or "Unknown", "tc": club_name,
            "f": body.fee, "l": 1 if body.is_loan else 0, "d": on_date,
        })
        try:
            from app.api.routes.inbox import push_inbox_message
            label = "арендован" if body.is_loan else f"куплен за £{body.fee:,}"
            await push_inbox_message(
                db, career_id,
                category="transfer_done",
                subject=f"✅ {pname} {label}",
                body=f"Игрок присоединился к {club_name}.",
                on_date=on_date,
            )
        except Exception:
            pass

    await db.commit()
    return {
        "success": accepted,
        "status": status_val,
        "counter_fee": counter_fee,
        "fair_high": fair_high,
        "fair_low": fair_low,
        "offer_id": offer_id,
        "attempt": attempts + 1,
        "insult": insult_reject if not body.is_loan else False,
    }


class SellReq(BaseModel):
    squad_player_id: int
    asking_price: int


@router.post("/careers/{career_id}/negotiations/sell")
async def sell_player(
    career_id: int,
    body: SellReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark player as transfer-listed with an asking price. AI clubs will
    buy if any of them values the player at or above the price."""
    on_date = await _career_date(db, career_id, user.id)

    # Mark listed
    await db.execute(text(
        "UPDATE squad_players SET is_transfer_listed = 1 "
        "WHERE id = :s AND career_id = :c"
    ), {"s": body.squad_player_id, "c": career_id})
    # Store the asking price in `wage` adjacent column? Use payload table.
    # For simplicity, record via transfer_offers with direction='listing'.
    sp = await db.execute(text(
        "SELECT player_id FROM squad_players WHERE id = :s AND career_id = :c"
    ), {"s": body.squad_player_id, "c": career_id})
    sp_row = sp.fetchone()
    if not sp_row:
        raise HTTPException(404, "Squad player not found")
    pid = sp_row[0]
    await db.execute(text(
        "INSERT INTO transfer_offers "
        "(career_id, direction, player_id, fee, status, created_date) "
        "VALUES (:c, 'listing', :p, :f, 'pending', :d)"
    ), {"c": career_id, "p": pid, "f": body.asking_price, "d": on_date})
    await db.commit()

    # NOTE: we deliberately do NOT generate AI bids synchronously here.
    # The user wanted a realistic delay — bids should arrive 1-3 in-game
    # days after listing, not the same day. The standard
    # `run_daily_ai_transfers` loop (called from advance-day) will pick
    # up listed players naturally and emit offers over the next few days.

    return {"success": True, "asking_price": body.asking_price}
