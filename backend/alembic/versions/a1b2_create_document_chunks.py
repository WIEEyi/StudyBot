"""create document_chunks table with pgvector

Revision ID: a1b2c3d4e5f6
Revises: 4e3d32cdf2c8
Create Date: 2026-06-05

包含:
1. 启用 pgvector 扩展 (CREATE EXTENSION IF NOT EXISTS vector)
2. 创建 document_chunks 表（含 VECTOR(1536) 列）
3. 创建 B-tree 索引（document_id, user_id）
4. 创建 HNSW 向量搜索索引（cosine 距离）
"""

from typing import Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4e3d32cdf2c8'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # 1. 启用 pgvector 扩展（幂等操作，重复执行不报错）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. 创建 document_chunks 表
    op.create_table(
        'document_chunks',
        # 主键
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # 外键
        sa.Column(
            'document_id', sa.Integer(),
            sa.ForeignKey('documents.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id', sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        # 分块数据
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        # pgvector 向量列 (text-embedding-3-small = 1536 维)
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        # 时间戳
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        # 主键约束
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. B-tree 索引（外键查询加速）
    op.create_index(
        'ix_document_chunks_document_id',
        'document_chunks', ['document_id'],
    )
    op.create_index(
        'ix_document_chunks_user_id',
        'document_chunks', ['user_id'],
    )

    # 4. HNSW 向量搜索索引（余弦距离）
    # m=16: 每个节点的最大连接数（平衡内存占用和搜索精度）
    # ef_construction=64: 构建时的搜索深度（越高越精确，构建越慢）
    # 注意: HNSW 索引创建在新表上很快（空表），数据量大后构建会变慢
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    # 逆序撤销：先删索引，再删表
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index('ix_document_chunks_user_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_table('document_chunks')
