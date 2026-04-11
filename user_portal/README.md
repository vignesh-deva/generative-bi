# user_portal/

User-facing application for the Generative BI Agent.

## Structure

| Folder | Stack | Port | Purpose |
|--------|-------|------|---------|
| `frontend/` | Next.js + Tailwind | 3000 | Dashboard, chat interface, request submissions |
| `backend/` | FastAPI | 8000 | LangGraph agent pipeline, chat API, request API |

## Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/` | 3×3 grid — 3 KPI cards + 6 recharts charts |
| **Chat** | `/chat` | NL-to-SQL chat with SSE streaming, SQL viewer, pipeline steps panel |
| **Recent** | `/recent` | Past chat sessions with relative timestamps, click to resume |
| **Requests** | `/requests` | Dashboard request lifecycle — Drafts / Active / Closed tabs, comment threads |

The login page at `/login` is the unauthenticated entry point. All other routes redirect there if no valid JWT cookie (`auth_token`) is present. This session is independent of the Operations Center — logging into one portal does not authenticate the other.

## Databases

The portal backend connects to:
- **PostgreSQL** — FMCG business data queries + pgvector for RAG few-shot retrieval
- **MongoDB** — chat sessions, messages, feedback, dashboard requests
