# `backend/api/`

> FastAPI route handlers — HTTP endpoints for chat, conversation history, and dashboard requests.

## Overview

This folder contains all FastAPI routers for the user-facing backend. The main chat endpoint invokes the LangGraph agent pipeline and streams results back via Server-Sent Events (SSE). Other routers handle chat history (stored in MongoDB) and dashboard request submission.

## Files

| File | Purpose |
|------|---------|
| `chat.py` | Main chat endpoint — receives a question, runs the LangGraph pipeline, streams SSE response |
| `history.py` | Returns past chat sessions and messages from MongoDB |
| `requests.py` | Handles dashboard requests (business users requesting new dashboards/reports) |
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
POST /api/requests                  — create a new dashboard request
GET  /api/requests                  — list all requests
GET  /api/requests/{id}             — request detail with comments
PUT  /api/requests/{id}/comments    — add/edit comments on a request
```

## Design Choices

- **SSE over WebSockets**: The pipeline is unidirectional (server pushes, client listens). SSE is simpler — no handshake, works over standard HTTP, easy to reconnect.
- **Chat history in MongoDB**: Messages are document-shaped (variable metadata, nested tool calls, streaming chunks) — not naturally relational. MongoDB gives flexible schema and easy querying by session/user/timestamp.
- **FMCG data stays in SQLite**: The SQL Agent executes generated queries against SQLite. Chat history and session data go to MongoDB. Clean separation.
- **Session-based chat**: Each conversation has a `session_id`. Messages are persisted to MongoDB collections.
- **Requests ≠ Chat History**: Different workflows. History = past chat sessions. Requests = formal submissions for new dashboards, tracked as tickets with comments.

## TODO

- [ ] All route files are currently empty scaffolds — implementation pending
- [ ] SSE event schema needs to be finalised and documented
- [ ] Auth/session management not yet defined — who can see whose history?
- [ ] Request detail view needs comment thread support (view + edit)
- [ ] Error events should include enough context for the frontend to show a useful message

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Updated for MongoDB chat history, LangGraph pipeline, request comments |
| 2026-03-11 | Initial README — scaffolded, implementation pending |
