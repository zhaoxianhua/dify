"""drop server_default for app trail related tables

Revision ID: c3df22613c99
Revises: e8c3b3c46151
Create Date: 2026-02-09 09:50:46.181969

"""
from alembic import op
import models as models
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3df22613c99'
down_revision = 'e8c3b3c46151'
branch_labels = None
depends_on = None

def _is_pg(conn):
    return conn.dialect.name == "postgresql"

def upgrade():
    conn = op.get_bind()
    if _is_pg(conn):
        op.alter_column("account_trial_app_records", "id", server_default=None)
        op.alter_column("exporle_banners", "id", server_default=None)
        op.alter_column("trial_apps", "id", server_default=None)
    else:
        op.execute("ALTER TABLE account_trial_app_records MODIFY COLUMN id CHAR(36) NOT NULL;")
        op.execute("ALTER TABLE exporle_banners MODIFY COLUMN id CHAR(36) NOT NULL;")
        op.execute("ALTER TABLE trial_apps MODIFY COLUMN id CHAR(36) NOT NULL;")


def downgrade():
    # This migration is primarily for schema consistence
    # between database  and model definitions.
    #
    # The original
    # DROP SERVER default is idemponent.
    # Besides, the original migration has been updated to
    # reflect the
    pass
