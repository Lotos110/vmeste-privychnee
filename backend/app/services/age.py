"""Возраст и возрастные группы для раздела «Поиск напарника» и публичного рейтинга.

Дата рождения приватна и нужна только здесь. Лента и общий рейтинг открыты с 12 лет, и подростки
(12–17) видят только подростков, а взрослые только взрослых. Без даты рождения разделы закрыты.
"""

from datetime import date
from typing import TYPE_CHECKING, Literal

from app.services import timeutil

if TYPE_CHECKING:
    from app.models import User

MIN_AGE = 12
ADULT_AGE = 18

AgeGroup = Literal["teen", "adult"]
CommunityAccess = Literal["ok", "need_birth_date", "too_young"]


def age_on(birth_date: date, today: date) -> int:
    years = today.year - birth_date.year
    return years - ((today.month, today.day) < (birth_date.month, birth_date.day))


def age_group_of(birth_date: date | None, timezone: str | None = None, today: date | None = None) -> AgeGroup | None:
    """None — раздел закрыт: даты рождения нет или человеку меньше 12 лет."""
    if birth_date is None:
        return None
    age = age_on(birth_date, today or timeutil.local_today(timezone))
    if age < MIN_AGE:
        return None
    return "adult" if age >= ADULT_AGE else "teen"


def age_group(user: "User") -> AgeGroup | None:
    return age_group_of(user.birth_date, user.timezone)


def community_access(user: "User") -> CommunityAccess:
    if user.birth_date is None:
        return "need_birth_date"
    return "ok" if age_group(user) else "too_young"


ACCESS_MESSAGES = {
    "need_birth_date": "Укажите дату рождения в профиле: раздел доступен с 12 лет",
    "too_young": "Этот раздел доступен с 12 лет",
}
