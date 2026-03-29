"""
Shared fixtures and constants for eval tests.

Eval tests run actual LLM calls.  DB I/O is mocked so the suite
can run without a live PostgreSQL/MongoDB instance.

Run:  RUN_EVAL=1 python -m pytest tests/eval/ -v
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

# ── Skip gate ──────────────────────────────────────────────────────
# Eval tests are opt-in — they need a real LLM endpoint and burn tokens.
# Set RUN_EVAL=1 in the environment to enable them.

if not os.getenv("RUN_EVAL"):
    collect_ignore_glob = ["*.py"]  # skip entire directory


# ── FMCG schema constants (used in sql_agent + pipeline e2e tests) ─

FMCG_TABLES = [
    "categories", "products", "zones", "states", "cities",
    "distributors", "wholesalers", "retailers",
    "orders", "order_items", "shipments", "shipment_items",
    "sales", "inventory",
]

SCHEMA_STUB = """\
TABLE categories:
  category_id integer NOT NULL [PK]
  name character varying NOT NULL

TABLE products:
  product_id integer NOT NULL [PK]
  name character varying NOT NULL
  category_id integer NOT NULL
  cost_price numeric NOT NULL
  mrp numeric NOT NULL

TABLE zones:
  zone_id integer NOT NULL [PK]
  name character varying NOT NULL

TABLE states:
  state_id integer NOT NULL [PK]
  name character varying NOT NULL
  zone_id integer NOT NULL

TABLE cities:
  city_id integer NOT NULL [PK]
  name character varying NOT NULL
  state_id integer NOT NULL

TABLE retailers:
  retailer_id integer NOT NULL [PK]
  name character varying NOT NULL
  city_id integer NOT NULL
  distributor_id integer NOT NULL
  retailer_type character varying NOT NULL

TABLE distributors:
  distributor_id integer NOT NULL [PK]
  name character varying NOT NULL
  city_id integer NOT NULL

TABLE orders:
  order_id integer NOT NULL [PK]
  distributor_id integer NOT NULL
  status character varying NOT NULL
  created_at timestamp NOT NULL

TABLE shipments:
  shipment_id integer NOT NULL [PK]
  order_id integer NOT NULL
  ship_date date NOT NULL
  delivered_date date

TABLE sales:
  sale_id integer NOT NULL [PK]
  retailer_id integer NOT NULL
  product_id integer NOT NULL
  qty_sold integer NOT NULL
  selling_price numeric NOT NULL
  sale_date date NOT NULL

TABLE inventory:
  inventory_id integer NOT NULL [PK]
  product_id integer NOT NULL
  distributor_id integer NOT NULL
  stock_qty integer NOT NULL
  snapshot_date date NOT NULL

FOREIGN KEYS:
  FK: products.category_id -> categories.category_id
  FK: states.zone_id -> zones.zone_id
  FK: cities.state_id -> states.state_id
  FK: retailers.city_id -> cities.city_id
  FK: retailers.distributor_id -> distributors.distributor_id
  FK: orders.distributor_id -> distributors.distributor_id
  FK: shipments.order_id -> orders.order_id
  FK: sales.retailer_id -> retailers.retailer_id
  FK: sales.product_id -> products.product_id
  FK: inventory.product_id -> products.product_id
  FK: inventory.distributor_id -> distributors.distributor_id
"""

# ── Fixture: mock all DB I/O for pipeline E2E eval ────────────────


@pytest.fixture
def db_io_mocked():
    """Patch DB I/O so LLM agents run for real without a live database.

    Mocks:
      - MongoDB chat history  → empty list
      - pgvector RAG lookup   → no few-shot examples
      - PostgreSQL schema     → SCHEMA_STUB (realistic FMCG DDL)
      - PostgreSQL dry-run    → always passes
      - PostgreSQL execute    → configurable via the returned namespace

    Yields a SimpleNamespace so individual tests can override run_query's
    return_value per scenario.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    run_query_mock = AsyncMock(return_value={
        "columns": ["zone", "revenue"],
        "rows": [
            ["North", 1250000],
            ["South", 980000],
            ["East", 870000],
            ["West", 760000],
        ],
        "row_count": 4,
    })

    patches = [
        patch("graph.pipeline.fetch_chat_history", AsyncMock(return_value=[])),
        patch("agents.rag_agent.retrieve_fewshots", AsyncMock(return_value=[])),
        patch("agents.schema_agent.list_tables", AsyncMock(return_value=FMCG_TABLES)),
        patch("agents.schema_agent.pull_schema", AsyncMock(return_value=SCHEMA_STUB)),
        patch("graph.pipeline.validate_dry_run", AsyncMock(return_value=(True, "Seq Scan on sales"))),
        patch("graph.pipeline.run_query", run_query_mock),
    ]

    for p in patches:
        p.start()

    yield SimpleNamespace(run_query=run_query_mock)

    for p in patches:
        p.stop()
