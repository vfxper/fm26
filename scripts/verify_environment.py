#!/usr/bin/env python3
"""
Environment Verification Script
Verifies that the environment is correctly configured for Telegram Football Manager
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_check(name, status, message=""):
    """Print a check result"""
    symbol = "✓" if status else "✗"
    status_text = "PASS" if status else "FAIL"
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    
    print(f"{color}{symbol} {name:40} [{status_text}]{reset}")
    if message:
        print(f"  → {message}")

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(".env")
    exists = env_path.exists()
    
    if exists:
        size = env_path.stat().st_size
        print_check(".env file exists", True, f"Size: {size} bytes")
    else:
        print_check(".env file exists", False, "Run: scripts/setup_environment.sh [environment]")
    
    return exists

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    required = (3, 11)
    is_valid = version >= required
    
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    required_str = f"{required[0]}.{required[1]}+"
    
    print_check(
        "Python version",
        is_valid,
        f"Current: {version_str}, Required: {required_str}"
    )
    
    return is_valid

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "redis",
        "celery",
        "pydantic",
        "pydantic_settings",
        "python-telegram-bot"
    ]
    
    all_installed = True
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            all_installed = False
            missing.append(package)
    
    if all_installed:
        print_check("Python dependencies", True, f"All {len(required_packages)} packages installed")
    else:
        print_check(
            "Python dependencies",
            False,
            f"Missing: {', '.join(missing)}. Run: pip install -r requirements.txt"
        )
    
    return all_installed

def check_environment_variables():
    """Check if critical environment variables are set"""
    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_check("Load .env file", False, "python-dotenv not installed")
        return False
    
    critical_vars = {
        "ENVIRONMENT": "Environment name (development/staging/production)",
        "DATABASE_URL": "PostgreSQL connection string",
        "REDIS_URL": "Redis connection string",
        "SECRET_KEY": "Secret key for JWT tokens",
        "TELEGRAM_BOT_TOKEN": "Telegram bot token"
    }
    
    all_set = True
    for var, description in critical_vars.items():
        value = os.getenv(var)
        is_set = value is not None and value != "" and "CHANGE_ME" not in value
        
        if is_set:
            # Mask sensitive values
            if var in ["SECRET_KEY", "TELEGRAM_BOT_TOKEN", "DATABASE_URL"]:
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print_check(var, True, display_value)
        else:
            print_check(var, False, f"Not set or needs update. {description}")
            all_set = False
    
    return all_set

def check_database_connection():
    """Check if database connection is working"""
    try:
        from app.core.config import settings
        import asyncpg
        import asyncio
        
        async def test_connection():
            try:
                # Extract connection parameters from DATABASE_URL
                url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
                conn = await asyncpg.connect(url)
                version = await conn.fetchval("SELECT version()")
                await conn.close()
                return True, version
            except Exception as e:
                return False, str(e)
        
        success, result = asyncio.run(test_connection())
        
        if success:
            # Extract PostgreSQL version
            version = result.split()[1] if result else "Unknown"
            print_check("Database connection", True, f"PostgreSQL {version}")
        else:
            print_check("Database connection", False, result)
        
        return success
    except Exception as e:
        print_check("Database connection", False, f"Error: {str(e)}")
        return False

def check_redis_connection():
    """Check if Redis connection is working"""
    try:
        from app.core.config import settings
        import redis
        
        # Parse Redis URL
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Test connection
        r.ping()
        info = r.info("server")
        version = info.get("redis_version", "Unknown")
        
        print_check("Redis connection", True, f"Redis {version}")
        return True
    except Exception as e:
        print_check("Redis connection", False, f"Error: {str(e)}")
        return False

def check_file_structure():
    """Check if required files and directories exist"""
    required_paths = [
        ("app/", True),
        ("app/main.py", False),
        ("app/core/config.py", False),
        ("app/core/database.py", False),
        ("app/core/cache.py", False),
        ("requirements.txt", False),
        ("2600球员属性.csv", False),
    ]
    
    all_exist = True
    for path, is_dir in required_paths:
        p = Path(path)
        exists = p.is_dir() if is_dir else p.is_file()
        
        if not exists:
            all_exist = False
        
        path_type = "Directory" if is_dir else "File"
        print_check(f"{path_type}: {path}", exists)
    
    return all_exist

def check_environment_config():
    """Check environment-specific configuration"""
    try:
        from app.core.config import settings
        
        env = settings.ENVIRONMENT
        debug = settings.DEBUG
        log_level = settings.LOG_LEVEL
        
        print_check("Environment", True, env)
        print_check("Debug mode", True, "ON" if debug else "OFF")
        print_check("Log level", True, log_level)
        
        # Environment-specific checks
        if env == "production":
            checks = [
                (not debug, "Debug mode should be OFF in production"),
                (settings.SECRET_KEY != "dev-secret-key-change-in-production-use-strong-random-key", 
                 "SECRET_KEY must be changed in production"),
                (settings.RATE_LIMIT_ENABLED, "Rate limiting should be enabled in production"),
                (log_level in ["WARNING", "ERROR"], "Log level should be WARNING or ERROR in production"),
            ]
            
            for check, message in checks:
                print_check(f"Production check: {message}", check)
        
        return True
    except Exception as e:
        print_check("Environment config", False, f"Error: {str(e)}")
        return False

def main():
    """Main verification function"""
    print_header("Telegram Football Manager - Environment Verification")
    
    print("\nChecking environment setup...\n")
    
    results = {}
    
    # Basic checks
    print_header("Basic Configuration")
    results["env_file"] = check_env_file()
    results["python_version"] = check_python_version()
    results["dependencies"] = check_dependencies()
    
    # Environment variables
    print_header("Environment Variables")
    results["env_vars"] = check_environment_variables()
    
    # File structure
    print_header("File Structure")
    results["file_structure"] = check_file_structure()
    
    # Environment configuration
    print_header("Environment Configuration")
    results["env_config"] = check_environment_config()
    
    # Service connections
    print_header("Service Connections")
    results["database"] = check_database_connection()
    results["redis"] = check_redis_connection()
    
    # Summary
    print_header("Verification Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✓ All checks passed! Your environment is ready.")
        print("\nYou can now start the application:")
        print("  python app/main.py")
        print("  or")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return 0
    else:
        print(f"\n✗ {failed} check(s) failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("  - Run: scripts/setup_environment.sh [environment]")
        print("  - Run: pip install -r requirements.txt")
        print("  - Ensure PostgreSQL and Redis are running")
        print("  - Update .env with correct credentials")
        return 1

if __name__ == "__main__":
    sys.exit(main())
