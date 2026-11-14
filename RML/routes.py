from functools import wraps
from datetime import datetime
import random
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db

main_bp = Blueprint("main", __name__)


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("main.login"))
            if role and session.get("role") != role:
                if session.get("role") != "admin":
                    flash("You do not have permission to access that page.", "danger")
                    return redirect(url_for("main.home"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@main_bp.route("/")
def home():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("main.admin_dashboard"))
    if role == "driver":
        return redirect(url_for("main.driver_schedule"))
    if role == "customer":
        return redirect(url_for("main.customer_catalog"))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    selected_role = request.args.get("role", "customer")
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        portal_role = request.form.get("portal_role", "customer")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE (email = ? OR staff_id = ?) AND is_active = 1",
            (identifier, identifier),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("main.home"))

        flash("Invalid credentials or inactive account.", "danger")
        selected_role = portal_role

    return render_template("auth/login.html", selected_role=selected_role)


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("main.register"))

        conn.execute(
            "INSERT INTO users (name, email, phone, address, password_hash, role) VALUES (?, ?, ?, ?, ?, 'customer')",
            (name, email, phone, address, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        flash("Account created! You can now sign in.", "success")
        return redirect(url_for("main.login", role="customer"))

    return render_template("auth/register.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/customer/catalog")
@login_required("customer")
def customer_catalog():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()

    conn = get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()

    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    query += " ORDER BY p.id"
    products = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "customer/catalog.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
    )


@main_bp.route("/customer/cart/add", methods=["POST"])
@login_required("customer")
def cart_add():
    product_id = str(request.form.get("product_id"))
    qty = int(request.form.get("quantity", 1))
    if qty < 1:
        qty = 1

    cart = session.get("cart", {})
    cart[product_id] = cart.get(product_id, 0) + qty
    session["cart"] = cart
    flash("Added item to your cart.", "success")
    return redirect(request.referrer or url_for("main.customer_catalog"))


@main_bp.route("/customer/cart/update", methods=["POST"])
@login_required("customer")
def cart_update():
    product_id = str(request.form.get("product_id"))
    qty = int(request.form.get("quantity", 0))
    cart = session.get("cart", {})

    if qty <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = qty

    session["cart"] = cart
    return redirect(url_for("main.customer_checkout"))


@main_bp.route("/customer/checkout", methods=["GET", "POST"])
@login_required("customer")
def customer_checkout():
    cart = session.get("cart", {})
    conn = get_db()

    cart_items = []
    subtotal = 0.0
    if cart:
        placeholders = ",".join("?" for _ in cart.keys())
        rows = conn.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})", list(cart.keys())
        ).fetchall()
        for row in rows:
            qty = cart.get(str(row["id"]), 0)
            line_total = qty * row["price"]
            subtotal += line_total
            cart_items.append({"product": row, "quantity": qty, "line_total": line_total})

    delivery_fee = 1500.00 if cart_items else 0.00
    vat_amount = round(subtotal * 0.12, 2)
    total_amount = round(subtotal + delivery_fee + vat_amount, 2)

    if request.method == "POST":
        if not cart_items:
            conn.close()
            flash("Your cart is empty.", "warning")
            return redirect(url_for("main.customer_catalog"))

        recipient_name = request.form.get("recipient_name", "").strip()
        phone = request.form.get("phone", "").strip()
        delivery_address = request.form.get("delivery_address", "").strip()
        preferred_date = request.form.get("preferred_date", "").strip()
        delivery_slot = request.form.get("delivery_slot", "Morning (08:00 - 12:00)")
        special_instructions = request.form.get("special_instructions", "").strip()

        order_code = f"#RML-{random.randint(1100, 9999)}"
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (
                order_code, customer_id, recipient_name, phone, delivery_address,
                preferred_date, delivery_slot, special_instructions,
                subtotal, delivery_fee, vat_amount, total_amount, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                order_code,
                session["user_id"],
                recipient_name,
                phone,
                delivery_address,
                preferred_date,
                delivery_slot,
                special_instructions,
                subtotal,
                delivery_fee,
                vat_amount,
                total_amount,
            ),
        )
        order_id = cur.lastrowid

        for item in cart_items:
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
                (order_id, item["product"]["id"], item["quantity"], item["product"]["price"], item["line_total"]),
            )

        conn.commit()
        conn.close()
        session["cart"] = {}
        return redirect(url_for("main.customer_payment", order_id=order_id))

    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template(
        "customer/checkout.html",
        cart_items=cart_items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        vat_amount=vat_amount,
        total_amount=total_amount,
        user=user,
    )


@main_bp.route("/customer/payment/<int:order_id>", methods=["GET", "POST"])
@login_required("customer")
def customer_payment(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()

    if request.method == "POST":
        method = request.form.get("method", "cash")
        ref = request.form.get("reference_number", "").strip()
        note = request.form.get("receipt_note", "").strip()

        if method == "cash" and not ref:
            ref = f"COD-{order['id']}"

        existing = conn.execute("SELECT id FROM payments WHERE order_id = ?", (order_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE payments SET method=?, reference_number=?, receipt_note=?, payment_status='pending', paid_at=datetime('now','localtime') WHERE order_id=?",
                (method, ref, note, order_id),
            )
        else:
            conn.execute(
                "INSERT INTO payments (order_id, method, reference_number, receipt_note, amount, payment_status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (order_id, method, ref, note, order["total_amount"]),
            )
        conn.commit()
        conn.close()
        flash("Payment details submitted!", "success")
        return redirect(url_for("main.customer_order_tracking", order_id=order_id))

    payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return render_template("customer/payment.html", order=order, items=items, payment=payment)


@main_bp.route("/customer/orders")
@login_required("customer")
def customer_orders():
    conn = get_db()
    orders = conn.execute(
        """
        SELECT o.*, p.method AS payment_method, p.payment_status,
               d.delivery_status, d.delivery_code
        FROM orders o
        LEFT JOIN payments p ON o.id = p.order_id
        LEFT JOIN deliveries d ON o.id = d.order_id
        WHERE o.customer_id = ?
        ORDER BY o.id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/orders.html", orders=orders)


@main_bp.route("/customer/orders/<int:order_id>/tracking")
@login_required("customer")
def customer_order_tracking(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchone()
    delivery = conn.execute(
        """
        SELECT d.*, u.name AS driver_name, u.phone AS driver_phone,
               t.truck_code, t.plate_number
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        WHERE d.order_id = ?
        """,
        (order_id,),
    ).fetchone()
    conn.close()

    return render_template(
        "customer/tracking.html",
        order=order,
        items=items,
        payment=payment,
        delivery=delivery,
    )


@main_bp.route("/customer/payment-history")
@login_required("customer")
def customer_payment_history():
    conn = get_db()
    payments = conn.execute(
        """
        SELECT p.*, o.order_code, o.created_at AS order_date
        FROM payments p
        JOIN orders o ON p.order_id = o.id
        WHERE o.customer_id = ?
        ORDER BY p.id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/payment_history.html", payments=payments)


@main_bp.route("/customer/support")
@login_required("customer")
def customer_support():
    return render_template("customer/support.html")


@main_bp.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    conn = get_db()
    pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'pending'").fetchone()[0]
    low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity <= low_stock_threshold").fetchone()[0]
    in_progress_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status IN ('assigned', 'loading', 'en_route')").fetchone()[0]
    stock_in = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory_logs WHERE movement_type = 'stock_in'").fetchone()[0]
    stock_out = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory_logs WHERE movement_type = 'stock_out'").fetchone()[0]
    payments_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    ready_dispatch = conn.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'approved'").fetchone()[0]
    pending_receipts = conn.execute("SELECT COUNT(*) FROM payments WHERE payment_status = 'pending'").fetchone()[0]
    conn.close()

    return render_template(
        "admin/dashboard.html",
        pending_orders=pending_orders,
        low_stock=low_stock,
        in_progress_deliveries=in_progress_deliveries,
        stock_in=stock_in,
        stock_out=stock_out,
        payments_count=payments_count,
        ready_dispatch=ready_dispatch,
        pending_receipts=pending_receipts,
    )


@main_bp.route("/admin/orders")
@login_required("admin")
def admin_orders():
    tab = request.args.get("tab", "pending")
    conn = get_db()

    base_sql = """
        SELECT o.*, u.name AS customer_name,
               MIN(CASE WHEN p.stock_quantity >= oi.quantity THEN 1 ELSE 0 END) AS all_in_stock
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.id
    """
    if tab == "pending":
        where = " WHERE o.order_status = 'pending'"
    elif tab == "ready":
        where = " WHERE o.order_status = 'approved'"
    else:
        where = ""

    orders = conn.execute(
        base_sql + where + " GROUP BY o.id ORDER BY o.id DESC"
    ).fetchall()

    counts = {
        "pending": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status='pending'").fetchone()[0],
        "ready": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status='approved'").fetchone()[0],
        "all": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }

    items_by_order = {}
    all_items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit, p.stock_quantity
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        """
    ).fetchall()
    for item in all_items:
        items_by_order.setdefault(item["order_id"], []).append(item)

    conn.close()
    return render_template(
        "admin/orders.html",
        orders=orders,
        tab=tab,
        counts=counts,
        items_by_order=items_by_order,
    )


@main_bp.route("/admin/orders/<int:order_id>/decision", methods=["POST"])
@login_required("admin")
def admin_order_decision(order_id):
    decision = request.form.get("decision")
    reason = request.form.get("rejection_reason", "").strip()
    conn = get_db()

    if decision == "approve":
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        for item in items:
            conn.execute(
                "UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, 'stock_out', ?, ?, ?)",
                (item["product_id"], item["quantity"], f"Approved Order ID #{order_id}", session["user_id"]),
            )
        conn.execute("UPDATE orders SET order_status = 'approved' WHERE id = ?", (order_id,))
        flash("Order approved and stock reserved.", "success")
    elif decision == "reject":
        conn.execute(
            "UPDATE orders SET order_status = 'rejected', rejection_reason = ? WHERE id = ?",
            (reason or "Insufficient stock / cancelled by admin", order_id),
        )
        flash("Order rejected.", "warning")

    conn.commit()
    conn.close()
    return redirect(url_for("main.admin_orders"))


@main_bp.route("/admin/inventory", methods=["GET", "POST"])
@login_required("admin")
def admin_inventory():
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_product":
            name = request.form.get("name", "").strip()
            category_id = request.form.get("category_id")
            description = request.form.get("description", "").strip()
            unit = request.form.get("unit", "pc").strip()
            price = float(request.form.get("price", 0))
            stock_quantity = int(request.form.get("stock_quantity", 0))
            low_stock_threshold = int(request.form.get("low_stock_threshold", 20))
            image_url = request.form.get("image_url", "").strip() or "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500&auto=format&fit=crop"

            conn.execute(
                "INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url),
            )
            conn.commit()
            flash(f"Product '{name}' saved.", "success")

        elif action == "stock_movement":
            product_id = int(request.form.get("product_id"))
            movement_type = request.form.get("movement_type", "stock_in")
            quantity = int(request.form.get("quantity", 0))
            remarks = request.form.get("remarks", "").strip()

            if movement_type == "stock_in":
                conn.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (quantity, product_id))
            else:
                conn.execute("UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?", (quantity, product_id))

            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, ?, ?, ?, ?)",
                (product_id, movement_type, quantity, remarks, session["user_id"]),
            )
            conn.commit()
            flash("Stock movement recorded.", "success")

        conn.close()
        return redirect(url_for("main.admin_inventory"))

    products = conn.execute(
        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON p.category_id = c.id ORDER BY p.id"
    ).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    low_stock_count = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity <= low_stock_threshold").fetchone()[0]
    logs = conn.execute(
        """
        SELECT l.*, p.name AS product_name, u.name AS staff_name
        FROM inventory_logs l
        JOIN products p ON l.product_id = p.id
        LEFT JOIN users u ON l.created_by = u.id
        ORDER BY l.id DESC LIMIT 10
        """
    ).fetchall()
    conn.close()

    return render_template(
        "admin/inventory.html",
        products=products,
        categories=categories,
        low_stock_count=low_stock_count,
        logs=logs,
    )


@main_bp.route("/admin/deliveries", methods=["GET", "POST"])
@login_required("admin")
def admin_deliveries():
    conn = get_db()

    if request.method == "POST":
        order_id = int(request.form.get("order_id"))
        driver_id = int(request.form.get("driver_id"))
        truck_id = int(request.form.get("truck_id"))
        delivery_window = request.form.get("delivery_window", "").strip()

        existing = conn.execute("SELECT id FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE deliveries SET driver_id=?, truck_id=?, delivery_window=?, delivery_status='assigned' WHERE order_id=?",
                (driver_id, truck_id, delivery_window, order_id),
            )
        else:
            d_code = f"DLV-{datetime.now().strftime('%m%d')}-{random.randint(10, 99)}"
            conn.execute(
                "INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status) VALUES (?, ?, ?, ?, ?, 'assigned')",
                (d_code, order_id, driver_id, truck_id, delivery_window),
            )

        conn.execute("UPDATE orders SET order_status = 'preparing' WHERE id = ?", (order_id,))
        conn.commit()
        flash("Delivery assigned to driver and truck.", "success")
        conn.close()
        return redirect(url_for("main.admin_deliveries"))

    counts = {
        "queued": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status='approved' AND id NOT IN (SELECT order_id FROM deliveries)").fetchone()[0],
        "assigned": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status IN ('assigned', 'loading')").fetchone()[0],
        "en_route": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status='en_route'").fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status='delivered'").fetchone()[0],
    }

    ready_orders = conn.execute(
        """
        SELECT o.*, u.name AS customer_name
        FROM orders o JOIN users u ON o.customer_id = u.id
        WHERE o.order_status IN ('approved', 'preparing')
        ORDER BY o.id DESC
        """
    ).fetchall()
    drivers = conn.execute("SELECT * FROM users WHERE role='driver' AND is_active=1").fetchall()
    trucks = conn.execute("SELECT * FROM trucks").fetchall()
    deliveries = conn.execute(
        """
        SELECT d.*, o.order_code, o.recipient_name, o.delivery_address,
               u.name AS driver_name, t.truck_code, t.plate_number
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        ORDER BY d.id DESC
        """
    ).fetchall()
    conn.close()

    return render_template(
        "admin/deliveries.html",
        counts=counts,
        ready_orders=ready_orders,
        drivers=drivers,
        trucks=trucks,
        deliveries=deliveries,
    )


@main_bp.route("/admin/customers")
@login_required("admin")
def admin_customers():
    conn = get_db()
    customers = conn.execute(
        """
        SELECT u.*, COUNT(o.id) AS total_orders, COALESCE(SUM(o.total_amount), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.customer_id
        WHERE u.role = 'customer'
        GROUP BY u.id
        ORDER BY u.id DESC
        """
    ).fetchall()
    conn.close()
    return render_template("admin/customers.html", customers=customers)


@main_bp.route("/admin/payments", methods=["GET", "POST"])
@login_required("admin")
def admin_payments():
    conn = get_db()
    if request.method == "POST":
        payment_id = int(request.form.get("payment_id"))
        status = request.form.get("status")
        conn.execute("UPDATE payments SET payment_status = ? WHERE id = ?", (status, payment_id))
        conn.commit()
        flash(f"Payment marked as {status}.", "success")
        conn.close()
        return redirect(url_for("main.admin_payments"))

    payments = conn.execute(
        """
        SELECT p.*, o.order_code, o.recipient_name
        FROM payments p
        JOIN orders o ON p.order_id = o.id
        ORDER BY p.id DESC
        """
    ).fetchall()
    conn.close()
    return render_template("admin/payments.html", payments=payments)


@main_bp.route("/admin/reports")
@login_required("admin")
def admin_reports():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()
    query = """
        SELECT o.*, p.method AS payment_method, p.payment_status
        FROM orders o
        LEFT JOIN payments p ON o.id = p.order_id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND date(o.created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(o.created_at) <= date(?)"
        params.append(end_date)
    query += " ORDER BY o.id DESC"

    orders = conn.execute(query, params).fetchall()
    total_sales = sum(o["total_amount"] for o in orders if o["order_status"] != "rejected")
    low_stock_items = conn.execute(
        "SELECT * FROM products WHERE stock_quantity <= low_stock_threshold"
    ).fetchall()
    conn.close()

    return render_template(
        "admin/reports.html",
        orders=orders,
        total_sales=total_sales,
        low_stock_items=low_stock_items,
        start_date=start_date,
        end_date=end_date,
    )


@main_bp.route("/admin/access", methods=["GET", "POST"])
@login_required("admin")
def admin_access():
    conn = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_staff":
            name = request.form.get("name", "").strip()
            staff_id = request.form.get("staff_id", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            role = request.form.get("role", "driver")
            password = request.form.get("password", "rml12345")
            conn.execute(
                "INSERT INTO users (staff_id, name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, ?, ?)",
                (staff_id, name, email, phone, generate_password_hash(password), role),
            )
            conn.commit()
            flash(f"Created {role} account for {name}.", "success")
        elif action == "toggle_active":
            uid = int(request.form.get("user_id"))
            conn.execute("UPDATE users SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (uid,))
            conn.commit()
            flash("Account status updated.", "info")

        conn.close()
        return redirect(url_for("main.admin_access"))

    users = conn.execute("SELECT * FROM users ORDER BY role, name").fetchall()
    conn.close()
    return render_template("admin/access.html", users=users)


@main_bp.route("/driver/schedule")
@login_required("driver")
def driver_schedule():
    conn = get_db()
    uid = session["user_id"]

    if session.get("role") == "admin":
        deliveries = conn.execute(
            """
            SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.phone,
                   t.truck_code, t.plate_number
            FROM deliveries d
            JOIN orders o ON d.order_id = o.id
            LEFT JOIN trucks t ON d.truck_id = t.id
            ORDER BY d.id DESC
            """
        ).fetchall()
    else:
        deliveries = conn.execute(
            """
            SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.phone,
                   t.truck_code, t.plate_number
            FROM deliveries d
            JOIN orders o ON d.order_id = o.id
            LEFT JOIN trucks t ON d.truck_id = t.id
            WHERE d.driver_id = ?
            ORDER BY d.id DESC
            """,
            (uid,),
        ).fetchall()

    delivered_count = sum(1 for d in deliveries if d["delivery_status"] == "delivered")
    conn.close()
    return render_template(
        "driver/schedule.html",
        deliveries=deliveries,
        delivered_count=delivered_count,
        total_count=len(deliveries),
    )


@main_bp.route("/driver/delivery/<int:delivery_id>", methods=["GET", "POST"])
@login_required("driver")
def driver_delivery_task(delivery_id):
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_status":
            new_status = request.form.get("delivery_status")
            conn.execute("UPDATE deliveries SET delivery_status = ? WHERE id = ?", (new_status, delivery_id))
            if new_status == "en_route":
                conn.execute(
                    "UPDATE orders SET order_status = 'in_transit' WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)",
                    (delivery_id,),
                )
            conn.commit()
            flash(f"Delivery status updated to '{new_status}'.", "success")

        elif action == "confirm_delivered":
            recipient = request.form.get("recipient_received_by", "").strip()
            role = request.form.get("recipient_role", "").strip()
            notes = request.form.get("delivery_notes", "").strip()
            conn.execute(
                """
                UPDATE deliveries
                SET delivery_status='delivered',
                    recipient_received_by=?,
                    recipient_role=?,
                    delivery_notes=?,
                    delivered_at=datetime('now', 'localtime')
                WHERE id=?
                """,
                (recipient, role, notes, delivery_id),
            )
            conn.execute(
                "UPDATE orders SET order_status = 'delivered' WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)",
                (delivery_id,),
            )
            conn.commit()
            flash("Delivery confirmed and marked as Delivered!", "success")

        conn.close()
        return redirect(url_for("main.driver_delivery_task", delivery_id=delivery_id))

    delivery = conn.execute(
        """
        SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.phone, o.special_instructions,
               t.truck_code, t.plate_number, u.name AS driver_name
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        WHERE d.id = ?
        """,
        (delivery_id,),
    ).fetchone()

    if not delivery:
        conn.close()
        flash("Delivery task not found.", "danger")
        return redirect(url_for("main.driver_schedule"))

    items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        (delivery["order_id"],),
    ).fetchall()
    conn.close()

    return render_template("driver/delivery_task.html", delivery=delivery, items=items)


@main_bp.route("/api/gps/update", methods=["POST"])
@login_required()
def api_gps_update():
    data = request.get_json(silent=True) or {}
    delivery_id = data.get("delivery_id")
    lat = data.get("lat")
    lng = data.get("lng")

    if not delivery_id or lat is None or lng is None:
        return jsonify({"ok": False, "error": "Missing coordinates"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE deliveries SET current_lat = ?, current_lng = ?, last_gps_update = datetime('now', 'localtime') WHERE id = ?",
        (float(lat), float(lng), int(delivery_id)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "lat": float(lat), "lng": float(lng)})


@main_bp.route("/api/gps/delivery/<int:delivery_id>")
@login_required()
def api_gps_get(delivery_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, delivery_code, delivery_status, current_lat, current_lng, last_gps_update FROM deliveries WHERE id = ?",
        (delivery_id,),
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False}), 404
    return jsonify(dict(row))
