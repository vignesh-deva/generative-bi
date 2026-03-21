# Project Notepad

A running log of decisions, next steps, and open questions for the Generative BI Agent project.

---

## Current Sprint: UI & Dashboards

### Completed — Scaffolding & Infrastructure
- [x] HLD alignment — LangGraph, MongoDB, Docker, ops portal
- [x] Domain-grouped folder restructure — `portal/` (FE+BE), `ops/` (FE+BE)
- [x] Replace SQLite + FAISS with PostgreSQL + pgvector
- [x] Docker Compose — 6 services (portal-fe, portal-be, ops-fe, ops-be, postgres, mongodb)
- [x] Migrate schema to PostgreSQL syntax; add pgvector `fewshot_examples` table
- [x] Initialize both frontends with `create-next-app` (Next.js + Tailwind, ports 3000 + 3001)
- [x] PostgreSQL connection pool (`asyncpg`) + read-only `execute_query()` for SQL Agent
- [x] MongoDB connection (`motor`) + collection definitions + indexes
- [x] Wired lifecycle events into `portal/backend/main.py` (pool init, index creation, teardown)
- [x] Rewrite `seed.py` for PostgreSQL — 60 products, 150 retailers, 832 orders, 178k sales records
- [x] `verify.py` — 33 automated checks (row counts, integrity, analytical queries), all passing
- [x] Username/password auth on PostgreSQL and MongoDB via `.env` / Docker Compose `${VAR}` substitution
- [x] Updated all READMEs to reflect current architecture
- [x] LLM config updated — model-agnostic via any OpenAI-compatible API (not Ollama-specific)

### Completed — UI & Dashboards
- [x] Portal frontend — Dashboard page (3×3 KPI/chart grid, recharts, INR formatting)
- [x] Portal frontend — Chat page (message bubbles, SSE streaming, suggestion chips, SQL viewer)
- [x] Portal frontend — Requests page (submit form + expandable list with status badges)
- [x] Portal frontend — Recent (chat history list with relative timestamps, session resume links)
- [x] Portal frontend — API lib (`fetchSessions`, `fetchMessages`, `fetchRequests`, `createRequest`, `checkHealth`)
- [x] Portal backend — `/api/chat` SSE endpoint with MongoDB session/message persistence (placeholder response)
- [x] Portal backend — `/api/history/sessions` + `/sessions/{id}/messages` (chat history)
- [x] Portal backend — `/api/requests` POST/GET (dashboard requests)
- [x] Ops frontend — full shell (AppShell, Sidebar, Header — violet theme)
- [x] Ops frontend — Tickets page (filtered list, status tabs, expandable details)
- [x] Ops frontend — Feedback page (thumbs up/down filter, AI responses with SQL)
- [x] Ops frontend — RAG Curation page (list/add few-shot NL→SQL examples)
- [x] Ops backend — `/api/tickets` + PATCH status, `/api/feedback`, `/api/rag/fewshots` GET/POST
- [x] Ops backend — db module (PostgreSQL pool + MongoDB connection, same DBs as portal)
- [x] Wire portal frontend to portal backend health endpoint

### Completed — Agent Pipeline (v1 skeleton, now superseded by v2 design)
- [x] `graph/pipeline.py` — LangGraph state schema, nodes, parallel fan-out, conditional routing
- [x] Initial agent implementations (Classifier, Guardrails, RAG, Schema, SQL, Validation, Insight)

### Completed — Pipeline Redesign (v2)
- [x] Designed 4-stage agentic pipeline with 12 agents — see `docs/agent-pipeline-design.html`
- [x] Every module is an agent (LLM + optional tools) for extensibility
- [x] Small/large model split for cost + latency optimization
- [x] Schema Linking replaces full schema dump — only relevant tables sent to LLM
- [x] Semantic Layer — metric definitions, value samples, FK join paths, business rules
- [x] LLM-based Guardrails (replaces regex-only)
- [x] Classifier + Disambiguator — asks user to clarify ambiguous queries
- [x] SQL Agent with Decomposer sub-agent for complex multi-step queries
- [x] EXPLAIN dry-run validation (free, deterministic) + LLM logic check
- [x] Error taxonomy (syntax, schema, logic, runtime) + Correction Agent
- [x] Self-repair loop increased to max 3 iterations

### Up Next — Implement v2 Pipeline
- [ ] Add `LLM_MODEL_SMALL` + `MAX_SQL_RETRIES` to `config/settings.py`
- [ ] Create `agents/tools/` — `schema_tools.py`, `rag_tools.py`, `semantic_tools.py`, `sql_tools.py`
- [ ] Implement Schema Linker agent (replace full Schema Agent)
- [ ] Implement Semantic Layer agent + static knowledge base
- [ ] Implement Classifier + Disambiguator (intent + ambiguity, SSE clarification flow)
- [ ] Upgrade Guardrails to LLM-based
- [ ] Implement SQL Agent with Decomposer + Sub-query Generator sub-agents
- [ ] Implement EXPLAIN dry-run validation (`sql_tools.dry_run_explain`)
- [ ] Implement Error Classifier + Correction Agent
- [ ] Implement Logic Check agent
- [ ] Rewrite `graph/pipeline.py` for v2 (4 stages, new nodes, updated routing)
- [ ] Wire v2 pipeline into `api/chat.py` — replace placeholder with `pipeline.ainvoke()` + SSE streaming
- [ ] Choose embedding model for RAG (e.g., `nomic-embed-text`, `text-embedding-3-small`)
- [ ] Implement vector similarity search in RAG Agent (replace DB fallback with pgvector `<=>`)
- [ ] Seed `fewshot_examples` with initial NL→SQL corpus (10-20 FMCG examples)
- [ ] End-to-end test: chat UI → SSE → pipeline → PostgreSQL → insight → streamed response

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
| LLM | Model-agnostic via API | Any OpenAI-compatible endpoint — configured via `.env` |
| DB auth | Username/password via `.env` | Credentials in `.env`, substituted into Docker Compose via `${VAR}` |

### Superseded Decisions
| Original | Replaced With | Why |
|----------|--------------|-----|
| SQLite for business data | PostgreSQL | Future-proofing — proper server, no file-sharing issues, pgvector bonus |
| FAISS for vector store | pgvector | Consolidates into PostgreSQL, one fewer technology to manage |
| Flat folder structure | Domain-grouped (`portal/`, `ops/`) | Clearer ownership boundaries, related FE+BE live together |
| Ollama-specific LLM config | Any OpenAI-compatible API | Not tied to a specific provider |

---

## Open Questions

- Power BI export — format and integration approach TBD
- Auth/access control for ops portal — TBD
- Embedding model choice for RAG — needs to be decided before implementing vector search in RAG Agent

---

## Notes

- LLM and embedding provider runs externally — not managed by Compose
- Docker named volumes ensure all data persists across container restarts
- `docker compose down -v` is the only way to lose data (the `-v` flag)
- Migrations auto-run on fresh PostgreSQL volume via `docker-entrypoint-initdb.d`
- Both backends connect to both PostgreSQL and MongoDB over the Docker network
- MongoDB auth enabled — connection URIs must include credentials + `?authSource=admin`
