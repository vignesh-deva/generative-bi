from fastapi import APIRouter

from db.database import execute_query

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/total-revenue")
async def total_revenue():
    result = await execute_query(
        "SELECT COALESCE(SUM(qty_sold * selling_price), 0) AS total_revenue FROM sales"
    )
    return {"total_revenue": float(result["rows"][0][0]) if result["rows"] else 0}


@router.get("/total-orders")
async def total_orders():
    result = await execute_query("SELECT COUNT(*) AS total_orders FROM orders")
    return {"total_orders": result["rows"][0][0] if result["rows"] else 0}


@router.get("/avg-order-value")
async def avg_order_value():
    result = await execute_query("""
        SELECT COALESCE(ROUND(AVG(order_total), 2), 0) AS avg_order_value
        FROM (
            SELECT o.order_id, SUM(oi.ordered_qty * oi.unit_price) AS order_total
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY o.order_id
        ) sub
    """)
    return {"avg_order_value": float(result["rows"][0][0]) if result["rows"] else 0}


@router.get("/revenue-by-category")
async def revenue_by_category():
    result = await execute_query("""
        SELECT c.name AS category, SUM(s.qty_sold * s.selling_price) AS revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        GROUP BY c.name
        ORDER BY revenue DESC
    """)
    return [
        {"category": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/monthly-sales-trend")
async def monthly_sales_trend():
    result = await execute_query("""
        SELECT TO_CHAR(sale_date, 'YYYY-MM') AS month,
               SUM(qty_sold * selling_price) AS revenue
        FROM sales
        GROUP BY TO_CHAR(sale_date, 'YYYY-MM')
        ORDER BY month
    """)
    return [
        {"month": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/top-products")
async def top_products():
    result = await execute_query("""
        SELECT p.name AS product, SUM(s.qty_sold * s.selling_price) AS revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT 10
    """)
    return [
        {"product": row[0], "revenue": float(row[1])} for row in result["rows"]
    ]


@router.get("/sales-by-zone")
async def sales_by_zone():
    result = await execute_query("""
        SELECT z.name AS zone, SUM(s.qty_sold * s.selling_price) AS revenue
        FROM sales s
        JOIN retailers r ON s.retailer_id = r.retailer_id
        JOIN cities ci ON r.city_id = ci.city_id
        JOIN states st ON ci.state_id = st.state_id
        JOIN zones z ON st.zone_id = z.zone_id
        GROUP BY z.name
        ORDER BY revenue DESC
    """)
    return [{"zone": row[0], "revenue": float(row[1])} for row in result["rows"]]


@router.get("/order-fulfillment")
async def order_fulfillment():
    result = await execute_query("""
        SELECT status, COUNT(*) AS count
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """)
    return [{"status": row[0], "count": row[1]} for row in result["rows"]]


@router.get("/inventory-by-category")
async def inventory_by_category():
    result = await execute_query("""
        SELECT c.name AS category, SUM(i.stock_qty) AS stock
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE i.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory)
        GROUP BY c.name
        ORDER BY stock DESC
    """)
    return [{"category": row[0], "stock": row[1]} for row in result["rows"]]
