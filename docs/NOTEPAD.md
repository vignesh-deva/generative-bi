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

### Up Next — UI & Dashboards
- [ ] Portal frontend — Dashboard page (hardcoded FMCG charts, 2×2 grid)
- [ ] Portal frontend — Chat page (UI shell, SSE-ready but no agent yet)
- [ ] Portal frontend — Requests page (submit + list dashboard requests)
- [ ] Portal frontend — Recent (chat history list)
- [ ] Ops frontend — Tickets page
- [ ] Ops frontend — Feedback page
- [ ] Ops frontend — RAG Curation page
- [ ] Wire portal frontend to portal backend health endpoint (confirm Docker connectivity)

### After UI — Agent Pipeline
- [ ] `graph/pipeline.py` — LangGraph state schema, node wiring, parallel fan-out, retry loop
- [ ] Classifier agent (intent: analytics / chitchat / out-of-scope)
- [ ] Schema Agent (introspect live PostgreSQL schema for SQL Agent prompt)
- [ ] SQL Agent (NL → PostgreSQL SQL)
- [ ] Validation Agent + retry loop (max 2 retries)
- [ ] Insight Agent (query results → plain English)
- [ ] RAG Agent (pgvector few-shot retrieval) — needs embedding model decision first
- [ ] Guardrails agent (SQL injection / prompt injection checks)
- [ ] `api/chat.py` — wire pipeline to SSE endpoint
- [ ] Seed `fewshot_examples` with initial NL→SQL corpus

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
- Guardrails agent — exact rules for SQL injection / prompt injection checks TBD
- Embedding model choice for RAG — needs to be decided before implementing RAG Agent

---

## Notes

- LLM and embedding provider runs externally — not managed by Compose
- Docker named volumes ensure all data persists across container restarts
- `docker compose down -v` is the only way to lose data (the `-v` flag)
- Migrations auto-run on fresh PostgreSQL volume via `docker-entrypoint-initdb.d`
- Both backends connect to both PostgreSQL and MongoDB over the Docker network
- MongoDB auth enabled — connection URIs must include credentials + `?authSource=admin`
