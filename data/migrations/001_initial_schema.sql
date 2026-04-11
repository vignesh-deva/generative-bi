-- ============================================================
-- Generative BI Agent — FMCG Supply Chain Schema
-- DB: PostgreSQL + pgvector
-- ============================================================

-- Enable pgvector extension for few-shot NL→SQL embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ------------------------------------------------------------
-- MASTER DATA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categories (
    category_id     SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,                          -- Beverages, Snacks, Dairy & Ready-to-eat
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    product_id      SERIAL PRIMARY KEY,
    category_id     INTEGER NOT NULL REFERENCES categories(category_id),
    sku_code        TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    brand           TEXT NOT NULL,
    unit            TEXT NOT NULL,                          -- e.g. 500ml, 100g, 1kg
    mrp             NUMERIC(10,2) NOT NULL,                -- Max Retail Price (INR)
    cost_price      NUMERIC(10,2) NOT NULL,                -- Manufacturer cost (INR)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS zones (
    zone_id         SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE                    -- North, South, East, West
);

CREATE TABLE IF NOT EXISTS states (
    state_id        SERIAL PRIMARY KEY,
    zone_id         INTEGER NOT NULL REFERENCES zones(zone_id),
    name            TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cities (
    city_id         SERIAL PRIMARY KEY,
    state_id        INTEGER NOT NULL REFERENCES states(state_id),
    name            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distributors (
    distributor_id  SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    contact_name    TEXT,
    phone           TEXT,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wholesalers (
    wholesaler_id   SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    contact_name    TEXT,
    phone           TEXT,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retailers (
    retailer_id     SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    retailer_type   TEXT NOT NULL,                          -- Modern Trade, General Trade, E-Commerce
    wholesaler_id   INTEGER REFERENCES wholesalers(wholesaler_id),
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- TRANSACTIONAL DATA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders (
    order_id            SERIAL PRIMARY KEY,
    distributor_id      INTEGER NOT NULL REFERENCES distributors(distributor_id),
    order_date          DATE NOT NULL,
    expected_delivery   DATE NOT NULL,
    status              TEXT NOT NULL
                            CHECK(status IN ('Pending','Fulfilled','Partial','Cancelled'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    ordered_qty     INTEGER NOT NULL,
    unit_price      NUMERIC(10,2) NOT NULL                 -- Price at time of order (INR)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    ship_date       DATE NOT NULL,
    delivered_date  DATE
);

CREATE TABLE IF NOT EXISTS shipment_items (
    shipment_item_id    SERIAL PRIMARY KEY,
    shipment_id         INTEGER NOT NULL REFERENCES shipments(shipment_id),
    product_id          INTEGER NOT NULL REFERENCES products(product_id),
    shipped_qty         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id         SERIAL PRIMARY KEY,
    retailer_id     INTEGER NOT NULL REFERENCES retailers(retailer_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    sale_date       DATE NOT NULL,
    qty_sold        INTEGER NOT NULL,
    selling_price   NUMERIC(10,2) NOT NULL                 -- Actual price sold at (INR)
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id    SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    snapshot_date   DATE NOT NULL,
    stock_qty       INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------
-- RAG: Few-shot NL → SQL examples (pgvector)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fewshot_examples (
    example_id      SERIAL PRIMARY KEY,
    question        TEXT NOT NULL,                          -- Natural language question
    sql_query       TEXT NOT NULL,                          -- Corresponding SQL query
    embedding       vector(1536),                          -- Question embedding (dimension depends on model)
    source          TEXT DEFAULT 'manual',                  -- 'manual' | 'curated' (via ops portal)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_sales_date        ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_product     ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_retailer    ON sales(retailer_id);
CREATE INDEX IF NOT EXISTS idx_inventory_date    ON inventory(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_date       ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_dist       ON orders(distributor_id);
CREATE INDEX IF NOT EXISTS idx_shipments_order   ON shipments(order_id);

-- pgvector HNSW index for similarity search on few-shot examples.
-- HNSW is preferred over IVFFlat because:
--   - Exact (not approximate) nearest-neighbor at any table size
--   - IVFFlat with lists=10 and probes=1 returns wrong results on small tables
--     (< ~1000 rows) because most clusters are searched from one probe only
-- m=16 ef_construction=64 are conservative defaults suitable for 1536-dim vectors.
CREATE INDEX IF NOT EXISTS idx_fewshot_embedding ON fewshot_examples
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- NOTE: Chat sessions, messages, and dashboard requests are stored in MongoDB.
-- See user_portal/backend/db/mongo.py for collection definitions.
