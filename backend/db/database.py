"""
Database connection management for Generative BI Agent.

Two connection modes:
- get_connection()          read-write, for chat/session persistence
- get_readonly_connection() read-only,  for SQL Agent query execution

Both are context managers that configure pragmas and close cleanly.
"""

import sqlite3
import pathlib
from contextlib import contextmanager
from typing import Any

DB_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "genbi.db"


def _configure(conn: sqlite3.Connection, readonly: bool = False) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not readonly:
        conn.execute("PRAGMA journal_mode = WAL")  # concurrent readers + one writer


@contextmanager
def get_connection():
    """Read-write connection — use for chat session and message persistence."""
    conn = sqlite3.connect(DB_PATH)
    try:
        _configure(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_readonly_connection():
    """Read-only connection — use for SQL Agent query execution.

    Opens the DB in immutable URI mode so SQLite rejects any writes at the
    driver level, protecting the data from accidental mutations by LLM-generated SQL.
    """
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        _configure(conn, readonly=True)
        yield conn
    finally:
        conn.close()


def execute_query(sql: str, params: tuple = ()) -> dict[str, Any]:
    """Execute a SELECT query and return results as a structured dict.

    Returns:
        {
            "columns": ["col1", "col2", ...],
            "rows":    [[val, val, ...], ...],
            "row_count": int,
        }

    Raises:
        ValueError  if the statement is not a SELECT (basic guard).
        sqlite3.Error on DB errors.
    """
    stripped = sql.strip().lstrip("(").upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        raise ValueError("Only SELECT / WITH queries are allowed via execute_query().")

    with get_readonly_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
    }
