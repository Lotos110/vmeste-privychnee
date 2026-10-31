"""Общие мелочи для тестов рейтинга и ленты."""

from datetime import date, datetime, timezone

UTC = timezone.utc
D = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)  # среда
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]
ADULT = "1990-05-17"


def years_ago(years: int) -> str:
    today = date.today()
    return today.replace(year=today.year - years, day=min(today.day, 28)).isoformat()


def adult_public(account, join=True):
    assert account.patch("/me", {"birth_date": ADULT}).status_code == 200
    if join:
        assert account.patch("/me", {"is_public": True}).status_code == 200
