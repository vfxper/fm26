# Database Migration Guide

This guide explains how to use Alembic for database migrations in the Telegram Football Manager project.

## Overview

The project uses **Alembic** for database schema migrations with **async SQLAlchemy 2.0** and **PostgreSQL**. All database models are defined in `app/models/` and migrations are stored in `alembic/versions/`.

## Prerequisites

- PostgreSQL database running and accessible
- Database connection configured in `.env` file
- Alembic installed (included in `requirements.txt`)

## Configuration

### Database Connection

The database URL is configured in your `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
```

### Alembic Configuration

- **alembic.ini**: Main configuration file
- **alembic/env.py**: Environment configuration for async SQLAlchemy
- **alembic/versions/**: Directory containing migration files

The configuration is set up to:
- Use async SQLAlchemy engine
- Load database URL from environment variables
- Import all models automatically
- Format migration files with Black
- Use timestamped migration filenames

## Common Migration Commands

### 1. Create a New Migration

**Auto-generate migration from model changes:**

```bash
python -m alembic revision --autogenerate -m "Description of changes"
```

**Create empty migration (for manual changes):**

```bash
python -m alembic revision -m "Description of changes"
```

### 2. Apply Migrations

**Upgrade to latest version:**

```bash
python -m alembic upgrade head
```

**Upgrade to specific revision:**

```bash
python -m alembic upgrade <revision_id>
```

**Upgrade by one revision:**

```bash
python -m alembic upgrade +1
```

### 3. Downgrade Migrations

**Downgrade by one revision:**

```bash
python -m alembic downgrade -1
```

**Downgrade to specific revision:**

```bash
python -m alembic downgrade <revision_id>
```

**Downgrade all migrations:**

```bash
python -m alembic downgrade base
```

### 4. View Migration History

**Show current revision:**

```bash
python -m alembic current
```

**Show migration history:**

```bash
python -m alembic history
```

**Show migration history with details:**

```bash
python -m alembic history --verbose
```

### 5. Other Useful Commands

**Show SQL without executing:**

```bash
python -m alembic upgrade head --sql
```

**Stamp database with specific revision (without running migrations):**

```bash
python -m alembic stamp <revision_id>
```

## Migration Workflow

### Initial Setup (First Time)

1. **Ensure database is running:**
   ```bash
   # Check database connection
   python scripts/test_db_connection.py
   ```

2. **Create initial migration:**
   ```bash
   python -m alembic revision --autogenerate -m "Initial migration with all models"
   ```

3. **Review the generated migration file** in `alembic/versions/`

4. **Apply the migration:**
   ```bash
   python -m alembic upgrade head
   ```

### Making Schema Changes

1. **Modify your models** in `app/models/`

2. **Generate migration:**
   ```bash
   python -m alembic revision --autogenerate -m "Add new field to User model"
   ```

3. **Review the generated migration:**
   - Check `alembic/versions/<timestamp>_<slug>.py`
   - Verify upgrade() and downgrade() functions
   - Make manual adjustments if needed

4. **Test the migration:**
   ```bash
   # Apply migration
   python -m alembic upgrade head
   
   # Test rollback
   python -m alembic downgrade -1
   
   # Re-apply
   python -m alembic upgrade head
   ```

5. **Commit the migration file** to version control

## Database Models

The following models are included in the initial migration:

### Core Models
- **User**: Telegram users
- **Player**: Football players from CSV database (50+ attributes)
- **Club**: Football clubs with infrastructure and finances
- **Career**: Single-club career mode saves

### Game Models
- **SquadPlayer**: Players in club squads
- **Match**: Match records
- **MatchEvent**: Events during matches
- **Transfer**: Player transfers
- **Injury**: Player injuries
- **Staff**: Club staff members

### Management Models
- **TrainingSchedule**: Training schedules
- **ScoutingAssignment**: Scouting assignments
- **MediaEvent**: Media events and press conferences

### Competition Models
- **Competition**: Competitions and leagues
- **Fixture**: Match fixtures

## Migration File Structure

Each migration file contains:

```python
"""Description of migration

Revision ID: <unique_id>
Revises: <previous_revision_id>
Create Date: <timestamp>
"""

def upgrade() -> None:
    """Apply migration changes"""
    # SQL operations to apply changes
    pass

def downgrade() -> None:
    """Revert migration changes"""
    # SQL operations to revert changes
    pass
```

## Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's autogenerate is powerful but not perfect. Always review:
- Column type changes
- Index creation/deletion
- Constraint modifications
- Data migrations

### 2. Test Migrations Thoroughly

```bash
# Test upgrade
python -m alembic upgrade head

# Test downgrade
python -m alembic downgrade -1

# Test re-upgrade
python -m alembic upgrade head
```

### 3. Use Descriptive Migration Messages

```bash
# Good
python -m alembic revision --autogenerate -m "Add email field to User model"

# Bad
python -m alembic revision --autogenerate -m "Update"
```

### 4. Handle Data Migrations Carefully

For data migrations, create manual migrations:

```python
def upgrade() -> None:
    # Schema change
    op.add_column('users', sa.Column('status', sa.String(20)))
    
    # Data migration
    op.execute("UPDATE users SET status = 'active' WHERE last_login_at IS NOT NULL")
    op.execute("UPDATE users SET status = 'inactive' WHERE last_login_at IS NULL")
    
    # Make column non-nullable after data migration
    op.alter_column('users', 'status', nullable=False)
```

### 5. Keep Migrations Small and Focused

Create separate migrations for:
- Schema changes
- Data migrations
- Index additions
- Constraint modifications

### 6. Never Modify Applied Migrations

Once a migration is applied to production:
- Never modify it
- Create a new migration to fix issues
- Use `alembic downgrade` only in development

## Troubleshooting

### Migration Conflicts

If you have migration conflicts:

```bash
# Check current state
python -m alembic current

# View history
python -m alembic history

# Merge branches (if needed)
python -m alembic merge <rev1> <rev2> -m "Merge migrations"
```

### Database Out of Sync

If database is out of sync with migrations:

```bash
# Check current database revision
python -m alembic current

# Stamp database with correct revision (use carefully!)
python -m alembic stamp head
```

### Autogenerate Not Detecting Changes

Ensure:
1. All models are imported in `alembic/env.py`
2. Models inherit from `Base`
3. Database connection is working
4. You're using the correct database

### Connection Issues

If you get connection errors:

1. **Check database is running:**
   ```bash
   python scripts/test_db_connection.py
   ```

2. **Verify DATABASE_URL in .env:**
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
   ```

3. **Check PostgreSQL service:**
   ```bash
   # Windows
   sc query postgresql-x64-14
   
   # Linux/Mac
   sudo systemctl status postgresql
   ```

## Advanced Topics

### Multiple Database Support

For multiple databases, create separate Alembic configurations:

```bash
alembic init alembic_db1
alembic init alembic_db2
```

### Custom Migration Templates

Modify `alembic/script.py.mako` to customize migration file templates.

### Offline Migrations

Generate SQL without database connection:

```bash
python -m alembic upgrade head --sql > migration.sql
```

### Branching and Merging

For parallel development:

```bash
# Create branch
python -m alembic revision -m "Feature A" --head=<base_rev>@branch_a

# Merge branches
python -m alembic merge <rev1> <rev2> -m "Merge feature branches"
```

## Integration with Application

### Startup Migration Check

Add to `app/main.py`:

```python
from alembic.config import Config
from alembic import command

async def check_migrations():
    """Check if migrations are up to date"""
    alembic_cfg = Config("alembic.ini")
    command.current(alembic_cfg)
```

### Automated Migration on Startup (Development Only)

```python
async def run_migrations():
    """Run migrations on startup (development only)"""
    if settings.ENVIRONMENT == "development":
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
```

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Quick Reference

```bash
# Create migration
python -m alembic revision --autogenerate -m "message"

# Apply migrations
python -m alembic upgrade head

# Rollback one migration
python -m alembic downgrade -1

# View current revision
python -m alembic current

# View history
python -m alembic history

# Generate SQL
python -m alembic upgrade head --sql
```

## Support

For issues or questions:
1. Check this guide
2. Review Alembic documentation
3. Check migration history: `python -m alembic history --verbose`
4. Verify database connection: `python scripts/test_db_connection.py`
