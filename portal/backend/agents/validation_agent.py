"""
Stage 3 validation agents — dry-run, error classification, correction, and logic check.

Dry-Run Validator: EXPLAIN on PostgreSQL (deterministic, no LLM)
Error Classifier: pure LLM call, categorizes errors (syntax/schema/logic/runtime)
Correction Agent: LLM + tools (pull_schema, value_samples, dry_run_explain)
Logic Check Agent: LLM validates that query results make sense for the question
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION
from agents.tools.sql_tools import dry_run_explain
from agents.tools.schema_tools import pull_schema, value_samples

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


# ── Dry-Run Validator ────────────────────────────────────────────

async def validate_dry_run(sql: str) -> tuple[bool, str]:
    """Run EXPLAIN on the SQL. Returns (passed, error_or_plan)."""
    result = await dry_run_explain(sql)
    if result["success"]:
        return True, result["plan"]
    return False, result["error"]


# ── Error Classifier ─────────────────────────────────────────────

ERROR_CLASSIFIER_PROMPT = """You are an error classifier for PostgreSQL queries.
Given an SQL query and its error message, classify the error into exactly one category:

- "syntax" — SQL syntax error (missing keyword, wrong clause order, bad quoting)
- "schema" — wrong table name, column name, or data type mismatch
- "logic" — query runs but has wrong logic (bad JOIN, missing GROUP BY, wrong aggregation)
- "runtime" — execution error (division by zero, out of memory, timeout)

Respond with ONLY the category name, nothing else."""


async def classify_error(sql: str, error: str) -> str:
    """Classify a SQL error into a category."""
    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": ERROR_CLASSIFIER_PROMPT},
            {"role": "user", "content": f"SQL:\n{sql}\n\nError:\n{error}"},
        ],
        temperature=0,
        max_tokens=20,
    )
    category = response.choices[0].message.content.strip().lower()
    if category not in ("syntax", "schema", "logic", "runtime"):
        return "syntax"
    return category


# ── Correction Agent ─────────────────────────────────────────────

CORRECTION_PROMPT = """You are a SQL correction agent for a {domain} PostgreSQL database.
You are given:
1. The original user question
2. The failed SQL query
3. The error message and error category
4. The database schema for relevant tables
5. Optionally, sample values from columns that may help fix the issue

Your job: fix the SQL query so it runs correctly.

Rules:
- Output ONLY the corrected SQL query, no explanation, no markdown fences
- Use only SELECT statements
- Make minimal changes — fix the specific error, don't rewrite the entire query
- If the error is a schema issue, check the provided schema carefully for correct table/column names

{schema_context}

{sample_values}"""


async def correct_sql(
    query: str,
    sql: str,
    error: str,
    error_category: str,
    tables: list[str],
) -> str:
    """Attempt to correct a failed SQL query using schema and value context."""
    # Pull fresh schema for the relevant tables
    schema_context = await pull_schema(tables)

    # For schema errors, fetch sample values from text columns to help correction
    sample_info = ""
    if error_category == "schema" and tables:
        try:
            from db.database import execute_query as _eq
            # Find actual text/varchar columns for the relevant tables
            col_result = await _eq(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = ANY($1) "
                "AND data_type IN ('character varying', 'text') "
                "ORDER BY table_name, ordinal_position",
                [tables[:3]],
            )
            samples = []
            for row in col_result["rows"][:10]:  # cap total columns sampled
                tbl, col = row[0], row[1]
                try:
                    vals = await value_samples(tbl, col, limit=5)
                    if vals:
                        samples.append(f"  {tbl}.{col}: {', '.join(vals)}")
                except Exception:
                    continue
            if samples:
                sample_info = "Sample values:\n" + "\n".join(samples)
        except Exception:
            pass

    system = CORRECTION_PROMPT.format(
        domain=DOMAIN_DESCRIPTION,
        schema_context=f"Schema:\n{schema_context}" if schema_context else "",
        sample_values=sample_info,
    )

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"Failed SQL:\n{sql}\n\n"
                    f"Error ({error_category}): {error}\n\n"
                    f"Please fix the SQL query."
                ),
            },
        ],
        temperature=0,
        max_tokens=1024,
    )

    corrected = response.choices[0].message.content.strip()
    if corrected.startswith("```"):
        corrected = corrected.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return corrected


# ── Logic Check Agent ────────────────────────────────────────────

LOGIC_CHECK_PROMPT = f"""You are a logic check agent for a {DOMAIN_DESCRIPTION} system.
Given the user's question, the SQL query, and the query results, verify that:

1. The SQL query logically answers the user's question
2. The results make sense (e.g., no negative revenue, reasonable row counts)
3. The aggregations and groupings match what was asked

If the logic is correct, respond with exactly: CORRECT
If there's a logic issue, respond with: INCORRECT: <brief description of the issue>

Be lenient — minor formatting differences are OK. Only flag genuine logic errors."""


async def check_logic(
    query: str,
    sql: str,
    result: dict,
) -> tuple[bool, str]:
    """Check if the SQL query logically answers the user's question."""
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", 0)

    result_preview = f"Columns: {', '.join(columns)}\nRow count: {row_count}\n"
    if rows:
        for row in rows[:5]:
            result_preview += " | ".join(str(v) for v in row) + "\n"
        if row_count > 5:
            result_preview += f"... ({row_count - 5} more rows)\n"

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {"role": "system", "content": LOGIC_CHECK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"SQL:\n{sql}\n\n"
                    f"Results:\n{result_preview}"
                ),
            },
        ],
        temperature=0,
        max_tokens=200,
    )

    text = response.choices[0].message.content.strip()
    if text.upper().startswith("CORRECT"):
        return True, ""
    feedback = text.replace("INCORRECT:", "").strip() if "INCORRECT:" in text.upper() else text
    return False, feedback
