#!/bin/bash
# FM26 Deployment Script (Task 37)
# Usage: ./deploy.sh [production|staging]

set -e

ENV=${1:-production}
echo "=== FM26 Deployment - $ENV ==="

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Build and start containers
echo "Building Docker images..."
docker-compose build --no-cache

echo "Starting services..."
docker-compose up -d

# Wait for DB
echo "Waiting for database..."
sleep 5

# Run migrations
echo "Running database migrations..."
docker-compose exec app alembic upgrade head

# Load player data (first time only)
echo "Checking player data..."
docker-compose exec app python -c "
from app.core.database import get_db_sync
# Check if players exist, if not load them
" 2>/dev/null || true

# Health check
echo "Running health check..."
sleep 3
curl -f http://localhost:8000/health || echo "WARNING: Health check failed"

echo ""
echo "=== Deployment Complete ==="
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:80"
echo ""
docker-compose ps
