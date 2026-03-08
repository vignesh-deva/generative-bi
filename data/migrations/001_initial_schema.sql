-- ============================================================
-- Generative BI Agent — FMCG Supply Chain Schema
-- DB: SQLite
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- MASTER DATA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categories (
    category_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                          -- Beverages, Snacks, Dairy & Ready-to-eat
    created_at      TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES categories(category_id),
    sku_code        TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    brand           TEXT NOT NULL,
    unit            TEXT NOT NULL,                          -- e.g. 500ml, 100g, 1kg
    mrp             REAL NOT NULL,                          -- Max Retail Price (INR)
    cost_price      REAL NOT NULL,                          -- Manufacturer cost (INR)
    created_at      TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS zones (
    zone_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE                    -- North, South, East, West
);

CREATE TABLE IF NOT EXISTS states (
    state_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id         INTEGER NOT NULL REFERENCES zones(zone_id),
    name            TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cities (
    city_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id        INTEGER NOT NULL REFERENCES states(state_id),
    name            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distributors (
    distributor_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    contact_name    TEXT,
    phone           TEXT,
    active          INTEGER DEFAULT 1,                      -- 1 = active, 0 = inactive
    created_at      TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS wholesalers (
    wholesaler_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    contact_name    TEXT,
    phone           TEXT,
    active          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS retailers (
    retailer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    retailer_type   TEXT NOT NULL,                          -- Modern Trade, General Trade, E-Commerce
    wholesaler_id   INTEGER REFERENCES wholesalers(wholesaler_id),
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    city_id         INTEGER NOT NULL REFERENCES cities(city_id),
    active          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (DATE('now'))
);

-- ------------------------------------------------------------
-- TRANSACTIONAL DATA
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders (
    order_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    distributor_id      INTEGER NOT NULL REFERENCES distributors(distributor_id),
    order_date          TEXT NOT NULL,                      -- ISO date YYYY-MM-DD
    expected_delivery   TEXT NOT NULL,
    status              TEXT NOT NULL
                            CHECK(status IN ('Pending','Fulfilled','Partial','Cancelled'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    ordered_qty     INTEGER NOT NULL,
    unit_price      REAL NOT NULL                           -- Price at time of order (INR)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    ship_date       TEXT NOT NULL,
    delivered_date  TEXT
);

CREATE TABLE IF NOT EXISTS shipment_items (
    shipment_item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id         INTEGER NOT NULL REFERENCES shipments(shipment_id),
    product_id          INTEGER NOT NULL REFERENCES products(product_id),
    shipped_qty         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer_id     INTEGER NOT NULL REFERENCES retailers(retailer_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    sale_date       TEXT NOT NULL,
    qty_sold        INTEGER NOT NULL,
    selling_price   REAL NOT NULL                           -- Actual price sold at (INR)
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    distributor_id  INTEGER NOT NULL REFERENCES distributors(distributor_id),
    snapshot_date   TEXT NOT NULL,
    stock_qty       INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------
-- SESSION / APP DATA (chat persistence)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id      TEXT PRIMARY KEY,                       -- UUID
    title           TEXT,
    created_at      TEXT DEFAULT (DATETIME('now')),
    updated_at      TEXT DEFAULT (DATETIME('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES chat_sessions(session_id),
    role            TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content         TEXT NOT NULL,
    sql_query       TEXT,                                   -- SQL generated for this message (if any)
    created_at      TEXT DEFAULT (DATETIME('now'))
);

CREATE TABLE IF NOT EXISTS insight_requests (
    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT REFERENCES chat_sessions(session_id),
    message_id      INTEGER REFERENCES chat_messages(message_id),
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT DEFAULT 'Pending'
                        CHECK(status IN ('Pending','In Progress','Done','Rejected')),
    created_at      TEXT DEFAULT (DATETIME('now'))
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
