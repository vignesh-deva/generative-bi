"""
Seed fewshot_examples with initial NL-to-SQL corpus for FMCG supply chain.

Run: python -m db.seed_fewshots

Embeddings are generated at seed time if EMBEDDING_MODEL is configured.
If embedding generation fails, examples are inserted without embeddings
(RAG will fall back to recency-based retrieval).
"""

import asyncio

from db.database import get_pool, close_pool

FEWSHOT_EXAMPLES = [
    {
        "question": "What is the total revenue for last month?",
        "sql": (
            "SELECT SUM(s.qty_sold * s.selling_price) AS total_revenue "
            "FROM sales s "
            "WHERE s.sale_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') "
            "AND s.sale_date < DATE_TRUNC('month', CURRENT_DATE)"
        ),
    },
    {
        "question": "Show me top 10 products by revenue",
        "sql": (
            "SELECT p.name AS product, SUM(s.qty_sold * s.selling_price) AS revenue "
            "FROM sales s "
            "JOIN products p ON p.product_id = s.product_id "
            "GROUP BY p.name "
            "ORDER BY revenue DESC "
            "LIMIT 10"
        ),
    },
    {
        "question": "What is the revenue by zone?",
        "sql": (
            "SELECT z.name AS zone, SUM(s.qty_sold * s.selling_price) AS revenue "
            "FROM sales s "
            "JOIN retailers r ON r.retailer_id = s.retailer_id "
            "JOIN cities c ON c.city_id = r.city_id "
            "JOIN states st ON st.state_id = c.state_id "
            "JOIN zones z ON z.zone_id = st.zone_id "
            "GROUP BY z.name "
            "ORDER BY revenue DESC"
        ),
    },
    {
        "question": "Which category has the highest gross margin?",
        "sql": (
            "SELECT cat.name AS category, "
            "ROUND(100.0 * SUM(s.qty_sold * (s.selling_price - p.cost_price)) "
            "/ NULLIF(SUM(s.qty_sold * s.selling_price), 0), 2) AS gross_margin_pct "
            "FROM sales s "
            "JOIN products p ON p.product_id = s.product_id "
            "JOIN categories cat ON cat.category_id = p.category_id "
            "GROUP BY cat.name "
            "ORDER BY gross_margin_pct DESC "
            "LIMIT 1"
        ),
    },
    {
        "question": "Show monthly sales trend for the last 6 months",
        "sql": (
            "SELECT DATE_TRUNC('month', s.sale_date)::DATE AS month, "
            "SUM(s.qty_sold * s.selling_price) AS revenue, "
            "SUM(s.qty_sold) AS units_sold "
            "FROM sales s "
            "WHERE s.sale_date >= CURRENT_DATE - INTERVAL '6 months' "
            "GROUP BY month "
            "ORDER BY month"
        ),
    },
    {
        "question": "What is the order fulfillment rate?",
        "sql": (
            "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Fulfilled') "
            "/ NULLIF(COUNT(*), 0), 2) AS fulfillment_rate_pct "
            "FROM orders"
        ),
    },
    {
        "question": "Top 5 distributors by order volume",
        "sql": (
            "SELECT d.name AS distributor, COUNT(o.order_id) AS order_count "
            "FROM orders o "
            "JOIN distributors d ON d.distributor_id = o.distributor_id "
            "GROUP BY d.name "
            "ORDER BY order_count DESC "
            "LIMIT 5"
        ),
    },
    {
        "question": "What is the average delivery time by zone?",
        "sql": (
            "SELECT z.name AS zone, "
            "ROUND(AVG(sh.delivered_date - sh.ship_date), 1) AS avg_delivery_days "
            "FROM shipments sh "
            "JOIN orders o ON o.order_id = sh.order_id "
            "JOIN distributors d ON d.distributor_id = o.distributor_id "
            "JOIN cities c ON c.city_id = d.city_id "
            "JOIN states st ON st.state_id = c.state_id "
            "JOIN zones z ON z.zone_id = st.zone_id "
            "WHERE sh.delivered_date IS NOT NULL "
            "GROUP BY z.name "
            "ORDER BY avg_delivery_days"
        ),
    },
    {
        "question": "Show current inventory levels by product category",
        "sql": (
            "WITH latest AS ( "
            "  SELECT product_id, distributor_id, stock_qty, "
            "  ROW_NUMBER() OVER (PARTITION BY product_id, distributor_id ORDER BY snapshot_date DESC) AS rn "
            "  FROM inventory "
            ") "
            "SELECT cat.name AS category, SUM(l.stock_qty) AS total_stock "
            "FROM latest l "
            "JOIN products p ON p.product_id = l.product_id "
            "JOIN categories cat ON cat.category_id = p.category_id "
            "WHERE l.rn = 1 "
            "GROUP BY cat.name "
            "ORDER BY total_stock DESC"
        ),
    },
    {
        "question": "Compare revenue between Modern Trade and General Trade",
        "sql": (
            "SELECT r.retailer_type, SUM(s.qty_sold * s.selling_price) AS revenue "
            "FROM sales s "
            "JOIN retailers r ON r.retailer_id = s.retailer_id "
            "WHERE r.retailer_type IN ('Modern Trade', 'General Trade') "
            "GROUP BY r.retailer_type "
            "ORDER BY revenue DESC"
        ),
    },
    {
        "question": "Which state has the most retailers?",
        "sql": (
            "SELECT st.name AS state, COUNT(r.retailer_id) AS retailer_count "
            "FROM retailers r "
            "JOIN cities c ON c.city_id = r.city_id "
            "JOIN states st ON st.state_id = c.state_id "
            "GROUP BY st.name "
            "ORDER BY retailer_count DESC "
            "LIMIT 1"
        ),
    },
    {
        "question": "What is the fill rate for orders this quarter?",
        "sql": (
            "SELECT ROUND(100.0 * SUM(si.shipped_qty) / NULLIF(SUM(oi.ordered_qty), 0), 2) AS fill_rate_pct "
            "FROM orders o "
            "JOIN order_items oi ON oi.order_id = o.order_id "
            "JOIN shipments sh ON sh.order_id = o.order_id "
            "JOIN shipment_items si ON si.shipment_id = sh.shipment_id AND si.product_id = oi.product_id "
            "WHERE o.order_date >= DATE_TRUNC('quarter', CURRENT_DATE)"
        ),
    },
    {
        "question": "Revenue by brand for the Beverages category",
        "sql": (
            "SELECT p.brand, SUM(s.qty_sold * s.selling_price) AS revenue "
            "FROM sales s "
            "JOIN products p ON p.product_id = s.product_id "
            "JOIN categories cat ON cat.category_id = p.category_id "
            "WHERE cat.name = 'Beverages' "
            "GROUP BY p.brand "
            "ORDER BY revenue DESC"
        ),
    },
    {
        "question": "Show me the cancelled orders with their distributor names",
        "sql": (
            "SELECT o.order_id, d.name AS distributor, o.order_date, o.expected_delivery "
            "FROM orders o "
            "JOIN distributors d ON d.distributor_id = o.distributor_id "
            "WHERE o.status = 'Cancelled' "
            "ORDER BY o.order_date DESC "
            "LIMIT 50"
        ),
    },
    {
        "question": "What is the average selling price per unit by category?",
        "sql": (
            "SELECT cat.name AS category, "
            "ROUND(SUM(s.qty_sold * s.selling_price) / NULLIF(SUM(s.qty_sold), 0), 2) AS avg_selling_price "
            "FROM sales s "
            "JOIN products p ON p.product_id = s.product_id "
            "JOIN categories cat ON cat.category_id = p.category_id "
            "GROUP BY cat.name "
            "ORDER BY avg_selling_price DESC"
        ),
    },
]


async def seed():
    pool = await get_pool()

    # Try to generate embeddings
    embeddings = [None] * len(FEWSHOT_EXAMPLES)
    try:
        from agents.tools.rag_tools import get_embedding
        for i, ex in enumerate(FEWSHOT_EXAMPLES):
            embeddings[i] = await get_embedding(ex["question"])
            print(f"  Generated embedding {i+1}/{len(FEWSHOT_EXAMPLES)}")
    except Exception as e:
        print(f"  Embedding generation failed ({e}), seeding without embeddings")
        embeddings = [None] * len(FEWSHOT_EXAMPLES)

    async with pool.acquire() as conn:
        # Clear existing seed data
        await conn.execute(
            "DELETE FROM fewshot_examples WHERE source = 'manual'"
        )

        for ex, emb in zip(FEWSHOT_EXAMPLES, embeddings):
            if emb is not None:
                await conn.execute(
                    "INSERT INTO fewshot_examples (question, sql_query, embedding, source) "
                    "VALUES ($1, $2, $3::vector, 'manual')",
                    ex["question"], ex["sql"], str(emb),
                )
            else:
                await conn.execute(
                    "INSERT INTO fewshot_examples (question, sql_query, source) "
                    "VALUES ($1, $2, 'manual')",
                    ex["question"], ex["sql"],
                )

    print(f"Seeded {len(FEWSHOT_EXAMPLES)} few-shot examples")


async def main():
    try:
        await seed()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
