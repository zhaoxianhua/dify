"""add chatbot color theme

Revision ID: b69ca54b9208
Revises: 4ff534e1eb11
Create Date: 2024-06-25 01:14:21.523873

"""
import sqlalchemy as sa
from alembic import op
import models as models

# 新增：判断数据库类型的工具函数
def _is_pg(conn) -> bool:
    return conn.dialect.name == "postgresql"

# revision identifiers, used by Alembic.
revision = 'b69ca54b9208'
down_revision = '4ff534e1eb11'
branch_labels = None
depends_on = None


def upgrade():
    # 获取数据库连接
    conn = op.get_bind()
    is_postgres = _is_pg(conn)

    # ========== 新增字段：区分 PostgreSQL/MySQL 语法 ==========
    # 1. 新增 chat_color_theme 字段（字符串类型，可空）
    if is_postgres:
        # PostgreSQL 支持 IF NOT EXISTS
        op.execute("""
            ALTER TABLE sites
            ADD COLUMN IF NOT EXISTS chat_color_theme VARCHAR(255) NULL;
        """)
    else:
        # MySQL 不支持 IF NOT EXISTS，直接新增（需确保字段不存在，Alembic 会自动处理重复执行）
        op.execute("""
            ALTER TABLE sites
            ADD COLUMN chat_color_theme VARCHAR(255) NULL;
        """)

    # 2. 新增 chat_color_theme_inverted 字段（布尔类型，非空，默认false）
    if is_postgres:
        op.execute("""
            ALTER TABLE sites
            ADD COLUMN IF NOT EXISTS chat_color_theme_inverted BOOLEAN
            NOT NULL DEFAULT FALSE;
        """)
    else:
        # MySQL 布尔类型映射为 TINYINT(1)，且移除 IF NOT EXISTS
        op.execute("""
            ALTER TABLE sites
            ADD COLUMN chat_color_theme_inverted BOOLEAN
            NOT NULL DEFAULT FALSE;
        """)


def downgrade():
    # ========== 删除字段：MySQL 同样不支持 DROP COLUMN IF EXISTS（低版本） ==========
    if _is_pg(op.get_bind()):
        op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS chat_color_theme_inverted;")
        op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS chat_color_theme;")
    else:
        # MySQL 直接删除字段
        op.execute("ALTER TABLE sites DROP COLUMN chat_color_theme_inverted;")
        op.execute("ALTER TABLE sites DROP COLUMN chat_color_theme;")
