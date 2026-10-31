"""Рейтинг: «Серия» (дней подряд) и «Неделя» (выполненных отметок за 7 дней).

Считается на лету из отметок (check_ins), а не из кэша серий в habit_members: тот устаревает у тех, кто
молчит. Чтобы рейтинг нельзя было накрутить, отметка засчитывается, только если поставлена в тот же день
или на следующий (по часовому поясу человека). Общий список и список «по привычке» кэшируются на 5 минут.
"""

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckIn, Habit, User
from app.services import timeutil
from app.services.age import age_group, age_group_of
from app.services.people import avatar_url, friend_ids
from app.services.streaks import activity_streaks

Metric = Literal["streak", "week"]
Scope = Literal["friends", "global", "habit"]

TOP_SIZE = 50
CACHE_SECONDS = 300
HISTORY_DAYS = 400  # глубже серию не считаем: хватает для рейтинга
CHUNK = 400  # сколько пользователей в одном запросе к базе

_cache: dict[tuple, tuple[float, list["Row"]]] = {}


@dataclass
class Row:
    user_id: int
    name: str
    avatar_url: str | None
    value: int


def clear_cache() -> None:
    _cache.clear()


def _created_day(check_in: CheckIn, tz_name: str) -> date:
    created = timeutil.as_utc(check_in.created_at) or timeutil.utcnow()
    return created.astimezone(timeutil.get_zone(tz_name)).date()


def scores(db: Session, users: list[User], metric: Metric, template_id: int | None = None) -> dict[int, int]:
    """Значение метрики для каждого из пользователей (нет отметок — 0)."""
    result = {u.id: 0 for u in users}
    if not users:
        return result
    horizon = timeutil.utcnow().date() - timedelta(days=HISTORY_DAYS + 2)
    template_habits = None
    if template_id is not None:
        template_habits = select(Habit.id).where(Habit.template_id == template_id)

    for start in range(0, len(users), CHUNK):
        chunk = users[start : start + CHUNK]
        query = select(CheckIn).where(
            CheckIn.user_id.in_([u.id for u in chunk]),
            CheckIn.status == "done",
            CheckIn.local_date >= horizon,
        )
        if template_habits is not None:
            query = query.where(CheckIn.habit_id.in_(template_habits))
        by_user: dict[int, list[CheckIn]] = {}
        for check_in in db.scalars(query):
            by_user.setdefault(check_in.user_id, []).append(check_in)

        for user in chunk:
            today = timeutil.local_today(user.timezone)
            valid = [
                c
                for c in by_user.get(user.id, [])
                if c.local_date <= today and (_created_day(c, user.timezone) - c.local_date).days <= 1
            ]
            if metric == "week":
                week_start = today - timedelta(days=6)
                result[user.id] = sum(1 for c in valid if c.local_date >= week_start)
            else:
                result[user.id] = activity_streaks({c.local_date for c in valid}, today)[0]
    return result


def _rows(users: list[User], values: dict[int, int]) -> list[Row]:
    rows = [Row(u.id, u.name, avatar_url(u), values.get(u.id, 0)) for u in users]
    rows.sort(key=lambda r: (-r.value, r.name.lower(), r.user_id))
    return rows


def ranked(rows: list[Row]) -> list[tuple[int, Row]]:
    """Места как в спорте: при равенстве значений место одно (1, 1, 3)."""
    out: list[tuple[int, Row]] = []
    previous: int | None = None
    place = 0
    for index, row in enumerate(rows, start=1):
        if row.value != previous:
            place = index
            previous = row.value
        out.append((place, row))
    return out


def rating_rows(
    db: Session, me: User, metric: Metric, scope: Scope, template_id: int | None = None
) -> list[Row]:
    """Все участники выбранного списка по убыванию значения (с нулями только у друзей)."""
    if scope == "friends":
        ids = friend_ids(db, me.id) | {me.id}
        users = [u for u in db.scalars(select(User).where(User.id.in_(ids))) if not u.is_banned or u.id == me.id]
        return _rows(users, scores(db, users, metric))

    group = age_group(me)
    key = (metric, scope, template_id if scope == "habit" else None, group)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]
    candidates = [
        u
        for u in db.scalars(select(User).where(User.is_public.is_(True), User.is_banned.is_(False)))
        if age_group_of(u.birth_date, u.timezone) == group
    ]
    values = scores(db, candidates, metric, template_id if scope == "habit" else None)
    rows = [r for r in _rows(candidates, values) if r.value > 0]
    _cache[key] = (time.monotonic(), rows)
    return rows
