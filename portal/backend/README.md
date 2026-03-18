# `portal/backend/`

> FastAPI service — agent pipeline, chat API, and dashboard request handling for the user-facing portal.

## Overview

This is the main backend service. It exposes REST + SSE endpoints consumed by the Next.js frontend and orchestrates the NL → SQL → Insight agent pipeline using **LangGraph**.

Runs as a Docker container (port 8000) or standalone via `uvicorn`.

## Structure

```
portal/backend/
├── main.py              # FastAPI app entry point, router registration, lifespan
├── agents/              # Individual agent modules (classifier, guardrails, RAG, SQL, etc.)
├── graph/               # LangGraph workflow definition (pipeline.py)
├── api/                 # FastAPI route handlers (chat, history, requests)
├── db/                  # PostgreSQL connection management, schema introspection, seeder
├── rag/                 # pgvector store and few-shot document corpus
├── utils/               # SSE streaming helpers
├── config/              # Pydantic settings (env-driven)
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

Each subfolder has its own README with detailed documentation.

## Key Responsibilities

- **Chat endpoint** — receives NL questions, runs the LangGraph agent pipeline, streams SSE events back to the frontend
- **Agent pipeline** — Classifier, Guardrails, and RAG run in parallel (fan-out), then Schema Agent → SQL Agent ↔ Validation Agent → PostgreSQL execution → Insight Agent
- **Chat history** — persisted in MongoDB (sessions, messages, feedback)
- **FMCG data** — queried via PostgreSQL (read-only for LLM-generated SQL)
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
docker-compose up portal-backend
```

### Manual
```bash
cd portal/backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# configure LLM endpoint, PostgreSQL DSN, and MongoDB URI in .env
uvicorn main:app --reload --port 8000
```

## TODO

- [ ] `main.py` is currently an empty scaffold — implementation pending
- [ ] `graph/` directory and `pipeline.py` do not exist yet — LangGraph workflow needs to be created
- [ ] `requirements.txt` needs LangGraph, motor (async MongoDB), asyncpg, pgvector, and other dependencies
- [ ] `.env.example` does not exist yet

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Initial README — LangGraph, MongoDB, Docker architecture |
