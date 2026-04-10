# ops_portal/frontend/

Next.js + Tailwind — Operations Center portal for the BI/dev team.

## Pages

| Page | Route | Description |
|------|-------|-------------|
| **Tickets** | `/` | View and manage dashboard requests submitted by business users — 8-status tabs, chat context preview, transition buttons |
| **Feedback** | `/feedback` | Review thumbs-up/down feedback on chat responses |
| **RAG Curation** | `/rag` | Review agent-generated SQL queries — save good ones or fix bad ones, then persist to pgvector as few-shot examples |

Unauthenticated visits to any route are redirected to `/login` by `src/middleware.ts`. The login form posts credentials to the backend and stores the returned JWT as a cookie.

## Purpose

Creates a human-in-the-loop feedback loop that continuously improves NL → SQL accuracy. When users give positive feedback, the dev team can review the generated SQL and promote it to the RAG store. For negative feedback, they can correct the SQL before saving.

## Stack

- Next.js (App Router)
- Tailwind CSS
- Runs on port 3001

## Getting Started

```bash
npm install
npm run dev   # starts on http://localhost:3001
```

Set `NEXT_PUBLIC_API_URL` in the environment (or it defaults to `http://localhost:8001`).
