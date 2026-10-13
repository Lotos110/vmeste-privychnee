import os
import tempfile

# Настройки для тестов задаём ДО импорта приложения: база в памяти, без планировщика и админки.
os.environ.update(
    {
        "DATABASE_URL": "sqlite://",
        "MEDIA_DIR": tempfile.mkdtemp(prefix="vmeste-media-"),
        "RUN_SCHEDULER": "false",
        "AUTO_CREATE_TABLES": "false",
        "ADMIN_PASSWORD": "",
        "ENVIRONMENT": "development",
        "SECRET_KEY": "test-secret-key-test-secret-key-0123456789",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_content  # noqa: E402
from app.services import timeutil  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_content(db)
    ratelimit.reset_all()
    yield


@pytest.fixture
def client():
    return TestClient(app)  # без «with»: lifespan (планировщик, сидирование) не нужен


@pytest.fixture
def freeze(monkeypatch):
    """freeze(datetime) подменяет «сейчас» для бизнес-логики (JWT живут по реальному времени)."""

    def _freeze(moment):
        monkeypatch.setattr(timeutil, "utcnow", lambda: moment)

    return _freeze


class Account:
    def __init__(self, client, data):
        self.client = client
        self.id = data["user"]["id"]
        self.code = data["user"]["friend_code"]
        self.headers = {"Authorization": f"Bearer {data['access_token']}"}
        self.tokens = data

    def get(self, url, **kw):
        return self.client.get(url, headers=self.headers, **kw)

    def post(self, url, json=None, **kw):
        return self.client.post(url, json=json, headers=self.headers, **kw)

    def patch(self, url, json=None, **kw):
        return self.client.patch(url, json=json, headers=self.headers, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self.headers, **kw)


@pytest.fixture
def register(client):
    def _register(email, name="Аня", timezone="UTC"):
        response = client.post(
            "/auth/register",
            json={"email": email, "password": "password123", "name": name, "timezone": timezone},
        )
        assert response.status_code == 201, response.text
        return Account(client, response.json())

    return _register


@pytest.fixture
def make_friends(register):
    """Два аккаунта, уже ставшие друзьями."""

    def _make(tz_a="UTC", tz_b="UTC"):
        anna = register("anna@example.com", "Анна", tz_a)
        dima = register("dima@example.com", "Дима", tz_b)
        assert anna.post("/friends/by-code", {"code": dima.code}).status_code == 200
        assert dima.post(f"/friends/{anna.id}/accept").status_code == 200
        return anna, dima

    return _make
