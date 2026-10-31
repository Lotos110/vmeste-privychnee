from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.user import PersonOut

TimePref = Literal["morning", "day", "evening", "any"]
ReportReason = Literal["contacts", "rude", "adult", "spam", "other"]


def _clean(value: str) -> str:
    return " ".join(value.split())  # лишние пробелы и переносы строк не нужны


class PostCreate(BaseModel):
    template_id: int | None = None
    topic: str | None = Field(default=None, max_length=60)  # своя тема, если шаблон не выбран
    text: str = Field(min_length=10, max_length=300)
    time_pref: TimePref = "any"

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = _clean(value)
        if len(value) < 10:
            raise ValueError("Расскажите чуть подробнее: не меньше 10 символов")
        return value

    @field_validator("topic")
    @classmethod
    def _topic(cls, value: str | None) -> str | None:
        return _clean(value) or None if value else None

    @model_validator(mode="after")
    def _has_topic(self):
        if self.template_id is None and not self.topic:
            raise ValueError("Выберите привычку или впишите свою тему")
        return self


class ResponseIn(BaseModel):
    text: str = Field(min_length=2, max_length=200)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = _clean(value)
        if len(value) < 2:
            raise ValueError("Напишите пару слов автору")
        return value


class ReportIn(BaseModel):
    reason: ReportReason


class PostOut(BaseModel):
    id: int
    author: PersonOut
    template_id: int | None = None
    topic: str
    text: str
    time_pref: TimePref
    created_at: datetime
    expires_at: datetime
    responded: bool = False  # вы уже откликнулись


class ResponseOut(BaseModel):
    id: int
    person: PersonOut
    text: str
    status: Literal["pending", "accepted", "declined"]
    created_at: datetime


class MyPostOut(BaseModel):
    id: int
    template_id: int | None = None
    topic: str
    text: str
    time_pref: TimePref
    status: Literal["open", "hidden"]  # hidden — скрыто модерацией после жалоб
    expired: bool
    created_at: datetime
    expires_at: datetime
    responses: list[ResponseOut]


class BlockedOut(BaseModel):
    blocked: list[PersonOut]
