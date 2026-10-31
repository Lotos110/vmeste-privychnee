"""Лента «Поиск напарника»: объявления, отклики, жалобы и блокировки.

Раздел открыт с 12 лет; подростки (12–17) и взрослые (18+) друг друга не видят. Контакты в текстах
запрещены (services/moderation.py). Откликнуться можно один раз на объявление; если автор принимает
отклик, они становятся друзьями и дальше могут создать общую привычку.
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.deps import DB, CurrentUser
from app.models import (
    Friendship,
    HabitTemplate,
    Nudge,
    PartnerPost,
    PostResponse,
    Report,
    User,
    UserBlock,
)
from app.schemas.community import (
    BlockedOut,
    MyPostOut,
    PostCreate,
    PostOut,
    ReportIn,
    ResponseIn,
    ResponseOut,
)
from app.schemas.user import PersonOut
from app.services import moderation, timeutil
from app.services.age import ACCESS_MESSAGES, AgeGroup, age_group, community_access
from app.services.people import person_out

router = APIRouter(tags=["community"])

POST_LIFETIME_DAYS = 30
MAX_OPEN_POSTS = 3
MAX_POSTS_PER_DAY = 5
MAX_RESPONSES_PER_DAY = 10
HIDE_AFTER_REPORTS = 3  # столько разных жалоб скрывают объявление до проверки
FEED_LIMIT = 50


def gate(user: User) -> AgeGroup:
    access = community_access(user)
    if access != "ok":
        raise HTTPException(status_code=403, detail=ACCESS_MESSAGES[access])
    return age_group(user)  # type: ignore[return-value]


def blocked_ids(db: Session, user_id: int) -> set[int]:
    """Те, кого заблокировал человек, и те, кто заблокировал его: друг друга они не видят."""
    rows = db.execute(
        select(UserBlock.blocker_id, UserBlock.blocked_id).where(
            or_(UserBlock.blocker_id == user_id, UserBlock.blocked_id == user_id)
        )
    ).all()
    return {b if a == user_id else a for a, b in rows}


def _post_out(post: PartnerPost, responded: bool = False) -> PostOut:
    return PostOut(
        id=post.id,
        author=person_out(post.author),
        template_id=post.template_id,
        topic=post.topic,
        text=post.text,
        time_pref=post.time_pref,
        created_at=timeutil.as_utc(post.created_at),
        expires_at=timeutil.as_utc(post.expires_at),
        responded=responded,
    )


def _reject_text(text: str) -> None:
    reason = moderation.check_text(text)
    if reason:
        raise HTTPException(status_code=422, detail=reason)


def _count_since(db: Session, column, owner_clause, hours: int = 24) -> int:
    since = timeutil.utcnow() - timedelta(hours=hours)
    return db.scalar(select(func.count()).select_from(column.class_).where(owner_clause, column >= since)) or 0


# ---------- объявления ----------


@router.get("/partner-posts", response_model=list[PostOut])
def feed(
    user: CurrentUser,
    db: DB,
    template_id: int | None = None,
    time_pref: str | None = None,
    offset: int = 0,
):
    group = gate(user)
    query = (
        select(PartnerPost)
        .join(User, User.id == PartnerPost.author_id)
        .where(
            PartnerPost.status == "open",
            PartnerPost.expires_at > timeutil.utcnow(),
            PartnerPost.age_group == group,
            PartnerPost.author_id != user.id,
            User.is_banned.is_(False),
        )
    )
    hidden = blocked_ids(db, user.id)
    if hidden:
        query = query.where(PartnerPost.author_id.not_in(hidden))
    if template_id is not None:
        query = query.where(PartnerPost.template_id == template_id)
    if time_pref in ("morning", "day", "evening"):
        query = query.where(PartnerPost.time_pref.in_([time_pref, "any"]))
    posts = db.scalars(
        query.order_by(PartnerPost.created_at.desc(), PartnerPost.id.desc())
        .offset(max(offset, 0))
        .limit(FEED_LIMIT)
    ).all()
    responded = set(
        db.scalars(
            select(PostResponse.post_id).where(
                PostResponse.user_id == user.id, PostResponse.post_id.in_([p.id for p in posts])
            )
        )
    ) if posts else set()
    return [_post_out(p, p.id in responded) for p in posts]


@router.get("/partner-posts/mine", response_model=list[MyPostOut])
def my_posts(user: CurrentUser, db: DB):
    gate(user)
    posts = db.scalars(
        select(PartnerPost)
        .where(PartnerPost.author_id == user.id, PartnerPost.status.in_(["open", "hidden"]))
        .order_by(PartnerPost.created_at.desc(), PartnerPost.id.desc())
    ).all()
    hidden = blocked_ids(db, user.id)
    now = timeutil.utcnow()
    result = []
    for post in posts:
        responses = [
            ResponseOut(
                id=r.id,
                person=person_out(r.user),
                text=r.text,
                status=r.status,
                created_at=timeutil.as_utc(r.created_at),
            )
            for r in sorted(post.responses, key=lambda r: r.created_at, reverse=True)
            if r.status != "hidden" and r.user_id not in hidden and not r.user.is_banned
        ]
        result.append(
            MyPostOut(
                id=post.id,
                template_id=post.template_id,
                topic=post.topic,
                text=post.text,
                time_pref=post.time_pref,
                status=post.status,
                expired=timeutil.as_utc(post.expires_at) <= now,
                created_at=timeutil.as_utc(post.created_at),
                expires_at=timeutil.as_utc(post.expires_at),
                responses=responses,
            )
        )
    return result


@router.post("/partner-posts", response_model=PostOut, status_code=201)
def create_post(data: PostCreate, user: CurrentUser, db: DB):
    group = gate(user)
    if data.template_id is not None:
        template = db.get(HabitTemplate, data.template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Такой привычки нет")
        topic = template.title
    else:
        topic = data.topic or ""
        _reject_text(topic)
    _reject_text(data.text)

    now = timeutil.utcnow()
    open_count = db.scalar(
        select(func.count()).select_from(PartnerPost).where(
            PartnerPost.author_id == user.id, PartnerPost.status == "open", PartnerPost.expires_at > now
        )
    )
    if (open_count or 0) >= MAX_OPEN_POSTS:
        raise HTTPException(
            status_code=409, detail=f"Можно держать не больше {MAX_OPEN_POSTS} активных объявлений. Закройте лишнее"
        )
    if _count_since(db, PartnerPost.created_at, PartnerPost.author_id == user.id) >= MAX_POSTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Сегодня достаточно объявлений, попробуйте завтра")

    post = PartnerPost(
        author_id=user.id,
        template_id=data.template_id,
        topic=topic,
        text=data.text,
        time_pref=data.time_pref,
        age_group=group,
        status="open",
        created_at=now,
        expires_at=now + timedelta(days=POST_LIFETIME_DAYS),
    )
    db.add(post)
    db.commit()
    return _post_out(post)


def _own_post(db: Session, post_id: int, user: User) -> PartnerPost:
    post = db.get(PartnerPost, post_id)
    if post is None or post.author_id != user.id or post.status == "closed":
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return post


@router.delete("/partner-posts/{post_id}", status_code=204, response_class=Response)
def close_post(post_id: int, user: CurrentUser, db: DB):
    post = _own_post(db, post_id, user)
    post.status = "closed"
    db.commit()
    return Response(status_code=204)


def _visible_post(db: Session, post_id: int, user: User, group: AgeGroup) -> PartnerPost:
    """Объявление, которое этот человек вообще может видеть в ленте."""
    post = db.get(PartnerPost, post_id)
    if (
        post is None
        or post.status != "open"
        or timeutil.as_utc(post.expires_at) <= timeutil.utcnow()
        or post.age_group != group
        or post.author.is_banned
        or post.author_id in blocked_ids(db, user.id)
    ):
        raise HTTPException(status_code=404, detail="Объявление не найдено или уже закрыто")
    return post


# ---------- отклики ----------


@router.post("/partner-posts/{post_id}/respond", status_code=201, response_class=Response)
def respond(post_id: int, data: ResponseIn, user: CurrentUser, db: DB):
    group = gate(user)
    post = _visible_post(db, post_id, user, group)
    if post.author_id == user.id:
        raise HTTPException(status_code=400, detail="Это ваше объявление")
    already = db.scalar(
        select(PostResponse.id).where(PostResponse.post_id == post.id, PostResponse.user_id == user.id)
    )
    if already is not None:
        raise HTTPException(status_code=409, detail="Вы уже откликнулись на это объявление")
    if _count_since(db, PostResponse.created_at, PostResponse.user_id == user.id) >= MAX_RESPONSES_PER_DAY:
        raise HTTPException(status_code=429, detail="Сегодня достаточно откликов, попробуйте завтра")
    _reject_text(data.text)

    db.add(PostResponse(post_id=post.id, user_id=user.id, text=data.text, status="pending"))
    db.add(
        Nudge(
            habit_id=None,
            from_user=user.id,
            to_user=post.author_id,
            kind="response",
            text=f"Откликнулся на «{post.topic}»: {data.text}"[:200],
        )
    )
    db.commit()
    return Response(status_code=201)


def _pending_response(db: Session, post_id: int, response_id: int, user: User) -> tuple[PartnerPost, PostResponse]:
    post = _own_post(db, post_id, user)
    response = db.get(PostResponse, response_id)
    if response is None or response.post_id != post.id or response.status != "pending":
        raise HTTPException(status_code=404, detail="Отклик не найден")
    return post, response


@router.post("/partner-posts/{post_id}/responses/{response_id}/accept", response_model=PersonOut)
def accept_response(post_id: int, response_id: int, user: CurrentUser, db: DB):
    gate(user)
    post, response = _pending_response(db, post_id, response_id, user)
    other = response.user
    if other.is_banned or other.id in blocked_ids(db, user.id):
        raise HTTPException(status_code=404, detail="Отклик не найден")

    response.status = "accepted"
    friendship = db.scalar(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == user.id, Friendship.friend_id == other.id),
                and_(Friendship.user_id == other.id, Friendship.friend_id == user.id),
            )
        )
    )
    if friendship is None:
        db.add(Friendship(user_id=user.id, friend_id=other.id, status="accepted"))
    else:
        friendship.status = "accepted"
    db.add(
        Nudge(
            habit_id=None,
            from_user=user.id,
            to_user=other.id,
            kind="accepted",
            text=f"Принял(а) ваш отклик на «{post.topic}». Теперь вы друзья: можно создать общую привычку",
        )
    )
    db.commit()
    return person_out(other)


@router.post("/partner-posts/{post_id}/responses/{response_id}/decline", status_code=204, response_class=Response)
def decline_response(post_id: int, response_id: int, user: CurrentUser, db: DB):
    _, response = _pending_response(db, post_id, response_id, user)
    response.status = "declined"  # отказ молчаливый: человеку ничего не отправляем
    db.commit()
    return Response(status_code=204)


# ---------- жалобы и блокировки ----------


def _add_report(db: Session, user: User, target_type: str, target_id: int, reason: str) -> None:
    exists = db.scalar(
        select(Report.id).where(
            Report.reporter_id == user.id, Report.target_type == target_type, Report.target_id == target_id
        )
    )
    if exists is None:
        db.add(Report(reporter_id=user.id, target_type=target_type, target_id=target_id, reason=reason))
        db.flush()


@router.post("/partner-posts/{post_id}/report", status_code=204, response_class=Response)
def report_post(post_id: int, data: ReportIn, user: CurrentUser, db: DB):
    group = gate(user)
    post = _visible_post(db, post_id, user, group)
    if post.author_id == user.id:
        raise HTTPException(status_code=400, detail="Это ваше объявление")
    _add_report(db, user, "post", post.id, data.reason)
    distinct = db.scalar(
        select(func.count(func.distinct(Report.reporter_id))).where(
            Report.target_type == "post", Report.target_id == post.id
        )
    )
    if (distinct or 0) >= HIDE_AFTER_REPORTS:
        post.status = "hidden"  # до проверки в админке
    db.commit()
    return Response(status_code=204)


@router.post("/partner-responses/{response_id}/report", status_code=204, response_class=Response)
def report_response(response_id: int, data: ReportIn, user: CurrentUser, db: DB):
    """Жалоба автора объявления на отклик: отклик сразу скрывается, остальное решает модератор."""
    response = db.get(PostResponse, response_id)
    if response is None or response.post.author_id != user.id:
        raise HTTPException(status_code=404, detail="Отклик не найден")
    _add_report(db, user, "response", response.id, data.reason)
    response.status = "hidden"
    db.commit()
    return Response(status_code=204)


@router.get("/blocks", response_model=BlockedOut)
def list_blocks(user: CurrentUser, db: DB):
    people = db.scalars(
        select(User).join(UserBlock, UserBlock.blocked_id == User.id).where(UserBlock.blocker_id == user.id)
    ).all()
    return BlockedOut(blocked=[person_out(p) for p in people])


@router.post("/users/{other_id}/block", status_code=204, response_class=Response)
def block_user(other_id: int, user: CurrentUser, db: DB):
    if other_id == user.id:
        raise HTTPException(status_code=400, detail="Себя заблокировать нельзя")
    if db.get(User, other_id) is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if db.get(UserBlock, (user.id, other_id)) is None:
        db.add(UserBlock(blocker_id=user.id, blocked_id=other_id))
    friendship = db.scalar(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == user.id, Friendship.friend_id == other_id),
                and_(Friendship.user_id == other_id, Friendship.friend_id == user.id),
            )
        )
    )
    if friendship is not None:  # заблокированный перестаёт быть другом
        db.delete(friendship)
    db.commit()
    return Response(status_code=204)


@router.delete("/users/{other_id}/block", status_code=204, response_class=Response)
def unblock_user(other_id: int, user: CurrentUser, db: DB):
    block = db.get(UserBlock, (user.id, other_id))
    if block is not None:
        db.delete(block)
        db.commit()
    return Response(status_code=204)
