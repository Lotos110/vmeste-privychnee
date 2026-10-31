from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from app.db import Base
from app.services import timeutil


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # хэш кода восстановления пароля (сам код показывается один раз); у старых аккаунтов пусто
    recovery_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(300), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # приватное поле
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # female | male
    avatar_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    friend_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    # участвует ли в общем рейтинге (по умолчанию нет: человек включает сам)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=expression.false())
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # +1 = отозвать все токены
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )

    def __str__(self) -> str:  # для админки
        return f"{self.name} ({self.email})"


class Friendship(Base):
    """Заявка в друзья: user_id отправил заявку, friend_id получил."""

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    friend_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | accepted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )
