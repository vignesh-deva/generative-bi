"""
LangGraph v2 pipeline — orchestrates the NL -> SQL -> Insight agent workflow.

5-stage pipeline:
  Stage 0: Fetch chat history from MongoDB
  Stage 0B: Query Rewriter — resolve follow-ups into standalone queries
  Stage 1: Pre-processing — Guardrails + Classifier + RAG (parallel fan-out)
           Routing: analytics -> continue | non-analytics -> Response Agent -> exit
  Stage 1B: Context Enrichment — Schema Linker (+ Semantic Layer)
  Stage 2: SQL Generation — SQL Agent (with Decomposer + Sub-query Generator)
  Stage 3: Validation + Self-repair — Dry-run -> Execute -> Logic Check (agentic)
           Error path: Error Classifier -> Correction Agent -> retry
  Stage 4: Response Synthesis — Insight Agent -> SSE stream

Non-analytics path: 4 LLM calls (Rewriter + Guardrails + Classifier + Response Agent)
Analytics path: ~10 LLM calls across all stages
"""

from __future__ import annotations

import logging
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

from agents.rewrite_agent import rewrite_query
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
from utils.timing import timed_node


# ── State schema ───────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    # Input
    query: str
    session_id: str
    # When True, insight_node skips its LLM call on the analytics success
    # path so the caller can stream insight tokens themselves.
    stream_insight: bool

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
    sql_strategy: str                     # "adapt" | "single" | "multi"

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

@timed_node("fetch_history")
async def history_node(state: PipelineState) -> PipelineState:
    session_id = state.get("session_id", "")
    history = await fetch_chat_history(session_id, limit=10)
    return {"chat_history": history}


# ── Stage 0B: Query Rewriter ────────────────────────────────────

@timed_node("query_rewriter")
async def rewrite_node(state: PipelineState) -> PipelineState:
    rewritten = await rewrite_query(
        state["query"],
        chat_history=state.get("chat_history"),
    )
    return {"query": rewritten}


# ── Stage 1: Pre-processing (parallel) ──────────────────────────

@timed_node("classifier")
async def classify_node(state: PipelineState) -> PipelineState:
    intent = await classify(
        state["query"],
        chat_history=state.get("chat_history"),
    )
    return {"intent": intent}


@timed_node("guardrails")
async def guardrails_node(state: PipelineState) -> PipelineState:
    passed, reason = await check_guardrails(state["query"])
    return {"guardrail_passed": passed, "guardrail_reason": reason}


@timed_node("rag")
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
        logger.info("routing=non_analytics reason=guardrail_blocked")
        return "non_analytics"
    intent = state.get("intent", "analytics")
    if intent in ("chitchat", "history", "ambiguous"):
        logger.info("routing=non_analytics reason=intent_%s", intent)
        return "non_analytics"
    logger.info("routing=analytics")
    return "analytics"


# ── Non-analytics exit: Response Agent ───────────────────────────

@timed_node("response_agent")
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

@timed_node("schema_linker")
async def schema_linker_node(state: PipelineState) -> PipelineState:
    result = await link_schema(state["query"])
    return {
        "linked_tables": result["tables"],
        "schema_context": result["schema_context"],
        "semantic_context": result["semantic_context"],
    }


# ── Stage 2: SQL Agent ──────────────────────────────────────────

@timed_node("sql_agent")
async def sql_node(state: PipelineState) -> PipelineState:
    sql, strategy = await generate_sql(
        query=state["query"],
        schema_context=state.get("schema_context", ""),
        semantic_context=state.get("semantic_context", ""),
        few_shot_examples=state.get("few_shot_examples", []),
        chat_history=state.get("chat_history", []),
    )
    return {
        "sql_query": sql,
        "sql_strategy": strategy,
        "dry_run_retries": state.get("dry_run_retries", 0),
        "logic_retries": state.get("logic_retries", 0),
    }


# ── Stage 3: Dry-Run Validation ──────────────────────────────────

@timed_node("dry_run")
async def dry_run_node(state: PipelineState) -> PipelineState:
    passed, result = await validate_dry_run(state["sql_query"])
    return {"dry_run_passed": passed, "dry_run_error": "" if passed else result}


def route_after_dry_run(state: PipelineState) -> str:
    """Route after every dry-run.

    If the dry-run passed, go to execute. If it failed, gate the correction
    branch BEHIND the retry-budget check so we never waste an LLM call once
    the budget is exhausted. When budget is exhausted we execute anyway —
    the read-only transaction is the ultimate safety net.
    """
    if state.get("dry_run_passed", False):
        return "passed"
    retries = state.get("dry_run_retries", 0)
    if retries >= MAX_SQL_RETRIES:
        logger.warning(
            "dry_run failed and retry budget exhausted (%d/%d) — executing anyway",
            retries, MAX_SQL_RETRIES,
        )
        return "max_retries"
    logger.info("dry_run failed — routing to error_classifier (retry %d/%d)", retries, MAX_SQL_RETRIES)
    return "failed"


# ── Stage 3: Error path ─────────────────────────────────────────

@timed_node("error_classifier")
async def error_classify_node(state: PipelineState) -> PipelineState:
    category = await classify_error(
        state.get("sql_query", ""),
        state.get("dry_run_error", ""),
    )
    return {"error_category": category}


@timed_node("correction_agent")
async def correction_node(state: PipelineState) -> PipelineState:
    retries = state.get("dry_run_retries", 0) + 1
    logger.info("correction attempt dry_run_retry=%d/%d", retries, MAX_SQL_RETRIES)
    corrected = await correct_sql(
        query=state["query"],
        sql=state.get("sql_query", ""),
        error=state.get("dry_run_error", ""),
        error_category=state.get("error_category", "syntax"),
        tables=state.get("linked_tables", []),
    )
    return {"sql_query": corrected, "dry_run_retries": retries}


# ── Stage 3: Execute + Logic Check ───────────────────────────────

@timed_node("execute")
async def execute_node(state: PipelineState) -> PipelineState:
    try:
        result = await run_query(state["sql_query"])
        logger.info("query executed — rows=%d", result.get("row_count", 0))
        return {"query_result": result}
    except Exception as e:
        logger.error("query execution failed: %s", e)
        return {"query_error": str(e)}


def route_after_execute(state: PipelineState) -> str:
    if state.get("query_error"):
        return "execution_failed"
    # On the adapt path the SQL is based on a curated, human-promoted RAG
    # example — trust it and skip the agentic logic check entirely. That
    # check is a multi-round LLM + tool-calling loop that dominates the
    # tail latency of otherwise-cached queries. The earlier dry-run already
    # validated the SQL syntactically, so we go straight to insight.
    if state.get("sql_strategy") == "adapt":
        logger.info("route_after_execute: skipping logic_check on adapt path")
        return "adapt_skip_logic"
    return "executed"


@timed_node("logic_check")
async def logic_check_node(state: PipelineState) -> PipelineState:
    passed, feedback = await check_logic(
        query=state["query"],
        sql=state.get("sql_query", ""),
        result=state.get("query_result", {}),
        schema_context=state.get("schema_context", ""),
    )
    return {"logic_passed": passed, "logic_feedback": feedback}


def route_after_logic(state: PipelineState) -> str:
    if state.get("logic_passed", True):
        return "correct"
    # Logic failed — route back to correction if retries remain
    if state.get("logic_retries", 0) >= MAX_SQL_RETRIES:
        return "correct"  # proceed anyway after max retries
    return "logic_error"


@timed_node("logic_correction")
async def logic_error_to_correction_node(state: PipelineState) -> PipelineState:
    """Convert logic error into a correction attempt.

    Resets dry_run_retries so the freshly-corrected SQL gets its own syntactic
    repair budget when it loops back through dry_run. Without this, earlier
    dry-run retries would starve the logic-corrected query's repair budget.
    """
    retries = state.get("logic_retries", 0) + 1
    logger.info(
        "logic correction attempt logic_retry=%d/%d feedback=%s",
        retries, MAX_SQL_RETRIES, state.get("logic_feedback", "")[:120],
    )
    corrected = await correct_sql(
        query=state["query"],
        sql=state.get("sql_query", ""),
        error=f"Logic check failed: {state.get('logic_feedback', '')}",
        error_category="logic",
        tables=state.get("linked_tables", []),
    )
    return {
        "sql_query": corrected,
        "logic_retries": retries,
        "dry_run_retries": 0,
    }


# ── Stage 4: Insight Agent ───────────────────────────────────────

@timed_node("insight_agent")
async def insight_node(state: PipelineState) -> PipelineState:
    if state.get("query_error"):
        return {
            "response": f"I couldn't execute the query: {state['query_error']}",
            "insight": "",
        }

    # If the caller wants to stream the insight themselves, skip the LLM
    # call here — state.query_result is already populated.
    if state.get("stream_insight"):
        return {"insight": "", "response": ""}

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
    graph.add_node("query_rewriter", rewrite_node)
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

    # ── Stage 0B: resolve follow-ups into standalone queries ──
    graph.add_edge("fetch_history", "query_rewriter")

    # ── Stage 1: parallel fan-out from rewriter ───────────────
    graph.add_edge("query_rewriter", "classifier")
    graph.add_edge("query_rewriter", "guardrails")
    graph.add_edge("query_rewriter", "rag")

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

    # ── Dry-run routing (budget check lives here now) ────────
    # "failed" only fires when retries < MAX_SQL_RETRIES; once the budget is
    # exhausted we skip the LLM correction call entirely and execute anyway.
    graph.add_conditional_edges(
        "dry_run",
        route_after_dry_run,
        {
            "passed": "execute",
            "failed": "error_classifier",
            "max_retries": "execute",
        },
    )

    # ── Error path: classify -> correct -> dry_run (loop) ────
    graph.add_edge("error_classifier", "correction_agent")
    graph.add_edge("correction_agent", "dry_run")

    # ── Execute -> check for errors ──────────────────────────
    # Adapt path skips logic_check entirely (curated RAG match is trusted).
    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "executed": "logic_check",
            "execution_failed": "insight_agent",
            "adapt_skip_logic": "insight_agent",
        },
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
