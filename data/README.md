# `data/`

> Data directory — SQL migration scripts for the FMCG supply chain PostgreSQL database.

## Overview

This folder contains migration scripts that define the PostgreSQL schema. The FMCG business data and the pgvector few-shot store both live in the same PostgreSQL instance.

This is exclusively for the **FMCG business data** that the SQL Agent queries. Chat history and session data live in MongoDB (a separate Docker service).

## Structure

```
data/
└── migrations/
    └── 001_initial_schema.sql   # Table definitions, indexes, pgvector extension
```

## How Migrations Run

In Docker, the `postgres` service mounts `./data/migrations` to `/docker-entrypoint-initdb.d/`. PostgreSQL automatically runs all `.sql` files there on first boot (fresh volume only).

## How to Seed

After the schema is applied, populate mock data by running the seed script:

```bash
cd portal/backend
python -m db.seed
```

Then verify the data is correct:

```bash
python -m db.verify
```

## Docker Volume

PostgreSQL data is persisted via a named Docker volume:

```yaml
volumes:
  pg-data:    # persists across docker compose restarts
```

Data survives `docker compose down`. Only `docker compose down -v` deletes the volume.

> **Note:** Migrations only auto-run on a fresh volume. If the schema changes and the volume already exists, drop the volume and restart: `docker compose down -v && docker compose up postgres`.

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Removed 002_seed_data.sql reference; updated seed run command; fixed volume name |
| 2026-03-15 | Initial README |
