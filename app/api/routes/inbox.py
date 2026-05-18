"""
Inbox API — manager-facing message feed (FM-style).

Endpoints:
  GET    /api/careers/{career_id}/inbox            - List messages (newest first)
  POST   /api/careers/{career_id}/inbox/read-all   - Mark all as read
  POST   /api/careers/{career_id}/inbox/{id}/read  - Mark one as read
  DELETE /api/careers/{career_id}/inbox/{id}       - Delete a message
  POST   /api/careers/{career_id}/inbox            - (internal) push a message
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.utils.money import format_money

router = APIRouter(prefix="/careers/{career_id}/inbox", tags=["inbox"])


class InboxPushRequest(BaseModel):
    category: str = Field(..., max_length=30)
    subject: str = Field(..., max_length=255)
    body: str = Field("", max_length=2000)
    payload: Optional[Dict[str, Any]] = None


@router.get("")
async def list_inbox(
    career_id: int,
    only_unread: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return messages newest first."""
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")

    sql = (
        "SELECT id, created_date, category, subject, body, is_read, is_pinned, payload "
        "FROM inbox_messages WHERE career_id = :cid "
    )
    if only_unread:
        sql += "AND is_read = 0 "
    sql += "ORDER BY id DESC LIMIT 200"

    res = await db.execute(text(sql), {"cid": career_id})
    msgs = [
        {
            "id": r[0],
            "date": r[1],
            "category": r[2] or "news",
            "subject": r[3] or "",
            "body": r[4] or "",
            "is_read": bool(r[5]),
            "is_pinned": bool(r[6]),
            "payload": r[7],
        }
        for r in res.fetchall()
    ]

    cnt = await db.execute(
        text("SELECT COUNT(*) FROM inbox_messages WHERE career_id = :cid AND is_read = 0"),
        {"cid": career_id},
    )
    unread_count = int(cnt.scalar() or 0)

    return {"messages": msgs, "unread_count": unread_count, "total": len(msgs)}


@router.post("/read-all")
async def mark_all_read(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row:
        raise HTTPException(404, "Career not found")
    if row[0] != user.id:
        raise HTTPException(403, "Not your career")
    await db.execute(
        text("UPDATE inbox_messages SET is_read = 1 WHERE career_id = :cid"),
        {"cid": career_id},
    )
    await db.commit()
    return {"success": True}


@router.post("/{message_id}/read")
async def mark_read(
    career_id: int,
    message_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row or row[0] != user.id:
        raise HTTPException(404, "Career not found")
    await db.execute(
        text(
            "UPDATE inbox_messages SET is_read = 1 "
            "WHERE id = :mid AND career_id = :cid"
        ),
        {"mid": message_id, "cid": career_id},
    )
    await db.commit()
    return {"success": True}


@router.delete("/{message_id}")
async def delete_message(
    career_id: int,
    message_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"), {"cid": career_id}
    )
    row = car.fetchone()
    if not row or row[0] != user.id:
        raise HTTPException(404, "Career not found")
    await db.execute(
        text("DELETE FROM inbox_messages WHERE id = :mid AND career_id = :cid"),
        {"mid": message_id, "cid": career_id},
    )
    await db.commit()
    return {"success": True}


# ─── Action handler — apply the consequence of an inbox-button click ───


class ActionRequest(BaseModel):
    action_id: str = Field(...)
    params: Optional[Dict[str, Any]] = None


@router.post("/{message_id}/action")
async def apply_action(
    career_id: int,
    message_id: int,
    body: ActionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply an inbox-button action. Reads the original message's
    payload to know which player it relates to."""
    car = await db.execute(
        text("SELECT user_id FROM careers WHERE id = :cid"),
        {"cid": career_id},
    )
    row = car.fetchone()
    if not row or row[0] != user.id:
        raise HTTPException(404, "Career not found")

    msg = await db.execute(text(
        "SELECT category, subject, payload, created_date "
        "FROM inbox_messages WHERE id=:m AND career_id=:c"
    ), {"m": message_id, "c": career_id})
    mr = msg.fetchone()
    if not mr:
        raise HTTPException(404, "Message not found")

    import json as _json
    try:
        payload = _json.loads(mr[2]) if mr[2] else {}
    except Exception:
        payload = {}

    pid = payload.get("linked_player_id")
    today = mr[3] or "2025-07-01"
    aid = body.action_id
    params = body.params or {}
    response_subject = ""
    response_body = ""

    if aid == "accept_contract" and pid:
        new_wage = int(params.get("new_wage") or 0)
        new_years = int(params.get("new_years") or 4)
        await db.execute(text(
            "UPDATE squad_players SET wage=:w, contract_years=:y, "
            "morale = MIN(100, COALESCE(morale,70) + 15) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"w": new_wage or 60_000, "y": new_years, "c": career_id, "p": pid})
        response_subject = "✓ Контракт продлён"
        response_body = f"Игрок подписал новый контракт ({new_years} лет, £{new_wage:,}/нед)."
    elif aid == "wait" and pid:
        await db.execute(text(
            "UPDATE squad_players SET morale = MAX(0, COALESCE(morale,70) - 5) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Игрок неохотно согласился подождать"
        response_body = "Мораль слегка упала. Решите вопрос до конца сезона."
    elif aid == "reject" and pid:
        await db.execute(text(
            "UPDATE squad_players SET morale = MAX(0, COALESCE(morale,70) - 15) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Игрок крайне разочарован"
        response_body = "Мораль резко упала. Возможен запрос на трансфер."
    elif aid == "promise_playing_time" and pid:
        # create promise with 8-week deadline
        deadline = _add_days_iso(today, 56)
        await db.execute(text(
            "INSERT INTO player_promises "
            "(career_id, player_id, promise_type, details_json, "
            "start_date, deadline_date, status) "
            "VALUES (:c, :p, 'playing_time', :d, :s, :dl, 'active')"
        ), {"c": career_id, "p": pid,
            "d": _json.dumps({"min_minutes_per_5": 200}),
            "s": today, "dl": deadline})
        await db.execute(text(
            "UPDATE squad_players SET morale = MIN(100, COALESCE(morale,70) + 8) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Обещание добавлено: больше игрового времени"
        response_body = f"Игрок ждёт >200 мин в следующих 5 матчах. Дедлайн {deadline}."
    elif aid == "wait_chance" and pid:
        await db.execute(text(
            "UPDATE squad_players SET morale = MAX(0, COALESCE(morale,70) - 4) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Игрок согласился ждать"
        response_body = "Лёгкое падение морали."
    elif aid == "list_transfer" and pid:
        await db.execute(text(
            "UPDATE squad_players SET is_transfer_listed=1 "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Игрок выставлен на трансфер"
        response_body = "ИИ-клубы могут начать делать предложения."
    elif aid == "promise_stay" and pid:
        deadline = _add_days_iso(today, 90)
        await db.execute(text(
            "INSERT INTO player_promises "
            "(career_id, player_id, promise_type, details_json, "
            "start_date, deadline_date, status) "
            "VALUES (:c, :p, 'sell_at_end', :d, :s, :dl, 'active')"
        ), {"c": career_id, "p": pid,
            "d": _json.dumps({"description": "продать в следующее окно"}),
            "s": today, "dl": deadline})
        await db.execute(text(
            "UPDATE squad_players SET morale = MIN(100, COALESCE(morale,70) + 10) "
            "WHERE career_id=:c AND player_id=:p"
        ), {"c": career_id, "p": pid})
        response_subject = "Игрок согласился остаться"
        response_body = "Обещание создано: продать в следующее трансферное окно."
    elif aid == "accept_incoming_offer":
        # Sell the player to the AI bidder.
        sp_id = params.get("sp_id")
        fee = int(params.get("fee") or 0)
        to_club = params.get("to_club")
        player_id = params.get("player_id")
        player_name = params.get("player_name") or "Игрок"
        offer_id = params.get("offer_id")
        if sp_id and player_id:
            # Update career budget + remove squad row + update player.club
            await db.execute(text(
                "UPDATE careers SET budget = budget + :f WHERE id = :c"
            ), {"f": fee, "c": career_id})
            await db.execute(text(
                "DELETE FROM squad_players WHERE id = :s AND career_id = :c"
            ), {"s": sp_id, "c": career_id})
            if to_club:
                await db.execute(text(
                    "UPDATE players SET club = :nc WHERE id = :p"
                ), {"nc": to_club, "p": player_id})
            await db.execute(text(
                "INSERT INTO ai_transfers "
                "(career_id, player_id, player_name, from_club, to_club, fee, "
                "is_loan, transfer_date) "
                "VALUES (:c, :p, :pn, 'Your club', :tc, :f, 0, :d)"
            ), {"c": career_id, "p": player_id, "pn": player_name,
                "tc": to_club or "Buyer", "f": fee, "d": today})
            if offer_id:
                await db.execute(text(
                    "UPDATE transfer_offers SET status='accepted', resolved_date=:d "
                    "WHERE id=:i"
                ), {"i": offer_id, "d": today})
        response_subject = f"{player_name} продан"
        response_body = f"Получено: {format_money(fee, 'GBP')}. Игрок ушёл в {to_club or 'клуб-покупатель'}."
    elif aid == "accept_incoming_loan":
        # Loan the player out for the season. Squad row stays (so the
        # player comes back next summer) but is_loaned flips to 1.
        sp_id = params.get("sp_id")
        to_club = params.get("to_club")
        player_id = params.get("player_id")
        player_name = params.get("player_name") or "Игрок"
        offer_id = params.get("offer_id")
        if sp_id and player_id:
            await db.execute(text(
                "UPDATE squad_players SET is_loaned = 1 "
                "WHERE id = :s AND career_id = :c"
            ), {"s": sp_id, "c": career_id})
            if to_club:
                await db.execute(text(
                    "UPDATE players SET club = :nc WHERE id = :p"
                ), {"nc": to_club, "p": player_id})
            await db.execute(text(
                "INSERT INTO ai_transfers "
                "(career_id, player_id, player_name, from_club, to_club, fee, "
                "is_loan, transfer_date) "
                "VALUES (:c, :p, :pn, 'Your club', :tc, 0, 1, :d)"
            ), {"c": career_id, "p": player_id, "pn": player_name,
                "tc": to_club or "Buyer", "d": today})
            if offer_id:
                await db.execute(text(
                    "UPDATE transfer_offers SET status='accepted', resolved_date=:d "
                    "WHERE id=:i"
                ), {"i": offer_id, "d": today})
        response_subject = f"{player_name} ушёл в аренду"
        response_body = f"Игрок арендован клубом {to_club or 'клуб-арендатор'} до конца сезона."
    elif aid == "reject_incoming_offer":
        offer_id = params.get("offer_id")
        if offer_id:
            await db.execute(text(
                "UPDATE transfer_offers SET status='rejected', resolved_date=:d "
                "WHERE id=:i"
            ), {"i": offer_id, "d": today})
        response_subject = "Предложение отклонено"
        response_body = ""
    elif aid == "counter_incoming_offer":
        # Player asks for a higher fee. We compute a counter price
        # (15-30% above the offered fee, capped to ~150% of CSV value)
        # and push it back to the AI buyer. The AI will respond after
        # 2-3 in-game days with: accept / reject / final-offer.
        from random import uniform
        try:
            from app.utils.money import format_money as _fm
        except Exception:
            _fm = lambda v, c="EUR": f"{v}"
        offer_id = params.get("offer_id")
        sp_id = params.get("sp_id")
        fee = int(params.get("fee") or 0)
        to_club = params.get("to_club") or "Buyer"
        player_id = params.get("player_id")
        player_name = params.get("player_name") or "Игрок"
        # If the user provided a custom price, use that. Otherwise ask
        # for 20-40% above the AI's offer (legacy behaviour).
        custom_fee = params.get("custom_fee")
        if custom_fee is not None:
            try:
                new_ask = max(1, int(custom_fee))
            except Exception:
                new_ask = int(fee * uniform(1.20, 1.40))
        else:
            new_ask = int(fee * uniform(1.20, 1.40))
        if offer_id:
            await db.execute(text(
                "UPDATE transfer_offers "
                "SET status='counter_sent', resolved_date=:d, "
                "    fee = :nf "
                "WHERE id=:i"
            ), {"i": offer_id, "d": today, "nf": new_ask})
        response_subject = (
            f"Контр-предложение отправлено: {player_name} за {_fm(new_ask)}"
        )
        response_body = (
            f"Мы запросили {_fm(new_ask)} вместо {_fm(fee)}. "
            f"{to_club} обдумывает ответ."
        )
        # Schedule the AI response — write a delayed offer that the
        # advance-day loop picks up when its created_date matches today.
        # Simplification: AI accepts 50% / final-offer 35% / reject 15%,
        # rolled now and posted to the inbox immediately under today's
        # date so the user sees it right away (waiting 2-3 in-game days
        # was confusing — users thought the AI ignored them).
        decision_roll = uniform(0, 1)
        land_date = today
        if decision_roll < 0.50:
            # Accept the counter — buyer pays the new ask. Push a new
            # transfer_in row so the user can confirm sale.
            await db.execute(text(
                "INSERT INTO transfer_offers "
                "(career_id, direction, player_id, from_club_name, "
                " to_club_name, fee, status, created_date) "
                "VALUES (:c, 'incoming', :p, :fc, :tc, :f, 'pending', :d)"
            ), {"c": career_id, "p": player_id,
                "fc": "Your club", "tc": to_club,
                "f": new_ask, "d": land_date})
            new_offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
            new_offer_id = int(new_offer_id_row.scalar() or 0)
            payload2 = json.dumps({
                "actions": [
                    {"id": "accept_incoming_offer",
                     "label": f"Принять ({_fm(new_ask)})",
                     "params": {"offer_id": new_offer_id, "sp_id": sp_id,
                                "fee": new_ask, "to_club": to_club,
                                "player_id": player_id,
                                "player_name": player_name}},
                    {"id": "reject_incoming_offer",
                     "label": "Отклонить",
                     "params": {"offer_id": new_offer_id}},
                ],
                "linked_player_id": player_id,
                "bid_tag": "counter_accepted",
            }, ensure_ascii=False)
            await push_inbox_message(
                db, career_id, category="transfer_in",
                subject=(f"{to_club} согласился на {_fm(new_ask)} за {player_name}"),
                body="Они приняли встречку. Подтвердите продажу.",
                on_date=land_date, payload=payload2,
            )
        elif decision_roll < 0.85:
            # Final offer — pay 90% of the counter, take it or leave it.
            final = int(new_ask * 0.90)
            await db.execute(text(
                "INSERT INTO transfer_offers "
                "(career_id, direction, player_id, from_club_name, "
                " to_club_name, fee, status, created_date) "
                "VALUES (:c, 'incoming', :p, :fc, :tc, :f, 'pending', :d)"
            ), {"c": career_id, "p": player_id,
                "fc": "Your club", "tc": to_club,
                "f": final, "d": land_date})
            new_offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
            new_offer_id = int(new_offer_id_row.scalar() or 0)
            payload2 = json.dumps({
                "actions": [
                    {"id": "accept_incoming_offer",
                     "label": f"Принять ({_fm(final)})",
                     "params": {"offer_id": new_offer_id, "sp_id": sp_id,
                                "fee": final, "to_club": to_club,
                                "player_id": player_id,
                                "player_name": player_name}},
                    {"id": "reject_incoming_offer",
                     "label": "Отклонить",
                     "params": {"offer_id": new_offer_id}},
                ],
                "linked_player_id": player_id,
                "bid_tag": "final_offer",
            }, ensure_ascii=False)
            await push_inbox_message(
                db, career_id, category="transfer_in",
                subject=(f"Финальное предложение от {to_club}: {_fm(final)} за {player_name}"),
                body="Это их последнее слово. Дальше — отказ.",
                on_date=land_date, payload=payload2,
            )
        else:
            # Reject — buyer walks away.
            await push_inbox_message(
                db, career_id, category="response",
                subject=f"{to_club} вышел из переговоров за {player_name}",
                body="Они посчитали ваш запрос завышенным.",
                on_date=land_date,
            )
    else:
        response_subject = "Действие применено"
        response_body = ""

    # Mark original message read
    await db.execute(text(
        "UPDATE inbox_messages SET is_read=1 WHERE id=:m"
    ), {"m": message_id})
    await db.commit()

    # Push a follow-up message
    if response_subject:
        await push_inbox_message(
            db, career_id,
            category="response",
            subject=response_subject,
            body=response_body,
            on_date=today,
        )
    return {"success": True}


def _add_days_iso(d: str, days: int) -> str:
    from datetime import date, timedelta
    y, m, dd = (int(p) for p in d.split("-"))
    return str(date(y, m, dd) + timedelta(days=days))


# ─── Internal helper used by other routes ──────────────────────────────────


async def push_inbox_message(
    db: AsyncSession,
    career_id: int,
    *,
    category: str,
    subject: str,
    body: str = "",
    on_date: Optional[str] = None,
    payload: Optional[str] = None,
    is_pinned: bool = False,
) -> int:
    """Insert a single inbox row. Returns the new message id.

    Wraps INSERT in its own try/except so a failure here never propagates
    up to the action that triggered it (match simulation, advance-day,
    etc. — the inbox is best-effort).
    """
    try:
        await db.execute(
            text(
                "INSERT INTO inbox_messages "
                "(career_id, created_date, category, subject, body, is_read, "
                " is_pinned, payload) "
                "VALUES (:cid, :d, :cat, :s, :b, 0, :pin, :pl)"
            ),
            {
                "cid": career_id,
                "d": on_date or "",
                "cat": category,
                "s": subject[:255],
                "b": body[:2000],
                "pin": 1 if is_pinned else 0,
                "pl": payload,
            },
        )
        await db.commit()
        r = await db.execute(text("SELECT last_insert_rowid()"))
        return int(r.scalar() or 0)
    except Exception:
        return 0
