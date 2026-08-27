"""
Database helper module.

Wraps raw sqlite3 access (no ORM). Foreign key enforcement is turned on
explicitly, since SQLite disables it by default.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "student_management.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Return a new SQLite connection with row access by column name
    and foreign key constraints enforced."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = None) -> None:
    """Create tables from schema.sql if they don't already exist."""
    conn = get_connection(db_path or DB_PATH)
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row is not None else None
