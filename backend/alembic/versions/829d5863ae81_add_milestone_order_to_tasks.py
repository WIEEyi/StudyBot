"""add milestone_order to tasks

Revision ID: 829d5863ae81
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 03:20:08.168424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '829d5863ae81'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 milestone_order 列，用于前端按阶段顺序展示任务
    op.add_column('tasks', sa.Column('milestone_order', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'milestone_order')
