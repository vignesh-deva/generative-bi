"""
MongoDB connection and collection definitions.

Stores chat sessions, messages, feedback, and dashboard requests.
Uses Motor (async MongoDB driver) for non-blocking I/O with FastAPI.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config.settings import MONGODB_URI, MONGODB_DB_NAME

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
        "session_id": str (UUID — references chat_sessions.session_id),
        "role": "user" | "assistant",
        "content": str,
        "sql_query": str | None,
        "feedback": "up" | "down" | None,
        "created_at": datetime
    }
    """
    return get_db()["chat_messages"]


def dashboard_requests():
    """
    Collection: dashboard_requests

    Document schema:
    {
        "_id": ObjectId,
        "title": str,
        "description": str | None,
        "status": "Pending" | "In Progress" | "Done" | "Rejected",
        "comments": [
            {
                "author": str,
                "text": str,
                "created_at": datetime
            }
        ],
        "created_at": datetime,
        "updated_at": datetime
    }
    """
    return get_db()["dashboard_requests"]


async def create_indexes():
    """Create indexes on startup. Idempotent — safe to call multiple times."""
    await chat_sessions().create_index("session_id", unique=True)
    await chat_messages().create_index("session_id")
    await chat_messages().create_index("created_at")
    await dashboard_requests().create_index("status")
    await dashboard_requests().create_index("created_at")
