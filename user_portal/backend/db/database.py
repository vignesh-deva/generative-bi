"""
PostgreSQL connection management for Generative BI Agent.

Uses asyncpg for async access. Two usage patterns:
- get_pool()          shared connection pool (created once at startup)
- execute_query()     read-only query execution for the SQL Agent
"""

import re
from typing import Any

import asyncpg
import pgvector.asyncpg

from config.settings import POSTGRES_URI

# Strip leading SQL comments (-- line, /* block */) and whitespace before the
# SELECT/WITH prefix check. Defense-in-depth — the read-only transaction is the
# real safety net.
_SQL_COMMENT_STRIP_RE = re.compile(
    r"^\s*(?:--[^\n]*\n|/\*.*?\*/|\s+)+",
    re.DOTALL,
)

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register pgvector codec so embeddings can be passed as Python lists."""
    await pgvector.asyncpg.register_vector(conn)


async def get_pool() -> asyncpg.Pool:
    """Get or create the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            POSTGRES_URI, min_size=2, max_size=10, init=_init_connection
        )
    return _pool


async def close_pool():
    """Close the connection pool. Call on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def execute_query(sql: str, params: list | None = None) -> dict[str, Any]:
    """Execute a SELECT query and return results as a structured dict.

    Returns:
        {
            "columns": ["col1", "col2", ...],
            "rows":    [[val, val, ...], ...],
            "row_count": int,
        }

    Raises:
        ValueError  if the statement is not a SELECT (basic guard).
    """
    # Application-level guard: fast-fail on obviously non-SELECT statements.
    # The real safety net is the read-only transaction below — PostgreSQL will
    # reject any DML/DDL even if this check is somehow bypassed.
    stripped = _SQL_COMMENT_STRIP_RE.sub("", sql).lstrip("(").upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        raise ValueError("Only SELECT / WITH queries are allowed via execute_query().")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql, *(params or []))
            columns = [key for key in rows[0].keys()] if rows else []

    return {
        "columns": columns,
        "rows": [list(row.values()) for row in rows],
        "row_count": len(rows),
    }
