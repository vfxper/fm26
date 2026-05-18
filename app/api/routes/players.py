"""
Player Routes - API endpoints for player search and management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.player_search import PlayerSearchService, PlayerSearchFilters
from app.schemas.player import (
    PlayerSearchRequest,
    PlayerSearchResponse,
    PlayerResponse,
    FilterOptionsResponse
)

router = APIRouter()


@router.post(
    "/search",
    response_model=PlayerSearchResponse,
    summary="Search players",
    description="""
    Search for players using comprehensive filters and full-text search.
    
    This endpoint provides powerful search capabilities across the entire player database:
    
    **Full-Text Search:**
    - Search across player name, position, club, and nationality
    - Uses PostgreSQL full-text search with relevance ranking
    - Example: "Messi" will find "Lionel Messi"
    
    **Filters:**
    - **Position**: Partial match (e.g., "ST" matches "AM/ST RL")
    - **Age**: Range filter (min_age, max_age)
    - **Current Ability (CA)**: Range filter (min_ca, max_ca) - 1 to 200
    - **Potential Ability (PA)**: Range filter (min_pa, max_pa) - -200 to 200
    - **Nationality**: Exact match
    - **Club**: Exact match
    
    **Sorting:**
    - **relevance**: Sort by search relevance (requires search_text)
    - **ca**: Sort by Current Ability (descending)
    - **pa**: Sort by Potential Ability (descending)
    - **age**: Sort by age (ascending)
    - **name**: Sort by name (ascending)
    
    **Pagination:**
    - Use `limit` and `offset` for pagination
    - Maximum limit: 200 results per page
    - Response includes `has_more` flag to indicate if more results exist
    
    **Example Queries:**
    
    1. Find all strikers with CA > 150:
    ```json
    {
        "position": "ST",
        "min_ca": 150,
        "order_by": "ca"
    }
    ```
    
    2. Search for "Messi":
    ```json
    {
        "search_text": "Messi",
        "order_by": "relevance"
    }
    ```
    
    3. Find young talents (age 18-21, PA > 160):
    ```json
    {
        "min_age": 18,
        "max_age": 21,
        "min_pa": 160,
        "order_by": "pa"
    }
    ```
    """,
    responses={
        200: {
            "description": "Successful search",
            "content": {
                "application/json": {
                    "example": {
                        "players": [
                            {
                                "uid": "player_001",
                                "name": "Lionel Messi",
                                "position": "AM/ST RL",
                                "age": 36,
                                "nationality": "Argentina",
                                "club": "Inter Miami",
                                "ca": 180,
                                "pa": 200
                            }
                        ],
                        "total": 1,
                        "limit": 50,
                        "offset": 0,
                        "has_more": False
                    }
                }
            }
        },
        400: {
            "description": "Invalid filter parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "min_ca cannot be greater than max_ca"
                    }
                }
            }
        },
        422: {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "loc": ["body", "min_ca"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def search_players(
    request: PlayerSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> PlayerSearchResponse:
    """
    Search for players using comprehensive filters.
    
    Args:
        request: PlayerSearchRequest with search criteria
        db: Database session (injected)
        
    Returns:
        PlayerSearchResponse with paginated results
        
    Raises:
        HTTPException 400: If filter validation fails
        HTTPException 500: If database error occurs
    """
    try:
        # Create search service
        search_service = PlayerSearchService(db)
        
        # Create filters from request
        filters = PlayerSearchFilters(
            search_text=request.search_text,
            position=request.position,
            min_age=request.min_age,
            max_age=request.max_age,
            min_ca=request.min_ca,
            max_ca=request.max_ca,
            min_pa=request.min_pa,
            max_pa=request.max_pa,
            nationality=request.nationality,
            club=request.club,
            limit=request.limit,
            offset=request.offset,
            order_by=request.order_by
        )
        
        # Execute search
        results = await search_service.search_players(filters)
        
        # Convert to response model
        return PlayerSearchResponse(
            players=[PlayerResponse.model_validate(player) for player in results["players"]],
            total=results["total"],
            limit=results["limit"],
            offset=results["offset"],
            has_more=results["has_more"]
        )
        
    except ValueError as e:
        # Filter validation error
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": str(e)
            }
        )
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An error occurred while searching players"
            }
        )


@router.get(
    "/search",
    response_model=PlayerSearchResponse,
    summary="Search players (GET)",
    description="""
    Search for players using query parameters (GET alternative to POST /search).
    
    This endpoint provides the same functionality as POST /search but uses query
    parameters instead of a request body. Useful for simple searches and bookmarkable URLs.
    
    See POST /search for detailed documentation on filters and sorting.
    
    **Example:**
    ```
    GET /api/players/search?search_text=Messi&min_ca=150&order_by=ca&limit=20
    ```
    """,
    responses={
        200: {
            "description": "Successful search",
        },
        400: {
            "description": "Invalid filter parameters",
        }
    }
)
async def search_players_get(
    search_text: Optional[str] = Query(None, description="Full-text search query"),
    q: Optional[str] = Query(None, description="Alias for search_text"),
    position: Optional[str] = Query(None, description="Filter by position (partial match)"),
    min_age: Optional[int] = Query(None, ge=15, le=50, description="Minimum age"),
    max_age: Optional[int] = Query(None, ge=15, le=50, description="Maximum age"),
    min_ca: Optional[int] = Query(None, ge=1, le=200, description="Minimum Current Ability"),
    max_ca: Optional[int] = Query(None, ge=1, le=200, description="Maximum Current Ability"),
    min_pa: Optional[int] = Query(None, ge=-200, le=200, description="Minimum Potential Ability"),
    max_pa: Optional[int] = Query(None, ge=-200, le=200, description="Maximum Potential Ability"),
    nationality: Optional[str] = Query(None, description="Filter by nationality (exact match)"),
    club: Optional[str] = Query(None, description="Filter by club (exact match)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    order_by: str = Query("ca", description="Sort order: relevance, ca, pa, age, name"),
    per_page: Optional[int] = Query(None, ge=1, le=200, description="Alias for limit"),
    db: AsyncSession = Depends(get_db)
) -> PlayerSearchResponse:
    """
    Search for players using query parameters.
    
    This is a GET alternative to POST /search that uses query parameters.
    Supports 'q' as alias for 'search_text' for convenience.
    """
    # Support 'q' as alias for search_text
    actual_search_text = search_text or q
    actual_limit = per_page or limit
    
    # Try the full search service first (works with PostgreSQL)
    try:
        request = PlayerSearchRequest(
            search_text=actual_search_text,
            position=position,
            min_age=min_age,
            max_age=max_age,
            min_ca=min_ca,
            max_ca=max_ca,
            min_pa=min_pa,
            max_pa=max_pa,
            nationality=nationality,
            club=club,
            limit=actual_limit,
            offset=offset,
            order_by=order_by if actual_search_text or order_by != "relevance" else "ca"
        )
        return await search_players(request, db)
    except Exception:
        # Fallback for SQLite: use simple LIKE queries
        pass
    
    # SQLite fallback - simple LIKE-based search with accent-insensitive
    # name match (so "mbappe" finds "Mbappé").
    try:
        from sqlalchemy import text as sql_text
        import unicodedata

        def _ascii_lower(s):
            if not s:
                return ""
            nfkd = unicodedata.normalize("NFKD", str(s))
            return "".join(
                c for c in nfkd
                if not unicodedata.combining(c) and ord(c) < 128
            ).lower()

        ascii_text = _ascii_lower(actual_search_text or "")

        conditions = []
        params = {}

        # When the user typed something, do NOT push a SQL LIKE on name —
        # we'll match in Python after stripping accents. We still allow
        # SQL LIKE for non-name fields below (so club/nationality/position
        # short-text queries don't blow the result set up).
        if actual_search_text and not ascii_text:
            # Empty after stripping accents → pointless.
            pass
        if actual_search_text and ascii_text:
            # The seed builds a `name_ascii` column (Pérez → "perez") so
            # accent-insensitive name matching is just a plain LIKE.
            # We OR with the raw query against club / nationality /
            # position to keep those fields searchable too.
            raw_q = (actual_search_text or "").lower()
            conditions.append(
                "(name_ascii LIKE :nlike OR LOWER(club) LIKE :nlike "
                "OR LOWER(nationality) LIKE :nlike "
                "OR LOWER(position) LIKE :nlike "
                "OR LOWER(name) LIKE :nraw OR LOWER(club) LIKE :nraw "
                "OR LOWER(nationality) LIKE :nraw "
                "OR LOWER(position) LIKE :nraw)"
            )
            params["nlike"] = f"%{ascii_text}%"
            params["nraw"] = f"%{raw_q}%"
        if position:
            conditions.append("position LIKE :pos")
            params["pos"] = f"%{position}%"
        if min_age is not None:
            conditions.append("age >= :min_age")
            params["min_age"] = min_age
        if max_age is not None:
            conditions.append("age <= :max_age")
            params["max_age"] = max_age
        if min_ca is not None:
            conditions.append("ca >= :min_ca")
            params["min_ca"] = min_ca
        if max_ca is not None:
            conditions.append("ca <= :max_ca")
            params["max_ca"] = max_ca
        if min_pa is not None:
            conditions.append("pa >= :min_pa")
            params["min_pa"] = min_pa
        if max_pa is not None:
            conditions.append("pa <= :max_pa")
            params["max_pa"] = max_pa
        if nationality:
            conditions.append("nationality = :nat")
            params["nat"] = nationality
        if club:
            conditions.append("club = :club")
            params["club"] = club

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Sort
        sort_map = {"ca": "ca DESC", "pa": "pa DESC", "age": "age ASC", "name": "name ASC"}
        order = sort_map.get(order_by, "ca DESC")

        # Pull a wider window when name search is active so the
        # post-filter doesn't run out of accent matches.
        wide_lim = actual_limit if not ascii_text else max(actual_limit * 4, 2000)
        query_sql = f"SELECT * FROM players WHERE {where_clause} ORDER BY {order} LIMIT :lim OFFSET :off"
        params["lim"] = wide_lim
        params["off"] = 0  # offset applied AFTER python filter

        result = await db.execute(sql_text(query_sql), params)
        rows = result.fetchall()
        columns = result.keys() if hasattr(result, 'keys') else []

        # Convert rows → dicts.
        candidates = []
        for row in rows:
            if hasattr(row, '_mapping'):
                rd = dict(row._mapping)
            elif columns:
                rd = dict(zip(columns, row))
            else:
                rd = {}
            candidates.append(rd)

        # Accent-insensitive Python filter.
        if ascii_text:
            filtered = []
            for rd in candidates:
                if ascii_text in _ascii_lower(rd.get("name") or ""):
                    filtered.append(rd)
                    continue
                # also allow club / nationality / position contains
                if (
                    ascii_text in _ascii_lower(rd.get("club") or "")
                    or ascii_text in _ascii_lower(rd.get("nationality") or "")
                    or ascii_text in _ascii_lower(rd.get("position") or "")
                ):
                    filtered.append(rd)
            candidates = filtered

        total = len(candidates)
        page = candidates[offset: offset + actual_limit]

        players = []
        for rd in page:
            players.append(PlayerResponse(
                # CRITICAL: send database id (not CSV uid) so the frontend
                # can fetch /players/{id}/profile reliably. We expose it
                # under both `id` and `uid` for compatibility.
                id=rd.get('id'),
                uid=str(rd.get('id', '')) or rd.get('uid') or '0',
                name=rd.get('name', ''),
                position=rd.get('position', ''),
                age=rd.get('age', 0),
                nationality=rd.get('nationality', ''),
                club=rd.get('club', ''),
                ca=rd.get('ca', 0),
                pa=rd.get('pa', 0),
                corners=rd.get('corners', 10),
                crossing=rd.get('crossing', 10),
                dribbling=rd.get('dribbling', 10),
                finishing=rd.get('finishing', 10),
                first_touch=rd.get('first_touch', 10),
                free_kicks=rd.get('free_kicks', rd.get('free_kick', 10)),
                heading=rd.get('heading', 10),
                long_shots=rd.get('long_shots', 10),
                long_throws=rd.get('long_throws', 10),
                marking=rd.get('marking', 10),
                passing=rd.get('passing', 10),
                penalty=rd.get('penalty', rd.get('penalty_taking', 10)),
                tackling=rd.get('tackling', 10),
                technique=rd.get('technique', 10),
                aggression=rd.get('aggression', 10),
                anticipation=rd.get('anticipation', 10),
                bravery=rd.get('bravery', 10),
                composure=rd.get('composure', 10),
                concentration=rd.get('concentration', 10),
                decisions=rd.get('decisions', 10),
                determination=rd.get('determination', 10),
                flair=rd.get('flair', 10),
                leadership=rd.get('leadership', 10),
                off_the_ball=rd.get('off_the_ball', 10),
                positioning=rd.get('positioning', 10),
                teamwork=rd.get('teamwork', 10),
                vision=rd.get('vision', 10),
                work_rate=rd.get('work_rate', 10),
                acceleration=rd.get('acceleration', 10),
                agility=rd.get('agility', 10),
                balance=rd.get('balance', 10),
                jumping=rd.get('jumping', rd.get('jumping_reach', 10)),
                stamina=rd.get('stamina', 10),
                pace=rd.get('pace', 10),
                endurance=rd.get('endurance', rd.get('natural_fitness', 10)),
                strength=rd.get('strength', 10),
                price=rd.get('price', '0'),
                wage=rd.get('wage', 0) or 0,
                height=rd.get('height', 180),
                weight=rd.get('weight', 75),
                left_foot=rd.get('left_foot', 10),
                right_foot=rd.get('right_foot', 10),
                traits=rd.get('traits'),
            ))
        
        return PlayerSearchResponse(
            players=players,
            total=total,
            limit=actual_limit,
            offset=offset,
            has_more=(offset + actual_limit) < total
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": f"Search failed: {str(e)}"
            }
        )


@router.get(
    "/filter-options",
    response_model=FilterOptionsResponse,
    summary="Get filter options",
    description="""
    Get available filter options from the database.
    
    This endpoint returns lists of unique values for categorical filters
    (positions, nationalities, clubs) and ranges for numerical filters
    (age, CA, PA). Use this to build dynamic filter UIs.
    
    **Response includes:**
    - **positions**: List of all unique positions in the database
    - **nationalities**: List of all unique nationalities (sorted)
    - **clubs**: List of all unique clubs (sorted)
    - **age_range**: Min and max age values
    - **ca_range**: Min and max Current Ability values
    - **pa_range**: Min and max Potential Ability values
    
    **Example Response:**
    ```json
    {
        "positions": ["GK", "DC", "DL", "DR", "DM", "MC", "ML", "MR", "AM", "ST"],
        "nationalities": ["Argentina", "Brazil", "England", "France"],
        "clubs": ["Barcelona", "Real Madrid", "Manchester United"],
        "age_range": {"min": 16, "max": 42},
        "ca_range": {"min": 50, "max": 200},
        "pa_range": {"min": -200, "max": 200}
    }
    ```
    """,
    responses={
        200: {
            "description": "Successful retrieval of filter options",
        },
        500: {
            "description": "Database error",
        }
    }
)
async def get_filter_options(
    db: AsyncSession = Depends(get_db)
) -> FilterOptionsResponse:
    """
    Get available filter options from the database.
    
    Args:
        db: Database session (injected)
        
    Returns:
        FilterOptionsResponse with available filter values
        
    Raises:
        HTTPException 500: If database error occurs
    """
    try:
        # Create search service
        search_service = PlayerSearchService(db)
        
        # Get filter options
        options = await search_service.get_filter_options()
        
        # Convert to response model
        return FilterOptionsResponse(**options)
        
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An error occurred while retrieving filter options"
            }
        )
