"""
Telegram Bot Core - Bot initialization and configuration
"""

from telegram import Update, Bot
from telegram.ext import Application, ApplicationBuilder
from typing import Optional
import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """
    Telegram Bot wrapper for TFM
    Manages bot lifecycle, webhook configuration, and application instance
    """
    
    def __init__(self):
        """Initialize Telegram Bot"""
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.username = settings.TELEGRAM_BOT_USERNAME
        self.webhook_url = settings.TELEGRAM_WEBHOOK_URL
        self.application: Optional[Application] = None
        self._initialized = False
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured in environment variables")
        
        logger.info(f"Initializing Telegram Bot: {self.username or 'Unknown'}")
    
    async def initialize(self) -> Application:
        """
        Initialize the bot application
        
        Returns:
            Application: Initialized telegram.ext.Application instance
        """
        if self._initialized and self.application:
            logger.warning("Bot already initialized, returning existing application")
            return self.application
        
        try:
            # Build application
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .build()
            )
            
            # Import and setup handlers
            from app.bot.handlers import setup_handlers
            setup_handlers(self.application)
            
            self._initialized = True
            logger.info("Telegram Bot application initialized successfully")
            
            return self.application
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram Bot: {e}")
            raise
    
    async def setup_webhook(self) -> bool:
        """
        Configure webhook for production deployment
        
        Returns:
            bool: True if webhook setup successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("TELEGRAM_WEBHOOK_URL not configured, skipping webhook setup")
            return False
        
        if not self.application:
            raise RuntimeError("Bot application not initialized. Call initialize() first.")
        
        try:
            bot: Bot = self.application.bot
            
            # Set webhook
            webhook_path = f"{self.webhook_url}/webhook/{self.token}"
            await bot.set_webhook(
                url=webhook_path,
                allowed_updates=["message", "callback_query", "inline_query"],
                drop_pending_updates=True,
            )
            
            # Verify webhook
            webhook_info = await bot.get_webhook_info()
            logger.info(f"Webhook configured: {webhook_info.url}")
            logger.info(f"Pending updates: {webhook_info.pending_update_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
            return False
    
    async def remove_webhook(self) -> bool:
        """
        Remove webhook configuration (for development/polling mode)
        
        Returns:
            bool: True if webhook removed successfully, False otherwise
        """
        if not self.application:
            raise RuntimeError("Bot application not initialized. Call initialize() first.")
        
        try:
            bot: Bot = self.application.bot
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}")
            return False
    
    async def start_polling(self):
        """
        Start bot in polling mode (for development)
        This is a blocking call that runs until stopped
        """
        if not self.application:
            raise RuntimeError("Bot application not initialized. Call initialize() first.")
        
        try:
            # Remove webhook if exists
            await self.remove_webhook()
            
            logger.info("Starting bot in polling mode...")
            
            # Initialize and start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=["message", "callback_query", "inline_query"],
                drop_pending_updates=True,
            )
            
            logger.info("Bot polling started successfully")
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping bot...")
        except Exception as e:
            logger.error(f"Error in polling mode: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot application"""
        if not self.application:
            return
        
        try:
            logger.info("Stopping Telegram Bot...")
            
            if self.application.updater and self.application.updater.running:
                await self.application.updater.stop()
            
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("Telegram Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def get_bot_info(self) -> dict:
        """
        Get bot information
        
        Returns:
            dict: Bot information including username, name, and webhook status
        """
        if not self.application:
            raise RuntimeError("Bot application not initialized. Call initialize() first.")
        
        try:
            bot: Bot = self.application.bot
            bot_info = await bot.get_me()
            webhook_info = await bot.get_webhook_info()
            
            return {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries,
                "webhook_url": webhook_info.url or None,
                "webhook_pending_updates": webhook_info.pending_update_count,
            }
            
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            raise


# Global bot instance
_bot_instance: Optional[TelegramBot] = None


def get_bot() -> TelegramBot:
    """
    Get or create global bot instance
    
    Returns:
        TelegramBot: Global bot instance
    """
    global _bot_instance
    
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    
    return _bot_instance
