from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401  (регистрирует таблицы в Base.metadata)
from app.db import add_missing_columns


def test_add_missing_columns_keeps_existing_data(tmp_path):
    """База от прошлой версии (без новых колонок) получает их без потери данных."""
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE habits (id INTEGER PRIMARY KEY, creator_id INTEGER NOT NULL, "
                "title VARCHAR(80) NOT NULL)"
            )
        )
        conn.execute(text("INSERT INTO habits (creator_id, title) VALUES (1, 'Пить воду')"))

    added = add_missing_columns(engine)
    assert "habits.icon" in added and "habits.color" in added
    assert {"icon", "color"} <= {c["name"] for c in inspect(engine).get_columns("habits")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT title, icon FROM habits")).one() == ("Пить воду", None)

    assert add_missing_columns(engine) == []  # повторный запуск ничего не меняет
