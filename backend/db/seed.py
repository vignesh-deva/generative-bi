"""
Seed script for Generative BI Agent — FMCG Supply Chain
Generates 12 months of mock data (Jan–Dec 2025) for Indian F&B market.
Run: python -m backend.db.seed  (from project root)
"""

import sqlite3
import random
import uuid
import pathlib
from datetime import date, timedelta
from faker import Faker

fake = Faker("en_IN")
random.seed(42)

DB_PATH = pathlib.Path("data/genbi.db")
SCHEMA_PATH = pathlib.Path("data/migrations/001_initial_schema.sql")
START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)


# ── Helpers ──────────────────────────────────────────────────────────────────

def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def seasonal_multiplier(d: date, category: str) -> float:
    """Return a sales volume multiplier based on category and month."""
    m = d.month
    if category == "Beverages":
        # Summer peak Mar–Jun, dip Nov–Jan
        return {1: 0.6, 2: 0.8, 3: 1.2, 4: 1.5, 5: 1.6, 6: 1.4,
                7: 1.1, 8: 1.0, 9: 0.9, 10: 0.8, 11: 0.7, 12: 0.6}[m]
    elif category == "Snacks":
        # Festive peak Oct–Nov (Navratri/Diwali), moderate rest
        return {1: 0.8, 2: 0.8, 3: 0.9, 4: 0.9, 5: 0.9, 6: 0.9,
                7: 1.0, 8: 1.0, 9: 1.1, 10: 1.5, 11: 1.6, 12: 1.1}[m]
    else:  # Dairy & Ready-to-eat
        # Steady with mild festive bump
        return {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
                7: 1.0, 8: 1.0, 9: 1.0, 10: 1.2, 11: 1.2, 12: 1.1}[m]


# ── Static Master Data ────────────────────────────────────────────────────────

CATEGORIES = ["Beverages", "Snacks", "Dairy & Ready-to-eat"]

PRODUCTS = [
    # (category, sku, name, brand, unit, mrp, cost_price)
    # Beverages
    ("Beverages", "BEV-001", "Mango Frooti", "Parle Agro", "200ml", 15.0, 8.0),
    ("Beverages", "BEV-002", "Mango Frooti", "Parle Agro", "500ml", 30.0, 16.0),
    ("Beverages", "BEV-003", "Appy Fizz", "Parle Agro", "250ml", 20.0, 11.0),
    ("Beverages", "BEV-004", "Real Orange Juice", "Dabur", "1L", 120.0, 65.0),
    ("Beverages", "BEV-005", "Real Mixed Fruit", "Dabur", "1L", 120.0, 65.0),
    ("Beverages", "BEV-006", "Real Guava Juice", "Dabur", "500ml", 65.0, 35.0),
    ("Beverages", "BEV-007", "Tropicana Orange", "PepsiCo", "1L", 130.0, 70.0),
    ("Beverages", "BEV-008", "Tropicana Cranberry", "PepsiCo", "1L", 140.0, 75.0),
    ("Beverages", "BEV-009", "Kinley Water", "Coca-Cola", "1L", 20.0, 8.0),
    ("Beverages", "BEV-010", "Kinley Water", "Coca-Cola", "500ml", 15.0, 6.0),
    ("Beverages", "BEV-011", "Bisleri Water", "Bisleri", "1L", 20.0, 8.0),
    ("Beverages", "BEV-012", "Bisleri Water", "Bisleri", "500ml", 15.0, 6.0),
    ("Beverages", "BEV-013", "Red Bull Energy", "Red Bull", "250ml", 125.0, 70.0),
    ("Beverages", "BEV-014", "Monster Energy", "Monster", "500ml", 135.0, 75.0),
    ("Beverages", "BEV-015", "Limca", "Coca-Cola", "300ml", 20.0, 10.0),
    ("Beverages", "BEV-016", "Maaza Mango", "Coca-Cola", "250ml", 20.0, 10.0),
    ("Beverages", "BEV-017", "Slice Mango", "PepsiCo", "250ml", 20.0, 10.0),
    ("Beverages", "BEV-018", "Paper Boat Aamras", "Hector", "250ml", 30.0, 16.0),
    ("Beverages", "BEV-019", "Paper Boat Jaljeera", "Hector", "250ml", 30.0, 16.0),
    ("Beverages", "BEV-020", "Nimbuzz Lemon Drink", "Rasna", "500ml", 25.0, 12.0),
    # Snacks
    ("Snacks", "SNK-001", "Lays Classic Salted", "PepsiCo", "26g", 20.0, 11.0),
    ("Snacks", "SNK-002", "Lays Cream & Onion", "PepsiCo", "26g", 20.0, 11.0),
    ("Snacks", "SNK-003", "Lays Magic Masala", "PepsiCo", "26g", 20.0, 11.0),
    ("Snacks", "SNK-004", "Kurkure Masala Munch", "PepsiCo", "90g", 30.0, 16.0),
    ("Snacks", "SNK-005", "Kurkure Green Chutney", "PepsiCo", "90g", 30.0, 16.0),
    ("Snacks", "SNK-006", "Bingo Mad Angles", "ITC", "75g", 30.0, 16.0),
    ("Snacks", "SNK-007", "Bingo Original Style", "ITC", "75g", 30.0, 16.0),
    ("Snacks", "SNK-008", "Haldiram Aloo Bhujia", "Haldiram", "200g", 80.0, 42.0),
    ("Snacks", "SNK-009", "Haldiram Mixture", "Haldiram", "200g", 75.0, 40.0),
    ("Snacks", "SNK-010", "Haldiram Moong Dal", "Haldiram", "200g", 75.0, 40.0),
    ("Snacks", "SNK-011", "Parle-G Biscuits", "Parle", "100g", 10.0, 5.0),
    ("Snacks", "SNK-012", "Good Day Butter", "Britannia", "100g", 30.0, 16.0),
    ("Snacks", "SNK-013", "Good Day Cashew", "Britannia", "100g", 35.0, 18.0),
    ("Snacks", "SNK-014", "Oreo Original", "Mondelez", "120g", 40.0, 21.0),
    ("Snacks", "SNK-015", "Hide & Seek", "Parle", "100g", 30.0, 16.0),
    ("Snacks", "SNK-016", "Too Yumm Multigrain", "RP-SG", "55g", 20.0, 10.0),
    ("Snacks", "SNK-017", "Cornitos Nachos", "Cornitos", "60g", 30.0, 16.0),
    ("Snacks", "SNK-018", "Lay's Wafer Thin", "PepsiCo", "55g", 30.0, 15.0),
    ("Snacks", "SNK-019", "Bikaji Bikaneri Bhujia", "Bikaji", "200g", 85.0, 45.0),
    ("Snacks", "SNK-020", "Balaji Wafers", "Balaji", "100g", 20.0, 10.0),
    # Dairy & Ready-to-eat
    ("Dairy & Ready-to-eat", "DRY-001", "Amul Kool Koko", "Amul", "200ml", 30.0, 16.0),
    ("Dairy & Ready-to-eat", "DRY-002", "Amul Kool Rose", "Amul", "200ml", 30.0, 16.0),
    ("Dairy & Ready-to-eat", "DRY-003", "Amul Mango Milk", "Amul", "200ml", 30.0, 16.0),
    ("Dairy & Ready-to-eat", "DRY-004", "Nestle Milo", "Nestle", "200ml", 35.0, 18.0),
    ("Dairy & Ready-to-eat", "DRY-005", "Britannia Cheese Slice", "Britannia", "200g", 110.0, 58.0),
    ("Dairy & Ready-to-eat", "DRY-006", "Maggi 2-Minute Noodles", "Nestle", "70g", 14.0, 7.0),
    ("Dairy & Ready-to-eat", "DRY-007", "Maggi Masala Noodles", "Nestle", "140g", 28.0, 14.0),
    ("Dairy & Ready-to-eat", "DRY-008", "Yippee Noodles Magic Masala", "ITC", "70g", 14.0, 7.0),
    ("Dairy & Ready-to-eat", "DRY-009", "Kellogg's Corn Flakes", "Kellogg's", "250g", 150.0, 80.0),
    ("Dairy & Ready-to-eat", "DRY-010", "Kellogg's Chocos", "Kellogg's", "250g", 165.0, 88.0),
    ("Dairy & Ready-to-eat", "DRY-011", "Baggry's Oats", "Baggry's", "400g", 180.0, 95.0),
    ("Dairy & Ready-to-eat", "DRY-012", "Saffola Oats", "Marico", "400g", 175.0, 92.0),
    ("Dairy & Ready-to-eat", "DRY-013", "MTR Poha", "MTR", "500g", 85.0, 44.0),
    ("Dairy & Ready-to-eat", "DRY-014", "MTR Upma Mix", "MTR", "500g", 90.0, 47.0),
    ("Dairy & Ready-to-eat", "DRY-015", "ITC Sunfeast Pasta", "ITC", "150g", 50.0, 26.0),
    ("Dairy & Ready-to-eat", "DRY-016", "Epigamia Greek Yogurt", "Epigamia", "90g", 55.0, 30.0),
    ("Dairy & Ready-to-eat", "DRY-017", "Nandini Curd", "KMF", "500g", 55.0, 28.0),
    ("Dairy & Ready-to-eat", "DRY-018", "Amul Lassi", "Amul", "200ml", 30.0, 15.0),
    ("Dairy & Ready-to-eat", "DRY-019", "B Natural Mixed Fruit", "ITC", "1L", 115.0, 60.0),
    ("Dairy & Ready-to-eat", "DRY-020", "Horlicks Classic Malt", "HUL", "500g", 290.0, 155.0),
]

GEOGRAPHY = {
    "North": {
        "Delhi": ["New Delhi", "Dwarka", "Rohini"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra"],
        "Punjab": ["Ludhiana", "Amritsar"],
        "Haryana": ["Gurugram", "Faridabad"],
    },
    "South": {
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
        "Karnataka": ["Bengaluru", "Mysuru"],
        "Telangana": ["Hyderabad", "Warangal"],
        "Kerala": ["Kochi", "Thiruvananthapuram"],
    },
    "East": {
        "West Bengal": ["Kolkata", "Howrah", "Durgapur"],
        "Odisha": ["Bhubaneswar", "Cuttack"],
        "Bihar": ["Patna", "Gaya"],
    },
    "West": {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara"],
        "Rajasthan": ["Jaipur", "Jodhpur"],
    },
}

RETAILER_TYPES = ["General Trade", "Modern Trade", "E-Commerce"]
RETAILER_TYPE_WEIGHTS = [0.65, 0.25, 0.10]


# ── Seed Functions ────────────────────────────────────────────────────────────

def seed_categories(con):
    rows = [(name,) for name in CATEGORIES]
    con.executemany("INSERT INTO categories (name) VALUES (?)", rows)
    return {name: i + 1 for i, name in enumerate(CATEGORIES)}


def seed_products(con, cat_id_map):
    rows = [
        (cat_id_map[cat], sku, name, brand, unit, mrp, cost)
        for cat, sku, name, brand, unit, mrp, cost in PRODUCTS
    ]
    con.executemany(
        "INSERT INTO products (category_id, sku_code, name, brand, unit, mrp, cost_price) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    return {sku: i + 1 for i, (_, sku, *_rest) in enumerate(PRODUCTS)}


def seed_geography(con):
    zone_ids, state_ids, city_ids = {}, {}, {}
    for zone_name, states in GEOGRAPHY.items():
        cur = con.execute("INSERT INTO zones (name) VALUES (?)", (zone_name,))
        zone_ids[zone_name] = cur.lastrowid
        for state_name, cities in states.items():
            cur = con.execute(
                "INSERT INTO states (zone_id, name) VALUES (?,?)",
                (zone_ids[zone_name], state_name),
            )
            state_ids[state_name] = cur.lastrowid
            for city_name in cities:
                cur = con.execute(
                    "INSERT INTO cities (state_id, name) VALUES (?,?)",
                    (state_ids[state_name], city_name),
                )
                city_ids[city_name] = cur.lastrowid
    return zone_ids, state_ids, city_ids


def seed_distributors(con, city_ids, n=15):
    all_cities = list(city_ids.items())
    rows = []
    for i in range(n):
        city_name, city_id = random.choice(all_cities)
        rows.append((
            fake.company() + " Distributors",
            city_id,
            fake.name(),
            fake.phone_number()[:15],
        ))
    con.executemany(
        "INSERT INTO distributors (name, city_id, contact_name, phone) VALUES (?,?,?,?)",
        rows,
    )
    return list(range(1, n + 1))


def seed_wholesalers(con, distributor_ids, city_ids, n=40):
    all_cities = list(city_ids.items())
    rows = []
    for i in range(n):
        city_name, city_id = random.choice(all_cities)
        dist_id = random.choice(distributor_ids)
        rows.append((
            fake.company() + " Wholesale",
            dist_id,
            city_id,
            fake.name(),
            fake.phone_number()[:15],
        ))
    con.executemany(
        "INSERT INTO wholesalers (name, distributor_id, city_id, contact_name, phone) VALUES (?,?,?,?,?)",
        rows,
    )
    return list(range(1, n + 1))


def seed_retailers(con, distributor_ids, wholesaler_ids, city_ids, n=150):
    all_cities = list(city_ids.items())
    rows = []
    for i in range(n):
        city_name, city_id = random.choice(all_cities)
        dist_id = random.choice(distributor_ids)
        ws_id = random.choice(wholesaler_ids) if random.random() > 0.2 else None
        r_type = random.choices(RETAILER_TYPES, RETAILER_TYPE_WEIGHTS)[0]
        store_prefixes = {
            "General Trade": ["Kirana Store", "Provision Store", "Super Mart", "General Stores"],
            "Modern Trade": ["Big Bazaar", "DMart", "Reliance Fresh", "More Supermarket", "Star Bazaar"],
            "E-Commerce": ["Blinkit Hub", "Zepto Dark Store", "Swiggy Instamart", "Amazon Fresh"],
        }
        name = random.choice(store_prefixes[r_type]) + " " + fake.last_name()
        rows.append((name, r_type, ws_id, dist_id, city_id))
    con.executemany(
        "INSERT INTO retailers (name, retailer_type, wholesaler_id, distributor_id, city_id) VALUES (?,?,?,?,?)",
        rows,
    )
    return list(range(1, n + 1))


def seed_orders_and_shipments(con, distributor_ids, product_ids, cat_id_map):
    """Generate orders monthly per distributor, with shipments and items."""
    order_count = 0
    all_products = list(product_ids.items())  # [(sku, product_id), ...]

    # Build category lookup: product_id → category name
    prod_cat = {}
    for cat, sku, *_ in PRODUCTS:
        prod_cat[product_ids[sku]] = cat

    for month in range(1, 13):
        for dist_id in distributor_ids:
            # 3–6 orders per distributor per month
            for _ in range(random.randint(3, 6)):
                order_day = random.randint(1, 25)
                try:
                    order_date = date(2025, month, order_day)
                except ValueError:
                    order_date = date(2025, month, 25)

                lead_days = random.randint(3, 7)
                expected_delivery = order_date + timedelta(days=lead_days)

                # Determine order status with realistic distribution
                r = random.random()
                if r < 0.75:
                    status = "Fulfilled"
                elif r < 0.88:
                    status = "Partial"
                elif r < 0.95:
                    status = "Pending"
                else:
                    status = "Cancelled"

                cur = con.execute(
                    "INSERT INTO orders (distributor_id, order_date, expected_delivery, status) VALUES (?,?,?,?)",
                    (dist_id, order_date.isoformat(), expected_delivery.isoformat(), status),
                )
                order_id = cur.lastrowid
                order_count += 1

                # 3–8 products per order
                selected = random.sample(all_products, k=random.randint(3, 8))
                for sku, prod_id in selected:
                    qty = random.randint(50, 500)
                    # Get MRP for this product
                    mrp = next(p[6] for p in PRODUCTS if p[1] == sku)
                    unit_price = round(mrp * random.uniform(0.70, 0.85), 2)
                    con.execute(
                        "INSERT INTO order_items (order_id, product_id, ordered_qty, unit_price) VALUES (?,?,?,?)",
                        (order_id, prod_id, qty, unit_price),
                    )

                # Create shipment if not Cancelled or Pending
                if status in ("Fulfilled", "Partial"):
                    actual_ship = order_date + timedelta(days=random.randint(1, lead_days))
                    actual_delivery = actual_ship + timedelta(days=random.randint(1, 3))
                    cur = con.execute(
                        "INSERT INTO shipments (order_id, ship_date, delivered_date) VALUES (?,?,?)",
                        (order_id, actual_ship.isoformat(), actual_delivery.isoformat()),
                    )
                    shipment_id = cur.lastrowid

                    for sku, prod_id in selected:
                        ordered_qty = next(
                            q for oi_order_id, q in
                            con.execute(
                                "SELECT order_id, ordered_qty FROM order_items WHERE order_id=? AND product_id=?",
                                (order_id, prod_id)
                            )
                        )
                        if status == "Fulfilled":
                            shipped_qty = ordered_qty
                        else:
                            shipped_qty = int(ordered_qty * random.uniform(0.5, 0.85))
                        con.execute(
                            "INSERT INTO shipment_items (shipment_id, product_id, shipped_qty) VALUES (?,?,?)",
                            (shipment_id, prod_id, shipped_qty),
                        )

    print(f"  Orders: {order_count}")


def seed_sales(con, retailer_ids, product_ids, cat_id_map):
    """Generate daily sales per retailer for a subset of products with seasonality."""
    # Build (product_id, category) list
    prod_list = [(product_ids[sku], cat) for cat, sku, *_ in PRODUCTS]
    mrp_map = {product_ids[sku]: mrp for _, sku, _, _, _, mrp, _ in PRODUCTS}

    rows = []
    for retailer_id in retailer_ids:
        # Each retailer carries a random subset of 10–20 products
        carrying = random.sample(prod_list, k=random.randint(10, 20))

        for d in date_range(START_DATE, END_DATE):
            # Sales happen ~4 days a week per retailer
            if random.random() > 0.57:
                continue
            for prod_id, category in carrying:
                if random.random() > 0.4:
                    continue
                multiplier = seasonal_multiplier(d, category)
                base_qty = random.randint(2, 20)
                qty = max(1, int(base_qty * multiplier * random.uniform(0.7, 1.3)))
                mrp = mrp_map[prod_id]
                selling_price = round(mrp * random.uniform(0.90, 1.0), 2)
                rows.append((retailer_id, prod_id, d.isoformat(), qty, selling_price))

    con.executemany(
        "INSERT INTO sales (retailer_id, product_id, sale_date, qty_sold, selling_price) VALUES (?,?,?,?,?)",
        rows,
    )
    print(f"  Sales records: {len(rows)}")


def seed_inventory(con, distributor_ids, product_ids):
    """Generate weekly inventory snapshots per distributor per product."""
    prod_ids = list(product_ids.values())
    rows = []

    snapshot_dates = []
    d = START_DATE
    while d <= END_DATE:
        snapshot_dates.append(d)
        d += timedelta(weeks=1)

    for dist_id in distributor_ids:
        carrying = random.sample(prod_ids, k=random.randint(30, 50))
        stock = {p: random.randint(200, 2000) for p in carrying}

        for snap_date in snapshot_dates:
            for prod_id in carrying:
                # Simulate stock movement: replenish partially, sell down
                stock[prod_id] = max(0, int(stock[prod_id] * random.uniform(0.7, 1.1)))
                # Occasional restock
                if stock[prod_id] < 100 or random.random() < 0.2:
                    stock[prod_id] += random.randint(200, 800)
                rows.append((prod_id, dist_id, snap_date.isoformat(), stock[prod_id]))

    con.executemany(
        "INSERT INTO inventory (product_id, distributor_id, snapshot_date, stock_qty) VALUES (?,?,?,?)",
        rows,
    )
    print(f"  Inventory snapshots: {len(rows)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Initialising database...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Drop and recreate for clean seed
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("  Dropped existing database.")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")

    print("Running schema migration...")
    con.executescript(SCHEMA_PATH.read_text())

    print("Seeding master data...")
    cat_id_map = seed_categories(con)
    product_ids = seed_products(con, cat_id_map)
    _, _, city_ids = seed_geography(con)
    distributor_ids = seed_distributors(con, city_ids, n=15)
    wholesaler_ids = seed_wholesalers(con, distributor_ids, city_ids, n=40)
    retailer_ids = seed_retailers(con, distributor_ids, wholesaler_ids, city_ids, n=150)
    print(f"  Categories: {len(cat_id_map)}")
    print(f"  Products: {len(product_ids)}")
    print(f"  Distributors: {len(distributor_ids)}")
    print(f"  Wholesalers: {len(wholesaler_ids)}")
    print(f"  Retailers: {len(retailer_ids)}")

    print("Seeding transactional data...")
    seed_orders_and_shipments(con, distributor_ids, product_ids, cat_id_map)
    seed_sales(con, retailer_ids, product_ids, cat_id_map)
    seed_inventory(con, distributor_ids, product_ids)

    con.commit()
    con.close()
    print("\nDone. Database ready at:", DB_PATH)


if __name__ == "__main__":
    main()
