"""Код восстановления пароля

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # у уже существующих аккаунтов кода нет (пусто): его можно создать в профиле
    op.add_column("users", sa.Column("recovery_hash", sa.String(255), nullable=True))


def downgrade() -> None:
    # batch-режим нужен SQLite: он не умеет удалять колонки напрямую
    with op.batch_alter_table("users") as batch:
        batch.drop_column("recovery_hash")
