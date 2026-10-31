"""Точка входа FastAPI.

Запуск для разработки:  uvicorn app.main:app --reload
Документация API:       http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.admin import setup_admin
from app.config import get_settings
from app.db import Base, SessionLocal, add_missing_columns, engine
from app.routers import articles, auth, community, friends, habits, legal, me, ratings, sos, stats
from app.scheduler import start_scheduler
from app.seed import seed_content

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("vmeste")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(engine)
        try:  # база осталась от прошлой версии: дописываем новые необязательные колонки
            for name in add_missing_columns(engine):
                log.info("В базу добавлена колонка %s", name)
        except Exception:
            log.exception("Не удалось дописать новые колонки в базу. Для PostgreSQL: alembic upgrade head")
    try:
        with SessionLocal() as db:
            seed_content(db)
    except Exception:
        log.exception(
            "Не удалось заполнить шаблоны и статьи. Если таблиц ещё нет, "
            "выполните: alembic upgrade head"
        )
    scheduler = start_scheduler() if settings.run_scheduler else None
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Вместе привычнее — API",
        version="0.1.0",
        description="Сервер социального трекера привычек (MVP).",
        lifespan=lifespan,
    )

    media = Path(settings.media_dir)
    (media / "avatars").mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media), name="media")

    for router in (auth.router, me.router, friends.router, habits.router, stats.router,
                   articles.router, sos.router, legal.router, ratings.router, community.router):
        app.include_router(router)

    @app.get("/health", tags=["service"])
    def health():
        return {"status": "ok"}

    setup_admin(app)
    return app


app = create_app()
