# `backend/api/`

> FastAPI route handlers — HTTP endpoints for chat, conversation history, and BI insight requests.

## Overview

This folder contains all FastAPI routers. It is the entry point for all HTTP traffic from the Next.js frontend. The main chat endpoint orchestrates the agent pipeline and streams results back via Server-Sent Events (SSE). The other routers handle session history retrieval and BI request submission.

## Files

| File | Purpose |
|------|---------|
| `chat.py` | Main chat endpoint — receives a question, runs the agent pipeline, streams SSE response |
| `history.py` | Returns past chat sessions and messages for the sidebar history view |
| `requests.py` | Handles BI insight requests (business users escalating to the BI team) |
| `__init__.py` | Package init |

## Planned Endpoints

### `chat.py`
```
POST /api/chat
  Body: { session_id, message }
  Response: text/event-stream (SSE)
  Events: { type: "thinking" | "sql" | "result" | "insight" | "error", data: ... }
```

### `history.py`
```
GET  /api/history/sessions          — list all chat sessions
GET  /api/history/sessions/{id}     — messages for a session
```

### `requests.py`
```
POST /api/requests                  — create a new BI insight request
GET  /api/requests                  — list all requests
```

## Design Choices

- **SSE over WebSockets**: The pipeline is unidirectional (server pushes, client listens). SSE is simpler — no handshake, works over standard HTTP, easy to reconnect.
- **Chat history is separate from Requests**: These are different workflows. History = past chat sessions. Requests = formal escalations to the BI team. Separate routers, separate DB tables.
- **Session-based chat**: Each conversation has a `session_id`. Messages are persisted to `chat_sessions` / `chat_messages` tables via `get_connection()` (read-write).

## TODO

- [ ] All route files are currently empty scaffolds — implementation pending
- [ ] SSE event schema needs to be finalised and documented
- [ ] Auth/session management not yet defined — who can see whose history?
- [ ] `requests.py` workflow (who receives the request, what happens next) needs to be designed
- [ ] Error events should include enough context for the frontend to show a useful message

## Changelog

| Date | Change |
|------|--------|
| 2026-03-11 | Initial README — scaffolded, implementation pending |
