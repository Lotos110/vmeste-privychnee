"""Подсчёт серий. Чистые функции без базы данных, покрыты тестами.

Правила:
* привычка идёт по расписанию — набору дней недели (0 = понедельник … 6 = воскресенье);
* день, в который привычка не запланирована, серию не ломает;
* запланированный прошедший день без отметки «выполнено» серию обнуляет;
* сегодняшний день без отметки ещё не ломает серию (человек может успеть);
* если сегодня отмечен срыв («missed»), серия обнуляется сразу;
* отметка «выполнено» в незапланированный день засчитывается как +1 к серии.
"""

from collections.abc import Collection, Sequence
from datetime import date, timedelta


def current_streak(done_dates: set[date], today: date) -> int:
    """Серия ежедневной привычки (эталон из технического описания)."""
    day = today if today in done_dates else today - timedelta(days=1)
    streak = 0
    while day in done_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def compute_streaks(
    done: Collection[date],
    missed: Collection[date],
    schedule: Sequence[int],
    start: date,
    today: date,
) -> tuple[int, int]:
    """Возвращает (текущая серия, рекордная серия) участника привычки."""
    scheduled = set(schedule)
    run = best = 0
    day = start
    while day <= today:
        if day in done:
            run += 1
            best = max(best, run)
        elif day.weekday() in scheduled and (day < today or day in missed):
            run = 0
        day += timedelta(days=1)
    return run, best


def shared_streak(
    done_sets: Sequence[Collection[date]],
    missed_sets: Sequence[Collection[date]],
    schedule: Sequence[int],
    start: date,
    today: date,
) -> int:
    """Общая серия: дни подряд, в которые выполнили все участники."""
    if not done_sets:
        return 0
    scheduled = set(schedule)
    run = 0
    day = start
    while day <= today:
        if all(day in done for done in done_sets):
            run += 1
        elif day.weekday() in scheduled and (day < today or any(day in m for m in missed_sets)):
            run = 0
        day += timedelta(days=1)
    return run


def today_status(
    done: Collection[date], missed: Collection[date], schedule: Sequence[int], today: date
) -> str:
    """'done' | 'missed' | 'pending' (ждёт отметки) | 'off' (сегодня не по расписанию)."""
    if today in done:
        return "done"
    if today in missed:
        return "missed"
    return "pending" if today.weekday() in schedule else "off"


def activity_streaks(active_days: set[date], today: date) -> tuple[int, int]:
    """Общая серия пользователя: дни подряд, в которые выполнена хотя бы одна привычка.

    Возвращает (текущая, рекордная). Если сегодня ещё нет отметок, серия считается со вчера.
    """
    if not active_days:
        return 0, 0
    best = run = 0
    previous: date | None = None
    for day in sorted(active_days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return current_streak(active_days, today), best
