"""
Chat endpoint — accepts a natural language query and streams
the agent pipeline response as Server-Sent Events (SSE).

SSE event format:
  data: {"type": "token", "content": "..."}
  data: {"type": "sql", "content": "SELECT ..."}
  data: {"type": "status", "content": "classifying..."}
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


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


def sse_event(data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"data: {payload}\n\n"


@router.post("")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

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
        yield sse_event({"type": "status", "content": "Processing your query..."})

        try:
            result = await pipeline.ainvoke(
                {"query": req.query, "session_id": session_id}
            )

            response_text = result.get("response", "")
            sql_query = result.get("sql_query")

            if sql_query:
                yield sse_event({"type": "sql", "content": sql_query})

            if response_text:
                # Stream the response word by word for a typing effect
                words = response_text.split(" ")
                for word in words:
                    yield sse_event({"type": "token", "content": word + " "})
            else:
                yield sse_event({
                    "type": "token",
                    "content": "I wasn't able to generate a response for that query. Please try rephrasing.",
                })
                response_text = "I wasn't able to generate a response for that query."

        except Exception as e:
            logger.exception("Pipeline error for session %s", session_id)
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
