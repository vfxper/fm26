"""
Load all players from CSV into SQLite database for testing.

This script:
1. Creates SQLite database
2. Loads all players from CSV
3. Performs batch insert
4. Shows progress and statistics
"""
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker, Session

from app.models.player import Player
from app.services.player_loader import PlayerCSVParser

# Create SQLite engine
DATABASE_URL = "sqlite:///./tfm_players.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def check_database():
    """Check if database is accessible"""
    print("Checking database...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful!")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def create_tables():
    """Create all tables"""
    print("\nCreating database tables...")
    try:
        from app.models.player import Base, Player
        from sqlalchemy import Table
        
        # For SQLite, we need to skip the PostgreSQL-specific GIN index
        # Temporarily remove it from table args
        original_table_args = Player.__table_args__
        
        # Filter out the GIN index
        filtered_args = tuple(
            arg for arg in original_table_args 
            if not (hasattr(arg, 'name') and arg.name == 'idx_players_fts')
        )
        
        # Temporarily replace table args
        Player.__table_args__ = filtered_args
        
        # Drop and recreate tables
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        
        # Restore original table args
        Player.__table_args__ = original_table_args
        
        print("✓ Tables created successfully!")
        return True
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_current_player_count(session: Session) -> int:
    """Get current number of players in database"""
    result = session.execute(select(func.count(Player.id)))
    return result.scalar_one()


def clear_existing_players(session: Session):
    """Clear all existing players from database"""
    print("\nClearing existing players...")
    count = get_current_player_count(session)
    if count > 0:
        session.execute(text("DELETE FROM players"))
        session.commit()
        print(f"✓ Cleared {count} existing players")
    else:
        print("✓ No existing players to clear")


def batch_insert_players(session: Session, players: list, batch_size: int = 1000):
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
        session.flush()
        
        # Show progress
        progress = min(i + batch_size, total)
        percent = (progress / total) * 100
        elapsed = time.time() - start_time
        rate = progress / elapsed if elapsed > 0 else 0
        
        print(f"  Progress: {progress}/{total} ({percent:.1f}%) - {rate:.0f} players/sec", end='\r')
    
    # Commit all changes
    session.commit()
    
    elapsed = time.time() - start_time
    print(f"\n✓ Inserted {total} players in {elapsed:.2f} seconds ({total/elapsed:.0f} players/sec)")


def verify_data(session: Session):
    """Verify loaded data"""
    print("\nVerifying loaded data...")
    
    # Count total players
    total_count = get_current_player_count(session)
    print(f"  Total players: {total_count}")
    
    # Count players with traits
    result = session.execute(
        select(func.count(Player.id)).where(Player.traits.isnot(None))
    )
    traits_count = result.scalar_one()
    print(f"  Players with traits: {traits_count} ({traits_count/total_count*100:.1f}%)")
    
    # Show sample players
    result = session.execute(
        select(Player).order_by(Player.ca.desc()).limit(5)
    )
    top_players = result.scalars().all()
    
    print(f"\n  Top 5 players by CA:")
    for i, player in enumerate(top_players, 1):
        traits_info = f" (traits: {player.traits[:30]}...)" if player.traits else ""
        print(f"    {i}. {player.name} - CA: {player.ca}, PA: {player.pa}{traits_info}")
    
    # Test search
    print(f"\n  Testing search for 'Messi':")
    result = session.execute(
        select(Player).where(Player.name.like('%Messi%')).limit(3)
    )
    messi_players = result.scalars().all()
    for player in messi_players:
        print(f"    - {player.name} ({player.club}) - CA: {player.ca}")
    
    print("\n✓ Data verification complete!")


def main():
    """Main function to load players into database"""
    print("="*60)
    print("PLAYER DATABASE LOADER (SQLite)")
    print("="*60)
    
    # Check database
    if not check_database():
        print("\n✗ Cannot proceed without database")
        return
    
    # Create tables
    if not create_tables():
        print("\n✗ Cannot proceed without tables")
        return
    
    # Load players from CSV
    csv_path = "2600球员属性.csv"
    print(f"\nLoading players from CSV: {csv_path}")
    parser = PlayerCSVParser(csv_path)
    
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
    with SessionLocal() as session:
        # Clear existing players
        clear_existing_players(session)
        
        # Batch insert
        batch_insert_players(session, players, batch_size=1000)
        
        # Verify
        verify_data(session)
    
    print("\n" + "="*60)
    print("✓ PLAYER DATABASE LOAD COMPLETE!")
    print(f"✓ Database saved to: {Path(DATABASE_URL.replace('sqlite:///', '')).absolute()}")
    print("="*60)


if __name__ == "__main__":
    main()
