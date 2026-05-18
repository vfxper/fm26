# Telegram Bot Quick Reference

Quick reference for common bot operations.

## Configuration

```bash
# .env file
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_WEBHOOK_URL=https://your-domain.com  # Production only
```

## Start Bot

### Development (Polling)

```bash
# Linux/Mac
./scripts/start_bot.sh

# Windows
scripts\start_bot.bat

# Manual
python -m app.bot.run_bot
```

### Production (Webhook)

```bash
# 1. Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Setup webhook
curl -X POST http://localhost:8000/api/webhook/setup
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Launch game with welcome message |
| `/play` | Quick launch to game |
| `/help` | Show help information |
| `/stats` | View career statistics |

## API Endpoints

```bash
# Get webhook info
GET /api/webhook/info

# Setup webhook
POST /api/webhook/setup

# Remove webhook
POST /api/webhook/remove

# Receive updates (Telegram calls this)
POST /api/webhook/{bot_token}
```

## Testing

```bash
# Run all bot tests
pytest tests/test_bot.py -v

# Run with coverage
pytest tests/test_bot.py --cov=app.bot
```

## Common Operations

### Get Bot Info

```python
from app.bot.bot import get_bot
import asyncio

async def main():
    bot = get_bot()
    await bot.initialize()
    info = await bot.get_bot_info()
    print(info)

asyncio.run(main())
```

### Setup Webhook Programmatically

```python
from app.bot.bot import get_bot
import asyncio

async def main():
    bot = get_bot()
    await bot.initialize()
    success = await bot.setup_webhook()
    print(f"Webhook setup: {success}")

asyncio.run(main())
```

### Remove Webhook

```python
from app.bot.bot import get_bot
import asyncio

async def main():
    bot = get_bot()
    await bot.initialize()
    success = await bot.remove_webhook()
    print(f"Webhook removed: {success}")

asyncio.run(main())
```

## Troubleshooting

### Bot not responding
- Check bot is running
- Verify token in `.env`
- Check logs for errors

### Webhook not working
- Verify HTTPS URL
- Check webhook status: `GET /api/webhook/info`
- Ensure server is publicly accessible

### Import errors
```bash
pip install python-telegram-bot==20.8
```

## File Structure

```
app/bot/
├── __init__.py       # Module exports
├── bot.py            # Core bot class
├── handlers.py       # Command handlers
├── webhook.py        # Webhook endpoints
└── run_bot.py        # Startup script

scripts/
├── start_bot.sh      # Linux/Mac startup
└── start_bot.bat     # Windows startup

tests/
└── test_bot.py       # Bot tests

docs/
├── BOT_SETUP.md      # Full setup guide
└── BOT_QUICK_REFERENCE.md  # This file
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_BOT_USERNAME` | No | Bot username |
| `TELEGRAM_WEBHOOK_URL` | Production | Public HTTPS URL |

## Security Notes

- ✅ Never commit bot token to git
- ✅ Use HTTPS for webhooks
- ✅ Validate all user inputs
- ✅ Implement rate limiting
- ✅ Handle errors gracefully
