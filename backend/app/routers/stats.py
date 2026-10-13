from typing import Literal

from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.schemas.habit import StatsOut
from app.services.stats import build_stats

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def get_stats(user: CurrentUser, db: DB, period: Literal["week", "month", "all"] = "week"):
    return build_stats(db, user, period)
