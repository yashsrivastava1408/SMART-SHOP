from flask import Flask, request, render_template, redirect, session, flash
import mysql.connector
import hashlib
from datetime import datetime
from reportlab.pdfgen import canvas
from flask import Response
from reportlab.lib.pagesizes import letter
from io import BytesIO
from reportlab.lib import colors


import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# MySQL Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "password",
    "database": "smart_shop"
}

# Initialize MySQL connection and create tables
def init_db():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    
    cur.execute("CREATE DATABASE IF NOT EXISTS smart_shop")
    cur.execute("USE smart_shop")

    # Admin Users Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    ''')

    # Customers Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    ''')

    # Products Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            quantity INT NOT NULL DEFAULT 1
        )
    ''')

    # Sales Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            total_price DECIMAL(10, 2) NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Inventory Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            distributor VARCHAR(255) NOT NULL,
            quantity_added INT NOT NULL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

init_db()


# Home (Title Page) Route
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect('/dashboard')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return "❌ Email and password are required!", 400

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        try:
            conn = mysql.connector.connect(**db_config)
            cur = conn.cursor()
            cur.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
            conn.commit()
            cur.close()
            conn.close()
            return redirect('/login')
        except mysql.connector.IntegrityError:
            return "❌ Email already registered!", 400

    return render_template('signup.html')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect('/products')  # Redirect back to the product list after deletion
# Redirect home to public products


@app.route('/public_products')
def public_product_list():
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('public_products.html', products=products)

@app.route('/customer-signup', methods=['GET', 'POST'])
def customer_signup():
    if 'customer_id' in session:
        return redirect('/public_products')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return "❌ Email and password are required!", 400

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        try:
            conn = mysql.connector.connect(**db_config)
            cur = conn.cursor()
            cur.execute("INSERT INTO customers (email, password) VALUES (%s, %s)", (email, hashed_password))
            conn.commit()
            cur.close()
            conn.close()
            return redirect('/customer-login')
        except mysql.connector.IntegrityError:
            return "❌ Email already registered!", 400

    return render_template('customer_signup.html')


@app.route('/customer-login', methods=['GET', 'POST'])
def customer_login():
    if 'customer_id' in session:
        return redirect('/public_products')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM customers WHERE email = %s AND password = %s", (email, hashed_password))
        customer = cur.fetchone()
        cur.close()
        conn.close()

        if customer:
            session['customer_id'] = customer['id']
            return redirect('/public_products')
        else:
            return render_template('customer_login.html', error_message="❌ Invalid email or password!")

    return render_template('customer_login.html')

@app.route('/customer-logout')
def customer_logout():
    session.pop('customer_id', None)
    return redirect('/choose-role')
from flask import Flask, request, render_template, redirect, session, flash
import mysql.connector
import hashlib
@app.route('/buy_product', methods=['POST'])


def buy_product():
    if 'customer_id' not in session:

        flash("❌ Please log in to make a purchase!", "error")
        return redirect('/login')

    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    if not product_id or not quantity:
        flash("❌ Product ID and quantity are required!", "error")
        return redirect('/products')

    try:
        quantity = int(quantity)
        if quantity < 1:
            flash("❌ Quantity must be at least 1!", "error")
            return redirect('/products')
    except ValueError:
        flash("❌ Invalid quantity!", "error")
        return redirect('/products')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)

    # Fetch product details
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    if not product:
        flash("❌ Product not found!", "error")
        return redirect('/products')

    if product["quantity"] < quantity:
        flash("❌ Not enough stock available!", "error")
        return redirect('/products')

    # Reduce stock
    new_quantity = product["quantity"] - quantity
    cur.execute("UPDATE products SET quantity = %s WHERE id = %s", (new_quantity, product_id))

    # Record sale with user_id
    customer_id = session['customer_id']

    total_price = product["price"] * quantity
    cur.execute(
    "INSERT INTO sales (customer_id, product_id, quantity_sold, total_price, sale_date) VALUES (%s, %s, %s, %s, NOW())",
    (session['customer_id'], product_id, quantity, total_price)
)






    conn.commit()
    cur.close()
    conn.close()

    # Redirect to bill page after purchase
    return redirect(f'/bill?product_id={product_id}&quantity={quantity}&total={total_price}')





@app.route('/download_bill')
def download_bill():
    product_name = request.args.get('product_name', 'Unknown Product')
    quantity = request.args.get('quantity', '1')
    total_price = request.args.get('total_price', '0')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # Get page dimensions

    # 🎨 HEADER: Title & Logo
    p.setFillColor(colors.blue)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(200, height - 50, "🛍 SMART SHOP - INVOICE")

    # Placeholder for logo
    p.setFillColor(colors.gray)
    p.setFont("Helvetica", 10)
    p.drawString(480, height - 50, "[LOGO]")  # Simulating a company logo

    # 🖋 Decorative Line
    p.setStrokeColor(colors.blue)
    p.setLineWidth(2)
    p.line(50, height - 60, 550, height - 60)

    # 📦 PRODUCT DETAILS BOX
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(80, height - 120, "Product Details:")

    p.setFont("Helvetica", 12)
    p.drawString(100, height - 150, f"📌 Product: {product_name}")
    p.drawString(100, height - 170, f"🔢 Quantity: {quantity}")
    p.drawString(100, height - 190, f"💰 Total Price: ₹{total_price}")
    p.drawString(100, height - 210, f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 🖋 BORDER AROUND PRODUCT DETAILS
    p.setStrokeColor(colors.gray)
    p.setLineWidth(1)
    p.rect(70, height - 220, 400, 90, stroke=1, fill=0)

    # 💳 PAYMENT STATUS
    p.setFont("Helvetica-Bold", 14)
    p.drawString(80, height - 260, "Payment Status:")
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.green)
    p.drawString(100, height - 280, "✅ PAID")

    # 🖊 SIGNATURE LINE
    p.setStrokeColor(colors.black)
    p.line(350, height - 320, 500, height - 320)
    p.setFont("Helvetica", 10)
    p.drawString(380, height - 335, "Authorized Signature")

    # 📄 Footer Note
    p.setFillColor(colors.darkgray)
    p.setFont("Helvetica", 10)
    p.drawString(180, 50, "Thank you for shopping with Smart Shop! 🛒")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    return Response(buffer, mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=invoice.pdf"})



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, hashed_password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            return redirect('/')
        else:
            return render_template('login.html', error_message="❌ Invalid email or password!")
        

    return render_template('login.html')





# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/home')

# Product List Route
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/choose-role')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('role_selection.html', products=products)

@app.route('/products')
def product_list():
    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('index.html', products=products)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
    SELECT p.name, 
           SUM(s.quantity_sold) AS quantity_sold, 
           SUM(s.total_price) AS total_revenue
    FROM sales s
    JOIN products p ON s.product_id = p.id
    GROUP BY p.name
""")

    
    sales_data = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('dashboard.html', sales=sales_data)



@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        distributor = request.form.get('distributor')
        quantity = request.form.get('quantity')

        if not product_id or not distributor or not quantity:
            flash("❌ All fields are required!", "error")
        else:
            try:
                quantity = int(quantity)
                if quantity < 1:
                    flash("❌ Quantity must be at least 1!", "error")
                else:
                    # Update inventory table
                    cur.execute("INSERT INTO inventory (product_id, distributor, stock_quantity) VALUES (%s, %s, %s)", 
                                (product_id, distributor, quantity))
                    
                    # Update product stock
                    cur.execute("UPDATE products SET quantity = quantity + %s WHERE id = %s", 
                                (quantity, product_id))
                    conn.commit()
                    flash("✅ Inventory updated successfully!", "success")
            except ValueError:
                flash("❌ Invalid quantity!", "error")
    
    # Fetch inventory records
    cur.execute("SELECT i.id, p.name AS product, i.distributor, i.stock_quantity, i.last_updated FROM inventory i JOIN products p ON i.product_id = p.id")
    inventory_records = cur.fetchall()

    # Fetch product list for dropdown
    cur.execute("SELECT id, name FROM products")
    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('inventory.html', inventory_records=inventory_records, products=products)




# Add Product Route
@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect('/login')

    name = request.form.get('name')
    price = request.form.get('price')
    quantity = request.form.get('quantity')

    if not name or not price or not quantity:
        return "❌ Name, price, and quantity are required!", 400

    try:
        price = float(price)
        quantity = int(quantity)
    except ValueError:
        return "❌ Invalid price or quantity!", 400

    try:
        # Connecting to the database
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        
        # Inserting the new product
        cur.execute("INSERT INTO products (name, price, quantity) VALUES (%s, %s, %s)", (name, price, quantity))
        conn.commit()
        
        cur.close()
        conn.close()
        
    except mysql.connector.Error as err:
        return f"❌ Database error: {err}", 500
    
    return redirect('/products')  # Redirecting to the product list page



@app.route('/bill')
def bill():
    if 'customer_id' not in session:
        return redirect('/login')

    product_id = request.args.get('product_id')
    quantity = request.args.get('quantity')
    total_price = request.args.get('total')

    if not product_id or not quantity or not total_price:
        flash("❌ Missing billing details!", "error")
        return redirect('/products')

    # Convert quantity to int
    try:
        quantity = int(quantity)
    except ValueError:
        flash("❌ Invalid quantity!", "error")
        return redirect('/products')

    # Fetch product details
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()

    if not product:
        flash("❌ Product not found!", "error")
        return redirect('/products')

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template("bill.html", product=product, quantity=quantity, total_price=total_price, current_time=current_time)


@app.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor(dictionary=True)

    # Assuming there is a sales table with a sale_date column (adjust as per your table structure)
    cur.execute("""
    SELECT p.name, 
       SUM(s.quantity_sold) AS quantity_sold, 
       SUM(s.total_price) AS total_revenue
FROM sales s
JOIN products p ON s.product_id = p.id
WHERE s.sale_date >= CURDATE() - INTERVAL 1 MONTH
GROUP BY p.name;
s
    """)

    sales_data = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('sales.html', sales=sales_data)

@app.route('/choose-role')
def choose_role():
    return render_template('role_selection.html')



# Show Available Routes (Debugging)
@app.route('/routes')
def show_routes():
    output = []
    for rule in app.url_map.iter_rules():
        output.append(f"{rule.endpoint}: {rule.rule}")
    return "<br>".join(output)

if __name__ == '__main__':
    app.run(debug=True)