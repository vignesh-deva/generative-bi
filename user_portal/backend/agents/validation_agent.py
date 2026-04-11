"""
Stage 3 validation agents — dry-run, error classification, correction, and logic check.

Dry-Run Validator: EXPLAIN on PostgreSQL (deterministic, no LLM)
Error Classifier: pure LLM call, categorizes errors (syntax/schema/logic/runtime)
Correction Agent: LLM + tools (pull_schema, value_samples, dry_run_explain)
Logic Check Agent: agentic LLM with tool-calling loop (schema, values, dates, test queries)
"""

import json
import logging
import re
from datetime import date

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION, LLM_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
from agents.tools.sql_tools import dry_run_explain
from agents.tools.schema_tools import pull_schema, value_samples, lookup_column
from agents.tools.text_utils import strip_markdown_fences
from utils.timing import AsyncTimedSpan

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=LLM_REQUEST_TIMEOUT)

MAX_TOOL_ROUNDS = 3


# ── Dry-Run Validator ────────────────────────────────────────────

async def validate_dry_run(sql: str) -> tuple[bool, str]:
    """Run EXPLAIN on the SQL. Returns (passed, error_or_plan)."""
    result = await dry_run_explain(sql)
    if result["success"]:
        logger.info("dry_run=passed")
        return True, result["plan"]
    logger.warning("dry_run=failed error=%s", result["error"])
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
    raw = response.choices[0].message.content.strip().lower()
    category = raw if raw in ("syntax", "schema", "logic", "runtime") else "syntax"
    if raw != category:
        logger.warning("unexpected error category=%r, defaulting to syntax", raw)
    logger.info("error_category=%s", category)
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

    # Fetch sample values from text columns to help correction.
    # Helpful for schema errors AND logic errors (filter-value typos often
    # surface as empty result sets or logic failures, not schema errors).
    sample_info = ""
    if error_category in ("schema", "logic") and tables:
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
                except Exception as e:
                    logger.debug("value_samples failed for %s.%s: %s", tbl, col, e)
                    continue
            if samples:
                sample_info = "Sample values:\n" + "\n".join(samples)
        except Exception as e:
            logger.debug("sample-value fetch failed: %s", e)

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

    corrected = strip_markdown_fences(response.choices[0].message.content)
    logger.info("corrected SQL:\n%s", corrected)
    return corrected


# ── Logic Check Agent (agentic with tool use) ───────────────────

LOGIC_CHECK_PROMPT = """You are a logic verification agent for a {domain} system.

{schema_section}

Your job: Given the user's question, the SQL query, and the query results, verify that:
1. The SQL query logically answers the user's question
2. The results make sense (reasonable values, correct date ranges, expected row counts)
3. The aggregations, groupings, and filters match what was asked
4. Entity names used in filters actually exist in the database
5. Date ranges in results are valid (today is {today})

{tool_guidance}

IMPORTANT: Your final response MUST start with exactly one of these two lines:
- CORRECT
- INCORRECT: <brief description of the issue>

Do not add any text before CORRECT or INCORRECT."""

LOGIC_CHECK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Returns today's date as an ISO string (YYYY-MM-DD). Use this to verify whether dates in the query results are valid.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_column",
            "description": (
                "Inspect a database column — type-aware. "
                "For text/varchar: returns distinct values matching an optional search term. "
                "For numeric: returns AVG, MIN, MAX, distinct count. "
                "For date/timestamp: returns the date range (MIN to MAX). "
                "Use this to verify entity names, check value ranges, or confirm date coverage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name (e.g., 'products')"},
                    "column": {"type": "string", "description": "Column name (e.g., 'name')"},
                    "search_term": {
                        "type": "string",
                        "description": "Optional — for text columns, filter values containing this term (e.g., 'chocos')",
                    },
                },
                "required": ["table", "column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "Returns the DDL (columns, types, PKs, FKs) for the specified tables. Use this to verify column names, data types, or join paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of table names",
                    },
                },
                "required": ["tables"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_join_info",
            "description": "Returns only the foreign key relationships for the specified tables. Use this to verify join paths are correct.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of table names",
                    },
                },
                "required": ["tables"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_test_query",
            "description": "Run EXPLAIN on an alternative SQL query to test if it would work. Does NOT execute — only validates syntax and plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "The SQL query to test"},
                },
                "required": ["sql"],
            },
        },
    },
]


async def _dispatch_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if name == "get_current_date":
            return date.today().isoformat()

        if name == "lookup_column":
            return await lookup_column(
                arguments["table"],
                arguments["column"],
                search_term=arguments.get("search_term"),
            )

        if name == "get_schema":
            schema = await pull_schema(arguments["tables"])
            return schema or "No schema found for the specified tables."

        if name == "get_join_info":
            full_schema = await pull_schema(arguments["tables"])
            if "FOREIGN KEYS:" in full_schema:
                return full_schema[full_schema.index("FOREIGN KEYS:"):]
            return "No foreign key relationships found for the specified tables."

        if name == "run_test_query":
            result = await dry_run_explain(arguments["sql"])
            if result["success"]:
                return f"Query is valid. Plan:\n{result['plan']}"
            return f"Query failed: {result['error']}"

        return f"Unknown tool: {name}"

    except Exception as e:
        logger.warning("tool %s failed: %s", name, e)
        return f"Tool error: {str(e)}"


def _parse_logic_verdict(text: str) -> tuple[bool, str]:
    """Parse the logic checker's verdict from its text response.

    Handles three response styles from the LLM:
    1. Clean:   "CORRECT" or "INCORRECT: reason"
    2. Verbose: multi-line analysis ending with "**Final Verdict**: CORRECT"
    3. Mixed:   CORRECT/INCORRECT embedded anywhere in the response

    Uses whole-word matching so "CORRECT" inside "INCORRECT" is not a false pass.
    Prefers the LAST occurrence when the response contains multiple verdict words.
    """
    if not text:
        logger.warning("logic_check empty response, defaulting to passed")
        return True, ""

    # Fast path: clean one-line response starting with the verdict keyword
    upper_stripped = text.lstrip("*# \t\n").upper()
    if upper_stripped.startswith("CORRECT"):
        logger.info("logic_check=passed (clean)")
        return True, ""
    if upper_stripped.startswith("INCORRECT"):
        feedback = re.sub(r"(?i)^incorrect[:\s]*", "", text.lstrip("*# \t\n")).strip()
        logger.warning("logic_check=failed (clean) feedback=%s", feedback)
        return False, feedback

    # Verbose path: scan for the last INCORRECT / CORRECT word boundary match.
    # \bCORRECT\b does NOT match inside "INCORRECT" because the preceding 'R'
    # is a word character, so no word boundary exists before the 'C'.
    last_incorrect = None
    last_correct = None
    for m in re.finditer(r"(?i)\bINCORRECT\b", text):
        last_incorrect = m
    for m in re.finditer(r"(?i)\bCORRECT\b", text):
        last_correct = m

    if last_incorrect is None and last_correct is None:
        # No verdict keyword found — default to passed (be lenient per original intent)
        logger.warning("logic_check: no verdict keyword found, defaulting to passed text=%.120s", text)
        return True, ""

    # Determine which verdict comes last in the response
    incorrect_pos = last_incorrect.end() if last_incorrect else -1
    correct_pos = last_correct.end() if last_correct else -1

    if incorrect_pos > correct_pos:
        # INCORRECT is the final verdict
        after = text[last_incorrect.end():].lstrip(":- \t")
        feedback = after.strip() if after.strip() else text[:200]
        logger.warning("logic_check=failed (verbose) feedback=%s", feedback)
        return False, feedback

    # CORRECT is the final verdict
    logger.info("logic_check=passed (verbose)")
    return True, ""


async def _check_logic_agentic(messages: list[dict]) -> tuple[bool, str]:
    """Agentic logic check with tool-calling loop."""
    final_text = ""
    exhausted_with_tool_calls = False
    for round_num in range(MAX_TOOL_ROUNDS):
        async with AsyncTimedSpan(f"logic_check.llm_round_{round_num + 1}"):
            response = await _client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=LOGIC_CHECK_TOOLS,
                tool_choice="auto",
                temperature=0,
                max_tokens=500,
            )
        msg = response.choices[0].message
        # Append assistant message to conversation
        messages.append(msg)
        final_text = msg.content or ""

        if not msg.tool_calls:
            break

        logger.info(
            "logic_check round=%d tool_calls=%d",
            round_num + 1, len(msg.tool_calls),
        )

        async with AsyncTimedSpan(
            f"logic_check.tools_round_{round_num + 1}",
            calls=len(msg.tool_calls),
        ):
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}
                logger.info("logic_check tool=%s args=%s", tool_name, tool_args)

                result = await _dispatch_tool(tool_name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        # Track whether the final round ended with pending tool calls
        exhausted_with_tool_calls = (round_num == MAX_TOOL_ROUNDS - 1)

    # If we burned through all rounds with tool calls still pending (no final text),
    # force a final verdict by re-asking without tools — don't default-pass.
    if exhausted_with_tool_calls and not final_text.strip():
        logger.warning(
            "logic_check exhausted %d rounds with no final verdict — forcing final text-only call",
            MAX_TOOL_ROUNDS,
        )
        messages.append({
            "role": "user",
            "content": (
                "You have used all available tool rounds. Based on what you've learned, "
                "give your final verdict NOW. Respond with exactly 'CORRECT' or "
                "'INCORRECT: <brief reason>' — no more tool calls."
            ),
        })
        response = await _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=200,
        )
        final_text = response.choices[0].message.content or ""

    return _parse_logic_verdict(final_text)


async def _check_logic_single_shot(messages: list[dict]) -> tuple[bool, str]:
    """Fallback: single-shot logic check without tools (for providers that don't support function calling)."""
    messages_copy = list(messages)
    messages_copy[0] = {
        "role": "system",
        "content": messages[0]["content"]
        + f"\n\nNote: Today's date is {date.today().isoformat()}. Use this to judge date validity.",
    }

    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages_copy,
        temperature=0,
        max_tokens=200,
    )
    return _parse_logic_verdict(response.choices[0].message.content.strip())


async def check_logic(
    query: str,
    sql: str,
    result: dict,
    schema_context: str = "",
) -> tuple[bool, str]:
    """Check if the SQL query logically answers the user's question.

    If schema_context is provided (columns, types, value samples from schema_linker),
    it is embedded directly in the system prompt so the LLM can skip get_schema /
    lookup_column tool calls — cutting the agentic round-trip count from 3 to 1.

    Falls back to single-shot if the LLM provider does not support function calling.
    """
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", 0)

    result_preview = f"Columns: {', '.join(columns)}\nRow count: {row_count}\n"
    if rows:
        for row in rows[:5]:
            result_preview += " | ".join(str(v) for v in row) + "\n"
        if row_count > 5:
            result_preview += f"... ({row_count - 5} more rows)\n"

    # When schema context is available, embed it and tell the LLM not to call
    # get_schema / lookup_column for things already answered by the context.
    if schema_context:
        schema_section = (
            "The following schema and value samples are already available to you "
            "— use them directly without calling get_schema or lookup_column "
            "unless you need something not shown here:\n\n"
            + schema_context[:3000]  # cap to avoid token budget blowout
        )
        tool_guidance = (
            "Only use tools if you need information not covered by the schema above "
            "(e.g., a date range check with get_current_date, or a value that isn't in "
            "the samples). Prefer giving a direct verdict based on the available context."
        )
    else:
        schema_section = (
            "You have tools available to verify your suspicions. "
            "Do NOT guess — use a tool to check before making a judgment."
        )
        tool_guidance = (
            "Available tools: get_current_date, lookup_column, get_schema, "
            "get_join_info, run_test_query."
        )

    system_prompt = LOGIC_CHECK_PROMPT.format(
        domain=DOMAIN_DESCRIPTION,
        today=date.today().isoformat(),
        schema_section=schema_section,
        tool_guidance=tool_guidance,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Question: {query}\n\n"
                f"SQL:\n{sql}\n\n"
                f"Results:\n{result_preview}"
            ),
        },
    ]

    try:
        return await _check_logic_agentic(messages)
    except Exception as e:
        logger.warning("agentic logic check failed (%s), falling back to single-shot", e)
        return await _check_logic_single_shot(messages)
