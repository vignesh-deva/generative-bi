"""
Feedback endpoint — user submits thumbs up/down (with optional comment)
on a specific assistant message.

The comment is particularly useful for thumbs-down feedback so ops can
understand what went wrong when curating RAG examples later.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.mongo import chat_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackUpdate(BaseModel):
    feedback: Literal["up", "down"] | None = None
    comment: str | None = Field(default=None, max_length=2000)


@router.patch("/{message_id}")
async def submit_feedback(message_id: str, body: FeedbackUpdate):
    msg = await chat_messages().find_one({"message_id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.get("role") != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Feedback can only be attached to assistant messages",
        )

    comment = (body.comment or "").strip() or None
    now = datetime.now(timezone.utc)

    await chat_messages().update_one(
        {"message_id": message_id},
        {
            "$set": {
                "feedback": body.feedback,
                "feedback_comment": comment,
                "feedback_at": now if body.feedback is not None else None,
            }
        },
    )

    logger.info(
        "feedback message_id=%s vote=%s comment_chars=%d",
        message_id,
        body.feedback,
        len(comment or ""),
    )

    return {
        "message_id": message_id,
        "feedback": body.feedback,
        "feedback_comment": comment,
        "feedback_at": now.isoformat() if body.feedback is not None else None,
    }
