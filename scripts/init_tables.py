"""
Initialize Database Tables Script

This script creates all database tables defined in SQLAlchemy models.
Run this script after setting up the database and before starting the application.

Usage:
    python scripts/init_tables.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import init_db, check_db_health, get_engine
from app.core.config import settings
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """),
            {"table_name": table_name}
        )
        exists = (await result.fetchone())[0]
        return exists


async def list_tables() -> list[str]:
    """
    List all tables in the database.
    
    Returns:
        list[str]: List of table names
    """
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in await result.fetchall()]
        return tables


async def main():
    """Main function to initialize database tables."""
    print("=" * 60)
    print("Database Tables Initialization")
    print("=" * 60)
    print()
    
    # Check database connection
    print("Step 1: Checking database connection...")
    if not await check_db_health():
        print("❌ Database connection failed!")
        print()
        print("Please ensure:")
        print("1. PostgreSQL is running")
        print("2. Database credentials in .env are correct")
        print("3. Database exists (run scripts/setup_database.sh)")
        print()
        sys.exit(1)
    
    print("✅ Database connection successful")
    print()
    
    # List existing tables
    print("Step 2: Checking existing tables...")
    existing_tables = await list_tables()
    
    if existing_tables:
        print(f"Found {len(existing_tables)} existing tables:")
        for table in existing_tables:
            print(f"  - {table}")
    else:
        print("No existing tables found (fresh database)")
    print()
    
    # Check if training_schedules table exists
    training_schedules_exists = await check_table_exists("training_schedules")
    
    if training_schedules_exists:
        print("⚠️  training_schedules table already exists")
        print()
        response = input("Do you want to recreate all tables? (yes/no): ").strip().lower()
        
        if response != "yes":
            print("Aborted. No changes made.")
            sys.exit(0)
        
        print()
        print("Dropping all tables...")
        engine = get_engine()
        async with engine.begin() as conn:
            # Import Base to access metadata
            from app.core.database import Base
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ All tables dropped")
        print()
    
    # Create all tables
    print("Step 3: Creating database tables...")
    try:
        await init_db()
        print("✅ All tables created successfully")
        print()
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        logger.exception("Failed to create tables")
        sys.exit(1)
    
    # Verify tables were created
    print("Step 4: Verifying table creation...")
    final_tables = await list_tables()
    
    print(f"✅ Created {len(final_tables)} tables:")
    for table in sorted(final_tables):
        print(f"  - {table}")
    print()
    
    # Check specifically for training_schedules table
    if "training_schedules" in final_tables:
        print("✅ training_schedules table created successfully")
        
        # Get table details
        engine = get_engine()
        async with engine.connect() as conn:
            # Get column information
            result = await conn.execute(
                text("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = 'training_schedules'
                    ORDER BY ordinal_position
                """)
            )
            columns = await result.fetchall()
            
            print()
            print("Table structure:")
            print(f"  Columns ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"    - {col[0]}: {col[1]} {nullable}{default}")
            
            # Get index information
            result = await conn.execute(
                text("""
                    SELECT 
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public' 
                    AND tablename = 'training_schedules'
                    ORDER BY indexname
                """)
            )
            indexes = await result.fetchall()
            
            print()
            print(f"  Indexes ({len(indexes)}):")
            for idx in indexes:
                print(f"    - {idx[0]}")
            
            # Get constraint information
            result = await conn.execute(
                text("""
                    SELECT 
                        conname,
                        contype,
                        pg_get_constraintdef(oid) as definition
                    FROM pg_constraint
                    WHERE conrelid = 'training_schedules'::regclass
                    ORDER BY conname
                """)
            )
            constraints = await result.fetchall()
            
            print()
            print(f"  Constraints ({len(constraints)}):")
            for con in constraints:
                con_type = {
                    'p': 'PRIMARY KEY',
                    'f': 'FOREIGN KEY',
                    'c': 'CHECK',
                    'u': 'UNIQUE'
                }.get(con[1], con[1])
                print(f"    - {con[0]} ({con_type})")
    else:
        print("❌ training_schedules table was not created!")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ Database initialization completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run tests to verify table functionality")
    print("2. Start the application: python -m app.main")
    print()


if __name__ == "__main__":
    asyncio.run(main())
