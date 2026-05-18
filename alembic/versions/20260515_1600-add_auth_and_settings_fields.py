"""Add auth and settings fields to users table

Revision ID: a1b2c3d4e5f6
Revises: 20260514_1925
Create Date: 2026-05-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None  # Set to latest revision ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make telegram_user_id nullable (was NOT NULL before)
    op.alter_column('users', 'telegram_user_id',
                    existing_type=sa.BigInteger(),
                    nullable=True)

    # Add email authentication fields
    op.add_column('users', sa.Column('email', sa.String(320), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(),
                                     nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires',
                                     sa.DateTime(timezone=True), nullable=True))

    # Add Google OAuth fields
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))

    # Add auth provider tracking
    op.add_column('users', sa.Column('auth_provider', sa.String(20),
                                     nullable=False, server_default='telegram'))

    # Add settings JSON storage
    op.add_column('users', sa.Column('settings_json', sa.Text(), nullable=True))

    # Add unique constraints and indexes
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_google_id', 'users', ['google_id'])


def downgrade() -> None:
    # Remove indexes and constraints
    op.drop_index('idx_users_google_id', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_constraint('uq_users_email', 'users', type_='unique')

    # Remove columns
    op.drop_column('users', 'settings_json')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')

    # Restore telegram_user_id as NOT NULL
    op.alter_column('users', 'telegram_user_id',
                    existing_type=sa.BigInteger(),
                    nullable=False)
