# `portal/backend/utils/`

> Shared utilities — SSE streaming helpers used across the API layer.

## Overview

Thin utility layer. Contains the SSE streaming helper that formats and flushes events to the frontend. Kept separate so the event format is defined in one place and all API routes use the same structure. The LangGraph pipeline yields events at each node, and the streaming helper wraps them as SSE.

## Files

| File | Purpose |
|------|---------|
| `streaming.py` | SSE event formatter and async generator helpers for `chat.py` |
| `__init__.py` | Package init |

## Planned Functionality

### `streaming.py`
```python
def make_event(event_type: str, data: dict) -> str:
    # Returns a formatted SSE string: "event: thinking\ndata: {...}\n\n"

async def stream_pipeline(question: str, session_id: str) -> AsyncGenerator[str, None]:
    # Runs the agent pipeline and yields SSE events at each stage
```

Event types emitted during a pipeline run:

| Event | When | Payload |
|-------|------|---------|
| `thinking` | Classifier / RAG running | `{ message: "Analysing your question..." }` |
| `sql` | SQL generated | `{ sql: "SELECT ..." }` |
| `result` | Query executed | `{ columns: [...], rows: [...], row_count: N }` |
| `insight` | Insight generated | `{ text: "..." }` |
| `error` | Any agent fails | `{ message: "...", stage: "sql_agent" }` |

## Design Choices

- **SSE over WebSockets**: The pipeline is one-directional — server streams progress to the client. SSE is simpler, requires no special server setup, and reconnects automatically in browsers.
- **Typed event kinds**: Each SSE event has an explicit `event:` field so the frontend can handle each stage differently (e.g. render SQL in a code block, results in a table, insight as prose).

## TODO

- [ ] `streaming.py` is currently an empty scaffold — implementation pending
- [ ] Event payload schema should be shared with the frontend TypeScript types
- [ ] Consider a `done` event type so the frontend knows the stream has ended cleanly

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Updated for LangGraph pipeline integration |
| 2026-03-11 | Initial README — scaffolded, implementation pending |
