"""Своя иконка и цвет привычки

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("habits", sa.Column("icon", sa.String(40), nullable=True))
    op.add_column("habits", sa.Column("color", sa.String(20), nullable=True))


def downgrade() -> None:
    # batch-режим нужен SQLite: он не умеет удалять колонки напрямую
    with op.batch_alter_table("habits") as batch:
        batch.drop_column("color")
        batch.drop_column("icon")
