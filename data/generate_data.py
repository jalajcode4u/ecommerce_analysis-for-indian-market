"""
generate_data.py  ·  E-Commerce Sales Analysis Dataset Generator
Generates: customers.csv, products.csv, orders.csv, order_items.csv
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

random.seed(42)
np.random.seed(42)

OUT = os.path.dirname(os.path.abspath(__file__))

# ── Config ────────────────────────────────────────────────────────
N_CUSTOMERS  = 1000
N_PRODUCTS   = 120
N_ORDERS     = 5000
START_DATE   = datetime(2023, 1, 1)
END_DATE     = datetime(2024, 12, 31)

# ── Reference data ────────────────────────────────────────────────
CATEGORIES = {
    "Electronics":   {"weight": 0.20, "price_range": (2000, 80000)},
    "Clothing":      {"weight": 0.22, "price_range": (299,  4999)},
    "Home & Kitchen":{"weight": 0.18, "price_range": (199,  15000)},
    "Books":         {"weight": 0.10, "price_range": (99,   899)},
    "Sports":        {"weight": 0.12, "price_range": (399,  12000)},
    "Beauty":        {"weight": 0.10, "price_range": (149,  3499)},
    "Toys":          {"weight": 0.08, "price_range": (199,  4999)},
}

PRODUCTS_BY_CAT = {
    "Electronics":    ["Wireless Earbuds","Bluetooth Speaker","USB-C Hub","Smart Watch","Laptop Stand",
                       "Mechanical Keyboard","Gaming Mouse","Webcam","Power Bank","LED Monitor"],
    "Clothing":       ["Men's T-Shirt","Women's Kurta","Denim Jeans","Sports Hoodie","Formal Shirt",
                       "Summer Dress","Track Pants","Winter Jacket","Polo T-Shirt","Leggings"],
    "Home & Kitchen": ["Air Fryer","Coffee Maker","Non-Stick Pan","Mixer Grinder","Water Bottle",
                       "Storage Box","Bed Sheet Set","Curtain Pair","Wall Clock","Dinner Set"],
    "Books":          ["Data Science Handbook","Python Crash Course","Atomic Habits","Rich Dad Poor Dad",
                       "SQL for Beginners","Deep Work","The Psychology of Money","Clean Code",
                       "System Design Interview","Zero to One"],
    "Sports":         ["Yoga Mat","Resistance Bands","Cricket Bat","Football","Cycling Helmet",
                       "Dumbell Set","Skipping Rope","Badminton Racket","Swimming Goggles","Running Shoes"],
    "Beauty":         ["Face Serum","Sunscreen SPF50","Hair Oil","Lipstick Set","Eye Shadow Palette",
                       "Face Wash","Moisturizer","Perfume","Nail Polish Set","BB Cream"],
    "Toys":           ["LEGO Classic Set","Remote Control Car","Board Game","Puzzle 1000pc",
                       "Soft Toy Bear","Dollhouse","Science Kit","Card Game","Art Set","Drone Mini"],
}

CITIES = [
    ("Mumbai","Maharashtra"),("Delhi","Delhi"),("Bangalore","Karnataka"),
    ("Hyderabad","Telangana"),("Chennai","Tamil Nadu"),("Kolkata","West Bengal"),
    ("Pune","Maharashtra"),("Ahmedabad","Gujarat"),("Jaipur","Rajasthan"),
    ("Lucknow","Uttar Pradesh"),("Surat","Gujarat"),("Nagpur","Maharashtra"),
    ("Indore","Madhya Pradesh"),("Bhopal","Madhya Pradesh"),("Patna","Bihar"),
]

FIRST_NAMES = ["Rahul","Priya","Amit","Sunita","Vijay","Neha","Raj","Pooja","Suresh","Kavita",
               "Arjun","Divya","Ankit","Ritu","Manish","Sita","Deepak","Anjali","Rohit","Smita"]
LAST_NAMES  = ["Sharma","Verma","Singh","Patel","Kumar","Gupta","Joshi","Mehta","Yadav","Mishra"]

# ── 1. CUSTOMERS ──────────────────────────────────────────────────
print("Generating customers...")
customers = []
for i in range(1, N_CUSTOMERS + 1):
    city, state = random.choice(CITIES)
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    join_days = random.randint(0, (END_DATE - START_DATE).days)
    join_date = START_DATE + timedelta(days=join_days)
    segment = random.choices(
        ["Regular", "Premium", "VIP"],
        weights=[0.65, 0.25, 0.10]
    )[0]
    customers.append({
        "customer_id":   f"C{i:04d}",
        "customer_name": name,
        "email":         f"{name.lower().replace(' ','.')}{i}@email.com",
        "city":          city,
        "state":         state,
        "segment":       segment,
        "join_date":     join_date.strftime("%Y-%m-%d"),
    })

df_customers = pd.DataFrame(customers)
df_customers.to_csv(f"{OUT}/customers.csv", index=False)
print(f"  ✅ customers.csv  — {len(df_customers)} rows")

# ── 2. PRODUCTS ───────────────────────────────────────────────────
print("Generating products...")
products = []
pid = 1
for cat, info in CATEGORIES.items():
    for pname in PRODUCTS_BY_CAT[cat]:
        lo, hi = info["price_range"]
        price = round(random.uniform(lo, hi), -1)   # round to nearest 10
        cost  = round(price * random.uniform(0.4, 0.65), -1)
        products.append({
            "product_id":   f"P{pid:03d}",
            "product_name": pname,
            "category":     cat,
            "price":        price,
            "cost_price":   cost,
            "brand":        random.choice(["ShopX","BrandY","ValuePlus","ProLine","EcoChoice"]),
            "in_stock":     random.choices([1, 0], weights=[0.92, 0.08])[0],
        })
        pid += 1

df_products = pd.DataFrame(products)
df_products.to_csv(f"{OUT}/products.csv", index=False)
print(f"  ✅ products.csv   — {len(df_products)} rows")

# ── 3. ORDERS ─────────────────────────────────────────────────────
print("Generating orders...")

# VIP/Premium customers order more frequently
customer_weights = []
for _, c in df_customers.iterrows():
    w = 3 if c["segment"] == "VIP" else (2 if c["segment"] == "Premium" else 1)
    customer_weights.append(w)

orders = []
order_items = []
item_id = 1

for oid in range(1, N_ORDERS + 1):
    # Random customer (weighted by segment)
    cust = df_customers.sample(1, weights=customer_weights).iloc[0]

    # Order date after customer join date
    cust_join = datetime.strptime(cust["join_date"], "%Y-%m-%d")
    earliest  = max(cust_join, START_DATE)
    if earliest >= END_DATE:
        earliest = START_DATE
    days_range = (END_DATE - earliest).days
    order_date = earliest + timedelta(days=random.randint(0, max(1, days_range)))

    # Status
    status = random.choices(
        ["Delivered","Shipped","Returned","Cancelled"],
        weights=[0.72, 0.15, 0.08, 0.05]
    )[0]

    # Payment method
    payment = random.choices(
        ["UPI","Credit Card","Debit Card","Net Banking","Cash on Delivery"],
        weights=[0.35, 0.25, 0.20, 0.10, 0.10]
    )[0]

    # Items in order (1-5 products)
    n_items = random.choices([1,2,3,4,5], weights=[0.40,0.30,0.15,0.10,0.05])[0]
    chosen_prods = df_products.sample(n_items)

    order_total = 0
    for _, prod in chosen_prods.iterrows():
        qty      = random.choices([1,2,3], weights=[0.70,0.22,0.08])[0]
        discount = random.choices([0, 5, 10, 15, 20], weights=[0.40,0.20,0.20,0.12,0.08])[0]
        unit_price = prod["price"]
        line_total = round(unit_price * qty * (1 - discount/100), 2)
        order_total += line_total

        order_items.append({
            "item_id":       f"I{item_id:06d}",
            "order_id":      f"O{oid:05d}",
            "product_id":    prod["product_id"],
            "quantity":      qty,
            "unit_price":    unit_price,
            "discount_pct":  discount,
            "line_total":    line_total,
        })
        item_id += 1

    orders.append({
        "order_id":      f"O{oid:05d}",
        "customer_id":   cust["customer_id"],
        "order_date":    order_date.strftime("%Y-%m-%d"),
        "status":        status,
        "payment_method":payment,
        "order_total":   round(order_total, 2),
        "city":          cust["city"],
        "state":         cust["state"],
    })

df_orders      = pd.DataFrame(orders)
df_order_items = pd.DataFrame(order_items)

df_orders.to_csv(f"{OUT}/orders.csv", index=False)
df_order_items.to_csv(f"{OUT}/order_items.csv", index=False)

print(f"  ✅ orders.csv      — {len(df_orders):,} rows")
print(f"  ✅ order_items.csv — {len(df_order_items):,} rows")
print(f"\n📊 Quick Stats:")
print(f"  Total Revenue : ₹{df_orders[df_orders['status']=='Delivered']['order_total'].sum():,.0f}")
print(f"  Avg Order Value: ₹{df_orders['order_total'].mean():,.0f}")
print(f"  Date Range    : {df_orders['order_date'].min()} → {df_orders['order_date'].max()}")
print(f"  Unique Customers who ordered: {df_orders['customer_id'].nunique()}")
