# ops_portal/

Operations Center application for the BI/dev team.

## Structure

| Folder | Stack | Port | Purpose |
|--------|-------|------|---------|
| `frontend/` | Next.js + Tailwind | 3001 | Ticket management, feedback review, RAG curation UI |
| `backend/` | FastAPI | 8001 | Ops APIs for tickets, feedback, and vector store management |

## Pages

| Page | Description |
|------|-------------|
| **Tickets** | View and manage dashboard development requests from business users |
| **Feedback** | Review thumbs-up/down feedback on chat responses |
| **RAG Curation** | Review agent-generated SQL — save good queries or fix bad ones, then persist to pgvector as few-shot examples |

## Purpose

Creates a human-in-the-loop feedback loop that continuously improves NL → SQL accuracy. When users give positive feedback, the dev team can review the generated SQL and promote it to the vector store. For negative feedback, they can correct the SQL before saving.

## Databases

The ops backend connects to:
- **PostgreSQL** — reads FMCG data for SQL validation, writes curated few-shot examples to pgvector
- **MongoDB** — reads chat sessions, messages, and feedback for review
