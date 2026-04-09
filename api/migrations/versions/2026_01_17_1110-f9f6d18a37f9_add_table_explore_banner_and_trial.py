"""add table explore banner and trial

Revision ID: f9f6d18a37f9
Revises: 9e6fa5cbcd80
Create Date: 2026-01-017 11:10:18.079355

"""
from alembic import op
import models as models
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f9f6d18a37f9'
down_revision = '9e6fa5cbcd80'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    db_type = bind.dialect.name

    if db_type == "mysql":
        op.execute("""
        CREATE TABLE account_trial_app_records (
            id CHAR(36) NOT NULL,
            account_id CHAR(36) NOT NULL,
            app_id CHAR(36) NOT NULL,
            `count` INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY unique_account_trial_app_record (account_id, app_id),
            INDEX account_trial_app_record_account_id_idx (account_id),
            INDEX account_trial_app_record_app_id_idx (app_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        op.execute("""
        CREATE TABLE exporle_banners (
            id CHAR(36) NOT NULL,
            content JSON NOT NULL,
            link VARCHAR(255) NOT NULL,
            sort INTEGER NOT NULL,
            status VARCHAR(255) NOT NULL DEFAULT 'enabled',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `language` VARCHAR(255) NOT NULL DEFAULT 'en-US',
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        op.execute("""
        CREATE TABLE trial_apps (
            id CHAR(36) NOT NULL,
            app_id CHAR(36) NOT NULL,
            tenant_id CHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            trial_limit INTEGER NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY unique_trail_app_id (app_id),
            INDEX trial_app_app_id_idx (app_id),
            INDEX trial_app_tenant_id_idx (tenant_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

    else:
        op.create_table('account_trial_app_records',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('account_id', models.types.StringUUID(), nullable=False),
        sa.Column('app_id', models.types.StringUUID(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='user_trial_app_pkey'),
        sa.UniqueConstraint('account_id', 'app_id', name='unique_account_trial_app_record')
        )
        with op.batch_alter_table('account_trial_app_records', schema=None) as batch_op:
            batch_op.create_index('account_trial_app_record_account_id_idx', ['account_id'], unique=False)
            batch_op.create_index('account_trial_app_record_app_id_idx', ['app_id'], unique=False)

        op.create_table('exporle_banners',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('link', sa.String(length=255), nullable=False),
        sa.Column('sort', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=255), server_default=sa.text("'enabled'"), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('language', sa.String(length=255), server_default=sa.text("'en-US'"), nullable=False),
        sa.PrimaryKeyConstraint('id', name='exporler_banner_pkey')
        )
        op.create_table('trial_apps',
        sa.Column('id', models.types.StringUUID(), nullable=False),
        sa.Column('app_id', models.types.StringUUID(), nullable=False),
        sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('trial_limit', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='trial_app_pkey'),
        sa.UniqueConstraint('app_id', name='unique_trail_app_id')
        )
        with op.batch_alter_table('trial_apps', schema=None) as batch_op:
            batch_op.create_index('trial_app_app_id_idx', ['app_id'], unique=False)
            batch_op.create_index('trial_app_tenant_id_idx', ['tenant_id'], unique=False)


def downgrade():
    with op.batch_alter_table('trial_apps', schema=None) as batch_op:
        batch_op.drop_index('trial_app_tenant_id_idx')
        batch_op.drop_index('trial_app_app_id_idx')

    op.drop_table('trial_apps')
    op.drop_table('exporle_banners')
    with op.batch_alter_table('account_trial_app_records', schema=None) as batch_op:
        batch_op.drop_index('account_trial_app_record_app_id_idx')
        batch_op.drop_index('account_trial_app_record_account_id_idx')

    op.drop_table('account_trial_app_records')
