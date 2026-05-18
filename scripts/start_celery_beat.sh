#!/bin/bash
# Start Celery Beat Scheduler for Telegram Football Manager

# Exit on error
set -e

echo "Starting Celery Beat Scheduler..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Set Python path to include app directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Celery beat scheduler
celery -A app.core.celery:celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat:PersistentScheduler

echo "Celery Beat stopped."
