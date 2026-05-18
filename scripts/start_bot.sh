#!/bin/bash
# Start Telegram Bot in polling mode (development)

echo "Starting Telegram Football Manager Bot..."
echo "Press Ctrl+C to stop"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run bot
python -m app.bot.run_bot
