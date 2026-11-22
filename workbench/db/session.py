from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from workbench.runtime_paths import get_runtime_paths


def create_sqlite_engine(database_path: Optional[Path] = None) -> Engine:
    path = (database_path or get_runtime_paths().database).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


def create_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or create_sqlite_engine(), expire_on_commit=False)
