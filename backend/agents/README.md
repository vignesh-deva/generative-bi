# `backend/agents/`

> Agent pipeline — the chain of LLM-powered modules that convert a natural language question into a SQL query, execute it, and produce a business insight.

## Overview

This folder contains every agent in the NL → SQL → Insight pipeline. Each agent is a focused module with a single responsibility. They are orchestrated by `backend/api/chat.py`, which wires them together and streams results to the frontend via SSE.

## Files

| File | Purpose |
|------|---------|
| `classifier.py` | Classifies incoming questions as analytics, chitchat, or out-of-scope |
| `rag_agent.py` | Retrieves few-shot SQL examples from the vector store to guide the SQL Agent |
| `schema_agent.py` | Fetches the live DB schema and formats it for the SQL Agent's system prompt |
| `sql_agent.py` | Generates SQLite SQL from the question, schema, and few-shot examples |
| `validation_agent.py` | Checks generated SQL for correctness and safety; provides feedback for retries |
| `insight_agent.py` | Converts query results into a plain-English business insight |
| `__init__.py` | Package init |

## Agent Pipeline

```mermaid
flowchart TD
    Q[User Question] --> C[Classifier]
    C -->|analytics| R[RAG Agent]
    C -->|chitchat / OOS| STOP[Early exit]
    R -->|few-shot examples| S[Schema Agent]
    S -->|schema + examples| SQL[SQL Agent]
    SQL -->|generated SQL| V[Validation Agent]
    V -->|valid| DB[(SQLite)]
    V -->|invalid + feedback| SQL
    DB -->|results| I[Insight Agent]
    I -->|streamed insight| SSE[SSE → Frontend]
```

The SQL Agent retries up to 2 times when Validation Agent returns an error, passing the error message back as context.

## Design Choices

- **RAG output feeds SQL Agent as few-shot examples** — not used as a standalone answer path. This grounds the LLM in real query patterns from the codebase rather than generating SQL blind.
- **Validation Agent provides feedback, never blocks** — it returns structured feedback that the SQL Agent uses on retry. Max 2 retries to prevent infinite loops.
- **Each agent is stateless** — agents receive all context they need as function arguments. No shared mutable state between pipeline steps.
- **Model-agnostic** — all agents call the LLM endpoint configured in `backend/config/settings.py`. Supports Ollama, LM Studio, or any OpenAI-compatible API.

## TODO

- [ ] All agent files are currently empty scaffolds — implementation pending
- [ ] Classifier needs label definitions: what counts as "analytics" vs out-of-scope for FMCG supply chain
- [ ] SQL Agent retry limit (2) should come from `settings.py`, not be hardcoded
- [ ] Validation Agent should check for SQL injection patterns in addition to syntax errors
- [ ] Consider adding a timeout per agent to prevent hung LLM calls blocking the SSE stream

## Changelog

| Date | Change |
|------|--------|
| 2026-03-11 | Initial README — scaffolded, implementation pending |
