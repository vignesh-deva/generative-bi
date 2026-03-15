# portal/

User-facing application for the Generative BI Agent.

## Structure

| Folder | Stack | Port | Purpose |
|--------|-------|------|---------|
| `frontend/` | Next.js + Tailwind | 3000 | Dashboard, chat interface, request submissions |
| `backend/` | FastAPI | 8000 | LangGraph agent pipeline, chat API, request API |

## Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/dashboard` | Static 2x2 chart grid with hardcoded FMCG data |
| **Request New** | `/requests/new` | Submit a request for a new dashboard/report |
| **+ New Chat** | `/chat` | NL → SQL chat with streaming agent responses |
| **Recent** | `/chat/history` | Past chat sessions (click to view) |

## Databases

The portal backend connects to:
- **PostgreSQL** — FMCG business data queries + pgvector for RAG few-shot retrieval
- **MongoDB** — chat sessions, messages, feedback, dashboard requests
