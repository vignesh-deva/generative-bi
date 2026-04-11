from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import execute_query

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class ChartMeta(BaseModel):
    chart_id: str
    title: str
    description: str
    chart_type: str  # "kpi" | "bar" | "line" | "pie" | "donut"
    sql_query: str


# Single source of truth for chart SQL. Endpoints below read from this registry
# so the /charts/metadata endpoint and the chat "chart context" feature never
# drift apart.
CHART_REGISTRY: list[ChartMeta] = [
    ChartMeta(
        chart_id="total-revenue",
        title="Total Revenue",
        description="Total revenue across all sales.",
        chart_type="kpi",
        sql_query="SELECT COALESCE(SUM(qty_sold * selling_price), 0) AS total_revenue FROM sales",
    ),
    ChartMeta(
        chart_id="total-orders",
        title="Total Orders",
        description="Total number of orders placed.",
        chart_type="kpi",
        sql_query="SELECT COUNT(*) AS total_orders FROM orders",
    ),
    ChartMeta(
        chart_id="avg-order-value",
        title="Average Order Value",
        description="Average value of an order across all order line items.",
        chart_type="kpi",
        sql_query="""SELECT COALESCE(ROUND(AVG(order_total), 2), 0) AS avg_order_value
FROM (
    SELECT o.order_id, SUM(oi.ordered_qty * oi.unit_price) AS order_total
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id
) sub""",
    ),
    ChartMeta(
        chart_id="revenue-by-category",
        title="Revenue by Category",
        description="Total sales revenue broken down by product category.",
        chart_type="bar",
        sql_query="""SELECT c.name AS category, SUM(s.qty_sold * s.selling_price) AS revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
GROUP BY c.name
ORDER BY revenue DESC""",
    ),
    ChartMeta(
        chart_id="monthly-sales-trend",
        title="Monthly Sales Trend",
        description="Sales revenue aggregated by month.",
        chart_type="line",
        sql_query="""SELECT TO_CHAR(sale_date, 'YYYY-MM') AS month,
       SUM(qty_sold * selling_price) AS revenue
FROM sales
GROUP BY TO_CHAR(sale_date, 'YYYY-MM')
ORDER BY month""",
    ),
    ChartMeta(
        chart_id="top-products",
        title="Top 10 Products by Revenue",
        description="The top ten products ranked by total sales revenue.",
        chart_type="bar",
        sql_query="""SELECT p.name AS product, SUM(s.qty_sold * s.selling_price) AS revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.name
ORDER BY revenue DESC
LIMIT 10""",
    ),
    ChartMeta(
        chart_id="sales-by-zone",
        title="Sales by Zone",
        description="Sales revenue broken down by geographic zone.",
        chart_type="donut",
        sql_query="""SELECT z.name AS zone, SUM(s.qty_sold * s.selling_price) AS revenue
FROM sales s
JOIN retailers r ON s.retailer_id = r.retailer_id
JOIN cities ci ON r.city_id = ci.city_id
JOIN states st ON ci.state_id = st.state_id
JOIN zones z ON st.zone_id = z.zone_id
GROUP BY z.name
ORDER BY revenue DESC""",
    ),
    ChartMeta(
        chart_id="order-fulfillment",
        title="Order Fulfillment Status",
        description="Count of orders grouped by their fulfillment status.",
        chart_type="bar",
        sql_query="""SELECT status, COUNT(*) AS count
FROM orders
GROUP BY status
ORDER BY count DESC""",
    ),
    ChartMeta(
        chart_id="inventory-by-category",
        title="Inventory Levels by Category",
        description="Latest inventory stock levels broken down by product category.",
        chart_type="bar",
        sql_query="""SELECT c.name AS category, SUM(i.stock_qty) AS stock
FROM inventory i
JOIN products p ON i.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
WHERE i.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory)
GROUP BY c.name
ORDER BY stock DESC""",
    ),
]


_CHART_BY_ID: dict[str, ChartMeta] = {c.chart_id: c for c in CHART_REGISTRY}


def get_chart_sql(chart_id: str) -> str:
    chart = _CHART_BY_ID.get(chart_id)
    if chart is None:
        raise HTTPException(status_code=404, detail=f"Unknown chart: {chart_id}")
    return chart.sql_query


def get_chart_meta(chart_id: str) -> ChartMeta | None:
    return _CHART_BY_ID.get(chart_id)


@router.get("/charts/metadata", response_model=list[ChartMeta])
async def list_charts_metadata() -> list[ChartMeta]:
    """Return all available charts with their id, title, and SQL query.

    Used by the chat input's slash-command chart picker so users can attach a
    chart as context to their message.
    """
    return CHART_REGISTRY


@router.get("/total-revenue")
async def total_revenue():
    result = await execute_query(get_chart_sql("total-revenue"))
    return {"total_revenue": float(result["rows"][0][0]) if result["rows"] else 0}


@router.get("/total-orders")
async def total_orders():
    result = await execute_query(get_chart_sql("total-orders"))
    return {"total_orders": result["rows"][0][0] if result["rows"] else 0}


@router.get("/avg-order-value")
async def avg_order_value():
    result = await execute_query(get_chart_sql("avg-order-value"))
    return {"avg_order_value": float(result["rows"][0][0]) if result["rows"] else 0}


@router.get("/revenue-by-category")
async def revenue_by_category():
    result = await execute_query(get_chart_sql("revenue-by-category"))
    return [
        {"category": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/monthly-sales-trend")
async def monthly_sales_trend():
    result = await execute_query(get_chart_sql("monthly-sales-trend"))
    return [
        {"month": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/top-products")
async def top_products():
    result = await execute_query(get_chart_sql("top-products"))
    return [
        {"product": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/sales-by-zone")
async def sales_by_zone():
    result = await execute_query(get_chart_sql("sales-by-zone"))
    return [{"zone": row[0], "revenue": float(row[1])} for row in result["rows"]]


@router.get("/order-fulfillment")
async def order_fulfillment():
    result = await execute_query(get_chart_sql("order-fulfillment"))
    return [{"status": row[0], "count": row[1]} for row in result["rows"]]


@router.get("/inventory-by-category")
async def inventory_by_category():
    result = await execute_query(get_chart_sql("inventory-by-category"))
    return [{"category": row[0], "stock": row[1]} for row in result["rows"]]
