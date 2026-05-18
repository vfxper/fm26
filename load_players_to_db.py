"""
Load all players from CSV into the database with batch insert.

This script:
1. Applies database migrations (adds traits column)
2. Loads all players from CSV
3. Performs batch insert into database
4. Shows progress and statistics
"""
import sys
import asyncio
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_engine, get_session_factory
from app.core.config import settings
from app.models.player import Player
from app.services.player_loader import PlayerCSVParser


async def check_database_connection():
    """Check if database is accessible"""
    print("Checking database connection...")
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connection successful!")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


async def apply_migrations():
    """Apply pending database migrations"""
    print("\nApplying database migrations...")
    try:
        # Import alembic and run migrations
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations applied successfully!")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        print("  Continuing anyway (migrations may already be applied)...")
        return True


async def get_current_player_count(session: AsyncSession) -> int:
    """Get current number of players in database"""
    result = await session.execute(select(func.count(Player.id)))
    return result.scalar_one()


async def clear_existing_players(session: AsyncSession):
    """Clear all existing players from database"""
    print("\nClearing existing players...")
    count = await get_current_player_count(session)
    if count > 0:
        await session.execute(text("DELETE FROM players"))
        await session.commit()
        print(f"✓ Cleared {count} existing players")
    else:
        print("✓ No existing players to clear")


async def batch_insert_players(session: AsyncSession, players: list, batch_size: int = 1000):
    """
    Insert players in batches for efficiency.
    
    Args:
        session: Database session
        players: List of Player objects
        batch_size: Number of players per batch
    """
    total = len(players)
    print(f"\nInserting {total} players in batches of {batch_size}...")
    
    start_time = time.time()
    
    for i in range(0, total, batch_size):
        batch = players[i:i + batch_size]
        session.add_all(batch)
        await session.flush()
        
        # Show progress
        progress = min(i + batch_size, total)
        percent = (progress / total) * 100
        elapsed = time.time() - start_time
        rate = progress / elapsed if elapsed > 0 else 0
        
        print(f"  Progress: {progress}/{total} ({percent:.1f}%) - {rate:.0f} players/sec", end='\r')
    
    # Commit all changes
    await session.commit()
    
    elapsed = time.time() - start_time
    print(f"\n✓ Inserted {total} players in {elapsed:.2f} seconds ({total/elapsed:.0f} players/sec)")


async def verify_data(session: AsyncSession):
    """Verify loaded data"""
    print("\nVerifying loaded data...")
    
    # Count total players
    total_count = await get_current_player_count(session)
    print(f"  Total players: {total_count}")
    
    # Count players with traits
    result = await session.execute(
        select(func.count(Player.id)).where(Player.traits.isnot(None))
    )
    traits_count = result.scalar_one()
    print(f"  Players with traits: {traits_count} ({traits_count/total_count*100:.1f}%)")
    
    # Show sample players
    result = await session.execute(
        select(Player).order_by(Player.ca.desc()).limit(5)
    )
    top_players = result.scalars().all()
    
    print(f"\n  Top 5 players by CA:")
    for i, player in enumerate(top_players, 1):
        traits_info = f" (traits: {player.traits[:30]}...)" if player.traits else ""
        print(f"    {i}. {player.name} - CA: {player.ca}, PA: {player.pa}{traits_info}")
    
    print("\n✓ Data verification complete!")


async def main():
    """Main function to load players into database"""
    print("="*60)
    print("PLAYER DATABASE LOADER")
    print("="*60)
    
    # Check database connection
    if not await check_database_connection():
        print("\n✗ Cannot proceed without database connection")
        return
    
    # Apply migrations
    if not await apply_migrations():
        print("\n✗ Cannot proceed without migrations")
        return
    
    # Load players from CSV
    print(f"\nLoading players from CSV: {settings.PLAYER_CSV_PATH}")
    parser = PlayerCSVParser(settings.PLAYER_CSV_PATH)
    
    print("  Parsing CSV...")
    df = parser.load()
    print(f"  ✓ Loaded {len(df)} rows from CSV")
    
    print("  Cleaning and validating data...")
    clean_df, report = parser.clean_data(df)
    print(f"  ✓ Validated {report['valid_count']} players")
    print(f"    - Invalid: {report['invalid_count']}")
    print(f"    - Duplicates removed: {report['duplicates_removed']}")
    print(f"    - Weight defaults applied: {report['default_values_applied']['weight']}")
    print(f"    - Height defaults applied: {report['default_values_applied']['height']}")
    
    # Convert to Player objects
    print("\n  Converting to Player objects...")
    from app.services.player_loader import _create_player_from_row
    
    players = []
    failed = 0
    for idx, row in clean_df.iterrows():
        try:
            player = _create_player_from_row(row)
            players.append(player)
        except Exception as e:
            failed += 1
            if failed <= 5:  # Show first 5 errors
                print(f"    ✗ Failed to create player: {row.get('name', 'unknown')} - {e}")
    
    print(f"  ✓ Created {len(players)} Player objects ({failed} failed)")
    
    # Insert into database
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Clear existing players
        await clear_existing_players(session)
        
        # Batch insert
        await batch_insert_players(session, players, batch_size=1000)
        
        # Verify
        await verify_data(session)
    
    print("\n" + "="*60)
    print("✓ PLAYER DATABASE LOAD COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
