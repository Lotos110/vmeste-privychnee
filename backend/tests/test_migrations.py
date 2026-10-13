from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db import Base

BACKEND = Path(__file__).resolve().parent.parent


def test_migration_matches_models(tmp_path):
    """alembic upgrade head создаёт те же таблицы и колонки, что описаны в моделях."""
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")
    inspector = inspect(create_engine(url))
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert tables == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        assert {c["name"] for c in inspector.get_columns(name)} == {c.name for c in table.columns}, name

    command.downgrade(cfg, "base")
    assert set(inspect(create_engine(url)).get_table_names()) == {"alembic_version"}
