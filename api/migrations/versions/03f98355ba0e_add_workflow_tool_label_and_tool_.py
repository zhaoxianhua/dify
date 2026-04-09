"""add workflow tool label and tool bindings idx

Revision ID: 03f98355ba0e
Revises: 9e98fbaffb88
Create Date: 2024-05-25 07:17:00.539125

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

import models as models

# revision identifiers, used by Alembic.
revision = '03f98355ba0e'
down_revision = '9e98fbaffb88'
branch_labels = None
depends_on = None


def upgrade():
    create_unique_idx_sql = """
    CREATE UNIQUE INDEX IF NOT EXISTS unique_tool_label_bind
    ON tool_label_bindings (tool_id, label_name);
    """
    op.execute(create_unique_idx_sql)
    add_label_column_sql = """
    ALTER TABLE tool_workflow_providers
    ADD COLUMN label VARCHAR(255) NOT NULL DEFAULT '';
    """
    op.execute(add_label_column_sql)


def downgrade():
    # 回滚1：删除 label 列（原生 SQL 兼容 Dingodb）
    drop_label_column_sql = "ALTER TABLE tool_workflow_providers DROP COLUMN IF EXISTS label;"
    op.execute(drop_label_column_sql)

    # 回滚2：删除唯一索引（Dingodb 兼容语法）
    drop_unique_idx_sql = """
    DROP INDEX IF EXISTS unique_tool_label_bind
    ON tool_label_bindings;
    """
    op.execute(drop_unique_idx_sql)
