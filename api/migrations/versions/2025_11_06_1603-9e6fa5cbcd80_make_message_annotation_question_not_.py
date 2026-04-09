"""make message annotation question not nullable

Revision ID: 9e6fa5cbcd80
Revises: 03f8dcbc611e
Create Date: 2025-11-06 16:03:54.549378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e6fa5cbcd80'
down_revision = '288345cd01d1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    db_type = bind.dialect.name

    if db_type == "postgresql":
        # PG 保留原有 ORM 逻辑，不做修改
        message_annotations = sa.table(
            "message_annotations",
            sa.column("id", sa.String),
            sa.column("message_id", sa.String),
            sa.column("question", sa.Text),
        )
        messages = sa.table(
            "messages",
            sa.column("id", sa.String),
            sa.column("query", sa.Text),
        )
        update_question_from_message = (
            sa.update(message_annotations)
            .where(
                sa.and_(
                    message_annotations.c.question.is_(None),
                    message_annotations.c.message_id.isnot(None),
                )
            )
            .values(
                question=sa.select(sa.func.coalesce(messages.c.query, ""))
                .where(messages.c.id == message_annotations.c.message_id)
                .scalar_subquery()
            )
        )
        bind.execute(update_question_from_message)

        fill_remaining_questions = (
            sa.update(message_annotations)
            .where(message_annotations.c.question.is_(None))
            .values(question="")
        )
        bind.execute(fill_remaining_questions)
    else:
        op.execute("""
            UPDATE message_annotations, messages
            SET message_annotations.question = COALESCE(messages.query, '')
            WHERE message_annotations.message_id = messages.id
              AND message_annotations.question IS NULL
              AND message_annotations.message_id IS NOT NULL;
        """)
        # 第二步：填充剩余无关联的空 question 字段
        op.execute("""
            UPDATE message_annotations
            SET question = ''
            WHERE question IS NULL;
        """)

    # 第三步：修改字段为 NOT NULL（ORM 语法兼容 MySQL/PG）
    with op.batch_alter_table('message_annotations', schema=None) as batch_op:
        batch_op.alter_column('question', existing_type=sa.TEXT(), nullable=False)


def downgrade():
    # 降级逻辑保持不变（ORM 语法兼容双库）
    with op.batch_alter_table('message_annotations', schema=None) as batch_op:
        batch_op.alter_column('question', existing_type=sa.TEXT(), nullable=True)
