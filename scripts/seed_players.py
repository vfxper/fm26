"""
Database Seeding Script for Player Data

This script loads all players from the 2600球员属性.csv file
and inserts them into the PostgreSQL database.

Usage:
    python scripts/seed_players.py [--csv-path PATH] [--batch-size SIZE] [--dry-run]

Options:
    --csv-path PATH      Path to CSV file (default: fm26/2600球员属性.csv)
    --batch-size SIZE    Number of players to insert per batch (default: 500)
    --dry-run            Parse CSV but don't insert into database
    --force              Drop existing players and re-seed
    --verbose            Enable verbose logging
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.player import Player
from app.services.player_loader import load_players_from_csv, PlayerLoaderError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Seed player database from CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--csv-path',
        type=str,
        default='2600球员属性.csv',
        help='Path to CSV file (default: 2600球员属性.csv)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Number of players to insert per batch (default: 500)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse CSV but don\'t insert into database'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Drop existing players and re-seed'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def check_existing_players(db) -> int:
    """
    Check how many players already exist in the database.
    
    Args:
        db: Database session
        
    Returns:
        int: Number of existing players
    """
    try:
        count = db.scalar(select(func.count()).select_from(Player))
        return count or 0
    except Exception as e:
        logger.error(f"Failed to check existing players: {e}")
        return 0


def delete_all_players(db) -> int:
    """
    Delete all players from the database.
    
    Args:
        db: Database session
        
    Returns:
        int: Number of players deleted
    """
    try:
        count = check_existing_players(db)
        if count > 0:
            logger.info(f"Deleting {count} existing players...")
            db.query(Player).delete()
            db.commit()
            logger.info(f"Successfully deleted {count} players")
        return count
    except Exception as e:
        logger.error(f"Failed to delete players: {e}")
        db.rollback()
        raise


def insert_players_batch(db, players: List[Player], batch_size: int = 500) -> tuple:
    """
    Insert players into database in batches.
    
    Args:
        db: Database session
        players: List of Player objects to insert
        batch_size: Number of players per batch
        
    Returns:
        tuple: (successful_count, failed_count)
    """
    total = len(players)
    successful = 0
    failed = 0
    
    logger.info(f"Inserting {total} players in batches of {batch_size}...")
    
    for i in range(0, total, batch_size):
        batch = players[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        try:
            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} players)..."
            )
            
            # Use bulk_save_objects for efficient insertion
            db.bulk_save_objects(batch)
            db.commit()
            
            successful += len(batch)
            logger.info(
                f"Batch {batch_num}/{total_batches} completed successfully. "
                f"Progress: {successful}/{total} players"
            )
            
        except IntegrityError as e:
            logger.error(
                f"Integrity error in batch {batch_num}: {e}. "
                f"Attempting individual inserts..."
            )
            db.rollback()
            
            # Try inserting individually to identify problematic rows
            for player in batch:
                try:
                    db.add(player)
                    db.commit()
                    successful += 1
                except IntegrityError as ie:
                    logger.warning(
                        f"Failed to insert player {player.name} (uid: {player.uid}): {ie}"
                    )
                    db.rollback()
                    failed += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error inserting player {player.name}: {e}"
                    )
                    db.rollback()
                    failed += 1
                    
        except Exception as e:
            logger.error(f"Unexpected error in batch {batch_num}: {e}")
            db.rollback()
            failed += len(batch)
    
    return successful, failed


def seed_players(
    csv_path: str,
    batch_size: int = 500,
    dry_run: bool = False,
    force: bool = False
) -> bool:
    """
    Main function to seed players from CSV into database.
    
    Args:
        csv_path: Path to CSV file
        batch_size: Number of players per batch
        dry_run: If True, parse CSV but don't insert
        force: If True, delete existing players first
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Player Database Seeding Script")
    logger.info("=" * 80)
    
    # Validate CSV file exists
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return False
    
    logger.info(f"CSV file: {csv_file.absolute()}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Force re-seed: {force}")
    logger.info("-" * 80)
    
    # Load players from CSV
    try:
        logger.info("Loading players from CSV...")
        db = SessionLocal()
        players = load_players_from_csv(str(csv_file), db_session=db)
        logger.info(f"Successfully loaded {len(players)} players from CSV")
    except PlayerLoaderError as e:
        logger.error(f"Failed to load players from CSV: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error loading CSV: {e}")
        return False
    
    if dry_run:
        logger.info("Dry run mode - skipping database insertion")
        logger.info(f"Would have inserted {len(players)} players")
        return True
    
    # Database operations
    try:
        # Check existing players
        existing_count = check_existing_players(db)
        logger.info(f"Found {existing_count} existing players in database")
        
        if existing_count > 0 and not force:
            logger.warning(
                "Database already contains players. "
                "Use --force to delete and re-seed."
            )
            response = input("Continue and add new players? (y/N): ")
            if response.lower() != 'y':
                logger.info("Seeding cancelled by user")
                return False
        
        # Delete existing players if force flag is set
        if force and existing_count > 0:
            delete_all_players(db)
        
        # Insert players
        logger.info("-" * 80)
        successful, failed = insert_players_batch(db, players, batch_size)
        
        # Summary
        logger.info("=" * 80)
        logger.info("Seeding Summary")
        logger.info("=" * 80)
        logger.info(f"Total players loaded from CSV: {len(players)}")
        logger.info(f"Successfully inserted: {successful}")
        logger.info(f"Failed to insert: {failed}")
        logger.info(f"Success rate: {(successful / len(players) * 100):.2f}%")
        
        # Verify final count
        final_count = check_existing_players(db)
        logger.info(f"Total players in database: {final_count}")
        logger.info("=" * 80)
        
        if failed > 0:
            logger.warning(
                f"{failed} players failed to insert. "
                f"Check logs for details."
            )
        
        return failed == 0
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        db.close()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Run seeding
    success = seed_players(
        csv_path=args.csv_path,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        force=args.force
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
