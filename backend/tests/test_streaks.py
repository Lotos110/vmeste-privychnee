from datetime import date, timedelta

from app.services.streaks import (
    activity_streaks,
    compute_streaks,
    current_streak,
    shared_streak,
    today_status,
)

DAILY = [0, 1, 2, 3, 4, 5, 6]
TODAY = date(2026, 10, 7)  # среда


def days_back(*offsets):
    return {TODAY - timedelta(days=n) for n in offsets}


def test_reference_current_streak_counts_from_yesterday_if_today_not_marked():
    assert current_streak(days_back(1, 2, 3), TODAY) == 3
    assert current_streak(days_back(0, 1, 2), TODAY) == 3
    assert current_streak(days_back(2, 3), TODAY) == 0  # вчера пропущено


def test_daily_streak_today_pending_does_not_break():
    start = TODAY - timedelta(days=5)
    current, best = compute_streaks(days_back(1, 2, 3, 4, 5), set(), DAILY, start, TODAY)
    assert (current, best) == (5, 5)


def test_daily_streak_today_done_extends():
    start = TODAY - timedelta(days=5)
    current, best = compute_streaks(days_back(0, 1, 2, 3, 4, 5), set(), DAILY, start, TODAY)
    assert (current, best) == (6, 6)


def test_gap_breaks_streak_and_best_is_kept():
    start = TODAY - timedelta(days=9)
    done = days_back(9, 8, 7, 6, 5, 3, 2, 1)  # пропущен день -4
    current, best = compute_streaks(done, set(), DAILY, start, TODAY)
    assert (current, best) == (3, 5)


def test_missed_today_resets_immediately():
    start = TODAY - timedelta(days=3)
    current, best = compute_streaks(days_back(1, 2, 3), {TODAY}, DAILY, start, TODAY)
    assert current == 0
    assert best == 3


def test_unscheduled_days_do_not_break_streak():
    # пн, ср, пт; сегодня среда 7 октября
    schedule = [0, 2, 4]
    start = date(2026, 9, 28)  # понедельник
    done = {date(2026, 9, 28), date(2026, 9, 30), date(2026, 10, 2), date(2026, 10, 5)}
    current, best = compute_streaks(done, set(), schedule, start, TODAY)
    assert (current, best) == (4, 4)  # среда сегодня ещё не отмечена, но серия жива


def test_missed_scheduled_day_breaks_streak():
    schedule = [0, 2, 4]
    start = date(2026, 9, 28)
    done = {date(2026, 9, 28), date(2026, 9, 30), date(2026, 10, 5)}  # пропущена пятница 2.10
    current, best = compute_streaks(done, set(), schedule, start, TODAY)
    assert (current, best) == (1, 2)


def test_start_date_is_respected():
    # привычку начали только вчера: позавчера и раньше не считаются пропусками
    current, best = compute_streaks(days_back(1), set(), DAILY, TODAY - timedelta(days=1), TODAY)
    assert (current, best) == (1, 1)


def test_shared_streak_requires_everyone():
    start = TODAY - timedelta(days=3)
    anna = days_back(3, 2, 1)
    dima = days_back(3, 1)  # пропустил день -2
    assert shared_streak([anna, dima], [set(), set()], DAILY, start, TODAY) == 1
    assert shared_streak([anna, anna], [set(), set()], DAILY, start, TODAY) == 3


def test_shared_streak_empty():
    assert shared_streak([], [], DAILY, TODAY, TODAY) == 0


def test_today_status():
    assert today_status({TODAY}, set(), DAILY, TODAY) == "done"
    assert today_status(set(), {TODAY}, DAILY, TODAY) == "missed"
    assert today_status(set(), set(), DAILY, TODAY) == "pending"
    assert today_status(set(), set(), [0], TODAY) == "off"  # среда не по расписанию


def test_activity_streaks():
    assert activity_streaks(set(), TODAY) == (0, 0)
    days = days_back(1, 2, 3, 10, 11, 12, 13, 14)
    assert activity_streaks(days, TODAY) == (3, 5)
