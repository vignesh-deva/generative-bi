"""
Seed script for Generative BI Agent — FMCG Supply Chain
Generates 12 months of mock data (Jan–Dec 2025) for Indian F&B market.

Run from user_portal/backend/:
    python -m db.seed

Or directly:
    python user_portal/backend/db/seed.py
"""

import asyncio
import os
import random
from datetime import date, timedelta

import asyncpg
from dotenv import load_dotenv
from faker import Faker

load_dotenv()

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://genbi:change-me@localhost:5432/genbi")

fake = Faker("en_IN")
random.seed(42)

START_DATE = date(2025, 1, 1)
END_DATE   = date(2025, 12, 31)


# ── Helpers ───────────────────────────────────────────────────────────────────

def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def seasonal_multiplier(d: date, category: str) -> float:
    m = d.month
    if category == "Beverages":
        return {1: 0.6, 2: 0.8, 3: 1.2, 4: 1.5, 5: 1.6, 6: 1.4,
                7: 1.1, 8: 1.0, 9: 0.9, 10: 0.8, 11: 0.7, 12: 0.6}[m]
    elif category == "Snacks":
        return {1: 0.8, 2: 0.8, 3: 0.9, 4: 0.9, 5: 0.9, 6: 0.9,
                7: 1.0, 8: 1.0, 9: 1.1, 10: 1.5, 11: 1.6, 12: 1.1}[m]
    else:  # Dairy & Ready-to-eat
        return {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
                7: 1.0, 8: 1.0, 9: 1.0, 10: 1.2, 11: 1.2, 12: 1.1}[m]


# ── Static Master Data ────────────────────────────────────────────────────────

CATEGORIES = ["Beverages", "Snacks", "Dairy & Ready-to-eat"]

PRODUCTS = [
    # (category, sku, name, brand, unit, mrp, cost_price)
    # Beverages
    ("Beverages", "BEV-001", "Mango Frooti",         "Parle Agro", "200ml", 15.0,  8.0),
    ("Beverages", "BEV-002", "Mango Frooti",         "Parle Agro", "500ml", 30.0, 16.0),
    ("Beverages", "BEV-003", "Appy Fizz",            "Parle Agro", "250ml", 20.0, 11.0),
    ("Beverages", "BEV-004", "Real Orange Juice",    "Dabur",      "1L",   120.0, 65.0),
    ("Beverages", "BEV-005", "Real Mixed Fruit",     "Dabur",      "1L",   120.0, 65.0),
    ("Beverages", "BEV-006", "Real Guava Juice",     "Dabur",      "500ml", 65.0, 35.0),
    ("Beverages", "BEV-007", "Tropicana Orange",     "PepsiCo",    "1L",   130.0, 70.0),
    ("Beverages", "BEV-008", "Tropicana Cranberry",  "PepsiCo",    "1L",   140.0, 75.0),
    ("Beverages", "BEV-009", "Kinley Water",         "Coca-Cola",  "1L",    20.0,  8.0),
    ("Beverages", "BEV-010", "Kinley Water",         "Coca-Cola",  "500ml", 15.0,  6.0),
    ("Beverages", "BEV-011", "Bisleri Water",        "Bisleri",    "1L",    20.0,  8.0),
    ("Beverages", "BEV-012", "Bisleri Water",        "Bisleri",    "500ml", 15.0,  6.0),
    ("Beverages", "BEV-013", "Red Bull Energy",      "Red Bull",   "250ml",125.0, 70.0),
    ("Beverages", "BEV-014", "Monster Energy",       "Monster",    "500ml",135.0, 75.0),
    ("Beverages", "BEV-015", "Limca",                "Coca-Cola",  "300ml", 20.0, 10.0),
    ("Beverages", "BEV-016", "Maaza Mango",          "Coca-Cola",  "250ml", 20.0, 10.0),
    ("Beverages", "BEV-017", "Slice Mango",          "PepsiCo",    "250ml", 20.0, 10.0),
    ("Beverages", "BEV-018", "Paper Boat Aamras",    "Hector",     "250ml", 30.0, 16.0),
    ("Beverages", "BEV-019", "Paper Boat Jaljeera",  "Hector",     "250ml", 30.0, 16.0),
    ("Beverages", "BEV-020", "Nimbuzz Lemon Drink",  "Rasna",      "500ml", 25.0, 12.0),
    # Snacks
    ("Snacks", "SNK-001", "Lays Classic Salted",     "PepsiCo",    "26g",   20.0, 11.0),
    ("Snacks", "SNK-002", "Lays Cream & Onion",      "PepsiCo",    "26g",   20.0, 11.0),
    ("Snacks", "SNK-003", "Lays Magic Masala",       "PepsiCo",    "26g",   20.0, 11.0),
    ("Snacks", "SNK-004", "Kurkure Masala Munch",    "PepsiCo",    "90g",   30.0, 16.0),
    ("Snacks", "SNK-005", "Kurkure Green Chutney",   "PepsiCo",    "90g",   30.0, 16.0),
    ("Snacks", "SNK-006", "Bingo Mad Angles",        "ITC",        "75g",   30.0, 16.0),
    ("Snacks", "SNK-007", "Bingo Original Style",    "ITC",        "75g",   30.0, 16.0),
    ("Snacks", "SNK-008", "Haldiram Aloo Bhujia",    "Haldiram",   "200g",  80.0, 42.0),
    ("Snacks", "SNK-009", "Haldiram Mixture",        "Haldiram",   "200g",  75.0, 40.0),
    ("Snacks", "SNK-010", "Haldiram Moong Dal",      "Haldiram",   "200g",  75.0, 40.0),
    ("Snacks", "SNK-011", "Parle-G Biscuits",        "Parle",      "100g",  10.0,  5.0),
    ("Snacks", "SNK-012", "Good Day Butter",         "Britannia",  "100g",  30.0, 16.0),
    ("Snacks", "SNK-013", "Good Day Cashew",         "Britannia",  "100g",  35.0, 18.0),
    ("Snacks", "SNK-014", "Oreo Original",           "Mondelez",   "120g",  40.0, 21.0),
    ("Snacks", "SNK-015", "Hide & Seek",             "Parle",      "100g",  30.0, 16.0),
    ("Snacks", "SNK-016", "Too Yumm Multigrain",     "RP-SG",      "55g",   20.0, 10.0),
    ("Snacks", "SNK-017", "Cornitos Nachos",         "Cornitos",   "60g",   30.0, 16.0),
    ("Snacks", "SNK-018", "Lay's Wafer Thin",        "PepsiCo",    "55g",   30.0, 15.0),
    ("Snacks", "SNK-019", "Bikaji Bikaneri Bhujia",  "Bikaji",     "200g",  85.0, 45.0),
    ("Snacks", "SNK-020", "Balaji Wafers",           "Balaji",     "100g",  20.0, 10.0),
    # Dairy & Ready-to-eat
    ("Dairy & Ready-to-eat", "DRY-001", "Amul Kool Koko",          "Amul",       "200ml",  30.0,  16.0),
    ("Dairy & Ready-to-eat", "DRY-002", "Amul Kool Rose",          "Amul",       "200ml",  30.0,  16.0),
    ("Dairy & Ready-to-eat", "DRY-003", "Amul Mango Milk",         "Amul",       "200ml",  30.0,  16.0),
    ("Dairy & Ready-to-eat", "DRY-004", "Nestle Milo",             "Nestle",     "200ml",  35.0,  18.0),
    ("Dairy & Ready-to-eat", "DRY-005", "Britannia Cheese Slice",  "Britannia",  "200g",  110.0,  58.0),
    ("Dairy & Ready-to-eat", "DRY-006", "Maggi 2-Minute Noodles",  "Nestle",     "70g",    14.0,   7.0),
    ("Dairy & Ready-to-eat", "DRY-007", "Maggi Masala Noodles",    "Nestle",     "140g",   28.0,  14.0),
    ("Dairy & Ready-to-eat", "DRY-008", "Yippee Noodles",          "ITC",        "70g",    14.0,   7.0),
    ("Dairy & Ready-to-eat", "DRY-009", "Kellogg's Corn Flakes",   "Kellogg's",  "250g",  150.0,  80.0),
    ("Dairy & Ready-to-eat", "DRY-010", "Kellogg's Chocos",        "Kellogg's",  "250g",  165.0,  88.0),
    ("Dairy & Ready-to-eat", "DRY-011", "Baggry's Oats",           "Baggry's",   "400g",  180.0,  95.0),
    ("Dairy & Ready-to-eat", "DRY-012", "Saffola Oats",            "Marico",     "400g",  175.0,  92.0),
    ("Dairy & Ready-to-eat", "DRY-013", "MTR Poha",                "MTR",        "500g",   85.0,  44.0),
    ("Dairy & Ready-to-eat", "DRY-014", "MTR Upma Mix",            "MTR",        "500g",   90.0,  47.0),
    ("Dairy & Ready-to-eat", "DRY-015", "ITC Sunfeast Pasta",      "ITC",        "150g",   50.0,  26.0),
    ("Dairy & Ready-to-eat", "DRY-016", "Epigamia Greek Yogurt",   "Epigamia",   "90g",    55.0,  30.0),
    ("Dairy & Ready-to-eat", "DRY-017", "Nandini Curd",            "KMF",        "500g",   55.0,  28.0),
    ("Dairy & Ready-to-eat", "DRY-018", "Amul Lassi",              "Amul",       "200ml",  30.0,  15.0),
    ("Dairy & Ready-to-eat", "DRY-019", "B Natural Mixed Fruit",   "ITC",        "1L",    115.0,  60.0),
    ("Dairy & Ready-to-eat", "DRY-020", "Horlicks Classic Malt",   "HUL",        "500g",  290.0, 155.0),
]

GEOGRAPHY = {
    "North": {
        "Delhi":         ["New Delhi", "Dwarka", "Rohini"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra"],
        "Punjab":        ["Ludhiana", "Amritsar"],
        "Haryana":       ["Gurugram", "Faridabad"],
    },
    "South": {
        "Tamil Nadu":  ["Chennai", "Coimbatore", "Madurai"],
        "Karnataka":   ["Bengaluru", "Mysuru"],
        "Telangana":   ["Hyderabad", "Warangal"],
        "Kerala":      ["Kochi", "Thiruvananthapuram"],
    },
    "East": {
        "West Bengal": ["Kolkata", "Howrah", "Durgapur"],
        "Odisha":      ["Bhubaneswar", "Cuttack"],
        "Bihar":       ["Patna", "Gaya"],
    },
    "West": {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
        "Gujarat":     ["Ahmedabad", "Surat", "Vadodara"],
        "Rajasthan":   ["Jaipur", "Jodhpur"],
    },
}

RETAILER_TYPES        = ["General Trade", "Modern Trade", "E-Commerce"]
RETAILER_TYPE_WEIGHTS = [0.65, 0.25, 0.10]

STORE_PREFIXES = {
    "General Trade": ["Kirana Store", "Provision Store", "Super Mart", "General Stores"],
    "Modern Trade":  ["Big Bazaar", "DMart", "Reliance Fresh", "More Supermarket", "Star Bazaar"],
    "E-Commerce":    ["Blinkit Hub", "Zepto Dark Store", "Swiggy Instamart", "Amazon Fresh"],
}

_CHUNK = 5_000  # bulk insert batch size


# ── Seed Functions ────────────────────────────────────────────────────────────

async def seed_categories(conn) -> dict[str, int]:
    cat_ids = {}
    for name in CATEGORIES:
        cat_ids[name] = await conn.fetchval(
            "INSERT INTO categories (name) VALUES ($1) RETURNING category_id", name
        )
    return cat_ids


async def seed_products(conn, cat_id_map: dict[str, int]) -> dict[str, int]:
    prod_ids = {}
    for cat, sku, name, brand, unit, mrp, cost in PRODUCTS:
        prod_ids[sku] = await conn.fetchval(
            "INSERT INTO products (category_id, sku_code, name, brand, unit, mrp, cost_price) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING product_id",
            cat_id_map[cat], sku, name, brand, unit, mrp, cost,
        )
    return prod_ids


async def seed_geography(conn) -> tuple[dict, dict, dict]:
    zone_ids, state_ids, city_ids = {}, {}, {}
    for zone_name, states in GEOGRAPHY.items():
        zone_ids[zone_name] = await conn.fetchval(
            "INSERT INTO zones (name) VALUES ($1) RETURNING zone_id", zone_name
        )
        for state_name, cities in states.items():
            state_ids[state_name] = await conn.fetchval(
                "INSERT INTO states (zone_id, name) VALUES ($1, $2) RETURNING state_id",
                zone_ids[zone_name], state_name,
            )
            for city_name in cities:
                city_ids[city_name] = await conn.fetchval(
                    "INSERT INTO cities (state_id, name) VALUES ($1, $2) RETURNING city_id",
                    state_ids[state_name], city_name,
                )
    return zone_ids, state_ids, city_ids


async def seed_distributors(conn, city_ids: dict[str, int], n: int = 15) -> list[int]:
    all_cities = list(city_ids.items())
    dist_ids = []
    for _ in range(n):
        _, city_id = random.choice(all_cities)
        dist_ids.append(await conn.fetchval(
            "INSERT INTO distributors (name, city_id, contact_name, phone) "
            "VALUES ($1, $2, $3, $4) RETURNING distributor_id",
            fake.company() + " Distributors",
            city_id,
            fake.name(),
            fake.phone_number()[:15],
        ))
    return dist_ids


async def seed_wholesalers(
    conn, distributor_ids: list[int], city_ids: dict[str, int], n: int = 40
) -> list[int]:
    all_cities = list(city_ids.items())
    ws_ids = []
    for _ in range(n):
        _, city_id = random.choice(all_cities)
        ws_ids.append(await conn.fetchval(
            "INSERT INTO wholesalers (name, distributor_id, city_id, contact_name, phone) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING wholesaler_id",
            fake.company() + " Wholesale",
            random.choice(distributor_ids),
            city_id,
            fake.name(),
            fake.phone_number()[:15],
        ))
    return ws_ids


async def seed_retailers(
    conn,
    distributor_ids: list[int],
    wholesaler_ids: list[int],
    city_ids: dict[str, int],
    n: int = 150,
) -> list[int]:
    all_cities = list(city_ids.items())
    retailer_ids = []
    for _ in range(n):
        _, city_id = random.choice(all_cities)
        r_type  = random.choices(RETAILER_TYPES, RETAILER_TYPE_WEIGHTS)[0]
        ws_id   = random.choice(wholesaler_ids) if random.random() > 0.2 else None
        name    = random.choice(STORE_PREFIXES[r_type]) + " " + fake.last_name()
        retailer_ids.append(await conn.fetchval(
            "INSERT INTO retailers (name, retailer_type, wholesaler_id, distributor_id, city_id) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING retailer_id",
            name, r_type, ws_id, random.choice(distributor_ids), city_id,
        ))
    return retailer_ids


async def seed_orders_and_shipments(
    conn, distributor_ids: list[int], product_ids: dict[str, int]
) -> None:
    all_products = list(product_ids.items())
    mrp_map = {product_ids[sku]: mrp for _, sku, _, _, _, mrp, _ in PRODUCTS}

    order_count = 0

    for month in range(1, 13):
        for dist_id in distributor_ids:
            for _ in range(random.randint(3, 6)):
                order_day = min(random.randint(1, 28), 28)
                order_date       = date(2025, month, order_day)
                lead_days        = random.randint(3, 7)
                expected_delivery = order_date + timedelta(days=lead_days)

                r = random.random()
                status = (
                    "Fulfilled" if r < 0.75 else
                    "Partial"   if r < 0.88 else
                    "Pending"   if r < 0.95 else
                    "Cancelled"
                )

                order_id = await conn.fetchval(
                    "INSERT INTO orders (distributor_id, order_date, expected_delivery, status) "
                    "VALUES ($1, $2, $3, $4) RETURNING order_id",
                    dist_id, order_date, expected_delivery, status,
                )
                order_count += 1

                selected = random.sample(all_products, k=random.randint(3, 8))
                qty_map  = {}
                item_rows = []
                for sku, prod_id in selected:
                    qty = random.randint(50, 500)
                    unit_price = round(mrp_map[prod_id] * random.uniform(0.70, 0.85), 2)
                    qty_map[prod_id] = qty
                    item_rows.append((order_id, prod_id, qty, unit_price))

                await conn.executemany(
                    "INSERT INTO order_items (order_id, product_id, ordered_qty, unit_price) "
                    "VALUES ($1, $2, $3, $4)",
                    item_rows,
                )

                if status in ("Fulfilled", "Partial"):
                    actual_ship     = order_date + timedelta(days=random.randint(1, lead_days))
                    actual_delivery = actual_ship + timedelta(days=random.randint(1, 3))
                    shipment_id = await conn.fetchval(
                        "INSERT INTO shipments (order_id, ship_date, delivered_date) "
                        "VALUES ($1, $2, $3) RETURNING shipment_id",
                        order_id, actual_ship, actual_delivery,
                    )

                    shipment_rows = []
                    for sku, prod_id in selected:
                        ordered_qty = qty_map[prod_id]
                        shipped_qty = (
                            ordered_qty if status == "Fulfilled"
                            else int(ordered_qty * random.uniform(0.5, 0.85))
                        )
                        shipment_rows.append((shipment_id, prod_id, shipped_qty))

                    await conn.executemany(
                        "INSERT INTO shipment_items (shipment_id, product_id, shipped_qty) "
                        "VALUES ($1, $2, $3)",
                        shipment_rows,
                    )

    print(f"  Orders: {order_count}")


async def seed_sales(
    conn, retailer_ids: list[int], product_ids: dict[str, int]
) -> None:
    prod_list = [(product_ids[sku], cat) for cat, sku, *_ in PRODUCTS]
    mrp_map   = {product_ids[sku]: mrp for _, sku, _, _, _, mrp, _ in PRODUCTS}

    rows = []
    for retailer_id in retailer_ids:
        carrying = random.sample(prod_list, k=random.randint(10, 20))
        for d in date_range(START_DATE, END_DATE):
            if random.random() > 0.57:
                continue
            for prod_id, category in carrying:
                if random.random() > 0.4:
                    continue
                multiplier    = seasonal_multiplier(d, category)
                qty           = max(1, int(random.randint(2, 20) * multiplier * random.uniform(0.7, 1.3)))
                selling_price = round(mrp_map[prod_id] * random.uniform(0.90, 1.0), 2)
                rows.append((retailer_id, prod_id, d, qty, selling_price))

    for i in range(0, len(rows), _CHUNK):
        await conn.executemany(
            "INSERT INTO sales (retailer_id, product_id, sale_date, qty_sold, selling_price) "
            "VALUES ($1, $2, $3, $4, $5)",
            rows[i : i + _CHUNK],
        )
    print(f"  Sales records: {len(rows)}")


async def seed_inventory(conn, distributor_ids: list[int], product_ids: dict[str, int]) -> None:
    prod_ids = list(product_ids.values())

    snapshot_dates = []
    d = START_DATE
    while d <= END_DATE:
        snapshot_dates.append(d)
        d += timedelta(weeks=1)

    rows = []
    for dist_id in distributor_ids:
        carrying = random.sample(prod_ids, k=random.randint(30, 50))
        stock    = {p: random.randint(200, 2000) for p in carrying}
        for snap_date in snapshot_dates:
            for prod_id in carrying:
                stock[prod_id] = max(0, int(stock[prod_id] * random.uniform(0.7, 1.1)))
                if stock[prod_id] < 100 or random.random() < 0.2:
                    stock[prod_id] += random.randint(200, 800)
                rows.append((prod_id, dist_id, snap_date, stock[prod_id]))

    for i in range(0, len(rows), _CHUNK):
        await conn.executemany(
            "INSERT INTO inventory (product_id, distributor_id, snapshot_date, stock_qty) "
            "VALUES ($1, $2, $3, $4)",
            rows[i : i + _CHUNK],
        )
    print(f"  Inventory snapshots: {len(rows)}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(POSTGRES_URI)

    print("Seeding master data...")
    cat_id_map      = await seed_categories(conn)
    product_ids     = await seed_products(conn, cat_id_map)
    _, _, city_ids  = await seed_geography(conn)
    distributor_ids = await seed_distributors(conn, city_ids, n=15)
    wholesaler_ids  = await seed_wholesalers(conn, distributor_ids, city_ids, n=40)
    retailer_ids    = await seed_retailers(conn, distributor_ids, wholesaler_ids, city_ids, n=150)

    print(f"  Categories:   {len(cat_id_map)}")
    print(f"  Products:     {len(product_ids)}")
    print(f"  Distributors: {len(distributor_ids)}")
    print(f"  Wholesalers:  {len(wholesaler_ids)}")
    print(f"  Retailers:    {len(retailer_ids)}")

    print("Seeding transactional data...")
    await seed_orders_and_shipments(conn, distributor_ids, product_ids)
    await seed_sales(conn, retailer_ids, product_ids)
    await seed_inventory(conn, distributor_ids, product_ids)

    await conn.close()
    print("\nDone. Database seeded.")


if __name__ == "__main__":
    asyncio.run(main())
