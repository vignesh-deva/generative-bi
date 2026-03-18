# `data/migrations/`

> SQL migration scripts — schema definitions and seed data for the FMCG supply chain PostgreSQL database.

## Overview

These SQL files define the database structure and are used by the seeder (`portal/backend/db/seed.py`) to create and populate the PostgreSQL database. They are applied in order by filename prefix.

## Files

| File | Purpose |
|------|---------|
| `001_initial_schema.sql` | Creates all tables, constraints, and indexes |
| `002_seed_data.sql` | Placeholder — actual seeding is done programmatically by `portal/backend/db/seed.py` |

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

### Session/App Data (to be migrated)
| Table | Description |
|-------|-------------|
| `chat_sessions` | Chat session metadata — **will move to MongoDB** |
| `chat_messages` | Chat messages — **will move to MongoDB** |
| `insight_requests` | Dashboard requests — **will move to MongoDB** |

These session tables exist in the current schema but will be removed once chat history and requests are fully served by MongoDB.

## Conventions

- All dates stored as `DATE` (PostgreSQL native type)
- Monetary values in INR (Indian Rupees), stored as `NUMERIC`
- Boolean flags as `BOOLEAN`
- Foreign keys enforced via standard PostgreSQL constraints

## Changelog

| Date | Change |
|------|--------|
| 2026-03-15 | Initial README — documented schema, noted MongoDB migration for session tables |
