"""
🤖 Football Manager 26 - Telegram Bot Launcher
================================================
Simple script to run the Telegram bot.

Before running:
1. Get a bot token from @BotFather in Telegram
2. Set TELEGRAM_BOT_TOKEN in .env file (or paste it below)

Usage:
    python run_bot.py
"""

import asyncio
import os
import sys

# Try to load .env file
try:
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())
except FileNotFoundError:
    pass

# Get bot token
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
    print("❌ ERROR: No bot token configured!")
    print()
    print("To fix this:")
    print("1. Open Telegram and message @BotFather")
    print("2. Send /newbot and follow instructions")
    print("3. Copy the token BotFather gives you")
    print("4. Open .env file and replace 'your_bot_token_here' with your token")
    print()
    print("Or paste your token here:")
    token = input("Bot token: ").strip()
    if token:
        BOT_TOKEN = token
        # Save to .env
        with open('.env', 'r') as f:
            content = f.read()
        content = content.replace('your_bot_token_here', token)
        with open('.env', 'w') as f:
            f.write(content)
        print(f"✅ Token saved to .env")
    else:
        sys.exit(1)

# Check if python-telegram-bot is installed
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
except ImportError:
    print("❌ python-telegram-bot not installed!")
    print("Run: python -m pip install python-telegram-bot")
    sys.exit(1)

print(f"🤖 Starting Football Manager 26 Bot...")
print(f"   Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print()


# ─── Bot Handlers ────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Game", web_app={"url": "https://your-domain.com"})],
        [InlineKeyboardButton("📊 My Career", callback_data="career")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚽ *Welcome to Football Manager 26!*\n\n"
        f"Hello, {user.first_name}! 👋\n\n"
        f"Manage your club, buy players, train your squad, "
        f"and compete in leagues and cups!\n\n"
        f"🎮 Tap 'Play Game' to start your career.",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "⚽ *Football Manager 26 - Help*\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/play - Open the game\n"
        "/career - View your career\n"
        "/squad - View your squad\n"
        "/search <name> - Search for a player\n"
        "/help - Show this help\n\n"
        "Tap the buttons below messages to interact!",
        parse_mode="Markdown",
    )


async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command - search for players."""
    if not context.args:
        await update.message.reply_text("Usage: /search <player name>\nExample: /search Messi")
        return
    
    query = " ".join(context.args)
    
    # Load players and search
    import csv
    results = []
    csv_path = os.path.join(os.path.dirname(__file__), '2600球员属性.csv')
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if query.lower() in row['name'].lower():
                    results.append(row)
                    if len(results) >= 5:
                        break
    except Exception as e:
        await update.message.reply_text(f"❌ Error searching: {e}")
        return
    
    if not results:
        await update.message.reply_text(f"🔍 No players found for '{query}'")
        return
    
    text = f"🔍 *Search results for '{query}':*\n\n"
    for p in results:
        ca = int(p.get('ca', 0))
        pa = int(p.get('pa', 0))
        stars = "⭐" * (ca // 40 + 1)
        text += (
            f"*{p['name']}*\n"
            f"  📍 {p.get('position', '?')} | 🏟 {p.get('club', '?')}\n"
            f"  🌍 {p.get('nationality', '?')} | Age: {p.get('age', '?')}\n"
            f"  💪 CA: {ca} | PA: {pa} {stars}\n\n"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def career_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /career command."""
    await update.message.reply_text(
        "📊 *Your Career*\n\n"
        "You haven't started a career yet!\n"
        "Use /start and tap 'Play Game' to begin.",
        parse_mode="Markdown",
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "career":
        await query.edit_message_text("📊 Career mode coming soon! Use /search to find players.")
    elif query.data == "leaderboard":
        await query.edit_message_text("🏆 Leaderboard coming soon!")
    elif query.data == "settings":
        await query.edit_message_text("⚙️ Settings coming soon!")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    """Start the bot."""
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_player))
    app.add_handler(CommandHandler("career", career_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Start polling
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("   Open Telegram and message your bot to test.")
    print()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
