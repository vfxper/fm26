"""
API Routes - REST API endpoint definitions
"""

from fastapi import APIRouter

# Import route modules
from app.api.routes import players
from app.api.routes import auth
from app.api.routes import settings
from app.api.routes import careers
from app.api.routes import squad
from app.api.routes import tactics
from app.api.routes import transfers
from app.api.routes import training
from app.api.routes import matches
from app.api.routes import other
from app.api.routes import scouting
from app.api.routes import clubs
from app.api.routes import calendar
from app.api.routes import inbox
from app.api.routes import negotiations
from app.api.routes import match_play
from app.api.routes import medical

# Import bot webhook router
from app.bot.webhook import webhook_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Register route modules
api_router.include_router(players.router, prefix="/players", tags=["players"])
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(careers.router)
api_router.include_router(squad.router)
# NOTE: tactics.router (Task 25 — multi-preset CRUD) is intentionally
# DISABLED. Its `/careers/{cid}/tactics` GET/POST conflicts with the
# pitch-board tactic in negotiations.router and crashes on missing
# `tactics_presets` Career attr. The new flow uses career_tactics table.
# api_router.include_router(tactics.router)
api_router.include_router(transfers.router)
api_router.include_router(training.router)
api_router.include_router(matches.router)
api_router.include_router(matches.league_router)
api_router.include_router(other.router)
api_router.include_router(scouting.router)
api_router.include_router(clubs.router)
api_router.include_router(calendar.router)
api_router.include_router(inbox.router)
api_router.include_router(negotiations.router)
api_router.include_router(medical.router)
api_router.include_router(match_play.router, prefix="/careers")

# Register Telegram bot webhook router
api_router.include_router(webhook_router)

__all__ = ["api_router"]
