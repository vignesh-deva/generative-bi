"""
Chat endpoint — accepts a natural language query and streams
the agent pipeline response as Server-Sent Events (SSE).

SSE event format:
  data: {"type": "step", "content": "Classifying intent"}
  data: {"type": "token", "content": "..."}
  data: {"type": "sql", "content": "SELECT ..."}
  data: {"type": "error", "content": "..."}
  data: [DONE]
"""

import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


def sse_event(data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"data: {payload}\n\n"


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

    await chat_messages().insert_one(
        {
            "session_id": session_id,
            "role": "user",
            "content": req.query,
            "sql_query": None,
            "feedback": None,
            "created_at": datetime.now(timezone.utc),
        }
    )

    async def event_stream():
        result: dict = {}
        response_text = ""
        sql_query = None

        try:
            async for chunk in pipeline.astream(
                {"query": req.query, "session_id": session_id},
                stream_mode="updates",
            ):
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        result.update(node_update)
                    label = STEP_LABELS.get(node_name)
                    if label:
                        yield sse_event({"type": "step", "content": label})

            response_text = result.get("response", "")
            sql_query = result.get("sql_query")

            if sql_query:
                yield sse_event({"type": "sql", "content": sql_query})

            if response_text:
                for word in response_text.split(" "):
                    yield sse_event({"type": "token", "content": word + " "})
            else:
                fallback = "I wasn't able to generate a response for that query. Please try rephrasing."
                yield sse_event({"type": "token", "content": fallback})
                response_text = fallback

        except Exception:
            logger.exception("pipeline error session=%s", session_id)
            response_text = "An error occurred while processing your query. Please try again."
            sql_query = None
            yield sse_event({"type": "error", "content": response_text})

        # Persist assistant response
        await chat_messages().insert_one(
            {
                "session_id": session_id,
                "role": "assistant",
                "content": response_text,
                "sql_query": sql_query,
                "feedback": None,
                "created_at": datetime.now(timezone.utc),
            }
        )

        await chat_sessions().update_one(
            {"session_id": session_id},
            {"$set": {"updated_at": datetime.now(timezone.utc)}},
        )

        logger.info(
            "session=%s done sql=%s response_chars=%d",
            session_id,
            "yes" if sql_query else "no",
            len(response_text),
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
