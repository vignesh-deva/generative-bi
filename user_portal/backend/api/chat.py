"""
Chat endpoint — accepts a natural language query and streams
the agent pipeline response as Server-Sent Events (SSE).

SSE event format:
  data: {"type": "step", "content": "Classifying intent"}
  data: {"type": "token", "content": "..."}
  data: {"type": "sql", "content": "SELECT ..."}
  data: {"type": "error", "content": "..."}
  data: [DONE]

Streaming behavior:
- Analytics path: insight tokens are streamed live from the LLM as they
  arrive (via insight_agent.stream_insight).
- Non-analytics path: the short response from response_agent is emitted as
  one token event — no fake word-splitting.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
timing_logger = logging.getLogger("pipeline.timing")

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.insight_agent import stream_insight
from config.settings import PIPELINE_TIMEOUT_SECONDS
from db.mongo import chat_sessions, chat_messages
from graph.pipeline import pipeline

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Maps LangGraph node names to human-readable step labels.
# Nodes absent from this dict (fetch_history, router) emit no step event.
STEP_LABELS: dict[str, str] = {
    "query_rewriter":   "Resolving query",
    "classifier":       "Classifying intent",
    "guardrails":       "Checking safety",
    "rag":              "Retrieving examples",
    "schema_linker":    "Linking schema",
    "sql_agent":        "Generating SQL",
    "dry_run":          "Validating syntax",
    "error_classifier": "Diagnosing error",
    "correction_agent": "Correcting SQL",
    "execute":          "Executing query",
    "logic_check":      "Checking logic",
    "logic_correction": "Refining logic",
    "insight_agent":    "Synthesizing insight",
    "response_agent":   "Generating response",
}


class ChartContext(BaseModel):
    """A chart the user attached to their message via the slash-command picker.

    Carries only the metadata the agents need to ground their reasoning —
    title for human-readable references, sql_query for exact filters/joins/grain.
    """
    chart_id: str
    title: str
    sql_query: str


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    chart_context: ChartContext | None = None


def sse_event(data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"data: {payload}\n\n"


async def _run_pipeline(query: str, session_id: str, chart_context: dict | None):
    """Stream pipeline updates as nodes complete. Raises asyncio.TimeoutError if
    the overall wall-clock deadline is exceeded between chunks.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + PIPELINE_TIMEOUT_SECONDS

    async for chunk in pipeline.astream(
        {
            "query": query,
            "session_id": session_id,
            "stream_insight": True,
            "chart_context": chart_context,
        },
        stream_mode="updates",
    ):
        if loop.time() > deadline:
            raise asyncio.TimeoutError()
        for node_name, node_update in chunk.items():
            yield node_name, node_update


@router.post("")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    logger.info("session=%s query=%.120s", session_id, req.query)

    existing = await chat_sessions().find_one({"session_id": session_id})
    if not existing:
        await chat_sessions().insert_one(
            {
                "session_id": session_id,
                "title": req.query[:80],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )

    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())

    chart_context_dict = req.chart_context.model_dump() if req.chart_context else None

    await chat_messages().insert_one(
        {
            "message_id": user_message_id,
            "session_id": session_id,
            "role": "user",
            "content": req.query,
            "sql_query": None,
            "chart_context": chart_context_dict,
            "feedback": None,
            "feedback_comment": None,
            "feedback_at": None,
            "created_at": datetime.now(timezone.utc),
        }
    )

    async def event_stream():
        result: dict = {}
        response_text = ""
        sql_query = None
        request_start = time.perf_counter()

        # Tell the client which message_id the upcoming assistant reply will have,
        # so thumbs up/down can be submitted against it immediately.
        yield sse_event({"type": "message_id", "content": assistant_message_id})

        try:
            async for node_name, node_update in _run_pipeline(
                req.query, session_id, chart_context_dict
            ):
                if isinstance(node_update, dict):
                    result.update(node_update)
                label = STEP_LABELS.get(node_name)
                if label:
                    yield sse_event({"type": "step", "content": label})
            graph_end = time.perf_counter()
            timing_logger.info(
                "[timing] phase=graph_total elapsed=%.0fms session=%s",
                (graph_end - request_start) * 1000,
                session_id,
            )

            sql_query = result.get("sql_query")
            if sql_query:
                yield sse_event({"type": "sql", "content": sql_query})

            # Analytics success path: stream insight tokens live from the LLM.
            query_result = result.get("query_result")
            query_error = result.get("query_error")

            if query_error:
                response_text = f"I couldn't execute the query: {query_error}"
                yield sse_event({"type": "token", "content": response_text})
            elif query_result is not None:
                # Stream the insight directly from the LLM
                stream_start = time.perf_counter()
                first_token_at: float | None = None
                async for delta in stream_insight(
                    query=req.query,
                    sql=sql_query or "",
                    result=query_result,
                    chart_context=chart_context_dict,
                ):
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    response_text += delta
                    yield sse_event({"type": "token", "content": delta})
                stream_end = time.perf_counter()
                timing_logger.info(
                    "[timing] phase=stream_insight elapsed=%.0fms ttft=%sms chars=%d",
                    (stream_end - stream_start) * 1000,
                    f"{(first_token_at - stream_start) * 1000:.0f}" if first_token_at else "NA",
                    len(response_text),
                )
            else:
                # Non-analytics path: response_agent already produced the text
                cached = result.get("response", "")
                if cached:
                    response_text = cached
                    yield sse_event({"type": "token", "content": cached})
                else:
                    fallback = (
                        "I wasn't able to generate a response for that query. "
                        "Please try rephrasing."
                    )
                    response_text = fallback
                    yield sse_event({"type": "token", "content": fallback})

        except asyncio.TimeoutError:
            logger.warning("pipeline timed out after %ss session=%s", PIPELINE_TIMEOUT_SECONDS, session_id)
            response_text = (
                "The query took too long to process. Please try a simpler "
                "question or try again later."
            )
            sql_query = None
            yield sse_event({"type": "error", "content": response_text})
        except Exception:
            logger.exception("pipeline error session=%s", session_id)
            response_text = "An error occurred while processing your query. Please try again."
            sql_query = None
            yield sse_event({"type": "error", "content": response_text})

        # Persist assistant response — never let this orphan the user message
        try:
            await chat_messages().insert_one(
                {
                    "message_id": assistant_message_id,
                    "session_id": session_id,
                    "role": "assistant",
                    "content": response_text,
                    "sql_query": sql_query,
                    "feedback": None,
                    "feedback_comment": None,
                    "feedback_at": None,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            await chat_sessions().update_one(
                {"session_id": session_id},
                {"$set": {"updated_at": datetime.now(timezone.utc)}},
            )
        except Exception:
            logger.exception("failed to persist assistant reply session=%s", session_id)

        total_ms = (time.perf_counter() - request_start) * 1000
        timing_logger.info(
            "[timing] phase=request_total elapsed=%.0fms session=%s",
            total_ms, session_id,
        )
        logger.info(
            "session=%s done sql=%s response_chars=%d total_ms=%.0f",
            session_id,
            "yes" if sql_query else "no",
            len(response_text),
            total_ms,
        )
        yield sse_event("[DONE]")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )
