from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from app import ratelimit
from app.deps import DB, CurrentUser
from app.models import User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut
from app.security import create_token, decode_token, hash_password, verify_password
from app.services.people import build_me, generate_friend_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(db, user: User) -> TokenOut:
    return TokenOut(
        access_token=create_token(user.id, "access", user.token_version),
        refresh_token=create_token(user.id, "refresh", user.token_version),
        user=build_me(db, user),
    )


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=201,
    dependencies=[Depends(ratelimit.register_limiter.by_ip("register"))],
)
def register(data: RegisterIn, db: DB):
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован")
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        name=data.name,
        timezone=data.timezone or "UTC",
        friend_code=generate_friend_code(db),
    )
    db.add(user)
    db.commit()
    return _token_response(db, user)


@router.post(
    "/login",
    response_model=TokenOut,
    dependencies=[Depends(ratelimit.login_limiter.by_ip("login"))],
)
def login(data: LoginIn, db: DB):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    password_ok = verify_password(data.password, user.password_hash if user else None)
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return _token_response(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: DB):
    payload = decode_token(data.refresh_token, "refresh")
    user = db.get(User, int(payload["sub"])) if payload else None
    if user is None or payload.get("tv") != user.token_version:
        raise HTTPException(status_code=401, detail="Сессия истекла, войдите заново")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return _token_response(db, user)


@router.post("/logout", status_code=204, response_class=Response)
def logout(user: CurrentUser, db: DB):
    """Отзывает все выданные токены пользователя (на всех устройствах)."""
    user.token_version += 1
    db.commit()
    return Response(status_code=204)
