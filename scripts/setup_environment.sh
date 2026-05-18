#!/bin/bash
# Environment Setup Script for Linux/macOS
# This script helps set up the appropriate environment for Telegram Football Manager

set -e

echo "============================================================"
echo "Telegram Football Manager - Environment Setup"
echo "============================================================"
echo ""

# Function to display usage
usage() {
    echo "Usage: $0 [development|staging|production]"
    echo ""
    echo "Examples:"
    echo "  $0 development    # Set up development environment"
    echo "  $0 staging        # Set up staging environment"
    echo "  $0 production     # Set up production environment"
    echo ""
    exit 1
}

# Check if environment argument is provided
if [ $# -eq 0 ]; then
    echo "ERROR: No environment specified"
    echo ""
    usage
fi

ENVIRONMENT=$1

# Validate environment
if [ "$ENVIRONMENT" != "development" ] && [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo "ERROR: Invalid environment '$ENVIRONMENT'"
    echo "Valid environments: development, staging, production"
    echo ""
    usage
fi

echo "Setting up $ENVIRONMENT environment..."
echo ""

# Check if environment file exists
ENV_FILE=".env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file '$ENV_FILE' not found"
    echo ""
    exit 1
fi

# Backup existing .env if it exists
if [ -f ".env" ]; then
    BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up existing .env to $BACKUP_FILE"
    cp .env "$BACKUP_FILE"
    echo ""
fi

# Copy environment-specific file to .env
echo "Copying $ENV_FILE to .env"
cp "$ENV_FILE" .env
echo ""

# Display environment configuration
echo "============================================================"
echo "Environment Configuration"
echo "============================================================"
echo ""
echo "Environment: $ENVIRONMENT"
echo ""

# Extract key configuration values
if command -v grep &> /dev/null; then
    echo "Key Settings:"
    grep "^ENVIRONMENT=" .env || true
    grep "^DEBUG=" .env || true
    grep "^API_PORT=" .env || true
    grep "^LOG_LEVEL=" .env || true
    grep "^RATE_LIMIT_ENABLED=" .env || true
    echo ""
fi

# Environment-specific instructions
case $ENVIRONMENT in
    development)
        echo "Development Environment Setup Complete!"
        echo ""
        echo "Next steps:"
        echo "1. Ensure PostgreSQL is running (default: localhost:5432)"
        echo "2. Ensure Redis is running (default: localhost:6379)"
        echo "3. Create development database:"
        echo "   ./scripts/setup_database.sh"
        echo "4. Start the development server:"
        echo "   python app/main.py"
        echo "   or"
        echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        echo ""
        echo "Development features enabled:"
        echo "  - Debug mode: ON"
        echo "  - Database echo: ON"
        echo "  - Auto-reload: ON"
        echo "  - Rate limiting: OFF"
        echo "  - Verbose logging: DEBUG level"
        echo ""
        ;;
    staging)
        echo "Staging Environment Setup Complete!"
        echo ""
        echo "IMPORTANT: Update the following in .env before deploying:"
        echo "  - DATABASE_URL (staging database credentials)"
        echo "  - REDIS_URL (staging Redis host)"
        echo "  - TELEGRAM_BOT_TOKEN (staging bot token)"
        echo "  - SECRET_KEY (generate strong random key)"
        echo "  - TELEGRAM_WEBHOOK_URL (staging domain)"
        echo "  - CORS_ORIGINS (staging domain)"
        echo ""
        echo "Next steps:"
        echo "1. Update .env with staging credentials"
        echo "2. Run database migrations:"
        echo "   alembic upgrade head"
        echo "3. Start the application:"
        echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"
        echo "4. Configure reverse proxy (Nginx) for HTTPS"
        echo "5. Set up Telegram webhook"
        echo ""
        echo "Staging features:"
        echo "  - Debug mode: OFF"
        echo "  - Rate limiting: MODERATE (120/min)"
        echo "  - Logging: INFO level"
        echo "  - Monitoring: ENABLED"
        echo ""
        ;;
    production)
        echo "Production Environment Setup Complete!"
        echo ""
        echo "⚠️  CRITICAL: Update the following in .env before deploying:"
        echo "  - DATABASE_URL (production database with strong password)"
        echo "  - REDIS_URL (production Redis host)"
        echo "  - TELEGRAM_BOT_TOKEN (production bot token)"
        echo "  - SECRET_KEY (MUST be strong random key, min 32 chars)"
        echo "  - TELEGRAM_WEBHOOK_URL (production domain)"
        echo "  - CORS_ORIGINS (production domain only)"
        echo ""
        echo "Security checklist:"
        echo "  ✓ Use strong database passwords"
        echo "  ✓ Enable SSL/TLS for all connections"
        echo "  ✓ Configure firewall rules"
        echo "  ✓ Set up automated backups"
        echo "  ✓ Enable monitoring and alerting"
        echo "  ✓ Review CORS settings"
        echo "  ✓ Test rate limiting"
        echo ""
        echo "Next steps:"
        echo "1. Update .env with production credentials"
        echo "2. Run database migrations:"
        echo "   alembic upgrade head"
        echo "3. Load player database:"
        echo "   python scripts/load_players.py"
        echo "4. Start the application with multiple workers:"
        echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
        echo "5. Configure reverse proxy (Nginx) with SSL"
        echo "6. Set up Telegram webhook"
        echo "7. Configure monitoring (Prometheus/Grafana)"
        echo "8. Set up log aggregation"
        echo ""
        echo "Production features:"
        echo "  - Debug mode: OFF"
        echo "  - Rate limiting: STRICT (60/min)"
        echo "  - Logging: WARNING level"
        echo "  - Monitoring: ENABLED"
        echo "  - Multiple workers: 4"
        echo ""
        ;;
esac

echo "============================================================"
echo ""
echo "To verify your environment setup, run:"
echo "  python scripts/verify_environment.py"
echo ""

