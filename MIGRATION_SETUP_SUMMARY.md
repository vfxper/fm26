# Database Migration System Setup Summary

## Overview

Alembic has been successfully configured for the Telegram Football Manager project with async SQLAlchemy 2.0 and PostgreSQL support.

## What Was Set Up

### 1. Alembic Initialization

- ✅ Initialized Alembic in the project
- ✅ Created `alembic/` directory structure
- ✅ Created `alembic/versions/` for migration files
- ✅ Generated `alembic.ini` configuration file
- ✅ Generated `alembic/env.py` environment file

### 2. Async SQLAlchemy Configuration

The `alembic/env.py` file has been configured to:
- Use async SQLAlchemy engine (`async_engine_from_config`)
- Load database URL from environment variables via `app.core.config.settings`
- Import all 15 database models automatically
- Support both online and offline migration modes
- Enable type and server default comparison for accurate autogeneration

### 3. Alembic Configuration

The `alembic.ini` file has been configured with:
- Timestamped migration filenames: `YYYYMMDD_HHMM-<rev>_<slug>.py`
- Black code formatting for generated migrations
- PostgreSQL-specific settings
- Database URL loaded from environment variables

### 4. Initial Migration

An initial migration file has been created:
- File: `alembic/versions/20260511_1750-f0fc2f73da19_initial_migration_with_all_models.py`
- Status: Empty template (ready to be populated when database is available)
- Purpose: Will create all tables for the 15 models when applied

### 5. Helper Scripts

Created convenient helper scripts:

**Python Script:**
- `scripts/migrate.py` - Full-featured migration helper
  - Commands: create, upgrade, downgrade, current, history, stamp, sql
  - User-friendly interface with error handling
  - Confirmation prompts for dangerous operations

**Shell Scripts:**
- `scripts/migrate.bat` (Windows)
- `scripts/migrate.sh` (Linux/Mac)

### 6. Documentation

Created comprehensive documentation:

**Main Guides:**
- `docs/MIGRATION_GUIDE.md` - Complete migration guide (50+ sections)
  - Configuration details
  - Common commands
  - Workflow examples
  - Best practices
  - Troubleshooting
  - Advanced topics

- `docs/MIGRATION_QUICK_REFERENCE.md` - Quick command reference
  - Essential commands
  - Common workflows
  - Troubleshooting tips

**Directory Documentation:**
- `alembic/README.md` - Alembic directory overview

**Updated Documentation:**
- `README.md` - Added migration section
- `QUICKSTART.md` - Added migration setup steps

## Database Models Tracked

All 15 models are automatically tracked for migrations:

### Core Models
1. **User** - Telegram users
2. **Player** - Football players (50+ attributes)
3. **Club** - Football clubs with infrastructure
4. **Career** - Career mode saves

### Game Models
5. **SquadPlayer** - Players in club squads
6. **Match** - Match records
7. **MatchEvent** - Match events
8. **Transfer** - Player transfers
9. **Injury** - Player injuries
10. **Staff** - Club staff

### Management Models
11. **TrainingSchedule** - Training schedules
12. **ScoutingAssignment** - Scouting assignments
13. **MediaEvent** - Media events

### Competition Models
14. **Competition** - Competitions and leagues
15. **Fixture** - Match fixtures

## How to Use

### Quick Start

```bash
# 1. Ensure database is running
python scripts/test_db_connection.py

# 2. Apply migrations (when database is available)
python scripts/migrate.py upgrade

# 3. Create new migration after model changes
python scripts/migrate.py create "Description of changes"
```

### Common Commands

```bash
# Create migration
python scripts/migrate.py create "Add email to User"

# Apply migrations
python scripts/migrate.py upgrade

# Rollback one migration
python scripts/migrate.py downgrade

# View current revision
python scripts/migrate.py current

# View migration history
python scripts/migrate.py history
```

### Using Alembic Directly

```bash
# Create migration
python -m alembic revision --autogenerate -m "Description"

# Apply migrations
python -m alembic upgrade head

# Rollback
python -m alembic downgrade -1

# View status
python -m alembic current
python -m alembic history
```

## Next Steps

### When Database is Available

1. **Test database connection:**
   ```bash
   python scripts/test_db_connection.py
   ```

2. **Generate initial migration with actual schema:**
   ```bash
   python scripts/migrate.py create "Initial migration with all models"
   ```
   
   This will auto-generate the complete schema from all 15 models.

3. **Review the generated migration:**
   - Check `alembic/versions/<timestamp>_initial_migration_with_all_models.py`
   - Verify all tables, columns, indexes, and constraints are correct

4. **Apply the migration:**
   ```bash
   python scripts/migrate.py upgrade
   ```

5. **Verify tables were created:**
   ```bash
   # Connect to PostgreSQL
   psql -U tfm_user -d tfm_db
   
   # List tables
   \dt
   
   # Describe a table
   \d users
   ```

### Making Schema Changes

1. Modify models in `app/models/`
2. Generate migration: `python scripts/migrate.py create "Description"`
3. Review generated migration file
4. Test migration: `python scripts/migrate.py upgrade`
5. Test rollback: `python scripts/migrate.py downgrade`
6. Commit migration file to version control

## Configuration Files

### Environment Variables (.env)

```env
DATABASE_URL=postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
```

### Alembic Configuration (alembic.ini)

- Script location: `alembic`
- File template: Timestamped
- Post-write hooks: Black formatting
- Database URL: Loaded from environment

### Environment Configuration (alembic/env.py)

- Async engine: `async_engine_from_config`
- Target metadata: `Base.metadata`
- All models imported automatically
- Type comparison enabled
- Server default comparison enabled

## Features

### Async Support
- ✅ Fully async SQLAlchemy 2.0 compatible
- ✅ Uses `async_engine_from_config`
- ✅ Async connection handling

### Auto-generation
- ✅ Detects model changes automatically
- ✅ Generates upgrade and downgrade functions
- ✅ Compares types and server defaults

### Code Quality
- ✅ Black formatting for migration files
- ✅ Timestamped filenames for ordering
- ✅ Descriptive migration messages

### Safety
- ✅ Confirmation prompts for dangerous operations
- ✅ Rollback support
- ✅ SQL preview without execution
- ✅ Migration history tracking

## Documentation Resources

- **Migration Guide**: `docs/MIGRATION_GUIDE.md`
- **Quick Reference**: `docs/MIGRATION_QUICK_REFERENCE.md`
- **Alembic README**: `alembic/README.md`
- **Main README**: `README.md` (migration section)
- **Quick Start**: `QUICKSTART.md` (migration setup)

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
python scripts/test_db_connection.py

# Check .env file
cat .env | grep DATABASE_URL
```

### Migration Not Detecting Changes

Ensure:
1. All models are imported in `alembic/env.py` ✅
2. Models inherit from `Base` ✅
3. Database connection is working
4. You're using the correct database

### Autogenerate Requires Database

The autogenerate feature requires a database connection to compare the current schema with the models. If the database is not available:

1. Use offline mode: `python -m alembic revision -m "message"`
2. Manually write the migration
3. Or wait until database is available

## Summary

The database migration system is fully configured and ready to use. Once a PostgreSQL database is available, you can:

1. Generate the initial migration with all 15 models
2. Apply migrations to create the database schema
3. Make model changes and generate new migrations
4. Use the helper scripts for convenient migration management

All documentation and helper tools are in place to support the complete migration workflow.
