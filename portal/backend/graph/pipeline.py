"""
LangGraph pipeline — orchestrates the NL → SQL → Insight agent workflow.

Pipeline flow:
  User Query
    ├── Classifier (intent)       ─┐
    ├── Guardrails (safety)        ├── parallel fan-out
    └── RAG Lookup (few-shot)     ─┘
              │
        Schema Agent
              │
         SQL Agent ◄── Validation Agent (max 2 retries)
              │
      Query Execution (PostgreSQL)
              │
        Insight Agent
              │
     SSE stream → Frontend
"""

from __future__ import annotations

from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from agents.classifier import classify
from agents.guardrails import check_guardrails
from agents.rag_agent import retrieve_fewshots
from agents.schema_agent import get_schema_context
from agents.sql_agent import generate_sql
from agents.validation_agent import validate_sql
from agents.insight_agent import generate_insight
from db.database import execute_query

MAX_SQL_RETRIES = 2


# ── State schema ───────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    # Input
    query: str

    # Parallel fan-out outputs
    intent: str                          # "analytics" | "chitchat" | "out_of_scope"
    guardrail_passed: bool
    guardrail_reason: str
    few_shot_examples: list[dict]        # [{question, sql}, ...]

    # Schema Agent
    schema_context: str                  # formatted table/column metadata

    # SQL Agent + Validation loop
    sql_query: str
    sql_retries: int
    validation_passed: bool
    validation_feedback: str

    # Query execution
    query_result: dict                   # {columns, rows, row_count}
    query_error: str

    # Insight Agent
    insight: str

    # Control
    error: str


# ── Node functions ─────────────────────────────────────────────────

async def classify_node(state: PipelineState) -> PipelineState:
    intent = await classify(state["query"])
    return {"intent": intent}


async def guardrails_node(state: PipelineState) -> PipelineState:
    passed, reason = await check_guardrails(state["query"])
    return {"guardrail_passed": passed, "guardrail_reason": reason}


async def rag_node(state: PipelineState) -> PipelineState:
    examples = await retrieve_fewshots(state["query"])
    return {"few_shot_examples": examples}


async def schema_node(state: PipelineState) -> PipelineState:
    context = await get_schema_context()
    return {"schema_context": context}


async def sql_node(state: PipelineState) -> PipelineState:
    retries = state.get("sql_retries", 0)
    feedback = state.get("validation_feedback", "")

    sql = await generate_sql(
        query=state["query"],
        schema_context=state.get("schema_context", ""),
        few_shot_examples=state.get("few_shot_examples", []),
        previous_error=feedback if retries > 0 else "",
    )
    return {"sql_query": sql, "sql_retries": retries + 1}


async def validation_node(state: PipelineState) -> PipelineState:
    passed, feedback = await validate_sql(
        sql=state.get("sql_query", ""),
        schema_context=state.get("schema_context", ""),
    )
    return {"validation_passed": passed, "validation_feedback": feedback}


async def execute_node(state: PipelineState) -> PipelineState:
    try:
        result = await execute_query(state["sql_query"])
        return {"query_result": result}
    except Exception as e:
        return {"query_error": str(e)}


async def insight_node(state: PipelineState) -> PipelineState:
    if state.get("query_error"):
        return {"insight": f"Query execution failed: {state['query_error']}"}

    insight = await generate_insight(
        query=state["query"],
        sql=state.get("sql_query", ""),
        result=state.get("query_result", {}),
    )
    return {"insight": insight}


# ── Routing functions ──────────────────────────────────────────────

def after_fanin(state: PipelineState) -> str:
    """Route after parallel fan-out merges."""
    if not state.get("guardrail_passed", True):
        return "blocked"
    if state.get("intent") in ("chitchat", "out_of_scope"):
        return "non_analytics"
    return "analytics"


def after_validation(state: PipelineState) -> str:
    """Route after validation — retry or proceed."""
    if state.get("validation_passed", False):
        return "valid"
    if state.get("sql_retries", 0) >= MAX_SQL_RETRIES:
        return "max_retries"
    return "retry"


# ── Graph assembly ─────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """Build and compile the LangGraph pipeline."""

    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("classifier", classify_node)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("rag", rag_node)
    graph.add_node("schema_agent", schema_node)
    graph.add_node("sql_agent", sql_node)
    graph.add_node("validation_agent", validation_node)
    graph.add_node("execute", execute_node)
    graph.add_node("insight_agent", insight_node)

    # Entry: parallel fan-out to classifier, guardrails, rag
    graph.set_entry_point("classifier")

    # Parallel branches — classifier, guardrails, rag all start from entry
    # LangGraph handles fan-out via multiple edges from the same source
    graph.add_edge("classifier", "schema_agent")
    graph.add_edge("guardrails", "schema_agent")
    graph.add_edge("rag", "schema_agent")

    # After fan-in at schema_agent, route based on intent + guardrails
    graph.add_conditional_edges(
        "schema_agent",
        after_fanin,
        {
            "analytics": "sql_agent",
            "non_analytics": END,
            "blocked": END,
        },
    )

    # SQL Agent → Validation
    graph.add_edge("sql_agent", "validation_agent")

    # Validation → conditional (retry or execute)
    graph.add_conditional_edges(
        "validation_agent",
        after_validation,
        {
            "valid": "execute",
            "retry": "sql_agent",
            "max_retries": "execute",  # try anyway after max retries
        },
    )

    # Execute → Insight → END
    graph.add_edge("execute", "insight_agent")
    graph.add_edge("insight_agent", END)

    return graph.compile()


# Compiled pipeline singleton
pipeline = build_pipeline()
