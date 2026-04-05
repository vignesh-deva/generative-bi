"""
Eval: SQL Agent — structural validity of generated queries.

Calls the real LLM with the FMCG schema injected as context.
Does NOT execute queries against a real DB — asserts structural properties:
  - Starts with SELECT or WITH
  - Contains no forbidden DML/DDL keywords
  - References at least one expected table

Run:  RUN_EVAL=1 python -m pytest tests/eval/test_sql_agent.py -v
"""

import os
import re
import pytest
from agents.sql_agent import generate_sql

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_EVAL"), reason="Set RUN_EVAL=1 to run eval tests"
)
from tests.eval.conftest import SCHEMA_STUB, FMCG_TABLES
from config.semantic_layer import SEMANTIC_LAYER
from agents.tools.semantic_tools import get_semantic_context

# Semantic context using the real semantic layer (no DB needed)
SEMANTIC_CTX = get_semantic_context(FMCG_TABLES)

# DML/DDL keywords that must never appear in generated SQL
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE)\b",
    re.IGNORECASE,
)

# ── Test cases ─────────────────────────────────────────────────────
# (query, tables_that_must_appear_in_sql)

SQL_CASES = [
    (
        "What is the total revenue by zone for Q1 2025?",
        ["sales", "zones"],
    ),
    (
        "Show the top 10 distributors by order volume",
        ["orders", "distributors"],
    ),
    (
        "What is the gross profit margin by product category this year?",
        ["sales", "products", "categories"],
    ),
    (
        "Which products are currently out of stock (stock_qty = 0)?",
        ["inventory", "products"],
    ),
    (
        "What is the average delivery time in days per zone?",
        ["shipments"],
    ),
    (
        "How many Fulfilled vs Cancelled orders does each distributor have?",
        ["orders", "distributors"],
    ),
]


# ── Helpers ────────────────────────────────────────────────────────


def _is_select(sql: str) -> bool:
    stripped = sql.strip().lstrip("(").upper()
    return stripped.startswith("SELECT") or stripped.startswith("WITH")


def _has_no_forbidden(sql: str) -> bool:
    return not FORBIDDEN.search(sql)


def _references_tables(sql: str, expected_tables: list[str]) -> bool:
    sql_lower = sql.lower()
    return any(t in sql_lower for t in expected_tables)


# ── Parametrized tests ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "query,expected_tables",
    SQL_CASES,
    ids=[c[0][:55] for c in SQL_CASES],
)
async def test_sql_is_valid_select(query, expected_tables):
    sql = await generate_sql(
        query=query,
        schema_context=SCHEMA_STUB,
        semantic_context=SEMANTIC_CTX,
        few_shot_examples=[],
        chat_history=[],
    )

    assert sql, "SQL agent returned an empty string"

    assert _is_select(sql), (
        f"Generated SQL does not start with SELECT/WITH.\n"
        f"Query: {query!r}\n"
        f"SQL:   {sql[:300]}"
    )

    assert _has_no_forbidden(sql), (
        f"Generated SQL contains forbidden DML/DDL keyword.\n"
        f"Query: {query!r}\n"
        f"SQL:   {sql[:300]}"
    )

    assert _references_tables(sql, expected_tables), (
        f"Generated SQL does not reference any expected table.\n"
        f"Query:           {query!r}\n"
        f"Expected tables: {expected_tables}\n"
        f"SQL:             {sql[:300]}"
    )


# ── Adapt path: high-similarity RAG match ────────────────────────
# When a RAG example has similarity >= 0.85 the agent adapts it.
# Verify the adapted SQL is still a valid SELECT.


async def test_sql_adapt_from_rag_match():
    """High-similarity RAG match triggers adapt path — result must be SELECT."""
    matched_example = {
        "question": "What is the total revenue by zone?",
        "sql": (
            "SELECT z.name AS zone, SUM(s.qty_sold * s.selling_price) AS revenue "
            "FROM sales s "
            "JOIN retailers r ON s.retailer_id = r.retailer_id "
            "JOIN cities c ON r.city_id = c.city_id "
            "JOIN states st ON c.state_id = st.state_id "
            "JOIN zones z ON st.zone_id = z.zone_id "
            "GROUP BY z.name ORDER BY revenue DESC"
        ),
        "similarity": 0.91,  # above 0.85 threshold → adapt path
    }

    sql = await generate_sql(
        query="What is the total revenue by zone for Q4 2024?",
        schema_context=SCHEMA_STUB,
        semantic_context=SEMANTIC_CTX,
        few_shot_examples=[matched_example],
        chat_history=[],
    )

    assert _is_select(sql), f"Adapted SQL does not start with SELECT/WITH: {sql[:300]}"
    assert _has_no_forbidden(sql), f"Adapted SQL contains forbidden keyword: {sql[:300]}"
    assert "sales" in sql.lower(), "Adapted SQL should reference the sales table"
