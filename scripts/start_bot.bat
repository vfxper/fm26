@echo off
REM Start Telegram Bot in polling mode (development)

echo Starting Telegram Football Manager Bot...
echo Press Ctrl+C to stop
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run bot
python -m app.bot.run_bot

pause
