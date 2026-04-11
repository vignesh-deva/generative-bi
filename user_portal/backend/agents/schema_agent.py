"""
Schema Linker agent — identifies relevant tables from the user's query
and returns only those tables' DDL + semantic context.

Replaces v1's full-schema dump with targeted schema linking.
Uses LLM to match query concepts to table names, then pulls
schema + semantic context for only the relevant tables.
"""

import logging

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL, DOMAIN_DESCRIPTION, LLM_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)
from agents.tools.schema_tools import list_tables, pull_schema, pull_value_samples
from agents.tools.semantic_tools import get_semantic_context
from utils.chart_context import format_chart_context_block
from utils.timing import AsyncTimedSpan

# Cap fallback table count to keep the schema prompt within context budget
# when the LLM returns no valid tables.
MAX_FALLBACK_TABLES = 12

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=LLM_REQUEST_TIMEOUT)

SYSTEM_PROMPT = """You are a schema linking agent for a {domain} database.
Given a user's natural language query and a list of available tables, identify which tables
are needed to answer the query.

Available tables:
{tables}

Rules:
- Include tables needed for JOINs (e.g., if asking about sales by zone, include sales, retailers, cities, states, zones)
- Include lookup/dimension tables needed for filtering or grouping
- Don't include tables that are clearly irrelevant
- Return ONLY a comma-separated list of table names, nothing else

Example:
Query: "What is the total revenue by zone for last month?"
Answer: sales,retailers,cities,states,zones"""


async def link_schema(query: str, chart_context: dict | None = None) -> dict:
    """Identify relevant tables and return their schema + semantic context.

    Returns:
        {
            "tables": ["sales", "products", ...],
            "schema_context": "TABLE sales:\n  ...",
            "semantic_context": "METRIC DEFINITIONS:\n  ...",
        }
    """
    async with AsyncTimedSpan("schema_linker.list_tables"):
        all_tables = await list_tables()

    system_content = SYSTEM_PROMPT.format(
        domain=DOMAIN_DESCRIPTION, tables=", ".join(all_tables)
    ) + format_chart_context_block(chart_context)

    async with AsyncTimedSpan("schema_linker.llm_pick_tables"):
        response = await _client.chat.completions.create(
            model=LLM_MODEL_SMALL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=100,
        )

    raw = response.choices[0].message.content.strip()
    linked_tables = [
        t.strip().lower()
        for t in raw.split(",")
        if t.strip().lower() in all_tables
    ]

    # Fallback: if LLM returned nothing useful, use a bounded prefix of the
    # table list so the schema prompt stays within context budget.
    if not linked_tables:
        linked_tables = all_tables[:MAX_FALLBACK_TABLES]
        logger.warning(
            "LLM returned no valid tables (raw=%r), falling back to %d of %d tables",
            raw, len(linked_tables), len(all_tables),
        )

    logger.info("linked_tables=%s query=%.80s", linked_tables, query)

    async with AsyncTimedSpan("schema_linker.pull_schema", tables=len(linked_tables)):
        schema_context = await pull_schema(linked_tables)
    async with AsyncTimedSpan("schema_linker.pull_value_samples", tables=len(linked_tables)):
        value_context = await pull_value_samples(linked_tables)
    if value_context:
        schema_context = schema_context + "\n" + value_context
    semantic_context = get_semantic_context(linked_tables)

    return {
        "tables": linked_tables,
        "schema_context": schema_context,
        "semantic_context": semantic_context,
    }
