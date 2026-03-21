"""
MongoDB connection for the ops backend.
Accesses the same collections as the portal backend.
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


def chat_messages():
    return get_db()["chat_messages"]


def dashboard_requests():
    return get_db()["dashboard_requests"]


async def create_indexes():
    await dashboard_requests().create_index("request_id", unique=True)
    await dashboard_requests().create_index("status")
    await dashboard_requests().create_index("created_at")
