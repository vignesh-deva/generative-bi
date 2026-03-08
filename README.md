# Generative BI Agent

A local AI-powered BI tool where users ask business questions in natural language and receive data insights generated automatically from an FMCG supply chain dataset.

---

## Overview

Business users interact with the system through a chat interface. Questions are processed by an agentic backend that classifies intent, retrieves context, generates and validates SQL, executes queries, and returns structured insights. A separate Charts dashboard displays saved insight cards. Business users can escalate insights to the BI team via the Requests workflow.

Everything runs locally — no cloud services required.

---

## Project Structure

```
generative-bi/
├── frontend/                        # Next.js + Tailwind UI
│   ├── public/
│   └── src/
│       ├── app/                     # Next.js app router (layout, pages)
│       ├── components/
│       │   ├── Sidebar.tsx          # Nav: Charts, New Chat, Requests, History
│       │   ├── ChatWindow.tsx       # Main chat interface with streaming
│       │   ├── InsightCard.tsx      # Rendered insight: data + explanation
│       │   └── RequestsPanel.tsx    # Business user request submissions
│       ├── hooks/                   # Custom React hooks (e.g. useChat, useStream)
│       ├── lib/                     # API client, utilities
│       └── types/                   # Shared TypeScript types
│
├── backend/                         # FastAPI agentic service
│   ├── main.py                      # App entry point, router registration
│   ├── agents/
│   │   ├── classifier.py            # Routes query → RAG or SQL workflow
│   │   ├── rag_agent.py             # FAQ answers + few-shot examples for SQL gen
│   │   ├── schema_agent.py          # Provides DB schema context to LLM
│   │   ├── sql_agent.py             # NL → SQL generation
│   │   ├── validation_agent.py      # Validates SQL, provides error feedback for retry
│   │   └── insight_agent.py         # Generates explanation from query results
│   ├── api/
│   │   ├── chat.py                  # POST /chat — main streaming query endpoint
│   │   ├── requests.py              # Insight request submission (business users)
│   │   └── history.py               # Chat session history endpoints
│   ├── db/
│   │   ├── database.py              # SQLite connection and query execution
│   │   ├── models.py                # ORM models (sessions, messages, requests)
│   │   └── seed.py                  # Seed script for mock FMCG data
│   ├── rag/
│   │   ├── vector_store.py          # FAISS index build and retrieval
│   │   └── documents.py             # Source FAQ/metric definition documents
│   ├── utils/
│   │   └── streaming.py             # SSE streaming helpers
│   ├── config/
│   │   └── settings.py              # Model config, DB path, env vars
│   ├── requirements.txt
│   └── .env.example
│
├── data/
│   └── migrations/
│       ├── 001_initial_schema.sql   # FMCG supply chain schema
│       └── 002_seed_data.sql        # Mock data: products, orders, inventory, etc.
│
└── docs/
    ├── architecture.md              # Agent workflow and system design
    └── data-model.md                # Database schema reference
```

---

## FMCG Supply Chain Data Model (Overview)

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

## Agent Workflow

```
User Query
    │
    ▼
Classifier
    ├── FAQ / Metric Definition
    │       └── RAG Agent → few-shot examples → SQL Agent
    │
    └── Analytics Query
            └── Schema Agent
                    └── SQL Agent
                            └── Validation Agent (feedback loop, max 2 retries)
                                    └── Query Execution (SQLite)
                                            └── Insight Agent
                                                    └── Streamed response to frontend
```

---

## Key Features

- Natural language → SQL analytics
- RAG for metric definitions and FAQ (FAISS, local)
- RAG output used as few-shot examples for SQL generation
- Agentic validation loop with error feedback
- Streaming responses via Server-Sent Events (SSE)
- Chat session persistence (SQLite)
- Business user insight request workflow
- Charts dashboard (Power BI export planned)
- Fully local — model-agnostic, configurable via `.env`

---

## Getting Started

_Setup instructions will be added as the project is scaffolded._

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# configure your model in .env
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Configuration

All model settings are in `backend/.env`. Developers can point to any locally hosted model (Ollama, LM Studio, etc.) or API-compatible endpoint.

```env
MODEL_NAME=llama3
MODEL_BASE_URL=http://localhost:11434
DB_PATH=./data/genbi.db
```
