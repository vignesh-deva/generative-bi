"""
Schema tools — introspect PostgreSQL metadata for schema linking and correction.

Tools:
  pull_schema(tables)  — DDL + FK info for specified tables only
  value_samples(table, column, limit)  — sample distinct values from a column
  list_tables()  — list all user tables in the public schema
"""

from db.database import execute_query


async def list_tables() -> list[str]:
    """Return all user table names in the public schema."""
    result = await execute_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
        "AND table_name != 'fewshot_examples' "
        "ORDER BY table_name"
    )
    return [row[0] for row in result["rows"]]


async def pull_schema(tables: list[str]) -> str:
    """Return formatted DDL for the given tables: columns, types, PKs, FKs."""
    if not tables:
        return ""

    placeholders = ", ".join(f"${i+1}" for i in range(len(tables)))

    col_query = f"""
    SELECT
        t.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable,
        CASE WHEN pk.column_name IS NOT NULL THEN 'PK' ELSE '' END AS is_pk
    FROM information_schema.tables t
    JOIN information_schema.columns c
        ON c.table_schema = t.table_schema AND c.table_name = t.table_name
    LEFT JOIN (
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_schema = 'public'
    ) pk ON pk.table_name = t.table_name AND pk.column_name = c.column_name
    WHERE t.table_schema = 'public'
        AND t.table_name IN ({placeholders})
    ORDER BY t.table_name, c.ordinal_position
    """
    col_result = await execute_query(col_query, tables)

    fk_query = f"""
    SELECT
        tc.table_name AS from_table,
        kcu.column_name AS from_column,
        ccu.table_name AS to_table,
        ccu.column_name AS to_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND (tc.table_name IN ({placeholders}) OR ccu.table_name IN ({placeholders}))
    """
    fk_params = tables + tables
    fk_placeholders_query = fk_query
    # Rebuild with correct placeholder indices
    offset = len(tables)
    fk_placeholders_query = f"""
    SELECT
        tc.table_name AS from_table,
        kcu.column_name AS from_column,
        ccu.table_name AS to_table,
        ccu.column_name AS to_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND (tc.table_name IN ({placeholders})
             OR ccu.table_name IN ({", ".join(f"${i+1+offset}" for i in range(len(tables)))}))
    """
    fk_result = await execute_query(fk_placeholders_query, fk_params)

    # Format columns
    table_cols: dict[str, list[str]] = {}
    for row in col_result["rows"]:
        table, col, dtype, nullable, pk = row
        marker = " [PK]" if pk else ""
        null_marker = "" if nullable == "YES" else " NOT NULL"
        table_cols.setdefault(table, []).append(f"  {col} {dtype}{null_marker}{marker}")

    # Format FKs
    fk_lines: list[str] = []
    for row in fk_result["rows"]:
        from_t, from_c, to_t, to_c = row
        fk_lines.append(f"  FK: {from_t}.{from_c} -> {to_t}.{to_c}")

    lines = []
    for table, columns in table_cols.items():
        lines.append(f"TABLE {table}:")
        lines.extend(columns)
        lines.append("")

    if fk_lines:
        lines.append("FOREIGN KEYS:")
        lines.extend(fk_lines)
        lines.append("")

    return "\n".join(lines)


async def value_samples(table: str, column: str, limit: int = 10) -> list[str]:
    """Return sample distinct values from a column (for disambiguation / correction)."""
    # Validate table/column names to prevent injection (alphanumeric + underscore only)
    if not table.replace("_", "").isalnum() or not column.replace("_", "").isalnum():
        raise ValueError("Invalid table or column name")

    result = await execute_query(
        f"SELECT DISTINCT {column}::TEXT FROM {table} "
        f"WHERE {column} IS NOT NULL "
        f"ORDER BY {column}::TEXT LIMIT $1",
        [limit],
    )
    return [row[0] for row in result["rows"]]
