import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATABASE_PATH = DATA_DIR / "app.sqlite3"


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                character_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )