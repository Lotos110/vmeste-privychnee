from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from app import ratelimit
from app.deps import DB, CurrentUser
from app.models import User
from app.schemas.auth import (
    LoginIn,
    PasswordConfirmIn,
    RecoveryCodeOut,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
)
from app.security import (
    create_token,
    decode_token,
    generate_recovery_code,
    hash_password,
    normalize_recovery_code,
    verify_password,
)
from app.services.people import build_me, generate_friend_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(db, user: User, recovery_code: str | None = None) -> TokenOut:
    return TokenOut(
        access_token=create_token(user.id, "access", user.token_version),
        refresh_token=create_token(user.id, "refresh", user.token_version),
        user=build_me(db, user),
        recovery_code=recovery_code,
    )


def _issue_recovery_code(user: User) -> str:
    """Создаёт новый код восстановления, хранит только его хэш и возвращает сам код (показать один раз)."""
    code = generate_recovery_code()
    user.recovery_hash = hash_password(normalize_recovery_code(code))
    return code


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
    recovery_code = _issue_recovery_code(user)
    db.add(user)
    db.commit()
    return _token_response(db, user, recovery_code)


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


@router.post(
    "/reset-password",
    response_model=TokenOut,
    dependencies=[Depends(ratelimit.reset_limiter.by_ip("reset"))],
)
def reset_password(data: ResetPasswordIn, db: DB):
    """Новый пароль по коду восстановления. Все прежние входы отзываются, код после использования сгорает:
    в ответе приходит новый код (его нужно сохранить)."""
    email = data.email.lower()
    ratelimit.reset_email_limiter.hit(email)
    user = db.scalar(select(User).where(User.email == email))
    # проверяем код и для несуществующего email (с хэшем-пустышкой): ответ и время не выдают, есть ли аккаунт
    code_ok = verify_password(
        normalize_recovery_code(data.recovery_code), user.recovery_hash if user else None
    )
    if user is None or not code_ok:
        raise HTTPException(status_code=400, detail="Неверный email или код восстановления")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    recovery_code = _issue_recovery_code(user)
    db.commit()
    return _token_response(db, user, recovery_code)


@router.post(
    "/recovery-code",
    response_model=RecoveryCodeOut,
    dependencies=[Depends(ratelimit.recovery_code_limiter.by_ip("recovery"))],
)
def new_recovery_code(data: PasswordConfirmIn, user: CurrentUser, db: DB):
    """Новый код восстановления (для старых аккаунтов или если прежний потерян). Нужен пароль; прежний код перестаёт работать."""
    if not verify_password(data.password, user.password_hash):
        # 403, а не 401: клиент при 401 считает сессию потерянной и выходит из аккаунта
        raise HTTPException(status_code=403, detail="Неверный пароль")
    code = _issue_recovery_code(user)
    db.commit()
    return RecoveryCodeOut(recovery_code=code)


@router.post("/logout", status_code=204, response_class=Response)
def logout(user: CurrentUser, db: DB):
    """Отзывает все выданные токены пользователя (на всех устройствах)."""
    user.token_version += 1
    db.commit()
    return Response(status_code=204)
