"""add player fts gin index

Revision ID: add_player_fts_gin_index
Revises: add_player_listing_fields
Create Date: 2026-05-14 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_player_fts_gin_index'
down_revision: Union[str, None] = 'add_player_listing_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add GIN index for full-text search on players table.
    
    This creates a PostgreSQL GIN (Generalized Inverted Index) on a tsvector
    expression combining player name, position, club, and nationality fields.
    
    The index enables efficient full-text search queries like:
        SELECT * FROM players 
        WHERE to_tsvector('simple', name || ' ' || position || ' ' || club || ' ' || nationality)
              @@ plainto_tsquery('simple', 'search text')
    
    Uses 'simple' configuration for language-agnostic search supporting multiple languages.
    """
    # Create GIN index for full-text search
    # Note: This uses raw SQL because SQLAlchemy's Index with text() expression
    # doesn't work well with Alembic migrations
    op.execute("""
        CREATE INDEX idx_players_fts ON players 
        USING GIN(
            to_tsvector('simple', 
                COALESCE(name, '') || ' ' || 
                COALESCE(position, '') || ' ' || 
                COALESCE(club, '') || ' ' || 
                COALESCE(nationality, '')
            )
        )
    """)


def downgrade() -> None:
    """
    Remove GIN index for full-text search on players table.
    """
    op.execute("DROP INDEX IF EXISTS idx_players_fts")
