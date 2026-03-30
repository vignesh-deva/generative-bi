"""
LangGraph v2 pipeline — orchestrates the NL -> SQL -> Insight agent workflow.

4-stage pipeline:
  Stage 0: Fetch chat history from MongoDB
  Stage 1: Pre-processing — Guardrails + Classifier + RAG (parallel fan-out)
           Routing: analytics -> continue | non-analytics -> Response Agent -> exit
  Stage 1B: Context Enrichment — Schema Linker (+ Semantic Layer)
  Stage 2: SQL Generation — SQL Agent (with Decomposer + Sub-query Generator)
  Stage 3: Validation + Self-repair — Dry-run -> Execute -> Logic Check
           Error path: Error Classifier -> Correction Agent -> retry
  Stage 4: Response Synthesis — Insight Agent -> SSE stream

Non-analytics path: 3 LLM calls (Guardrails + Classifier + Response Agent)
Analytics path: ~9 LLM calls across all stages
"""

from __future__ import annotations

from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from agents.classifier import classify
from agents.guardrails import check_guardrails
from agents.rag_agent import retrieve_examples
from agents.schema_agent import link_schema
from agents.sql_agent import generate_sql
from agents.validation_agent import validate_dry_run, classify_error, correct_sql, check_logic
from agents.insight_agent import generate_insight
from agents.response_agent import generate_response
from agents.tools.history_tools import fetch_chat_history
from agents.tools.sql_tools import run_query
from config.settings import MAX_SQL_RETRIES


# ── State schema ───────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    # Input
    query: str
    session_id: str

    # Chat history (fetched from MongoDB)
    chat_history: list[dict]

    # Stage 1: parallel fan-out
    intent: str                          # "analytics" | "chitchat" | "history" | "ambiguous"
    guardrail_passed: bool
    guardrail_reason: str
    few_shot_examples: list[dict]        # [{question, sql, similarity}, ...]

    # Stage 1B: Schema Linker
    linked_tables: list[str]
    schema_context: str
    semantic_context: str

    # Stage 2: SQL Agent
    sql_query: str

    # Stage 3: Validation loop
    dry_run_retries: int
    logic_retries: int
    dry_run_passed: bool
    dry_run_error: str
    error_category: str

    # Query execution
    query_result: dict                   # {columns, rows, row_count}
    query_error: str

    # Logic check
    logic_passed: bool
    logic_feedback: str

    # Stage 4: Response
    insight: str
    response: str                        # final text sent to user

    # Control
    error: str


# ── Stage 0: Fetch chat history ──────────────────────────────────

async def history_node(state: PipelineState) -> PipelineState:
    session_id = state.get("session_id", "")
    history = await fetch_chat_history(session_id, limit=10)
    return {"chat_history": history}


# ── Stage 1: Pre-processing (parallel) ──────────────────────────

async def classify_node(state: PipelineState) -> PipelineState:
    intent = await classify(
        state["query"],
        chat_history=state.get("chat_history"),
    )
    return {"intent": intent}


async def guardrails_node(state: PipelineState) -> PipelineState:
    passed, reason = await check_guardrails(state["query"])
    return {"guardrail_passed": passed, "guardrail_reason": reason}


async def rag_node(state: PipelineState) -> PipelineState:
    examples = await retrieve_examples(state["query"])
    return {"few_shot_examples": examples}


# ── Fan-in router (pass-through node) ────────────────────────────

async def router_node(state: PipelineState) -> PipelineState:
    """Pass-through node that serves as the fan-in point for parallel branches."""
    return {}


# ── Routing after Stage 1 ───────────────────────────────────────

def route_after_fanin(state: PipelineState) -> str:
    """Route after parallel fan-out merges."""
    if not state.get("guardrail_passed", True):
        return "non_analytics"
    intent = state.get("intent", "analytics")
    if intent in ("chitchat", "history", "ambiguous"):
        return "non_analytics"
    return "analytics"


# ── Non-analytics exit: Response Agent ───────────────────────────

async def response_node(state: PipelineState) -> PipelineState:
    """Handle all non-analytics intents via Response Agent."""
    intent = state.get("intent", "chitchat")

    # If guardrails blocked, override intent to "blocked"
    if not state.get("guardrail_passed", True):
        intent = "blocked"

    response = await generate_response(
        query=state["query"],
        intent=intent,
        chat_history=state.get("chat_history"),
        guardrail_reason=state.get("guardrail_reason", ""),
    )
    return {"response": response}


# ── Stage 1B: Schema Linker ─────────────────────────────────────

async def schema_linker_node(state: PipelineState) -> PipelineState:
    result = await link_schema(state["query"])
    return {
        "linked_tables": result["tables"],
        "schema_context": result["schema_context"],
        "semantic_context": result["semantic_context"],
    }


# ── Stage 2: SQL Agent ──────────────────────────────────────────

async def sql_node(state: PipelineState) -> PipelineState:
    sql = await generate_sql(
        query=state["query"],
        schema_context=state.get("schema_context", ""),
        semantic_context=state.get("semantic_context", ""),
        few_shot_examples=state.get("few_shot_examples", []),
        chat_history=state.get("chat_history", []),
    )
    return {
        "sql_query": sql,
        "dry_run_retries": state.get("dry_run_retries", 0),
        "logic_retries": state.get("logic_retries", 0),
    }


# ── Stage 3: Dry-Run Validation ──────────────────────────────────

async def dry_run_node(state: PipelineState) -> PipelineState:
    passed, result = await validate_dry_run(state["sql_query"])
    return {"dry_run_passed": passed, "dry_run_error": "" if passed else result}


def route_after_dry_run(state: PipelineState) -> str:
    if state.get("dry_run_passed", False):
        return "passed"
    return "failed"


# ── Stage 3: Error path ─────────────────────────────────────────

async def error_classify_node(state: PipelineState) -> PipelineState:
    category = await classify_error(
        state.get("sql_query", ""),
        state.get("dry_run_error", ""),
    )
    return {"error_category": category}


async def correction_node(state: PipelineState) -> PipelineState:
    retries = state.get("dry_run_retries", 0) + 1
    corrected = await correct_sql(
        query=state["query"],
        sql=state.get("sql_query", ""),
        error=state.get("dry_run_error", ""),
        error_category=state.get("error_category", "syntax"),
        tables=state.get("linked_tables", []),
    )
    return {"sql_query": corrected, "dry_run_retries": retries}


def route_after_correction(state: PipelineState) -> str:
    if state.get("dry_run_retries", 0) >= MAX_SQL_RETRIES:
        return "max_retries"
    return "retry"


# ── Stage 3: Execute + Logic Check ───────────────────────────────

async def execute_node(state: PipelineState) -> PipelineState:
    try:
        result = await run_query(state["sql_query"])
        return {"query_result": result}
    except Exception as e:
        return {"query_error": str(e)}


def route_after_execute(state: PipelineState) -> str:
    if state.get("query_error"):
        return "execution_failed"
    return "executed"


async def logic_check_node(state: PipelineState) -> PipelineState:
    passed, feedback = await check_logic(
        query=state["query"],
        sql=state.get("sql_query", ""),
        result=state.get("query_result", {}),
    )
    return {"logic_passed": passed, "logic_feedback": feedback}


def route_after_logic(state: PipelineState) -> str:
    if state.get("logic_passed", True):
        return "correct"
    # Logic failed — route back to correction if retries remain
    if state.get("logic_retries", 0) >= MAX_SQL_RETRIES:
        return "correct"  # proceed anyway after max retries
    return "logic_error"


async def logic_error_to_correction_node(state: PipelineState) -> PipelineState:
    """Convert logic error into a correction attempt."""
    retries = state.get("logic_retries", 0) + 1
    corrected = await correct_sql(
        query=state["query"],
        sql=state.get("sql_query", ""),
        error=f"Logic check failed: {state.get('logic_feedback', '')}",
        error_category="logic",
        tables=state.get("linked_tables", []),
    )
    return {"sql_query": corrected, "logic_retries": retries}


# ── Stage 4: Insight Agent ───────────────────────────────────────

async def insight_node(state: PipelineState) -> PipelineState:
    if state.get("query_error"):
        return {
            "response": f"I couldn't execute the query: {state['query_error']}",
            "insight": "",
        }

    insight = await generate_insight(
        query=state["query"],
        sql=state.get("sql_query", ""),
        result=state.get("query_result", {}),
    )
    return {"insight": insight, "response": insight}


# ── Graph assembly ────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """Build and compile the v2 LangGraph pipeline."""

    graph = StateGraph(PipelineState)

    # ── Nodes ─────────────────────────────────────────────────
    graph.add_node("fetch_history", history_node)
    graph.add_node("classifier", classify_node)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("rag", rag_node)
    graph.add_node("router", router_node)
    graph.add_node("response_agent", response_node)
    graph.add_node("schema_linker", schema_linker_node)
    graph.add_node("sql_agent", sql_node)
    graph.add_node("dry_run", dry_run_node)
    graph.add_node("error_classifier", error_classify_node)
    graph.add_node("correction_agent", correction_node)
    graph.add_node("execute", execute_node)
    graph.add_node("logic_check", logic_check_node)
    graph.add_node("logic_correction", logic_error_to_correction_node)
    graph.add_node("insight_agent", insight_node)

    # ── Stage 0: fetch chat history first ─────────────────────
    graph.add_edge("__start__", "fetch_history")

    # ── Stage 1: parallel fan-out from history ────────────────
    graph.add_edge("fetch_history", "classifier")
    graph.add_edge("fetch_history", "guardrails")
    graph.add_edge("fetch_history", "rag")

    # ── Fan-in: all three converge at router node ─────────────
    graph.add_edge("classifier", "router")
    graph.add_edge("guardrails", "router")
    graph.add_edge("rag", "router")

    # ── Route based on merged state ───────────────────────────
    graph.add_conditional_edges(
        "router",
        route_after_fanin,
        {"analytics": "schema_linker", "non_analytics": "response_agent"},
    )

    # Response Agent -> END
    graph.add_edge("response_agent", END)

    # ── Stage 1B -> Stage 2 ──────────────────────────────────
    graph.add_edge("schema_linker", "sql_agent")

    # ── Stage 2 -> Stage 3: Dry-run ─────────────────────────
    graph.add_edge("sql_agent", "dry_run")

    # ── Dry-run routing ──────────────────────────────────────
    graph.add_conditional_edges(
        "dry_run",
        route_after_dry_run,
        {"passed": "execute", "failed": "error_classifier"},
    )

    # ── Error path: classify -> correct -> retry or bail ─────
    graph.add_edge("error_classifier", "correction_agent")
    graph.add_conditional_edges(
        "correction_agent",
        route_after_correction,
        {"retry": "dry_run", "max_retries": "execute"},
    )

    # ── Execute -> check for errors ──────────────────────────
    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {"executed": "logic_check", "execution_failed": "insight_agent"},
    )

    # ── Logic check routing ──────────────────────────────────
    graph.add_conditional_edges(
        "logic_check",
        route_after_logic,
        {"correct": "insight_agent", "logic_error": "logic_correction"},
    )

    # Logic correction -> retry dry-run
    graph.add_edge("logic_correction", "dry_run")

    # ── Insight -> END ───────────────────────────────────────
    graph.add_edge("insight_agent", END)

    return graph.compile()


# Compiled pipeline singleton
pipeline = build_pipeline()
