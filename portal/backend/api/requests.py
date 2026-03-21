"""
Dashboard requests endpoints — business users can submit requests
for new dashboards/reports. The ops team manages them from the ops portal.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.mongo import dashboard_requests

router = APIRouter(prefix="/api/requests", tags=["requests"])


class CreateRequest(BaseModel):
    title: str
    description: str | None = None


@router.post("")
async def create_request(req: CreateRequest):
    request_id = str(uuid.uuid4())
    doc = {
        "request_id": request_id,
        "title": req.title,
        "description": req.description,
        "status": "Pending",
        "comments": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await dashboard_requests().insert_one(doc)
    return {"id": request_id, "status": "Pending"}


@router.get("")
async def list_requests(limit: int = 50, skip: int = 0):
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


@router.get("/{request_id}")
async def get_request(request_id: str):
    doc = await dashboard_requests().find_one(
        {"request_id": request_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Request not found")
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    for c in doc.get("comments", []):
        c["created_at"] = c["created_at"].isoformat()
    return doc
