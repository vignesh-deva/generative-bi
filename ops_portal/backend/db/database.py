"""
PostgreSQL connection pool for the ops backend.
Mirrors user_portal/backend/db/database.py — same pool pattern, same DB.
"""

import asyncpg

from config.settings import POSTGRES_URI

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(POSTGRES_URI, min_size=2, max_size=5)
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def execute_query(sql: str, params: list | None = None) -> dict:
    normalized = sql.strip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        raise ValueError("Only SELECT / WITH queries are allowed")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql, *(params or []))
            if rows:
                columns = list(rows[0].keys())
                return {
                    "columns": columns,
                    "rows": [list(r.values()) for r in rows],
                    "row_count": len(rows),
                }
            return {"columns": [], "rows": [], "row_count": 0}
