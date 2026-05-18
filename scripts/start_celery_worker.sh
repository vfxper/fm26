#!/bin/bash
# Start Celery Worker for Telegram Football Manager

# Exit on error
set -e

echo "Starting Celery Worker..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Set Python path to include app directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Celery worker with configuration
celery -A app.core.celery:celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=matches,updates,ai,default \
    --max-tasks-per-child=1000 \
    --time-limit=300 \
    --soft-time-limit=240

echo "Celery Worker stopped."
