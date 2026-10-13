"""Планировщик напоминаний (APScheduler работает в том же процессе, что и API)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.db import SessionLocal
from app.services.reminders import run_reminders

log = logging.getLogger(__name__)


def _job() -> None:
    try:
        with SessionLocal() as db:
            run_reminders(db)
    except Exception:  # планировщик не должен падать из-за одной неудачной итерации
        log.exception("Ошибка при отправке напоминаний")


def start_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _job,
        "interval",
        minutes=settings.reminder_interval_minutes,
        id="reminders",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info("Планировщик напоминаний запущен (каждые %s мин.)", settings.reminder_interval_minutes)
    return scheduler
