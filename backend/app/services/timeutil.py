"""Время. День отметки всегда локальный: считается по часовому поясу пользователя."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def utcnow() -> datetime:
    """Текущее время UTC. Везде вызываем как timeutil.utcnow(), чтобы в тестах подменять."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite отдаёт datetime без часового пояса; считаем такие значения UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return False
    return True


def local_now(tz_name: str | None, now: datetime | None = None) -> datetime:
    return (now or utcnow()).astimezone(get_zone(tz_name))


def local_today(tz_name: str | None, now: datetime | None = None) -> date:
    return local_now(tz_name, now).date()
