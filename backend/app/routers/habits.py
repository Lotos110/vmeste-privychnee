import calendar
import re
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import DB, CurrentUser
from app.models import CheckIn, Habit, HabitMember, HabitTemplate, Nudge
from app.schemas.habit import (
    CalendarDay,
    CalendarOut,
    CheckInIn,
    HabitCreate,
    HabitOut,
    HabitUpdate,
    InviteIn,
    NudgeIn,
    NudgeOut,
    TemplateOut,
)
from app.services import timeutil
from app.services.habits import (
    get_member_or_404,
    parse_time,
    refresh_member_cache,
    serialize_habit,
    serialize_habits,
    user_habits,
)
from app.services.people import friend_ids, person_out

router = APIRouter(tags=["habits"])

MAX_BACKFILL_DAYS = 7
MAX_NUDGES_PER_DAY = 10


# ---------- шаблоны ----------


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: DB):
    templates = db.scalars(select(HabitTemplate).order_by(HabitTemplate.position, HabitTemplate.id))
    return [
        TemplateOut(
            id=t.id,
            title=t.title,
            icon=t.icon,
            category=t.category,
            default_goal=t.default_goal,
            default_schedule=list(t.default_schedule),
            default_time=t.default_time,
        )
        for t in templates
    ]


# ---------- привычки ----------


@router.get("/habits", response_model=list[HabitOut])
def list_habits(user: CurrentUser, db: DB):
    """Мои привычки со статусом «сегодня»."""
    return serialize_habits(db, user, user_habits(db, user, "active"))


@router.get("/invites", response_model=list[HabitOut])
def list_invites(user: CurrentUser, db: DB):
    """Привычки, в которые меня пригласили друзья."""
    return serialize_habits(db, user, user_habits(db, user, "invited"))


@router.post("/habits", response_model=HabitOut, status_code=201)
def create_habit(data: HabitCreate, user: CurrentUser, db: DB):
    if data.template_id is not None and db.get(HabitTemplate, data.template_id) is None:
        raise HTTPException(status_code=422, detail="Шаблон не найден")

    invited_ids = {fid for fid in data.invite_friend_ids if fid != user.id}
    if not invited_ids <= friend_ids(db, user.id):
        raise HTTPException(status_code=400, detail="Приглашать можно только друзей")

    habit = Habit(
        creator_id=user.id,
        template_id=data.template_id,
        title=data.title,
        goal=data.goal,
        schedule=data.schedule,
        remind_time=parse_time(data.remind_time),
        icon=data.icon,
        color=data.color,
    )
    db.add(habit)
    db.flush()
    db.add(
        HabitMember(
            habit_id=habit.id,
            user_id=user.id,
            status="active",
            joined_date=timeutil.local_today(user.timezone),
        )
    )
    for friend_id in sorted(invited_ids):
        db.add(HabitMember(habit_id=habit.id, user_id=friend_id, status="invited"))
        db.add(_invite_nudge(habit, user.id, friend_id))
    db.commit()
    return serialize_habit(db, user, habit)


def _invite_nudge(habit: Habit, from_user: int, to_user: int) -> Nudge:
    return Nudge(
        habit_id=habit.id,
        from_user=from_user,
        to_user=to_user,
        kind="partner",
        text=f"Зовёт вас вместе формировать привычку «{habit.title}»",
    )


@router.get("/habits/{habit_id}", response_model=HabitOut)
def get_habit(habit_id: int, user: CurrentUser, db: DB):
    habit, _ = get_member_or_404(db, habit_id, user, allow_invited=True)
    return serialize_habit(db, user, habit)


@router.patch("/habits/{habit_id}", response_model=HabitOut)
def update_habit(habit_id: int, data: HabitUpdate, user: CurrentUser, db: DB):
    """Цель общая, поэтому править её может любой активный участник."""
    habit, member = get_member_or_404(db, habit_id, user)
    fields = data.model_dump(exclude_unset=True)
    if fields.get("title") is not None:
        habit.title = fields["title"]
    if "goal" in fields:
        habit.goal = (fields["goal"] or "").strip() or None
    if fields.get("schedule") is not None:
        habit.schedule = fields["schedule"]
    if "remind_time" in fields:
        habit.remind_time = parse_time(fields["remind_time"])
    if "icon" in fields:
        habit.icon = fields["icon"]
    if "color" in fields:
        habit.color = fields["color"]
    db.flush()
    refresh_member_cache(db, habit, member, user)
    db.commit()
    return serialize_habit(db, user, habit)


@router.delete("/habits/{habit_id}/membership", status_code=204, response_class=Response)
def leave_habit(habit_id: int, user: CurrentUser, db: DB):
    """Выйти из привычки. Когда не остаётся ни участников, ни приглашённых — привычка удаляется."""
    habit, member = get_member_or_404(db, habit_id, user, allow_invited=True)
    member.status = "left"
    db.flush()
    remaining = db.scalar(
        select(func.count())
        .select_from(HabitMember)
        .where(HabitMember.habit_id == habit.id, HabitMember.status.in_(("active", "invited")))
    )
    if not remaining:
        db.delete(habit)
    db.commit()
    return Response(status_code=204)


# ---------- совместный режим ----------


@router.post("/habits/{habit_id}/invite", response_model=HabitOut)
def invite_friend(habit_id: int, data: InviteIn, user: CurrentUser, db: DB):
    habit, _ = get_member_or_404(db, habit_id, user)
    if data.friend_id not in friend_ids(db, user.id):
        raise HTTPException(status_code=400, detail="Приглашать можно только друзей")
    existing = db.get(HabitMember, (habit.id, data.friend_id))
    if existing is not None and existing.status in ("active", "invited"):
        raise HTTPException(status_code=409, detail="Друг уже участвует или приглашён")
    if existing is None:
        db.add(HabitMember(habit_id=habit.id, user_id=data.friend_id, status="invited"))
    else:
        existing.status = "invited"
    db.add(_invite_nudge(habit, user.id, data.friend_id))
    db.commit()
    return serialize_habit(db, user, habit)


@router.post("/habits/{habit_id}/accept", response_model=HabitOut)
def accept_invite(habit_id: int, user: CurrentUser, db: DB):
    habit, member = get_member_or_404(db, habit_id, user, allow_invited=True)
    if member.status == "invited":
        member.status = "active"
        member.joined_date = timeutil.local_today(user.timezone)
        member.current_streak = member.best_streak = 0
        db.commit()
    return serialize_habit(db, user, habit)


@router.post("/habits/{habit_id}/decline", status_code=204, response_class=Response)
def decline_invite(habit_id: int, user: CurrentUser, db: DB):
    _, member = get_member_or_404(db, habit_id, user, allow_invited=True)
    if member.status == "invited":
        member.status = "left"
        db.commit()
    return Response(status_code=204)


@router.post("/habits/{habit_id}/nudges", status_code=201, response_class=Response)
def send_nudge(habit_id: int, data: NudgeIn, user: CurrentUser, db: DB):
    """Поддерживающее сообщение напарнику: «Не прерывай серию», «Ты сможешь»…"""
    habit, _ = get_member_or_404(db, habit_id, user)
    if data.to_user_id == user.id:
        raise HTTPException(status_code=400, detail="Напарнику, а не себе")
    target = db.get(HabitMember, (habit.id, data.to_user_id))
    if target is None or target.status != "active":
        raise HTTPException(status_code=404, detail="Напарник не найден")
    since = timeutil.utcnow() - timedelta(hours=24)
    sent = db.scalar(
        select(func.count())
        .select_from(Nudge)
        .where(Nudge.from_user == user.id, Nudge.habit_id == habit.id, Nudge.created_at >= since)
    )
    if (sent or 0) >= MAX_NUDGES_PER_DAY:
        raise HTTPException(status_code=429, detail="Сегодня достаточно сообщений, подождите")
    db.add(
        Nudge(
            habit_id=habit.id,
            from_user=user.id,
            to_user=data.to_user_id,
            kind="partner",
            text=data.text,
        )
    )
    db.commit()
    return Response(status_code=201)


@router.get("/nudges", response_model=list[NudgeOut])
def list_nudges(user: CurrentUser, db: DB):
    nudges = db.scalars(
        select(Nudge)
        .where(Nudge.to_user == user.id)
        .options(selectinload(Nudge.habit), selectinload(Nudge.sender))
        .order_by(Nudge.created_at.desc(), Nudge.id.desc())
        .limit(50)
    ).all()
    return [
        NudgeOut(
            id=n.id,
            habit_id=n.habit_id,
            habit_title=n.habit.title,
            sender=person_out(n.sender) if n.sender else None,
            text=n.text,
            kind=n.kind,
            created_at=timeutil.as_utc(n.created_at),
            read=n.read_at is not None,
        )
        for n in nudges
    ]


@router.post("/nudges/read", status_code=204, response_class=Response)
def mark_nudges_read(user: CurrentUser, db: DB):
    now = timeutil.utcnow()
    unread = db.scalars(select(Nudge).where(Nudge.to_user == user.id, Nudge.read_at.is_(None))).all()
    for nudge in unread:
        nudge.read_at = now
    db.commit()
    return Response(status_code=204)


# ---------- отметки ----------


@router.post("/habits/{habit_id}/check-ins", response_model=HabitOut)
def check_in(habit_id: int, data: CheckInIn, user: CurrentUser, db: DB):
    habit, member = get_member_or_404(db, habit_id, user)
    today = timeutil.local_today(user.timezone)
    day = data.local_date or today
    if day > today:
        raise HTTPException(status_code=400, detail="Нельзя отметить будущий день")
    if day < today - timedelta(days=MAX_BACKFILL_DAYS):
        raise HTTPException(status_code=400, detail="Отметить можно не более чем за 7 дней")
    if day < (member.joined_date or today):
        raise HTTPException(status_code=400, detail="Нельзя отметить день до начала привычки")

    row = db.scalar(
        select(CheckIn).where(
            CheckIn.habit_id == habit.id, CheckIn.user_id == user.id, CheckIn.local_date == day
        )
    )
    reason = data.miss_reason if data.status == "missed" else None
    if row is None:
        db.add(
            CheckIn(
                habit_id=habit.id,
                user_id=user.id,
                local_date=day,
                status=data.status,
                miss_reason=reason,
            )
        )
    else:
        row.status = data.status
        row.miss_reason = reason
    db.flush()
    refresh_member_cache(db, habit, member, user)
    db.commit()
    return serialize_habit(db, user, habit)


@router.delete("/habits/{habit_id}/check-ins/{local_date}", response_model=HabitOut)
def undo_check_in(habit_id: int, local_date: date, user: CurrentUser, db: DB):
    habit, member = get_member_or_404(db, habit_id, user)
    row = db.scalar(
        select(CheckIn).where(
            CheckIn.habit_id == habit.id,
            CheckIn.user_id == user.id,
            CheckIn.local_date == local_date,
        )
    )
    if row is not None:
        db.delete(row)
        db.flush()
        refresh_member_cache(db, habit, member, user)
        db.commit()
    return serialize_habit(db, user, habit)


MONTH_RE = re.compile(r"^(?!0000)\d{4}-(0[1-9]|1[0-2])$")


@router.get("/habits/{habit_id}/calendar", response_model=CalendarOut)
def habit_calendar(
    habit_id: int,
    user: CurrentUser,
    db: DB,
    month: str | None = Query(default=None, description="YYYY-MM, по умолчанию текущий месяц"),
):
    habit, _ = get_member_or_404(db, habit_id, user)
    if month is None:
        today = timeutil.local_today(user.timezone)
        year, mon = today.year, today.month
    elif MONTH_RE.match(month):
        year, mon = int(month[:4]), int(month[5:])
    else:
        raise HTTPException(status_code=422, detail="Месяц нужен в формате ГГГГ-ММ")

    days_in_month = calendar.monthrange(year, mon)[1]
    first, last = date(year, mon, 1), date(year, mon, days_in_month)
    statuses = dict(
        db.execute(
            select(CheckIn.local_date, CheckIn.status).where(
                CheckIn.habit_id == habit.id,
                CheckIn.user_id == user.id,
                CheckIn.local_date >= first,
                CheckIn.local_date <= last,
            )
        ).all()
    )
    schedule = set(habit.schedule)
    days = []
    for number in range(1, days_in_month + 1):
        day = date(year, mon, number)
        days.append(
            CalendarDay(
                date=day,
                scheduled=day.weekday() in schedule,
                status=statuses.get(day, "none"),
            )
        )
    return CalendarOut(month=f"{year:04d}-{mon:02d}", days=days)
