"""
Telegram Bot Module - Entry point for Telegram Bot functionality
"""

from app.bot.bot import TelegramBot
from app.bot.handlers import setup_handlers

__all__ = ["TelegramBot", "setup_handlers"]
