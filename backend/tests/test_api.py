from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image

from app.db import SessionLocal
from app.models import User

UTC = timezone.utc
D = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)  # среда
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


def new_habit(account, **extra):
    payload = {"title": "Пить воду", "goal": "2 л в день", "schedule": ALL_DAYS}
    payload.update(extra)
    response = account.post("/habits", payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- авторизация ----------


def test_register_login_refresh_logout(client):
    body = {"email": "Anna@Example.com", "password": "password123", "name": "Анна"}
    registered = client.post("/auth/register", json=body)
    assert registered.status_code == 201
    data = registered.json()
    assert data["user"]["email"] == "anna@example.com"
    assert len(data["user"]["friend_code"]) == 8

    assert client.post("/auth/register", json={**body, "email": "anna@example.com"}).status_code == 409
    assert client.post("/auth/register", json={**body, "email": "b@example.com", "password": "short"}).status_code == 422

    bad = client.post("/auth/login", json={"email": "anna@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    ok = client.post("/auth/login", json={"email": "anna@example.com", "password": "password123"})
    assert ok.status_code == 200

    refreshed = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert refreshed.status_code == 200
    # access-токен не годится вместо refresh-токена
    assert client.post("/auth/refresh", json={"refresh_token": data["access_token"]}).status_code == 401

    headers = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get("/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401  # токены отозваны
    assert client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]}).status_code == 401


def test_requires_auth(client):
    assert client.get("/me").status_code == 401
    assert client.get("/habits").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_banned_user_is_rejected(register):
    anna = register("anna@example.com")
    with SessionLocal() as db:
        db.query(User).update({"is_banned": True})
        db.commit()
    assert anna.get("/me").status_code == 403


# ---------- профиль ----------


def test_profile_update_and_avatar(register, client):
    anna = register("anna@example.com", "Анна")
    updated = anna.patch(
        "/me",
        {"name": "Анна", "last_name": "Смирнова", "bio": "Маленькие шаги", "gender": "female",
         "birth_date": "2000-05-12", "timezone": "Asia/Barnaul"},
    )
    assert updated.status_code == 200
    me = updated.json()
    assert me["last_name"] == "Смирнова" and me["timezone"] == "Asia/Barnaul"

    assert anna.patch("/me", {"timezone": "Mars/Base"}).status_code == 422
    assert anna.patch("/me", {"name": "   "}).status_code == 422

    buffer = BytesIO()
    Image.new("RGB", (900, 600), "red").save(buffer, "PNG")
    uploaded = client.post(
        "/me/avatar", files={"file": ("a.png", buffer.getvalue(), "image/png")}, headers=anna.headers
    )
    assert uploaded.status_code == 200, uploaded.text
    url = uploaded.json()["avatar_url"]
    assert url.startswith("/media/avatars/")
    picture = client.get(url)
    assert picture.status_code == 200
    assert Image.open(BytesIO(picture.content)).size == (512, 512)

    fake = client.post(
        "/me/avatar", files={"file": ("a.png", b"not an image", "image/png")}, headers=anna.headers
    )
    assert fake.status_code == 400


# ---------- друзья ----------


def test_friends_by_code_flow(register):
    anna = register("anna@example.com", "Анна")
    dima = register("dima@example.com", "Дима")

    assert anna.post("/friends/by-code", {"code": anna.code}).status_code == 400
    assert anna.post("/friends/by-code", {"code": "ZZZZZZZZ"}).status_code == 404

    spaced = dima.code[:4].lower() + "-" + dima.code[4:].lower()  # код терпим к регистру и дефису
    sent = anna.post("/friends/by-code", {"code": spaced})
    assert sent.status_code == 200 and sent.json()["status"] == "pending"

    assert [p["name"] for p in dima.get("/friends").json()["incoming"]] == ["Анна"]
    assert [p["name"] for p in anna.get("/friends").json()["outgoing"]] == ["Дима"]

    assert dima.post(f"/friends/{anna.id}/accept").json()["status"] == "accepted"
    friends = anna.get("/friends").json()["friends"]
    assert [p["name"] for p in friends] == ["Дима"]
    assert set(friends[0]) == {"id", "name", "avatar_url"}  # email и дата рождения не видны

    assert anna.get("/me").json()["friends_count"] == 1
    assert anna.delete(f"/friends/{dima.id}").status_code == 204
    assert dima.get("/friends").json()["friends"] == []


def test_mutual_requests_become_friends(register):
    anna = register("anna@example.com")
    dima = register("dima@example.com")
    anna.post("/friends/by-code", {"code": dima.code})
    assert dima.post("/friends/by-code", {"code": anna.code}).json()["status"] == "accepted"


def test_friend_code_lookup_is_rate_limited(register):
    anna = register("anna@example.com")
    for _ in range(20):
        assert anna.post("/friends/by-code", {"code": "AAAAAAAA"}).status_code == 404
    assert anna.post("/friends/by-code", {"code": "AAAAAAAA"}).status_code == 429


# ---------- шаблоны и привычки ----------


def test_templates(client):
    templates = client.get("/templates").json()
    assert len(templates) == 9
    assert templates[0]["title"] == "Сон"


def test_habit_streak_grows_and_resets(register, freeze):
    anna = register("anna@example.com")
    freeze(D)
    habit = new_habit(anna, remind_time="10:00")
    assert habit["today_status"] == "pending" and habit["current_streak"] == 0
    assert habit["my_status"] == "active" and habit["shared_streak"] is None

    for offset in range(3):
        freeze(D + timedelta(days=offset))
        marked = anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
        assert marked.status_code == 200, marked.text
        assert marked.json()["current_streak"] == offset + 1
        assert marked.json()["today_status"] == "done"

    freeze(D + timedelta(days=3))  # день не отмечен, но он ещё не закончился
    assert anna.get("/habits").json()[0]["current_streak"] == 3
    freeze(D + timedelta(days=4))  # вчерашний день пропущен
    habit_now = anna.get("/habits").json()[0]
    assert habit_now["current_streak"] == 0 and habit_now["best_streak"] == 3


def test_habit_week_days_for_home_card(register, freeze):
    anna = register("anna@example.com")
    freeze(D)  # среда; привычка по будням, создана сегодня
    habit = new_habit(anna, schedule=[0, 1, 2, 3, 4])
    url = f"/habits/{habit['id']}/check-ins"
    assert anna.post(url, {"status": "done"}).status_code == 200
    freeze(D + timedelta(days=2))  # пятница: срыв, четверг остался без отметки
    assert anna.post(url, {"status": "missed"}).status_code == 200
    freeze(D + timedelta(days=3))  # суббота: не по расписанию

    days = anna.get("/habits").json()[0]["week_days"]
    assert [d["date"] for d in days] == [f"2026-10-{n:02d}" for n in range(4, 11)]
    assert [d["weekday"] for d in days] == [6, 0, 1, 2, 3, 4, 5]
    # до создания привычки и в нерабочие дни — off; среда выполнена, четверг пропущен без отметки, пятница — срыв
    assert [d["status"] for d in days] == ["off", "off", "off", "done", "none", "missed", "off"]


def test_check_in_validation_undo_and_miss_reason(register, freeze):
    anna = register("anna@example.com")
    freeze(D)
    habit = new_habit(anna)
    url = f"/habits/{habit['id']}/check-ins"

    assert anna.post(url, {"status": "done", "local_date": "2026-10-08"}).status_code == 400  # будущее
    assert anna.post(url, {"status": "done", "local_date": "2026-10-06"}).status_code == 400  # до старта

    missed = anna.post(url, {"status": "missed", "miss_reason": "Не было времени"})
    assert missed.status_code == 200
    assert missed.json()["today_status"] == "missed" and missed.json()["current_streak"] == 0

    again = anna.post(url, {"status": "done"})  # передумал: отметка заменяется, а не дублируется
    assert again.json()["today_status"] == "done" and again.json()["current_streak"] == 1

    undone = anna.delete(f"{url}/2026-10-07")
    assert undone.status_code == 200 and undone.json()["today_status"] == "pending"


def test_calendar_uses_local_day_of_user(register, freeze):
    anna = register("anna@example.com", timezone="Asia/Barnaul")  # UTC+7
    freeze(datetime(2026, 10, 10, 20, 0, tzinfo=UTC))  # в Барнауле уже 11 октября, 03:00
    habit = new_habit(anna)
    assert anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"}).status_code == 200

    calendar = anna.get(f"/habits/{habit['id']}/calendar", params={"month": "2026-10"}).json()
    by_day = {d["date"]: d["status"] for d in calendar["days"]}
    assert len(calendar["days"]) == 31
    assert by_day["2026-10-11"] == "done" and by_day["2026-10-10"] == "none"
    assert anna.get(f"/habits/{habit['id']}/calendar", params={"month": "2026-13"}).status_code == 422


def test_habit_update_and_validation(register):
    anna = register("anna@example.com")
    assert anna.post("/habits", {"title": "Х", "schedule": []}).status_code == 422
    assert anna.post("/habits", {"title": "Х", "schedule": [7]}).status_code == 422
    assert anna.post("/habits", {"title": "Х", "remind_time": "25:00"}).status_code == 422
    habit = new_habit(anna)
    patched = anna.patch(f"/habits/{habit['id']}", {"title": "Пить воду 💧", "schedule": [4, 2, 2]})
    assert patched.status_code == 200
    assert patched.json()["schedule"] == [2, 4] and patched.json()["title"] == "Пить воду 💧"


# ---------- совместный режим и права доступа ----------


def test_shared_habit_flow(make_friends, register, freeze):
    freeze(D)
    anna, dima = make_friends()
    stranger = register("stranger@example.com", "Чужой")

    assert anna.post("/habits", {"title": "Х", "invite_friend_ids": [stranger.id]}).status_code == 400

    habit = new_habit(anna, invite_friend_ids=[dima.id])
    statuses = {m["name"]: m["status"] for m in habit["members"]}
    assert statuses == {"Анна": "active", "Дима": "invited"}

    invites = dima.get("/invites").json()
    assert [h["id"] for h in invites] == [habit["id"]] and dima.get("/habits").json() == []
    assert dima.post(f"/habits/{habit['id']}/accept").json()["my_status"] == "active"

    assert anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"}).status_code == 200
    seen_by_dima = dima.get(f"/habits/{habit['id']}").json()
    anna_member = next(m for m in seen_by_dima["members"] if m["name"] == "Анна")
    assert anna_member["today_status"] == "done"  # напарники видят отметки друг друга
    assert seen_by_dima["shared_streak"] == 0

    both = dima.post(f"/habits/{habit['id']}/check-ins", {"status": "done"}).json()
    assert both["shared_streak"] == 1 and both["current_streak"] == 1

    nudge = dima.post(f"/habits/{habit['id']}/nudges", {"to_user_id": anna.id, "text": "Не прерывай серию"})
    assert nudge.status_code == 201
    inbox = anna.get("/nudges").json()
    assert inbox[0]["text"] == "Не прерывай серию" and inbox[0]["sender"]["name"] == "Дима"
    assert anna.post("/nudges/read").status_code == 204
    assert all(n["read"] for n in anna.get("/nudges").json())
    assert dima.post(f"/habits/{habit['id']}/nudges", {"to_user_id": dima.id, "text": "Себе"}).status_code == 400

    # чужой человек не видит и не меняет привычку
    for response in (
        stranger.get(f"/habits/{habit['id']}"),
        stranger.post(f"/habits/{habit['id']}/check-ins", {"status": "done"}),
        stranger.post(f"/habits/{habit['id']}/nudges", {"to_user_id": anna.id, "text": "Привет"}),
        stranger.post(f"/habits/{habit['id']}/invite", {"friend_id": dima.id}),
        stranger.patch(f"/habits/{habit['id']}", {"title": "Взлом"}),
        stranger.get(f"/habits/{habit['id']}/calendar"),
    ):
        assert response.status_code == 404
    assert stranger.get("/habits").json() == []


def test_invite_existing_habit_and_decline(make_friends):
    anna, dima = make_friends()
    habit = new_habit(anna)
    url = f"/habits/{habit['id']}/invite"
    assert anna.post(url, {"friend_id": dima.id}).status_code == 200
    assert anna.post(url, {"friend_id": dima.id}).status_code == 409  # уже приглашён
    assert dima.post(f"/habits/{habit['id']}/decline").status_code == 204
    assert dima.get("/invites").json() == []
    assert anna.post(url, {"friend_id": dima.id}).status_code == 200  # можно позвать снова


def test_leaving_habit(make_friends):
    anna, dima = make_friends()
    habit = new_habit(anna, invite_friend_ids=[dima.id])
    dima.post(f"/habits/{habit['id']}/accept")

    assert dima.delete(f"/habits/{habit['id']}/membership").status_code == 204
    assert dima.get(f"/habits/{habit['id']}").status_code == 404
    assert anna.get(f"/habits/{habit['id']}").status_code == 200  # у Анны привычка осталась

    assert anna.delete(f"/habits/{habit['id']}/membership").status_code == 204
    assert anna.get(f"/habits/{habit['id']}").status_code == 404
    assert anna.get("/habits").json() == []


# ---------- статистика, статьи, SOS ----------


def test_stats(register, freeze):
    anna = register("anna@example.com")
    freeze(D)
    habit = new_habit(anna)
    anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})

    week = anna.get("/stats", params={"period": "week"}).json()
    assert len(week["points"]) == 7
    today_point = week["points"][2]  # среда
    assert today_point["done"] == 1 and today_point["planned"] == 1 and today_point["percent"] == 100
    assert week["points"][6]["percent"] is None  # воскресенье ещё не наступило
    assert week["current_streak"] == 1 and week["total_done"] == 1 and week["completion_percent"] == 100

    assert len(anna.get("/stats", params={"period": "month"}).json()["points"]) == 30
    assert len(anna.get("/stats", params={"period": "all"}).json()["points"]) == 1
    assert anna.get("/stats", params={"period": "year"}).status_code == 422
    assert anna.get("/me").json()["streak"] == 1


def test_articles(client):
    articles = client.get("/articles").json()
    assert len(articles) >= 6
    assert all(a["reading_minutes"] >= 1 for a in articles)
    assert {a["category"] for a in client.get("/articles", params={"category": "sleep"}).json()} == {"sleep"}

    sleep = next(a for a in articles if a["category"] == "sleep")
    full = client.get(f"/articles/{sleep['id']}").json()
    assert full["body_md"] and full["template"]["title"] == "Сон"  # для кнопки «Начать формирование»
    assert client.get("/articles/99999").status_code == 404


def test_sos_bot(register, client):
    anna = register("anna@example.com")
    assert client.get("/sos/start").status_code == 401
    start = anna.get("/sos/start").json()
    assert start["scene"]["id"] == "start" and start["disclaimer"]

    relapse = anna.post("/sos/next", {"scene_id": "start", "button_id": "relapse"}).json()
    assert relapse["scene"]["id"] == "relapse"
    assert anna.post("/sos/next", {"scene_id": "plan5", "button_id": "habit"}).status_code == 400  # action
    assert anna.post("/sos/next", {"scene_id": "nope", "button_id": "x"}).status_code == 404


def test_service_pages(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/legal/terms").status_code == 200
    assert client.get("/docs").status_code == 200
