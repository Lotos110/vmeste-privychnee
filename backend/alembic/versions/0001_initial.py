"""Начальная схема: 8 таблиц MVP

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("last_name", sa.String(60), nullable=True),
        sa.Column("bio", sa.String(300), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("avatar_path", sa.String(255), nullable=True),
        sa.Column("friend_code", sa.String(8), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("is_banned", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_friend_code", "users", ["friend_code"], unique=True)

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("friend_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "friend_id", name="uq_friendship_pair"),
    )
    op.create_index("ix_friendships_user_id", "friendships", ["user_id"])
    op.create_index("ix_friendships_friend_id", "friendships", ["friend_id"])

    op.create_table(
        "habit_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(60), nullable=False, unique=True),
        sa.Column("icon", sa.String(40), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("default_goal", sa.String(100), nullable=True),
        sa.Column("default_schedule", sa.JSON(), nullable=False),
        sa.Column("default_time", sa.String(5), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )

    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "template_id", sa.Integer(), sa.ForeignKey("habit_templates.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("goal", sa.String(120), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("remind_time", sa.Time(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "habit_members",
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("joined_date", sa.Date(), nullable=True),
        sa.Column("current_streak", sa.Integer(), nullable=False),
        sa.Column("best_streak", sa.Integer(), nullable=False),
    )
    op.create_index("ix_habit_members_user_id", "habit_members", ["user_id"])

    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("miss_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("habit_id", "user_id", "local_date", name="uq_checkin_day"),
    )
    op.create_index("ix_check_ins_habit_id", "check_ins", ["habit_id"])
    op.create_index("ix_checkins_user_date", "check_ins", ["user_id", "local_date"])

    op.create_table(
        "nudges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_user", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("to_user", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_nudges_to_user_created", "nudges", ["to_user", "created_at"])

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False, unique=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(200), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("cover_path", sa.String(255), nullable=True),
        sa.Column(
            "habit_template_id",
            sa.Integer(),
            sa.ForeignKey("habit_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for table in (
        "articles",
        "nudges",
        "check_ins",
        "habit_members",
        "habits",
        "habit_templates",
        "friendships",
        "users",
    ):
        op.drop_table(table)
