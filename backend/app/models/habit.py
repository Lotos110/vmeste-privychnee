from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.user import User
from app.services import timeutil

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


class HabitTemplate(Base):
    __tablename__ = "habit_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(60), unique=True)
    icon: Mapped[str] = mapped_column(String(40))  # имя иконки Material, например WATER_DROP
    category: Mapped[str] = mapped_column(String(20))
    default_goal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_schedule: Mapped[list[int]] = mapped_column(JSON, default=lambda: list(ALL_DAYS))
    default_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # «HH:MM»
    position: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.title


class Habit(Base):
    """Привычка — одна запись с участниками: личная и совместная устроены одинаково."""

    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("habit_templates.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(80))
    goal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    schedule: Mapped[list[int]] = mapped_column(JSON, default=lambda: list(ALL_DAYS))
    remind_time: Mapped[time | None] = mapped_column(Time, nullable=True)  # местное время
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)  # своя иконка Material
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # purple/green/orange/blue/red
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )

    template: Mapped[HabitTemplate | None] = relationship()
    members: Mapped[list["HabitMember"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", passive_deletes=True
    )
    check_ins: Mapped[list["CheckIn"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    nudges: Mapped[list["Nudge"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", passive_deletes=True
    )


class HabitMember(Base):
    __tablename__ = "habit_members"

    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    status: Mapped[str] = mapped_column(String(10), default="active")  # invited | active | left
    joined_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # местная дата старта
    # Кэш для быстрых экранов и будущего рейтинга. Истина хранится в check_ins.
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)

    habit: Mapped[Habit] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class CheckIn(Base):
    __tablename__ = "check_ins"
    __table_args__ = (
        UniqueConstraint("habit_id", "user_id", "local_date", name="uq_checkin_day"),
        Index("ix_checkins_user_date", "user_id", "local_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10))  # done | missed
    miss_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )


class Nudge(Base):
    """Сообщение пользователю: от напарника или напоминание от системы (from_user пуст)."""

    __tablename__ = "nudges"
    __table_args__ = (Index("ix_nudges_to_user_created", "to_user", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"))
    from_user: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    to_user: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), default="partner")  # partner | reminder | risk
    local_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # для защиты от дублей
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: timeutil.utcnow()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    habit: Mapped[Habit] = relationship(back_populates="nudges")
    sender: Mapped[User | None] = relationship(foreign_keys=[from_user])


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), unique=True)
    category: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(String(200), default="")
    body_md: Mapped[str] = mapped_column(Text)
    cover_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    habit_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("habit_templates.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    habit_template: Mapped["HabitTemplate | None"] = relationship()  # для формы в админке

    def __str__(self) -> str:
        return self.title
