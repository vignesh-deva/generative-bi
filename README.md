# Generative BI Agent

An AI-powered BI tool where users ask business questions in natural language and receive data insights generated automatically from an FMCG supply chain dataset.

---

## Overview

Business users interact with the system through a chat interface. Questions are processed by a **4-stage agentic pipeline** (orchestrated with LangGraph) that classifies intent, disambiguates queries, links relevant schema, generates and validates SQL, self-repairs on errors, and streams structured insights back via SSE. A separate Dashboard page displays static chart cards, and business users can submit requests for new dashboards.

A dedicated **Operations Center** portal (separate app) allows the BI/dev team to review feedback, curate few-shot SQL examples in the vector store, and manage dashboard development tickets.

All services run via **Docker Compose**. LLM and embedding models are consumed via API — works with any OpenAI-compatible endpoint (cloud or self-hosted).

---

## Agent Pipeline Design

> **This is the core of the system.** Open the interactive design document in your browser:
>
> **[`docs/agent-pipeline-design.html`](docs/agent-pipeline-design.html)**
>
> To view: open the file directly in any browser, or run `start docs/agent-pipeline-design.html` (Windows) / `open docs/agent-pipeline-design.html` (Mac).

The pipeline is a 4-stage agentic system with 12 agents, parallel fan-out, a self-repair loop, and a small/large model split for cost and latency optimization:

```
Stage 1: Pre-processing (4-way parallel)
├── Guardrails Agent [small]          LLM-based safety check
├── Classifier + Disambiguator [small] Intent + ambiguity detection
├── RAG Agent [small + tool]          Few-shot retrieval (pgvector)
└── Schema Linker Agent [small + tool] Select relevant tables only
         │
         ▼ fan-in + route (blocked / ambiguous / chitchat → early exit)
         │
Stage 1B: Context Enrichment
└── Semantic Layer Agent [small + tool] Metric defs, value samples, join paths

Stage 2: SQL Generation
└── SQL Agent [large]
    ├── tool: Decomposer [small]       Single-step vs multi-step decision
    └── tool: Sub-query Gen [large]    SQL per sub-query (parallelizable)

Stage 3: Validation + Self-repair (max 3 iterations)
├── EXPLAIN dry-run (PostgreSQL)       Catches syntax + schema errors free
├── Execute query (PostgreSQL)
├── Error Classifier [small]           Categorize: syntax | schema | logic | runtime
├── Correction Agent [large]           Targeted fix based on error type
└── Logic Check Agent [small]          Does the SQL answer the question?

Stage 4: Response Synthesis
└── Insight Agent [large]              NL business insight
         │
         ▼
    SSE stream → Frontend
```

---

## Architecture

```
docker-compose.yml
├── portal-frontend     Next.js — user portal              :3000
├── portal-backend      FastAPI — agent pipeline & APIs     :8000
├── ops-frontend        Next.js — operations center UI      :3001
├── ops-backend         FastAPI — ticket mgmt, RAG curation :8001
├── postgres            PostgreSQL + pgvector               :5432
└── mongodb             Chat history & session data         :27017
```

The LLM and embedding API provider runs externally — not managed by Compose.

---

## Project Structure

```
generative-bi/
├── user_portal/                         # User-facing application
│   ├── frontend/                        # Next.js + Tailwind (port 3000)
│   │   └── src/
│   │       ├── app/                     # App router pages
│   │       │   ├── page.tsx             # Dashboard (3x3 KPI/chart grid)
│   │       │   ├── chat/page.tsx        # Chat (SSE streaming, SQL viewer)
│   │       │   ├── recent/page.tsx      # Recent chat sessions
│   │       │   └── requests/page.tsx    # Dashboard request submission
│   │       ├── components/              # AppShell, Sidebar, Header, KpiCard, ChartCard
│   │       └── lib/api.ts              # API client (fetch wrappers)
│   │
│   └── backend/                         # FastAPI — agent pipeline & APIs
│       ├── main.py                      # App entry, router registration, lifespan
│       ├── agents/                      # Agent modules (LLM + tools)
│       │   ├── guardrails.py            # [small] LLM-based safety check
│       │   ├── classifier.py            # [small] Intent classification (analytics/chitchat/history/ambiguous)
│       │   ├── response_agent.py        # [small] Handles non-analytics intents (chitchat, history, blocked, ambiguous)
│       │   ├── rag_agent.py             # Few-shot retrieval via pgvector cosine similarity
│       │   ├── schema_agent.py          # [small + tool] Schema Linker — selects relevant tables only
│       │   ├── semantic_layer.py        # Static knowledge base — metrics, join paths, business rules
│       │   ├── sql_agent.py             # [large + sub-agents] SQL generation (Decomposer + adapt/single/multi)
│       │   ├── validation_agent.py      # Dry-run, Error Classifier, Correction Agent, Logic Check
│       │   ├── insight_agent.py         # [large] NL business insight generation
│       │   └── tools/                   # Tool functions for agents
│       │       ├── schema_tools.py      # list_tables(), pull_schema(), value_samples()
│       │       ├── rag_tools.py         # get_embedding(), retrieve_fewshots()
│       │       ├── semantic_tools.py    # get_semantic_context()
│       │       ├── sql_tools.py         # dry_run_explain(), run_query()
│       │       └── history_tools.py     # fetch_chat_history()
│       ├── graph/
│       │   └── pipeline.py              # LangGraph v2 workflow (4 stages, fan-out, self-repair loop)
│       ├── api/
│       │   ├── chat.py                  # POST /api/chat — SSE streaming via pipeline.ainvoke()
│       │   ├── dashboard.py             # GET /api/dashboard/* — KPI + chart data
│       │   ├── requests.py              # POST/GET /api/requests
│       │   └── history.py               # GET /api/history/sessions
│       ├── db/
│       │   ├── database.py              # PostgreSQL pool (asyncpg), read-only queries
│       │   ├── mongo.py                 # MongoDB collections (motor)
│       │   ├── seed.py                  # Seed script — 60 products, 150 retailers, 178k sales
│       │   └── seed_fewshots.py         # Seed 15 NL-to-SQL few-shot examples (with embeddings)
│       └── config/
│           └── settings.py              # LLM_MODEL, LLM_MODEL_SMALL, EMBEDDING_MODEL, DB URIs
│
├── ops_portal/                          # Operations center application
│   ├── frontend/                        # Next.js + Tailwind (port 3001)
│   │   └── src/
│   │       ├── app/
│   │       │   ├── page.tsx             # Tickets (dashboard requests from users)
│   │       │   ├── feedback/page.tsx    # Feedback review (thumbs up/down)
│   │       │   └── rag/page.tsx         # RAG curation (few-shot examples)
│   │       ├── components/              # AppShell, Sidebar, Header
│   │       └── lib/api.ts              # API client
│   │
│   └── backend/                         # FastAPI — ops APIs
│       ├── main.py
│       ├── api/
│       │   ├── tickets.py               # GET/PATCH /api/tickets
│       │   ├── feedback.py              # GET /api/feedback
│       │   └── rag.py                   # GET/POST /api/rag/fewshots
│       ├── db/                          # Same PostgreSQL + MongoDB as portal
│       └── config/settings.py
│
├── data/
│   └── migrations/
│       └── 001_initial_schema.sql       # PostgreSQL schema + pgvector + indexes
│
├── docs/
│   ├── agent-pipeline-design.html       # Agent pipeline visual design (open in browser)
│   ├── data-guide.md                    # Dataset overview — schema, products, geography, example questions
│   └── NOTEPAD.md                       # Sprint log — decisions & next steps
│
├── docker-compose.yml
└── .env.example
```

---

## User Portal Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/` | 3x3 grid — 3 KPI cards + 6 charts (recharts, INR formatting) |
| **Chat** | `/chat` | NL-to-SQL chat with SSE streaming, suggestion chips, SQL viewer |
| **Recent** | `/recent` | Past chat sessions with relative timestamps, click to resume |
| **Requests** | `/requests` | Submit dashboard requests + track status (Pending/In Progress/Done/Rejected) |

---

## Operations Center Pages

| Page | Route | Description |
|------|-------|-------------|
| **Tickets** | `/` | View/manage dashboard requests from business users with status filter tabs |
| **Feedback** | `/feedback` | Review thumbs-up/down feedback on AI responses with SQL preview |
| **RAG Curation** | `/rag` | Manage few-shot NL-to-SQL examples — add, review, curate for accuracy |

This creates a **human-in-the-loop feedback loop** that continuously improves NL-to-SQL accuracy.

---

## FMCG Supply Chain Data Model

The PostgreSQL database is modelled from an FMCG manufacturer's perspective. For a full walkthrough of the dataset — products, geography, seasonality, and example questions — see the **[Data Guide](docs/data-guide.md)**.

| Table | Description |
|---|---|
| `categories` | Product categories (Beverages, Snacks, Dairy & Ready-to-eat) |
| `products` | 60 SKUs with brand, unit, MRP, cost price |
| `zones` / `states` / `cities` | Geographic hierarchy (4 zones, 13 states, 30+ cities) |
| `distributors` | Distributor master |
| `wholesalers` | Wholesaler master |
| `retailers` | Retailer master (Modern Trade, General Trade, E-Commerce) |
| `orders` / `order_items` | Purchase orders from distributors |
| `shipments` / `shipment_items` | Outbound shipments against orders |
| `sales` | Sell-through data at retailer level (~178k records) |
| `inventory` | Weekly stock snapshots across the supply chain |
| `fewshot_examples` | NL-to-SQL pairs with pgvector embeddings for RAG |

---

## Databases

| Store | Engine | Purpose |
|-------|--------|---------|
| **FMCG data** | PostgreSQL | Relational business data — the NL-to-SQL query target |
| **RAG examples** | pgvector (PostgreSQL extension) | Few-shot NL-to-SQL pairs with embeddings — curated via Operations Center |
| **Chat history** | MongoDB | Sessions, messages, feedback — document-shaped, persistent |

All data is persisted via Docker named volumes (`pg-data`, `mongo-data`). Data survives `docker-compose down` and container restarts. To wipe all data and start fresh, use `docker-compose down -v`.

---

## Key Features

- 4-stage agentic NL-to-SQL pipeline with 12 agents (LangGraph)
- Small/large model split — fast routing + powerful generation
- 4-way parallel pre-processing (Guardrails, Classifier, RAG, Schema Linker)
- Schema Linking — only relevant tables sent to LLM (not the full schema)
- Semantic Layer — metric definitions, value samples, FK join paths, business rules
- Query disambiguation — asks user to clarify ambiguous questions
- SQL Decomposer — breaks complex queries into sub-queries
- EXPLAIN dry-run validation — catches errors before execution (zero LLM cost)
- Error taxonomy + targeted correction (syntax, schema, logic, runtime)
- Self-repair loop with max 3 retries
- Streaming responses via SSE
- Chat history persistence (MongoDB)
- Dashboard request workflow for business users
- Operations Center for feedback review and RAG curation
- Model-agnostic — any OpenAI-compatible endpoint via `.env`
- Dockerized — all services via `docker-compose up`

---

## Running the App

### Docker (recommended)

**1. Configure environment**
```bash
cp .env.example .env
# Edit .env — set your LLM_MODEL, LLM_MODEL_SMALL, LLM_BASE_URL, LLM_API_KEY
```

**2. Build and start all services**
```bash
docker compose build
docker compose up -d
```

> **After any code change**, always run `docker compose build` before `docker compose up -d` — `up` alone reuses cached images and will not pick up your changes.

On **first start**, Docker creates two named volumes (`pg-data`, `mongo-data`) and PostgreSQL automatically runs all files in `data/migrations/` in order — schema is created before the backends start. On **subsequent starts**, the volumes already exist so migrations are skipped and your data is preserved.

> **Resetting data:** `docker compose down -v` removes the volumes and wipes all data. The next `docker compose up -d` will re-run migrations from scratch. Use this if setup failed partway through and you want a clean slate.

**3. Seed the database** (first run only)
```bash
# Seed FMCG supply chain data (~178k sales records)
docker compose exec portal-backend python db/seed.py

# Seed few-shot NL-to-SQL examples into pgvector (requires LLM_API_KEY for embeddings)
docker compose exec portal-backend python db/seed_fewshots.py
```

**4. Open in browser**

| Service | URL |
|---------|-----|
| User Portal | http://localhost:3000 |
| Operations Center | http://localhost:3001 |
| Portal API docs | http://localhost:8000/docs |
| Ops API docs | http://localhost:8001/docs |

---

### Local Development

For working on individual services without rebuilding Docker images.

**Prerequisites:** PostgreSQL (with pgvector extension) and MongoDB running locally. Copy and configure `.env` files before starting:

```bash
cp .env.example user_portal/backend/.env
cp ops_portal/backend/.env.example ops_portal/backend/.env
# Edit each .env with your local DB URIs and LLM settings
```

#### Portal Backend
```bash
cd user_portal/backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Seed data (first run):
```bash
python db/seed.py
python db/seed_fewshots.py
```

#### Portal Frontend
```bash
cd user_portal/frontend
npm install
npm run dev          # starts on :3000
```

#### Ops Backend
```bash
cd ops_portal/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

#### Ops Frontend
```bash
cd ops_portal/frontend
npm install
npm run dev          # starts on :3001
```

---

## Testing

The test suite has two layers with different purposes and run frequencies.

### Unit Tests — Orchestration (no LLM, ~4 seconds)

Tests the LangGraph graph routing, retry loops, error handling, and guardrail short-circuiting. All LLM calls and DB calls are mocked. These are deterministic and fast — run them on every commit.

```bash
cd user_portal/backend
python -m pytest tests/test_pipeline.py -v
```

**What is covered (21 tests):**

| Category | Tests | What is verified |
|---|---|---|
| Analytics happy path | 6 | Full pipeline: classify → schema → sql → dry-run → execute → logic → insight |
| Non-analytics routing | 4 | Chitchat, history, ambiguous queries exit early via response agent |
| Guardrails blocking | 4 | SQL injection, prompt injection, DML requests are blocked |
| Dry-run retry loop | 3 | Single retry, double retry, max retries exhausted then proceeds |
| Execution errors | 2 | DB connection lost, statement timeout produce error responses |
| Logic check failures | 2 | Logic correction succeeds; max retries causes pipeline to proceed anyway |

---

### Eval Tests — LLM Integration (requires a configured LLM endpoint)

Tests that the individual agents and the full pipeline produce correct output when real LLM calls are made. DB I/O is mocked — no live PostgreSQL or MongoDB needed. These are non-deterministic and consume tokens, so they are opt-in.

Enable by setting `RUN_EVAL=1`:

```bash
cd user_portal/backend

# Run the full eval suite
RUN_EVAL=1 python -m pytest tests/eval/ -v

# Run individual eval files
RUN_EVAL=1 python -m pytest tests/eval/test_classifier.py -v     # intent accuracy (12 cases)
RUN_EVAL=1 python -m pytest tests/eval/test_guardrails.py -v     # safe/unsafe detection (15 cases)
RUN_EVAL=1 python -m pytest tests/eval/test_sql_agent.py -v      # SQL structure validation (7 cases)
RUN_EVAL=1 python -m pytest tests/eval/test_pipeline_e2e.py -v   # full pipeline (5 cases)
```

**What is covered:**

| File | Cases | What is verified |
|---|---|---|
| `test_classifier.py` | 12 | Correct intent for analytics, chitchat, history, ambiguous queries; follow-up resolution with chat history |
| `test_guardrails.py` | 15 | Safe analytics queries pass; SQL injection, prompt injection, DML, PII extraction are blocked |
| `test_sql_agent.py` | 7 | Generated SQL starts with `SELECT`/`WITH`, no DML keywords, references expected tables; RAG adapt path |
| `test_pipeline_e2e.py` | 5 | End-to-end: correct routing, SQL present for analytics, non-empty insights, chitchat handled, guardrails active |

**When to run evals:**
- After changing any agent prompt
- After switching LLM models
- Before merging a feature branch that touches the pipeline

---

### Running both suites

```bash
cd user_portal/backend

# Unit tests only (default, CI-safe)
python -m pytest tests/test_pipeline.py -v

# Unit tests + eval (manual, pre-merge)
RUN_EVAL=1 python -m pytest tests/ -v
```

---

## Configuration

All model and database settings are configured via environment variables (`.env`).

```env
# Large model — SQL generation, correction, insights
LLM_MODEL=gpt-5.4
# Small model — classification, routing, guardrails, schema linking
LLM_MODEL_SMALL=gpt-5.4-mini
# LLM endpoint (any OpenAI-compatible API)
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key

# Embedding model — used for RAG few-shot similarity search
EMBEDDING_MODEL=text-embedding-3-small

# Max SQL retry attempts in self-repair loop
MAX_SQL_RETRIES=3

# Databases
POSTGRES_URI=postgresql://genbi:genbi@localhost:5432/genbi
MONGODB_URI=mongodb://localhost:27017
```

| Setup | Small Model | Large Model |
|-------|-------------|-------------|
| OpenAI | `gpt-5.4-mini` | `gpt-5.4` |
| Local (Ollama) | `llama3:8b` | `llama3:70b` / `deepseek-coder-v2` |
| Anthropic | `claude-haiku-4-5` | `claude-sonnet-4-6` |
| Single model | Set both to the same value | |
