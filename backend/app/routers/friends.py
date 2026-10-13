from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import and_, or_, select

from app import ratelimit
from app.deps import DB, CurrentUser
from app.models import Friendship, User
from app.schemas.user import FriendCodeIn, FriendRequestOut, FriendsOut
from app.services.people import normalize_code, person_out

router = APIRouter(prefix="/friends", tags=["friends"])


def _between(a: int, b: int):
    return or_(
        and_(Friendship.user_id == a, Friendship.friend_id == b),
        and_(Friendship.user_id == b, Friendship.friend_id == a),
    )


@router.get("", response_model=FriendsOut)
def list_friends(user: CurrentUser, db: DB):
    rows = db.scalars(
        select(Friendship).where(or_(Friendship.user_id == user.id, Friendship.friend_id == user.id))
    ).all()
    other_ids = {f.friend_id if f.user_id == user.id else f.user_id for f in rows}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(other_ids)))} if other_ids else {}

    friends, incoming, outgoing = [], [], []
    for f in rows:
        other = people.get(f.friend_id if f.user_id == user.id else f.user_id)
        if other is None or other.is_banned:
            continue
        if f.status == "accepted":
            friends.append(person_out(other))
        elif f.user_id == user.id:
            outgoing.append(person_out(other))
        else:
            incoming.append(person_out(other))
    return FriendsOut(friends=friends, incoming=incoming, outgoing=outgoing)


@router.post("/by-code", response_model=FriendRequestOut)
def add_by_code(data: FriendCodeIn, user: CurrentUser, db: DB):
    # Частота ограничена, чтобы коды нельзя было перебрать.
    ratelimit.code_limiter.hit(f"code:{user.id}")
    code = normalize_code(data.code)
    other = db.scalar(select(User).where(User.friend_code == code))
    if other is None or other.is_banned:
        raise HTTPException(status_code=404, detail="Пользователь с таким кодом не найден")
    if other.id == user.id:
        raise HTTPException(status_code=400, detail="Это ваш собственный код")

    existing = db.scalar(select(Friendship).where(_between(user.id, other.id)))
    if existing is None:
        db.add(Friendship(user_id=user.id, friend_id=other.id, status="pending"))
        status = "pending"
    elif existing.status == "accepted":
        status = "accepted"
    elif existing.friend_id == user.id:  # встречная заявка: подтверждаем дружбу
        existing.status = "accepted"
        status = "accepted"
    else:
        status = "pending"
    db.commit()
    return FriendRequestOut(status=status, person=person_out(other))


@router.post("/{other_id}/accept", response_model=FriendRequestOut)
def accept(other_id: int, user: CurrentUser, db: DB):
    friendship = db.scalar(
        select(Friendship).where(
            Friendship.user_id == other_id,
            Friendship.friend_id == user.id,
            Friendship.status == "pending",
        )
    )
    other = db.get(User, other_id)
    if friendship is None or other is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    friendship.status = "accepted"
    db.commit()
    return FriendRequestOut(status="accepted", person=person_out(other))


@router.delete("/{other_id}", status_code=204, response_class=Response)
def remove(other_id: int, user: CurrentUser, db: DB):
    """Отклонить заявку, отменить свою или удалить из друзей."""
    friendship = db.scalar(select(Friendship).where(_between(user.id, other_id)))
    if friendship is None:
        raise HTTPException(status_code=404, detail="Не найдено")
    db.delete(friendship)
    db.commit()
    return Response(status_code=204)
