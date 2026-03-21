"""
Schema agent — introspects the live PostgreSQL schema and formats it
as context for the SQL Agent's system prompt.

Queries information_schema for tables, columns, types, and constraints.
"""

from db.database import execute_query

SCHEMA_QUERY = """
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
    AND t.table_type = 'BASE TABLE'
    AND t.table_name NOT IN ('fewshot_examples')
ORDER BY t.table_name, c.ordinal_position
"""


async def get_schema_context() -> str:
    result = await execute_query(SCHEMA_QUERY)

    tables: dict[str, list[str]] = {}
    for row in result["rows"]:
        table, col, dtype, nullable, pk = row
        marker = " [PK]" if pk else ""
        null_marker = "" if nullable == "YES" else " NOT NULL"
        tables.setdefault(table, []).append(
            f"  {col} {dtype}{null_marker}{marker}"
        )

    lines = []
    for table, columns in tables.items():
        lines.append(f"TABLE {table}:")
        lines.extend(columns)
        lines.append("")

    return "\n".join(lines)
