"""Add career_saves table for save system

Revision ID: add_career_saves
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_career_saves'
down_revision = '20260515_1600-add_auth_and_settings_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'career_saves',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('career_id', sa.Integer(), sa.ForeignKey('careers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slot_type', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('week', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('checksum', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_career_saves_career_user', 'career_saves', ['career_id', 'user_id'])


def downgrade():
    op.drop_table('career_saves')
