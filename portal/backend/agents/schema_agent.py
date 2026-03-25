"""
Schema Linker agent — identifies relevant tables from the user's query
and returns only those tables' DDL + semantic context.

Replaces v1's full-schema dump with targeted schema linking.
Uses LLM to match query concepts to table names, then pulls
schema + semantic context for only the relevant tables.
"""

from openai import AsyncOpenAI

from config.settings import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL_SMALL
from agents.tools.schema_tools import list_tables, pull_schema
from agents.tools.semantic_tools import get_semantic_context

_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

SYSTEM_PROMPT = """You are a schema linking agent for an FMCG supply chain database.
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


async def link_schema(query: str) -> dict:
    """Identify relevant tables and return their schema + semantic context.

    Returns:
        {
            "tables": ["sales", "products", ...],
            "schema_context": "TABLE sales:\n  ...",
            "semantic_context": "METRIC DEFINITIONS:\n  ...",
        }
    """
    all_tables = await list_tables()

    response = await _client.chat.completions.create(
        model=LLM_MODEL_SMALL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(tables=", ".join(all_tables)),
            },
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

    # Fallback: if LLM returned nothing useful, include core tables
    if not linked_tables:
        linked_tables = ["sales", "products", "categories", "retailers"]

    schema_context = await pull_schema(linked_tables)
    semantic_context = get_semantic_context(linked_tables)

    return {
        "tables": linked_tables,
        "schema_context": schema_context,
        "semantic_context": semantic_context,
    }
