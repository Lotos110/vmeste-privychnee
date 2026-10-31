"""Подключение к базе данных (синхронный SQLAlchemy 2.0)."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine() -> Engine:
    settings = get_settings()
    url = settings.sqlalchemy_url
    if settings.is_sqlite:
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # база в памяти (тесты): одно соединение на всех
            kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _record):  # включаем внешние ключи в SQLite
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


def add_missing_columns(bind: Engine) -> list[str]:
    """Для базы, созданной через create_all (быстрый старт на SQLite): добавляет в уже существующие
    таблицы новые колонки, которых там ещё нет, и возвращает их имена («таблица.колонка»).
    Подходят необязательные колонки и обязательные с простым server_default (например, false).

    create_all не меняет готовые таблицы, поэтому без этого после обновления кода сервер упал бы на
    базе с данными. Обязательные колонки и сложные правки схемы так не делаются: для них есть Alembic.
    """
    inspector = inspect(bind)
    quote = bind.dialect.identifier_preparer.quote
    added: list[str] = []
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing or column.primary_key:
                    continue
                kind = column.type.compile(dialect=bind.dialect)
                extra = ""
                if not column.nullable:
                    default = getattr(column.server_default, "arg", None)
                    if default is None:
                        continue  # обязательная колонка без значения по умолчанию: только через Alembic
                    if not isinstance(default, str):
                        default = str(default.compile(dialect=bind.dialect))
                    extra = f" NOT NULL DEFAULT {default if default.isidentifier() or default.isdigit() else repr(default)}"
                conn.execute(
                    text(f"ALTER TABLE {quote(table.name)} ADD COLUMN {quote(column.name)} {kind}{extra}")
                )
                added.append(f"{table.name}.{column.name}")
    return added


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
