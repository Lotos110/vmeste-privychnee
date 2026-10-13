from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.services.reminders import run_reminders

UTC = timezone.utc
D = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)  # понедельник


def run(now):
    with SessionLocal() as db:
        return run_reminders(db, now)


def test_reminder_is_sent_once_after_remind_time(register, freeze):
    anna = register("anna@example.com")
    freeze(D)
    habit = anna.post("/habits", {"title": "Пить воду", "remind_time": "10:00"}).json()

    assert run(D) == 0  # ещё рано
    assert run(D.replace(hour=10, minute=30)) == 1
    assert run(D.replace(hour=11)) == 0  # повторно за день не шлём

    inbox = anna.get("/nudges").json()
    assert len(inbox) == 1
    assert inbox[0]["kind"] == "reminder" and inbox[0]["sender"] is None
    assert "Пить воду" in inbox[0]["text"]

    # отметился — больше напоминаний за этот день нет
    anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
    assert run(D.replace(hour=21)) == 0


def test_streak_at_risk_warning(register, freeze):
    anna = register("anna@example.com")
    freeze(D)
    habit = anna.post("/habits", {"title": "Спорт"}).json()  # без времени напоминания
    anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
    freeze(D + timedelta(days=1))
    anna.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})

    evening = D + timedelta(days=2, hours=13)  # 21:00 третьего дня, отметки за сегодня нет
    freeze(evening)
    assert run(evening) == 1
    inbox = anna.get("/nudges").json()
    assert inbox[0]["kind"] == "risk" and "Серия 2" in inbox[0]["text"]
    assert run(evening + timedelta(minutes=15)) == 0
