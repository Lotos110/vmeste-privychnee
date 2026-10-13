"""Статистика выполнения привычек для экрана «Моя статистика»."""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckIn, Habit, HabitMember, User
from app.schemas.habit import StatPoint, StatsOut
from app.services import timeutil
from app.services.streaks import activity_streaks

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _percent(done: int, planned: int) -> int | None:
    return round(100 * done / planned) if planned else None


def build_stats(db: Session, user: User, period: str, today: date | None = None) -> StatsOut:
    today = today or timeutil.local_today(user.timezone)

    rows = db.execute(
        select(Habit.id, Habit.schedule, HabitMember.joined_date)
        .join(HabitMember, HabitMember.habit_id == Habit.id)
        .where(HabitMember.user_id == user.id, HabitMember.status == "active")
    ).all()
    habits = [(hid, set(schedule), joined or today) for hid, schedule, joined in rows]

    done_by_day: dict[date, set[int]] = defaultdict(set)
    for habit_id, day in db.execute(
        select(CheckIn.habit_id, CheckIn.local_date).where(
            CheckIn.user_id == user.id, CheckIn.status == "done"
        )
    ):
        done_by_day[day].add(habit_id)

    def day_numbers(day: date) -> tuple[int, int]:
        """(выполнено, запланировано) за день по привычкам, которые уже шли в этот день."""
        planned_ids = {hid for hid, sched, start in habits if start <= day and day.weekday() in sched}
        return len(planned_ids & done_by_day.get(day, set())), len(planned_ids)

    points: list[StatPoint] = []
    total_done = total_planned = 0

    if period == "week":
        monday = today - timedelta(days=today.weekday())
        for offset in range(7):
            day = monday + timedelta(days=offset)
            if day > today:
                points.append(StatPoint(label=WEEKDAYS[offset], date=day, done=0, planned=0))
                continue
            done, planned = day_numbers(day)
            total_done, total_planned = total_done + done, total_planned + planned
            points.append(
                StatPoint(
                    label=WEEKDAYS[offset], date=day, done=done, planned=planned,
                    percent=_percent(done, planned),
                )
            )
    elif period == "month":
        for offset in range(29, -1, -1):
            day = today - timedelta(days=offset)
            done, planned = day_numbers(day)
            total_done, total_planned = total_done + done, total_planned + planned
            points.append(
                StatPoint(
                    label=str(day.day), date=day, done=done, planned=planned,
                    percent=_percent(done, planned),
                )
            )
    else:  # all: по месяцам, от первого дня активности
        candidates = [start for _, _, start in habits] + list(done_by_day)
        first = min(candidates) if candidates else today
        buckets: dict[tuple[int, int], list[int]] = {}
        day = date(first.year, first.month, 1)
        while day <= today:
            buckets[(day.year, day.month)] = [0, 0]
            day = date(day.year + (day.month == 12), day.month % 12 + 1, 1)
        day = first
        while day <= today:
            done, planned = day_numbers(day)
            bucket = buckets[(day.year, day.month)]
            bucket[0] += done
            bucket[1] += planned
            total_done, total_planned = total_done + done, total_planned + planned
            day += timedelta(days=1)
        for (year, month), (done, planned) in buckets.items():
            points.append(
                StatPoint(
                    label=MONTHS[month - 1], date=date(year, month, 1), done=done,
                    planned=planned, percent=_percent(done, planned),
                )
            )

    all_done_days = {day for day, ids in done_by_day.items() if ids}
    current, best = activity_streaks(all_done_days, today)
    return StatsOut(
        period=period,
        current_streak=current,
        best_streak=best,
        total_done=total_done,
        completion_percent=_percent(total_done, total_planned) or 0,
        points=points,
    )
