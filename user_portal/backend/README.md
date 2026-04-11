# `user_portal/backend/`

> FastAPI service — agent pipeline, chat API, and dashboard request handling for the user-facing portal.

## Overview

This is the main backend service. It exposes REST + SSE endpoints consumed by the Next.js frontend and orchestrates the NL-to-SQL-to-Insight agent pipeline using **LangGraph**.

Runs as a Docker container (port 8000) or standalone via `uvicorn`.

## Structure

```
user_portal/backend/
├── main.py              # FastAPI app entry point, lifespan (pool init + index creation)
├── agents/              # Agent modules
│   ├── guardrails.py    # [small] LLM-based safety check (no tools)
│   ├── classifier.py    # [small] Intent classification with chat history (no tools)
│   ├── response_agent.py # [small] Handles non-analytics intents (blocked/ambiguous/chitchat/history)
│   ├── rag_agent.py     # RAG few-shot retrieval via pgvector cosine similarity
│   ├── schema_agent.py  # [small + tool] Schema Linker — identifies relevant tables
│   ├── semantic_layer.py # Deprecated shim — re-exports from config/semantic_layer.py
│   ├── sql_agent.py     # [large + sub-agents] SQL generation (Decomposer + adapt/single/multi)
│   ├── validation_agent.py # Dry-run, Error Classifier, Correction Agent, Logic Check
│   ├── insight_agent.py # [large] NL business insight generation
│   └── tools/           # Tool functions shared across agents
│       ├── schema_tools.py  # list_tables(), pull_schema(), value_samples()
│       ├── rag_tools.py     # get_embedding(), retrieve_fewshots()
│       ├── semantic_tools.py # get_semantic_context()
│       ├── sql_tools.py     # dry_run_explain(), run_query()
│       └── history_tools.py # fetch_chat_history()
├── graph/
│   └── pipeline.py      # LangGraph v2 pipeline (4 stages, fan-out, self-repair)
├── api/                 # FastAPI route handlers
│   ├── auth.py          # POST /auth/login — JWT issuance; verify_token dependency used by all routers
│   ├── chat.py          # POST /api/chat — SSE streaming via pipeline.ainvoke()
│   ├── dashboard.py     # GET /api/dashboard/* — KPI + chart data
│   ├── history.py       # GET /api/history/sessions + messages
│   └── requests.py      # POST/GET /api/requests (8-state lifecycle)
├── db/                  # Database connections, seeder, verifier
│   ├── database.py      # PostgreSQL pool (asyncpg), read-only execute_query()
│   ├── mongo.py         # MongoDB collections (motor)
│   ├── seed.py          # Seed FMCG data (60 products, 150 retailers, 178k sales)
│   └── seed_fewshots.py # Seed 15 NL-to-SQL few-shot examples (with embeddings)
├── config/
│   ├── settings.py      # LLM_MODEL, EMBEDDING_MODEL, DOMAIN_DESCRIPTION, DB URIs
│   └── semantic_layer.py # Static knowledge base — metrics, join paths, business rules, known values
├── requirements.txt
└── .env.example
```

## Agent Pipeline (v2)

The pipeline is a 4-stage LangGraph workflow with 12 agents:

```
Query → Fetch Chat History (MongoDB)
      → Query Rewriter (resolves follow-up references; skips if no history)
      → [Guardrails | Classifier | RAG | Schema Agent] (parallel fan-out)
      → Router (fan-in)
          ├── non-analytics → Response Agent → SSE → END
          └── analytics → Semantic Layer → SQL Agent → Dry-Run
              ├── passes → Execute → Validation Agent → Insight Agent → SSE → END
              └── fails  → Error Classifier → Correction Agent → retry (max 3)
```

### Agent Inventory

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Query Rewriter | small | none | Resolves follow-up references into a standalone query; skips if no history |
| Guardrails | small | none | LLM-based safety check (prompt injection, SQL injection, PII) |
| Classifier | small | none | Intent: analytics / chitchat / history / ambiguous |
| RAG Agent | — | pgvector | Few-shot NL-to-SQL retrieval by cosine similarity |
| Schema Agent | small | pull_schema, value_samples | Selects relevant tables; appends value samples for exact entity names |
| Response Agent | small | fetch_chat_history | Handles blocked, ambiguous, chitchat, history |
| Semantic Layer | — | — | Static knowledge base in `config/`: metrics, join paths, business rules |
| SQL Agent | large | decompose, generate | Decomposer sub-agent + adapt/single/multi strategies; injects today's date |
| Dry-Run Validator | — | EXPLAIN | PostgreSQL EXPLAIN validation (no LLM cost) |
| Error Classifier | small | none | Categorizes: syntax / schema / logic / runtime |
| Correction Agent | large | pull_schema, value_samples, dry_run_explain | Targeted SQL fix |
| Validation Agent | small | get_current_date, lookup_column, get_schema, get_join_info, run_test_query | Agentic logic check (tool loop, max 3 rounds); single-shot fallback |
| Insight Agent | large | none | Generates NL business insight from results |

## Databases

| Store | Engine | What It Stores |
|-------|--------|----------------|
| FMCG data | PostgreSQL | Products, orders, sales, inventory — the NL-to-SQL query target |
| Chat history | MongoDB | Sessions, messages, user feedback (thumbs up/down) |
| RAG examples | pgvector (PostgreSQL extension) | NL-to-SQL few-shot pairs, curated via Operations Center |

## Running

### Docker (recommended)
```bash
# From project root
docker compose up portal-backend
```

### Manual
```bash
cd user_portal/backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Fill in LLM endpoint, EMBEDDING_MODEL, POSTGRES_URI, and MONGODB_URI in .env
uvicorn main:app --reload --port 8000
```

### Seed the database
```bash
cd user_portal/backend
python -m db.seed           # populate mock FMCG data
python -m db.verify         # verify 33 checks pass
python -m db.seed_fewshots  # seed 15 NL-to-SQL few-shot examples
```

## Testing

### End-to-end (curl)
```bash
# Get a token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Analytics query — full pipeline: classify → RAG → schema link → SQL → execute → insight
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "What is the total revenue by zone?"}' \
  --no-buffer

# Non-analytics — Response Agent path
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "Hello, what can you help me with?"}' \
  --no-buffer

# Health check (public — no token required)
curl http://localhost:8000/health
```

SSE events in the response:
- `{"type": "status"}` — pipeline stage updates
- `{"type": "sql"}` — generated SQL query
- `{"type": "token"}` — streamed insight text (one word per event)
- `[DONE]` — stream complete

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `llama3` | Large model for SQL generation, correction, insights |
| `LLM_MODEL_SMALL` | same as LLM_MODEL | Small model for classification, guardrails, routing |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Any OpenAI-compatible API endpoint |
| `LLM_API_KEY` | `ollama` | API key for the LLM endpoint |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model for RAG embedding generation |
| `MAX_SQL_RETRIES` | `3` | Max self-repair iterations in the validation loop |
| `DOMAIN_DESCRIPTION` | `FMCG supply chain analytics` | Business domain label injected into all agent prompts |
| `PORTAL_USERNAME` | `testuser` | Login username for the user portal |
| `PORTAL_PASSWORD` | `testpass` | Login password for the user portal |
| `JWT_SECRET` | `dev-secret-change-in-prod` | HS256 signing secret for JWT tokens (change before deploying) |
| `POSTGRES_URI` | `postgresql://genbi:genbi@localhost:5432/genbi` | PostgreSQL connection |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection |

## Changelog

| Date | Change |
|------|--------|
| 2026-04-10 | Add JWT auth — `api/auth.py`, `verify_token` dependency on all API routers; `/auth/login` and `/health` remain public |
| 2026-04-05 | Dashboard request v2 — 8-state lifecycle, chat context capture, comment threads, auto-close |
| 2026-04-04 | Add Query Rewriter; upgrade Logic Check → Validation Agent (agentic tool loop); Schema Agent appends value samples; SQL Agent injects today's date |
| 2026-03-27 | Move semantic_layer to config/; derive all domain context from semantic layer + DOMAIN_DESCRIPTION setting |
| 2026-03-25 | v2 pipeline: 12 agents, 4 stages, semantic layer, schema linker, response agent, self-repair loop |
| 2026-03-18 | Cleared stale TODOs; added seed/verify commands; updated databases table |
| 2026-03-15 | Initial README — LangGraph, MongoDB, Docker architecture |
