from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.timeutil import is_valid_timezone


class PersonOut(BaseModel):
    """То, что друзья видят друг о друге: только имя и аватар."""

    id: int
    name: str
    avatar_url: str | None = None


class MeOut(BaseModel):
    id: int
    email: str
    name: str
    last_name: str | None = None
    bio: str | None = None
    birth_date: date | None = None
    gender: Literal["female", "male"] | None = None
    avatar_url: str | None = None
    friend_code: str
    timezone: str
    friends_count: int = 0
    habits_count: int = 0
    streak: int = 0
    best_streak: int = 0
    is_public: bool = False  # участвует в общем рейтинге
    # доступ к ленте «Поиск напарника» и общему рейтингу: ok | need_birth_date | too_young (меньше 12 лет)
    community: Literal["ok", "need_birth_date", "too_young"] = "need_birth_date"


class MeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)
    bio: str | None = Field(default=None, max_length=300)
    birth_date: date | None = None
    gender: Literal["female", "male"] | None = None
    timezone: str | None = None
    is_public: bool | None = None

    @field_validator("name", "last_name", "bio")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("birth_date")
    @classmethod
    def _birth_date_in_past(cls, value: date | None) -> date | None:
        if value is not None and (value > date.today() or value.year < 1900):
            raise ValueError("Некорректная дата рождения")
        return value

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_timezone(value):
            raise ValueError("Неизвестный часовой пояс")
        return value


class FriendsOut(BaseModel):
    friends: list[PersonOut]
    incoming: list[PersonOut]  # хотят добавить вас
    outgoing: list[PersonOut]  # ваши заявки, которые ещё не приняли


class FriendCodeIn(BaseModel):
    code: str = Field(min_length=4, max_length=20)


class FriendRequestOut(BaseModel):
    status: Literal["pending", "accepted"]
    person: PersonOut
