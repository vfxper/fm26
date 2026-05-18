"""add traits column to players

Revision ID: add_traits_column
Revises: f0fc2f73da19
Create Date: 2026-05-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_traits_column'
down_revision: Union[str, None] = 'f0fc2f73da19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add traits column to players table"""
    op.add_column('players', sa.Column('traits', sa.Text(), nullable=True, comment="Player traits and playing style characteristics"))


def downgrade() -> None:
    """Remove traits column from players table"""
    op.drop_column('players', 'traits')
