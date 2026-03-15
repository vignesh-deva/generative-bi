# Project Notepad

A running log of decisions, next steps, and open questions for the Generative BI Agent project.

---

## Current Sprint: Scaffolding & Infrastructure

### Completed
- [x] HLD alignment — LangGraph, MongoDB, Docker, ops portal
- [x] Updated all READMEs to reflect new architecture
- [x] Merged `feat/hld-update` → `develop` (PR #2)
- [x] Scaffold new directories — `ops-frontend/`, `ops-backend/`, `backend/graph/`
- [x] Set up Docker — `docker-compose.yml`, Dockerfiles, `.env.example`, `.dockerignore`
- [x] Remove SQLite session tables from schema (moved to MongoDB)
- [x] Set up MongoDB — `motor` driver, `backend/db/mongo.py`, collection definitions with indexes
- [x] Initialize frontends — `create-next-app` for `frontend/` (port 3000) and `ops-frontend/` (port 3001)
- [x] Updated `backend/requirements.txt` with FastAPI, Motor, LangGraph, LangChain deps
- [x] Created `backend/config/settings.py` with all env vars
- [x] Wired MongoDB lifecycle into `backend/main.py` (lifespan events)

### In Progress
- [ ] Restructure to domain-grouped folders — `portal/` (frontend + backend), `ops/` (frontend + backend)
- [ ] Replace SQLite + FAISS with PostgreSQL + pgvector
- [ ] Update `docker-compose.yml` — 6 services (portal-fe, portal-be, ops-fe, ops-be, postgres, mongodb)
- [ ] Migrate schema from SQLite to PostgreSQL syntax
- [ ] Add pgvector table for few-shot NL→SQL examples
- [ ] Update all READMEs, configs, Dockerfiles to match new structure

### Up Next
- [ ] Build LangGraph pipeline (`portal/backend/graph/pipeline.py`)
- [ ] Implement agents one by one (Classifier → Guardrails → RAG → Schema → SQL → Validation → Insight)
- [ ] Frontend pages — Dashboard (hardcoded charts), Chat, Requests, Recent
- [ ] Operations Center pages — Tickets, Feedback, RAG Curation
- [ ] SSE streaming integration
- [ ] Seed pgvector with sample few-shot NL→SQL examples

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent orchestration | LangGraph | Parallel fan-out (Classifier + Guardrails + RAG), conditional edges, state management |
| Chat/session storage | MongoDB | Document-shaped data, flexible schema for messages/feedback |
| Business data | PostgreSQL | Proper DB server, scales from dev to prod, no file-locking across containers |
| Vector store | pgvector (PostgreSQL extension) | Native vector search in same DB as business data, eliminates separate FAISS service |
| Deployment | Docker Compose | 6 services, named volumes for persistence |
| Folder structure | Domain-grouped | `portal/` (user-facing FE+BE), `ops/` (operations FE+BE) |
| Ops portal | Separate FE + BE | Clean separation, independent access control |
| LLM | Model-agnostic | `.env` config — Ollama, LM Studio, cloud APIs |

### Superseded Decisions
| Original | Replaced With | Why |
|----------|--------------|-----|
| SQLite for business data | PostgreSQL | Future-proofing — proper server, no file-sharing issues, pgvector bonus |
| FAISS for vector store | pgvector | Consolidates into PostgreSQL, one fewer technology to manage |
| Flat folder structure | Domain-grouped (`portal/`, `ops/`) | Clearer ownership boundaries, related FE+BE live together |

---

## Open Questions
- Power BI export — format and integration approach TBD
- Auth/access control for ops portal — TBD
- Guardrails agent — exact rules for SQL injection / prompt injection checks TBD

---

## Notes
- Ollama runs on host, not in Compose (users manage independently)
- Docker named volumes ensure all data persists across container restarts
- `docker-compose down -v` is the only way to lose data (the `-v` flag)
- Both backends connect to both PostgreSQL and MongoDB over the Docker network — no file mounts for data
- `data/migrations/` stays in repo as source for schema + seed — applied to PostgreSQL at startup
