# Database Quick Reference Guide

Quick reference for common database operations in Telegram Football Manager.

## Connection String Format

```
postgresql+asyncpg://[user]:[password]@[host]:[port]/[database]
```

**Example:**
```
postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
```

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False
```

## Quick Setup Commands

### Create Database and User

```sql
-- Connect as postgres superuser
psql -U postgres

-- Create user and database
CREATE USER tfm_user WITH PASSWORD 'tfm_password';
CREATE DATABASE tfm_db OWNER tfm_user;
GRANT ALL PRIVILEGES ON DATABASE tfm_db TO tfm_user;

-- Connect to database
\c tfm_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO tfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tfm_user;
```

### Test Connection

```bash
# Run test script
python scripts/test_db_connection.py

# Or use psql
psql -U tfm_user -d tfm_db -h localhost
```

## Using Database in Code

### Get Database Session (Dependency Injection)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session

@app.get("/example")
async def example_endpoint(db: AsyncSession = Depends(get_db_session)):
    # Use db session here
    result = await db.execute(text("SELECT 1"))
    return {"result": result.scalar()}
```

### Direct Database Access

```python
from app.core.database import get_engine, get_session_factory
from sqlalchemy import text

# Get engine
engine = get_engine()

# Get session factory
session_factory = get_session_factory()

# Use session
async with session_factory() as session:
    result = await session.execute(text("SELECT 1"))
    row = await result.fetchone()
    await session.commit()
```

### Query Examples

```python
from sqlalchemy import select, insert, update, delete
from app.models import Player  # Example model

# SELECT
async with session_factory() as session:
    # Select all
    result = await session.execute(select(Player))
    players = result.scalars().all()
    
    # Select with filter
    result = await session.execute(
        select(Player).where(Player.position == "ST")
    )
    strikers = result.scalars().all()
    
    # Select one
    result = await session.execute(
        select(Player).where(Player.id == 1)
    )
    player = result.scalar_one_or_none()

# INSERT
async with session_factory() as session:
    new_player = Player(name="Test Player", position="ST", ca=150)
    session.add(new_player)
    await session.commit()
    await session.refresh(new_player)  # Get ID

# UPDATE
async with session_factory() as session:
    result = await session.execute(
        select(Player).where(Player.id == 1)
    )
    player = result.scalar_one()
    player.ca = 160
    await session.commit()

# DELETE
async with session_factory() as session:
    result = await session.execute(
        select(Player).where(Player.id == 1)
    )
    player = result.scalar_one()
    await session.delete(player)
    await session.commit()
```

### Transaction Handling

```python
async with session_factory() as session:
    try:
        # Multiple operations
        player1 = Player(name="Player 1", position="ST")
        player2 = Player(name="Player 2", position="GK")
        
        session.add(player1)
        session.add(player2)
        
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
```

## Health Check

### Check Database Health

```python
from app.core.database import check_db_health

is_healthy = await check_db_health()
if is_healthy:
    print("Database is healthy")
else:
    print("Database is unhealthy")
```

### Health Endpoint

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Telegram Football Manager",
  "version": "0.1.0",
  "database": "healthy",
  "cache": "healthy"
}
```

## Common psql Commands

```bash
# Connect to database
psql -U tfm_user -d tfm_db -h localhost

# List databases
\l

# Connect to database
\c tfm_db

# List tables
\dt

# Describe table
\d table_name

# List all schemas
\dn

# List all users
\du

# Show current user
SELECT current_user;

# Show current database
SELECT current_database();

# Show PostgreSQL version
SELECT version();

# Exit
\q
```

## Monitoring Queries

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('tfm_db'));

-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;

-- Active queries
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active';

-- Long-running queries
SELECT 
    pid,
    now() - query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;

-- Kill a query
SELECT pg_terminate_backend(pid);
```

## Backup and Restore

```bash
# Backup
pg_dump -U tfm_user -d tfm_db -F c -f backup_$(date +%Y%m%d).dump

# Restore
pg_restore -U tfm_user -d tfm_db -c backup_20240101.dump

# Backup as SQL
pg_dump -U tfm_user -d tfm_db > backup.sql

# Restore from SQL
psql -U tfm_user -d tfm_db < backup.sql
```

## Testing

```bash
# Run all database tests
pytest tests/test_database.py -v

# Run specific test
pytest tests/test_database.py::test_database_connection -v

# Run with coverage
pytest tests/test_database.py --cov=app.core.database

# Run connection test script
python scripts/test_db_connection.py
```

## Troubleshooting

### Connection Issues

```bash
# Check if PostgreSQL is running
# Windows
sc query postgresql-x64-15

# Linux
sudo systemctl status postgresql

# macOS
brew services list | grep postgresql

# Check port
netstat -an | grep 5432  # Windows/Linux
lsof -i :5432            # macOS
```

### Reset Database

```sql
-- Connect as postgres
psql -U postgres

-- Drop and recreate
DROP DATABASE IF EXISTS tfm_db;
CREATE DATABASE tfm_db OWNER tfm_user;

-- Reconnect and grant privileges
\c tfm_db
GRANT ALL ON SCHEMA public TO tfm_user;
```

### Clear All Tables

```sql
-- Connect to database
\c tfm_db

-- Drop all tables
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO tfm_user;
```

## Performance Tips

1. **Use Connection Pooling**: Already configured (pool_size=20)
2. **Use Indexes**: Create indexes on frequently queried columns
3. **Use EXPLAIN**: Analyze query performance
   ```sql
   EXPLAIN ANALYZE SELECT * FROM players WHERE position = 'ST';
   ```
4. **Batch Operations**: Use bulk inserts for multiple records
5. **Avoid N+1 Queries**: Use joins or eager loading
6. **Use JSONB**: For flexible player attributes (faster than JSON)

## Configuration Files

- **Database Config**: `app/core/config.py`
- **Database Module**: `app/core/database.py`
- **Environment**: `.env` (copy from `.env.example`)
- **Tests**: `tests/test_database.py`
- **Test Config**: `tests/conftest.py`

## Useful Links

- [PostgreSQL 15 Docs](https://www.postgresql.org/docs/15/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [asyncpg Docs](https://magicstack.github.io/asyncpg/)
- [FastAPI Database Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## Support

For detailed setup instructions, see:
- `docs/DATABASE_SETUP.md` - Complete setup guide
- `SETUP_INSTRUCTIONS.md` - Project setup instructions
- `.kiro/specs/telegram-football-manager/design.md` - Database architecture
