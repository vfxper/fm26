"""
Script to manually apply the GIN index for full-text search on players table.

This script creates the PostgreSQL GIN index directly without using Alembic,
which is useful when Alembic has path issues.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import get_engine


async def apply_gin_index():
    """Apply the GIN index for full-text search on players table."""
    
    print("=" * 70)
    print("Applying GIN Index for Player Full-Text Search")
    print("=" * 70)
    print()
    
    engine = get_engine()
    
    try:
        async with engine.begin() as conn:
            # Check if index already exists
            print("Step 1: Checking if index already exists...")
            result = await conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'players' 
                AND indexname = 'idx_players_fts'
            """))
            existing = await result.fetchone()
            
            if existing:
                print("✅ Index 'idx_players_fts' already exists!")
                print()
                return True
            
            print("   Index does not exist yet.")
            print()
            
            # Create the GIN index
            print("Step 2: Creating GIN index...")
            await conn.execute(text("""
                CREATE INDEX idx_players_fts ON players 
                USING GIN(
                    to_tsvector('simple', 
                        COALESCE(name, '') || ' ' || 
                        COALESCE(position, '') || ' ' || 
                        COALESCE(club, '') || ' ' || 
                        COALESCE(nationality, '')
                    )
                )
            """))
            print("✅ GIN index created successfully!")
            print()
            
            # Verify the index was created
            print("Step 3: Verifying index creation...")
            result = await conn.execute(text("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'players' 
                AND indexname = 'idx_players_fts'
            """))
            index_info = await result.fetchone()
            
            if index_info:
                print("✅ Index verified!")
                print(f"   Index name: {index_info[0]}")
                print(f"   Index definition: {index_info[1]}")
                print()
            else:
                print("❌ Index verification failed!")
                return False
            
            # Test the index with a sample query
            print("Step 4: Testing full-text search...")
            result = await conn.execute(text("""
                SELECT name, position, club, nationality
                FROM players
                WHERE to_tsvector('simple', 
                    COALESCE(name, '') || ' ' || 
                    COALESCE(position, '') || ' ' || 
                    COALESCE(club, '') || ' ' || 
                    COALESCE(nationality, '')
                ) @@ plainto_tsquery('simple', 'striker')
                LIMIT 5
            """))
            
            players = await result.fetchall()
            if players:
                print(f"✅ Full-text search working! Found {len(players)} sample results:")
                for player in players:
                    print(f"   - {player[0]} ({player[1]}) - {player[2]} - {player[3]}")
            else:
                print("⚠️  No results found (this might be normal if no data matches)")
            print()
            
            print("=" * 70)
            print("SUCCESS: GIN index applied successfully!")
            print("=" * 70)
            print()
            print("The players table now has a GIN index for efficient full-text search.")
            print("You can search players using queries like:")
            print()
            print("  SELECT * FROM players")
            print("  WHERE to_tsvector('simple', name || ' ' || position || ' ' || club || ' ' || nationality)")
            print("        @@ plainto_tsquery('simple', 'your search text')")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ ERROR: Failed to apply GIN index: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(apply_gin_index())
    sys.exit(0 if success else 1)
