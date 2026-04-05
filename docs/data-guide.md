# FMCG Supply Chain Data Guide

This document describes the mock dataset powering the Generative BI Agent — what's in it, how it's structured, and what kinds of questions you can ask.

---

## Dataset at a Glance

| Dimension | Detail |
|-----------|--------|
| **Period** | January – December 2025 (full calendar year) |
| **Market** | Indian FMCG — Food & Beverage |
| **Categories** | Beverages · Snacks · Dairy & Ready-to-eat |
| **Products** | 60 SKUs across 20 Beverages, 20 Snacks, 20 Dairy & RTE |
| **Geography** | 4 zones · 13 states · 30+ cities |
| **Retailers** | ~150 stores across General Trade, Modern Trade, E-Commerce |
| **Sales records** | ~178,000 sell-through transactions |
| **Currency** | Indian Rupees (INR) |
| **Perspective** | FMCG manufacturer — tracking sales through the distribution chain |

---

## Schema Overview

The PostgreSQL database has two layers: **master data** (who, what, where) and **transactional data** (what happened).

```
categories ──< products
zones ──< states ──< cities ──< distributors ──< wholesalers ──< retailers
                                distributors ──< orders ──< order_items ──< products
                                distributors ──< shipments ──< shipment_items ──< products
                                retailers ──< sales ──< products
                                distributors ──< inventory ──< products
```

### Master Data Tables

| Table | Key Columns | Description |
|-------|-------------|-------------|
| `categories` | `category_id`, `name` | 3 categories: Beverages, Snacks, Dairy & Ready-to-eat |
| `products` | `product_id`, `name`, `brand`, `sku_code`, `unit`, `mrp`, `cost_price` | 60 SKUs with pricing |
| `zones` | `zone_id`, `name` | 4 zones: North, South, East, West |
| `states` | `state_id`, `zone_id`, `name` | 13 states mapped to zones |
| `cities` | `city_id`, `state_id`, `name` | 30+ cities mapped to states |
| `distributors` | `distributor_id`, `name`, `city_id` | Distributor master |
| `wholesalers` | `wholesaler_id`, `name`, `distributor_id`, `city_id` | Wholesaler master |
| `retailers` | `retailer_id`, `name`, `retailer_type`, `city_id` | Store master with channel type |

### Transactional Data Tables

| Table | Key Columns | Description |
|-------|-------------|-------------|
| `sales` | `sale_id`, `retailer_id`, `product_id`, `sale_date`, `qty_sold`, `selling_price` | Sell-through at retailer level (~178k rows) |
| `orders` | `order_id`, `distributor_id`, `order_date`, `status` | Purchase orders from distributors |
| `order_items` | `order_item_id`, `order_id`, `product_id`, `ordered_qty`, `unit_price` | Line items per order |
| `shipments` | `shipment_id`, `order_id`, `ship_date`, `delivered_date` | Outbound shipments |
| `shipment_items` | `shipment_item_id`, `shipment_id`, `product_id`, `shipped_qty` | Line items per shipment |
| `inventory` | `inventory_id`, `product_id`, `distributor_id`, `snapshot_date`, `stock_qty` | Weekly stock snapshots |

---

## Geography

The data models an all-India FMCG distribution network:

| Zone | States | Key Cities |
|------|--------|------------|
| **North** | Delhi, Uttar Pradesh, Punjab, Haryana | New Delhi, Lucknow, Kanpur, Ludhiana, Amritsar, Gurugram |
| **South** | Tamil Nadu, Karnataka, Telangana, Kerala | Chennai, Bengaluru, Hyderabad, Kochi |
| **East** | West Bengal, Odisha, Bihar | Kolkata, Bhubaneswar, Patna |
| **West** | Maharashtra, Gujarat, Rajasthan | Mumbai, Pune, Ahmedabad, Surat, Jaipur |

---

## Product Catalogue

### Beverages (20 SKUs)

| Brand | Products |
|-------|----------|
| **Parle Agro** | Mango Frooti (200ml, 500ml), Appy Fizz (250ml) |
| **Dabur** | Real Orange Juice, Real Mixed Fruit, Real Guava Juice |
| **PepsiCo** | Tropicana Orange, Tropicana Cranberry, Slice Mango |
| **Coca-Cola** | Kinley Water (1L, 500ml), Limca, Maaza Mango |
| **Bisleri** | Bisleri Water (1L, 500ml) |
| **Red Bull / Monster** | Red Bull Energy (250ml), Monster Energy (500ml) |
| **Hector** | Paper Boat Aamras, Paper Boat Jaljeera |
| **Rasna** | Nimbuzz Lemon Drink |

**Price range:** ₹15 (Kinley 500ml) — ₹140 (Monster 500ml)

### Snacks (20 SKUs)

| Brand | Products |
|-------|----------|
| **PepsiCo** | Lays Classic Salted, Lays Cream & Onion, Lays Magic Masala, Kurkure Masala Munch, Kurkure Green Chutney, Lay's Wafer Thin |
| **ITC** | Bingo Mad Angles, Bingo Original Style |
| **Haldiram** | Aloo Bhujia, Mixture, Moong Dal |
| **Parle** | Parle-G Biscuits, Hide & Seek |
| **Britannia** | Good Day Butter, Good Day Cashew |
| **Mondelez** | Oreo Original |
| **Bikaji** | Bikaji Bikaneri Bhujia |
| **Others** | Too Yumm Multigrain, Cornitos Nachos, Balaji Wafers |

**Price range:** ₹10 (Parle-G) — ₹85 (Bikaji Bikaneri Bhujia)

### Dairy & Ready-to-eat (20 SKUs)

| Brand | Products |
|-------|----------|
| **Amul** | Kool Koko, Kool Rose, Mango Milk, Lassi |
| **Nestle** | Milo, Maggi 2-Minute Noodles, Maggi Masala Noodles |
| **ITC** | Yippee Noodles, B Natural Mixed Fruit, Sunfeast Pasta |
| **Kellogg's** | Corn Flakes (250g), Chocos (250g) |
| **Britannia** | Cheese Slice |
| **Baggry's / Marico** | Baggry's Oats, Saffola Oats |
| **MTR** | MTR Poha, MTR Upma Mix |
| **Others** | Epigamia Greek Yogurt, Nandini Curd, Horlicks Classic Malt |

**Price range:** ₹14 (Maggi 70g) — ₹290 (Horlicks 500g)

---

## Retailer Channels

| Channel | Share | Store Types |
|---------|-------|-------------|
| **General Trade** | ~65% | Kirana stores, provision stores, super marts |
| **Modern Trade** | ~25% | Big Bazaar, DMart, Reliance Fresh, More Supermarket, Star Bazaar |
| **E-Commerce** | ~10% | Blinkit, Zepto, Swiggy Instamart, Amazon Fresh |

---

## Seasonality Patterns

The data has realistic seasonal demand baked in:

| Category | Peak Season | Low Season |
|----------|-------------|------------|
| **Beverages** | April – June (summer peak, 1.5–1.6× baseline) | November – February (0.6–0.8×) |
| **Snacks** | October – November (Diwali / festival season, 1.5–1.6×) | January – March (0.8–0.9×) |
| **Dairy & RTE** | October – December (moderate uplift, 1.1–1.2×) | January – February (0.9×) |

---

## Metrics & Definitions

| Metric | How It's Calculated |
|--------|---------------------|
| **Revenue** | `qty_sold × selling_price` from the `sales` table |
| **Gross Profit** | Revenue minus `cost_price × qty_sold` from products |
| **Margin %** | `(selling_price - cost_price) / selling_price × 100` |
| **Units Sold** | `SUM(qty_sold)` from sales |
| **Order Value** | `SUM(ordered_qty × unit_price)` from order_items |
| **Fill Rate** | `shipped_qty / ordered_qty` from shipment_items vs order_items |
| **Stock Level** | `stock_qty` from the latest `snapshot_date` in inventory |

---

## Example Questions

Use these as starting points. You can also combine or follow up — the agent resolves references like "show the same for South zone" or "break it down by month."

### Sales & Revenue

```
What was the total revenue in 2025?
Show monthly revenue trend for the full year.
Which month had the highest sales?
What is the revenue split across Beverages, Snacks, and Dairy & Ready-to-eat?
Compare Q1 vs Q2 vs Q3 vs Q4 revenue.
What was the revenue in the festival months (October and November)?
Show revenue by week for Q4 2025.
```

### Products & SKUs

```
What are the top 10 best-selling products by revenue?
Which product has the highest gross margin?
Which Kellogg's product performs better — Corn Flakes or Chocos?
How many units of Parle-G Biscuits were sold in 2025?
Which Lays variant sells the most?
What is the revenue contribution of PepsiCo products?
Which products had zero sales in any month?
Show all products with MRP above ₹100.
```

### Geography & Zones

```
Which zone has the highest revenue?
Show me the revenue breakdown across all four zones.
Which city generates the most revenue in the South zone?
Compare sales between Mumbai and Delhi.
Which state has the most retailers?
Show revenue by zone for Q4 2025.
What percentage of sales come from the West zone?
```

### Channels & Retailers

```
What percentage of sales come from Modern Trade vs General Trade vs E-Commerce?
Which retailer has the highest purchase volume?
Show revenue by retailer type for each quarter.
Which E-Commerce retailers are in Bengaluru?
How many General Trade stores are active in the North zone?
```

### Distribution & Supply Chain

```
How many orders were placed in 2025?
What percentage of orders were fulfilled vs cancelled?
Which distributor has the highest order volume?
Show average delivery time (order to delivery) by zone.
Which distributors have pending orders?
Show shipment volumes by month.
```

### Inventory

```
Which products have the lowest stock levels right now?
Show inventory for Maggi Noodles across all distributors.
Which distributor has the highest inventory of Beverages?
Show stock snapshots for the West zone in December 2025.
Which products are at risk of stockout (stock below 100 units)?
```

### Trends & Seasonality

```
How do Beverage sales in summer (April–June) compare to winter (October–December)?
Show month-over-month growth rate for Snacks in 2025.
Which product category grew the most from H1 to H2 2025?
Did Red Bull sales peak in summer as expected?
Show Maggi Noodles sales trend across all 12 months.
Which zone shows the strongest October uplift?
```

### Profitability

```
Which product category has the highest average gross margin?
Show the top 5 most profitable products.
What is the total gross profit for 2025?
Compare margin % between Modern Trade and General Trade.
Which Haldiram product has a better margin — Aloo Bhujia or Mixture?
```

---

## Tips for Best Results

- **Use exact product names** when filtering — e.g., "Kellogg's Chocos" not just "Chocos"
- **Zone names** are: North, South, East, West
- **Retailer types** are: General Trade, Modern Trade, E-Commerce
- **Order statuses** are: Pending, Fulfilled, Partial, Cancelled
- **Date range** is January–December 2025 — queries about 2026 data will return no results
- For follow-ups, you can reference context — "show the same for Snacks" or "break it down by zone"
