from __future__ import annotations

import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS exchange_rates (
    rate_date TEXT NOT NULL,
    usd_to_mxn REAL NOT NULL,
    usd_to_cad REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (rate_date)
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
