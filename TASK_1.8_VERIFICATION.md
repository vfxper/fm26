# Task 1.8 Verification Guide

This guide helps verify that the Telegram Bot configuration is working correctly.

## Prerequisites Verification

### 1. Check Dependencies

```bash
# Verify python-telegram-bot is installed
pip list | grep python-telegram-bot
# Expected: python-telegram-bot    20.8
```

### 2. Check Configuration Files

```bash
# Verify bot module exists
ls -la app/bot/
# Expected files:
# - __init__.py
# - bot.py
# - handlers.py
# - webhook.py
# - run_bot.py

# Verify scripts exist
ls -la scripts/start_bot.*
# Expected files:
# - start_bot.sh
# - start_bot.bat

# Verify tests exist
ls -la tests/test_bot.py
# Expected: test_bot.py exists

# Verify documentation exists
ls -la docs/BOT_*.md
# Expected files:
# - BOT_SETUP.md
# - BOT_QUICK_REFERENCE.md
```

### 3. Check Environment Configuration

```bash
# Check .env.example has bot configuration
grep TELEGRAM_BOT .env.example
# Expected output:
# TELEGRAM_BOT_TOKEN=your_bot_token_here
# TELEGRAM_BOT_USERNAME=your_bot_username
# TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
```

## Code Verification

### 1. Import Tests

```python
# Test imports work correctly
python -c "from app.bot import TelegramBot, setup_handlers; print('✅ Imports OK')"

# Test bot module
python -c "from app.bot.bot import get_bot; print('✅ Bot module OK')"

# Test handlers module
python -c "from app.bot.handlers import start_command, help_command; print('✅ Handlers OK')"

# Test webhook module
python -c "from app.bot.webhook import webhook_router; print('✅ Webhook OK')"
```

### 2. Syntax Verification

```bash
# Check for syntax errors
python -m py_compile app/bot/bot.py
python -m py_compile app/bot/handlers.py
python -m py_compile app/bot/webhook.py
python -m py_compile app/bot/run_bot.py
python -m py_compile tests/test_bot.py

# If no output, syntax is correct
```

### 3. Static Analysis

```bash
# Run flake8 (if available)
flake8 app/bot/ --max-line-length=120

# Run mypy (if available)
mypy app/bot/ --ignore-missing-imports
```

## Unit Tests Verification

### 1. Run All Bot Tests

```bash
# Run all tests
pytest tests/test_bot.py -v

# Expected output:
# tests/test_bot.py::TestBotHandlers::test_start_command PASSED
# tests/test_bot.py::TestBotHandlers::test_help_command PASSED
# tests/test_bot.py::TestBotHandlers::test_play_command PASSED
# tests/test_bot.py::TestBotHandlers::test_stats_command PASSED
# tests/test_bot.py::TestBotHandlers::test_button_callback_help PASSED
# tests/test_bot.py::TestBotHandlers::test_button_callback_stats PASSED
# tests/test_bot.py::TestBotHandlers::test_button_callback_back_to_menu PASSED
# tests/test_bot.py::TestTelegramBot::test_bot_initialization_without_token PASSED
# tests/test_bot.py::TestTelegramBot::test_bot_initialization_with_token PASSED
# tests/test_bot.py::TestTelegramBot::test_get_bot_singleton PASSED
# tests/test_bot.py::TestTelegramBot::test_bot_initialize PASSED
# tests/test_bot.py::TestTelegramBot::test_bot_initialize_idempotent PASSED
# tests/test_bot.py::TestTelegramBot::test_setup_webhook_without_url PASSED
# tests/test_bot.py::TestTelegramBot::test_setup_webhook_with_url PASSED
# tests/test_bot.py::TestTelegramBot::test_remove_webhook PASSED
# tests/test_bot.py::TestTelegramBot::test_get_bot_info PASSED
# tests/test_bot.py::TestHandlerSetup::test_setup_handlers PASSED
#
# ==================== 20 passed in X.XXs ====================
```

### 2. Run Tests with Coverage

```bash
# Generate coverage report
pytest tests/test_bot.py --cov=app.bot --cov-report=term-missing

# Expected coverage:
# app/bot/__init__.py          100%
# app/bot/bot.py               >80%
# app/bot/handlers.py          >80%
# app/bot/webhook.py           >70%
# app/bot/run_bot.py           >50%
```

### 3. Run Specific Test Categories

```bash
# Test handlers only
pytest tests/test_bot.py::TestBotHandlers -v

# Test bot class only
pytest tests/test_bot.py::TestTelegramBot -v

# Test handler setup only
pytest tests/test_bot.py::TestHandlerSetup -v
```

## Integration Verification

### 1. Check FastAPI Integration

```python
# Verify webhook router is registered
python -c "
from app.api.routes import api_router
routes = [route.path for route in api_router.routes]
webhook_routes = [r for r in routes if 'webhook' in r]
print('Webhook routes:', webhook_routes)
assert len(webhook_routes) > 0, 'No webhook routes found'
print('✅ FastAPI integration OK')
"
```

### 2. Check Configuration Integration

```python
# Verify settings are accessible
python -c "
from app.core.config import settings
assert hasattr(settings, 'TELEGRAM_BOT_TOKEN'), 'Missing TELEGRAM_BOT_TOKEN'
assert hasattr(settings, 'TELEGRAM_BOT_USERNAME'), 'Missing TELEGRAM_BOT_USERNAME'
assert hasattr(settings, 'TELEGRAM_WEBHOOK_URL'), 'Missing TELEGRAM_WEBHOOK_URL'
print('✅ Configuration integration OK')
"
```

## Manual Testing (Requires Bot Token)

### 1. Setup Test Environment

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your bot token
# TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 2. Test Bot Initialization

```python
# Test bot can initialize
python -c "
import asyncio
from app.bot.bot import get_bot

async def test():
    bot = get_bot()
    await bot.initialize()
    info = await bot.get_bot_info()
    print(f'✅ Bot initialized: @{info[\"username\"]}')
    await bot.stop()

asyncio.run(test())
"
```

### 3. Test Polling Mode (Development)

```bash
# Start bot in polling mode
python -m app.bot.run_bot

# Expected output:
# INFO - Starting Telegram Football Manager Bot...
# INFO - Bot Info: @your_bot_username (ID: 123456789)
# INFO - Webhook: Not configured
# INFO - Starting polling mode (press Ctrl+C to stop)...
# INFO - Bot polling started successfully

# In Telegram:
# 1. Search for your bot
# 2. Send /start
# 3. Should receive welcome message with Web App button
# 4. Send /help
# 5. Should receive help information
# 6. Send /play
# 7. Should receive quick launch button
# 8. Send /stats
# 9. Should receive statistics (placeholder)

# Stop bot with Ctrl+C
```

### 4. Test Webhook Mode (Production)

```bash
# 1. Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. In another terminal, setup webhook
curl -X POST http://localhost:8000/api/webhook/setup

# Expected response:
# {
#   "success": true,
#   "message": "Webhook configured successfully",
#   "webhook_url": "https://your-domain.com/api/webhook/..."
# }

# 3. Check webhook info
curl http://localhost:8000/api/webhook/info

# Expected response:
# {
#   "bot_username": "your_bot_username",
#   "bot_id": 123456789,
#   "webhook_configured": true,
#   "webhook_url": "https://...",
#   "pending_updates": 0
# }

# 4. Test bot in Telegram (same as polling mode)

# 5. Remove webhook when done
curl -X POST http://localhost:8000/api/webhook/remove
```

## Documentation Verification

### 1. Check Documentation Completeness

```bash
# Verify BOT_SETUP.md exists and has content
wc -l docs/BOT_SETUP.md
# Expected: >400 lines

# Verify BOT_QUICK_REFERENCE.md exists
wc -l docs/BOT_QUICK_REFERENCE.md
# Expected: >100 lines

# Check documentation sections
grep "^##" docs/BOT_SETUP.md
# Expected sections:
# - Prerequisites
# - Bot Configuration
# - Development Mode
# - Production Mode
# - Bot Commands
# - Testing
# - Troubleshooting
```

### 2. Verify Code Examples in Documentation

```bash
# Extract and test code examples from documentation
# (Manual verification recommended)
```

## Checklist

Use this checklist to verify all requirements:

### Module Structure
- [ ] `app/bot/__init__.py` exists and exports correctly
- [ ] `app/bot/bot.py` exists with TelegramBot class
- [ ] `app/bot/handlers.py` exists with command handlers
- [ ] `app/bot/webhook.py` exists with FastAPI endpoints
- [ ] `app/bot/run_bot.py` exists as startup script

### Command Handlers
- [ ] `/start` command implemented
- [ ] `/help` command implemented
- [ ] `/play` command implemented
- [ ] `/stats` command implemented (placeholder)
- [ ] Callback query handlers implemented
- [ ] Error handler implemented

### Web App Integration
- [ ] Web App button in `/start` command
- [ ] Web App button in `/play` command
- [ ] WebAppInfo configured with correct URL
- [ ] Inline keyboard markup working

### Configuration
- [ ] `TELEGRAM_BOT_TOKEN` in config.py
- [ ] `TELEGRAM_BOT_USERNAME` in config.py
- [ ] `TELEGRAM_WEBHOOK_URL` in config.py
- [ ] All settings in .env.example

### Bot Initialization
- [ ] Bot class initializes correctly
- [ ] Webhook setup works
- [ ] Webhook removal works
- [ ] Polling mode works
- [ ] Bot info retrieval works

### Startup Scripts
- [ ] `scripts/start_bot.sh` exists and is executable
- [ ] `scripts/start_bot.bat` exists
- [ ] Scripts activate virtual environment
- [ ] Scripts run bot correctly

### Unit Tests
- [ ] `tests/test_bot.py` exists
- [ ] All handler tests pass
- [ ] All bot class tests pass
- [ ] Handler setup tests pass
- [ ] Test coverage >70%

### Documentation
- [ ] `docs/BOT_SETUP.md` exists and is comprehensive
- [ ] `docs/BOT_QUICK_REFERENCE.md` exists
- [ ] Documentation covers all features
- [ ] Examples are correct and working
- [ ] Troubleshooting section included

### Integration
- [ ] Webhook router registered in FastAPI
- [ ] Bot imports work correctly
- [ ] No circular dependencies
- [ ] No syntax errors
- [ ] No import errors

## Common Issues and Solutions

### Issue: Bot token not configured
**Solution:** Add `TELEGRAM_BOT_TOKEN` to `.env` file

### Issue: Import errors
**Solution:** Install dependencies: `pip install python-telegram-bot==20.8`

### Issue: Tests fail
**Solution:** Check Python version (3.11+) and pytest installation

### Issue: Webhook setup fails
**Solution:** Verify `TELEGRAM_WEBHOOK_URL` is a valid HTTPS URL

### Issue: Bot not responding
**Solution:** Check bot is running and token is correct

## Success Criteria

All of the following should be true:

✅ All files created as specified
✅ No syntax errors in any file
✅ All imports work correctly
✅ All unit tests pass (20/20)
✅ Test coverage >70%
✅ Documentation is comprehensive
✅ Bot can initialize with valid token
✅ Command handlers work correctly
✅ Webhook endpoints are registered
✅ Scripts are executable and work

## Conclusion

If all verification steps pass, Task 1.8 is successfully completed and the Telegram Bot is ready for use.
