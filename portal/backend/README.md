# `portal/backend/`

> FastAPI service — agent pipeline, chat API, and dashboard request handling for the user-facing portal.

## Overview

This is the main backend service. It exposes REST + SSE endpoints consumed by the Next.js frontend and orchestrates the NL → SQL → Insight agent pipeline using **LangGraph**.

Runs as a Docker container (port 8000) or standalone via `uvicorn`.

## Structure

```
portal/backend/
├── main.py              # FastAPI app entry point, lifespan (pool init + index creation)
├── agents/              # Individual agent modules (classifier, guardrails, RAG, SQL, etc.)
├── graph/               # LangGraph workflow definition (pipeline.py)
├── api/                 # FastAPI route handlers (chat, history, requests)
├── db/                  # PostgreSQL + MongoDB connection management, seeder, verifier
├── rag/                 # pgvector store and few-shot document corpus
├── utils/               # SSE streaming helpers
├── config/              # Environment-driven settings
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

Each subfolder has its own README with detailed documentation.

## Key Responsibilities

- **Chat endpoint** — receives NL questions, runs the LangGraph agent pipeline, streams SSE events back to the frontend
- **Agent pipeline** — Classifier, Guardrails, and RAG run in parallel (fan-out), then Schema Agent → SQL Agent ↔ Validation Agent → PostgreSQL execution → Insight Agent
- **Chat history** — persisted in MongoDB (sessions, messages, feedback)
- **FMCG data** — queried via PostgreSQL (read-only transactions for LLM-generated SQL)
- **Dashboard requests** — business users submit requests for new dashboards/reports, tracked with comments

## Databases

| Store | Engine | What It Stores |
|-------|--------|----------------|
| FMCG data | PostgreSQL | Products, orders, sales, inventory — the NL → SQL query target |
| Chat history | MongoDB | Sessions, messages, user feedback (thumbs up/down) |
| RAG examples | pgvector | NL → SQL few-shot pairs, curated via Operations Center |

## Running

### Docker (recommended)
```bash
# From project root
docker compose up portal-backend
```

### Manual
```bash
cd portal/backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Fill in LLM endpoint, POSTGRES_URI, and MONGODB_URI in .env
uvicorn main:app --reload --port 8000
```

### Seed the database
```bash
cd portal/backend
python -m db.seed    # populate mock FMCG data
python -m db.verify  # verify 33 checks pass
```

## TODO

- [ ] Agent files are currently empty scaffolds — LangGraph pipeline implementation pending
- [ ] `graph/pipeline.py` needs to be created
- [ ] SSE event schema needs to be finalised and shared with frontend TypeScript types
- [ ] Auth/session management not yet defined

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Cleared stale TODOs; added seed/verify commands; updated databases table |
| 2026-03-15 | Initial README — LangGraph, MongoDB, Docker architecture |
