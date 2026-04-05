# `user_portal/backend/db/`

> Database layer — PostgreSQL connection pool (asyncpg), MongoDB collections (motor), schema introspection, mock data seeding, and post-seed verification.

## Overview

This folder owns the database access layer. PostgreSQL stores the FMCG supply chain data and pgvector few-shot examples. MongoDB stores chat sessions, messages, feedback, and dashboard requests.

All other backend modules access databases through the public API exported from `__init__.py`.

## Files

| File | Purpose |
|------|---------|
| `database.py` | asyncpg connection pool, read-only `execute_query()` for the SQL Agent |
| `mongo.py` | Motor (async MongoDB) client, collection accessors, index creation |
| `models.py` | Schema introspection — dataclasses for table/column/FK metadata, prompt-ready schema string |
| `seed.py` | Mock data generator — 12 months of FMCG supply chain data (Jan–Dec 2025) |
| `verify.py` | Post-seed verification — 33 checks across row counts, integrity, and analytical queries |
| `__init__.py` | Re-exports `get_pool`, `execute_query`, `get_db`, `close_client`, `create_indexes` |

## Running the Seeder and Verifier

```bash
cd user_portal/backend

# Populate mock data
python -m db.seed

# Verify the data (exits 0 on pass, 1 on failure)
python -m db.verify
```

Expected seed output (with `random.seed(42)`):
```
Categories:   3
Products:     60
Distributors: 15
Wholesalers:  40
Retailers:    150
Orders:       832
Sales:        178,651
Inventory:    29,468
```

## Functionality

### PostgreSQL Connection (`database.py`)

asyncpg connection pool initialised at app startup via `get_pool()`. SQL Agent queries execute inside read-only transactions — LLM-generated SQL physically cannot mutate data.

```python
async def execute_query(sql: str, params: list | None = None) -> dict[str, Any]:
    # Returns: {"columns": [...], "rows": [[...], ...], "row_count": int}
    # Raises ValueError if query is not SELECT or WITH
```

### MongoDB Connection (`mongo.py`)

Motor async client with collection accessors for each document type. Indexes created at app startup via `create_indexes()`.

```python
def chat_sessions()       -> AsyncIOMotorCollection
def chat_messages()       -> AsyncIOMotorCollection
def dashboard_requests()  -> AsyncIOMotorCollection
```

### Schema Introspection (`models.py`)

Introspects the live PostgreSQL schema at runtime using `information_schema` queries. Returns a formatted string injected into the SQL Agent's system prompt.

### Seed Data (`seed.py`)

Generates realistic FMCG data with:
- **60 products** across 3 categories from real Indian brands
- **15 distributors**, 40 wholesalers, 150 retailers across 4 zones
- **832 orders** with items and shipments (72.8% fulfilment rate)
- **178,651 sales records** with category-aware seasonality (Beverages peak summer, Snacks peak Diwali)
- **29,468 weekly inventory snapshots** per distributor

Uses `random.seed(42)` — re-running always produces the same dataset.

### Verify Script (`verify.py`)

33 automated checks run against the live DB:
- **14 row count checks** — every table meets expected minimums
- **11 integrity checks** — no orphaned FKs, valid enums, clean date ranges, no bad prices
- **8 analytical checks** — seasonality patterns, fulfilment rate, zone coverage, MRP compliance

## Design Choices

- **Read-only transactions for SQL Agent**: Defense in depth — LLM-generated SQL cannot mutate data at the driver level, not just application logic.
- **Schema introspected at runtime**: Always matches actual DB state — no risk of drift between hardcoded descriptions and real columns.
- **asyncpg connection pool**: Shared pool initialised at startup, reused across requests.
- **Motor for MongoDB**: Fully async — no blocking I/O in FastAPI request handlers.
- **Deterministic seed**: `random.seed(42)` makes debugging reproducible.

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Added mongo.py and verify.py to file table; corrected data counts; fixed run commands; updated __init__ exports |
| 2026-03-15 | Migrated from SQLite to PostgreSQL (asyncpg); added MongoDB layer |
| 2026-03-11 | Initial README |
