# Alembic Database Migrations

This directory contains database migration files for the Telegram Football Manager project.

## Overview

Alembic is configured for async SQLAlchemy 2.0 with PostgreSQL. All database models are automatically imported and tracked for changes.

## Directory Structure

```
alembic/
├── versions/           # Migration files (timestamped)
├── env.py             # Environment configuration (async setup)
├── script.py.mako     # Migration template
└── README             # Alembic default readme
```

## Configuration

### env.py

The `env.py` file is configured to:
- Use async SQLAlchemy engine
- Load database URL from environment variables via `app.core.config`
- Import all models from `app.models`
- Support both online and offline migration modes
- Enable type and server default comparison

### alembic.ini

The main configuration file includes:
- Timestamped migration filenames
- Black code formatting for generated migrations
- PostgreSQL-specific settings

## Creating Migrations

### Auto-generate from model changes

```bash
# Using helper script (recommended)
python scripts/migrate.py create "Add email to User"

# Using Alembic directly
python -m alembic revision --autogenerate -m "Add email to User"
```

### Create empty migration

```bash
# Using helper script
python scripts/migrate.py create-empty "Custom data migration"

# Using Alembic directly
python -m alembic revision -m "Custom data migration"
```

## Applying Migrations

```bash
# Using helper script (recommended)
python scripts/migrate.py upgrade

# Using Alembic directly
python -m alembic upgrade head
```

## Migration File Format

Migration files are named with timestamp:
```
YYYYMMDD_HHMM-<revision_id>_<slug>.py
```

Example:
```
20260511_1750-f0fc2f73da19_initial_migration_with_all_models.py
```

## Important Notes

1. **Always review auto-generated migrations** before applying them
2. **Test migrations** in development before applying to production
3. **Never modify applied migrations** - create new ones instead
4. **Commit migration files** to version control
5. **Database connection required** for autogenerate to work

## Models Tracked

All models in `app/models/` are automatically tracked:

- User
- Player
- Club
- Career
- SquadPlayer
- Match
- MatchEvent
- Transfer
- Injury
- Staff
- TrainingSchedule
- ScoutingAssignment
- MediaEvent
- Competition
- Fixture

## Documentation

For complete documentation, see:
- [Migration Guide](../docs/MIGRATION_GUIDE.md)
- [Migration Quick Reference](../docs/MIGRATION_QUICK_REFERENCE.md)

## Troubleshooting

### Autogenerate not detecting changes

Ensure:
1. All models are imported in `env.py`
2. Models inherit from `Base`
3. Database connection is working
4. You're using the correct database

### Connection errors

Check:
1. PostgreSQL is running
2. DATABASE_URL in `.env` is correct
3. Database exists and is accessible

### Migration conflicts

If you have conflicts:
```bash
# Check current state
python scripts/migrate.py current

# View history
python scripts/migrate.py history
```

## Quick Commands

```bash
# Create migration
python scripts/migrate.py create "message"

# Apply migrations
python scripts/migrate.py upgrade

# Rollback
python scripts/migrate.py downgrade

# View status
python scripts/migrate.py current
python scripts/migrate.py history
```
