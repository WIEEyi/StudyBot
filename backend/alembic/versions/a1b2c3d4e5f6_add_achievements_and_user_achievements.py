"""add achievements and user_achievements tables

Revision ID: a1b2c3d4e5f6
Revises: eb0ace215fb2
Create Date: 2026-06-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '03765c961300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- achievements 成就定义表 ---
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=False, server_default='🏆'),
        sa.Column('category', sa.String(length=30), nullable=False, server_default='learning'),
        sa.Column('rarity', sa.String(length=20), nullable=False, server_default='common'),
        sa.Column('threshold', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_achievements_code'), 'achievements', ['code'], unique=True)
    op.create_index(op.f('ix_achievements_category'), 'achievements', ['category'], unique=False)

    # --- user_achievements 用户成就关联表 ---
    op.create_table(
        'user_achievements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('achievement_id', sa.Integer(), nullable=False),
        sa.Column('progress_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['achievement_id'], ['achievements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )
    op.create_index(op.f('ix_user_achievements_user_id'), 'user_achievements', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_achievements_achievement_id'), 'user_achievements', ['achievement_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_achievements_achievement_id'), table_name='user_achievements')
    op.drop_index(op.f('ix_user_achievements_user_id'), table_name='user_achievements')
    op.drop_table('user_achievements')
    op.drop_index(op.f('ix_achievements_category'), table_name='achievements')
    op.drop_index(op.f('ix_achievements_code'), table_name='achievements')
    op.drop_table('achievements')
