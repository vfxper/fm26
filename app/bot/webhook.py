"""
Telegram Bot Webhook Handler
Handles incoming webhook requests from Telegram in production
"""

from fastapi import APIRouter, Request, Response, HTTPException
from telegram import Update
import json

from app.bot.bot import get_bot
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create router for webhook endpoints
webhook_router = APIRouter(prefix="/webhook", tags=["telegram-webhook"])


@webhook_router.post("/{token}")
async def telegram_webhook(token: str, request: Request) -> Response:
    """
    Handle incoming webhook updates from Telegram
    
    Args:
        token: Bot token (for security - must match configured token)
        request: FastAPI request object containing update data
    
    Returns:
        Response: Empty 200 OK response
    """
    # Verify token matches configured token
    if token != settings.TELEGRAM_BOT_TOKEN:
        logger.warning(f"Webhook called with invalid token: {token[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid token")
    
    try:
        # Get bot instance
        bot = get_bot()
        
        # Ensure bot is initialized
        if not bot.application:
            await bot.initialize()
        
        # Parse update from request body
        update_data = await request.json()
        update = Update.de_json(update_data, bot.application.bot)
        
        # Process update
        await bot.application.process_update(update)
        
        logger.debug(f"Processed webhook update: {update.update_id}")
        
        return Response(status_code=200)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@webhook_router.get("/info")
async def webhook_info() -> dict:
    """
    Get webhook configuration information
    
    Returns:
        dict: Webhook status and configuration
    """
    try:
        bot = get_bot()
        
        # Ensure bot is initialized
        if not bot.application:
            await bot.initialize()
        
        # Get bot info
        bot_info = await bot.get_bot_info()
        
        return {
            "bot_username": bot_info["username"],
            "bot_id": bot_info["id"],
            "webhook_configured": bool(bot_info["webhook_url"]),
            "webhook_url": bot_info["webhook_url"],
            "pending_updates": bot_info["webhook_pending_updates"],
        }
        
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@webhook_router.post("/setup")
async def setup_webhook() -> dict:
    """
    Setup webhook configuration (admin endpoint)
    
    Returns:
        dict: Setup result
    """
    try:
        bot = get_bot()
        
        # Ensure bot is initialized
        if not bot.application:
            await bot.initialize()
        
        # Setup webhook
        success = await bot.setup_webhook()
        
        if success:
            bot_info = await bot.get_bot_info()
            return {
                "success": True,
                "message": "Webhook configured successfully",
                "webhook_url": bot_info["webhook_url"],
            }
        else:
            return {
                "success": False,
                "message": "Failed to configure webhook (check TELEGRAM_WEBHOOK_URL)",
            }
        
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@webhook_router.post("/remove")
async def remove_webhook() -> dict:
    """
    Remove webhook configuration (admin endpoint)
    
    Returns:
        dict: Removal result
    """
    try:
        bot = get_bot()
        
        # Ensure bot is initialized
        if not bot.application:
            await bot.initialize()
        
        # Remove webhook
        success = await bot.remove_webhook()
        
        return {
            "success": success,
            "message": "Webhook removed successfully" if success else "Failed to remove webhook",
        }
        
    except Exception as e:
        logger.error(f"Error removing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
