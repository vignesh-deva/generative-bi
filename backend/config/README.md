# `backend/config/`

> Application settings — environment-driven configuration for the LLM endpoint, model selection, and runtime behaviour.

## Overview

Single source of truth for all configurable values. Settings are loaded from environment variables (via `.env`) so the LLM backend can be swapped between Ollama, LM Studio, or any OpenAI-compatible endpoint without touching code.

## Files

| File | Purpose |
|------|---------|
| `settings.py` | Pydantic settings model — reads from `.env`, exposes typed config to all modules |
| `__init__.py` | Package init |

## Planned Configuration

```python
# Expected settings in settings.py
LLM_BASE_URL: str       # e.g. http://localhost:11434/v1  (Ollama)
LLM_MODEL: str          # e.g. llama3, mistral, deepseek-coder
LLM_API_KEY: str        # "ollama" for local, real key for cloud
LLM_TEMPERATURE: float  # default 0.0 for deterministic SQL
LLM_MAX_TOKENS: int     # response length cap

DB_PATH: str            # optional override for data/genbi.db
```

## Design Choices

- **Model-agnostic by design**: The project targets local inference (Ollama / LM Studio) but any OpenAI-compatible endpoint works. The base URL and model name are the only things that change.
- **Temperature 0 for SQL generation**: Deterministic output is critical for SQL — you don't want creative variation in query structure.
- **No cloud services**: All config values point to local endpoints. Nothing is sent to external APIs unless the user explicitly sets `LLM_BASE_URL` to a cloud endpoint.

## TODO

- [ ] `settings.py` is currently an empty scaffold — implementation pending
- [ ] Use `pydantic-settings` (`BaseSettings`) for automatic `.env` loading and type validation
- [ ] `DB_PATH` override would allow pointing at a different database for testing without touching `database.py`

## Changelog

| Date | Change |
|------|--------|
| 2026-03-11 | Initial README — scaffolded, implementation pending |
