"""
Analyze club-to-player distribution from the database.

This script provides statistics about:
1. Total number of clubs
2. Players per club distribution
3. Top clubs by player count
4. Top clubs by average CA
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.models.player import Player

# Connect to SQLite database
DATABASE_URL = "sqlite:///./tfm_players.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def main():
    """Analyze club distribution"""
    print("="*60)
    print("CLUB-TO-PLAYER DISTRIBUTION ANALYSIS")
    print("="*60)
    
    with SessionLocal() as session:
        # Total clubs
        total_clubs = session.execute(
            select(func.count(func.distinct(Player.club)))
        ).scalar_one()
        
        print(f"\nTotal clubs: {total_clubs}")
        
        # Players per club statistics
        result = session.execute(
            select(
                Player.club,
                func.count(Player.id).label('player_count'),
                func.avg(Player.ca).label('avg_ca'),
                func.max(Player.ca).label('max_ca')
            ).group_by(Player.club).order_by(func.count(Player.id).desc())
        )
        
        clubs_data = result.all()
        
        # Distribution statistics
        player_counts = [club.player_count for club in clubs_data]
        avg_players = sum(player_counts) / len(player_counts)
        max_players = max(player_counts)
        min_players = min(player_counts)
        
        print(f"\nPlayers per club:")
        print(f"  Average: {avg_players:.1f}")
        print(f"  Maximum: {max_players}")
        print(f"  Minimum: {min_players}")
        
        # Top 20 clubs by player count
        print(f"\nTop 20 clubs by player count:")
        for i, club in enumerate(clubs_data[:20], 1):
            print(f"  {i:2d}. {club.club[:40]:40s} - {club.player_count:3d} players (avg CA: {club.avg_ca:.1f})")
        
        # Top 20 clubs by average CA
        print(f"\nTop 20 clubs by average CA:")
        clubs_by_ca = sorted(clubs_data, key=lambda x: x.avg_ca, reverse=True)
        for i, club in enumerate(clubs_by_ca[:20], 1):
            print(f"  {i:2d}. {club.club[:40]:40s} - avg CA: {club.avg_ca:.1f} ({club.player_count} players)")
        
        # Clubs with 1 player
        single_player_clubs = [club for club in clubs_data if club.player_count == 1]
        print(f"\nClubs with only 1 player: {len(single_player_clubs)}")
        
        # Clubs with 20+ players
        large_clubs = [club for club in clubs_data if club.player_count >= 20]
        print(f"Clubs with 20+ players: {len(large_clubs)}")
        
        print("\n" + "="*60)
        print("✓ ANALYSIS COMPLETE")
        print("="*60)


if __name__ == "__main__":
    main()
