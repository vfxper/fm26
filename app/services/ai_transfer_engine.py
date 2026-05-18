"""
AI-vs-AI transfer engine. Runs every in-game day during a transfer window.

Algorithm (high level):
1. Determine if the date is within a transfer window (summer 01-07..31-08
   or winter 01-01..31-01). If not вЂ” skip.
2. Pick a random subset of N AI clubs that haven't yet hit their window
   quota of 10 transfers.
3. For each picked AI club:
   - Look at the squad it has (best-effort: top-N players in CSV by
     `club` column) plus their CA.
   - Decide if it wants to BUY a player or SELL/LOAN.
   - For BUY: scan candidate AI clubs, pick a player slightly better
     than the buyer's current weakest at that position, fee scaled by
     CA, weighted by club reputation.
   - Execute the move: bump quota, write to ai_transfers + push inbox
     news, update player.club to the new club.
4. Loans use the same flow but is_loan=True and the player snapshot
   carries `loan_until` until window closes.

The player's own club is never touched here.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.club_budgets import CLUBS
from app.utils.money import format_money


def _ascii_safe(s: str) -> str:
    """Strip non-Latin letters from a name to avoid mojibake when the
    string passes through the SQLite + aiosqlite pipe. Replaces accented
    Latin letters with ASCII equivalents (e.g. ş→s, ş→s, ć→c). If the
    result is empty (full Cyrillic / Arabic), falls back to the original
    string — caller can decide what to do with it."""
    if not s:
        return s
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", s)
    cleaned = "".join(c for c in nfkd if not unicodedata.combining(c) and ord(c) < 128)
    cleaned = cleaned.strip()
    return cleaned if cleaned else s


def _is_window_open(on_date: str) -> Optional[str]:
    try:
        y, m, d = (int(p) for p in on_date.split("-"))
    except Exception:
        return None
    # summer: 07-01..08-31, winter: 01-01..01-31
    if m in (7, 8):
        return "summer"
    if m == 1:
        return "winter"
    return None


def _ca_to_fee(ca: int) -> int:
    """Translate CA into a rough transfer fee in ВЈ. Logarithmic curve so
    mid-tier players sit at ВЈ2-15M, world-class at ВЈ80-150M.

    Used as a FALLBACK when the player's CSV price is unparseable.
    Prefer ``_real_market_value(db, player_id)`` whenever you have a
    DB session — it returns the actual CSV-derived price for THIS
    player, which is what the user expects in the UI."""
    if ca <= 100:
        return random.randint(150_000, 2_000_000)
    if ca <= 130:
        return random.randint(2_000_000, 15_000_000)
    if ca <= 150:
        return random.randint(15_000_000, 50_000_000)
    if ca <= 170:
        return random.randint(50_000_000, 100_000_000)
    return random.randint(100_000_000, 250_000_000)


async def _real_market_value(db: AsyncSession, player_id: int,
                              fallback_ca: int = 100) -> int:
    """Return the player's CSV-derived market value in £ as an int.
    Falls back to ``_ca_to_fee(fallback_ca)`` when the row is missing
    or its price string can't be parsed."""
    try:
        from app.api.routes.negotiations import _parse_price
        r = await db.execute(text(
            "SELECT price FROM players WHERE id = :p"
        ), {"p": player_id})
        row = r.fetchone()
        if row and row[0]:
            v = _parse_price(row[0])
            if v > 0:
                return v
    except Exception:
        pass
    return _ca_to_fee(fallback_ca)


def _club_reputation(club_name: str) -> int:
    """Rough club reputation based on its CLUBS budget index. Top of list
    = strongest. Index normalized to 1..100."""
    for idx, (name, _, _, _) in enumerate(CLUBS):
        if name.lower() == (club_name or "").lower():
            # Position 1 -> 100; position 200 -> ~5
            return max(5, int(100 - (idx / max(1, len(CLUBS))) * 95))
    return 30


async def _quota_used(db: AsyncSession, career_id: int, club_name: str,
                      window_year: int, window_kind: str) -> int:
    r = await db.execute(text(
        "SELECT count FROM ai_window_quota "
        "WHERE career_id=:c AND club_name=:n "
        "AND window_year=:y AND window_kind=:k"
    ), {"c": career_id, "n": club_name, "y": window_year, "k": window_kind})
    v = r.scalar()
    return int(v or 0)


async def _bump_quota(db: AsyncSession, career_id: int, club_name: str,
                      window_year: int, window_kind: str) -> None:
    if await _quota_used(db, career_id, club_name, window_year, window_kind) == 0:
        await db.execute(text(
            "INSERT INTO ai_window_quota "
            "(career_id, club_name, window_year, window_kind, count) "
            "VALUES (:c, :n, :y, :k, 1)"
        ), {"c": career_id, "n": club_name, "y": window_year, "k": window_kind})
    else:
        await db.execute(text(
            "UPDATE ai_window_quota SET count = count + 1 "
            "WHERE career_id=:c AND club_name=:n "
            "AND window_year=:y AND window_kind=:k"
        ), {"c": career_id, "n": club_name, "y": window_year, "k": window_kind})


async def run_daily_ai_transfers(
    db: AsyncSession,
    *,
    career_id: int,
    on_date: str,
    player_club_name: Optional[str] = None,
) -> List[str]:
    """Execute AI-vs-AI transfers for one day. Returns the list of news
    headlines emitted (also pushed to inbox)."""
    window = _is_window_open(on_date)
    headlines: List[str] = []
    window_year = int(on_date.split("-")[0])

    # в”Ђв”Ђв”Ђ AI-vs-AI deals (only inside transfer window) в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
    if window is not None:
        # Only 1-3 deals per day (was 1-6 — too noisy).
        deals_today = max(1, random.randint(1, 3))
        candidate_clubs = [c[0] for c in CLUBS if c[0] != player_club_name]
        random.shuffle(candidate_clubs)

        # Track which deals are big enough to actually surface in the
        # inbox. Anything below MAJOR_TRANSFER_THRESHOLD is logged into
        # ai_transfers (so the world stays consistent) but doesn't
        # spam the user. Loans never surface either.
        MAJOR_TRANSFER_THRESHOLD = 30_000_000
        major_headlines: List[str] = []

        attempts = 0
        while len(headlines) < deals_today and attempts < 60:
            attempts += 1
            if not candidate_clubs:
                break
            buyer = random.choice(candidate_clubs)
            if await _quota_used(db, career_id, buyer, window_year, window) >= 10:
                continue

            seller_pool = [c for c in candidate_clubs if c != buyer]
            if not seller_pool:
                break
            seller = random.choice(seller_pool)
            if await _quota_used(db, career_id, seller, window_year, window) >= 10:
                continue

            buyer_rep = _club_reputation(buyer)
            seller_rep = _club_reputation(seller)
            if seller_rep > buyer_rep + 25 and random.random() > 0.15:
                continue

            ca_target_min = max(95, buyer_rep - 15)
            ca_target_max = min(180, buyer_rep + 35)

            candidates = await db.execute(text(
                "SELECT id, name, position, ca, age FROM players "
                "WHERE club = :club AND ca BETWEEN :mn AND :mx "
                "ORDER BY RANDOM() LIMIT 5"
            ), {"club": seller, "mn": ca_target_min, "mx": ca_target_max})
            rows = candidates.fetchall()
            if not rows:
                continue
            player_id, player_name, pos, ca, age = rows[0]

            own = await db.execute(text(
                "SELECT 1 FROM squad_players WHERE career_id=:c AND player_id=:p LIMIT 1"
            ), {"c": career_id, "p": player_id})
            if own.fetchone():
                continue

            is_loan = age < 24 and random.random() < 0.30
            fee = 0 if is_loan else await _real_market_value(db, player_id, fallback_ca=ca)

            await db.execute(text(
                "UPDATE players SET club = :nb WHERE id = :p"
            ), {"nb": buyer, "p": player_id})
            await db.execute(text(
                "INSERT INTO ai_transfers "
                "(career_id, player_id, player_name, from_club, to_club, fee, "
                "is_loan, transfer_date) "
                "VALUES (:c, :p, :pn, :fc, :tc, :f, :l, :d)"
            ), {
                "c": career_id, "p": player_id, "pn": _ascii_safe(player_name),
                "fc": _ascii_safe(seller), "tc": _ascii_safe(buyer), "f": fee,
                "l": 1 if is_loan else 0, "d": on_date,
            })
            await _bump_quota(db, career_id, buyer, window_year, window)
            if not is_loan:
                await _bump_quota(db, career_id, seller, window_year, window)
            kind = "loan" if is_loan else format_money(fee)
            headline = f"{_ascii_safe(player_name)}: {_ascii_safe(seller)} -> {_ascii_safe(buyer)} ({kind})"
            headlines.append(headline)

            # Only the big-money or top-club deals get pushed to the
            # user's inbox. Everyone else just lands silently in the
            # ai_transfers ledger so the world keeps churning.
            if not is_loan and fee >= MAJOR_TRANSFER_THRESHOLD:
                major_headlines.append(headline)

        await db.commit()

        # Push only the major-transfer headlines.
        if major_headlines:
            try:
                from app.api.routes.inbox import push_inbox_message
                for h in major_headlines:
                    await push_inbox_message(
                        db, career_id,
                        category="news_transfer",
                        subject=h,
                        body="",
                        on_date=on_date,
                    )
            except Exception:
                pass

    # AI bids on the human player's listed players (only during a window).
    if window is None:
        return headlines
    try:
        from app.data.club_budgets import get_wage_budget
        listed = await db.execute(text(
            "SELECT sp.id, sp.player_id, p.name, p.ca, p.age, sp.wage "
            "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
            "WHERE sp.career_id = :c AND sp.is_transfer_listed = 1"
        ), {"c": career_id})
        listed_rows = listed.fetchall()
        for r in listed_rows:
            sp_id, pid, pname, ca, age, wage = r
            base_prob = 0.15 if (ca or 0) <= 130 else 0.30 if (ca or 0) <= 150 else 0.50
            if random.random() > base_prob:
                continue
            buyer_pool = [c[0] for c in CLUBS if c[0] != player_club_name]
            random.shuffle(buyer_pool)
            buyer = None
            ca_norm = min(100, max(0, (ca or 100) // 2 + 10))
            for candidate in buyer_pool[:50]:
                rep = _club_reputation(candidate)
                # Compare on the rep (1..100) scale — same as the
                # ca_norm we just built. Without normalisation we'd
                # need rep ≥ ~150 for a CA-150 player which doesn't
                # exist (rep max is 100), so the listed bids would
                # silently never fire.
                if rep < ca_norm - 25 or rep > ca_norm + 25:
                    continue
                if get_wage_budget(candidate) < (wage or 0):
                    continue
                if await _quota_used(db, career_id, candidate, window_year, window) >= 10:
                    continue
                buyer = candidate
                break
            if not buyer:
                continue
            ask = await db.execute(text(
                "SELECT fee FROM transfer_offers "
                "WHERE career_id=:c AND player_id=:p AND direction='listing' "
                "ORDER BY id DESC LIMIT 1"
            ), {"c": career_id, "p": pid})
            ask_row = ask.fetchone()
            asking_price = int(ask_row[0]) if ask_row else await _real_market_value(db, pid, fallback_ca=ca or 100)
            buyer_rep = _club_reputation(buyer)
            offer_ratio = 0.55 + (buyer_rep / 100) * 0.30
            offered_fee = int(asking_price * offer_ratio * random.uniform(0.95, 1.05))
            # Never overpay — buyer caps at the asking price.
            offered_fee = min(offered_fee, asking_price)

            await db.execute(text(
                "INSERT INTO transfer_offers "
                "(career_id, direction, player_id, from_club_name, to_club_name, "
                "fee, status, created_date) "
                "VALUES (:c, 'incoming', :p, :fc, :tc, :f, 'pending', :d)"
            ), {"c": career_id, "p": pid,
                "fc": player_club_name or "Your club",
                "tc": buyer, "f": offered_fee, "d": on_date})
            offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
            offer_id = int(offer_id_row.scalar() or 0)

            try:
                from app.api.routes.inbox import push_inbox_message
                payload = json.dumps({
                    "actions": [
                        {"id": "accept_incoming_offer",
                         "label": f"Accept ({format_money(offered_fee)})",
                         "params": {"offer_id": offer_id, "sp_id": sp_id,
                                    "fee": offered_fee, "to_club": buyer,
                                    "player_id": pid, "player_name": pname}},
                        {"id": "counter_incoming_offer",
                         "label": "Запросить больше",
                         "params": {"offer_id": offer_id, "sp_id": sp_id,
                                    "fee": offered_fee, "to_club": buyer,
                                    "player_id": pid, "player_name": pname}},
                        {"id": "reject_incoming_offer",
                         "label": "Reject",
                         "params": {"offer_id": offer_id}},
                    ],
                    "linked_player_id": pid,
                }, ensure_ascii=False)
                await push_inbox_message(
                    db, career_id,
                    category="transfer_in",
                    subject=f"{_ascii_safe(buyer)} предлагает {format_money(offered_fee)} за {_ascii_safe(pname)}",
                    body=f"Запрашиваемая цена: {format_money(asking_price)}.",
                    on_date=on_date,
                    payload=payload,
                )
                headlines.append(f"Предложение за {_ascii_safe(pname)}: {format_money(offered_fee)} от {_ascii_safe(buyer)}")
            except Exception:
                pass
        if listed_rows:
            await db.commit()
    except Exception as e:
        print(f"Listed-player bids warning: {e}")

    # ─── Unsolicited bids on NON-listed players ──────────────────────────
    # The user did not put these players up for sale, but other clubs
    # may still come knocking. The bid amount is often a low-ball
    # (50-75% of the player's CSV value) to test whether the manager
    # would sell on the cheap. The user can still reject; if they want
    # a counter-offer, they list the player and the standard listed
    # path takes over.
    try:
        from app.data.club_budgets import get_wage_budget as _get_wage_budget
        unlisted = await db.execute(text(
            "SELECT sp.id, sp.player_id, p.name, p.ca, p.age, sp.wage, p.position "
            "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
            "WHERE sp.career_id = :c "
            "  AND COALESCE(sp.is_transfer_listed, 0) = 0 "
            "  AND COALESCE(sp.is_loaned, 0) = 0"
        ), {"c": career_id})
        rows = unlisted.fetchall()
        # We DON'T want a flood — at most 1 unsolicited bid per day
        # (was 2). Higher CA players still attract more interest via
        # the per-player probability below.
        candidates = sorted(rows, key=lambda r: -(r[3] or 0))
        bids_today = 0
        for r in candidates:
            if bids_today >= 1:
                break
            sp_id, pid, pname, ca, age, wage, pos = r
            ca = ca or 0
            # Only good players draw unsolicited interest. Backups get
            # left alone unless they're young (under 23 = potential).
            if ca < 130 and (age or 30) >= 23:
                continue
            # Per-player chance per day. Tuned WAY down — beta-testers
            # complained "Too many transfer offers". Halved from the
            # previous 0.005/0.012/0.020 tier.
            base_prob = 0.0015 if ca < 145 else 0.004 if ca < 165 else 0.008
            if random.random() > base_prob:
                continue
            buyer_pool = [c[0] for c in CLUBS if c[0] != player_club_name]
            random.shuffle(buyer_pool)
            buyer = None
            # Map player CA (1..200) to a comparable reputation band
            # (1..100). _club_reputation() returns 1..100 too, so we
            # compare on the same scale. A small ± window keeps things
            # plausible: a CA-180 superstar attracts buyers with rep
            # 60+, not Tondela.
            ca_norm = min(100, max(0, ca // 2 + 10))  # CA 180 -> 100, CA 130 -> 75
            for candidate in buyer_pool[:60]:
                rep = _club_reputation(candidate)
                # Buyer rep must be within ±25 of the CA-normalised band.
                if rep < ca_norm - 25 or rep > ca_norm + 25:
                    continue
                if _get_wage_budget(candidate) < (wage or 0):
                    continue
                if await _quota_used(db, career_id, candidate, window_year, window) >= 10:
                    continue
                buyer = candidate
                break
            if not buyer:
                continue

            # Bid amount. CSV-derived "fair" value, then a low-ball
            # multiplier 50%..115%. About 30% of bids are absurd low
            # offers (below 65%) — those should be rejected by the
            # manager as a signal to push for more.
            fair = await _real_market_value(db, pid, fallback_ca=ca)
            roll = random.random()
            if roll < 0.30:
                multiplier = random.uniform(0.50, 0.65)  # low-ball
            elif roll < 0.85:
                multiplier = random.uniform(0.70, 0.95)  # decent
            else:
                multiplier = random.uniform(1.00, 1.15)  # over-pay
            offered_fee = max(100_000, int(fair * multiplier))
            bids_today += 1

            await db.execute(text(
                "INSERT INTO transfer_offers "
                "(career_id, direction, player_id, from_club_name, to_club_name, "
                "fee, status, created_date) "
                "VALUES (:c, 'incoming', :p, :fc, :tc, :f, 'pending', :d)"
            ), {"c": career_id, "p": pid,
                "fc": player_club_name or "Your club",
                "tc": buyer, "f": offered_fee, "d": on_date})
            offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
            offer_id = int(offer_id_row.scalar() or 0)

            try:
                from app.api.routes.inbox import push_inbox_message
                # Tag the offer for the UI: "lowball", "fair", "premium".
                tag = "lowball" if multiplier < 0.66 else "fair" if multiplier < 1.0 else "premium"
                payload = json.dumps({
                    "actions": [
                        {"id": "accept_incoming_offer",
                         "label": f"Принять ({format_money(offered_fee)})",
                         "params": {"offer_id": offer_id, "sp_id": sp_id,
                                    "fee": offered_fee, "to_club": buyer,
                                    "player_id": pid, "player_name": pname}},
                        {"id": "counter_incoming_offer",
                         "label": "Запросить больше",
                         "params": {"offer_id": offer_id, "sp_id": sp_id,
                                    "fee": offered_fee, "to_club": buyer,
                                    "player_id": pid, "player_name": pname}},
                        {"id": "reject_incoming_offer",
                         "label": "Отклонить",
                         "params": {"offer_id": offer_id}},
                    ],
                    "linked_player_id": pid,
                    "bid_tag": tag,
                    "fair_value": fair,
                }, ensure_ascii=False)
                # Subject differs by tag so the user can spot insulting
                # bids at a glance from the inbox list. No emoji — keep
                # the inbox clean and FM-style.
                subj_prefix = {
                    "lowball": "Заниженное предложение",
                    "fair":    "Предложение",
                    "premium": "Щедрое предложение",
                }[tag]
                await push_inbox_message(
                    db, career_id,
                    category="transfer_in",
                    subject=(
                        f"{subj_prefix}: {_ascii_safe(buyer)} "
                        f"предлагает {format_money(offered_fee)} за "
                        f"{_ascii_safe(pname)}"
                    ),
                    body=(
                        f"Игрок не выставлен на трансфер. "
                        f"Реальная стоимость: {format_money(fair)}. "
                        f"Принять, отклонить или выставить на трансфер "
                        f"для торга."
                    ),
                    on_date=on_date,
                    payload=payload,
                )
                headlines.append(
                    f"{subj_prefix}: {_ascii_safe(pname)} — "
                    f"{format_money(offered_fee)} от {_ascii_safe(buyer)}"
                )
            except Exception:
                pass
        if rows:
            await db.commit()
    except Exception as e:
        print(f"Unsolicited bids warning: {e}")

    # ─── Loan bids on young, non-starting players ────────────────────────
    # Other clubs ask to LOAN a young player who isn't getting minutes.
    # Conditions: age < 24, status in (prospect, backup, rotation),
    # not transfer-listed, not already loaned. Lower-rep clubs send
    # these requests so the youngster can get game time.
    try:
        young_rows = await db.execute(text(
            "SELECT sp.id, sp.player_id, p.name, p.ca, p.age, sp.status "
            "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
            "WHERE sp.career_id = :c "
            "  AND COALESCE(p.age, 30) < 24 "
            "  AND COALESCE(sp.is_transfer_listed, 0) = 0 "
            "  AND COALESCE(sp.is_loaned, 0) = 0 "
            "  AND COALESCE(sp.is_loan_listed, 0) = 0 "
            "  AND COALESCE(sp.status, 'starter') IN ('prospect', 'backup', 'rotation')"
        ), {"c": career_id})
        young_rows = young_rows.fetchall()
        loan_bids_today = 0
        random.shuffle(young_rows)
        for r in young_rows:
            if loan_bids_today >= 2:
                break
            sp_id, pid, pname, ca, age, sstatus = r
            ca = ca or 100
            if random.random() > 0.008:
                continue
            buyer_pool = [c[0] for c in CLUBS if c[0] != player_club_name]
            random.shuffle(buyer_pool)
            buyer = None
            ca_norm = min(100, max(0, ca // 2 + 10))
            for candidate in buyer_pool[:60]:
                rep = _club_reputation(candidate)
                # Loan suitor must be SMALLER than the source.
                if rep < ca_norm - 35 or rep > ca_norm:
                    continue
                buyer = candidate
                break
            if not buyer:
                continue

            await db.execute(text(
                "INSERT INTO transfer_offers "
                "(career_id, direction, player_id, from_club_name, to_club_name, "
                "fee, status, created_date) "
                "VALUES (:c, 'incoming_loan', :p, :fc, :tc, 0, 'pending', :d)"
            ), {"c": career_id, "p": pid,
                "fc": player_club_name or "Your club",
                "tc": buyer, "d": on_date})
            offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
            offer_id = int(offer_id_row.scalar() or 0)

            try:
                from app.api.routes.inbox import push_inbox_message
                payload = json.dumps({
                    "actions": [
                        {"id": "accept_incoming_loan",
                         "label": "Согласиться на аренду",
                         "params": {"offer_id": offer_id, "sp_id": sp_id,
                                    "to_club": buyer, "player_id": pid,
                                    "player_name": pname}},
                        {"id": "reject_incoming_offer",
                         "label": "Отказать",
                         "params": {"offer_id": offer_id}},
                    ],
                    "linked_player_id": pid,
                    "is_loan_request": True,
                }, ensure_ascii=False)
                await push_inbox_message(
                    db, career_id,
                    category="loan_request",
                    subject=(
                        f"Запрос аренды: {_ascii_safe(buyer)} хочет арендовать "
                        f"{_ascii_safe(pname)} ({age} лет, CA {ca})"
                    ),
                    body=(
                        f"Молодому игроку нужны минуты. {_ascii_safe(buyer)} "
                        f"готов взять его в аренду на сезон. "
                        f"Решай: согласиться или оставить в команде."
                    ),
                    on_date=on_date,
                    payload=payload,
                )
                headlines.append(
                    f"Запрос аренды: {_ascii_safe(pname)} -> {_ascii_safe(buyer)}"
                )
                loan_bids_today += 1
            except Exception:
                pass
        if young_rows:
            await db.commit()
    except Exception as e:
        print(f"Loan bids warning: {e}")

    return headlines


async def generate_bid_for_listed_player(
    db: AsyncSession,
    *,
    career_id: int,
    squad_player_id: int,
    on_date: str,
    asking_price: int,
    n_bids: int = 3,
) -> List[int]:
    """Force AI bid(s) on a freshly-listed player so the user gets
    instant feedback in the inbox.

    Generates up to ``n_bids`` distinct offers from different clubs.
    Bids are generated REGARDLESS of the transfer window — when the
    user lists a star, the world hears about it immediately. The fee
    they offer scales with their reputation relative to the player's
    CA, so weak clubs lowball big stars and top clubs are more
    aggressive.

    Returns the list of created offer ids (may be empty).
    """
    window = _is_window_open(on_date)
    # We DO try to bid even outside the window — buying clubs can
    # "register interest" any time. The actual quota table is only
    # bumped in-window.
    window_year = int(on_date.split("-")[0])

    # Player + own club name
    pr = await db.execute(text(
        "SELECT sp.id, sp.player_id, p.name, p.ca, p.age, p.club, sp.wage "
        "FROM squad_players sp JOIN players p ON p.id = sp.player_id "
        "WHERE sp.id = :s AND sp.career_id = :c"
    ), {"s": squad_player_id, "c": career_id})
    row = pr.fetchone()
    if not row:
        return []
    sp_id, pid, pname, ca, age, player_club_name, wage = row
    ca = ca or 100
    wage = wage or 0

    from app.data.club_budgets import get_wage_budget

    # Build a ranked pool of plausible buyers. Reputation ±25 of the
    # player's CA, with budget for their wage. Sort by reputation
    # descending so the strongest matching buyers come first.
    candidates = []
    for cand_name, *_rest in CLUBS:
        if cand_name == player_club_name:
            continue
        rep = _club_reputation(cand_name)
        if rep < ca - 25 or rep > ca + 35:
            continue
        if get_wage_budget(cand_name) < wage:
            continue
        if window is not None and await _quota_used(
            db, career_id, cand_name, window_year, window
        ) >= 10:
            continue
        candidates.append((cand_name, rep))
    candidates.sort(key=lambda x: -x[1])

    # Always pick from the TOP-N (by rep) plus a random tail so the
    # user gets a mix of mega-clubs and mid-table.
    chosen = []
    if candidates:
        # Take the top half deterministically; sample the rest randomly.
        top_n = min(len(candidates), max(n_bids, 6))
        head = candidates[:top_n]
        random.shuffle(head)
        for cand, rep in head[:n_bids]:
            chosen.append((cand, rep))

    if not chosen:
        # Reputation-band fallback: anyone with rep at least half the
        # player's CA. Keeps low-table clubs out of bidding for stars.
        bucket = []
        for cand_name, *_rest in CLUBS:
            if cand_name == player_club_name:
                continue
            rep = _club_reputation(cand_name)
            if rep < ca // 2:
                continue
            bucket.append((cand_name, rep))
        random.shuffle(bucket)
        chosen = bucket[:n_bids]

    if not chosen:
        return []

    offer_ids: List[int] = []
    seen_buyers = set()
    for buyer, buyer_rep in chosen:
        if buyer in seen_buyers:
            continue
        seen_buyers.add(buyer)

        # Stronger clubs offer closer to asking price.
        offer_ratio = 0.78 + (buyer_rep / 100) * 0.30
        offered_fee = max(50_000, int(
            asking_price * offer_ratio * random.uniform(0.92, 1.08)
        ))

        await db.execute(text(
            "INSERT INTO transfer_offers "
            "(career_id, direction, player_id, from_club_name, to_club_name, "
            "fee, status, created_date) "
            "VALUES (:c, 'incoming', :p, :fc, :tc, :f, 'pending', :d)"
        ), {"c": career_id, "p": pid,
            "fc": player_club_name or "Your club",
            "tc": buyer, "f": offered_fee, "d": on_date})
        offer_id_row = await db.execute(text("SELECT last_insert_rowid()"))
        offer_id = int(offer_id_row.scalar() or 0)
        offer_ids.append(offer_id)

        try:
            from app.api.routes.inbox import push_inbox_message
            payload = json.dumps({
                "actions": [
                    {"id": "accept_incoming_offer",
                     "label": f"Принять (£{offered_fee:,})",
                     "params": {"offer_id": offer_id, "sp_id": sp_id,
                                "fee": offered_fee, "to_club": buyer,
                                "player_id": pid, "player_name": pname}},
                    {"id": "reject_incoming_offer",
                     "label": "Отказать",
                     "params": {"offer_id": offer_id}},
                ],
                "linked_player_id": pid,
            }, ensure_ascii=False)
            await push_inbox_message(
                db, career_id,
                category="transfer_in",
                subject=f"💰 {_ascii_safe(buyer)} предлагает £{offered_fee:,} за {_ascii_safe(pname)}",
                body=f"Запрашиваемая цена: £{asking_price:,}.",
                on_date=on_date,
                payload=payload,
            )
        except Exception:
            pass

    await db.commit()
    return offer_ids
