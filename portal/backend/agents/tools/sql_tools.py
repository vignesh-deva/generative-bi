"""
SQL tools — dry-run validation and query execution against PostgreSQL.

Tools:
  dry_run_explain(sql)  — EXPLAIN without executing; returns plan or error
  execute_query(sql)    — run a SELECT and return structured results
"""

from db.database import get_pool, execute_query


async def dry_run_explain(sql: str) -> dict:
    """Run EXPLAIN on a SQL query without executing it.

    Returns:
        {"success": True, "plan": "..."} on success
        {"success": False, "error": "..."} on failure
    """
    sql_stripped = sql.strip().rstrip(";").strip()
    if not sql_stripped.upper().startswith(("SELECT", "WITH")):
        return {"success": False, "error": "Only SELECT/WITH queries can be explained"}

    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(f"EXPLAIN {sql}")
                plan = "\n".join(row[0] for row in rows)
                return {"success": True, "plan": plan}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_query(sql: str) -> dict:
    """Execute a SELECT query and return structured results.

    Delegates to db.database.execute_query which enforces SELECT-only.
    Returns: {"columns": [...], "rows": [...], "row_count": int}
    Raises on non-SELECT or execution error.
    """
    return await execute_query(sql)
