"""Участие в общем рейтинге

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # у всех существующих аккаунтов выключено: человек включает участие сам
    op.add_column(
        "users",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_public")
