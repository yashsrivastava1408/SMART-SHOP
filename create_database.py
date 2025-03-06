import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('shop.db')
cur = conn.cursor()


# Insert sample products
products = [
    ('Product 1', 10.99, 100),
    ('Product 2', 20.99, 50),
    ('Product 3', 5.49, 200),
    ('Product 4', 15.99, 80),
    ('Product 5', 25.49, 30),
    ('Product 6', 7.99, 150),
    ('Product 7', 12.50, 90),
    ('Product 8', 18.75, 40),
    ('Product 9', 9.99, 120),
    ('Product 10', 30.00, 20)
]

cur.executemany("INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)", products)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database and products table created successfully!")
