"""Общие зависимости FastAPI: сессия БД и текущий пользователь."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Требуется вход в аккаунт",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise unauthorized
    user = db.get(User, int(payload["sub"]))
    if user is None or payload.get("tv") != user.token_version:
        raise unauthorized
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
