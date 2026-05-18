"""Add UEFA Champions League tables

Revision ID: 7a3c9e5b1d8f
Revises: add_career_saves
Create Date: 2026-05-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3c9e5b1d8f'
down_revision: Union[str, None] = 'add_career_saves'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'competition_rounds',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competition_id', sa.Integer,
                  sa.ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('round_type', sa.String(30), nullable=False),
        sa.Column('round_order', sa.Integer, nullable=False),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('is_completed', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_comp_rounds_comp', 'competition_rounds', ['competition_id'])
    op.create_index('idx_comp_rounds_comp_order', 'competition_rounds',
                    ['competition_id', 'round_order'], unique=True)

    op.create_table(
        'ucl_participants',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competition_id', sa.Integer,
                  sa.ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('club_id', sa.Integer, nullable=True),
        sa.Column('club_name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(50), nullable=False),
        sa.Column('seed', sa.Integer, nullable=False),
        sa.Column('final_rank', sa.Integer, nullable=True),
    )
    op.create_index('idx_ucl_part_comp', 'ucl_participants', ['competition_id'])
    op.create_index('idx_ucl_part_comp_seed', 'ucl_participants',
                    ['competition_id', 'seed'], unique=True)

    op.create_table(
        'ucl_standings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competition_id', sa.Integer,
                  sa.ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('participant_id', sa.Integer,
                  sa.ForeignKey('ucl_participants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('played', sa.Integer, nullable=False, server_default='0'),
        sa.Column('won', sa.Integer, nullable=False, server_default='0'),
        sa.Column('drawn', sa.Integer, nullable=False, server_default='0'),
        sa.Column('lost', sa.Integer, nullable=False, server_default='0'),
        sa.Column('goals_for', sa.Integer, nullable=False, server_default='0'),
        sa.Column('goals_against', sa.Integer, nullable=False, server_default='0'),
        sa.Column('goal_difference', sa.Integer, nullable=False, server_default='0'),
        sa.Column('points', sa.Integer, nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer, nullable=True),
    )
    op.create_index('idx_ucl_stand_comp', 'ucl_standings', ['competition_id'])
    op.create_index('idx_ucl_stand_comp_part', 'ucl_standings',
                    ['competition_id', 'participant_id'], unique=True)

    op.create_table(
        'ucl_ties',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competition_id', sa.Integer,
                  sa.ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('round_id', sa.Integer,
                  sa.ForeignKey('competition_rounds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('home_participant_id', sa.Integer,
                  sa.ForeignKey('ucl_participants.id'), nullable=True),
        sa.Column('away_participant_id', sa.Integer,
                  sa.ForeignKey('ucl_participants.id'), nullable=True),
        sa.Column('leg1_home_score', sa.Integer, nullable=True),
        sa.Column('leg1_away_score', sa.Integer, nullable=True),
        sa.Column('leg2_home_score', sa.Integer, nullable=True),
        sa.Column('leg2_away_score', sa.Integer, nullable=True),
        sa.Column('aggregate_home', sa.Integer, nullable=True),
        sa.Column('aggregate_away', sa.Integer, nullable=True),
        sa.Column('winner_participant_id', sa.Integer,
                  sa.ForeignKey('ucl_participants.id'), nullable=True),
        sa.Column('winner_decided_by', sa.String(20), nullable=True),
        sa.Column('bracket_position', sa.Integer, nullable=False),
    )
    op.create_index('idx_ucl_tie_comp', 'ucl_ties', ['competition_id'])
    op.create_index('idx_ucl_tie_round', 'ucl_ties', ['round_id'])
    op.create_index('idx_ucl_tie_round_pos', 'ucl_ties',
                    ['round_id', 'bracket_position'], unique=True)


def downgrade():
    op.drop_index('idx_ucl_tie_round_pos', table_name='ucl_ties')
    op.drop_table('ucl_ties')
    op.drop_index('idx_ucl_stand_comp_part', table_name='ucl_standings')
    op.drop_table('ucl_standings')
    op.drop_index('idx_ucl_part_comp_seed', table_name='ucl_participants')
    op.drop_table('ucl_participants')
    op.drop_index('idx_comp_rounds_comp_order', table_name='competition_rounds')
    op.drop_table('competition_rounds')
