# PostgreSQL Database Setup Guide

This guide covers the setup and configuration of PostgreSQL 15+ for the Telegram Football Manager project.

## Prerequisites

- PostgreSQL 15 or higher
- Python 3.11+
- asyncpg driver (included in requirements.txt)

## Installation

### Windows

1. **Download PostgreSQL**:
   - Visit https://www.postgresql.org/download/windows/
   - Download PostgreSQL 15 or higher installer
   - Run the installer and follow the setup wizard

2. **During Installation**:
   - Set a password for the `postgres` superuser (remember this!)
   - Default port: 5432
   - Default locale: Use your system locale
   - Install pgAdmin 4 (optional but recommended for GUI management)

3. **Verify Installation**:
   ```bash
   psql --version
   ```

### Linux (Ubuntu/Debian)

```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update and install
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
```

### macOS

```bash
# Using Homebrew
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Verify installation
psql --version
```

## Database Configuration

### 1. Create Database and User

Connect to PostgreSQL as the superuser:

```bash
# Windows (using Command Prompt or PowerShell)
psql -U postgres

# Linux/macOS
sudo -u postgres psql
```

Execute the following SQL commands:

```sql
-- Create database user
CREATE USER tfm_user WITH PASSWORD 'tfm_password';

-- Create database
CREATE DATABASE tfm_db OWNER tfm_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tfm_db TO tfm_user;

-- Connect to the database
\c tfm_db

-- Grant schema privileges (PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO tfm_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tfm_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tfm_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tfm_user;

-- Exit psql
\q
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update the database configuration:

```bash
cp .env.example .env
```

Edit `.env` and set the database URL:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False
```

**Database URL Format**:
```
postgresql+asyncpg://[user]:[password]@[host]:[port]/[database]
```

- `postgresql+asyncpg`: SQLAlchemy dialect + async driver
- `user`: Database user (e.g., `tfm_user`)
- `password`: User password (e.g., `tfm_password`)
- `host`: Database host (e.g., `localhost`)
- `port`: Database port (default: `5432`)
- `database`: Database name (e.g., `tfm_db`)

### 3. Test Database Connection

Run the database connection test script:

```bash
python scripts/test_db_connection.py
```

Expected output:
```
============================================================
PostgreSQL Database Connection Test
============================================================

Database URL: ***@localhost:5432/tfm_db
Pool Size: 20
Max Overflow: 10

Test 1: Creating database engine...
✓ Engine created successfully

Test 2: Testing database connection...
✓ Database connection successful

Test 3: Checking PostgreSQL version...
✓ PostgreSQL version: PostgreSQL 15.x ...

Test 4: Checking current database...
✓ Connected to database: tfm_db

Test 5: Checking user permissions...
✓ Connected as user: tfm_user

Test 6: Testing session factory...
✓ Session factory working correctly

Test 7: Checking for existing tables...
✓ No tables found (database is empty - this is expected for initial setup)

Test 8: Testing transaction handling...
✓ Transaction handling working correctly

============================================================
✓ All database connection tests passed!
============================================================

Database is properly configured and ready to use.
```

## Database Architecture

### Connection Pooling

The application uses SQLAlchemy's async connection pooling:

- **Pool Size**: 20 connections (configurable via `DATABASE_POOL_SIZE`)
- **Max Overflow**: 10 additional connections (configurable via `DATABASE_MAX_OVERFLOW`)
- **Pool Class**: 
  - Production: `AsyncAdaptedQueuePool` (persistent connections)
  - Development: `NullPool` (no pooling for easier debugging)

### Async Support

The application uses:
- **SQLAlchemy 2.0** with async support
- **asyncpg** driver for PostgreSQL (faster than psycopg2)
- **AsyncSession** for all database operations

## Common Operations

### Check Database Status

```bash
# Check if PostgreSQL is running (Windows)
sc query postgresql-x64-15

# Check if PostgreSQL is running (Linux)
sudo systemctl status postgresql

# Check if PostgreSQL is running (macOS)
brew services list | grep postgresql
```

### Connect to Database

```bash
# Using psql
psql -U tfm_user -d tfm_db -h localhost

# List all databases
\l

# List all tables in current database
\dt

# Describe a table
\d table_name

# Exit psql
\q
```

### Backup and Restore

```bash
# Backup database
pg_dump -U tfm_user -d tfm_db -F c -f tfm_backup.dump

# Restore database
pg_restore -U tfm_user -d tfm_db -c tfm_backup.dump
```

### Reset Database

```bash
# Connect as superuser
psql -U postgres

# Drop and recreate database
DROP DATABASE IF EXISTS tfm_db;
CREATE DATABASE tfm_db OWNER tfm_user;
\q
```

## Troubleshooting

### Connection Refused

**Error**: `could not connect to server: Connection refused`

**Solutions**:
1. Check if PostgreSQL is running:
   ```bash
   # Windows
   sc query postgresql-x64-15
   
   # Linux
   sudo systemctl status postgresql
   
   # macOS
   brew services list
   ```

2. Start PostgreSQL if not running:
   ```bash
   # Windows (as Administrator)
   net start postgresql-x64-15
   
   # Linux
   sudo systemctl start postgresql
   
   # macOS
   brew services start postgresql@15
   ```

3. Check PostgreSQL is listening on the correct port:
   ```bash
   # Linux/macOS
   sudo netstat -plnt | grep 5432
   
   # Windows
   netstat -an | findstr 5432
   ```

### Authentication Failed

**Error**: `FATAL: password authentication failed for user "tfm_user"`

**Solutions**:
1. Verify credentials in `.env` file
2. Reset user password:
   ```sql
   psql -U postgres
   ALTER USER tfm_user WITH PASSWORD 'new_password';
   \q
   ```
3. Check `pg_hba.conf` authentication method (should be `md5` or `scram-sha-256`)

### Database Does Not Exist

**Error**: `FATAL: database "tfm_db" does not exist`

**Solution**:
```bash
psql -U postgres
CREATE DATABASE tfm_db OWNER tfm_user;
\q
```

### Permission Denied

**Error**: `permission denied for schema public`

**Solution**:
```sql
psql -U postgres -d tfm_db
GRANT ALL ON SCHEMA public TO tfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tfm_user;
\q
```

### asyncpg Not Installed

**Error**: `No module named 'asyncpg'`

**Solution**:
```bash
pip install asyncpg
# or
pip install -r requirements.txt
```

## Performance Tuning

### PostgreSQL Configuration

Edit `postgresql.conf` (location varies by OS):

```conf
# Connection Settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

Restart PostgreSQL after changes:
```bash
# Windows (as Administrator)
net stop postgresql-x64-15
net start postgresql-x64-15

# Linux
sudo systemctl restart postgresql

# macOS
brew services restart postgresql@15
```

### Monitoring

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check database size
SELECT pg_size_pretty(pg_database_size('tfm_db'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check slow queries
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
ORDER BY duration DESC;
```

## Next Steps

After successful database setup:

1. **Initialize Database Schema**: Run Alembic migrations (Task 2.17)
2. **Load Player Data**: Import `2600球员属性.csv` (Task 3)
3. **Run Application**: Start the FastAPI server
4. **Verify Health**: Check `/health` endpoint

## References

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/15/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
