from datetime import timedelta

from helpers import adult_public, years_ago

from app import ratelimit
from app.db import SessionLocal
from app.models import Friendship, PartnerPost
from app.services import moderation, timeutil

POST = {"template_id": None, "topic": "Бег по утрам", "text": "Ищу напарника для пробежек по утрам", "time_pref": "morning"}


def adult(register, email, name):
    ratelimit.reset_all()  # лимит регистраций с одного адреса не нужен в тестах
    account = register(email, name)
    adult_public(account, join=False)
    return account


def make_post(account, **extra):
    response = account.post("/partner-posts", {**POST, **extra})
    assert response.status_code == 201, response.text
    return response.json()


# ---------- фильтр ----------


def test_moderation_filter():
    for text in (
        "Бегаю по утрам, нужен напарник", "Требуется поддержка, хочу бросить курить", "Читаю по 20 страниц в день",
    ):
        assert moderation.check_text(text) is None, text
    for text in (
        "пиши в телеграм", "мой номер +7 701 123 45 67", "vk.com/abc", "@ivan_ivanov", "test@mail.ru",
        "ты урод", "пиzда", "www.example.com",
    ):
        assert moderation.check_text(text), text


# ---------- доступ по возрасту ----------


def test_feed_closed_without_birth_date_and_for_under_12(register):
    anna = register("anna@example.com", "Анна")
    assert anna.get("/partner-posts").status_code == 403
    assert "дату рождения" in anna.get("/partner-posts").json()["detail"]
    assert anna.patch("/me", {"birth_date": years_ago(10)}).status_code == 200
    assert anna.get("/partner-posts").status_code == 403
    assert anna.post("/partner-posts", POST).status_code == 403
    assert anna.patch("/me", {"birth_date": years_ago(12)}).status_code == 200
    assert anna.get("/partner-posts").status_code == 200


def test_teens_and_adults_do_not_see_each_other(register):
    anna = adult(register, "anna@example.com", "Анна")
    lena = register("lena@example.com", "Лена")
    assert lena.patch("/me", {"birth_date": years_ago(15)}).status_code == 200
    post = make_post(anna)
    assert lena.get("/partner-posts").json() == []
    assert lena.post(f"/partner-posts/{post['id']}/respond", {"text": "Давайте вместе"}).status_code == 404
    dima = adult(register, "dima@example.com", "Дима")
    assert [p["id"] for p in dima.get("/partner-posts").json()] == [post["id"]]


# ---------- объявления ----------


def test_create_and_list_posts_with_filters(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    templates = anna.get("/templates").json()
    sport = templates[4]
    p1 = make_post(anna, template_id=sport["id"], topic=None, time_pref="evening")
    assert p1["topic"] == sport["title"] and p1["author"]["name"] == "Анна"
    p2 = make_post(anna, time_pref="any")

    feed = dima.get("/partner-posts").json()
    assert [p["id"] for p in feed] == [p2["id"], p1["id"]]  # новые сверху
    assert anna.get("/partner-posts").json() == []  # своих в ленте нет
    assert [p["id"] for p in dima.get(f"/partner-posts?template_id={sport['id']}").json()] == [p1["id"]]
    assert {p["id"] for p in dima.get("/partner-posts?time_pref=morning").json()} == {p2["id"]}  # «любое» подходит всем
    assert {p["id"] for p in dima.get("/partner-posts?time_pref=evening").json()} == {p1["id"], p2["id"]}


def test_post_validation_and_limits(register):
    anna = adult(register, "anna@example.com", "Анна")
    assert anna.post("/partner-posts", {**POST, "text": "коротко"}).status_code == 422
    assert anna.post("/partner-posts", {**POST, "topic": None}).status_code == 422  # нет ни шаблона, ни темы
    bad = anna.post("/partner-posts", {**POST, "text": "Пишите мне в телеграм, ищу напарника"})
    assert bad.status_code == 422 and "контакты" in bad.json()["detail"]
    assert anna.post("/partner-posts", {**POST, "topic": "звоните +7 701 123 45 67"}).status_code == 422
    for _ in range(3):
        make_post(anna)
    full = anna.post("/partner-posts", POST)
    assert full.status_code == 409


def test_close_post_and_expiry(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    first, second = make_post(anna), make_post(anna)
    assert anna.delete(f"/partner-posts/{first['id']}").status_code == 204
    assert dima.delete(f"/partner-posts/{second['id']}").status_code == 404  # чужое закрыть нельзя
    assert [p["id"] for p in dima.get("/partner-posts").json()] == [second["id"]]

    with SessionLocal() as db:  # объявление старше 30 дней пропадает из ленты
        db.get(PartnerPost, second["id"]).expires_at = timeutil.utcnow() - timedelta(minutes=1)
        db.commit()
    assert dima.get("/partner-posts").json() == []
    mine = anna.get("/partner-posts/mine").json()
    assert [(p["id"], p["expired"]) for p in mine] == [(second["id"], True)]


# ---------- отклики ----------


def test_response_accept_makes_friends_and_notifies(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    post = make_post(anna)
    url = f"/partner-posts/{post['id']}"

    assert anna.post(f"{url}/respond", {"text": "Давайте"}).status_code == 400  # на своё нельзя
    assert dima.post(f"{url}/respond", {"text": "мой ник @dima_run"}).status_code == 422
    assert dima.post(f"{url}/respond", {"text": "Давайте бегать вместе!"}).status_code == 201
    assert dima.post(f"{url}/respond", {"text": "Ещё раз"}).status_code == 409
    assert dima.get("/partner-posts").json()[0]["responded"] is True

    nudges = anna.get("/nudges").json()
    assert nudges[0]["kind"] == "response" and nudges[0]["habit_id"] is None
    assert nudges[0]["sender"]["name"] == "Дима" and "Давайте бегать" in nudges[0]["text"]

    mine = anna.get("/partner-posts/mine").json()
    response = mine[0]["responses"][0]
    assert response["status"] == "pending" and response["person"]["name"] == "Дима"

    assert dima.post(f"{url}/responses/{response['id']}/accept").status_code == 404  # принимает только автор
    accepted = anna.post(f"{url}/responses/{response['id']}/accept")
    assert accepted.status_code == 200 and accepted.json()["name"] == "Дима"
    assert [f["name"] for f in anna.get("/friends").json()["friends"]] == ["Дима"]
    assert [f["name"] for f in dima.get("/friends").json()["friends"]] == ["Анна"]
    back = dima.get("/nudges").json()[0]
    assert back["kind"] == "accepted" and back["habit_id"] is None and "друзья" in back["text"]
    assert anna.post(f"{url}/responses/{response['id']}/accept").status_code == 404  # повторно нельзя
    assert anna.get("/partner-posts/mine").json()[0]["responses"][0]["status"] == "accepted"
    anna.post("/nudges/read")


def test_decline_is_silent(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    post = make_post(anna)
    dima.post(f"/partner-posts/{post['id']}/respond", {"text": "Давайте вместе"})
    response = anna.get("/partner-posts/mine").json()[0]["responses"][0]
    assert anna.post(f"/partner-posts/{post['id']}/responses/{response['id']}/decline").status_code == 204
    assert dima.get("/nudges").json() == []
    with SessionLocal() as db:
        assert db.query(Friendship).count() == 0


def test_response_daily_limit(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    ids = []
    for index in range(11):
        author = adult(register, f"a{index}@example.com", f"Автор{index}")
        ids.append(make_post(author)["id"])
    for post_id in ids[:10]:
        assert dima.post(f"/partner-posts/{post_id}/respond", {"text": "Давайте вместе"}).status_code == 201
    assert dima.post(f"/partner-posts/{ids[10]}/respond", {"text": "Давайте вместе"}).status_code == 429
    assert anna.get("/partner-posts").status_code == 200


# ---------- жалобы и блокировки ----------


def test_three_reports_hide_post(register):
    anna = adult(register, "anna@example.com", "Анна")
    post = make_post(anna)
    reporters = [adult(register, f"r{i}@example.com", f"Р{i}") for i in range(3)]
    url = f"/partner-posts/{post['id']}/report"
    assert anna.post(url, {"reason": "spam"}).status_code == 400
    for index, reporter in enumerate(reporters):
        assert reporter.post(url, {"reason": "rude"}).status_code == 204
        assert reporter.post(url, {"reason": "rude"}).status_code in (204, 404)  # повтор безвреден
        visible = reporters[-1].get("/partner-posts").json()
        assert bool(visible) == (index < 2), index
    assert anna.get("/partner-posts/mine").json()[0]["status"] == "hidden"


def test_report_response_hides_it_from_author(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    post = make_post(anna)
    dima.post(f"/partner-posts/{post['id']}/respond", {"text": "Давайте вместе"})
    response = anna.get("/partner-posts/mine").json()[0]["responses"][0]
    assert dima.post(f"/partner-responses/{response['id']}/report", {"reason": "rude"}).status_code == 404
    assert anna.post(f"/partner-responses/{response['id']}/report", {"reason": "rude"}).status_code == 204
    assert anna.get("/partner-posts/mine").json()[0]["responses"] == []


def test_block_hides_both_ways_and_removes_friendship(register):
    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    assert anna.post("/friends/by-code", {"code": dima.code}).status_code == 200
    assert dima.post(f"/friends/{anna.id}/accept").status_code == 200
    a_post, d_post = make_post(anna), make_post(dima)

    assert anna.post(f"/users/{anna.id}/block").status_code == 400
    assert anna.post(f"/users/{dima.id}/block").status_code == 204
    assert anna.get("/partner-posts").json() == [] and dima.get("/partner-posts").json() == []
    assert dima.post(f"/partner-posts/{a_post['id']}/respond", {"text": "Давайте вместе"}).status_code == 404
    assert anna.post(f"/partner-posts/{d_post['id']}/respond", {"text": "Давайте вместе"}).status_code == 404
    assert anna.get("/friends").json()["friends"] == []
    assert [p["name"] for p in anna.get("/blocks").json()["blocked"]] == ["Дима"]

    assert anna.delete(f"/users/{dima.id}/block").status_code == 204
    assert anna.get("/blocks").json()["blocked"] == []
    assert len(anna.get("/partner-posts").json()) == 1


def test_banned_author_disappears_from_feed(register):
    from app.models import User

    anna = adult(register, "anna@example.com", "Анна")
    dima = adult(register, "dima@example.com", "Дима")
    make_post(anna)
    with SessionLocal() as db:
        db.get(User, anna.id).is_banned = True
        db.commit()
    assert dima.get("/partner-posts").json() == []
