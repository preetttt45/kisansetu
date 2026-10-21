from flask import Flask, render_template, request, session, redirect, url_for
from database.database import init_db, get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Required for Flask sessions
app.secret_key = "kesansetu-secret-key"

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            return "Please fill in all fields.", 400

        return render_template("contact.html", success=True)

    return render_template("contact.html", success=False)

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form.get("role", "").strip().lower()

        if role not in ["farmer", "buyer"]:
            return "Invalid role selected.", 400

        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, password, role)
            )

            connection.commit()

        except Exception as e:
            connection.close()
            return f"Registration failed: {e}"

        connection.close()

        return "Registration successful!"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT * FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]


            if user["role"] == "farmer":
                return redirect("/farmer/dashboard")

            elif user["role"] == "buyer":
                return redirect("/buyer/dashboard")
            
            elif user["role"] == "admin":
                 return redirect(url_for("admin_dashboard"))

            

        return "Invalid email or password!"

    return render_template("login.html")



@app.route("/farmer/dashboard")
def farmer_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!"

    farmer_id = session["user_id"]

    connection = get_db_connection()

    total_products = connection.execute(
        "SELECT COUNT(*) FROM products WHERE farmer_id = ?",
        (farmer_id,)
    ).fetchone()[0]

    total_orders = connection.execute("""
        SELECT COUNT(*)
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE products.farmer_id = ?
    """, (farmer_id,)).fetchone()[0]

    connection.close()

    return render_template(
        "farmer/dashboard.html",
        name=session["name"],
        total_products=total_products,
        total_orders=total_orders
    )



@app.route("/farmer/add-product", methods=["GET", "POST"])
def add_product():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    if request.method == "POST":
        crop_name = request.form["crop_name"].strip()
        quantity = request.form["quantity"]
        price = request.form["price"]
        quality = request.form["quality"]
        location = request.form["location"].strip()

        try:
            quantity = float(quantity)
            price = float(price)

            if not crop_name or not location or quantity <= 0 or price <= 0:
                return "Please enter valid product details.", 400

            connection = get_db_connection()

            try:
                connection.execute(
                    """
                    INSERT INTO products
                    (farmer_id, crop_name, quantity, price, quality, location)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session["user_id"],
                        crop_name,
                        quantity,
                        price,
                        quality,
                        location
                    )
                )
                connection.commit()
            finally:
                connection.close()

            return "Product added successfully!"

        except ValueError:
            return "Quantity and price must be valid numbers.", 400

    return render_template("farmer/add_product.html")


@app.route("/farmer/my-products")
def my_products():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        products = connection.execute(
            """
            SELECT * FROM products
            WHERE farmer_id = ?
            ORDER BY created_at DESC
            """,
            (session["user_id"],)
        ).fetchall()
    finally:
        connection.close()

    return render_template(
        "farmer/my_products.html",
        products=products
    )


@app.route("/farmer/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    
    connection = get_db_connection()

    try:
        product = connection.execute(
            """
            SELECT * FROM products
            WHERE id = ? AND farmer_id = ?
            """,
            (product_id, session["user_id"])
        ).fetchone()

        if product is None:
            return "Product not found.", 404

        if request.method == "POST":
            crop_name = request.form.get("crop_name", "").strip()
            location = request.form.get("location", "").strip()
            quality = request.form.get("quality", "").strip()

            try:
                quantity = float(request.form.get("quantity", ""))
                price = float(request.form.get("price", ""))
            except (ValueError, TypeError):
                return "Quantity and price must be valid numbers.", 400

            if not crop_name or not location or quantity <= 0 or price <= 0:
                return "Please enter valid product details.", 400

            connection.execute(
                """
                UPDATE products
                SET crop_name = ?, quantity = ?, price = ?,
                    quality = ?, location = ?
                WHERE id = ? AND farmer_id = ?
                """,
                (
                    crop_name, quantity, price, quality, location,
                    product_id, session["user_id"]
                )
            )
            connection.commit()
            return redirect(url_for("my_products"))

        return render_template("farmer/edit_product.html", product=product)

    finally:
        connection.close()



@app.route("/farmer/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        product = connection.execute(
            """
            SELECT id FROM products
            WHERE id = ? AND farmer_id = ?
            """,
            (product_id, session["user_id"])
        ).fetchone()

        if product is None:
            return "Product not found.", 404

        # Keep order history intact: don't delete products with orders.
        existing_order = connection.execute(
            "SELECT id FROM orders WHERE product_id = ? LIMIT 1",
            (product_id,)
        ).fetchone()

        if existing_order:
            return (
                "This product cannot be deleted because it has order history."
            ), 400

        connection.execute(
            "DELETE FROM products WHERE id = ? AND farmer_id = ?",
            (product_id, session["user_id"])
        )
        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("my_products"))




@app.route("/farmer/orders")
def farmer_orders():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        orders = connection.execute("""
            SELECT
                orders.id,
                orders.quantity,
                orders.total_price,
                orders.status,
                products.crop_name,
                users.name AS buyer_name
            FROM orders
            JOIN products ON orders.product_id = products.id
            JOIN users ON orders.buyer_id = users.id
            WHERE products.farmer_id = ?
            ORDER BY orders.created_at DESC
        """, (session["user_id"],)).fetchall()
    finally:
        connection.close()

    return render_template(
        "farmer/orders.html",
        orders=orders
    )


@app.route("/farmer/update-order/<int:order_id>", methods=["POST"])
def update_order(order_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "farmer":
        return "Access denied!", 403

    new_status = request.form.get("status")

    if new_status not in ["Accepted", "Rejected"]:
        return "Invalid order status.", 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        order = connection.execute("""
            SELECT orders.id, orders.product_id, orders.quantity
            FROM orders
            JOIN products ON orders.product_id = products.id
            WHERE orders.id = ?
              AND products.farmer_id = ?
              AND orders.status = 'Pending'
        """, (order_id, session["user_id"])).fetchone()

        if order is None:
            connection.rollback()
            return "Order not found or already processed.", 404

        # Restore reserved stock if farmer rejects the order
        if new_status == "Rejected":
            connection.execute("""
                UPDATE products
                SET quantity = quantity + ?
                WHERE id = ?
            """, (order["quantity"], order["product_id"]))

        connection.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ? AND status = 'Pending'
        """, (new_status, order_id))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("farmer_orders"))



@app.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        total_users = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_farmers = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'farmer'"
        ).fetchone()[0]

        total_buyers = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'buyer'"
        ).fetchone()[0]

        total_products = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        total_orders = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

    finally:
        connection.close()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_farmers=total_farmers,
        total_buyers=total_buyers,
        total_products=total_products,
        total_orders=total_orders
    )



@app.route("/admin/users")
def admin_users():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        users = connection.execute("""
            SELECT id, name, email, role
            FROM users
            ORDER BY id DESC
        """).fetchall()
    finally:
        connection.close()

    return render_template(
        "admin/users.html",
        users=users
    )



@app.route("/admin/products")
def admin_products():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        products = connection.execute("""
            SELECT
                products.id,
                products.crop_name,
                products.quantity,
                products.price,
                products.quality,
                products.location,
                users.name AS farmer_name
            FROM products
            JOIN users ON products.farmer_id = users.id
            ORDER BY products.id DESC
        """).fetchall()
    finally:
        connection.close()

    return render_template(
        "admin/products.html",
        products=products
    )



@app.route("/admin/orders")
def admin_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
    
        orders = connection.execute("""
            SELECT
                orders.id,
                orders.quantity,
                orders.total_price,
                orders.status,
                orders.created_at,
                products.crop_name,
                buyer.name AS buyer_name,
                farmer.name AS farmer_name,
                logistics.delivery_method,
                logistics.delivery_address,
                logistics.transport_name,
                logistics.vehicle_number,
                logistics.driver_contact,
                logistics.delivery_status,
                logistics.assigned_at,
                logistics.delivered_at
            FROM orders
            JOIN products
                ON orders.product_id = products.id
            JOIN users AS buyer
                ON orders.buyer_id = buyer.id
            JOIN users AS farmer
                ON products.farmer_id = farmer.id
            LEFT JOIN logistics
                ON logistics.order_id = orders.id
            ORDER BY orders.id DESC
        """).fetchall()
    
    
    finally:
        connection.close()

    return render_template(
        "admin/orders.html",
        orders=orders
    )




@app.route("/buyer/dashboard")
def buyer_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "buyer":
        return "Access denied!"

    return render_template(
        "buyer/dashboard.html",
        name=session["name"]
    )


@app.route("/buyer/marketplace")
def marketplace():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "buyer":
        return "Access denied!", 403

    connection = get_db_connection()

    try:
        products = connection.execute("""
            SELECT products.*, users.name AS farmer_name
            FROM products
            JOIN users ON products.farmer_id = users.id
            ORDER BY products.created_at DESC
        """).fetchall()
    finally:
        connection.close()

    return render_template(
        "buyer/marketplace.html",
        products=products
    )




@app.route("/buyer/place-order/<int:product_id>", methods=["POST"])
def place_order(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "buyer":
        return "Access denied!", 403

    try:
        quantity = float(request.form.get("quantity", 0))
    except (ValueError, TypeError):
        return "Invalid quantity.", 400

    if quantity <= 0:
        return "Quantity must be greater than zero.", 400

    delivery_method = request.form.get("delivery_method", "").strip()
    delivery_address = request.form.get("delivery_address", "").strip()

    if delivery_method not in ("Delivery", "Self Pickup"):
        return "Please select a valid delivery method.", 400

    if delivery_method == "Delivery" and not delivery_address:
        return "Delivery address is required.", 400

    if delivery_method == "Self Pickup":
        delivery_address = None

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            connection.rollback()
            return "Product not found.", 404

        if quantity > product["quantity"]:
            connection.rollback()
            return "Requested quantity is unavailable.", 400

        total_price = quantity * product["price"]

        # Reserve stock immediately
        cursor = connection.execute("""
            UPDATE products
            SET quantity = quantity - ?
            WHERE id = ? AND quantity >= ?
        """, (quantity, product_id, quantity))

        if cursor.rowcount != 1:
            connection.rollback()
            return "Requested quantity is unavailable.", 400

        cursor = connection.execute("""
            INSERT INTO orders
                (buyer_id, product_id, quantity, total_price)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            product_id,
            quantity,
            total_price
        ))

        order_id = cursor.lastrowid

        connection.execute("""
            INSERT INTO logistics
                (order_id, delivery_method, delivery_address, delivery_status)
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            delivery_method,
            delivery_address,
            "Pending Assignment" if delivery_method == "Delivery"
            else "Self Pickup"
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return render_template(
        "buyer/order_success.html",
        total_price=total_price,
        quantity=quantity,
        delivery_method=delivery_method,
        delivery_address=delivery_address
    )





@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



if __name__ == "__main__":
    init_db()
    app.run(debug=True)