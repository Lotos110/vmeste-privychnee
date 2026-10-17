"""Привычки: доступ, сборка ответов для API, пересчёт кэша серий."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CheckIn, Habit, HabitMember, HabitTemplate, User
from app.schemas.habit import HabitOut, MemberOut, WeekDayOut
from app.services import timeutil
from app.services.people import avatar_url
from app.services.streaks import compute_streaks, shared_streak, today_status

NOT_FOUND = "Привычка не найдена"


def format_time(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def parse_time(value: str | None) -> time | None:
    if not value:
        return None
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def get_member_or_404(
    db: Session, habit_id: int, user: User, *, allow_invited: bool = False
) -> tuple[Habit, HabitMember]:
    """Проверка доступа: чужую или несуществующую привычку не отличаем (всегда 404)."""
    member = db.get(HabitMember, (habit_id, user.id))
    allowed = ("active", "invited") if allow_invited else ("active",)
    if member is None or member.status not in allowed:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    habit = db.get(Habit, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return habit, member


def _load_check_ins(
    db: Session, habit_ids: list[int]
) -> dict[tuple[int, int], tuple[set[date], set[date]]]:
    """{(habit_id, user_id): (даты «выполнено», даты «срыв»)}"""
    rows = db.execute(
        select(CheckIn.habit_id, CheckIn.user_id, CheckIn.local_date, CheckIn.status).where(
            CheckIn.habit_id.in_(habit_ids)
        )
    ).all()
    result: dict[tuple[int, int], tuple[set[date], set[date]]] = defaultdict(
        lambda: (set(), set())
    )
    for habit_id, user_id, day, status in rows:
        result[(habit_id, user_id)][0 if status == "done" else 1].add(day)
    return result


def serialize_habits(
    db: Session, viewer: User, habits: list[Habit], now: datetime | None = None
) -> list[HabitOut]:
    if not habits:
        return []
    now = now or timeutil.utcnow()
    habit_ids = [h.id for h in habits]

    members_by_habit: dict[int, list[HabitMember]] = defaultdict(list)
    members = db.scalars(
        select(HabitMember)
        .where(HabitMember.habit_id.in_(habit_ids), HabitMember.status.in_(("invited", "active")))
        .options(selectinload(HabitMember.user))
    ).all()
    for member in members:
        members_by_habit[member.habit_id].append(member)

    check_ins = _load_check_ins(db, habit_ids)
    template_ids = {h.template_id for h in habits if h.template_id}
    templates = (
        {t.id: t for t in db.scalars(select(HabitTemplate).where(HabitTemplate.id.in_(template_ids)))}
        if template_ids
        else {}
    )
    viewer_today = timeutil.local_today(viewer.timezone, now)

    result: list[HabitOut] = []
    for habit in habits:
        schedule = list(habit.schedule)
        member_items: list[MemberOut] = []
        active_done: list[set[date]] = []
        active_missed: list[set[date]] = []
        active_starts: list[date] = []
        mine: MemberOut | None = None
        mine_done: set[date] = set()
        mine_missed: set[date] = set()
        mine_start = viewer_today

        for member in sorted(members_by_habit[habit.id], key=lambda m: m.user_id):
            user = member.user
            done, missed = check_ins.get((habit.id, member.user_id), (set(), set()))
            item = MemberOut(
                user_id=user.id,
                name=user.name,
                avatar_url=avatar_url(user),
                status=member.status,
                is_me=user.id == viewer.id,
            )
            if member.status == "active":
                user_today = timeutil.local_today(user.timezone, now)
                start = min(member.joined_date or user_today, user_today)
                item.current_streak, item.best_streak = compute_streaks(
                    done, missed, schedule, start, user_today
                )
                item.today_status = today_status(done, missed, schedule, user_today)
                active_done.append(done)
                active_missed.append(missed)
                active_starts.append(start)
                if user.id == viewer.id:
                    mine_done, mine_missed, mine_start = done, missed, start
            member_items.append(item)
            if user.id == viewer.id:
                mine = item

        if mine is None:  # не должно случаться: вызываем только для привычек пользователя
            continue

        shared = None
        if len(active_done) >= 2:
            shared = shared_streak(
                active_done, active_missed, schedule, min(max(active_starts), viewer_today), viewer_today
            )

        window_start = max(mine_start, viewer_today - timedelta(days=6))
        week_planned = week_done = 0
        day = window_start
        while day <= viewer_today:
            if day.weekday() in schedule:
                week_planned += 1
                if day in mine_done:
                    week_done += 1
            day += timedelta(days=1)

        week_days: list[WeekDayOut] = []
        for back in range(6, -1, -1):
            day = viewer_today - timedelta(days=back)
            if day in mine_done:
                day_status = "done"
            elif day in mine_missed:
                day_status = "missed"
            elif day < mine_start or day.weekday() not in schedule:
                day_status = "off"
            else:
                day_status = "none"
            week_days.append(WeekDayOut(date=day, weekday=day.weekday(), status=day_status))

        template = templates.get(habit.template_id) if habit.template_id else None
        result.append(
            HabitOut(
                id=habit.id,
                title=habit.title,
                goal=habit.goal,
                schedule=schedule,
                remind_time=format_time(habit.remind_time),
                template_id=habit.template_id,
                icon=template.icon if template else None,
                category=template.category if template else None,
                created_by=habit.creator_id,
                today=viewer_today,
                my_status=mine.status,
                today_status=mine.today_status,
                current_streak=mine.current_streak,
                best_streak=mine.best_streak,
                shared_streak=shared,
                week_done=week_done,
                week_planned=week_planned,
                week_days=week_days,
                members=member_items,
            )
        )
    return result


def serialize_habit(db: Session, viewer: User, habit: Habit) -> HabitOut:
    items = serialize_habits(db, viewer, [habit])
    if not items:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return items[0]


def refresh_member_cache(
    db: Session, habit: Habit, member: HabitMember, user: User, now: datetime | None = None
) -> None:
    """Пересчитывает кэш current_streak/best_streak участника (коммит делает вызывающий)."""
    rows = db.execute(
        select(CheckIn.local_date, CheckIn.status).where(
            CheckIn.habit_id == habit.id, CheckIn.user_id == user.id
        )
    ).all()
    done = {d for d, s in rows if s == "done"}
    missed = {d for d, s in rows if s == "missed"}
    today = timeutil.local_today(user.timezone, now)
    start = min(member.joined_date or today, today)
    member.current_streak, member.best_streak = compute_streaks(
        done, missed, list(habit.schedule), start, today
    )


def user_habits(db: Session, user: User, status: str = "active") -> list[Habit]:
    return list(
        db.scalars(
            select(Habit)
            .join(HabitMember, HabitMember.habit_id == Habit.id)
            .where(HabitMember.user_id == user.id, HabitMember.status == status)
            .order_by(Habit.id)
        )
    )
