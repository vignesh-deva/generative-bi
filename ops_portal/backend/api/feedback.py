"""
Feedback review endpoint — ops team reviews user feedback (thumbs up/down +
comments) on AI responses and promotes good NL→SQL pairs into the RAG
fewshot_examples table.

Dedup:
  For every feedback row we compute an embedding of the user's NL question
  and run a nearest-neighbor lookup against fewshot_examples. When
  hide_duplicates=true (default), rows whose top match has similarity
  >= RAG_DEDUP_THRESHOLD are omitted from the list.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config.settings import RAG_DEDUP_THRESHOLD
from db.database import get_pool
from db.mongo import chat_messages
from tools.embedding import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


async def _lookup_user_question(session_id: str, before: datetime) -> str | None:
    """Return the content of the most recent user message in `session_id`
    that precedes `before`. That's the NL question the assistant reply was
    answering."""
    doc = await chat_messages().find_one(
        {
            "session_id": session_id,
            "role": "user",
            "created_at": {"$lt": before},
        },
        sort=[("created_at", -1)],
    )
    return doc.get("content") if doc else None


async def _top_similarity(
    question: str,
) -> tuple[float, str | None, int | None]:
    """Embed the question and return (similarity, matched_question, example_id)
    for the single nearest fewshot example. Returns (0.0, None, None) if the
    RAG store is empty or embedding generation fails."""
    try:
        embedding = await get_embedding(question)
    except Exception:
        logger.warning("embedding failed for question=%.80s", question)
        return 0.0, None, None

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT example_id, question, 1 - (embedding <=> $1) AS sim "
            "FROM fewshot_examples "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> $1 "
            "LIMIT 1",
            embedding,
        )
    if row is None:
        return 0.0, None, None
    return float(row["sim"]), row["question"], int(row["example_id"])


@router.get("")
async def list_feedback(
    vote: Literal["all", "up", "down"] = "all",
    hide_duplicates: bool = True,
    include_promoted: bool = False,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """List user feedback for ops review.

    Fields returned per row are derived from the *assistant* message that
    carries the feedback, plus a lookup of the preceding user message for
    the actual NL question.
    """
    mongo_filter: dict = {"role": "assistant"}
    if vote == "up":
        mongo_filter["feedback"] = "up"
    elif vote == "down":
        mongo_filter["feedback"] = "down"
    else:
        mongo_filter["feedback"] = {"$ne": None}
    if not include_promoted:
        # $in [null] matches both explicitly-null and missing fields in Mongo.
        mongo_filter["promoted_at"] = {"$in": [None]}

    cursor = (
        chat_messages()
        .find(mongo_filter, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    raw = await cursor.to_list(length=limit)

    results: list[dict] = []
    for m in raw:
        message_id = m.get("message_id")
        if not message_id:
            # Legacy rows without a stable id can't be promoted — skip.
            continue

        question = await _lookup_user_question(
            m["session_id"], m["created_at"]
        )
        if not question:
            continue

        sim, match_q, _ = await _top_similarity(question)
        if hide_duplicates and sim >= RAG_DEDUP_THRESHOLD:
            continue

        promoted_at = m.get("promoted_at")
        results.append(
            {
                "message_id": message_id,
                "session_id": m["session_id"],
                "question": question,
                "sql_query": m.get("sql_query"),
                "answer": m.get("content"),
                "feedback": m.get("feedback"),
                "feedback_comment": m.get("feedback_comment"),
                "created_at": m["created_at"].isoformat(),
                "top_similarity": round(sim, 4),
                "top_match_question": match_q,
                "promoted_at": promoted_at.isoformat() if promoted_at else None,
                "promoted_example_id": m.get("promoted_example_id"),
            }
        )

    return results


class PromoteBody(BaseModel):
    question: str
    sql: str


@router.post("/{message_id}/promote")
async def promote_feedback(
    message_id: str,
    body: PromoteBody,
    force: bool = False,
):
    """Promote a reviewed feedback item into the RAG fewshot_examples store.

    Workflow:
      1. Fetch the feedback message.
      2. Embed the (possibly ops-edited) question.
      3. Check similarity vs existing fewshots. If >= RAG_DEDUP_THRESHOLD and
         not force=true, return 409 with the conflicting match.
      4. Insert (question, sql, embedding) with source='curated'.
      5. Mark the chat_messages doc with promoted_at + promoted_example_id.
    """
    msg = await chat_messages().find_one({"message_id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Feedback message not found")
    if msg.get("promoted_at"):
        raise HTTPException(status_code=409, detail="Already promoted")

    question = body.question.strip()
    sql = body.sql.strip()
    if not question or not sql:
        raise HTTPException(
            status_code=400, detail="question and sql must be non-empty"
        )

    try:
        embedding = await get_embedding(question)
    except Exception as e:
        logger.exception("promote: embedding failed")
        raise HTTPException(
            status_code=503, detail=f"Embedding service unavailable: {e}"
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        match = await conn.fetchrow(
            "SELECT example_id, question, 1 - (embedding <=> $1) AS sim "
            "FROM fewshot_examples "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> $1 "
            "LIMIT 1",
            embedding,
        )
        if match is not None and float(match["sim"]) >= RAG_DEDUP_THRESHOLD and not force:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate",
                    "similarity": round(float(match["sim"]), 4),
                    "top_match": {
                        "example_id": int(match["example_id"]),
                        "question": match["question"],
                    },
                    "threshold": RAG_DEDUP_THRESHOLD,
                },
            )

        row = await conn.fetchrow(
            "INSERT INTO fewshot_examples (question, sql_query, embedding, source) "
            "VALUES ($1, $2, $3, 'curated') RETURNING example_id",
            question,
            sql,
            embedding,
        )
    example_id = int(row["example_id"])

    now = datetime.now(timezone.utc)
    await chat_messages().update_one(
        {"message_id": message_id},
        {"$set": {"promoted_at": now, "promoted_example_id": example_id}},
    )

    logger.info(
        "promoted feedback message_id=%s -> example_id=%d force=%s",
        message_id, example_id, force,
    )
    return {
        "example_id": example_id,
        "message_id": message_id,
        "promoted_at": now.isoformat(),
    }
