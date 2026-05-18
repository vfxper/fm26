"""update pa constraint to allow negative values

Revision ID: update_pa_constraint
Revises: add_traits_column
Create Date: 2026-05-11 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_pa_constraint'
down_revision: Union[str, None] = 'add_traits_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update PA constraint to allow negative values (random potential in FM)"""
    # Drop old constraint
    op.drop_constraint('check_pa_range', 'players', type_='check')
    
    # Add new constraint allowing -200 to 200 (excluding 0)
    op.create_check_constraint(
        'check_pa_range',
        'players',
        'pa >= -200 AND pa <= 200 AND pa != 0'
    )


def downgrade() -> None:
    """Revert PA constraint to original (1-200)"""
    # Drop new constraint
    op.drop_constraint('check_pa_range', 'players', type_='check')
    
    # Add old constraint
    op.create_check_constraint(
        'check_pa_range',
        'players',
        'pa >= 1 AND pa <= 200'
    )
