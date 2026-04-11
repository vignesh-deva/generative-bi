"""
Chat history endpoints — list sessions and retrieve messages for a session.
"""

from fastapi import APIRouter, HTTPException

from db.mongo import chat_sessions, chat_messages

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions")
async def list_sessions(limit: int = 50, skip: int = 0):
    cursor = (
        chat_sessions()
        .find({}, {"_id": 0})
        .sort("updated_at", -1)
        .skip(skip)
        .limit(limit)
    )
    sessions = await cursor.to_list(length=limit)
    for s in sessions:
        s["created_at"] = s["created_at"].isoformat()
        s["updated_at"] = s["updated_at"].isoformat()
    return sessions


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    session = await chat_sessions().find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cursor = (
        chat_messages()
        .find({"session_id": session_id}, {"_id": 0})
        .sort("created_at", 1)
    )
    messages = await cursor.to_list(length=500)
    for m in messages:
        m["created_at"] = m["created_at"].isoformat()
        # Older rows predate these fields; normalize so clients don't have to guard.
        m.setdefault("message_id", None)
        m.setdefault("feedback", None)
        m.setdefault("feedback_comment", None)
        m.setdefault("chart_context", None)
        if m.get("feedback_at") is not None:
            m["feedback_at"] = m["feedback_at"].isoformat()
        else:
            m["feedback_at"] = None
    return messages
