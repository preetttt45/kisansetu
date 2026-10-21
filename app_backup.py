from flask import Flask, render_template, request, session, redirect, url_for
from database.database import init_db, get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Required for Flask sessions
app.secret_key = "kesansetu-secret-key"


@app.route("/")
def home():
    return "Welcome to KisanSetu AI"


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

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

        return "Invalid email or password!"

    return render_template("login.html")

@app.route("/farmer/dashboard")
def farmer_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "farmer":
        return "Access denied!"

    return render_template(
        "farmer/dashboard.html",
        name=session["name"]
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
        order = connection.execute("""
            SELECT orders.id
            FROM orders
            JOIN products ON orders.product_id = products.id
            WHERE orders.id = ?
              AND products.farmer_id = ?
              AND orders.status = 'Pending'
        """, (order_id, session["user_id"])).fetchone()

        if order is None:
            return "Order not found or already processed.", 404

        connection.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
        """, (new_status, order_id))

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("farmer_orders"))





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

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            return "Product not found.", 404

        if quantity > product["quantity"]:
            return "Requested quantity is unavailable.", 400

        total_price = quantity * product["price"]

        connection.execute(
            """
            INSERT INTO orders
            (buyer_id, product_id, quantity, total_price)
            VALUES (?, ?, ?, ?)
            """,
            (
                session["user_id"],
                product_id,
                quantity,
                total_price
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return f"Order placed successfully! Total price: ₹{total_price:.2f}"



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)