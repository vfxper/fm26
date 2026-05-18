#!/usr/bin/env python
"""
Verify Alembic Configuration

This script verifies that Alembic is properly configured without requiring
a database connection.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def verify_alembic_config():
    """Verify Alembic configuration"""
    print("Verifying Alembic Configuration...")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # 1. Check alembic.ini exists
    print("\n1. Checking alembic.ini...")
    alembic_ini = project_root / "alembic.ini"
    if alembic_ini.exists():
        print("   ✓ alembic.ini found")
    else:
        errors.append("alembic.ini not found")
        print("   ✗ alembic.ini not found")
    
    # 2. Check alembic directory exists
    print("\n2. Checking alembic directory...")
    alembic_dir = project_root / "alembic"
    if alembic_dir.exists() and alembic_dir.is_dir():
        print("   ✓ alembic directory found")
    else:
        errors.append("alembic directory not found")
        print("   ✗ alembic directory not found")
    
    # 3. Check env.py exists
    print("\n3. Checking env.py...")
    env_py = alembic_dir / "env.py"
    if env_py.exists():
        print("   ✓ env.py found")
        
        # Check if env.py has async configuration
        with open(env_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "async_engine_from_config" in content:
            print("   ✓ Async engine configuration found")
        else:
            warnings.append("env.py may not be configured for async")
            print("   ⚠ Async engine configuration not found")
        
        if "from app.core.database import Base" in content:
            print("   ✓ Base import found")
        else:
            warnings.append("Base import not found in env.py")
            print("   ⚠ Base import not found")
        
        if "from app.models import" in content:
            print("   ✓ Model imports found")
        else:
            warnings.append("Model imports not found in env.py")
            print("   ⚠ Model imports not found")
    else:
        errors.append("env.py not found")
        print("   ✗ env.py not found")
    
    # 4. Check versions directory exists
    print("\n4. Checking versions directory...")
    versions_dir = alembic_dir / "versions"
    if versions_dir.exists() and versions_dir.is_dir():
        print("   ✓ versions directory found")
        
        # Count migration files
        migration_files = list(versions_dir.glob("*.py"))
        migration_files = [f for f in migration_files if not f.name.startswith("__")]
        print(f"   ℹ {len(migration_files)} migration file(s) found")
    else:
        errors.append("versions directory not found")
        print("   ✗ versions directory not found")
    
    # 5. Check if models can be imported
    print("\n5. Checking model imports...")
    try:
        from app.core.database import Base
        print("   ✓ Base imported successfully")
    except Exception as e:
        errors.append(f"Failed to import Base: {e}")
        print(f"   ✗ Failed to import Base: {e}")
    
    try:
        from app.models import (
            User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
            Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
            Competition, Fixture
        )
        print("   ✓ All models imported successfully")
        print(f"   ℹ {len(Base.metadata.tables)} tables registered in metadata")
    except Exception as e:
        errors.append(f"Failed to import models: {e}")
        print(f"   ✗ Failed to import models: {e}")
    
    # 6. Check if Alembic can be imported
    print("\n6. Checking Alembic installation...")
    try:
        from alembic.config import Config
        from alembic import command
        print("   ✓ Alembic imported successfully")
    except Exception as e:
        errors.append(f"Failed to import Alembic: {e}")
        print(f"   ✗ Failed to import Alembic: {e}")
    
    # 7. Try to load Alembic config
    print("\n7. Checking Alembic configuration loading...")
    try:
        from alembic.config import Config
        cfg = Config(str(alembic_ini))
        print("   ✓ Alembic config loaded successfully")
        
        # Check script location
        script_location = cfg.get_main_option("script_location")
        print(f"   ℹ Script location: {script_location}")
    except Exception as e:
        errors.append(f"Failed to load Alembic config: {e}")
        print(f"   ✗ Failed to load Alembic config: {e}")
    
    # 8. Check environment variables
    print("\n8. Checking environment configuration...")
    try:
        from app.core.config import settings
        print("   ✓ Settings imported successfully")
        print(f"   ℹ Environment: {settings.ENVIRONMENT}")
        
        # Check if DATABASE_URL is set (don't print the actual value for security)
        if settings.DATABASE_URL:
            # Mask the password in the URL
            url = settings.DATABASE_URL
            if "@" in url:
                parts = url.split("@")
                user_pass = parts[0].split("://")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    masked_url = url.replace(user_pass, f"{user}:****")
                    print(f"   ℹ DATABASE_URL: {masked_url}")
                else:
                    print(f"   ℹ DATABASE_URL: {url}")
            else:
                print(f"   ℹ DATABASE_URL: {url}")
        else:
            warnings.append("DATABASE_URL not set")
            print("   ⚠ DATABASE_URL not set")
    except Exception as e:
        warnings.append(f"Failed to load settings: {e}")
        print(f"   ⚠ Failed to load settings: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if not errors and not warnings:
        print("\n✓ All checks passed! Alembic is properly configured.")
        print("\nNext steps:")
        print("1. Ensure PostgreSQL database is running")
        print("2. Run: python scripts/test_db_connection.py")
        print("3. Generate initial migration: python scripts/migrate.py create 'Initial migration'")
        print("4. Apply migrations: python scripts/migrate.py upgrade")
        return 0
    
    if warnings and not errors:
        print(f"\n⚠ {len(warnings)} warning(s) found:")
        for warning in warnings:
            print(f"   - {warning}")
        print("\nAlembic should work, but review the warnings above.")
        return 0
    
    if errors:
        print(f"\n✗ {len(errors)} error(s) found:")
        for error in errors:
            print(f"   - {error}")
        
        if warnings:
            print(f"\n⚠ {len(warnings)} warning(s) found:")
            for warning in warnings:
                print(f"   - {warning}")
        
        print("\nPlease fix the errors above before using Alembic.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_alembic_config())
