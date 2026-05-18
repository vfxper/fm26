"""
Telegram Bot Handlers - Command and message handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command - Entry point to the game
    
    Shows welcome message and Web App launch button
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    # Construct Web App URL
    # In production, this should point to your hosted frontend
    # For development, you can use ngrok or similar tunneling service
    web_app_url = settings.TELEGRAM_WEBHOOK_URL or "https://your-domain.com"
    if web_app_url.endswith("/"):
        web_app_url = web_app_url[:-1]
    
    # Welcome message
    welcome_text = (
        f"⚽ Welcome to *{settings.APP_NAME}*\\!\n\n"
        f"Hello {user.mention_markdown_v2()}\\! 👋\n\n"
        f"Take control of your football club and lead them to glory\\!\n\n"
        f"🎮 *Features:*\n"
        f"• Manage a squad from 2600\\+ real players\n"
        f"• Watch matches in real\\-time 2D animation\n"
        f"• Build tactics and formations\n"
        f"• Transfer market and player development\n"
        f"• Compete in leagues and cups\n\n"
        f"Click the button below to start your managerial career\\!"
    )
    
    # Create Web App button
    keyboard = [
        [
            InlineKeyboardButton(
                "🎮 Play Game",
                web_app=WebAppInfo(url=web_app_url)
            )
        ],
        [
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send welcome message
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="MarkdownV2",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command - Show help information
    """
    user = update.effective_user
    logger.info(f"User {user.id} requested help")
    
    help_text = (
        f"⚽ *{settings.APP_NAME} Help*\n\n"
        f"*Available Commands:*\n"
        f"/start - Launch the game\n"
        f"/play - Quick launch game\n"
        f"/help - Show this help message\n"
        f"/stats - View your career statistics\n\n"
        f"*How to Play:*\n"
        f"1️⃣ Click 'Play Game' to launch the Web App\n"
        f"2️⃣ Select your club to start your career\n"
        f"3️⃣ Manage your squad, tactics, and transfers\n"
        f"4️⃣ Watch matches in real-time 2D animation\n"
        f"5️⃣ Lead your club to glory!\n\n"
        f"*Need Support?*\n"
        f"Contact: @your_support_username"
    )
    
    # Create back button
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /play command - Quick launch to game
    """
    user = update.effective_user
    logger.info(f"User {user.id} used /play command")
    
    # Construct Web App URL
    web_app_url = settings.TELEGRAM_WEBHOOK_URL or "https://your-domain.com"
    if web_app_url.endswith("/"):
        web_app_url = web_app_url[:-1]
    
    # Create Web App button
    keyboard = [
        [
            InlineKeyboardButton(
                "🎮 Launch Game",
                web_app=WebAppInfo(url=web_app_url)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚽ Ready to manage your club?",
        reply_markup=reply_markup,
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command - Show user career statistics
    
    TODO: Integrate with Career_Manager to fetch real stats
    """
    user = update.effective_user
    logger.info(f"User {user.id} requested stats")
    
    # Placeholder stats - will be replaced with real data from database
    stats_text = (
        f"📊 *Career Statistics*\n\n"
        f"*Manager:* {user.first_name}\n"
        f"*Club:* Not Started\n"
        f"*Seasons:* 0\n"
        f"*Matches:* 0 (W: 0, D: 0, L: 0)\n"
        f"*Trophies:* 0\n"
        f"*Win Rate:* 0%\n\n"
        f"_Start your career to see your stats!_"
    )
    
    # Create buttons
    keyboard = [
        [InlineKeyboardButton("🎮 Start Career", callback_data="start_career")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline button callbacks
    """
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    callback_data = query.data
    
    logger.info(f"User {user.id} pressed button: {callback_data}")
    
    if callback_data == "help":
        # Show help information
        help_text = (
            f"⚽ *{settings.APP_NAME} Help*\n\n"
            f"*Available Commands:*\n"
            f"/start - Launch the game\n"
            f"/play - Quick launch game\n"
            f"/help - Show this help message\n"
            f"/stats - View your career statistics\n\n"
            f"*How to Play:*\n"
            f"1️⃣ Click 'Play Game' to launch the Web App\n"
            f"2️⃣ Select your club to start your career\n"
            f"3️⃣ Manage your squad, tactics, and transfers\n"
            f"4️⃣ Watch matches in real-time 2D animation\n"
            f"5️⃣ Lead your club to glory!\n\n"
            f"*Need Support?*\n"
            f"Contact: @your_support_username"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    
    elif callback_data == "stats":
        # Show stats (placeholder)
        stats_text = (
            f"📊 *Career Statistics*\n\n"
            f"*Manager:* {user.first_name}\n"
            f"*Club:* Not Started\n"
            f"*Seasons:* 0\n"
            f"*Matches:* 0 (W: 0, D: 0, L: 0)\n"
            f"*Trophies:* 0\n"
            f"*Win Rate:* 0%\n\n"
            f"_Start your career to see your stats!_"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Start Career", callback_data="start_career")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    
    elif callback_data == "start_career":
        # Launch Web App
        web_app_url = settings.TELEGRAM_WEBHOOK_URL or "https://your-domain.com"
        if web_app_url.endswith("/"):
            web_app_url = web_app_url[:-1]
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎮 Launch Game",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚽ Ready to start your managerial career?",
            reply_markup=reply_markup,
        )
    
    elif callback_data == "back_to_menu":
        # Return to main menu
        web_app_url = settings.TELEGRAM_WEBHOOK_URL or "https://your-domain.com"
        if web_app_url.endswith("/"):
            web_app_url = web_app_url[:-1]
        
        welcome_text = (
            f"⚽ *{settings.APP_NAME}*\n\n"
            f"Welcome back, {user.first_name}! 👋\n\n"
            f"Ready to manage your club?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎮 Play Game",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors in bot handlers
    """
    logger.error(f"Update {update} caused error: {context.error}")
    
    # Notify user of error
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred while processing your request. Please try again later."
        )


def setup_handlers(application: Application) -> None:
    """
    Setup all bot command and callback handlers
    
    Args:
        application: Telegram Application instance
    """
    logger.info("Setting up bot handlers...")
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("Bot handlers setup complete")
