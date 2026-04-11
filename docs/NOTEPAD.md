# Project Notepad

A running log of decisions, next steps, and open questions for the Generative BI Agent project.

---

## Current Sprint: Bug Fixes

### Completed — Scaffolding & Infrastructure
- [x] HLD alignment — LangGraph, MongoDB, Docker, ops portal
- [x] Domain-grouped folder restructure — `user_portal/` (FE+BE), `ops_portal/` (FE+BE)
- [x] Replace SQLite + FAISS with PostgreSQL + pgvector
- [x] Docker Compose — 6 services (portal-fe, portal-be, ops-fe, ops-be, postgres, mongodb)
- [x] Migrate schema to PostgreSQL syntax; add pgvector `fewshot_examples` table
- [x] Initialize both frontends with `create-next-app` (Next.js + Tailwind, ports 3000 + 3001)
- [x] PostgreSQL connection pool (`asyncpg`) + read-only `execute_query()` for SQL Agent
- [x] MongoDB connection (`motor`) + collection definitions + indexes
- [x] Wired lifecycle events into `user_portal/backend/main.py` (pool init, index creation, teardown)
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

### Completed — Pipeline Refinements (v2.1)
- [x] Guardrails, Classifier, Error Classifier → pure LLM calls, no tools (simpler, cheaper)
- [x] Response Agent added — handles chitchat + history intents (non-analytics exit path)
- [x] Intents refined to: chitchat, history (summary/question on chat history), analytics
- [x] RAG few-shot examples now explicitly wired into SQL Agent prompt as exemplars
- [x] Decomposer checks RAG similarity score — if ≥ 0.85, skips decomposition and adapts matched query directly
- [x] Chat history integration — fetched from MongoDB before Stage 1, injected into Classifier (follow-up resolution) and SQL Agent
- [x] Correction Agent given tools: `pull_schema`, `value_samples`, `dry_run_explain` — can properly diagnose and fix errors
- [x] Removed Indian formatting from Insight Agent
- [x] Added `response_agent.py` + `history_tools.py` to file structure
- [x] Non-analytics timing path added — 3 LLM calls (Guardrails + Classifier + Response Agent)

### Completed — v2 Pipeline Implementation (2026-03-27, branch: feat/e2e-wiring)
- [x] Add `LLM_MODEL_SMALL` + `MAX_SQL_RETRIES` + `DOMAIN_DESCRIPTION` to `config/settings.py`
- [x] Create `agents/tools/` — `schema_tools.py`, `rag_tools.py`, `semantic_tools.py`, `sql_tools.py`, `history_tools.py`
- [x] Implement Schema Agent (replaces full schema dump with targeted linking + value samples)
- [x] Implement Semantic Layer — moved to `config/semantic_layer.py` (metrics, join paths, business rules, known values)
- [x] Implement Classifier (intents: analytics / chitchat / history / ambiguous) — terms derived from semantic layer
- [x] Implement Response Agent (chitchat, history, blocked, ambiguous — context from semantic layer)
- [x] Upgrade Guardrails to LLM-based (no tools)
- [x] Implement SQL Agent with Decomposer + Sub-query Generator sub-agents (RAG fewshots as exemplars)
- [x] Implement EXPLAIN dry-run validation (`sql_tools.dry_run_explain`)
- [x] Implement Error Classifier (no tools) + Correction Agent (with schema/sample/explain tools)
- [x] Rewrite `graph/pipeline.py` for v2 (4 stages, fan-out, self-repair, chat history fetch)
- [x] Wire v2 pipeline into `api/chat.py` — `pipeline.ainvoke()` + SSE streaming
- [x] Choose embedding model → `text-embedding-3-small` (OpenAI), set in `.env`
- [x] Implement pgvector similarity search in RAG Agent — register codec via asyncpg `init`
- [x] Seed `fewshot_examples` with 15 NL→SQL examples + OpenAI embeddings
- [x] End-to-end verified: chat → SSE → pipeline → PostgreSQL → insight → streamed response
- [x] Agents made domain-agnostic: hardcoded FMCG references replaced with `DOMAIN_DESCRIPTION` + semantic layer injection

### Completed — v2.2 Pipeline Refinements (2026-04-04, branch: feat/e2e-wiring)
- [x] Add Query Rewriter agent — resolves follow-up references into standalone queries before fan-out
- [x] Upgrade Logic Check → Validation Agent — agentic tool-calling loop (get_current_date, lookup_column, get_schema, get_join_info, run_test_query); single-shot fallback
- [x] Schema Agent appends value samples to schema context — SQL Agent uses exact entity names
- [x] SQL Agent injects today's date into system prompt
- [x] Add `lookup_column` to `schema_tools.py` — type-aware (distinct values / stats / date range)
- [x] Add collapsible StepsPanel to chat UI — shows pipeline steps with spinner; auto-collapses on first token
- [x] Fix session switching — `useSearchParams` + `sessionParam` dependency
- [x] Add structured logging across all agents

### Completed — Dashboard Request v2 (2026-04-05, branch: feat/dashboard-request-v2)
- [x] Replaced 4-status request flow with full 8-state lifecycle (draft → requested → in-progress → need additional details → completed → accepted/request changes → closed)
- [x] MongoDB schema v2 with one-shot migration (drop + recreate on boot)
- [x] State-machine-enforced transitions in both user and ops backends
- [x] Chat integration — "Request Dashboard" button on every assistant message captures question, answer, SQL, and last 6 messages as context
- [x] User portal — Drafts/Active/Closed tabs, hint panel, comment threads, Accept / Request Changes / Close actions
- [x] Ops portal — 8-status tabs, chat context preview, transition buttons
- [x] Lazy auto-close sweep (no scheduler needed) — runs on list/detail reads

### Completed — Portal Auth (2026-04-10, branch: feat/dashboard-request-v2)
- [x] JWT-based auth (PyJWT, HS256, 7-day tokens) on both portal backends
- [x] `POST /auth/login` endpoint — validates `PORTAL_USERNAME` / `PORTAL_PASSWORD` from `.env`
- [x] All API routes protected via FastAPI dependency (`verify_token`) — `/auth/login` and `/health` remain public
- [x] Next.js middleware on both frontends — redirects unauthenticated users to `/login`
- [x] Login pages for user portal (port 3000) and ops portal (port 3001)
- [x] `logout()` helper clears cookie and redirects; logout button in both portal headers
- [x] `PORTAL_USERNAME=testuser`, `PORTAL_PASSWORD=testpass`, `JWT_SECRET` added to root `.env` and all `.env.example` files; passed to Docker services via docker-compose
- [x] Separate session cookies — user portal uses `auth_token`, ops portal uses `ops_auth_token` — sessions are fully independent

### Completed — Feedback RAG Promotion (2026-04-11, branch: feat/feedback-rag-promotion)
- [x] Ops portal — Feedback page: promote feedback to RAG, mark reviewed, delete actions wired up
- [x] Ops portal — RAG Curation: updated queries and curation workflow

### Completed — Chat with Charts (2026-04-11, branch: feat/chat-with-charts)
- [x] Chart context injected into chat — assistant can reference dashboard chart data in responses

### Open Bugs
- [ ] **[BUG]** SSE response lost on session switch — if the user navigates to another chat while a response is still streaming and then returns, the in-progress response is gone. The stream is abandoned client-side on unmount and there is no mechanism to reconnect or replay the partial/completed response. Fix requires either persisting the full streamed response to MongoDB as it arrives (so it can be loaded on return), or keeping the SSE connection alive in a background context and rehydrating the UI on re-navigation.
- [ ] **[BUG]** Slash command chart picker — arrow key navigation resets to top. When using the arrow keys to move down through the chart list in the slash command dropdown, focus jumps back to the first item instead of advancing. Scrolling with mouse and clicking works fine.

### Up Next
- [ ] Fix open bugs (see above)
- [ ] Power BI export — format and integration approach TBD
- [ ] Auth/access control hardening for production (separate ops vs user credentials, HTTPS-only cookies)

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent orchestration | LangGraph | Parallel fan-out (Classifier + Guardrails + RAG), conditional edges, state management |
| Chat/session storage | MongoDB | Document-shaped data, flexible schema for messages/feedback |
| Business data | PostgreSQL | Proper DB server, scales from dev to prod, no file-locking across containers |
| Vector store | pgvector (PostgreSQL extension) | Native vector search in same DB as business data, eliminates separate FAISS service |
| Deployment | Docker Compose | 6 services, named volumes for persistence |
| Folder structure | Domain-grouped | `user_portal/` (user-facing FE+BE), `ops_portal/` (operations FE+BE) |
| Ops portal | Separate FE + BE | Clean separation, independent access control |
| LLM | Model-agnostic via API | Any OpenAI-compatible endpoint — configured via `.env` |
| DB auth | Username/password via `.env` | Credentials in `.env`, substituted into Docker Compose via `${VAR}` |

### Superseded Decisions
| Original | Replaced With | Why |
|----------|--------------|-----|
| SQLite for business data | PostgreSQL | Future-proofing — proper server, no file-sharing issues, pgvector bonus |
| FAISS for vector store | pgvector | Consolidates into PostgreSQL, one fewer technology to manage |
| Flat folder structure | Domain-grouped (`user_portal/`, `ops_portal/`) | Clearer ownership boundaries, related FE+BE live together |
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
