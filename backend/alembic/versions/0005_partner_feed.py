"""Лента «Поиск напарника»: объявления, отклики, жалобы, блокировки

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "template_id", sa.Integer(), sa.ForeignKey("habit_templates.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("topic", sa.String(60), nullable=False),
        sa.Column("text", sa.String(300), nullable=False),
        sa.Column("time_pref", sa.String(10), nullable=False),
        sa.Column("age_group", sa.String(5), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_partner_posts_author_id", "partner_posts", ["author_id"])
    op.create_index("ix_partner_posts_feed", "partner_posts", ["status", "age_group", "created_at"])

    op.create_table(
        "post_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("partner_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(200), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("post_id", "user_id", name="uq_response_once"),
    )
    op.create_index("ix_post_responses_post_id", "post_responses", ["post_id"])
    op.create_index("ix_post_responses_user_id", "post_responses", ["user_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(10), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_report_once"),
    )
    op.create_index("ix_reports_target_id", "reports", ["target_id"])

    op.create_table(
        "user_blocks",
        sa.Column("blocker_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("blocked_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"])

    # сообщения из ленты не привязаны к привычке
    with op.batch_alter_table("nudges") as batch:
        batch.alter_column("habit_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM nudges WHERE habit_id IS NULL")
    with op.batch_alter_table("nudges") as batch:
        batch.alter_column("habit_id", existing_type=sa.Integer(), nullable=False)
    op.drop_table("user_blocks")
    op.drop_table("reports")
    op.drop_table("post_responses")
    op.drop_table("partner_posts")
