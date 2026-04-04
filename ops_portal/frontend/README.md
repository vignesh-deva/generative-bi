# ops_portal/frontend/

Next.js + Tailwind — Operations Center portal for the BI/dev team.

## Pages

| Page | Description |
|------|-------------|
| **Tickets** | View and manage dashboard development requests submitted by business users |
| **Feedback** | Review thumbs-up/down feedback on chat responses |
| **RAG Curation** | Review agent-generated SQL queries — save good ones or fix bad ones, then persist to the pgvector store as few-shot examples |

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
