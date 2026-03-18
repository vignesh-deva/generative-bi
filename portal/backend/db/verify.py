"""
Post-seed verification script for Generative BI Agent.

Connects to the live PostgreSQL DB and runs:
  1. Row count checks  — every table has expected minimums
  2. Integrity checks  — no orphaned FKs, no nulls in required fields
  3. Analytical queries — sample NL→SQL-style queries to confirm the data
                          is meaningful (same queries the agent would generate)

Run from portal/backend/:
    python -m db.verify

Or directly:
    python portal/backend/db/verify.py
"""

import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:change-me@localhost:5432/genbi")

PASS = "\033[32m PASS\033[0m"
FAIL = "\033[31m FAIL\033[0m"


def _result(label: str, passed: bool, detail: str = "") -> bool:
    icon = PASS if passed else FAIL
    print(f"  [{icon}] {label}" + (f" — {detail}" if detail else ""))
    return passed


# ── 1. Row Count Checks ───────────────────────────────────────────────────────

ROW_COUNT_MINIMUMS = {
    "categories":      3,
    "products":       60,
    "zones":           4,
    "states":         13,
    "cities":         30,
    "distributors":   15,
    "wholesalers":    40,
    "retailers":     150,
    "orders":        500,
    "order_items":  1500,
    "shipments":     400,
    "shipment_items":1200,
    "sales":        50_000,
    "inventory":     5_000,
}

async def check_row_counts(conn) -> int:
    print("\n[1] Row Count Checks")
    failures = 0
    for table, minimum in ROW_COUNT_MINIMUMS.items():
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        passed = count >= minimum
        if not _result(f"{table}: {count:,} rows (min {minimum:,})", passed):
            failures += 1
    return failures


# ── 2. Integrity Checks ───────────────────────────────────────────────────────

async def check_integrity(conn) -> int:
    print("\n[2] Integrity Checks")
    failures = 0

    checks = [
        (
            "No products with NULL category",
            "SELECT COUNT(*) FROM products WHERE category_id IS NULL",
            0,
        ),
        (
            "No order_items referencing missing orders",
            "SELECT COUNT(*) FROM order_items oi "
            "LEFT JOIN orders o ON oi.order_id = o.order_id "
            "WHERE o.order_id IS NULL",
            0,
        ),
        (
            "No shipment_items referencing missing shipments",
            "SELECT COUNT(*) FROM shipment_items si "
            "LEFT JOIN shipments s ON si.shipment_id = s.shipment_id "
            "WHERE s.shipment_id IS NULL",
            0,
        ),
        (
            "No sales referencing missing retailers",
            "SELECT COUNT(*) FROM sales s "
            "LEFT JOIN retailers r ON s.retailer_id = r.retailer_id "
            "WHERE r.retailer_id IS NULL",
            0,
        ),
        (
            "No sales referencing missing products",
            "SELECT COUNT(*) FROM sales s "
            "LEFT JOIN products p ON s.product_id = p.product_id "
            "WHERE p.product_id IS NULL",
            0,
        ),
        (
            "No inventory referencing missing distributors",
            "SELECT COUNT(*) FROM inventory i "
            "LEFT JOIN distributors d ON i.distributor_id = d.distributor_id "
            "WHERE d.distributor_id IS NULL",
            0,
        ),
        (
            "All order statuses are valid",
            "SELECT COUNT(*) FROM orders "
            "WHERE status NOT IN ('Pending','Fulfilled','Partial','Cancelled')",
            0,
        ),
        (
            "All retailer types are valid",
            "SELECT COUNT(*) FROM retailers "
            "WHERE retailer_type NOT IN ('General Trade','Modern Trade','E-Commerce')",
            0,
        ),
        (
            "Sales dates within 2025",
            "SELECT COUNT(*) FROM sales "
            "WHERE sale_date < '2025-01-01' OR sale_date > '2025-12-31'",
            0,
        ),
        (
            "No negative stock in inventory",
            "SELECT COUNT(*) FROM inventory WHERE stock_qty < 0",
            0,
        ),
        (
            "No zero or negative selling prices",
            "SELECT COUNT(*) FROM sales WHERE selling_price <= 0",
            0,
        ),
    ]

    for label, query, expected in checks:
        result = await conn.fetchval(query)
        passed = result == expected
        detail = f"got {result}" if not passed else ""
        if not _result(label, passed, detail):
            failures += 1

    return failures


# ── 3. Analytical Queries ─────────────────────────────────────────────────────

async def check_analytical(conn) -> int:
    """
    Sample queries mirroring real NL→SQL questions the agent would handle.
    These verify the data produces meaningful, non-trivial results.
    """
    print("\n[3] Analytical Query Checks")
    failures = 0

    # 3a. Top 5 products by revenue
    rows = await conn.fetch("""
        SELECT p.name, SUM(s.qty_sold * s.selling_price) AS revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT 5
    """)
    passed = len(rows) == 5 and all(r["revenue"] > 0 for r in rows)
    _result("Top 5 products by revenue returns 5 rows with positive revenue", passed,
            f"top: {rows[0]['name']} ₹{rows[0]['revenue']:,.0f}" if rows else "no rows")
    if not passed:
        failures += 1

    # 3b. Monthly sales trend for Beverages
    rows = await conn.fetch("""
        SELECT DATE_TRUNC('month', s.sale_date) AS month,
               SUM(s.qty_sold) AS units_sold
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE c.name = 'Beverages'
          AND s.sale_date BETWEEN '2025-01-01' AND '2025-12-31'
        GROUP BY month
        ORDER BY month
    """)
    passed = len(rows) == 12
    _result("Monthly Beverages sales trend has 12 months", passed,
            f"got {len(rows)} months")
    if not passed:
        failures += 1

    # 3c. Seasonal peak — Beverages summer (Apr–Jun) should outsell winter (Nov–Jan)
    summer = await conn.fetchval("""
        SELECT SUM(s.qty_sold)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE c.name = 'Beverages'
          AND EXTRACT(MONTH FROM s.sale_date) IN (4, 5, 6)
    """)
    winter = await conn.fetchval("""
        SELECT SUM(s.qty_sold)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE c.name = 'Beverages'
          AND EXTRACT(MONTH FROM s.sale_date) IN (11, 12, 1)
    """)
    passed = summer > winter
    _result("Beverages summer sales > winter sales (seasonality check)",
            passed, f"summer={summer:,} winter={winter:,}")
    if not passed:
        failures += 1

    # 3d. Snacks festive peak — Oct/Nov should outsell Feb/Mar
    festive = await conn.fetchval("""
        SELECT SUM(s.qty_sold)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE c.name = 'Snacks'
          AND EXTRACT(MONTH FROM s.sale_date) IN (10, 11)
    """)
    offpeak = await conn.fetchval("""
        SELECT SUM(s.qty_sold)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE c.name = 'Snacks'
          AND EXTRACT(MONTH FROM s.sale_date) IN (2, 3)
    """)
    passed = festive > offpeak
    _result("Snacks festive (Oct/Nov) sales > off-peak (Feb/Mar)",
            passed, f"festive={festive:,} off-peak={offpeak:,}")
    if not passed:
        failures += 1

    # 3e. Order fulfilment rate
    total     = await conn.fetchval("SELECT COUNT(*) FROM orders")
    fulfilled = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'Fulfilled'")
    rate      = fulfilled / total if total else 0
    passed    = 0.65 <= rate <= 0.85
    _result(f"Order fulfilment rate in expected range 65–85%",
            passed, f"{rate:.1%} ({fulfilled}/{total})")
    if not passed:
        failures += 1

    # 3f. Zone coverage — all 4 zones have sales
    zones_with_sales = await conn.fetchval("""
        SELECT COUNT(DISTINCT z.zone_id)
        FROM sales s
        JOIN retailers r  ON s.retailer_id = r.retailer_id
        JOIN cities ci    ON r.city_id      = ci.city_id
        JOIN states st    ON ci.state_id    = st.state_id
        JOIN zones z      ON st.zone_id     = z.zone_id
    """)
    passed = zones_with_sales == 4
    _result("All 4 zones (North/South/East/West) have sales data",
            passed, f"{zones_with_sales}/4 zones covered")
    if not passed:
        failures += 1

    # 3g. Distributor with highest inventory
    row = await conn.fetchrow("""
        SELECT d.name, SUM(i.stock_qty) AS total_stock
        FROM inventory i
        JOIN distributors d ON i.distributor_id = d.distributor_id
        GROUP BY d.name
        ORDER BY total_stock DESC
        LIMIT 1
    """)
    passed = row is not None and row["total_stock"] > 0
    _result("Top distributor by inventory stock returns a result",
            passed, f"{row['name']}: {row['total_stock']:,} units" if row else "no rows")
    if not passed:
        failures += 1

    # 3h. Gross margin check — selling price should generally be <= MRP
    over_mrp = await conn.fetchval("""
        SELECT COUNT(*)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        WHERE s.selling_price > p.mrp * 1.05  -- allow 5% tolerance
    """)
    passed = over_mrp == 0
    _result("No sales at more than 5% above MRP", passed,
            f"{over_mrp} violations" if not passed else "")
    if not passed:
        failures += 1

    return failures


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(POSTGRES_URI)

    total_failures = 0
    total_failures += await check_row_counts(conn)
    total_failures += await check_integrity(conn)
    total_failures += await check_analytical(conn)

    await conn.close()

    print(f"\n{'─' * 50}")
    if total_failures == 0:
        print("\033[32mAll checks passed. Database is ready.\033[0m")
        sys.exit(0)
    else:
        print(f"\033[31m{total_failures} check(s) failed. Review output above.\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
