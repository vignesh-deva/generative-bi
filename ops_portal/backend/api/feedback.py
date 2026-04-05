"""
Feedback endpoint — ops team reviews user feedback on AI responses.
Reads from the chat_messages collection (messages with non-null feedback).
"""

from fastapi import APIRouter

from db.mongo import chat_messages

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.get("")
async def list_feedback(limit: int = 100, skip: int = 0):
    cursor = (
        chat_messages()
        .find({"feedback": {"$ne": None}}, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    for item in items:
        item["created_at"] = item["created_at"].isoformat()
    return items
