"""Пользователи, друзья, профиль."""

import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CheckIn, Friendship, HabitMember, User
from app.schemas.user import MeOut, PersonOut
from app.services import timeutil
from app.services.age import community_access
from app.services.streaks import activity_streaks

# Без похожих символов: нет 0/O и 1/I. 32 символа в 8 позициях — больше триллиона кодов.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def generate_friend_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if db.scalar(select(User.id).where(User.friend_code == code)) is None:
            return code


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def avatar_url(user: User) -> str | None:
    return f"/media/avatars/{user.avatar_path}" if user.avatar_path else None


def person_out(user: User) -> PersonOut:
    return PersonOut(id=user.id, name=user.name, avatar_url=avatar_url(user))


def friend_ids(db: Session, user_id: int) -> set[int]:
    rows = db.execute(
        select(Friendship.user_id, Friendship.friend_id).where(
            Friendship.status == "accepted",
            or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
        )
    ).all()
    return {b if a == user_id else a for a, b in rows}


def are_friends(db: Session, user_id: int, other_id: int) -> bool:
    return other_id in friend_ids(db, user_id)


def build_me(db: Session, user: User) -> MeOut:
    done_days = set(
        db.scalars(
            select(CheckIn.local_date).where(CheckIn.user_id == user.id, CheckIn.status == "done")
        )
    )
    streak, best = activity_streaks(done_days, timeutil.local_today(user.timezone))
    habits_count = db.scalar(
        select(func.count())
        .select_from(HabitMember)
        .where(HabitMember.user_id == user.id, HabitMember.status == "active")
    )
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        last_name=user.last_name,
        bio=user.bio,
        birth_date=user.birth_date,
        gender=user.gender,
        avatar_url=avatar_url(user),
        friend_code=user.friend_code,
        timezone=user.timezone,
        friends_count=len(friend_ids(db, user.id)),
        habits_count=habits_count or 0,
        streak=streak,
        best_streak=best,
        is_public=bool(user.is_public),
        community=community_access(user),
    )
