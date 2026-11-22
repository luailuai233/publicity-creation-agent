from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

from sqlalchemy import text

from workbench.db.session import create_sqlite_engine


def test_sqlite_connections_enable_foreign_keys_wal_and_busy_timeout(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "runtime.db")

    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        assert connection.scalar(text("PRAGMA journal_mode")) == "wal"
        assert connection.scalar(text("PRAGMA busy_timeout")) == 5000


def test_short_write_lock_waits_instead_of_failing_immediately(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "locked.db")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE samples (value TEXT NOT NULL)"))

    def delayed_write() -> None:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO samples(value) VALUES ('second')"))

    first = engine.connect()
    first.exec_driver_sql("BEGIN IMMEDIATE")
    first.execute(text("INSERT INTO samples(value) VALUES ('first')"))
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(delayed_write)
            time.sleep(0.1)
            first.commit()
            future.result(timeout=2)
    finally:
        first.close()

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM samples")) == 2
