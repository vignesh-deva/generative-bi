"""
Chat endpoint — accepts a natural language query and streams
the agent pipeline response as Server-Sent Events (SSE).

SSE event format:
  data: {"type": "token", "content": "..."}
  data: {"type": "sql", "content": "SELECT ..."}
  data: {"type": "error", "content": "..."}
  data: [DONE]
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.mongo import chat_sessions, chat_messages

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
        # TODO: Replace with real LangGraph pipeline invocation
        # For now, return a placeholder response so the UI is testable
        placeholder = (
            "The agent pipeline is not wired up yet. "
            "This is a placeholder response to confirm the chat UI and SSE streaming work end-to-end. "
            "Once the LangGraph pipeline is built, this endpoint will route your query through: "
            "Classifier -> Guardrails -> RAG -> Schema Agent -> SQL Agent -> Validation -> Execution -> Insight Agent."
        )

        for word in placeholder.split(" "):
            yield sse_event({"type": "token", "content": word + " "})

        await chat_messages().insert_one(
            {
                "session_id": session_id,
                "role": "assistant",
                "content": placeholder,
                "sql_query": None,
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
