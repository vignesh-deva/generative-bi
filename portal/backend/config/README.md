# `portal/backend/config/`

> Application settings — environment-driven configuration for the LLM endpoint, databases, and runtime behaviour.

## Overview

Single source of truth for all configurable values. Settings are loaded from environment variables (via `.env`) so the LLM backend, PostgreSQL DSN, MongoDB URI, and pgvector settings can be changed without touching code.

## Files

| File | Purpose |
|------|---------|
| `settings.py` | Pydantic settings model — reads from `.env`, exposes typed config to all modules |
| `__init__.py` | Package init |

## Planned Configuration

```python
# LLM settings
LLM_BASE_URL: str         # e.g. http://localhost:11434/v1  (Ollama)
LLM_MODEL: str            # e.g. llama3, mistral, deepseek-coder
LLM_API_KEY: str          # "ollama" for local, real key for cloud
LLM_TEMPERATURE: float    # default 0.0 for deterministic SQL
LLM_MAX_TOKENS: int       # response length cap

# Database settings
POSTGRES_DSN: str         # FMCG business data + pgvector (asyncpg format)
MONGODB_URI: str          # Chat history & sessions (default: mongodb://localhost:27017)
MONGODB_DB_NAME: str      # Database name (default: genbi)

# RAG settings
PGVECTOR_TABLE: str       # Table name for pgvector few-shot store (default: rag_examples)

# Agent settings
SQL_MAX_RETRIES: int      # Validation retry limit (default: 2)
```

## Design Choices

- **Model-agnostic by design**: Works with Ollama, LM Studio, or any OpenAI-compatible endpoint. The base URL and model name are the only things that change.
- **Temperature 0 for SQL generation**: Deterministic output is critical for SQL — you don't want creative variation in query structure.
- **Dual database config**: PostgreSQL DSN for FMCG data and pgvector, MongoDB URI for chat/session storage. Each can be configured independently.
- **Docker-aware defaults**: In Docker, services reference container hostnames (e.g. `postgresql://postgres:5432/genbi`, `mongodb://mongodb:27017`). Locally, they default to `localhost`.

## TODO

- [ ] `settings.py` is currently an empty scaffold — implementation pending
- [ ] Use `pydantic-settings` (`BaseSettings`) for automatic `.env` loading and type validation
- [ ] `POSTGRES_DSN` override would allow pointing at a different database for testing

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Updated for PostgreSQL (asyncpg), pgvector, MongoDB, Docker-aware config |
| 2026-03-11 | Initial README — scaffolded, implementation pending |
