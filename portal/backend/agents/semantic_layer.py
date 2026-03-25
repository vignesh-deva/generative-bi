"""
Semantic Layer — static knowledge base of business metrics, join paths,
business rules, and known categorical values for the FMCG supply chain database.

This is injected into the SQL Agent's context alongside schema information
to help the LLM generate accurate, business-aware queries.
"""

SEMANTIC_LAYER = {
    "metrics": [
        {
            "name": "revenue",
            "formula": "SUM(s.qty_sold * s.selling_price)",
            "tables": ["sales"],
            "note": "Use selling_price (actual transaction price), not mrp",
        },
        {
            "name": "cost_of_goods_sold (COGS)",
            "formula": "SUM(s.qty_sold * p.cost_price)",
            "tables": ["sales", "products"],
            "note": "Join sales to products for cost_price",
        },
        {
            "name": "gross_profit",
            "formula": "SUM(s.qty_sold * (s.selling_price - p.cost_price))",
            "tables": ["sales", "products"],
            "note": "Revenue minus COGS per unit",
        },
        {
            "name": "gross_margin_pct",
            "formula": "ROUND(100.0 * SUM(s.qty_sold * (s.selling_price - p.cost_price)) / NULLIF(SUM(s.qty_sold * s.selling_price), 0), 2)",
            "tables": ["sales", "products"],
            "note": "As a percentage of revenue",
        },
        {
            "name": "total_units_sold",
            "formula": "SUM(s.qty_sold)",
            "tables": ["sales"],
            "note": None,
        },
        {
            "name": "average_selling_price (ASP)",
            "formula": "ROUND(SUM(s.qty_sold * s.selling_price) / NULLIF(SUM(s.qty_sold), 0), 2)",
            "tables": ["sales"],
            "note": "Weighted average, not simple AVG(selling_price)",
        },
        {
            "name": "order_fulfillment_rate",
            "formula": "ROUND(100.0 * COUNT(*) FILTER (WHERE o.status = 'Fulfilled') / NULLIF(COUNT(*), 0), 2)",
            "tables": ["orders"],
            "note": "Percentage of orders with status 'Fulfilled'",
        },
        {
            "name": "average_delivery_days",
            "formula": "ROUND(AVG(sh.delivered_date - sh.ship_date), 1)",
            "tables": ["shipments"],
            "note": "Only for shipments where delivered_date IS NOT NULL",
        },
        {
            "name": "stock_on_hand",
            "formula": "SUM(i.stock_qty)",
            "tables": ["inventory"],
            "note": "Use latest snapshot_date for current stock",
        },
        {
            "name": "fill_rate",
            "formula": "ROUND(100.0 * SUM(si.shipped_qty) / NULLIF(SUM(oi.ordered_qty), 0), 2)",
            "tables": ["order_items", "shipment_items"],
            "note": "Shipped quantity vs ordered quantity",
        },
    ],

    "join_paths": [
        {
            "description": "Sales to product details",
            "path": "sales.product_id -> products.product_id",
            "tables": ["sales", "products"],
        },
        {
            "description": "Sales to category",
            "path": "sales -> products.product_id -> categories.category_id",
            "tables": ["sales", "products", "categories"],
        },
        {
            "description": "Sales to retailer location",
            "path": "sales.retailer_id -> retailers.retailer_id -> cities.city_id -> states.state_id -> zones.zone_id",
            "tables": ["sales", "retailers", "cities", "states", "zones"],
        },
        {
            "description": "Sales to distributor",
            "path": "sales.retailer_id -> retailers.retailer_id -> retailers.distributor_id -> distributors.distributor_id",
            "tables": ["sales", "retailers", "distributors"],
        },
        {
            "description": "Orders to distributor",
            "path": "orders.distributor_id -> distributors.distributor_id",
            "tables": ["orders", "distributors"],
        },
        {
            "description": "Orders to shipments",
            "path": "orders.order_id -> shipments.order_id",
            "tables": ["orders", "shipments"],
        },
        {
            "description": "Order items to shipment items",
            "path": "order_items.order_id = shipment_items.shipment_id (via shipments.order_id)",
            "tables": ["order_items", "shipment_items", "shipments"],
        },
        {
            "description": "Inventory to product and distributor",
            "path": "inventory.product_id -> products, inventory.distributor_id -> distributors",
            "tables": ["inventory", "products", "distributors"],
        },
        {
            "description": "Retailer to wholesaler to distributor",
            "path": "retailers.wholesaler_id -> wholesalers.wholesaler_id -> wholesalers.distributor_id -> distributors",
            "tables": ["retailers", "wholesalers", "distributors"],
        },
        {
            "description": "Distributor to city/state/zone",
            "path": "distributors.city_id -> cities -> states -> zones",
            "tables": ["distributors", "cities", "states", "zones"],
        },
    ],

    "business_rules": [
        {
            "rule": "Revenue always uses selling_price (actual transaction price), never mrp (max retail price). MRP is the ceiling price printed on the product.",
            "tables": ["sales", "products"],
        },
        {
            "rule": "For time-based comparisons, use sale_date from the sales table (not created_at).",
            "tables": ["sales"],
        },
        {
            "rule": "Inventory snapshots are point-in-time. For current stock, use the MAX(snapshot_date) per product-distributor combination.",
            "tables": ["inventory"],
        },
        {
            "rule": "Order status values are: 'Pending', 'Fulfilled', 'Partial', 'Cancelled'. These are the only valid statuses.",
            "tables": ["orders"],
        },
        {
            "rule": "Retailer types are: 'Modern Trade', 'General Trade', 'E-Commerce'. Use exact strings for filtering.",
            "tables": ["retailers"],
        },
        {
            "rule": "Zones are: 'North', 'South', 'East', 'West'. Use exact strings.",
            "tables": ["zones"],
        },
        {
            "rule": "A retailer can optionally belong to a wholesaler (wholesaler_id is nullable) but always belongs to a distributor.",
            "tables": ["retailers"],
        },
        {
            "rule": "Shipment delivered_date can be NULL (not yet delivered). Filter on IS NOT NULL when computing delivery metrics.",
            "tables": ["shipments"],
        },
        {
            "rule": "All monetary values (mrp, cost_price, selling_price, unit_price) are in INR.",
            "tables": ["products", "sales", "order_items"],
        },
    ],

    "known_values": {
        "categories.name": ["Beverages", "Snacks", "Dairy", "Ready-to-eat"],
        "zones.name": ["North", "South", "East", "West"],
        "orders.status": ["Pending", "Fulfilled", "Partial", "Cancelled"],
        "retailers.retailer_type": ["Modern Trade", "General Trade", "E-Commerce"],
        "fewshot_examples.source": ["manual", "curated"],
    },
}
