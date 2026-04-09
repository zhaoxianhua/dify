"""add unique constraint to tenant_default_models

Revision ID: f55813ffe2c8
Revises: c3df22613c99
Create Date: 2026-02-10 15:07:00.000000

"""
from alembic import op
import sqlalchemy as sa


def _is_pg(conn):
    return conn.dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = 'f55813ffe2c8'
down_revision = 'c3df22613c99'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    if _is_pg(conn):
        conn.execute(sa.text("""
            DELETE FROM tenant_default_models
            WHERE id NOT IN (
                SELECT DISTINCT ON (tenant_id, model_type) id
                FROM tenant_default_models
                ORDER BY tenant_id, model_type, updated_at DESC, id DESC
            )
        """))

    conn = op.get_bind()
    if _is_pg(conn):
        with op.batch_alter_table('tenant_default_models', schema=None) as batch_op:
            batch_op.create_unique_constraint('unique_tenant_default_model_type', ['tenant_id', 'model_type'])
    else:
        conn.execute(sa.text("""
            ALTER TABLE tenant_default_models ADD UNIQUE (tenant_id, model_type)
        """))


def downgrade():
    conn = op.get_bind()
    if _is_pg(conn):
        with op.batch_alter_table('tenant_default_models', schema=None) as batch_op:
            batch_op.drop_constraint('unique_tenant_default_model_type', type_='unique')
    else:
        conn.execute(sa.text("""
            ALTER TABLE tenant_default_models DROP INDEX tenant_id
        """))
