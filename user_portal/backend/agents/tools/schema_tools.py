"""
Schema tools — introspect PostgreSQL metadata for schema linking and correction.

Tools:
  pull_schema(tables)  — DDL + FK info for specified tables only
  value_samples(table, column, limit)  — sample distinct values from a column
  list_tables()  — list all user tables in the public schema
  lookup_column(table, column, search_term)  — type-aware column inspection
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

    offset = len(tables)
    fk_placeholders_target = ", ".join(f"${i+1+offset}" for i in range(len(tables)))
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
        AND (tc.table_name IN ({placeholders})
             OR ccu.table_name IN ({fk_placeholders_target}))
    """
    fk_result = await execute_query(fk_query, tables + tables)

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


async def pull_value_samples(tables: list[str], max_per_column: int = 15) -> str:
    """Return sample distinct values for name/text columns of the given tables.

    Targets columns likely used for filtering: 'name', 'title', 'type', 'status'.
    Returns a formatted string suitable for inclusion in an LLM prompt.
    """
    if not tables:
        return ""

    placeholders = ", ".join(f"${i+1}" for i in range(len(tables)))
    col_result = await execute_query(
        f"SELECT table_name, column_name FROM information_schema.columns "
        f"WHERE table_schema = 'public' AND table_name IN ({placeholders}) "
        f"AND data_type IN ('character varying', 'text') "
        f"AND (column_name LIKE '%name%' OR column_name LIKE '%title%' "
        f"     OR column_name LIKE '%type%' OR column_name LIKE '%status%') "
        f"ORDER BY table_name, ordinal_position",
        tables,
    )

    if not col_result["rows"]:
        return ""

    sections = []
    for row in col_result["rows"]:
        tbl, col = row[0], row[1]
        try:
            vals = await value_samples(tbl, col, limit=max_per_column)
            if vals:
                sections.append(f"  {tbl}.{col}: {', '.join(vals)}")
        except Exception:
            continue

    if not sections:
        return ""

    return "VALUE SAMPLES (use exact values for filtering):\n" + "\n".join(sections)


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


async def lookup_column(
    table: str, column: str, search_term: str | None = None, limit: int = 50,
) -> str:
    """Type-aware column inspection — returns appropriate info based on data type.

    - Text/varchar: distinct values matching search_term (ILIKE), or all if no term
    - Numeric (int, numeric, float, double): AVG, MIN, MAX
    - Date/timestamp: MIN, MAX (date range)
    - Other: sample distinct values

    Returns a human-readable string suitable for an LLM tool response.
    """
    if not table.replace("_", "").isalnum() or not column.replace("_", "").isalnum():
        raise ValueError("Invalid table or column name")

    # Detect column data type
    type_result = await execute_query(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2",
        [table, column],
    )
    if not type_result["rows"]:
        return f"Column {table}.{column} not found."

    data_type = type_result["rows"][0][0].lower()

    # Text / varchar columns — distinct value search
    if data_type in ("character varying", "text", "char", "character"):
        if search_term:
            result = await execute_query(
                f"SELECT DISTINCT {column}::TEXT FROM {table} "
                f"WHERE {column}::TEXT ILIKE '%' || $1 || '%' "
                f"ORDER BY {column}::TEXT LIMIT $2",
                [search_term, limit],
            )
            values = [row[0] for row in result["rows"]]
            if not values:
                return f"No values in {table}.{column} matching '{search_term}'."
            return f"{table}.{column} matching '{search_term}': {', '.join(values)}"
        else:
            result = await execute_query(
                f"SELECT DISTINCT {column}::TEXT FROM {table} "
                f"WHERE {column} IS NOT NULL "
                f"ORDER BY {column}::TEXT LIMIT $1",
                [limit],
            )
            values = [row[0] for row in result["rows"]]
            if not values:
                return f"{table}.{column} has no non-null values."
            return f"{table}.{column} distinct values ({len(values)}): {', '.join(values)}"

    # Numeric columns — aggregate stats
    if data_type in (
        "integer", "bigint", "smallint", "numeric", "decimal",
        "real", "double precision",
    ):
        result = await execute_query(
            f"SELECT ROUND(AVG({column})::NUMERIC, 2), MIN({column}), MAX({column}), "
            f"COUNT(DISTINCT {column}) FROM {table} WHERE {column} IS NOT NULL",
        )
        if result["rows"] and result["rows"][0][0] is not None:
            avg, mn, mx, distinct = result["rows"][0]
            return (
                f"{table}.{column} ({data_type}): "
                f"AVG={avg}, MIN={mn}, MAX={mx}, distinct_count={distinct}"
            )
        return f"{table}.{column} has no non-null values."

    # Date / timestamp columns — range
    if "date" in data_type or "timestamp" in data_type:
        result = await execute_query(
            f"SELECT MIN({column})::TEXT, MAX({column})::TEXT FROM {table} "
            f"WHERE {column} IS NOT NULL",
        )
        if result["rows"] and result["rows"][0][0] is not None:
            mn, mx = result["rows"][0]
            return f"{table}.{column} ({data_type}): range {mn} to {mx}"
        return f"{table}.{column} has no non-null values."

    # Fallback — sample distinct values
    result = await execute_query(
        f"SELECT DISTINCT {column}::TEXT FROM {table} "
        f"WHERE {column} IS NOT NULL "
        f"ORDER BY {column}::TEXT LIMIT $1",
        [limit],
    )
    values = [row[0] for row in result["rows"]]
    if not values:
        return f"{table}.{column} has no non-null values."
    return f"{table}.{column} sample values: {', '.join(values)}"
