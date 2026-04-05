# `user_portal/backend/config/`

> Application settings — environment-driven configuration for the LLM API, databases, and runtime behaviour.

## Overview

Single source of truth for all configurable values. Settings are loaded from environment variables (via `.env`) so the LLM endpoint, PostgreSQL URI, and MongoDB URI can be changed without touching code.

## Files

| File | Purpose |
|------|---------|
| `settings.py` | Loads env vars via `python-dotenv` — exposes typed config to all modules |
| `__init__.py` | Package init |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `your-model-name` | Large model — SQL generation, correction, insight |
| `LLM_MODEL_SMALL` | same as `LLM_MODEL` | Small model — classification, guardrails, rewriting, routing |
| `LLM_BASE_URL` | — | Base URL of any OpenAI-compatible API endpoint |
| `LLM_API_KEY` | — | API key for the LLM provider |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model for RAG embedding generation |
| `MAX_SQL_RETRIES` | `3` | Max self-repair iterations in the validation loop |
| `DOMAIN_DESCRIPTION` | `FMCG supply chain analytics` | Business domain label injected into all agent prompts |
| `POSTGRES_URI` | — | Full asyncpg connection string (includes credentials) |
| `MONGODB_URI` | — | Full MongoDB connection string (includes credentials + `?authSource=admin`) |
| `MONGODB_DB_NAME` | `genbi` | MongoDB database name |

Copy `.env.example` to `.env` and fill in values before running.

## Design Choices

- **Model-agnostic by design**: Works with any OpenAI-compatible API — cloud providers, self-hosted, etc. Only the base URL and model name change.
- **Temperature 0 for SQL generation**: Deterministic output is critical — you don't want creative variation in query structure.
- **Dual database config**: PostgreSQL URI for FMCG data and pgvector; MongoDB URI for chat/session storage. Each configured independently.
- **Docker-aware URIs**: In Docker, service hostnames replace `localhost` (e.g. `postgres`, `mongodb`). In `.env.example` for Docker vs local are documented separately.

## Changelog

| Date | Change |
|------|--------|
| 2026-04-04 | Added `DOMAIN_DESCRIPTION`, `LLM_MODEL_SMALL`, `EMBEDDING_MODEL`, `MAX_SQL_RETRIES` to docs |
| 2026-03-27 | Added `LLM_MODEL_SMALL`, `MAX_SQL_RETRIES`, `DOMAIN_DESCRIPTION` to settings.py |
| 2026-03-18 | Removed Ollama-specific references; corrected POSTGRES_DSN → POSTGRES_URI |
| 2026-03-15 | Initial README |
