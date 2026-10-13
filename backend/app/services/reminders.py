"""Напоминания внутри приложения: «пора выполнить» и «серия под угрозой».

Запускается планировщиком каждые N минут (см. scheduler.py). Сообщения кладутся в таблицу
nudges (from_user пуст) и показываются в приложении. Push на телефон — план v2.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models import CheckIn, Habit, HabitMember, Nudge
from app.services import timeutil
from app.services.habits import refresh_member_cache

log = logging.getLogger(__name__)


def run_reminders(db: Session, now: datetime | None = None) -> int:
    """Создаёт напоминания и обновляет кэш серий. Возвращает число созданных сообщений."""
    now = now or timeutil.utcnow()
    settings = get_settings()
    created = 0

    members = db.scalars(
        select(HabitMember)
        .where(HabitMember.status == "active")
        .options(selectinload(HabitMember.user))
    ).all()
    habits = {h.id: h for h in db.scalars(select(Habit))}

    for member in members:
        user, habit = member.user, habits.get(member.habit_id)
        if habit is None or user.is_banned:
            continue
        local = timeutil.local_now(user.timezone, now)
        today = local.date()

        # кэш серии нужно обновлять и когда человек молчит: вчерашний пропуск обнуляет серию
        refresh_member_cache(db, habit, member, user, now)

        if today.weekday() not in habit.schedule:
            continue
        marked = db.scalar(
            select(CheckIn.id).where(
                CheckIn.habit_id == habit.id,
                CheckIn.user_id == user.id,
                CheckIn.local_date == today,
            )
        )
        if marked is not None:
            continue

        def already_sent(kind: str, member=member, today=today, habit=habit) -> bool:
            return (
                db.scalar(
                    select(Nudge.id).where(
                        Nudge.habit_id == habit.id,
                        Nudge.to_user == member.user_id,
                        Nudge.kind == kind,
                        Nudge.local_date == today,
                    )
                )
                is not None
            )

        if (
            habit.remind_time
            and local.time().replace(second=0, microsecond=0) >= habit.remind_time
            and not already_sent("reminder")
        ):
            db.add(
                Nudge(
                    habit_id=habit.id,
                    to_user=user.id,
                    kind="reminder",
                    local_date=today,
                    text=f"Пора выполнить «{habit.title}»",
                )
            )
            created += 1

        if (
            local.hour >= settings.risk_hour
            and member.current_streak >= 2
            and not already_sent("risk")
        ):
            db.add(
                Nudge(
                    habit_id=habit.id,
                    to_user=user.id,
                    kind="risk",
                    local_date=today,
                    text=(
                        f"Серия {member.current_streak} дн. под угрозой: "
                        f"отметьте «{habit.title}» до конца дня"
                    ),
                )
            )
            created += 1

    db.commit()
    if created:
        log.info("Создано напоминаний: %s", created)
    return created
