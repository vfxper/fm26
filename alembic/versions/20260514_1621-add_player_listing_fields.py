"""add player listing fields to squad_players

Revision ID: add_player_listing_fields
Revises: update_pa_constraint
Create Date: 2026-05-14 16:21:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_player_listing_fields'
down_revision = 'update_pa_constraint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add player listing fields to squad_players table.
    
    Adds:
    - is_listed_for_sale: Boolean flag indicating if player is listed for sale
    - asking_price: Optional asking price when player is listed
    """
    # Add is_listed_for_sale column
    op.add_column(
        'squad_players',
        sa.Column(
            'is_listed_for_sale',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Whether player is listed for sale'
        )
    )
    
    # Add asking_price column
    op.add_column(
        'squad_players',
        sa.Column(
            'asking_price',
            sa.BigInteger(),
            nullable=True,
            comment='Asking price when listed for sale (NULL if not listed)'
        )
    )
    
    # Add check constraint for asking_price (non-negative if set)
    op.create_check_constraint(
        'check_asking_price_non_negative',
        'squad_players',
        'asking_price IS NULL OR asking_price >= 0'
    )
    
    # Create index for is_listed_for_sale for efficient queries
    op.create_index(
        'idx_squad_players_is_listed_for_sale',
        'squad_players',
        ['is_listed_for_sale']
    )


def downgrade() -> None:
    """
    Remove player listing fields from squad_players table.
    """
    # Drop index
    op.drop_index('idx_squad_players_is_listed_for_sale', table_name='squad_players')
    
    # Drop check constraint
    op.drop_constraint('check_asking_price_non_negative', 'squad_players', type_='check')
    
    # Drop columns
    op.drop_column('squad_players', 'asking_price')
    op.drop_column('squad_players', 'is_listed_for_sale')
