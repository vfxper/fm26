#!/usr/bin/env python
"""
Script to create Alembic migrations without requiring database connection
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command

def create_migration(message: str, autogenerate: bool = True):
    """
    Create a new Alembic migration
    
    Args:
        message: Migration message
        autogenerate: Whether to autogenerate migration from models
    """
    # Get alembic config
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    
    # Create revision
    if autogenerate:
        command.revision(alembic_cfg, message=message, autogenerate=True)
    else:
        command.revision(alembic_cfg, message=message)
    
    print(f"Migration created: {message}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_migration.py <message> [--no-autogenerate]")
        sys.exit(1)
    
    message = sys.argv[1]
    autogenerate = "--no-autogenerate" not in sys.argv
    
    create_migration(message, autogenerate)
