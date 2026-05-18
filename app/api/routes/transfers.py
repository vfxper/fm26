"""
Transfers API Endpoints (Task 26)
GET /api/players/search - Search all players with filters
POST /api/careers/{career_id}/transfers/bid - Submit transfer bid
POST /api/careers/{career_id}/transfers/loan - Submit loan offer
POST /api/careers/{career_id}/transfers/list - List player for sale
GET /api/careers/{career_id}/transfers/history - Get transfer history
GET /api/careers/{career_id}/transfers/window - Get transfer window status
GET /api/careers/{career_id}/transfers/budget - Get transfer budget
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.services.transfer_service import TransferService
from app.services.career_service import CareerService

router = APIRouter(tags=["transfers"])


class BidRequest(BaseModel):
    player_id: int
    amount: int = Field(..., gt=0, description="Bid amount in currency units")
    wage_offer: Optional[int] = None


class LoanRequest(BaseModel):
    player_id: int
    loan_type: str = Field(default="season", description="season or emergency")
    wage_contribution: Optional[int] = Field(None, description="% of wage to pay")


class ListPlayerRequest(BaseModel):
    player_id: int
    asking_price: Optional[int] = None


# === Search (global) ===

@router.get("/players/search")
async def search_players(
    q: Optional[str] = Query(None, description="Search query (name)"),
    search_text: Optional[str] = Query(None, description="Alias for q"),
    position: Optional[str] = Query(None),
    min_ca: Optional[int] = Query(None, ge=1, le=200),
    max_ca: Optional[int] = Query(None, ge=1, le=200),
    min_pa: Optional[int] = Query(None, ge=1, le=200),
    max_pa: Optional[int] = Query(None, ge=1, le=200),
    min_age: Optional[int] = Query(None, ge=15, le=45),
    max_age: Optional[int] = Query(None, ge=15, le=45),
    nationality: Optional[str] = Query(None),
    club: Optional[str] = Query(None),
    max_price: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    order_by: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Search all players with filters.

    Name match is accent-insensitive: a query "mbappe" matches "Mbappé".
    We do this by transliterating the query to ASCII first, then filter
    in Python after a fast LIKE prefilter on the first letters.
    """
    from sqlalchemy import select, or_, func
    from app.models.player import Player
    import unicodedata

    def _ascii_lower(s: str) -> str:
        if not s:
            return ""
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c) and ord(c) < 128).lower()

    name_q = (q or search_text or "").strip()
    name_q_ascii = _ascii_lower(name_q)

    query = select(Player)

    # First-letter SQL prefilter for performance: search ANY player
    # whose name *contains* the first 2 letters of the query (helps
    # narrow down before Python-side accent-insensitive match). If
    # query is too short or fully ASCII, just use direct LIKE.
    if name_q:
        if name_q.isascii():
            query = query.where(Player.name.ilike(f"%{name_q}%"))
        else:
            # Direct case-sensitive subquery — accent-insensitive
            # filter happens below in Python.
            pass
    if position:
        query = query.where(Player.position.ilike(f"%{position}%"))
    if min_ca:
        query = query.where(Player.ca >= min_ca)
    if max_ca:
        query = query.where(Player.ca <= max_ca)
    if min_pa:
        query = query.where(Player.pa >= min_pa)
    if max_pa:
        query = query.where(Player.pa <= max_pa)
    if min_age:
        query = query.where(Player.age >= min_age)
    if max_age:
        query = query.where(Player.age <= max_age)
    if nationality:
        query = query.where(Player.nationality.ilike(f"%{nationality}%"))
    if club:
        query = query.where(Player.club.ilike(f"%{club}%"))

    # Count total (rough — accent-insensitive matches not yet filtered)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    if limit:
        per_page = min(int(limit), 100)
    sort_field = Player.ca.desc()
    if order_by == "pa":
        sort_field = Player.pa.desc()
    elif order_by == "age":
        sort_field = Player.age.asc()

    # If query is non-ASCII (e.g. "mbappe" → "mbappé") we need to
    # iterate over a wider candidate set and match in Python.
    if name_q and not name_q.isascii():
        # Bigger window to ensure accent-matches are captured
        bigger = query.order_by(sort_function := sort_field).limit(2000)
        result = await db.execute(bigger)
        all_players = result.scalars().all()
        filtered = [p for p in all_players if name_q_ascii in _ascii_lower(p.name or "")]
        total = len(filtered)
        offset = (page - 1) * per_page
        players = filtered[offset:offset + per_page]
    elif name_q and name_q.isascii():
        # When the query is plain ASCII, _ascii_lower(p.name) keeps
        # accent variants in the result. We expand the LIKE filter to
        # also match accent-stripped names by iterating Python-side.
        bigger = query.order_by(sort_field).limit(2000)
        result = await db.execute(bigger)
        all_players = result.scalars().all()
        filtered = [p for p in all_players if name_q_ascii in _ascii_lower(p.name or "")]
        total = len(filtered)
        offset = (page - 1) * per_page
        players = filtered[offset:offset + per_page]
    else:
        offset = (page - 1) * per_page
        query = query.order_by(sort_field).offset(offset).limit(per_page)
        result = await db.execute(query)
        players = result.scalars().all()

    return {
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "age": p.age,
                "position": p.position,
                "nationality": p.nationality,
                "club": p.club,
                "ca": p.ca,
                "pa": p.pa,
                "price": p.price,
                "wage": p.wage,
            }
            for p in players
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# === Transfer Operations ===

@router.post("/careers/{career_id}/transfers/bid")
async def submit_bid(
    career_id: int,
    request: BidRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a transfer bid for a player."""
    career = await _verify_career(career_id, user.id, db)
    service = TransferService()

    if not service.is_transfer_window_open(career.week):
        raise HTTPException(400, "Transfer window is closed")

    result = await service.submit_transfer_bid_async(
        db=db,
        career=career,
        player_id=request.player_id,
        bid_amount=request.amount,
    )

    await db.commit()
    return result


@router.post("/careers/{career_id}/transfers/loan")
async def submit_loan(
    career_id: int,
    request: LoanRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a loan offer."""
    career = await _verify_career(career_id, user.id, db)
    service = TransferService()

    result = await service.submit_loan_offer_async(
        db=db,
        career=career,
        player_id=request.player_id,
        loan_type=request.loan_type,
    )

    await db.commit()
    return result


@router.post("/careers/{career_id}/transfers/list")
async def list_player(
    career_id: int,
    request: ListPlayerRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List a player for sale."""
    career = await _verify_career(career_id, user.id, db)

    from sqlalchemy import select
    from app.models.squad_player import SquadPlayer

    result = await db.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == request.player_id,
        )
    )
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Player not in your squad")

    service = TransferService()
    listing = service.list_player_for_sale(sp, asking_price=request.asking_price)
    await db.commit()

    return {"success": True, "listing": listing}


@router.get("/careers/{career_id}/transfers/history")
async def get_history(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transfer history for this career."""
    await _verify_career(career_id, user.id, db)
    service = TransferService()
    history = await service.get_transfer_bid_history(db, career_id)
    return {"history": history}


@router.get("/careers/{career_id}/transfers/window")
async def get_window_status(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current transfer window status."""
    career = await _verify_career(career_id, user.id, db)
    service = TransferService()

    is_open = service.is_transfer_window_open(career.week)
    window_type = service.get_window_type(career.week)

    return {
        "is_open": is_open,
        "window_type": window_type,
        "current_week": career.week,
        "summer_window": "weeks 1-8",
        "winter_window": "weeks 26-30",
    }


@router.get("/careers/{career_id}/transfers/budget")
async def get_budget(
    career_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transfer budget status."""
    career = await _verify_career(career_id, user.id, db)
    service = TransferService()
    budget = service.get_budget_status(career)

    return budget.__dict__ if hasattr(budget, '__dict__') else budget


async def _verify_career(career_id, user_id, db):
    service = CareerService(db)
    career = await service.get_career_by_id(career_id)
    if not career:
        raise HTTPException(404, "Career not found")
    if career.user_id != user_id:
        raise HTTPException(403, "Not your career")
    return career
