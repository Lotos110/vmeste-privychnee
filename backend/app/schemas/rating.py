from typing import Literal

from pydantic import BaseModel

from app.schemas.user import PersonOut


class RatingRow(BaseModel):
    rank: int
    person: PersonOut
    value: int
    is_me: bool = False


class RatingMe(BaseModel):
    rank: int | None = None  # None — вас нет в списке (не участвуете или пока нет отметок)
    value: int
    joined: bool  # участвует ли в общем рейтинге (для друзей всегда true)


class RatingOut(BaseModel):
    metric: Literal["streak", "week"]
    scope: Literal["friends", "global", "habit"]
    template_id: int | None = None
    total: int
    items: list[RatingRow]
    me: RatingMe
