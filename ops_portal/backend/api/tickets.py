"""
Tickets endpoints — BI ops team views and manages dashboard requests
submitted from the user portal. Enforces the shared state machine for
ops-controlled transitions (in-progress, need additional details, completed).

Reads from and writes to the same `dashboard_requests` collection as the
user portal.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.mongo import dashboard_requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

OPS_AUTHOR = "Ops Team"
AUTO_CLOSE_DAYS = 10  # also defined in user_portal/backend/api/requests.py — keep in sync

# (from_status, "ops") -> allowed next statuses
OPS_TRANSITIONS: dict[str, set[str]] = {
    "requested": {"in-progress", "need additional details"},
    "in-progress": {"need additional details", "completed"},
    "need additional details": {"in-progress"},
    "request changes": {"in-progress", "need additional details"},
}

AUTO_CLOSE_STATUSES = {"accepted", "completed"}


# ── Serialization ─────────────────────────────────────────────────

def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    for key in (
        "created_at", "updated_at", "submitted_at",
        "closed_at", "auto_close_eligible_at",
    ):
        if key in doc and doc[key] is not None:
            doc[key] = _iso(doc[key])
    for c in doc.get("comments", []):
        if "created_at" in c:
            c["created_at"] = _iso(c["created_at"])
    for h in doc.get("status_history", []):
        if "at" in h:
            h["at"] = _iso(h["at"])
    ctx = doc.get("chat_context")
    if ctx and "history" in ctx:
        for m in ctx["history"]:
            if "created_at" in m:
                m["created_at"] = _iso(m["created_at"])
    return doc


# ── Auto-close sweep (lazy) ───────────────────────────────────────

async def _auto_close_sweep() -> int:
    now = datetime.now(timezone.utc)
    system_comment = {
        "comment_id": str(uuid.uuid4()),
        "author": "System",
        "text": f"Auto-closed after {AUTO_CLOSE_DAYS} days of inactivity.",
        "type": "status_change",
        "created_at": now,
    }
    result = await dashboard_requests().update_many(
        {
            "status": {"$in": list(AUTO_CLOSE_STATUSES)},
            "auto_close_eligible_at": {"$lte": now},
        },
        [
            {"$set": {
                "status_history": {"$concatArrays": [
                    {"$ifNull": ["$status_history", []]},
                    [{
                        "from": "$status",
                        "to": "closed",
                        "actor": "system",
                        "at": now,
                        "note": f"auto-close {AUTO_CLOSE_DAYS}d",
                    }],
                ]},
                "comments": {"$concatArrays": [
                    {"$ifNull": ["$comments", []]},
                    [system_comment],
                ]},
                "status": "closed",
                "closed_at": now,
                "updated_at": now,
                "auto_close_eligible_at": None,
            }}
        ],
    )
    if result.modified_count:
        logger.info("auto_close sweep: closed=%d", result.modified_count)
    return result.modified_count


async def _load_or_404(request_id: str) -> dict:
    doc = await dashboard_requests().find_one({"request_id": request_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return doc


# ── Pydantic schemas ──────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str
    comment: str | None = None


class CommentBody(BaseModel):
    text: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("")
async def list_tickets(
    status: str | None = None,
    limit: int = 50,
    skip: int = 0,
):
    await _auto_close_sweep()
    # Ops never sees drafts.
    query: dict = {"status": {"$ne": "draft"}}
    if status:
        query["status"] = status
    cursor = (
        dashboard_requests()
        .find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = await cursor.to_list(length=limit)
    return [_serialize(item) for item in items]


@router.get("/{request_id}")
async def get_ticket(request_id: str):
    await _auto_close_sweep()
    doc = await dashboard_requests().find_one(
        {"request_id": request_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if doc.get("status") == "draft":
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize(doc)


@router.patch("/{request_id}/status")
async def update_status(request_id: str, body: StatusUpdate):
    doc = await _load_or_404(request_id)
    current = doc["status"]
    new_status = body.status

    if current == "draft":
        raise HTTPException(status_code=404, detail="Ticket not found")

    allowed = OPS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Illegal transition: {current} -> {new_status} by ops",
        )

    now = datetime.now(timezone.utc)
    set_fields: dict = {"status": new_status, "updated_at": now}

    if new_status in AUTO_CLOSE_STATUSES:
        set_fields["auto_close_eligible_at"] = now + timedelta(days=AUTO_CLOSE_DAYS)
    else:
        set_fields["auto_close_eligible_at"] = None

    status_change_comment = {
        "comment_id": str(uuid.uuid4()),
        "author": OPS_AUTHOR,
        "text": f"Status changed: {current} → {new_status}"
                + (f" — {body.comment.strip()}" if body.comment and body.comment.strip() else ""),
        "type": "status_change",
        "created_at": now,
    }
    history_entry = {
        "from": current,
        "to": new_status,
        "actor": "ops",
        "at": now,
        "note": body.comment.strip() if body.comment and body.comment.strip() else None,
    }

    await dashboard_requests().update_one(
        {"request_id": request_id},
        {
            "$set": set_fields,
            "$push": {
                "comments": status_change_comment,
                "status_history": history_entry,
            },
        },
    )
    updated = await dashboard_requests().find_one({"request_id": request_id}, {"_id": 0})
    return _serialize(updated)


@router.post("/{request_id}/comments")
async def add_comment(request_id: str, body: CommentBody):
    doc = await _load_or_404(request_id)
    if doc["status"] in ("draft", "closed"):
        raise HTTPException(status_code=409, detail=f"Cannot comment on a {doc['status']} ticket")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="comment text is required")
    now = datetime.now(timezone.utc)
    comment = {
        "comment_id": str(uuid.uuid4()),
        "author": OPS_AUTHOR,
        "text": body.text.strip(),
        "type": "comment",
        "created_at": now,
    }
    await dashboard_requests().update_one(
        {"request_id": request_id},
        {"$set": {"updated_at": now}, "$push": {"comments": comment}},
    )
    updated = await dashboard_requests().find_one({"request_id": request_id}, {"_id": 0})
    return _serialize(updated)
