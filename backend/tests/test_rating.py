from datetime import timedelta

from helpers import ALL_DAYS, D, adult_public, years_ago


def habit(account, freeze, template_id=None, title="Пить воду"):
    """Привычка создаётся «10 дней назад»: отметки задним числом нельзя ставить раньше её начала."""
    freeze(D - timedelta(days=10))
    try:
        return _create(account, template_id, title)
    finally:
        freeze(D)


def _create(account, template_id, title):
    response = account.post("/habits", {"title": title, "schedule": ALL_DAYS, "template_id": template_id})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def check(account, habit_id, days_ago=0):
    day = (D - timedelta(days=days_ago)).date().isoformat()
    response = account.post(f"/habits/{habit_id}/check-ins", {"status": "done", "local_date": day})
    assert response.status_code == 200, response.text


def test_friends_rating_streak_and_week(make_friends, freeze):
    freeze(D)
    anna, dima = make_friends()
    h = habit(anna, freeze)
    check(anna, h)
    check(anna, h, 1)  # вчера, отмечено сегодня: засчитывается
    g = habit(dima, freeze, title="Чтение")
    check(dima, g)

    streak = anna.get("/ratings?metric=streak&scope=friends").json()
    assert [(r["person"]["name"], r["rank"], r["value"]) for r in streak["items"]] == [("Анна", 1, 2), ("Дима", 2, 1)]
    assert streak["me"] == {"rank": 1, "value": 2, "joined": True}
    assert streak["items"][0]["is_me"] is True

    week = dima.get("/ratings?metric=week&scope=friends").json()
    assert [(r["person"]["name"], r["value"]) for r in week["items"]] == [("Анна", 2), ("Дима", 1)]
    assert week["me"]["rank"] == 2


def test_ties_share_place_and_zero_friend_is_listed(make_friends, freeze):
    freeze(D)
    anna, dima = make_friends()
    check(anna, habit(anna, freeze))
    data = anna.get("/ratings?metric=streak&scope=friends").json()
    assert [(r["rank"], r["value"]) for r in data["items"]] == [(1, 1), (2, 0)]
    check(dima, habit(dima, freeze, title="Чтение"))
    data = anna.get("/ratings?metric=streak&scope=friends").json()
    assert [r["rank"] for r in data["items"]] == [1, 1]  # поровну: оба на первом месте


def test_old_backdated_check_ins_do_not_count(register, freeze):
    freeze(D)
    anna = register("anna@example.com", "Анна")
    h = habit(anna, freeze)
    check(anna, h, 3)  # поставлено сегодня за позавчера: больше суток разницы, в рейтинг не идёт
    check(anna, h, 0)
    week = anna.get("/ratings?metric=week&scope=friends").json()
    assert week["me"]["value"] == 1
    assert anna.get("/ratings?metric=streak&scope=friends").json()["me"]["value"] == 1


def test_global_rating_requires_birth_date_and_opt_in(register, freeze):
    freeze(D)
    anna = register("anna@example.com", "Анна")
    assert anna.get("/me").json()["community"] == "need_birth_date"
    assert anna.get("/ratings?scope=global").status_code == 403
    assert anna.patch("/me", {"is_public": True}).status_code == 422  # без даты рождения нельзя

    adult_public(anna, join=False)
    assert anna.get("/me").json()["community"] == "ok"
    check(anna, habit(anna, freeze))
    data = anna.get("/ratings?scope=global").json()
    assert data["items"] == [] and data["me"] == {"rank": None, "value": 1, "joined": False}

    assert anna.patch("/me", {"is_public": True}).status_code == 200
    assert anna.get("/me").json()["is_public"] is True
    data = anna.get("/ratings?scope=global").json()  # включение сбрасывает кэш
    assert data["items"][0]["is_me"] is True and data["me"]["rank"] == 1


def test_global_rating_separates_age_groups_and_skips_private(register, freeze):
    freeze(D)
    anna = register("anna@example.com", "Анна")
    dima = register("dima@example.com", "Дима")
    lena = register("lena@example.com", "Лена")  # подросток
    tihon = register("tihon@example.com", "Тихон")  # не участвует
    kid = register("kid@example.com", "Малыш")
    adult_public(anna)
    adult_public(dima)
    adult_public(tihon, join=False)
    assert lena.patch("/me", {"birth_date": years_ago(15), "is_public": True}).status_code == 200
    assert kid.patch("/me", {"birth_date": years_ago(9)}).status_code == 200
    for person in (anna, dima, lena, tihon):
        check(person, habit(person, freeze))
    check(dima, habit(dima, freeze, title="Чтение"))

    data = anna.get("/ratings?metric=week&scope=global").json()
    assert [r["person"]["name"] for r in data["items"]] == ["Дима", "Анна"]  # подростка и скрытого нет
    assert data["total"] == 2

    teen = lena.get("/ratings?metric=week&scope=global").json()
    assert [r["person"]["name"] for r in teen["items"]] == ["Лена"]

    assert kid.get("/me").json()["community"] == "too_young"
    assert kid.get("/ratings?scope=global").status_code == 403
    assert kid.patch("/me", {"is_public": True}).status_code == 422
    assert kid.get("/ratings?scope=friends").status_code == 200  # друзья доступны всем


def test_rating_by_habit_template(register, freeze):
    freeze(D)
    anna = register("anna@example.com", "Анна")
    dima = register("dima@example.com", "Дима")
    adult_public(anna)
    adult_public(dima)
    templates = anna.get("/templates").json()
    water, sport = templates[3]["id"], templates[4]["id"]
    check(anna, habit(anna, freeze, water))
    check(dima, habit(dima, freeze, sport, title="Спорт"))

    data = anna.get(f"/ratings?metric=week&scope=habit&template_id={water}").json()
    assert [r["person"]["name"] for r in data["items"]] == ["Анна"]
    assert data["template_id"] == water
    assert anna.get("/ratings?scope=habit").status_code == 422
    assert anna.get("/ratings?scope=habit&template_id=9999").status_code == 404
