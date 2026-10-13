from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import MeOut
from app.services.timeutil import is_valid_timezone


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=60)
    timezone: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите имя")
        return value

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        # Неизвестный пояс от клиента не должен ломать регистрацию: возьмём UTC.
        if value is not None and not is_valid_timezone(value):
            return None
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MeOut
