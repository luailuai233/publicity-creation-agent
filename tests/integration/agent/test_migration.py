from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_blank_database_upgrades_to_agent_runtime_head(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "migration.db"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(f"sqlite:///{database}"))
    assert {"goal", "decisions", "revision"} <= {column["name"] for column in inspector.get_columns("projects")}
    assert {"agent_runs", "agent_steps", "agent_messages"} <= set(inspector.get_table_names())
