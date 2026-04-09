"""remove workflow_node_executions.retry_index if exists

Revision ID: d7999dfa4aae
Revises: e1944c35e15e
Create Date: 2024-12-23 11:54:15.344543

"""
import warnings
from alembic import op, context
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "d7999dfa4aae"
down_revision = "e1944c35e15e"
branch_labels = None
depends_on = None

warnings.filterwarnings('ignore', 'Unknown schema content')

def _is_pg(conn):
    return conn.dialect.name == "postgresql"


def upgrade():
    def _has_retry_index_column() -> bool:
        if context.is_offline_mode():
            # 离线模式下无法检查表结构，默认认为字段不存在
            op.execute(
                '-- Executing in offline mode: assuming the "retry_index" column does not exist.\n'
                "-- The generated SQL may differ from what will actually be executed.\n"
                "-- Please review the migration script carefully!"
            )
            return False

        conn = op.get_bind()
        # 统一使用 SQLAlchemy inspector 检查列是否存在
        inspector = inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("workflow_node_executions")]
        return "retry_index" in columns

    has_column = _has_retry_index_column()
    if not has_column:
        return

    conn = op.get_bind()
    if _is_pg(conn):
        # PostgreSQL: 使用 batch_alter_table
        with op.batch_alter_table("workflow_node_executions", schema=None) as batch_op:
            batch_op.drop_column("retry_index")
    else:
        # MySQL: 使用原生 SQL 删除字段
        op.execute("ALTER TABLE workflow_node_executions DROP COLUMN IF EXISTS retry_index;")


def downgrade():
    # 按业务需求，降级操作不需要恢复 retry_index 字段，保持原有逻辑
    pass
