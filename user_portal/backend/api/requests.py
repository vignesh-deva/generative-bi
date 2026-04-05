"""
Dashboard requests endpoints — business users submit requests for new
dashboards/reports. Requests move through an 8-state workflow managed
jointly by users (this portal) and the BI ops team (ops portal).

Workflow:
  draft -> requested -> in-progress -> completed -> accepted -> closed
  with branches: need additional details, request changes
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.mongo import dashboard_requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/requests", tags=["requests"])

USER_AUTHOR = "Business User"
AUTO_CLOSE_DAYS = 10

# ── State machine ─────────────────────────────────────────────────

Status = Literal[
    "draft", "requested", "in-progress", "need additional details",
    "completed", "accepted", "request changes", "closed",
]

# (from_status, actor) -> set of allowed next statuses
TRANSITIONS: dict[tuple[str, str], set[str]] = {
    ("draft", "user"): {"requested"},
    ("requested", "ops"): {"in-progress", "need additional details"},
    ("in-progress", "ops"): {"need additional details", "completed"},
    ("need additional details", "ops"): {"in-progress"},
    ("completed", "user"): {"accepted", "request changes"},
    ("request changes", "ops"): {"in-progress", "need additional details"},
    ("accepted", "user"): {"closed"},
    ("accepted", "system"): {"closed"},
    ("completed", "system"): {"closed"},
}

AUTO_CLOSE_STATUSES = {"accepted", "completed"}


def _allowed_next(current: str, actor: str) -> set[str]:
    return TRANSITIONS.get((current, actor), set())


# ── Serialization helpers ─────────────────────────────────────────

def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize(doc: dict) -> dict:
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
    """Close accepted/completed requests whose auto_close_eligible_at has passed."""
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


# ── Transition helper ─────────────────────────────────────────────

async def _transition(
    doc: dict,
    new_status: str,
    actor: str,
    note: str | None = None,
) -> dict:
    """Validate, apply, and persist a state transition. Returns updated doc."""
    current = doc["status"]
    allowed = _allowed_next(current, actor)
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Illegal transition: {current} -> {new_status} by {actor}",
        )

    now = datetime.now(timezone.utc)
    set_fields: dict = {"status": new_status, "updated_at": now}

    if new_status == "requested" and current == "draft":
        set_fields["submitted_at"] = now

    if new_status in AUTO_CLOSE_STATUSES:
        set_fields["auto_close_eligible_at"] = now + timedelta(days=AUTO_CLOSE_DAYS)
    else:
        # Moving out of accepted/completed clears the auto-close timer
        set_fields["auto_close_eligible_at"] = None

    if new_status == "closed":
        set_fields["closed_at"] = now

    status_change_comment = {
        "comment_id": str(uuid.uuid4()),
        "author": USER_AUTHOR if actor == "user" else ("System" if actor == "system" else "Ops Team"),
        "text": f"Status changed: {current} → {new_status}" + (f" — {note}" if note else ""),
        "type": "status_change",
        "created_at": now,
    }
    history_entry = {
        "from": current,
        "to": new_status,
        "actor": actor,
        "at": now,
        "note": note,
    }

    await dashboard_requests().update_one(
        {"request_id": doc["request_id"]},
        {
            "$set": set_fields,
            "$push": {
                "comments": status_change_comment,
                "status_history": history_entry,
            },
        },
    )
    updated = await dashboard_requests().find_one(
        {"request_id": doc["request_id"]}, {"_id": 0}
    )
    return _serialize(updated)


async def _load_or_404(request_id: str) -> dict:
    doc = await dashboard_requests().find_one({"request_id": request_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Request not found")
    return doc


# ── Pydantic schemas ──────────────────────────────────────────────

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str | None = None


class ChatContext(BaseModel):
    message_id: str
    question: str
    answer: str
    sql: str | None = None
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class CreateDraftBody(BaseModel):
    title: str
    description: str
    chat_context: ChatContext | None = None
    session_id: str | None = None


class UpdateDraftBody(BaseModel):
    title: str | None = None
    description: str | None = None


class CreateRequestBody(BaseModel):
    """One-shot create + submit (used by chat modal)."""
    title: str
    description: str
    chat_context: ChatContext | None = None
    session_id: str | None = None


class CommentBody(BaseModel):
    text: str


class NoteBody(BaseModel):
    note: str | None = None


class RequiredNoteBody(BaseModel):
    note: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/drafts")
async def create_draft(body: CreateDraftBody):
    if not body.title.strip() or not body.description.strip():
        raise HTTPException(status_code=400, detail="title and description are required")
    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    doc = {
        "request_id": request_id,
        "session_id": body.session_id,
        "title": body.title.strip(),
        "description": body.description.strip(),
        "chat_context": body.chat_context.model_dump() if body.chat_context else None,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "submitted_at": None,
        "closed_at": None,
        "auto_close_eligible_at": None,
        "comments": [],
        "status_history": [
            {"from": None, "to": "draft", "actor": "user", "at": now, "note": None}
        ],
    }
    await dashboard_requests().insert_one(doc)
    doc.pop("_id", None)
    return _serialize(doc)


@router.patch("/drafts/{request_id}")
async def update_draft(request_id: str, body: UpdateDraftBody):
    doc = await _load_or_404(request_id)
    if doc["status"] != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be edited")
    set_fields: dict = {"updated_at": datetime.now(timezone.utc)}
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=400, detail="title cannot be empty")
        set_fields["title"] = body.title.strip()
    if body.description is not None:
        if not body.description.strip():
            raise HTTPException(status_code=400, detail="description cannot be empty")
        set_fields["description"] = body.description.strip()
    await dashboard_requests().update_one(
        {"request_id": request_id}, {"$set": set_fields}
    )
    updated = await dashboard_requests().find_one({"request_id": request_id}, {"_id": 0})
    return _serialize(updated)


@router.delete("/drafts/{request_id}")
async def delete_draft(request_id: str):
    doc = await _load_or_404(request_id)
    if doc["status"] != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be deleted")
    await dashboard_requests().delete_one({"request_id": request_id})
    return {"deleted": True}


@router.post("/drafts/{request_id}/submit")
async def submit_draft(request_id: str):
    doc = await _load_or_404(request_id)
    return await _transition(doc, "requested", actor="user")


@router.post("")
async def create_request(body: CreateRequestBody):
    """One-shot: create the doc already in 'requested' state (used by chat modal)."""
    if not body.title.strip() or not body.description.strip():
        raise HTTPException(status_code=400, detail="title and description are required")
    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    doc = {
        "request_id": request_id,
        "session_id": body.session_id,
        "title": body.title.strip(),
        "description": body.description.strip(),
        "chat_context": body.chat_context.model_dump() if body.chat_context else None,
        "status": "requested",
        "created_at": now,
        "updated_at": now,
        "submitted_at": now,
        "closed_at": None,
        "auto_close_eligible_at": None,
        "comments": [],
        "status_history": [
            {"from": None, "to": "requested", "actor": "user", "at": now, "note": None}
        ],
    }
    await dashboard_requests().insert_one(doc)
    doc.pop("_id", None)
    return _serialize(doc)


@router.get("")
async def list_requests(
    status: str | None = None,
    limit: int = 50,
    skip: int = 0,
):
    await _auto_close_sweep()
    query: dict = {}
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
async def get_request(request_id: str):
    await _auto_close_sweep()
    doc = await dashboard_requests().find_one(
        {"request_id": request_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Request not found")
    return _serialize(doc)


@router.post("/{request_id}/comments")
async def add_comment(request_id: str, body: CommentBody):
    doc = await _load_or_404(request_id)
    if doc["status"] == "closed":
        raise HTTPException(status_code=409, detail="Cannot comment on a closed request")
    if doc["status"] == "draft":
        raise HTTPException(status_code=409, detail="Cannot comment on a draft")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="comment text is required")
    now = datetime.now(timezone.utc)
    comment = {
        "comment_id": str(uuid.uuid4()),
        "author": USER_AUTHOR,
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


@router.post("/{request_id}/accept")
async def accept_request(request_id: str, body: NoteBody):
    doc = await _load_or_404(request_id)
    return await _transition(doc, "accepted", actor="user", note=body.note)


@router.post("/{request_id}/request-changes")
async def request_changes(request_id: str, body: RequiredNoteBody):
    if not body.note.strip():
        raise HTTPException(status_code=400, detail="note is required")
    doc = await _load_or_404(request_id)
    return await _transition(doc, "request changes", actor="user", note=body.note.strip())


@router.post("/{request_id}/close")
async def close_request(request_id: str):
    doc = await _load_or_404(request_id)
    return await _transition(doc, "closed", actor="user")
