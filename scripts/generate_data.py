"""
generate_data.py
Generates a realistic, enterprise-grade e-commerce dataset for portfolio analytics.
Includes:
- Customers (demographics, acquisition channels)
- Products (categories, pricing, cost of goods sold)
- Orders (multi-year timeline, seasonality, retention & churn dynamics)
- Order Items (multi-item transactions with realistic cross-sell affinities)
- SQLite database (ecommerce.db) populated with clean relational tables
- Analytics master CSV for Power BI / Tableau / Excel import
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Set deterministic seed for reproducibility
np.random.seed(42)
random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "data" / "ecommerce.db"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

print("[INFO] Starting realistic E-Commerce data generation...")

# ==========================================
# 1. PRODUCTS CATALOG
# ==========================================
products_data = [
    # Electronics
    (101, "Pro Noise-Cancelling Headphones", "Electronics", 199.99, 85.00),
    (102, "Ultra Ergonomic Wireless Mouse", "Electronics", 49.99, 18.00),
    (103, "Mechanical Gaming Keyboard", "Electronics", 89.99, 36.00),
    (104, "4K Ultra-HD Monitor 27-inch", "Electronics", 349.99, 175.00),
    (105, "USB-C Multi-Port Hub Adapter", "Electronics", 39.99, 12.00),
    (106, "Smart Fitness Watch Gen 4", "Electronics", 179.99, 70.00),
    (107, "Portable Bluetooth Speaker Waterproof", "Electronics", 59.99, 22.00),
    (108, "High-Speed MagSafe Wireless Charger", "Electronics", 29.99, 9.50),
    
    # Apparel
    (201, "Classic Organic Cotton Crewneck T-Shirt", "Apparel", 28.00, 8.50),
    (202, "Slim Fit Stretch Denim Jeans", "Apparel", 68.00, 22.00),
    (203, "Water-Resistant Commuter Jacket", "Apparel", 120.00, 42.00),
    (204, "Thermal Merino Wool Socks (3-Pack)", "Apparel", 24.00, 6.00),
    (205, "Breathable Athletic Jogger Pants", "Apparel", 54.00, 16.00),
    (206, "All-Weather Polarized Sunglasses", "Apparel", 45.00, 11.00),
    
    # Home & Kitchen
    (301, "Precision Barista Espresso Machine", "Home & Kitchen", 289.00, 130.00),
    (302, "Ceramic Burr Coffee Bean Grinder", "Home & Kitchen", 45.00, 15.00),
    (303, "Artisan Whole Bean Roast Coffee (2lb)", "Home & Kitchen", 24.99, 7.50),
    (304, "Cast Iron Pre-Seasoned Skillet 10in", "Home & Kitchen", 39.99, 14.00),
    (305, "Stainless Steel Chef Knife 8-inch", "Home & Kitchen", 59.99, 20.00),
    (306, "Aroma Ultrasonic Essential Oil Diffuser", "Home & Kitchen", 32.50, 10.00),
    (307, "Insulated Vacuum Water Bottle 32oz", "Home & Kitchen", 29.99, 8.00),
    
    # Health & Beauty
    (401, "Hydrating Hyaluronic Acid Serum", "Health & Beauty", 26.00, 6.00),
    (402, "Vitamin C Brightening Facial Moisturizer", "Health & Beauty", 34.00, 8.50),
    (403, "Mineral SPF 50 Broad Spectrum Sunscreen", "Health & Beauty", 22.00, 5.20),
    (404, "Sonic Electric Toothbrush + 3 Heads", "Health & Beauty", 64.99, 21.00),
    (405, "Organic Lavender Sleep Aromatherapy Mist", "Health & Beauty", 18.00, 4.00),
    
    # Sports & Outdoors
    (501, "Eco-Friendly High Density Yoga Mat", "Sports & Outdoors", 42.00, 13.00),
    (502, "Adjustable Resistance Fitness Bands Set", "Sports & Outdoors", 22.99, 5.50),
    (503, "Collapsible Lightweight Trekking Poles", "Sports & Outdoors", 48.00, 15.00),
    (504, "Quick-Dry Microfiber Camp Towel", "Sports & Outdoors", 16.99, 4.20),
    (505, "High-Capacity Hydration Running Vest", "Sports & Outdoors", 75.00, 24.00),
]

products_df = pd.DataFrame(
    products_data,
    columns=["product_id", "product_name", "category", "unit_price", "unit_cost"]
)
products_df["margin_percentage"] = (
    (products_df["unit_price"] - products_df["unit_cost"]) / products_df["unit_price"] * 100
).round(2)

print(f"[SUCCESS] Generated {len(products_df)} products across {products_df['category'].nunique()} categories.")

# ==========================================
# 2. CUSTOMERS GENERATION
# ==========================================
NUM_CUSTOMERS = 4000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
region_weights = [0.48, 0.28, 0.16, 0.08]

channels = ["Paid Search", "Organic Search", "Social Media", "Referral", "Email Marketing"]
channel_weights = [0.32, 0.24, 0.22, 0.12, 0.10]

customer_records = []
for cid in range(1, NUM_CUSTOMERS + 1):
    # Customer signup skewed towards earlier months to allow observing multi-month cohorts
    signup_day_offset = int(np.random.beta(a=1.4, b=1.8) * TOTAL_DAYS)
    signup_date = START_DATE + timedelta(days=signup_day_offset)
    
    region = np.random.choice(regions, p=region_weights)
    channel = np.random.choice(channels, p=channel_weights)
    
    # Customer loyalty archetype
    # 55% one-time buyers, 25% occasional (2-3 orders), 15% frequent (4-7 orders), 5% VIP champions (8+ orders)
    archetype = np.random.choice(
        ["one_timer", "occasional", "frequent", "champion"],
        p=[0.55, 0.25, 0.15, 0.05]
    )
    
    customer_records.append({
        "customer_id": f"CUST-{cid:05d}",
        "first_name": f"User{cid}",
        "email": f"user{cid}@example.com",
        "signup_date": signup_date.strftime("%Y-%m-%d"),
        "region": region,
        "acquisition_channel": channel,
        "archetype": archetype
    })

customers_df = pd.DataFrame(customer_records)
print(f"[SUCCESS] Generated {len(customers_df)} customers.")

# ==========================================
# 3. ORDERS & TRANSACTIONS GENERATION
# ==========================================
order_records = []
order_item_records = []
order_counter = 1
item_counter = 1

# Product affinities for realistic cross-sell
affinities = {
    104: [102, 103, 105],  # Monitor -> Mouse, Keyboard, Hub
    101: [108, 107],       # Headphones -> Charger, Speaker
    301: [302, 303],       # Espresso machine -> Grinder, Coffee beans
    401: [402, 403],       # Serum -> Moisturizer, Sunscreen
    501: [502, 307],       # Yoga mat -> Resistance bands, Water bottle
}

payment_methods = ["Credit Card", "PayPal", "Buy Now Pay Later", "Debit Card"]
payment_weights = [0.52, 0.26, 0.14, 0.08]

for idx, cust in customers_df.iterrows():
    c_id = cust["customer_id"]
    signup_dt = datetime.strptime(cust["signup_date"], "%Y-%m-%d")
    archetype = cust["archetype"]
    
    if archetype == "one_timer":
        num_orders = 1
    elif archetype == "occasional":
        num_orders = random.randint(2, 3)
    elif archetype == "frequent":
        num_orders = random.randint(4, 7)
    else:  # champion
        num_orders = random.randint(8, 15)
        
    # First order occurs typically within 0-5 days of signup
    current_order_dt = signup_dt + timedelta(days=random.randint(0, 5))
    
    for order_seq in range(1, num_orders + 1):
        if current_order_dt > END_DATE:
            break
            
        order_id = f"ORD-{order_counter:06d}"
        order_counter += 1
        
        # Seasonality effect: November and December have slight boost in size & promotions
        is_holiday_season = current_order_dt.month in [11, 12]
        
        # Status
        status_rand = random.random()
        if status_rand < 0.93:
            status = "Completed"
        elif status_rand < 0.97:
            status = "Returned"
        else:
            status = "Cancelled"
            
        payment_method = np.random.choice(payment_methods, p=payment_weights)
        
        # Decide discount
        has_discount = (random.random() < 0.35) or (is_holiday_season and random.random() < 0.60)
        discount_rate = round(random.choice([0.05, 0.10, 0.15, 0.20]), 2) if has_discount else 0.0
        
        # Shipping fee: free for larger orders, else $5-$10
        shipping_fee = 0.0 if random.random() < 0.65 else round(random.choice([4.99, 7.99, 9.99]), 2)
        
        # Select items for this order
        num_items_in_order = np.random.choice([1, 2, 3, 4], p=[0.58, 0.27, 0.11, 0.04])
        if is_holiday_season:
            num_items_in_order = min(4, num_items_in_order + 1)
            
        primary_product = products_df.sample(1).iloc[0]
        selected_prod_ids = [primary_product["product_id"]]
        
        # Check affinity cross-sell
        if primary_product["product_id"] in affinities and num_items_in_order > 1:
            for related_pid in affinities[primary_product["product_id"]]:
                if len(selected_prod_ids) < num_items_in_order and random.random() < 0.60:
                    selected_prod_ids.append(related_pid)
                    
        # Fill remaining if needed
        while len(selected_prod_ids) < num_items_in_order:
            fill_pid = products_df.sample(1).iloc[0]["product_id"]
            if fill_pid not in selected_prod_ids:
                selected_prod_ids.append(fill_pid)
                
        order_subtotal = 0.0
        order_total_cost = 0.0
        
        for pid in selected_prod_ids:
            prod_row = products_df[products_df["product_id"] == pid].iloc[0]
            qty = np.random.choice([1, 2, 3], p=[0.85, 0.12, 0.03])
            unit_price = prod_row["unit_price"]
            unit_cost = prod_row["unit_cost"]
            line_subtotal = round(unit_price * qty, 2)
            line_cost = round(unit_cost * qty, 2)
            
            order_subtotal += line_subtotal
            order_total_cost += line_cost
            
            order_item_records.append({
                "item_id": f"ITEM-{item_counter:07d}",
                "order_id": order_id,
                "product_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "line_subtotal": line_subtotal,
                "line_cost": line_cost
            })
            item_counter += 1
            
        discount_amount = round(order_subtotal * discount_rate, 2)
        total_order_amount = round(order_subtotal - discount_amount + shipping_fee, 2)
        gross_profit = round((order_subtotal - discount_amount) - order_total_cost, 2)
        
        order_records.append({
            "order_id": order_id,
            "customer_id": c_id,
            "order_date": current_order_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "order_date_only": current_order_dt.strftime("%Y-%m-%d"),
            "order_status": status,
            "payment_method": payment_method,
            "subtotal": order_subtotal,
            "discount_amount": discount_amount,
            "shipping_fee": shipping_fee,
            "total_amount": total_order_amount,
            "total_cost": order_total_cost,
            "gross_profit": gross_profit,
            "order_sequence": order_seq
        })
        
        # Inter-purchase interval (days to next order): typically 20 to 75 days
        days_to_next = int(np.random.gamma(shape=3.5, scale=12.0)) + 5
        current_order_dt += timedelta(days=days_to_next)

orders_df = pd.DataFrame(order_records)
order_items_df = pd.DataFrame(order_item_records)

print(f"[SUCCESS] Generated {len(orders_df)} orders and {len(order_items_df)} line items.")

# ==========================================
# 4. SAVE TO RAW CSVs
# ==========================================
customers_df_clean = customers_df.drop(columns=["archetype"])
customers_df_clean.to_csv(RAW_DATA_DIR / "customers.csv", index=False)
products_df.to_csv(RAW_DATA_DIR / "products.csv", index=False)
orders_df.to_csv(RAW_DATA_DIR / "orders.csv", index=False)
order_items_df.to_csv(RAW_DATA_DIR / "order_items.csv", index=False)

print(f"[SUCCESS] Raw CSV files saved to {RAW_DATA_DIR}")

# ==========================================
# 5. DENORMALIZED ANALYTICS MASTER TABLE
# ==========================================
# Join orders + customers + order_items + products for BI drag & drop
master_df = order_items_df.merge(orders_df, on="order_id", how="inner")
master_df = master_df.merge(customers_df_clean, on="customer_id", how="inner")
master_df = master_df.merge(products_df, on="product_id", how="inner")

master_df.to_csv(PROCESSED_DATA_DIR / "ecommerce_analytics_master.csv", index=False)
print(f"[SUCCESS] Analytics Master CSV saved to {PROCESSED_DATA_DIR} ({len(master_df)} rows).")

# ==========================================
# 6. POPULATE SQLITE DATABASE
# ==========================================
if DB_PATH.exists():
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
customers_df_clean.to_sql("customers", conn, if_exists="replace", index=False)
products_df.to_sql("products", conn, if_exists="replace", index=False)
orders_df.to_sql("orders", conn, if_exists="replace", index=False)
order_items_df.to_sql("order_items", conn, if_exists="replace", index=False)
master_df.to_sql("analytics_master", conn, if_exists="replace", index=False)

# Add indexes for high-speed analytical queries
cursor = conn.cursor()
cursor.execute("CREATE INDEX idx_orders_cust ON orders(customer_id);")
cursor.execute("CREATE INDEX idx_orders_date ON orders(order_date_only);")
cursor.execute("CREATE INDEX idx_items_order ON order_items(order_id);")
cursor.execute("CREATE INDEX idx_items_prod ON order_items(product_id);")
conn.commit()
conn.close()

print(f"[SUCCESS] SQLite Database successfully initialized and indexed at: {DB_PATH}")
print("[DONE] Data generation complete! Ready for SQL analysis and dashboard execution.")

