# Database Migration Quick Reference

Quick reference for common Alembic migration commands.

## Essential Commands

### Create Migration
```bash
# Auto-generate from model changes
python -m alembic revision --autogenerate -m "Add email to User"

# Create empty migration
python -m alembic revision -m "Custom data migration"
```

### Apply Migrations
```bash
# Upgrade to latest
python -m alembic upgrade head

# Upgrade one step
python -m alembic upgrade +1

# Upgrade to specific revision
python -m alembic upgrade abc123
```

### Rollback Migrations
```bash
# Downgrade one step
python -m alembic downgrade -1

# Downgrade to specific revision
python -m alembic downgrade abc123

# Downgrade all
python -m alembic downgrade base
```

### View Status
```bash
# Current revision
python -m alembic current

# Migration history
python -m alembic history

# Detailed history
python -m alembic history --verbose
```

### Generate SQL
```bash
# Show SQL without executing
python -m alembic upgrade head --sql

# Save SQL to file
python -m alembic upgrade head --sql > migration.sql
```

## Common Workflows

### Initial Setup
```bash
# 1. Check database connection
python scripts/test_db_connection.py

# 2. Create initial migration
python -m alembic revision --autogenerate -m "Initial migration"

# 3. Apply migration
python -m alembic upgrade head
```

### Making Changes
```bash
# 1. Modify models in app/models/

# 2. Generate migration
python -m alembic revision --autogenerate -m "Description"

# 3. Review migration file in alembic/versions/

# 4. Apply migration
python -m alembic upgrade head
```

### Testing Migrations
```bash
# Apply migration
python -m alembic upgrade head

# Test rollback
python -m alembic downgrade -1

# Re-apply
python -m alembic upgrade head
```

## Migration File Locations

- **Configuration**: `alembic.ini`
- **Environment**: `alembic/env.py`
- **Migrations**: `alembic/versions/`
- **Models**: `app/models/`

## Troubleshooting

### Check Current State
```bash
python -m alembic current
python -m alembic history
```

### Fix Out of Sync Database
```bash
# Stamp database with revision (use carefully!)
python -m alembic stamp head
```

### Connection Issues
```bash
# Test database connection
python scripts/test_db_connection.py

# Check .env file has correct DATABASE_URL
```

## Important Notes

- ✅ Always review auto-generated migrations
- ✅ Test migrations before committing
- ✅ Use descriptive migration messages
- ✅ Commit migration files to version control
- ❌ Never modify applied migrations
- ❌ Never use `stamp` in production

## Database URL Format

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

Example:
```env
DATABASE_URL=postgresql+asyncpg://tfm_user:tfm_password@localhost:5432/tfm_db
```

## Need More Help?

See the full [Migration Guide](MIGRATION_GUIDE.md) for detailed information.
