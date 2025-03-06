import sqlite3
import random

# Connect to the database
conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# Fetch all product IDs
cur.execute("SELECT id, price FROM products")
products = cur.fetchall()

if not products:
    print("❌ No products found! Add products first.")
    exit()

# Generate 100,000+ sales records in batches
sales_data = []
for _ in range(100000):
    product_id, price = random.choice(products)
    quantity_sold = random.randint(1, 5)
    total_price = round(quantity_sold * price, 2)

    sales_data.append((product_id, quantity_sold, total_price))

# Insert data in bulk
cur.executemany("INSERT INTO sales (product_id, quantity_sold, total_price) VALUES (?, ?, ?)", sales_data)

conn.commit()
conn.close()

print("✅ 100,000+ sales records added successfully!")

