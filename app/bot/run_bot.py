"""
Telegram Bot Startup Script
Run this script to start the bot in polling mode (development)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.bot.bot import get_bot
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def main():
    """Main entry point for bot"""
    try:
        logger.info("Starting Telegram Football Manager Bot...")
        
        # Get bot instance
        bot = get_bot()
        
        # Initialize bot
        await bot.initialize()
        
        # Get and display bot info
        bot_info = await bot.get_bot_info()
        logger.info(f"Bot Info: @{bot_info['username']} (ID: {bot_info['id']})")
        logger.info(f"Webhook: {bot_info['webhook_url'] or 'Not configured'}")
        
        # Start polling
        logger.info("Starting polling mode (press Ctrl+C to stop)...")
        await bot.start_polling()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
