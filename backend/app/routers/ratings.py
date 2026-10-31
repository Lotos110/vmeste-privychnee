from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.deps import DB, CurrentUser
from app.models import HabitTemplate
from app.schemas.rating import RatingMe, RatingOut, RatingRow
from app.schemas.user import PersonOut
from app.services import rating
from app.services.age import ACCESS_MESSAGES, community_access

router = APIRouter(tags=["rating"])


@router.get("/ratings", response_model=RatingOut)
def get_rating(
    user: CurrentUser,
    db: DB,
    metric: Annotated[Literal["streak", "week"], Query()] = "streak",
    scope: Annotated[Literal["friends", "global", "habit"], Query()] = "friends",
    template_id: int | None = None,
):
    if scope != "friends":
        access = community_access(user)
        if access != "ok":
            raise HTTPException(status_code=403, detail=ACCESS_MESSAGES[access])
    if scope == "habit":
        if template_id is None:
            raise HTTPException(status_code=422, detail="Выберите привычку")
        if db.get(HabitTemplate, template_id) is None:
            raise HTTPException(status_code=404, detail="Такой привычки нет")

    rows = rating.rating_rows(db, user, metric, scope, template_id)
    places = rating.ranked(rows)
    mine = next(((place, row) for place, row in places if row.user_id == user.id), None)
    if mine:
        me = RatingMe(rank=mine[0], value=mine[1].value, joined=True)
    else:  # вас нет в списке: показываем только ваше значение
        own = rating.scores(db, [user], metric, template_id if scope == "habit" else None)[user.id]
        me = RatingMe(rank=None, value=own, joined=user.is_public)
    items = [
        RatingRow(
            rank=place,
            person=PersonOut(id=row.user_id, name=row.name, avatar_url=row.avatar_url),
            value=row.value,
            is_me=row.user_id == user.id,
        )
        for place, row in places[: rating.TOP_SIZE]
    ]
    return RatingOut(
        metric=metric, scope=scope, template_id=template_id if scope == "habit" else None,
        total=len(rows), items=items, me=me,
    )
