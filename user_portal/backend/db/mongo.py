"""
MongoDB connection and collection definitions.

Stores chat sessions, messages, feedback, and dashboard requests.
Uses Motor (async MongoDB driver) for non-blocking I/O with FastAPI.
"""

import logging
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import UpdateOne

from config.settings import MONGODB_URI, MONGODB_DB_NAME

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[MONGODB_DB_NAME]
    return _db


async def close_client():
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


# ---- Collection accessors ----

def chat_sessions():
    """
    Collection: chat_sessions

    Document schema:
    {
        "_id": ObjectId,
        "session_id": str (UUID),
        "title": str | None,
        "created_at": datetime,
        "updated_at": datetime
    }
    """
    return get_db()["chat_sessions"]


def chat_messages():
    """
    Collection: chat_messages

    Document schema:
    {
        "_id": ObjectId,
        "message_id": str (UUID — stable id exposed to clients),
        "session_id": str (UUID — references chat_sessions.session_id),
        "role": "user" | "assistant",
        "content": str,
        "sql_query": str | None,
        "feedback": "up" | "down" | None,
        "feedback_comment": str | None,
        "feedback_at": datetime | None,
        "promoted_at": datetime | None,       # set when ops curates into RAG
        "promoted_example_id": int | None,    # fewshot_examples.example_id
        "created_at": datetime
    }
    """
    return get_db()["chat_messages"]


def dashboard_requests():
    """
    Collection: dashboard_requests (schema v2)

    Document schema:
    {
        "_id": ObjectId,
        "request_id": str (UUID),
        "session_id": str | None,           # set when created from chat
        "title": str,
        "description": str,
        "chat_context": None | {
            "message_id": str,
            "question": str,
            "answer": str,
            "sql": str | None,
            "history": [ { "role", "content", "created_at" } ]
        },
        "status": "draft" | "requested" | "in-progress" | "need additional details"
                | "completed" | "accepted" | "request changes" | "closed",
        "created_at": datetime,
        "updated_at": datetime,
        "submitted_at": datetime | None,
        "closed_at": datetime | None,
        "auto_close_eligible_at": datetime | None,  # now + 10d on entry to accepted/completed
        "comments": [
            {
                "comment_id": str,
                "author": str,
                "text": str,
                "type": "comment" | "status_change",
                "created_at": datetime
            }
        ],
        "status_history": [
            { "from": str|None, "to": str, "actor": "user"|"ops"|"system",
              "at": datetime, "note": str|None }
        ]
    }
    """
    return get_db()["dashboard_requests"]


async def create_indexes():
    """Create indexes on startup. Idempotent — safe to call multiple times."""
    await chat_sessions().create_index("session_id", unique=True)
    await chat_messages().create_index("session_id")
    await chat_messages().create_index("created_at")
    await chat_messages().create_index("message_id", unique=True, sparse=True)
    await chat_messages().create_index(
        [("feedback", 1), ("created_at", -1)], sparse=True
    )
    await dashboard_requests().create_index("request_id", unique=True)
    await dashboard_requests().create_index("status")
    await dashboard_requests().create_index("created_at")
    await dashboard_requests().create_index("updated_at")
    await dashboard_requests().create_index("session_id", sparse=True)
    await dashboard_requests().create_index("auto_close_eligible_at", sparse=True)


async def migrate_dashboard_requests():
    """
    One-shot schema migration for dashboard_requests.

    Drops the legacy collection (4-status model) and recreates it with v2 indexes.
    Gated by a _meta document so it runs exactly once.
    """
    meta = get_db()["_meta"]
    current = await meta.find_one({"key": "dashboard_requests_schema"})
    if current and current.get("version") == "v2":
        return
    drop_count = await dashboard_requests().count_documents({})
    await dashboard_requests().drop()
    logger.info("dropped legacy dashboard_requests collection (%d documents)", drop_count)
    await create_indexes()
    await meta.update_one(
        {"key": "dashboard_requests_schema"},
        {"$set": {
            "version": "v2",
            "migrated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    logger.info("dashboard_requests migrated to v2")


async def backfill_message_ids():
    """Assign a stable message_id to legacy chat_messages that predate the field."""
    col = chat_messages()
    cursor = col.find({"message_id": {"$exists": False}}, {"_id": 1})
    ops = []
    async for doc in cursor:
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"message_id": str(uuid.uuid4())}}))
    if ops:
        result = await col.bulk_write(ops, ordered=False)
        logger.info("backfilled message_id for %d legacy messages", result.modified_count)
