#!/bin/bash
# PostgreSQL Database Setup Script for Linux/macOS
# This script helps set up the PostgreSQL database for Telegram Football Manager

set -e

echo "============================================================"
echo "PostgreSQL Database Setup for Telegram Football Manager"
echo "============================================================"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed or not in PATH"
    echo ""
    echo "Please install PostgreSQL 15+:"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt install postgresql-15"
    echo ""
    echo "macOS:"
    echo "  brew install postgresql@15"
    echo ""
    exit 1
fi

echo "PostgreSQL found!"
echo ""

# Database configuration
DB_NAME="tfm_db"
DB_USER="tfm_user"
DB_PASSWORD="tfm_password"

echo "Database configuration:"
echo "  Database Name: $DB_NAME"
echo "  Database User: $DB_USER"
echo "  Database Password: $DB_PASSWORD"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    POSTGRES_USER=$(whoami)
    echo "Detected macOS - using user: $POSTGRES_USER"
else
    # Linux
    POSTGRES_USER="postgres"
    echo "Detected Linux - using user: $POSTGRES_USER"
fi

echo ""
echo "Creating database and user..."
echo ""

# Create SQL commands
cat > /tmp/setup_db.sql << EOF
-- Create database user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# Execute SQL commands
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - no sudo needed
    psql -U $POSTGRES_USER postgres -f /tmp/setup_db.sql
else
    # Linux - use sudo
    sudo -u $POSTGRES_USER psql -f /tmp/setup_db.sql
fi

# Grant schema privileges
cat > /tmp/grant_privileges.sql << EOF
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

if [[ "$OSTYPE" == "darwin"* ]]; then
    psql -U $POSTGRES_USER -f /tmp/grant_privileges.sql
else
    sudo -u $POSTGRES_USER psql -f /tmp/grant_privileges.sql
fi

# Clean up SQL files
rm /tmp/setup_db.sql
rm /tmp/grant_privileges.sql

echo ""
echo "============================================================"
echo "Database setup completed successfully!"
echo "============================================================"
echo ""
echo "Database Name: $DB_NAME"
echo "Database User: $DB_USER"
echo "Database Password: $DB_PASSWORD"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the database credentials"
echo "2. Run: python scripts/test_db_connection.py"
echo "3. If test passes, you're ready to start development!"
echo ""
echo "DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
