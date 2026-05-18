"""
Test PostgreSQL Database Connection
This script verifies that the PostgreSQL database is accessible and properly configured.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import get_engine, get_session_factory
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def test_database_connection():
    """Test database connection and basic operations"""
    
    print("=" * 60)
    print("PostgreSQL Database Connection Test")
    print("=" * 60)
    print()
    
    # Display connection info (hide password)
    db_url = settings.DATABASE_URL
    safe_url = db_url.split('@')[1] if '@' in db_url else db_url
    print(f"Database URL: ***@{safe_url}")
    print(f"Pool Size: {settings.DATABASE_POOL_SIZE}")
    print(f"Max Overflow: {settings.DATABASE_MAX_OVERFLOW}")
    print()
    
    try:
        # Test 1: Create engine
        print("Test 1: Creating database engine...")
        engine = get_engine()
        print("✓ Engine created successfully")
        print()
        
        # Test 2: Test connection
        print("Test 2: Testing database connection...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = await result.fetchone()
            assert row[0] == 1
            print("✓ Database connection successful")
            print()
        
        # Test 3: Check PostgreSQL version
        print("Test 3: Checking PostgreSQL version...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = await result.fetchone()
            print(f"✓ PostgreSQL version: {version[0]}")
            print()
        
        # Test 4: Check database name
        print("Test 4: Checking current database...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            db_name = await result.fetchone()
            print(f"✓ Connected to database: {db_name[0]}")
            print()
        
        # Test 5: Check user permissions
        print("Test 5: Checking user permissions...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT current_user"))
            user = await result.fetchone()
            print(f"✓ Connected as user: {user[0]}")
            print()
        
        # Test 6: Test session factory
        print("Test 6: Testing session factory...")
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = await result.fetchone()
            assert row[0] == 1
            print("✓ Session factory working correctly")
            print()
        
        # Test 7: Check for existing tables
        print("Test 7: Checking for existing tables...")
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = await result.fetchall()
            if tables:
                print(f"✓ Found {len(tables)} existing tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("✓ No tables found (database is empty - this is expected for initial setup)")
            print()
        
        # Test 8: Test transaction handling
        print("Test 8: Testing transaction handling...")
        async with session_factory() as session:
            async with session.begin():
                await session.execute(text("SELECT 1"))
            print("✓ Transaction handling working correctly")
            print()
        
        # Cleanup
        await engine.dispose()
        
        print("=" * 60)
        print("✓ All database connection tests passed!")
        print("=" * 60)
        print()
        print("Database is properly configured and ready to use.")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Database connection test failed!")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("Troubleshooting steps:")
        print("1. Ensure PostgreSQL 15+ is installed and running")
        print("2. Check that the database exists:")
        print("   psql -U postgres -c 'CREATE DATABASE tfm_db;'")
        print("3. Verify database credentials in .env file")
        print("4. Check DATABASE_URL format:")
        print("   postgresql+asyncpg://user:password@host:port/database")
        print("5. Ensure asyncpg driver is installed:")
        print("   pip install asyncpg")
        print("6. Check PostgreSQL is accepting connections:")
        print("   psql -U tfm_user -d tfm_db -h localhost")
        print()
        
        return False


async def main():
    """Main entry point"""
    success = await test_database_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
