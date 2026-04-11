# `data/migrations/`

> SQL migration scripts — schema definitions for the FMCG supply chain PostgreSQL database.

## Overview

These SQL files are automatically applied by the PostgreSQL Docker container on first boot via `docker-entrypoint-initdb.d`. They run in filename order. Seeding (mock data) is handled separately by `user_portal/backend/db/seed.py`.

## Files

| File | Purpose |
|------|---------|
| `001_initial_schema.sql` | Creates all tables, indexes, and the pgvector extension |
| `002_seed_data.sql` | Reserved placeholder — empty. FMCG data is seeded manually via `user_portal/backend/db/seed.py` |

## Schema Summary

### Master Data
| Table | Description |
|-------|-------------|
| `categories` | Product categories (Beverages, Snacks, Dairy & Ready-to-eat) |
| `products` | SKUs with brand, unit, MRP, cost price |
| `zones` | Geographic zones (North, South, East, West) |
| `states` | States mapped to zones |
| `cities` | Cities mapped to states |
| `distributors` | Distributor master, linked to cities |
| `wholesalers` | Wholesaler master, linked to distributors and cities |
| `retailers` | Retailer master (Modern Trade, General Trade, E-Commerce) |

### Transactional Data
| Table | Description |
|-------|-------------|
| `orders` | Purchase orders from distributors (Pending/Fulfilled/Partial/Cancelled) |
| `order_items` | Line items per order (product, qty, unit price) |
| `shipments` | Outbound shipments against orders |
| `shipment_items` | Line items per shipment (product, shipped qty) |
| `sales` | Sell-through at retailer level (date, qty, selling price) |
| `inventory` | Weekly stock snapshots per product per distributor |

### RAG
| Table | Description |
|-------|-------------|
| `fewshot_examples` | NL → SQL pairs with pgvector embeddings for few-shot retrieval |

> Chat sessions, messages, feedback, and dashboard requests are stored in **MongoDB** — not PostgreSQL.

## Conventions

- All dates stored as `DATE` (PostgreSQL native type)
- Monetary values in INR (Indian Rupees), stored as `NUMERIC(10,2)`
- Boolean flags as `BOOLEAN`
- Foreign keys enforced via standard PostgreSQL constraints

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Removed stale session table references (moved to MongoDB); emptied 002_seed_data.sql (data seeding moved to seed.py) |
| 2026-03-15 | Migrated from SQLite to PostgreSQL; added pgvector fewshot_examples table |
| 2026-03-11 | Initial README |
