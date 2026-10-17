from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import PersonOut

TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"
ICON_PATTERN = r"^[A-Z0-9_]{1,40}$"  # имя иконки Material, например MENU_BOOK
HabitColor = Literal["purple", "green", "orange", "blue", "red"]  # цвет привычки, выбранный пользователем


def _clean_schedule(value: list[int]) -> list[int]:
    days = sorted(set(value))
    if not days or any(d < 0 or d > 6 for d in days):
        raise ValueError("Расписание: дни недели от 0 (пн) до 6 (вс), хотя бы один")
    return days


class TemplateOut(BaseModel):
    id: int
    title: str
    icon: str
    category: str
    default_goal: str | None = None
    default_schedule: list[int]
    default_time: str | None = None


class HabitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    goal: str | None = Field(default=None, max_length=120)
    schedule: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    remind_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    template_id: int | None = None
    icon: str | None = Field(default=None, pattern=ICON_PATTERN)  # своя иконка (иначе — иконка шаблона)
    color: HabitColor | None = None
    invite_friend_ids: list[int] = Field(default_factory=list, max_length=10)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите название привычки")
        return value

    @field_validator("goal")
    @classmethod
    def _goal(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("schedule")
    @classmethod
    def _schedule(cls, value: list[int]) -> list[int]:
        return _clean_schedule(value)


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    goal: str | None = Field(default=None, max_length=120)
    schedule: list[int] | None = None
    remind_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    icon: str | None = Field(default=None, pattern=ICON_PATTERN)  # null сбрасывает на иконку шаблона
    color: HabitColor | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Укажите название привычки")
        return value

    @field_validator("schedule")
    @classmethod
    def _schedule(cls, value: list[int] | None) -> list[int] | None:
        return None if value is None else _clean_schedule(value)


class MemberOut(BaseModel):
    user_id: int
    name: str
    avatar_url: str | None = None
    status: Literal["invited", "active"]
    is_me: bool = False
    current_streak: int = 0
    best_streak: int = 0
    today_status: Literal["done", "missed", "pending", "off"] = "off"


class WeekDayOut(BaseModel):
    """Один из последних 7 дней привычки глазами того, кто смотрит."""

    date: date
    weekday: int  # 0 — понедельник ... 6 — воскресенье
    # done — выполнено, missed — срыв, none — по расписанию, но отметки нет, off — не по расписанию
    status: Literal["done", "missed", "none", "off"]


class HabitOut(BaseModel):
    id: int
    title: str
    goal: str | None = None
    schedule: list[int]
    remind_time: str | None = None
    template_id: int | None = None
    icon: str | None = None
    color: str | None = None  # свой цвет; пусто — цвет берётся по категории шаблона
    category: str | None = None
    created_by: int
    today: date  # «сегодня» в часовом поясе того, кто смотрит
    my_status: Literal["invited", "active"]
    today_status: Literal["done", "missed", "pending", "off"]
    current_streak: int
    best_streak: int
    shared_streak: int | None = None  # только если активных участников двое и больше
    week_done: int = 0  # за последние 7 дней
    week_planned: int = 0
    week_days: list[WeekDayOut] = []  # последние 7 дней по возрастанию, последний — «сегодня»
    members: list[MemberOut]


class InviteIn(BaseModel):
    friend_id: int


class CheckInIn(BaseModel):
    status: Literal["done", "missed"] = "done"
    local_date: date | None = None  # по умолчанию «сегодня» в часовом поясе пользователя
    miss_reason: str | None = Field(default=None, max_length=200)

    @field_validator("miss_reason")
    @classmethod
    def _reason(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class CalendarDay(BaseModel):
    date: date
    scheduled: bool
    status: Literal["done", "missed", "none"]


class CalendarOut(BaseModel):
    month: str  # YYYY-MM
    days: list[CalendarDay]


class NudgeIn(BaseModel):
    to_user_id: int
    text: str = Field(min_length=1, max_length=140)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Пустое сообщение")
        return value


class NudgeOut(BaseModel):
    id: int
    habit_id: int
    habit_title: str
    sender: PersonOut | None = None  # None — напоминание от приложения
    text: str
    kind: Literal["partner", "reminder", "risk"]
    created_at: datetime
    read: bool


class StatPoint(BaseModel):
    label: str
    date: date
    done: int
    planned: int
    percent: int | None = None  # None — день ещё не наступил или нечего выполнять


class StatsOut(BaseModel):
    period: Literal["week", "month", "all"]
    current_streak: int
    best_streak: int
    total_done: int
    completion_percent: int
    points: list[StatPoint]
