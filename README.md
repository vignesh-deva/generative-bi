# Generative BI Agent

An AI-powered BI tool where users ask business questions in natural language and receive data insights generated automatically from an FMCG supply chain dataset.

---

## Overview

Business users interact with the system through a chat interface. Questions are processed by an agentic backend (orchestrated with **LangGraph**) that classifies intent, retrieves context, generates and validates SQL, executes queries, and returns structured insights. A separate Dashboard page displays static chart cards. Business users can submit requests for new dashboards via the Requests workflow.

A dedicated **Operations Center** portal (separate app) allows the BI/dev team to review feedback, curate few-shot SQL examples in the RAG vector store, and manage dashboard development tickets.

All services run via **Docker Compose**. Model-agnostic — works with Ollama, LM Studio, or any OpenAI-compatible endpoint.

---

## Architecture

```
docker-compose.yml
├── frontend          Next.js — user portal              :3000
├── backend           FastAPI — agent pipeline & APIs     :8000
├── ops-frontend      Next.js — operations center UI      :3001
├── ops-backend       FastAPI — ticket mgmt, RAG curation :8001
├── mongodb           Chat history & session data         :27017
└── sqlite            FMCG data (volume mount)
```

Ollama (or any LLM provider) runs on the host — not managed by Compose.

---

## Project Structure

```
generative-bi/
├── frontend/                        # Next.js + Tailwind — user portal
│   ├── public/
│   └── src/
│       ├── app/                     # Next.js app router (layout, pages)
│       ├── components/
│       │   ├── Sidebar.tsx          # Nav: Dashboard, Request New, +New Chat, Recent
│       │   ├── ChatWindow.tsx       # Main chat interface with streaming
│       │   ├── InsightCard.tsx      # Rendered insight: data + explanation
│       │   └── RequestsPanel.tsx    # Dashboard request submissions
│       ├── hooks/                   # Custom React hooks (e.g. useChat, useStream)
│       ├── lib/                     # API client, utilities
│       └── types/                   # Shared TypeScript types
│
├── ops-frontend/                    # Next.js + Tailwind — operations center
│   └── src/                         # (structure mirrors frontend/)
│
├── backend/                         # FastAPI — agent pipeline & user-facing APIs
│   ├── main.py                      # App entry point, router registration
│   ├── agents/
│   │   ├── classifier.py            # Intent classification
│   │   ├── guardrails.py            # Safety & injection checks
│   │   ├── rag_agent.py             # Few-shot SQL example retrieval
│   │   ├── schema_agent.py          # Provides DB schema context to LLM
│   │   ├── sql_agent.py             # NL → SQL generation
│   │   ├── validation_agent.py      # Validates SQL, provides error feedback for retry
│   │   └── insight_agent.py         # Generates explanation from query results
│   ├── graph/
│   │   └── pipeline.py              # LangGraph workflow definition
│   ├── api/
│   │   ├── chat.py                  # POST /chat — main streaming query endpoint
│   │   ├── requests.py              # Dashboard request submission (business users)
│   │   └── history.py               # Chat session history endpoints
│   ├── db/
│   │   ├── database.py              # SQLite connection and query execution
│   │   ├── models.py                # Schema introspection (table/column metadata)
│   │   └── seed.py                  # Seed script for mock FMCG data
│   ├── rag/
│   │   ├── vector_store.py          # FAISS index build and retrieval
│   │   └── documents.py             # NL→SQL example corpus
│   ├── utils/
│   │   └── streaming.py             # SSE streaming helpers
│   ├── config/
│   │   └── settings.py              # Model config, DB paths, env vars
│   ├── requirements.txt
│   └── .env.example
│
├── ops-backend/                     # FastAPI — operations center APIs
│   ├── main.py
│   ├── api/
│   │   ├── tickets.py               # Dashboard request ticket management
│   │   ├── feedback.py              # Chat feedback review & SQL curation
│   │   └── rag_admin.py             # RAG vector store CRUD
│   ├── config/
│   │   └── settings.py
│   ├── requirements.txt
│   └── .env.example
│
├── data/
│   └── migrations/
│       ├── 001_initial_schema.sql   # FMCG supply chain schema
│       └── 002_seed_data.sql        # Mock data: products, orders, inventory, etc.
│
├── docker-compose.yml
├── docs/
│   ├── architecture.md              # Agent workflow and system design
│   └── data-model.md                # Database schema reference
│
└── .env.example                     # Root-level env template
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
| **RAG Curation** | Review agent-generated SQL — save good queries or fix bad ones, then persist to the FAISS vector store as few-shot examples |

This creates a **human-in-the-loop feedback loop** that continuously improves NL → SQL accuracy.

---

## FMCG Supply Chain Data Model

The SQLite database is modelled from an FMCG manufacturer's perspective:

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
               Query Execution (SQLite)
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
| **FMCG data** | SQLite | Relational business data — the NL → SQL query target |
| **Chat history** | MongoDB | Sessions, messages, feedback — document-shaped, persistent |
| **RAG examples** | FAISS | Few-shot NL → SQL pairs — curated via Operations Center |

All data is persisted via Docker named volumes — survives container restarts.

---

## Key Features

- Natural language → SQL analytics via LangGraph agent pipeline
- Parallel intent classification, guardrails, and RAG retrieval
- RAG output used as few-shot examples for SQL generation
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
| Backend API | http://localhost:8000 |
| Ops API | http://localhost:8001 |

### Manual Setup

#### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# configure your model in .env
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Configuration

All model and database settings are configured via environment variables (`.env`). Point to any OpenAI-compatible endpoint — Ollama, LM Studio, cloud APIs, etc.

```env
LLM_MODEL=llama3
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
MONGODB_URI=mongodb://localhost:27017
SQLITE_DB_PATH=./data/genbi.db
FAISS_INDEX_PATH=./data/faiss_index
```
