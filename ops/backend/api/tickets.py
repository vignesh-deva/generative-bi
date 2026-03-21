"""
Tickets endpoints — ops team views and manages dashboard requests from users.
Reads from the same dashboard_requests collection the portal writes to.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.mongo import dashboard_requests

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class StatusUpdate(BaseModel):
    status: str
    comment: str | None = None


@router.get("")
async def list_tickets(limit: int = 50, skip: int = 0):
    cursor = (
        dashboard_requests()
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    for item in items:
        item["created_at"] = item["created_at"].isoformat()
        item["updated_at"] = item["updated_at"].isoformat()
        for c in item.get("comments", []):
            c["created_at"] = c["created_at"].isoformat()
    return items


@router.patch("/{title}/status")
async def update_status(title: str, body: StatusUpdate):
    doc = await dashboard_requests().find_one({"title": title})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update: dict = {
        "$set": {
            "status": body.status,
            "updated_at": datetime.now(timezone.utc),
        }
    }

    if body.comment:
        update["$push"] = {
            "comments": {
                "author": "Ops Team",
                "text": body.comment,
                "created_at": datetime.now(timezone.utc),
            }
        }

    await dashboard_requests().update_one({"title": title}, update)
    return {"status": body.status}
