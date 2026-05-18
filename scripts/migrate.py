#!/usr/bin/env python
"""
Database Migration Helper Script

Provides convenient commands for common migration operations.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command


def get_alembic_config() -> Config:
    """Get Alembic configuration"""
    alembic_ini = project_root / "alembic.ini"
    return Config(str(alembic_ini))


def create_migration(message: str, autogenerate: bool = True):
    """
    Create a new migration
    
    Args:
        message: Migration message
        autogenerate: Whether to autogenerate from models
    """
    print(f"Creating migration: {message}")
    cfg = get_alembic_config()
    
    try:
        if autogenerate:
            command.revision(cfg, message=message, autogenerate=True)
        else:
            command.revision(cfg, message=message)
        print("✓ Migration created successfully")
    except Exception as e:
        print(f"✗ Error creating migration: {e}")
        sys.exit(1)


def upgrade(revision: str = "head"):
    """
    Upgrade database to a revision
    
    Args:
        revision: Target revision (default: head)
    """
    print(f"Upgrading database to: {revision}")
    cfg = get_alembic_config()
    
    try:
        command.upgrade(cfg, revision)
        print("✓ Database upgraded successfully")
    except Exception as e:
        print(f"✗ Error upgrading database: {e}")
        sys.exit(1)


def downgrade(revision: str = "-1"):
    """
    Downgrade database to a revision
    
    Args:
        revision: Target revision (default: -1)
    """
    print(f"Downgrading database to: {revision}")
    cfg = get_alembic_config()
    
    try:
        command.downgrade(cfg, revision)
        print("✓ Database downgraded successfully")
    except Exception as e:
        print(f"✗ Error downgrading database: {e}")
        sys.exit(1)


def current():
    """Show current database revision"""
    print("Current database revision:")
    cfg = get_alembic_config()
    
    try:
        command.current(cfg)
    except Exception as e:
        print(f"✗ Error getting current revision: {e}")
        sys.exit(1)


def history(verbose: bool = False):
    """
    Show migration history
    
    Args:
        verbose: Show detailed history
    """
    print("Migration history:")
    cfg = get_alembic_config()
    
    try:
        command.history(cfg, verbose=verbose)
    except Exception as e:
        print(f"✗ Error getting history: {e}")
        sys.exit(1)


def stamp(revision: str):
    """
    Stamp database with a revision without running migrations
    
    Args:
        revision: Revision to stamp
    """
    print(f"⚠ WARNING: Stamping database with revision: {revision}")
    print("This will mark the database as being at this revision without running migrations.")
    response = input("Are you sure? (yes/no): ")
    
    if response.lower() != "yes":
        print("Cancelled")
        return
    
    cfg = get_alembic_config()
    
    try:
        command.stamp(cfg, revision)
        print("✓ Database stamped successfully")
    except Exception as e:
        print(f"✗ Error stamping database: {e}")
        sys.exit(1)


def show_sql(revision: str = "head"):
    """
    Show SQL for migration without executing
    
    Args:
        revision: Target revision (default: head)
    """
    print(f"SQL for upgrade to {revision}:")
    cfg = get_alembic_config()
    
    try:
        command.upgrade(cfg, revision, sql=True)
    except Exception as e:
        print(f"✗ Error generating SQL: {e}")
        sys.exit(1)


def print_usage():
    """Print usage information"""
    print("""
Database Migration Helper

Usage:
    python scripts/migrate.py <command> [options]

Commands:
    create <message>        Create new migration (autogenerate)
    create-empty <message>  Create empty migration
    upgrade [revision]      Upgrade to revision (default: head)
    downgrade [revision]    Downgrade to revision (default: -1)
    current                 Show current revision
    history                 Show migration history
    history-verbose         Show detailed migration history
    stamp <revision>        Stamp database with revision (use carefully!)
    sql [revision]          Show SQL for migration (default: head)

Examples:
    python scripts/migrate.py create "Add email to User"
    python scripts/migrate.py upgrade
    python scripts/migrate.py upgrade abc123
    python scripts/migrate.py downgrade
    python scripts/migrate.py downgrade -2
    python scripts/migrate.py current
    python scripts/migrate.py history
    python scripts/migrate.py sql
    """)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command_name = sys.argv[1].lower()
    
    if command_name == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message required")
            print("Usage: python scripts/migrate.py create <message>")
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        create_migration(message, autogenerate=True)
    
    elif command_name == "create-empty":
        if len(sys.argv) < 3:
            print("Error: Migration message required")
            print("Usage: python scripts/migrate.py create-empty <message>")
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        create_migration(message, autogenerate=False)
    
    elif command_name == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision)
    
    elif command_name == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade(revision)
    
    elif command_name == "current":
        current()
    
    elif command_name == "history":
        history(verbose=False)
    
    elif command_name == "history-verbose":
        history(verbose=True)
    
    elif command_name == "stamp":
        if len(sys.argv) < 3:
            print("Error: Revision required")
            print("Usage: python scripts/migrate.py stamp <revision>")
            sys.exit(1)
        revision = sys.argv[2]
        stamp(revision)
    
    elif command_name == "sql":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        show_sql(revision)
    
    else:
        print(f"Error: Unknown command '{command_name}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
