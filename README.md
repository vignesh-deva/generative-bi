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
└── Insight Agent [large]              NL business insight, Indian formatting
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
├── portal/                              # User-facing application
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
│       │   ├── guardrails.py            # [small] Safety check
│       │   ├── classifier.py            # [small] Intent + disambiguation
│       │   ├── rag_agent.py             # [small + tool] Few-shot retrieval
│       │   ├── schema_linker.py         # [small + tool] Table selection
│       │   ├── semantic_layer.py        # [small + tool] Metric defs + rules
│       │   ├── sql_agent.py             # [large + sub-agents] SQL generation
│       │   ├── error_classifier.py      # [small] Error taxonomy
│       │   ├── correction_agent.py      # [large] Targeted SQL fixes
│       │   ├── logic_check.py           # [small] Post-execution verification
│       │   ├── insight_agent.py         # [large] NL response generation
│       │   └── tools/                   # Tool functions for agents
│       │       ├── schema_tools.py      # pull_schema(), get_table_summaries()
│       │       ├── rag_tools.py         # search_fewshots()
│       │       ├── semantic_tools.py    # lookup_metrics()
│       │       └── sql_tools.py         # dry_run_explain(), execute_query()
│       ├── graph/
│       │   └── pipeline.py              # LangGraph workflow orchestration
│       ├── api/
│       │   ├── chat.py                  # POST /api/chat — SSE streaming endpoint
│       │   ├── dashboard.py             # GET /api/dashboard/* — KPI + chart data
│       │   ├── requests.py              # POST/GET /api/requests
│       │   └── history.py               # GET /api/history/sessions
│       ├── db/
│       │   ├── database.py              # PostgreSQL pool (asyncpg), read-only queries
│       │   ├── mongo.py                 # MongoDB collections (motor)
│       │   └── seed.py                  # Seed script — 60 products, 150 retailers, 178k sales
│       └── config/
│           └── settings.py              # LLM_MODEL, LLM_MODEL_SMALL, DB URIs
│
├── ops/                                 # Operations center application
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

The PostgreSQL database is modelled from an FMCG manufacturer's perspective:

| Table | Description |
|---|---|
| `categories` | Product categories (Beverages, Snacks, Dairy & Ready-to-eat) |
| `products` | SKUs with brand, unit, MRP, cost price |
| `zones` / `states` / `cities` | Geographic hierarchy (4 zones, 13 states, 30+ cities) |
| `distributors` | Distributor master |
| `wholesalers` | Wholesaler master |
| `retailers` | Retailer master (Modern Trade, General Trade, E-Commerce) |
| `orders` / `order_items` | Purchase orders from distributors |
| `shipments` / `shipment_items` | Outbound shipments against orders |
| `sales` | Sell-through data at retailer level (178k records) |
| `inventory` | Weekly stock snapshots across the supply chain |
| `fewshot_examples` | NL-to-SQL pairs with pgvector embeddings for RAG |

---

## Databases

| Store | Engine | Purpose |
|-------|--------|---------|
| **FMCG data** | PostgreSQL | Relational business data — the NL-to-SQL query target |
| **RAG examples** | pgvector (PostgreSQL extension) | Few-shot NL-to-SQL pairs with embeddings — curated via Operations Center |
| **Chat history** | MongoDB | Sessions, messages, feedback — document-shaped, persistent |

All data is persisted via Docker named volumes — survives container restarts.

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

## Getting Started

### Docker (recommended)
```bash
cp .env.example .env
# configure LLM endpoint in .env
docker-compose up
```

| Service | URL |
|---------|-----|
| User Portal | http://localhost:3000 |
| Operations Center | http://localhost:3001 |
| Portal API | http://localhost:8000 |
| Ops API | http://localhost:8001 |

### Manual Setup

#### Portal Backend
```bash
cd portal/backend
pip install -r requirements.txt
cp .env.example .env
# configure your model and DB URIs in .env
uvicorn main:app --reload
```

#### Portal Frontend
```bash
cd portal/frontend
npm install
npm run dev
```

---

## Configuration

All model and database settings are configured via environment variables (`.env`).

```env
# Large model — SQL generation, correction, insights
LLM_MODEL=llama3:70b
# Small model — classification, routing, tool use
LLM_MODEL_SMALL=llama3:8b
# LLM endpoint (any OpenAI-compatible API)
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama

# Max SQL retry attempts in self-repair loop
MAX_SQL_RETRIES=3

# Databases
POSTGRES_URI=postgresql://genbi:genbi@localhost:5432/genbi
MONGODB_URI=mongodb://localhost:27017
```

| Setup | Small Model | Large Model |
|-------|-------------|-------------|
| Local (Ollama) | `llama3:8b` | `llama3:70b` / `deepseek-coder-v2` |
| OpenAI | `gpt-4o-mini` | `gpt-4o` |
| Anthropic | `claude-haiku-4-5` | `claude-sonnet-4-6` |
| Single model | Set both to the same value | |
