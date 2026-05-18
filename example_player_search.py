"""
Example: Player Full-Text Search Usage

This script demonstrates how to use the GIN index for full-text search
on the players table.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import get_session_factory
from app.models.player import Player


async def example_basic_search():
    """Example 1: Basic player search"""
    print("=" * 70)
    print("Example 1: Basic Player Search")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search for players named "Messi"
    search_term = "Messi"
    print(f"Searching for: '{search_term}'")
    print()
    
    async with session_factory() as session:
        stmt = select(Player).where(
            Player.search_query_expression(search_term)
        ).limit(10)
        
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        if players:
            print(f"Found {len(players)} player(s):")
            for player in players:
                print(f"  • {player.name}")
                print(f"    Position: {player.position}")
                print(f"    Club: {player.club}")
                print(f"    Nationality: {player.nationality}")
                print(f"    CA: {player.ca}, PA: {player.pa}")
                print()
        else:
            print("No players found.")
    print()


async def example_search_with_ranking():
    """Example 2: Search with relevance ranking"""
    print("=" * 70)
    print("Example 2: Search with Relevance Ranking")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search for midfielders and rank by relevance
    search_term = "midfielder"
    print(f"Searching for: '{search_term}' (ordered by relevance)")
    print()
    
    async with session_factory() as session:
        rank = Player.search_rank_expression(search_term)
        stmt = select(
            Player,
            rank.label('relevance')
        ).where(
            Player.search_query_expression(search_term)
        ).order_by(
            rank.desc()
        ).limit(10)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if rows:
            print(f"Found {len(rows)} player(s) (top 10 by relevance):")
            for i, (player, relevance) in enumerate(rows, 1):
                print(f"  {i}. {player.name} (Relevance: {relevance:.4f})")
                print(f"     Position: {player.position}")
                print(f"     Club: {player.club}")
                print()
        else:
            print("No players found.")
    print()


async def example_complex_search():
    """Example 3: Complex multi-term search"""
    print("=" * 70)
    print("Example 3: Complex Multi-Term Search")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search for Portuguese forwards
    search_term = "Portugal forward"
    print(f"Searching for: '{search_term}'")
    print()
    
    async with session_factory() as session:
        stmt = select(Player).where(
            Player.search_query_expression(search_term)
        ).limit(10)
        
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        if players:
            print(f"Found {len(players)} player(s):")
            for player in players:
                print(f"  • {player.name}")
                print(f"    Position: {player.position}")
                print(f"    Club: {player.club}")
                print(f"    Nationality: {player.nationality}")
                print()
        else:
            print("No players found.")
    print()


async def example_search_with_filters():
    """Example 4: Search combined with attribute filters"""
    print("=" * 70)
    print("Example 4: Search with Attribute Filters")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search for young strikers with high CA
    search_term = "striker"
    min_ca = 150
    max_age = 25
    
    print(f"Searching for: '{search_term}'")
    print(f"Filters: CA >= {min_ca}, Age <= {max_age}")
    print()
    
    async with session_factory() as session:
        stmt = select(Player).where(
            Player.search_query_expression(search_term),
            Player.ca >= min_ca,
            Player.age <= max_age
        ).limit(10)
        
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        if players:
            print(f"Found {len(players)} player(s):")
            for player in players:
                print(f"  • {player.name} (Age: {player.age}, CA: {player.ca})")
                print(f"    Position: {player.position}")
                print(f"    Club: {player.club}")
                print()
        else:
            print("No players found matching criteria.")
    print()


async def example_search_by_club():
    """Example 5: Search players by club"""
    print("=" * 70)
    print("Example 5: Search Players by Club")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search for Barcelona players
    search_term = "Barcelona"
    print(f"Searching for players from: '{search_term}'")
    print()
    
    async with session_factory() as session:
        stmt = select(Player).where(
            Player.search_query_expression(search_term)
        ).limit(15)
        
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        if players:
            print(f"Found {len(players)} player(s):")
            for player in players:
                print(f"  • {player.name} ({player.position})")
                print(f"    CA: {player.ca}, Age: {player.age}")
                print()
        else:
            print("No players found.")
    print()


async def example_paginated_search():
    """Example 6: Paginated search results"""
    print("=" * 70)
    print("Example 6: Paginated Search Results")
    print("=" * 70)
    print()
    
    session_factory = get_session_factory()
    
    # Search with pagination
    search_term = "midfielder"
    page_size = 5
    page = 0  # First page
    
    print(f"Searching for: '{search_term}'")
    print(f"Page size: {page_size}, Page: {page + 1}")
    print()
    
    async with session_factory() as session:
        # Get total count
        count_stmt = select(Player).where(
            Player.search_query_expression(search_term)
        )
        count_result = await session.execute(count_stmt)
        total_count = len(count_result.scalars().all())
        
        # Get paginated results
        stmt = select(Player).where(
            Player.search_query_expression(search_term)
        ).limit(page_size).offset(page * page_size)
        
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        total_pages = (total_count + page_size - 1) // page_size
        
        print(f"Total results: {total_count}")
        print(f"Total pages: {total_pages}")
        print(f"Showing page {page + 1} of {total_pages}:")
        print()
        
        if players:
            for i, player in enumerate(players, 1):
                print(f"  {page * page_size + i}. {player.name}")
                print(f"     Position: {player.position}, Club: {player.club}")
                print()
        else:
            print("No players found.")
    print()


async def main():
    """Run all examples"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Player Full-Text Search Examples" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    try:
        # Run all examples
        await example_basic_search()
        await example_search_with_ranking()
        await example_complex_search()
        await example_search_with_filters()
        await example_search_by_club()
        await example_paginated_search()
        
        print("=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
