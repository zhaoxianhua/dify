"""Add human input related db models

Revision ID: e8c3b3c46151
Revises: 788d3099ae3a
Create Date: 2026-01-29 14:15:23.081903

"""

from alembic import op
import models as models
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8c3b3c46151"
down_revision = "788d3099ae3a"
branch_labels = None
depends_on = None

def _is_pg(conn):
    return conn.dialect.name == "postgresql"

def upgrade():
    conn = op.get_bind()

    if _is_pg(conn):
        op.create_table(
            "execution_extra_contents",
            sa.Column("id", models.types.StringUUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("type", sa.String(length=30), nullable=False),
            sa.Column("workflow_run_id", models.types.StringUUID(), nullable=False),
            sa.Column("message_id", models.types.StringUUID(), nullable=True),
            sa.Column("form_id", models.types.StringUUID(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("execution_extra_contents_pkey")),
        )
        with op.batch_alter_table("execution_extra_contents", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("execution_extra_contents_message_id_idx"), ["message_id"], unique=False)
            batch_op.create_index(
                batch_op.f("execution_extra_contents_workflow_run_id_idx"), ["workflow_run_id"], unique=False
            )

        op.create_table(
            "human_input_form_deliveries",
            sa.Column("id", models.types.StringUUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),

            sa.Column("form_id", models.types.StringUUID(), nullable=False),
            sa.Column("delivery_method_type", sa.String(length=20), nullable=False),
            sa.Column("delivery_config_id", models.types.StringUUID(), nullable=True),
            sa.Column("channel_payload", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("human_input_form_deliveries_pkey")),
        )

        op.create_table(
            "human_input_form_recipients",
            sa.Column("id", models.types.StringUUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),

            sa.Column("form_id", models.types.StringUUID(), nullable=False),
            sa.Column("delivery_id", models.types.StringUUID(), nullable=False),
            sa.Column("recipient_type", sa.String(length=20), nullable=False),
            sa.Column("recipient_payload", sa.Text(), nullable=False),
            sa.Column("access_token", sa.VARCHAR(length=32), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("human_input_form_recipients_pkey")),
        )
        with op.batch_alter_table('human_input_form_recipients', schema=None) as batch_op:
            batch_op.create_unique_constraint(batch_op.f('human_input_form_recipients_access_token_key'), ['access_token'])

        op.create_table(
            "human_input_forms",
            sa.Column("id", models.types.StringUUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("tenant_id", models.types.StringUUID(), nullable=False),
            sa.Column("app_id", models.types.StringUUID(), nullable=False),
            sa.Column("workflow_run_id", models.types.StringUUID(), nullable=True),
            sa.Column("form_kind", sa.String(length=20), nullable=False),
            sa.Column("node_id", sa.String(length=60), nullable=False),
            sa.Column("form_definition", sa.Text(), nullable=False),
            sa.Column("rendered_content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("expiration_time", sa.DateTime(), nullable=False),
            sa.Column("selected_action_id", sa.String(length=200), nullable=True),
            sa.Column("submitted_data", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("submission_user_id", models.types.StringUUID(), nullable=True),
            sa.Column("submission_end_user_id", models.types.StringUUID(), nullable=True),
            sa.Column("completed_by_recipient_id", models.types.StringUUID(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("human_input_forms_pkey")),
        )

    else:
        # ===================== MySQL 全部使用原生 SQL =====================

        # 1. execution_extra_contents
        op.execute("""
        CREATE TABLE execution_extra_contents (
            id CHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            type VARCHAR(30) NOT NULL,
            workflow_run_id CHAR(36) NOT NULL,
            message_id CHAR(36) NULL,
            form_id CHAR(36) NULL,
            PRIMARY KEY (id),
            INDEX execution_extra_contents_message_id_idx (message_id),
            INDEX execution_extra_contents_workflow_run_id_idx (workflow_run_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 2. human_input_form_deliveries
        op.execute("""
        CREATE TABLE human_input_form_deliveries (
            id CHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            form_id CHAR(36) NOT NULL,
            delivery_method_type VARCHAR(20) NOT NULL,
            delivery_config_id CHAR(36) NULL,
            channel_payload TEXT NOT NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 3. human_input_form_recipients（修复唯一约束）
        op.execute("""
        CREATE TABLE human_input_form_recipients (
            id CHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            form_id CHAR(36) NOT NULL,
            delivery_id CHAR(36) NOT NULL,
            recipient_type VARCHAR(20) NOT NULL,
            recipient_payload TEXT NOT NULL,
            access_token VARCHAR(32) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY human_input_form_recipients_access_token_key (access_token)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 4. human_input_forms
        op.execute("""
        CREATE TABLE human_input_forms (
            id CHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            tenant_id CHAR(36) NOT NULL,
            app_id CHAR(36) NOT NULL,
            workflow_run_id CHAR(36) NULL,
            form_kind VARCHAR(20) NOT NULL,
            node_id VARCHAR(60) NOT NULL,
            form_definition TEXT NOT NULL,
            rendered_content TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            expiration_time DATETIME NOT NULL,
            selected_action_id VARCHAR(200) NULL,
            submitted_data TEXT NULL,
            submitted_at DATETIME NULL,
            submission_user_id CHAR(36) NULL,
            submission_end_user_id CHAR(36) NULL,
            completed_by_recipient_id CHAR(36) NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)


def downgrade():
    conn = op.get_bind()
    if _is_pg(conn):
        op.drop_table("human_input_forms")
        op.drop_table("human_input_form_recipients")
        op.drop_table("human_input_form_deliveries")
        op.drop_table("execution_extra_contents")
    else:
        op.execute("DROP TABLE IF EXISTS human_input_forms;")
        op.execute("DROP TABLE IF EXISTS human_input_form_recipients;")
        op.execute("DROP TABLE IF EXISTS human_input_form_deliveries;")
        op.execute("DROP TABLE IF EXISTS execution_extra_contents;")
