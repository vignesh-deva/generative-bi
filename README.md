# Generative BI Agent

An AI-powered BI tool where users ask business questions in natural language and receive data insights generated automatically from an FMCG supply chain dataset.

---

## Overview

Business users interact with the system through a chat interface. Questions are processed by an agentic backend (orchestrated with **LangGraph**) that classifies intent, retrieves context, generates and validates SQL, executes queries, and returns structured insights. A separate Dashboard page displays static chart cards. Business users can submit requests for new dashboards via the Requests workflow.

A dedicated **Operations Center** portal (separate app) allows the BI/dev team to review feedback, curate few-shot SQL examples in the vector store, and manage dashboard development tickets.

All services run via **Docker Compose**. LLM and embedding models are consumed via API — works with any OpenAI-compatible endpoint (cloud or self-hosted).

---

## Architecture

```
docker-compose.yml
├── portal-frontend     Next.js — user portal              :3000
├── portal-backend      FastAPI — agent pipeline & APIs     :8000
├── ops-frontend        Next.js — operations center UI     :3001
├── ops-backend         FastAPI — ticket mgmt, RAG curation :8001
├── postgres            PostgreSQL + pgvector              :5432
└── mongodb             Chat history & session data        :27017
```

The LLM and embedding API provider runs externally — not managed by Compose.

---

## Project Structure

```
generative-bi/
├── portal/                              # User-facing application
│   ├── frontend/                        # Next.js + Tailwind
│   │   └── src/app/                     # App router (layout, pages)
│   │
│   └── backend/                         # FastAPI — agent pipeline & APIs
│       ├── main.py                      # App entry point, router registration
│       ├── agents/
│       │   ├── classifier.py            # Intent classification
│       │   ├── guardrails.py            # Safety & injection checks
│       │   ├── rag_agent.py             # Few-shot SQL example retrieval (pgvector)
│       │   ├── schema_agent.py          # Provides DB schema context to LLM
│       │   ├── sql_agent.py             # NL → SQL generation
│       │   ├── validation_agent.py      # Validates SQL, provides error feedback for retry
│       │   └── insight_agent.py         # Generates explanation from query results
│       ├── graph/
│       │   └── pipeline.py              # LangGraph workflow definition
│       ├── api/
│       │   ├── chat.py                  # POST /chat — main streaming query endpoint
│       │   ├── requests.py              # Dashboard request submission
│       │   └── history.py               # Chat session history endpoints
│       ├── db/
│       │   ├── database.py              # PostgreSQL connection pool (asyncpg)
│       │   ├── mongo.py                 # MongoDB connection and collections (motor)
│       │   ├── models.py                # Schema introspection (table/column metadata)
│       │   └── seed.py                  # Seed script for mock FMCG data
│       ├── rag/
│       │   ├── vector_store.py          # pgvector similarity search
│       │   └── documents.py             # NL→SQL example corpus
│       ├── utils/
│       │   └── streaming.py             # SSE streaming helpers
│       ├── config/
│       │   └── settings.py              # Model config, DB URIs, env vars
│       ├── requirements.txt
│       └── .env.example
│
├── ops/                                 # Operations center application
│   ├── frontend/                        # Next.js + Tailwind (port 3001)
│   │   └── src/app/
│   │
│   └── backend/                         # FastAPI — ops APIs
│       ├── main.py
│       ├── api/
│       │   ├── tickets.py               # Dashboard request ticket management
│       │   ├── feedback.py              # Chat feedback review & SQL curation
│       │   └── rag_admin.py             # RAG vector store CRUD (pgvector)
│       ├── config/
│       │   └── settings.py
│       ├── requirements.txt
│       └── .env.example
│
├── data/
│   └── migrations/
│       ├── 001_initial_schema.sql       # PostgreSQL schema + pgvector
│       └── 002_seed_data.sql            # Mock data: products, orders, inventory, etc.
│
├── docker-compose.yml
├── docs/
│   ├── NOTEPAD.md                       # Planning notepad — decisions & next steps
│   ├── architecture.md                  # Agent workflow and system design
│   └── data-model.md                    # Database schema reference
│
└── .env.example                         # Root-level env template
```

---

## User Portal Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/dashboard` | Static 2x2 chart grid with hardcoded FMCG data |
| **Request New** | `/requests/new` | Submit a request for a new dashboard/report |
| **+ New Chat** | `/chat` | NL → SQL chat with streaming agent responses |
| **Recent** | `/chat/history` | Past chat sessions (click to view) |

Requests have a detail view with viewable and editable comments.

---

## Operations Center Pages

| Page | Description |
|------|-------------|
| **Tickets** | View and manage dashboard development requests from business users |
| **Feedback** | Review thumbs-up/down feedback on chat responses |
| **RAG Curation** | Review agent-generated SQL — save good queries or fix bad ones, then persist to pgvector as few-shot examples |

This creates a **human-in-the-loop feedback loop** that continuously improves NL → SQL accuracy.

---

## FMCG Supply Chain Data Model

The PostgreSQL database is modelled from an FMCG manufacturer's perspective:

| Table | Description |
|---|---|
| `products` | SKUs, categories, brand, unit cost |
| `distributors` | Distributor master |
| `wholesalers` | Wholesaler master |
| `retailers` | Retailer master |
| `orders` | Purchase orders from distributors |
| `shipments` | Outbound shipments against orders |
| `sales` | Sell-through data at retailer level |
| `inventory` | Stock levels across the supply chain |
| `fewshot_examples` | NL → SQL pairs with embeddings (pgvector) |

---

## Agent Pipeline (LangGraph)

```
User Query
    │
    ├──────────────────────────────┐
    │ (parallel)                   │
    ▼                              ▼
┌─────────────┐  ┌────────────┐  ┌─────────────┐
│ Classifier  │  │ Guardrails │  │ RAG Lookup  │
│ (intent)    │  │ (safety)   │  │ (few-shot)  │
└──────┬──────┘  └─────┬──────┘  └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                 Schema Agent
                       │
                       ▼
                  SQL Agent ◄──── Validation Agent
                       │              (feedback loop, max 2 retries)
                       ▼
               Query Execution (PostgreSQL)
                       │
                       ▼
                 Insight Agent
                       │
                       ▼
              SSE stream → Frontend
```

---

## Databases

| Store | Engine | Purpose |
|-------|--------|---------|
| **FMCG data** | PostgreSQL | Relational business data — the NL → SQL query target |
| **RAG examples** | pgvector (PostgreSQL extension) | Few-shot NL → SQL pairs with embeddings — curated via Operations Center |
| **Chat history** | MongoDB | Sessions, messages, feedback — document-shaped, persistent |

All data is persisted via Docker named volumes — survives container restarts.

---

## Key Features

- Natural language → SQL analytics via LangGraph agent pipeline
- Parallel intent classification, guardrails, and RAG retrieval
- RAG output used as few-shot examples for SQL generation (pgvector)
- Agentic validation loop with error feedback (max 2 retries)
- Streaming responses via Server-Sent Events (SSE)
- Chat history persistence (MongoDB)
- Dashboard request workflow for business users
- Operations Center for feedback review and RAG curation
- Static dashboard with charts (Power BI export planned)
- Model-agnostic — configurable via `.env`
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

All model and database settings are configured via environment variables (`.env`). Point to any OpenAI-compatible API endpoint — cloud providers, self-hosted, etc.

```env
LLM_MODEL=your-model-name
LLM_BASE_URL=https://your-llm-api/v1
LLM_API_KEY=your-api-key
POSTGRES_URI=postgresql://genbi:genbi@localhost:5432/genbi
MONGODB_URI=mongodb://localhost:27017
```
