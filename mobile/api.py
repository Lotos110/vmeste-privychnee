"""Клиент к серверу (httpx): запросы, хранение токенов, автоматическое обновление токена."""

import os
import threading
from datetime import datetime, timedelta, timezone

import httpx

import config

ACCESS_KEY = "vmeste.access"
REFRESH_KEY = "vmeste.refresh"

FIELD_MESSAGES = {
    "email": "Проверьте адрес электронной почты",
    "password": "Пароль: не менее 8 символов",
    "name": "Укажите имя",
    "title": "Укажите название привычки",
    "code": "Проверьте код",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def detect_timezone() -> str:
    """Часовой пояс устройства: IANA-имя, а если не удалось определить — смещение от UTC."""
    try:
        import tzlocal  # необязательная зависимость

        name = str(tzlocal.get_localzone_name())
        if name:
            return name
    except Exception:
        pass
    offset = datetime.now(timezone.utc).astimezone().utcoffset() or timedelta(0)
    hours = offset.total_seconds() / 3600
    if hours == int(hours) and -12 <= hours <= 14:
        hours = int(hours)
        # В названиях Etc/GMT знак обратный: UTC+7 это «Etc/GMT-7»
        return "UTC" if hours == 0 else f"Etc/GMT{-hours:+d}"
    return "UTC"


class Storage:
    """Обёртка над page.client_storage; если хранилище недоступно, держим значения в памяти."""

    def __init__(self, client_storage=None):
        self._storage = client_storage
        self._memory: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        try:
            if self._storage is not None:
                value = self._storage.get(key)
                if value is not None:
                    return str(value)
        except Exception:
            pass
        return self._memory.get(key)

    def set(self, key: str, value: str) -> None:
        self._memory[key] = value
        try:
            if self._storage is not None:
                self._storage.set(key, value)
        except Exception:
            pass

    def remove(self, key: str) -> None:
        self._memory.pop(key, None)
        try:
            if self._storage is not None:
                self._storage.remove(key)
        except Exception:
            pass


class Api:
    def __init__(self, storage: Storage, on_auth_lost=None):
        self.storage = storage
        self.on_auth_lost = on_auth_lost
        self.client = httpx.Client(timeout=config.REQUEST_TIMEOUT)
        self._lock = threading.Lock()
        self.access: str | None = storage.get(ACCESS_KEY)
        self.refresh_token: str | None = storage.get(REFRESH_KEY)

    # ---------- адрес и сессия ----------

    @property
    def base_url(self) -> str:
        return config.DEFAULT_API_URL.rstrip("/")

    def media_url(self, path: str | None) -> str | None:
        if not path:
            return None
        return path if path.startswith("http") else f"{self.base_url}{path}"

    def has_session(self) -> bool:
        return bool(self.refresh_token)

    def save_tokens(self, access: str, refresh: str) -> None:
        self.access, self.refresh_token = access, refresh
        self.storage.set(ACCESS_KEY, access)
        self.storage.set(REFRESH_KEY, refresh)

    def clear_tokens(self) -> None:
        self.access = self.refresh_token = None
        self.storage.remove(ACCESS_KEY)
        self.storage.remove(REFRESH_KEY)

    # ---------- запросы ----------

    def request(self, method: str, path: str, *, json=None, params=None, files=None, auth=True):
        response = self._send(method, path, json, params, files, auth)
        if response.status_code == 401 and auth and self._refresh_tokens():
            response = self._send(method, path, json, params, files, auth)
        if response.status_code == 401 and auth:
            self.clear_tokens()
            if self.on_auth_lost:
                self.on_auth_lost()
        if response.status_code >= 400:
            raise ApiError(response.status_code, self._message(response))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _send(self, method, path, json, params, files, auth) -> httpx.Response:
        headers = {}
        if auth and self.access:
            headers["Authorization"] = f"Bearer {self.access}"
        try:
            return self.client.request(
                method, self.base_url + path, json=json, params=params, files=files, headers=headers
            )
        except httpx.HTTPError as exc:
            raise ApiError(
                0, f"Нет связи с сервером. Проверьте интернет и попробуйте ещё раз."
            ) from exc

    def _refresh_tokens(self) -> bool:
        with self._lock:
            if not self.refresh_token:
                return False
            try:
                response = self.client.post(
                    self.base_url + "/auth/refresh", json={"refresh_token": self.refresh_token}
                )
            except httpx.HTTPError:
                return False
            if response.status_code != 200:
                return False
            data = response.json()
            self.save_tokens(data["access_token"], data["refresh_token"])
            return True

    @staticmethod
    def _message(response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = None
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            first = detail[0]
            loc = first.get("loc", []) if isinstance(first, dict) else []
            for part in reversed(loc):
                if part in FIELD_MESSAGES:
                    return FIELD_MESSAGES[part]
            message = first.get("msg", "") if isinstance(first, dict) else ""
            if message.startswith("Value error, "):
                return message[len("Value error, ") :]
        return "Не удалось выполнить запрос. Проверьте введённые данные."

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self.request("POST", path, json=json, **kwargs)

    def patch(self, path, json=None, **kwargs):
        return self.request("PATCH", path, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    # ---------- авторизация ----------

    def register(self, email: str, password: str, name: str) -> dict:
        """Возвращает ответ сервера: user и recovery_code (код восстановления, его показывают один раз)."""
        data = self.post(
            "/auth/register",
            {"email": email, "password": password, "name": name, "timezone": detect_timezone()},
            auth=False,
        )
        self.save_tokens(data["access_token"], data["refresh_token"])
        return data

    def reset_password(self, email: str, recovery_code: str, new_password: str) -> dict:
        """Новый пароль по коду восстановления. Возвращает user и новый recovery_code, вход выполняется сразу."""
        data = self.post(
            "/auth/reset-password",
            {"email": email, "recovery_code": recovery_code, "new_password": new_password},
            auth=False,
        )
        self.save_tokens(data["access_token"], data["refresh_token"])
        return data

    def login(self, email: str, password: str) -> dict:
        data = self.post("/auth/login", {"email": email, "password": password}, auth=False)
        self.save_tokens(data["access_token"], data["refresh_token"])
        return data["user"]

    def logout(self) -> None:
        try:
            self.post("/auth/logout")
        except ApiError:
            pass
        self.clear_tokens()

    def upload_avatar(self, path: str) -> dict:
        with open(path, "rb") as handle:
            return self.request("POST", "/me/avatar", files={"file": (os.path.basename(path), handle)})
