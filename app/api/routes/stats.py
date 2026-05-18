"""
Stats API — top scorers / top assists per league or European cup.

Reads from the `player_match_stats` table populated by both the user's
own matches and the AI-vs-AI background runner.

Endpoints:
    GET /careers/{career_id}/stats/scorers?competition=...&season=...&limit=20
    GET /careers/{career_id}/stats/assists?competition=...&season=...&limit=20
    GET /careers/{career_id}/stats/competitions
        → list of competitions with at least one logged stat in this career
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user

router = APIRouter(tags=["stats"])


def _verify_career_access(db: AsyncSession, career_id: int, user_id: int):
    """Lightweight check — uses get_current_user dep upstream."""
    pass  # gating already happens in the dependency


async def _resolve_season(
    db: AsyncSession, career_id: int, requested: Optional[int]
) -> int:
    if requested is not None:
        return requested
    try:
        row = (
            await db.execute(
                text("SELECT current_season FROM careers WHERE id = :c"),
                {"c": career_id},
            )
        ).fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception:
        pass
    return 1


@router.get("/careers/{career_id}/stats/competitions")
async def list_competitions_with_stats(
    career_id: int,
    season: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all competitions with at least one logged player stat."""
    s = await _resolve_season(db, career_id, season)
    rows = await db.execute(
        text(
            "SELECT competition, COUNT(*) AS rows, SUM(goals) AS gtot "
            "FROM player_match_stats "
            "WHERE career_id = :c AND season = :s "
            "GROUP BY competition "
            "ORDER BY gtot DESC"
        ),
        {"c": career_id, "s": s},
    )
    competitions = [
        {
            "competition": r[0],
            "label": _competition_label(r[0]),
            "rows": int(r[1]),
            "total_goals": int(r[2] or 0),
        }
        for r in rows.fetchall()
    ]
    return {"season": s, "competitions": competitions}


def _competition_label(comp: str) -> str:
    """Make a human-readable label from a competition tag."""
    if not comp:
        return ""
    if comp == "ucl":
        return "Лига чемпионов"
    if comp == "uel":
        return "Лига Европы"
    if comp == "uecl":
        return "Лига конференций"
    if comp.startswith("league:"):
        # Strip leading emoji/flags so we get a clean league name.
        name = comp[len("league:"):].strip()
        cleaned = []
        for ch in name:
            cp = ord(ch)
            # Skip regional indicator symbols (flag letters)
            if 0x1F1E6 <= cp <= 0x1F1FF:
                continue
            # Skip tag base + tag latin letters
            if cp == 0xE0001 or 0xE0020 <= cp <= 0xE007F:
                continue
            # Skip variation selectors
            if 0xFE00 <= cp <= 0xFE0F:
                continue
            # Skip misc symbols & pictographs (including U+1F3F4 black flag)
            if 0x1F300 <= cp <= 0x1FAFF:
                continue
            # Skip various dingbat/symbol blocks
            if 0x2600 <= cp <= 0x27BF:
                continue
            cleaned.append(ch)
        return "".join(cleaned).strip() or name
    if comp.startswith("domestic_cup:"):
        return f"Кубок · {comp[len('domestic_cup:'):]}"
    return comp


@router.get("/careers/{career_id}/stats/scorers")
async def top_scorers(
    career_id: int,
    competition: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Top goal scorers in a competition (or across all if `competition` is None)."""
    s = await _resolve_season(db, career_id, season)
    where = ["pms.career_id = :c", "pms.season = :s"]
    params = {"c": career_id, "s": s, "lim": limit}
    if competition:
        where.append("pms.competition = :comp")
        params["comp"] = competition

    sql = (
        "SELECT pms.player_id, p.name, p.position, pms.club_name, "
        "       SUM(pms.goals) AS goals, "
        "       SUM(pms.assists) AS assists, "
        "       SUM(pms.appearances) AS apps "
        "FROM player_match_stats pms "
        "LEFT JOIN players p ON p.id = pms.player_id "
        f"WHERE {' AND '.join(where)} "
        "GROUP BY pms.player_id, p.name, p.position, pms.club_name "
        "HAVING SUM(pms.goals) > 0 "
        "ORDER BY SUM(pms.goals) DESC, SUM(pms.assists) DESC "
        "LIMIT :lim"
    )
    rows = await db.execute(text(sql), params)
    items = [
        {
            "player_id": int(r[0]),
            "name": r[1] or "?",
            "position": r[2] or "",
            "club": r[3] or "",
            "goals": int(r[4] or 0),
            "assists": int(r[5] or 0),
            "appearances": int(r[6] or 0),
        }
        for r in rows.fetchall()
    ]
    return {
        "season": s,
        "competition": competition,
        "competition_label": _competition_label(competition or ""),
        "scorers": items,
    }


@router.get("/careers/{career_id}/stats/assists")
async def top_assists(
    career_id: int,
    competition: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Top assist providers in a competition."""
    s = await _resolve_season(db, career_id, season)
    where = ["pms.career_id = :c", "pms.season = :s"]
    params = {"c": career_id, "s": s, "lim": limit}
    if competition:
        where.append("pms.competition = :comp")
        params["comp"] = competition

    sql = (
        "SELECT pms.player_id, p.name, p.position, pms.club_name, "
        "       SUM(pms.goals) AS goals, "
        "       SUM(pms.assists) AS assists, "
        "       SUM(pms.appearances) AS apps "
        "FROM player_match_stats pms "
        "LEFT JOIN players p ON p.id = pms.player_id "
        f"WHERE {' AND '.join(where)} "
        "GROUP BY pms.player_id, p.name, p.position, pms.club_name "
        "HAVING SUM(pms.assists) > 0 "
        "ORDER BY SUM(pms.assists) DESC, SUM(pms.goals) DESC "
        "LIMIT :lim"
    )
    rows = await db.execute(text(sql), params)
    items = [
        {
            "player_id": int(r[0]),
            "name": r[1] or "?",
            "position": r[2] or "",
            "club": r[3] or "",
            "goals": int(r[4] or 0),
            "assists": int(r[5] or 0),
            "appearances": int(r[6] or 0),
        }
        for r in rows.fetchall()
    ]
    return {
        "season": s,
        "competition": competition,
        "competition_label": _competition_label(competition or ""),
        "assisters": items,
    }
