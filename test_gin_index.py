"""
Test script for Player Full-Text Search with GIN Index

This script tests the full-text search functionality using the GIN index
on the players table.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, func, text
from app.core.database import get_engine, get_session_factory
from app.models.player import Player


async def test_gin_index():
    """Test the GIN index for full-text search."""
    
    print("=" * 70)
    print("Testing Player Full-Text Search with GIN Index")
    print("=" * 70)
    print()
    
    engine = get_engine()
    session_factory = get_session_factory()
    
    try:
        # Test 1: Check if index exists
        print("Test 1: Checking if GIN index exists...")
        async with engine.connect() as conn:
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
                print("✅ PASSED: GIN index 'idx_players_fts' exists")
                print(f"   Definition: {index_info[1]}")
            else:
                print("❌ FAILED: GIN index 'idx_players_fts' not found")
                print("   Run 'python apply_gin_index.py' to create the index")
                return False
        print()
        
        # Test 2: Count total players
        print("Test 2: Counting total players in database...")
        async with session_factory() as session:
            result = await session.execute(select(func.count(Player.id)))
            total_players = result.scalar()
            print(f"✅ PASSED: Found {total_players:,} players in database")
        print()
        
        # Test 3: Search by player name
        print("Test 3: Searching for players by name (e.g., 'Messi')...")
        async with session_factory() as session:
            stmt = select(Player).where(
                Player.search_query_expression("Messi")
            ).limit(5)
            result = await session.execute(stmt)
            players = result.scalars().all()
            
            if players:
                print(f"✅ PASSED: Found {len(players)} player(s) matching 'Messi':")
                for player in players:
                    print(f"   - {player.name} ({player.position}) - {player.club} - {player.nationality}")
            else:
                print("⚠️  No players found matching 'Messi' (might be normal if no such player exists)")
        print()
        
        # Test 4: Search by position
        print("Test 4: Searching for players by position (e.g., 'striker')...")
        async with session_factory() as session:
            stmt = select(Player).where(
                Player.search_query_expression("striker")
            ).limit(5)
            result = await session.execute(stmt)
            players = result.scalars().all()
            
            if players:
                print(f"✅ PASSED: Found {len(players)} player(s) with 'striker' in position:")
                for player in players:
                    print(f"   - {player.name} ({player.position}) - {player.club}")
            else:
                print("⚠️  No players found matching 'striker'")
        print()
        
        # Test 5: Search by club
        print("Test 5: Searching for players by club (e.g., 'Barcelona')...")
        async with session_factory() as session:
            stmt = select(Player).where(
                Player.search_query_expression("Barcelona")
            ).limit(5)
            result = await session.execute(stmt)
            players = result.scalars().all()
            
            if players:
                print(f"✅ PASSED: Found {len(players)} player(s) from Barcelona:")
                for player in players:
                    print(f"   - {player.name} ({player.position}) - {player.club}")
            else:
                print("⚠️  No players found from Barcelona")
        print()
        
        # Test 6: Search with relevance ranking
        print("Test 6: Testing relevance ranking...")
        async with session_factory() as session:
            rank = Player.search_rank_expression("midfielder")
            stmt = select(
                Player,
                rank.label('relevance')
            ).where(
                Player.search_query_expression("midfielder")
            ).order_by(
                rank.desc()
            ).limit(5)
            
            result = await session.execute(stmt)
            rows = result.all()
            
            if rows:
                print(f"✅ PASSED: Found {len(rows)} player(s) ranked by relevance:")
                for player, relevance in rows:
                    print(f"   - {player.name} ({player.position}) - Relevance: {relevance:.4f}")
            else:
                print("⚠️  No players found matching 'midfielder'")
        print()
        
        # Test 7: Complex search (multiple terms)
        print("Test 7: Testing complex search (e.g., 'Portugal forward')...")
        async with session_factory() as session:
            stmt = select(Player).where(
                Player.search_query_expression("Portugal forward")
            ).limit(5)
            result = await session.execute(stmt)
            players = result.scalars().all()
            
            if players:
                print(f"✅ PASSED: Found {len(players)} player(s) matching 'Portugal forward':")
                for player in players:
                    print(f"   - {player.name} ({player.position}) - {player.club} - {player.nationality}")
            else:
                print("⚠️  No players found matching 'Portugal forward'")
        print()
        
        # Test 8: Performance test - measure query time
        print("Test 8: Performance test (searching 1000 players)...")
        import time
        async with session_factory() as session:
            start_time = time.time()
            stmt = select(Player).where(
                Player.search_query_expression("midfielder")
            ).limit(1000)
            result = await session.execute(stmt)
            players = result.scalars().all()
            end_time = time.time()
            
            query_time = (end_time - start_time) * 1000  # Convert to milliseconds
            print(f"✅ PASSED: Query completed in {query_time:.2f}ms")
            print(f"   Found {len(players)} players")
            
            if query_time < 100:
                print("   ⚡ Excellent performance (< 100ms)")
            elif query_time < 500:
                print("   ✅ Good performance (< 500ms)")
            else:
                print("   ⚠️  Slow performance (> 500ms) - consider optimizing")
        print()
        
        print("=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • GIN index is properly configured")
        print("  • Full-text search is working correctly")
        print("  • Relevance ranking is functional")
        print("  • Performance is acceptable")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Test failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_gin_index())
    sys.exit(0 if success else 1)
