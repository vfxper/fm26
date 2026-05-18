"""
Clubs API Endpoints
GET /api/clubs - List all clubs
GET /api/clubs/searchable - Lightweight searchable list for the friendly opponent picker
GET /api/clubs/{club_id} - Get club details
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.get("")
async def list_clubs(
    top_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get list of clubs. Returns all clubs from top 10 leagues with player counts."""
    from app.data.club_budgets import get_all_clubs, CLUBS_TO_CSV

    all_clubs = get_all_clubs()

    # Get player counts per club from DB
    player_counts = {}
    try:
        result = await db.execute(
            text("SELECT club, COUNT(*) FROM players WHERE club IS NOT NULL GROUP BY club")
        )
        for row in result.fetchall():
            player_counts[row[0]] = row[1]
    except Exception:
        pass

    clubs = []
    for idx, c in enumerate(all_clubs, start=1):
        # 1) Exact match against CSV club column
        count = player_counts.get(c["name"], 0)
        # 2) Every alias from CLUBS_TO_CSV
        if count == 0:
            for alias in CLUBS_TO_CSV.get(c["name"], []):
                if alias in player_counts:
                    count = player_counts[alias]
                    break
        # 3) Last-resort fuzzy contain match
        if count == 0:
            for db_name, cnt in player_counts.items():
                if c["name"].lower() in db_name.lower() or db_name.lower() in c["name"].lower():
                    count = cnt
                    break
        
        clubs.append({
            "id": idx,
            "name": c["name"],
            "reputation": min(100, c["transfer_budget"] // 1000000),
            "league": c["league"],
            "country": "",
            "player_count": count,
            "transfer_budget": c["transfer_budget"],
            "scouting_budget": c["scouting_budget"],
        })
    
    return {"clubs": clubs, "total": len(clubs)}


@router.get("/searchable")
async def list_searchable_clubs(
    exclude_career_id: Optional[int] = Query(default=None, ge=1),
    ucl_only: bool = Query(default=False, description="When true, restrict to the 36 UCL participants of the active competition."),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight listing for the friendly opponent picker.

    Returns id (1-based), name, and league. When ``exclude_career_id``
    is provided, the career's own club is omitted from the response.
    When ``ucl_only=true`` the list is restricted to clubs that are
    1-based-mappable to ``CLUBS`` AND participate in the active UCL
    competition — useful for the "auto-pick UCL opponent" friendly
    picker. See Requirements 2.1, 2.6.
    """
    from app.data.club_budgets import CLUBS

    excluded_id = None
    if exclude_career_id is not None:
        result = await db.execute(
            text("SELECT club_id FROM careers WHERE id = :cid"),
            {"cid": exclude_career_id},
        )
        row = result.fetchone()
        if row:
            excluded_id = row[0]

    # Resolve the set of club_ids that participate in the most recent
    # UCL competition (only when caller asked for that filter).
    ucl_club_ids: Optional[set[int]] = None
    if ucl_only:
        comp = await db.execute(
            text(
                "SELECT id FROM competitions "
                "WHERE name = 'Champions League' "
                "ORDER BY id DESC LIMIT 1"
            )
        )
        comp_row = comp.fetchone()
        if comp_row:
            r = await db.execute(
                text(
                    "SELECT DISTINCT club_id FROM ucl_participants "
                    "WHERE competition_id = :cid AND club_id IS NOT NULL"
                ),
                {"cid": int(comp_row[0])},
            )
            ucl_club_ids = {int(x[0]) for x in r.fetchall() if x[0] is not None}
        else:
            ucl_club_ids = set()

    items = []
    for idx, (name, _scout, _trans, league) in enumerate(CLUBS, start=1):
        if idx == excluded_id:
            continue
        if ucl_club_ids is not None and idx not in ucl_club_ids:
            continue
        items.append({"id": idx, "name": name, "league": league})

    return {"clubs": items, "total": len(items)}


@router.get("/ucl-participants")
async def list_ucl_participants():
    """List the 36 UEFA Champions League participants for the current season.

    Returns each entry in UCL_PARTICIPANTS order with:
      - id: 1-based index in UCL_PARTICIPANTS (1..36) — used as the request
        body `club_id` when creating a career in `ucl_only` mode.
      - name: display name
      - country: country name
      - club_id: 1-based index in CLUBS, or null if the club is not in CLUBS
      - is_in_clubs: True iff club_id is not null
    """
    from app.data.ucl_config import UCL_PARTICIPANTS

    items = []
    for idx, (name, club_id, country) in enumerate(UCL_PARTICIPANTS, start=1):
        items.append({
            "id": idx,
            "name": name,
            "country": country,
            "club_id": club_id,
            "is_in_clubs": club_id is not None,
        })
    return {"clubs": items, "total": len(items)}


@router.get("/{club_id}")
async def get_club(
    club_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get club details by ID."""
    try:
        result = await db.execute(
            text("SELECT id, name, reputation, league, country FROM clubs WHERE id = :cid"),
            {"cid": club_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(404, "Club not found")
        return {
            "id": row[0],
            "name": row[1],
            "reputation": row[2],
            "league": row[3],
            "country": row[4],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch club: {str(e)}")
