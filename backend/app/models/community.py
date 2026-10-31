"""Лента «Поиск напарника»: объявления, отклики, жалобы и блокировки."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.habit import HabitTemplate
from app.models.user import User
from app.services import timeutil


class PartnerPost(Base):
    """Объявление «ищу напарника». age_group запоминается при создании: подростки и взрослые не пересекаются."""

    __tablename__ = "partner_posts"
    __table_args__ = (Index("ix_partner_posts_feed", "status", "age_group", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("habit_templates.id", ondelete="SET NULL"), nullable=True
    )
    topic: Mapped[str] = mapped_column(String(60))  # название шаблона или своя тема
    text: Mapped[str] = mapped_column(String(300))
    time_pref: Mapped[str] = mapped_column(String(10), default="any")  # morning | day | evening | any
    age_group: Mapped[str] = mapped_column(String(5))  # teen | adult
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | closed | hidden
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship()
    template: Mapped[HabitTemplate | None] = relationship()
    responses: Mapped[list["PostResponse"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )

    def __str__(self) -> str:  # для админки
        return f"#{self.id} {self.topic}: {self.text[:40]}"


class PostResponse(Base):
    __tablename__ = "post_responses"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_response_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("partner_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | accepted | declined | hidden
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )

    post: Mapped[PartnerPost] = relationship(back_populates="responses")
    user: Mapped[User] = relationship()

    def __str__(self) -> str:
        return f"#{self.id}: {self.text[:40]}"


class Report(Base):
    """Жалоба на объявление или отклик. Разбирается вручную в админке."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_report_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(10))  # post | response
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(20))  # contacts | rude | adult | spam | other
    status: Mapped[str] = mapped_column(String(10), default="new")  # new | done
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )

    reporter: Mapped[User] = relationship()


class UserBlock(Base):
    __tablename__ = "user_blocks"

    blocker_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )
