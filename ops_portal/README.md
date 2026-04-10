# ops_portal/

Operations Center application for the BI/dev team.

## Structure

| Folder | Stack | Port | Purpose |
|--------|-------|------|---------|
| `frontend/` | Next.js + Tailwind | 3001 | Ticket management, feedback review, RAG curation UI |
| `backend/` | FastAPI | 8001 | Ops APIs for tickets, feedback, and vector store management |

## Pages

| Page | Route | Description |
|------|-------|-------------|
| **Tickets** | `/` | View and manage dashboard requests from business users — 8-status tabs, chat context preview, transition buttons |
| **Feedback** | `/feedback` | Review thumbs-up/down feedback on chat responses |
| **RAG Curation** | `/rag` | Manage few-shot NL-to-SQL examples — add, review, curate for accuracy |

The login page at `/login` is the unauthenticated entry point. All other routes redirect there if no valid JWT cookie is present.

## Purpose

Creates a human-in-the-loop feedback loop that continuously improves NL → SQL accuracy. When users give positive feedback, the dev team can review the generated SQL and promote it to the vector store. For negative feedback, they can correct the SQL before saving.

## Databases

The ops backend connects to:
- **PostgreSQL** — reads FMCG data for SQL validation, writes curated few-shot examples to pgvector
- **MongoDB** — reads chat sessions, messages, feedback, and dashboard requests for review
