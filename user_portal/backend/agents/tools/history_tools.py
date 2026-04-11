"""
History tools — fetch chat history from MongoDB for context injection.

Tools:
  fetch_chat_history(session_id, limit)  — retrieve recent messages from a session
"""

from db.mongo import chat_messages


async def fetch_chat_history(session_id: str, limit: int = 10) -> list[dict]:
    """Fetch the most recent messages from a chat session.

    Returns list of {"role": "user"|"assistant", "content": "..."} dicts,
    ordered chronologically (oldest first).
    """
    if not session_id:
        return []

    cursor = (
        chat_messages()
        .find(
            {"session_id": session_id},
            {"_id": 0, "role": 1, "content": 1, "sql_query": 1, "chart_context": 1},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    messages = await cursor.to_list(length=limit)
    messages.reverse()  # chronological order
    return messages
