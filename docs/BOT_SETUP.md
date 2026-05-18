# Telegram Bot Setup Guide

This guide explains how to configure and run the Telegram Bot for Telegram Football Manager.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Bot Configuration](#bot-configuration)
3. [Development Mode (Polling)](#development-mode-polling)
4. [Production Mode (Webhook)](#production-mode-webhook)
5. [Bot Commands](#bot-commands)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to choose a name and username for your bot
4. BotFather will provide you with a **Bot Token** (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Save this token securely - you'll need it for configuration

### 2. Configure Bot Settings (Optional)

Send these commands to @BotFather to customize your bot:

```
/setdescription - Set bot description
/setabouttext - Set about text
/setuserpic - Set bot profile picture
/setcommands - Set bot commands list
```

Recommended commands list:
```
start - Launch the game
play - Quick launch game
help - Show help information
stats - View career statistics
```

---

## Bot Configuration

### Environment Variables

Add the following variables to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_WEBHOOK_URL=https://your-domain.com
```

**Configuration Details:**

- **TELEGRAM_BOT_TOKEN** (Required): Your bot token from BotFather
- **TELEGRAM_BOT_USERNAME** (Optional): Your bot's username (e.g., `tfm_bot`)
- **TELEGRAM_WEBHOOK_URL** (Required for production): Your public HTTPS URL for webhook

### Example Configuration

**Development:**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=tfm_dev_bot
TELEGRAM_WEBHOOK_URL=
```

**Production:**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=tfm_bot
TELEGRAM_WEBHOOK_URL=https://api.yourdomain.com
```

---

## Development Mode (Polling)

In development, the bot runs in **polling mode** - it actively checks for new messages from Telegram.

### Start Bot (Linux/Mac)

```bash
chmod +x scripts/start_bot.sh
./scripts/start_bot.sh
```

### Start Bot (Windows)

```cmd
scripts\start_bot.bat
```

### Manual Start

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run bot
python -m app.bot.run_bot
```

### What Happens in Polling Mode

1. Bot connects to Telegram servers
2. Continuously polls for new updates
3. Processes commands and messages in real-time
4. Logs all activity to console

### Stopping the Bot

Press `Ctrl+C` to gracefully stop the bot.

---

## Production Mode (Webhook)

In production, use **webhook mode** - Telegram sends updates to your server via HTTPS POST requests.

### Prerequisites

1. **HTTPS Domain**: You need a public domain with valid SSL certificate
2. **Public Server**: Your FastAPI server must be accessible from the internet
3. **Webhook URL**: Configure `TELEGRAM_WEBHOOK_URL` in `.env`

### Setup Webhook

#### Option 1: Automatic Setup (Recommended)

Start your FastAPI server, then call the setup endpoint:

```bash
curl -X POST http://localhost:8000/api/webhook/setup
```

Response:
```json
{
  "success": true,
  "message": "Webhook configured successfully",
  "webhook_url": "https://api.yourdomain.com/api/webhook/123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
}
```

#### Option 2: Manual Setup

```python
from app.bot.bot import get_bot
import asyncio

async def setup():
    bot = get_bot()
    await bot.initialize()
    success = await bot.setup_webhook()
    print(f"Webhook setup: {success}")

asyncio.run(setup())
```

### Verify Webhook

Check webhook status:

```bash
curl http://localhost:8000/api/webhook/info
```

Response:
```json
{
  "bot_username": "tfm_bot",
  "bot_id": 123456789,
  "webhook_configured": true,
  "webhook_url": "https://api.yourdomain.com/api/webhook/...",
  "pending_updates": 0
}
```

### Remove Webhook

To switch back to polling mode:

```bash
curl -X POST http://localhost:8000/api/webhook/remove
```

### Webhook Endpoint

The webhook endpoint is automatically registered at:

```
POST /api/webhook/{bot_token}
```

Telegram will send updates to this endpoint. The bot token in the URL provides basic security.

---

## Bot Commands

### User Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Launch the game with welcome message | `/start` |
| `/play` | Quick launch to game | `/play` |
| `/help` | Show help information | `/help` |
| `/stats` | View career statistics | `/stats` |

### Bot Features

1. **Web App Launch**: Inline button to launch the Telegram Web App
2. **Interactive Menus**: Inline keyboard buttons for navigation
3. **Career Stats**: Display user's career statistics (placeholder for now)
4. **Help System**: Comprehensive help information

---

## Testing

### Run Bot Tests

```bash
# Run all bot tests
pytest tests/test_bot.py -v

# Run specific test
pytest tests/test_bot.py::TestBotHandlers::test_start_command -v

# Run with coverage
pytest tests/test_bot.py --cov=app.bot --cov-report=html
```

### Test Coverage

The test suite covers:

- ✅ Command handlers (`/start`, `/help`, `/play`, `/stats`)
- ✅ Callback query handlers (inline buttons)
- ✅ Bot initialization
- ✅ Webhook setup and removal
- ✅ Bot information retrieval
- ✅ Error handling
- ✅ Handler registration

### Manual Testing

1. **Start the bot** in polling mode
2. **Open Telegram** and search for your bot
3. **Send `/start`** - should receive welcome message with Web App button
4. **Send `/help`** - should receive help information
5. **Send `/play`** - should receive quick launch button
6. **Send `/stats`** - should receive placeholder statistics
7. **Click inline buttons** - should navigate between menus

---

## Troubleshooting

### Bot Token Invalid

**Error:** `telegram.error.InvalidToken: Invalid token`

**Solution:**
- Verify `TELEGRAM_BOT_TOKEN` in `.env` is correct
- Check for extra spaces or quotes in the token
- Ensure token is from @BotFather

### Webhook Setup Failed

**Error:** `Failed to setup webhook`

**Solution:**
- Verify `TELEGRAM_WEBHOOK_URL` is a valid HTTPS URL
- Ensure your server is publicly accessible
- Check SSL certificate is valid
- Verify firewall allows incoming HTTPS traffic

### Bot Not Responding

**Polling Mode:**
- Check bot is running (`python -m app.bot.run_bot`)
- Verify no errors in console logs
- Ensure internet connection is stable

**Webhook Mode:**
- Verify webhook is configured: `curl http://localhost:8000/api/webhook/info`
- Check FastAPI server is running
- Review server logs for errors
- Test webhook endpoint manually

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'telegram'`

**Solution:**
```bash
pip install python-telegram-bot==20.8
```

### Database Connection Issues

The bot doesn't require database access for basic commands, but future features will integrate with the Career_Manager module.

---

## Architecture

### Bot Module Structure

```
app/bot/
├── __init__.py          # Module exports
├── bot.py               # TelegramBot class (core bot logic)
├── handlers.py          # Command and callback handlers
├── webhook.py           # Webhook endpoints for FastAPI
└── run_bot.py           # Standalone bot startup script
```

### Integration with FastAPI

The bot integrates with FastAPI through the webhook router:

```python
# app/api/routes/__init__.py
from app.bot.webhook import webhook_router
api_router.include_router(webhook_router)
```

Webhook endpoints:
- `POST /api/webhook/{token}` - Receive updates from Telegram
- `GET /api/webhook/info` - Get webhook status
- `POST /api/webhook/setup` - Configure webhook
- `POST /api/webhook/remove` - Remove webhook

### Bot Lifecycle

**Polling Mode:**
```
Initialize → Remove Webhook → Start Polling → Process Updates → Stop
```

**Webhook Mode:**
```
Initialize → Setup Webhook → Receive POST Requests → Process Updates
```

---

## Next Steps

1. **Integrate with Career_Manager**: Connect `/stats` command to real career data
2. **Add User Authentication**: Link Telegram user ID to game accounts
3. **Implement Notifications**: Send match results, transfer alerts, etc.
4. **Add Admin Commands**: Bot management commands for administrators
5. **Enhance Web App Integration**: Pass user data to Web App via `initData`

---

## Security Considerations

1. **Token Security**: Never commit bot token to version control
2. **Webhook Security**: Bot token in webhook URL provides basic security
3. **Rate Limiting**: Implement rate limiting for bot commands
4. **Input Validation**: Validate all user inputs in handlers
5. **Error Handling**: Never expose internal errors to users

---

## Resources

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Web Apps](https://core.telegram.org/bots/webapps)
- [BotFather Commands](https://core.telegram.org/bots#6-botfather)

---

## Support

For issues or questions:
1. Check this documentation
2. Review bot logs for errors
3. Test with @BotFather's `/mybots` command
4. Verify environment configuration
