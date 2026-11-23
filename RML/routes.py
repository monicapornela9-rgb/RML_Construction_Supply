from functools import wraps
from datetime import datetime, date, timedelta
import random
import os
import re
import secrets
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    abort,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from db import get_db, create_notification, sync_customer_notifications

main_bp = Blueprint("main", __name__)


def login_required(role=None):
    """Ensure user is logged in, verify role, and prevent cross-portal access."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "warning")
                if role in ("admin", "staff"):
                    return redirect(url_for("main.admin_login"))
                elif role == "driver":
                    return redirect(url_for("main.driver_login"))
                else:
                    next_target = request.full_path if (request.query_string and request.query_string.strip()) else request.path
                    if next_target.endswith("?"):
                        next_target = next_target[:-1]
                    return redirect(url_for("main.login", next=next_target))

            user_role = session.get("role")
            if role:
                if role in ("admin", "staff"):
                    if user_role not in ("admin", "staff"):
                        flash("Access denied. Restricted to authorized administrators.", "danger")
                        if user_role == "customer":
                            return redirect(url_for("main.customer_dashboard"))
                        elif user_role == "driver":
                            return redirect(url_for("main.driver_dashboard"))
                        return redirect(url_for("main.admin_login"))
                elif role == "driver":
                    if user_role != "driver":
                        flash("Access denied. Restricted to delivery drivers.", "danger")
                        if user_role == "customer":
                            return redirect(url_for("main.customer_dashboard"))
                        elif user_role in ("admin", "staff"):
                            return redirect(url_for("main.admin_dashboard"))
                        return redirect(url_for("main.driver_login"))
                elif role == "customer":
                    if user_role != "customer":
                        flash("Please access customer features from an authorized customer session.", "warning")
                        if user_role in ("admin", "staff"):
                            return redirect(url_for("main.admin_dashboard"))
                        elif user_role == "driver":
                            return redirect(url_for("main.driver_dashboard"))
                        return redirect(url_for("main.login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def validate_password_strength(password):
    """
    Validates password against strict security policy:
    1. Minimum 8 characters.
    2. At least one uppercase letter (A-Z).
    3. At least one lowercase letter (a-z).
    4. At least one number (0-9).
    5. At least one special character (@, $, !, %, *, ?, &, #, etc.).
    6. No spaces allowed.
    7. Reject common/weak passwords.
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if " " in password:
        return False, "Password must not contain spaces."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r"[@$!%*?&#^()_\-+=\[\]{}|\\:;\"'<>,.~`]", password):
        return False, "Password must contain at least one special character (@, $, !, %, *, ?, &, #, etc.)."

    common_passwords = {
        "password", "password123", "12345678", "123456789", "qwerty123",
        "admin123", "welcome123", "letmein123", "rml12345", "construction123",
        "rmlconstruction", "adminadmin", "password1"
    }
    if password.lower() in common_passwords:
        return False, "This password is too common or easily guessed. Please choose a stronger password."
    return True, None


def validate_ph_phone(phone):
    """
    Validates Philippine mobile numbers:
    Accepts 09XXXXXXXXX (11 digits) or +639XXXXXXXXX (13 chars).
    """
    if not phone:
        return False, None
    clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if re.match(r"^09\d{9}$", clean):
        return True, clean
    if re.match(r"^\+639\d{9}$", clean):
        return True, clean
    return False, None


def validate_email_format(email):
    """Validates email format."""
    if not email:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email.strip()))


def check_login_rate_limit(conn, user_row):
    """Checks if account is temporarily locked (5 failed attempts -> 15 min lock)."""
    if not user_row:
        return False, 0
    locked_until_str = user_row["locked_until"] if "locked_until" in user_row.keys() else None
    if locked_until_str:
        try:
            locked_until = datetime.strptime(locked_until_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if now < locked_until:
                diff_sec = (locked_until - now).total_seconds()
                rem_min = max(1, int(diff_sec // 60) + 1)
                return True, rem_min
        except Exception:
            pass
    return False, 0


def record_login_failure(conn, user_id):
    """Increments failed_login_attempts. Locks for 15 minutes upon reaching 5 failures."""
    if not user_id:
        return
    row = conn.execute("SELECT failed_login_attempts FROM users WHERE id = ?", (user_id,)).fetchone()
    current_attempts = (row["failed_login_attempts"] or 0) + 1 if row else 1
    if current_attempts >= 5:
        locked_until = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?",
            (current_attempts, locked_until, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET failed_login_attempts = ? WHERE id = ?",
            (current_attempts, user_id),
        )
    conn.commit()


def reset_login_failures(conn, user_id):
    """Resets failed attempts and unlocks account after successful authentication."""
    if not user_id:
        return
    conn.execute(
        "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()


def clean_order_code(code):
    """Normalize order code for display without repeating '#' prefixes."""
    if not code:
        return ""
    code_str = str(code).strip()
    return code_str if code_str.startswith("#") else f"#{code_str}"


@main_bp.app_template_filter("order_code")
def order_code_filter(code):
    return clean_order_code(code)


def get_delivery_setting(conn, key, default=""):
    """Fetch setting value from delivery_settings table."""
    row = conn.execute("SELECT setting_value FROM delivery_settings WHERE setting_key = ?", (key,)).fetchone()
    return row["setting_value"] if row else default


def expire_stale_reservations(conn):
    """
    Checks for proposed delivery reservations past their expiration timestamp (e.g. 24 hours).
    Releases the reserved slot, truck, driver, and reverts order to pending_scheduling.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stale_orders = conn.execute(
        """
        SELECT o.id, o.order_code, o.assigned_date, o.assigned_time_slot
        FROM orders o
        WHERE o.order_status = 'awaiting_confirmation'
          AND o.reservation_expires_at IS NOT NULL
          AND o.reservation_expires_at <= ?
        """,
        (now_str,),
    ).fetchall()

    for o in stale_orders:
        conn.execute(
            """
            UPDATE orders
            SET order_status = 'pending_scheduling',
                schedule_status = 'expired',
                assigned_date = NULL,
                assigned_time_slot = NULL,
                reservation_expires_at = NULL,
                approval_notes = 'Schedule reservation expired after 24 hours without customer confirmation.'
            WHERE id = ?
            """,
            (o["id"],),
        )
        conn.execute(
            """
            UPDATE deliveries
            SET delivery_status = 'cancelled',
                driver_id = NULL,
                truck_id = NULL
            WHERE order_id = ?
            """,
            (o["id"],),
        )
    if stale_orders:
        conn.commit()
    return len(stale_orders)


def find_and_reserve_delivery_slot(conn, order_id=None):
    """
    Automatic delivery schedule proposal engine:
    1. Expires stale reservations first.
    2. Reads admin availability settings (lead time, horizon, slot capacity, timeout).
    3. Finds next available (date, time_slot) where:
       - Date & slot is configured and is_available == 1
       - Current active bookings < max_capacity
       - An active truck and driver are available (not double-booked in that slot)
    4. If found: returns dict with assigned_date, assigned_time_slot, truck_id, driver_id, expires_at.
       Else: returns None.
    """
    expire_stale_reservations(conn)

    try:
        lead_time = int(get_delivery_setting(conn, "lead_time_days", 1))
    except (ValueError, TypeError):
        lead_time = 1
    try:
        horizon = int(get_delivery_setting(conn, "horizon_days", 14))
    except (ValueError, TypeError):
        horizon = 14
    try:
        timeout_hours = int(get_delivery_setting(conn, "reservation_timeout_hours", 24))
    except (ValueError, TypeError):
        timeout_hours = 24
    try:
        default_capacity = int(get_delivery_setting(conn, "default_slot_capacity", 3))
    except (ValueError, TypeError):
        default_capacity = 3

    today = datetime.now().date()
    slots = ["Morning (08:00 - 12:00)", "Afternoon (13:00 - 17:00)"]

    active_trucks = conn.execute(
        "SELECT id, truck_code, plate_number FROM trucks WHERE status != 'maintenance' ORDER BY id"
    ).fetchall()
    active_drivers = conn.execute(
        "SELECT id, name FROM users WHERE role = 'driver' AND is_active = 1 ORDER BY id"
    ).fetchall()

    if not active_trucks or not active_drivers:
        return None

    # Search day by day starting from today + lead_time
    for i in range(lead_time, lead_time + horizon):
        day_date = today + timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")

        for slot in slots:
            avail = conn.execute(
                "SELECT max_capacity, is_available FROM delivery_availability WHERE delivery_date = ? AND time_slot = ?",
                (day_str, slot),
            ).fetchone()

            if avail:
                if not avail["is_available"]:
                    continue
                capacity = avail["max_capacity"]
            else:
                if day_date.weekday() == 6:  # Sunday closed by default if unconfigured
                    continue
                capacity = default_capacity

            # Count current active bookings for this date and slot
            exclude_clause = " AND o.id != ?" if order_id else ""
            params = [day_str, slot]
            if order_id:
                params.append(order_id)

            booked_count = conn.execute(
                f"""
                SELECT COUNT(*) FROM orders o
                WHERE o.assigned_date = ? AND o.assigned_time_slot = ?
                  AND o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
                  {exclude_clause}
                """,
                params,
            ).fetchone()[0]

            if booked_count >= capacity:
                continue

            deliv_params = [day_str, slot]
            if order_id:
                deliv_params.append(order_id)

            booked_trucks = {
                r[0] for r in conn.execute(
                    f"""
                    SELECT d.truck_id FROM deliveries d
                    JOIN orders o ON d.order_id = o.id
                    WHERE o.assigned_date = ? AND o.assigned_time_slot = ?
                      AND o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
                      AND d.truck_id IS NOT NULL
                      {exclude_clause}
                    """,
                    deliv_params,
                ).fetchall()
            }

            booked_drivers = {
                r[0] for r in conn.execute(
                    f"""
                    SELECT d.driver_id FROM deliveries d
                    JOIN orders o ON d.order_id = o.id
                    WHERE o.assigned_date = ? AND o.assigned_time_slot = ?
                      AND o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
                      AND d.driver_id IS NOT NULL
                      {exclude_clause}
                    """,
                    deliv_params,
                ).fetchall()
            }

            available_truck = next((t for t in active_trucks if t["id"] not in booked_trucks), None)
            available_driver = next((d for d in active_drivers if d["id"] not in booked_drivers), None)

            if available_truck and available_driver:
                expires_at = (datetime.now() + timedelta(hours=timeout_hours)).strftime("%Y-%m-%d %H:%M:%S")
                return {
                    "assigned_date": day_str,
                    "assigned_time_slot": slot,
                    "truck_id": available_truck["id"],
                    "truck_code": available_truck["truck_code"],
                    "driver_id": available_driver["id"],
                    "driver_name": available_driver["name"],
                    "expires_at": expires_at,
                    "timeout_hours": timeout_hours,
                }

    return None


# -------------------------------------------------------------------------
# AUTHENTICATION & HOME
# -------------------------------------------------------------------------

@main_bp.route("/")
def home():
    role = session.get("role")
    if role in ("admin", "staff"):
        return redirect(url_for("main.admin_dashboard"))
    if role == "driver":
        return redirect(url_for("main.driver_dashboard"))

    conn = get_db()
    featured_products = conn.execute(
        """
        SELECT p.*, c.name AS category_name,
               (SELECT COUNT(*) FROM product_variations pv WHERE pv.product_id = p.id AND pv.is_available = 1) AS var_count,
               (SELECT MIN(pv.price) FROM product_variations pv WHERE pv.product_id = p.id AND pv.is_available = 1) AS min_var_price
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = 1
        ORDER BY CASE WHEN p.stock_quantity > 0 THEN 0 ELSE 1 END, p.id ASC
        LIMIT 6
        """
    ).fetchall()

    categories = conn.execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) AS product_count
        FROM categories c
        WHERE (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) > 0
        ORDER BY c.id ASC
        """
    ).fetchall()
    conn.close()

    return render_template("customer/landing.html", featured_products=featured_products, categories=categories)


# -------------------------------------------------------------------------
# 1. CUSTOMER PORTAL AUTHENTICATION
# -------------------------------------------------------------------------

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("role") == "customer":
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("main.customer_dashboard"))
    elif session.get("role") in ("admin", "staff"):
        return redirect(url_for("main.admin_dashboard"))
    elif session.get("role") == "driver":
        return redirect(url_for("main.driver_dashboard"))

    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("email") or "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? AND is_active = 1",
            (identifier,),
        ).fetchone()

        if user:
            # Check if this account belongs to admin/staff or driver
            if user["role"] in ("admin", "staff"):
                conn.close()
                flash("Admin/Staff accounts must sign in via the restricted Admin Portal.", "warning")
                return redirect(url_for("main.admin_login"))
            elif user["role"] == "driver":
                conn.close()
                flash("Driver accounts must sign in via the restricted Driver Portal.", "warning")
                return redirect(url_for("main.driver_login"))

            # Rate limiting check
            is_locked, rem_min = check_login_rate_limit(conn, user)
            if is_locked:
                conn.close()
                flash(f"Account temporarily locked due to too many failed attempts. Please try again in {rem_min} minute(s).", "danger")
                return render_template("auth/login.html")

            if check_password_hash(user["password_hash"], password):
                reset_login_failures(conn, user["id"])
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["user_name"] = user["name"]
                conn.close()
                flash(f"Welcome back, {user['name']}!", "success")
                next_url = request.form.get("next") or request.args.get("next")
                if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)
                return redirect(url_for("main.customer_dashboard"))
            else:
                record_login_failure(conn, user["id"])
                conn.close()
                flash("Invalid email or password.", "danger")
                return render_template("auth/login.html")
        else:
            conn.close()
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("role") == "customer":
        return redirect(url_for("main.customer_dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not phone or not address or not password:
            flash("All fields are required. Please fill in all fields.", "warning")
            return render_template("auth/register.html")

        if not validate_email_format(email):
            flash("Please enter a valid email address.", "warning")
            return render_template("auth/register.html")

        is_phone_valid, clean_phone = validate_ph_phone(phone)
        if not is_phone_valid:
            flash("Please enter a valid Philippine mobile number (e.g., 09171234567 or +639171234567).", "warning")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match. Please verify your password confirmation.", "danger")
            return render_template("auth/register.html")

        is_valid_pwd, pwd_err = validate_password_strength(password)
        if not is_valid_pwd:
            flash(pwd_err, "danger")
            return render_template("auth/register.html")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with that email already exists. Please sign in.", "warning")
            return redirect(url_for("main.login"))

        conn.execute(
            """
            INSERT INTO users (name, email, phone, address, password_hash, role, is_active, is_verified)
            VALUES (?, ?, ?, ?, ?, 'customer', 1, 1)
            """,
            (name, email, clean_phone, address, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! You can now sign in.", "success")
        return redirect(url_for("main.login"))

    return render_template("auth/register.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out from the Customer Portal.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email or not validate_email_format(email):
            flash("Please enter a valid email address.", "warning")
            return render_template("auth/forgot_password.html")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = ? AND role = 'customer'", (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?",
                (token, expires_at, user["id"]),
            )
            conn.commit()
            conn.close()

            reset_url = url_for("main.reset_password", token=token, _external=True)
            flash(f"Password reset link generated for {email}! (Local link: {reset_url})", "info")
            return redirect(url_for("main.login"))
        else:
            conn.close()
            flash("If an account exists with that email address, password reset instructions have been generated.", "info")
            return redirect(url_for("main.login"))

    return render_template("auth/forgot_password.html")


@main_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = conn.execute(
        "SELECT * FROM users WHERE reset_token = ? AND reset_token_expires_at > ?",
        (token, now_str),
    ).fetchone()

    if not user:
        conn.close()
        flash("Invalid or expired password reset link. Please submit a new request.", "danger")
        return redirect(url_for("main.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or password != confirm_password:
            flash("Passwords do not match.", "danger")
            email_val = user["email"]
            conn.close()
            return render_template("auth/reset_password.html", token=token, user_email=email_val)

        is_valid_pwd, pwd_err = validate_password_strength(password)
        if not is_valid_pwd:
            flash(pwd_err, "danger")
            email_val = user["email"]
            conn.close()
            return render_template("auth/reset_password.html", token=token, user_email=email_val)

        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?",
            (generate_password_hash(password), user["id"]),
        )
        conn.commit()
        conn.close()

        flash("Your password has been reset successfully! You can now sign in with your new password.", "success")
        return redirect(url_for("main.login"))

    email_val = user["email"]
    conn.close()
    return render_template("auth/reset_password.html", token=token, user_email=email_val)


# -------------------------------------------------------------------------
# 2. ADMIN/STAFF PORTAL AUTHENTICATION
# -------------------------------------------------------------------------

@main_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("role") in ("admin", "staff"):
        return redirect(url_for("main.admin_dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE (LOWER(email) = ? OR staff_id = ?) AND is_active = 1",
            (identifier.lower(), identifier),
        ).fetchone()

        if user:
            if user["role"] not in ("admin", "staff"):
                conn.close()
                flash("Access denied. Authorized administrative personnel only.", "danger")
                return render_template("auth/admin_login.html")

            is_locked, rem_min = check_login_rate_limit(conn, user)
            if is_locked:
                conn.close()
                flash(f"Account locked due to multiple failed login attempts. Try again in {rem_min} minute(s).", "danger")
                return render_template("auth/admin_login.html")

            if check_password_hash(user["password_hash"], password):
                reset_login_failures(conn, user["id"])
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["user_name"] = user["name"]
                conn.close()
                flash(f"Welcome, {user['name']}! (Admin Console)", "success")
                return redirect(url_for("main.admin_dashboard"))
            else:
                record_login_failure(conn, user["id"])
                conn.close()
                flash("Invalid administrator credentials.", "danger")
                return render_template("auth/admin_login.html")
        else:
            conn.close()
            flash("Invalid administrator credentials.", "danger")

    return render_template("auth/admin_login.html")


@main_bp.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Administrator session closed.", "info")
    return redirect(url_for("main.admin_login"))


# -------------------------------------------------------------------------
# 3. DRIVER PORTAL AUTHENTICATION
# -------------------------------------------------------------------------

@main_bp.route("/driver/login", methods=["GET", "POST"])
def driver_login():
    if session.get("role") == "driver":
        return redirect(url_for("main.driver_dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE (LOWER(email) = ? OR staff_id = ?) AND is_active = 1",
            (identifier.lower(), identifier),
        ).fetchone()

        if user:
            if user["role"] != "driver":
                conn.close()
                flash("Access denied. Authorized delivery drivers only.", "danger")
                return render_template("auth/driver_login.html")

            is_locked, rem_min = check_login_rate_limit(conn, user)
            if is_locked:
                conn.close()
                flash(f"Account locked due to multiple failed attempts. Try again in {rem_min} minute(s).", "danger")
                return render_template("auth/driver_login.html")

            if check_password_hash(user["password_hash"], password):
                reset_login_failures(conn, user["id"])
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["user_name"] = user["name"]
                conn.close()
                flash(f"Signed in as Delivery Driver: {user['name']}", "success")
                return redirect(url_for("main.driver_dashboard"))
            else:
                record_login_failure(conn, user["id"])
                conn.close()
                flash("Invalid driver credentials.", "danger")
                return render_template("auth/driver_login.html")
        else:
            conn.close()
            flash("Invalid driver credentials.", "danger")

    return render_template("auth/driver_login.html")


@main_bp.route("/driver/logout")
def driver_logout():
    session.clear()
    flash("Driver session closed.", "info")
    return redirect(url_for("main.driver_login"))


# -------------------------------------------------------------------------
# 4. CUSTOMER DASHBOARD & PROFILE
# -------------------------------------------------------------------------

@main_bp.route("/customer/dashboard")
@login_required("customer")
def customer_dashboard():
    user_id = session.get("user_id")
    conn = get_db()
    expire_stale_reservations(conn)
    sync_customer_notifications(conn, user_id)
    customer = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    orders = conn.execute(
        """
        SELECT o.*,
               (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS item_count
        FROM orders o
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
        """,
        (user_id,),
    ).fetchall()

    total_orders_count = len(orders)
    pending_orders_count = sum(1 for o in orders if o["order_status"] in ("pending", "pending_scheduling", "for_scheduling", "awaiting_confirmation"))
    processing_orders_count = sum(1 for o in orders if o["order_status"] in ("scheduled", "schedule_confirmed", "pending_payment", "pending_payment_verification", "payment_verified", "approved", "preparing"))
    active_deliveries_count = sum(1 for o in orders if o["order_status"] in ("ready_for_dispatch", "out_for_delivery", "in_transit") or (o["assigned_date"] and o["order_status"] not in ("delivered", "cancelled", "rejected")))
    awaiting_orders = [o for o in orders if o["order_status"] == "awaiting_confirmation"]
    awaiting_count = len(awaiting_orders)
    completed_orders_count = sum(1 for o in orders if o["order_status"] == "delivered")
    recent_orders = orders[:5]

    recent_updates = conn.execute(
        """
        SELECT n.*, o.order_code
        FROM notifications n
        LEFT JOIN orders o ON o.id = n.order_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()

    unread_count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
    ).fetchone()[0]

    conn.close()
    return render_template(
        "customer/dashboard.html",
        customer=customer,
        total_orders_count=total_orders_count,
        pending_orders_count=pending_orders_count,
        processing_orders_count=processing_orders_count,
        active_deliveries_count=active_deliveries_count,
        awaiting_count=awaiting_count,
        awaiting_orders=awaiting_orders,
        completed_orders_count=completed_orders_count,
        recent_orders=recent_orders,
        recent_updates=recent_updates,
        unread_count=unread_count,
    )


@main_bp.route("/customer/settings", methods=["GET", "POST"], endpoint="customer_settings")
@main_bp.route("/customer/profile", methods=["GET", "POST"], endpoint="customer_profile")
@login_required("customer")
def customer_settings():
    user_id = session.get("user_id")
    conn = get_db()
    customer = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if request.method == "POST":
        action = request.form.get("action")
        if action in ("update_profile", "update_info", "update_settings"):
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()

            if not name or not email or not phone or not address:
                flash("Please fill in all personal and delivery address fields.", "warning")
            elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                flash("Please enter a valid email address.", "danger")
            else:
                is_phone_valid, clean_phone = validate_ph_phone(phone)
                if not is_phone_valid:
                    flash("Please enter a valid Philippine mobile number (e.g. 09171234567 or +639171234567).", "danger")
                else:
                    existing_email = conn.execute(
                        "SELECT id FROM users WHERE LOWER(email) = ? AND id != ?",
                        (email, user_id),
                    ).fetchone()
                    if existing_email:
                        flash("This email address is already in use by another account.", "danger")
                    else:
                        conn.execute(
                            "UPDATE users SET name = ?, email = ?, phone = ?, address = ? WHERE id = ?",
                            (name, email, clean_phone, address, user_id),
                        )
                        conn.commit()
                        session["user_name"] = name
                        session["user_email"] = email
                        flash("Account profile and settings updated successfully.", "success")
                        conn.close()
                        return redirect(url_for("main.customer_settings"))

        elif action == "change_password":
            current_pwd = request.form.get("current_password", "")
            new_pwd = request.form.get("new_password", "")
            confirm_pwd = request.form.get("confirm_password", "") or request.form.get("confirm_new_password", "")

            if not current_pwd or not new_pwd:
                flash("Please fill in current and new password fields.", "warning")
            elif not check_password_hash(customer["password_hash"], current_pwd):
                flash("Current password is incorrect.", "danger")
            elif new_pwd != confirm_pwd:
                flash("New passwords do not match.", "danger")
            else:
                is_valid_pwd, pwd_err = validate_password_strength(new_pwd)
                if not is_valid_pwd:
                    flash(pwd_err, "danger")
                else:
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(new_pwd), user_id),
                    )
                    conn.commit()
                    flash("Password updated successfully! Please use your new password next time you sign in.", "success")
                    conn.close()
                    return redirect(url_for("main.customer_settings"))

    orders_count = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?", (user_id,)).fetchone()[0]
    customer = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template("customer/profile.html", customer=customer, orders_count=orders_count)


@main_bp.route("/customer/tracking")
@login_required("customer")
def customer_tracking():
    user_id = session.get("user_id")
    conn = get_db()
    expire_stale_reservations(conn)

    deliveries = conn.execute(
        """
        SELECT o.id AS order_id, o.order_code, o.order_status, o.total_amount,
               o.delivery_address, o.assigned_date, o.assigned_time_slot,
               o.created_at AS order_date,
               d.id AS delivery_id, d.delivery_code, d.delivery_status,
               d.current_lat, d.current_lng, d.last_gps_update, d.delivered_at,
               d.recipient_received_by, d.quantity_received, d.completion_time,
               t.truck_code, t.plate_number, t.capacity AS truck_capacity,
               u_drv.name AS driver_name, u_drv.phone AS driver_phone
        FROM orders o
        LEFT JOIN deliveries d ON d.order_id = o.id
        LEFT JOIN trucks t ON t.id = d.truck_id
        LEFT JOIN users u_drv ON u_drv.id = d.driver_id
        WHERE o.customer_id = ?
        ORDER BY o.created_at DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    active_deliveries = [
        d for d in deliveries
        if (d["delivery_status"] in ("en_route", "loading", "ready_for_dispatch", "authorized", "proposed", "assigned")
            or d["order_status"] in ("ready_for_dispatch", "out_for_delivery", "in_transit", "scheduled", "schedule_confirmed"))
    ]
    completed_deliveries = [
        d for d in deliveries
        if (d["delivery_status"] == "delivered" or d["order_status"] == "delivered")
    ]

    return render_template(
        "customer/delivery_tracking.html",
        deliveries=deliveries,
        active_deliveries=active_deliveries,
        completed_deliveries=completed_deliveries,
    )


def format_notification_time(dt_str, now=None):
    if not dt_str:
        return ""
    if now is None:
        now = datetime.now()
    try:
        if len(dt_str) == 10:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        elif len(dt_str) >= 19:
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.fromisoformat(dt_str)
    except Exception:
        return dt_str

    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "Just now"
    elif seconds < 60:
        return f"{seconds}s ago" if seconds > 5 else "Just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif seconds < 86400 and dt.date() == now.date():
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif dt.date() == (now.date() - timedelta(days=1)):
        return f"Yesterday at {dt.strftime('%I:%M %p')}"
    elif dt.year == now.year:
        return dt.strftime("%b %d, %I:%M %p")
    else:
        return dt.strftime("%b %d, %Y, %I:%M %p")


def get_notification_date_group(dt_str, now=None):
    if not dt_str:
        return "Earlier"
    if now is None:
        now = datetime.now()
    try:
        dt = datetime.strptime(dt_str[:10], "%Y-%m-%d").date()
        if dt == now.date():
            return "Today"
        elif dt == (now.date() - timedelta(days=1)):
            return "Yesterday"
        else:
            return "Earlier"
    except Exception:
        return "Earlier"


@main_bp.route("/customer/notifications")
@login_required("customer")
def customer_notifications():
    user_id = session.get("user_id")
    conn = get_db()
    sync_customer_notifications(conn, user_id)

    filter_type = request.args.get("type", "").strip().lower()

    base_query = """
        SELECT n.*, o.order_code
        FROM notifications n
        LEFT JOIN orders o ON o.id = n.order_id
        WHERE n.user_id = ?
    """
    params = [user_id]

    if filter_type in ("order", "schedule", "payment", "delivery"):
        base_query += " AND n.notification_type = ?"
        params.append(filter_type)
    elif filter_type == "unread":
        base_query += " AND n.is_read = 0"

    base_query += " ORDER BY n.created_at DESC, n.id DESC"

    notifications_raw = conn.execute(base_query, tuple(params)).fetchall()

    all_notifs = conn.execute(
        "SELECT id, is_read, notification_type FROM notifications WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    unread_count = sum(1 for n in all_notifs if not n["is_read"])
    total_count = len(all_notifs)

    conn.close()

    now = datetime.now()
    notifications = []
    grouped_notifications = {
        "Today": [],
        "Yesterday": [],
        "Earlier": [],
    }

    for row in notifications_raw:
        item = dict(row)
        item["relative_time"] = format_notification_time(item.get("created_at"), now)
        grp = get_notification_date_group(item.get("created_at"), now)
        item["date_group"] = grp
        notifications.append(item)
        if grp in grouped_notifications:
            grouped_notifications[grp].append(item)
        else:
            grouped_notifications["Earlier"].append(item)

    return render_template(
        "customer/notifications.html",
        notifications=notifications,
        grouped_notifications=grouped_notifications,
        unread_count=unread_count,
        total_count=total_count,
        active_filter=filter_type,
    )


@main_bp.route("/customer/notifications/<int:notification_id>/read", methods=["POST"])
@login_required("customer")
def customer_notification_mark_read(notification_id):
    user_id = session.get("user_id")
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notification_id, user_id),
    )
    conn.commit()
    conn.close()
    flash("Notification marked as read.", "success")
    return redirect(url_for("main.customer_notifications"))


@main_bp.route("/customer/notifications/mark-all-read", methods=["POST"])
@login_required("customer")
def customer_notifications_mark_all_read():
    user_id = session.get("user_id")
    conn = get_db()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("main.customer_notifications"))


def get_customer_cart_details(conn, user_id):
    """
    Retrieve customer's active cart items with real-time product prices and stocks from database.
    Recalculates subtotals, VAT, delivery fee, and cart totals securely.
    """
    rows = conn.execute(
        """
        SELECT ci.id AS cart_item_id, ci.user_id, ci.product_id, ci.variation_id, ci.quantity,
               p.name AS product_name, p.unit AS product_unit, p.price AS product_base_price,
               p.stock_quantity AS product_stock, p.image_url, p.is_active,
               pv.variation_name, pv.price AS variation_price, pv.unit AS variation_unit,
               pv.stock_quantity AS variation_stock, pv.is_available AS variation_available
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        LEFT JOIN product_variations pv ON ci.variation_id = pv.id
        WHERE ci.user_id = ? AND p.is_active = 1
        ORDER BY ci.id ASC
        """,
        (user_id,),
    ).fetchall()

    # Migration fallback: if database cart is empty, check legacy session['cart'] and migrate
    legacy_cart = session.get("cart", {})
    if not rows and legacy_cart:
        for c_key, c_qty in legacy_cart.items():
            try:
                c_qty = int(c_qty)
                if c_qty <= 0:
                    continue
                parts = str(c_key).split(":")
                p_id = int(parts[0]) if parts[0].isdigit() else 0
                v_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                if p_id > 0:
                    conn.execute(
                        "INSERT INTO cart_items (user_id, product_id, variation_id, quantity) VALUES (?, ?, ?, ?)",
                        (user_id, p_id, v_id, c_qty)
                    )
            except Exception:
                pass
        conn.commit()
        rows = conn.execute(
            """
            SELECT ci.id AS cart_item_id, ci.user_id, ci.product_id, ci.variation_id, ci.quantity,
                   p.name AS product_name, p.unit AS product_unit, p.price AS product_base_price,
                   p.stock_quantity AS product_stock, p.image_url, p.is_active,
                   pv.variation_name, pv.price AS variation_price, pv.unit AS variation_unit,
                   pv.stock_quantity AS variation_stock, pv.is_available AS variation_available
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            LEFT JOIN product_variations pv ON ci.variation_id = pv.id
            WHERE ci.user_id = ? AND p.is_active = 1
            ORDER BY ci.id ASC
            """,
            (user_id,),
        ).fetchall()

    cart_items = []
    subtotal = 0.0
    total_qty = 0

    for r in rows:
        var_id = r["variation_id"]
        # Determine actual price and unit from DB
        if var_id and r["variation_price"] is not None:
            unit_price = float(r["variation_price"])
            unit_label = r["variation_unit"] or r["product_unit"]
            display_name = f"{r['product_name']} ({r['variation_name']})"
            available_stock = int(r["variation_stock"] or 0)
        else:
            unit_price = float(r["product_base_price"])
            unit_label = r["product_unit"]
            display_name = r["product_name"]
            available_stock = int(r["product_stock"] or 0)

        qty = int(r["quantity"])
        if available_stock > 0 and qty > available_stock:
            qty = available_stock
            conn.execute(
                "UPDATE cart_items SET quantity = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (qty, r["cart_item_id"]),
            )
            conn.commit()

        line_total = round(qty * unit_price, 2)
        subtotal += line_total
        total_qty += qty

        cart_items.append({
            "cart_item_id": r["cart_item_id"],
            "product_id": r["product_id"],
            "variation_id": var_id,
            "product_name": r["product_name"],
            "variation_name": r["variation_name"],
            "display_name": display_name,
            "unit": unit_label,
            "price": unit_price,
            "stock": available_stock,
            "quantity": qty,
            "line_total": line_total,
            "image_url": r["image_url"] or "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500",
            "is_in_stock": available_stock > 0,
            "product": {
                "id": r["product_id"],
                "name": r["product_name"],
                "unit": r["product_unit"],
                "price": r["product_base_price"],
                "stock_quantity": r["product_stock"],
                "image_url": r["image_url"],
            },
            "variation": {
                "id": var_id,
                "variation_name": r["variation_name"],
                "price": r["variation_price"],
                "unit": r["variation_unit"],
                "stock_quantity": r["variation_stock"],
            } if var_id else None,
            "cart_key": f"{r['product_id']}:{var_id}" if var_id else str(r['product_id']),
        })

    subtotal = round(subtotal, 2)
    delivery_fee = 1500.00 if cart_items else 0.00
    vat_amount = round(subtotal * 0.12, 2)
    total_amount = round(subtotal + delivery_fee + vat_amount, 2)

    return {
        "items": cart_items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "vat_amount": vat_amount,
        "total_amount": total_amount,
        "total_items_count": total_qty,
    }


@main_bp.route("/customer/cart", methods=["GET"])
@login_required("customer")
def customer_cart():
    """Shopping Cart view: Allows reviewing and managing customer-selected products."""
    user_id = session.get("user_id")
    conn = get_db()
    cart_data = get_customer_cart_details(conn, user_id)
    conn.close()
    return render_template(
        "customer/cart.html",
        cart_items=cart_data["items"],
        subtotal=cart_data["subtotal"],
        delivery_fee=cart_data["delivery_fee"],
        vat_amount=cart_data["vat_amount"],
        total_amount=cart_data["total_amount"],
        total_items_count=cart_data["total_items_count"],
    )


# -------------------------------------------------------------------------
# CUSTOMER PORTAL
# -------------------------------------------------------------------------

@main_bp.route("/customer/catalog")
def customer_catalog():
    if session.get("role") in ("admin", "staff"):
        return redirect(url_for("main.admin_dashboard"))
    elif session.get("role") == "driver":
        return redirect(url_for("main.driver_dashboard"))

    if not session.get("user_id") or session.get("role") != "customer":
        flash("You need to sign in to access the complete product catalog.", "warning")
        next_target = request.full_path if (request.query_string and request.query_string.strip()) else request.path
        if next_target.endswith("?"):
            next_target = next_target[:-1]
        return redirect(url_for("main.login", next=next_target))

    search = request.args.get("q", "").strip() or request.args.get("search", "").strip()
    category_id = request.args.get("category", "").strip()
    stock_filter = request.args.get("stock", "").strip()
    sort_filter = request.args.get("sort", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()

    conn = get_db()
    categories = conn.execute(
        """
        SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) AS product_count
        FROM categories c
        WHERE (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) > 0
        ORDER BY c.name
        """
    ).fetchall()

    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = 1
    """
    params = []
    if search:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    if stock_filter == "instock":
        query += " AND p.stock_quantity > 0"
    if min_price:
        try:
            query += " AND p.price >= ?"
            params.append(float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            query += " AND p.price <= ?"
            params.append(float(max_price))
        except ValueError:
            pass

    if sort_filter == "price_asc":
        query += " ORDER BY p.price ASC"
    elif sort_filter == "price_desc":
        query += " ORDER BY p.price DESC"
    elif sort_filter == "name_asc":
        query += " ORDER BY p.name ASC"
    else:
        query += " ORDER BY p.id"

    products_raw = conn.execute(query, params).fetchall()

    # Load all active product variations
    all_vars = conn.execute(
        "SELECT * FROM product_variations WHERE is_available = 1 ORDER BY price ASC"
    ).fetchall()
    vars_by_prod = {}
    for v in all_vars:
        vars_by_prod.setdefault(v["product_id"], []).append(dict(v))

    products = []
    for p in products_raw:
        p_dict = dict(p)
        p_dict["variations"] = vars_by_prod.get(p["id"], [])
        products.append(p_dict)

    # Calculate cart total from customer database cart
    cart_total = 0.0
    if session.get("user_id"):
        c_items = conn.execute(
            """
            SELECT ci.quantity, COALESCE(pv.price, p.price) AS price
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            LEFT JOIN product_variations pv ON ci.variation_id = pv.id
            WHERE ci.user_id = ? AND p.is_active = 1
            """,
            (session["user_id"],),
        ).fetchall()
        for ci in c_items:
            cart_total += float(ci["quantity"]) * float(ci["price"])

    all_in_stock = all(p["stock_quantity"] > 0 for p in products)
    conn.close()

    return render_template(
        "customer/catalog.html",
        products=products,
        categories=categories,
        search=search,
        q=search,
        selected_category=category_id,
        stock_filter=stock_filter,
        sort_filter=sort_filter,
        min_price=min_price,
        max_price=max_price,
        cart_total=round(cart_total, 2),
        all_in_stock=all_in_stock,
    )


@main_bp.route("/customer/cart/add", methods=["POST"])
@login_required("customer")
def cart_add():
    user_id = session.get("user_id")
    product_id = request.form.get("product_id")
    variation_id = request.form.get("variation_id")
    try:
        qty = int(request.form.get("quantity", 1))
    except (ValueError, TypeError):
        qty = 1
    if qty < 1:
        qty = 1

    conn = get_db()
    prod = conn.execute(
        "SELECT id, name, unit, price, stock_quantity FROM products WHERE id = ? AND is_active = 1",
        (product_id,)
    ).fetchone()
    if not prod:
        conn.close()
        flash("Product not found or currently unavailable.", "danger")
        return redirect(url_for("main.customer_catalog"))

    display_name = prod["name"]
    max_stock = prod["stock_quantity"]
    var_id_int = None

    if variation_id and str(variation_id).strip():
        try:
            var_id_int = int(variation_id)
        except (ValueError, TypeError):
            var_id_int = None

    if var_id_int:
        var_row = conn.execute(
            "SELECT id, variation_name, price, unit, stock_quantity FROM product_variations WHERE id = ? AND product_id = ? AND is_available = 1",
            (var_id_int, product_id)
        ).fetchone()
        if var_row:
            display_name = f"{prod['name']} ({var_row['variation_name']})"
            max_stock = var_row["stock_quantity"]
        else:
            var_id_int = None

    if max_stock <= 0:
        conn.close()
        flash(f"Sorry, {display_name} is currently out of stock.", "warning")
        return redirect(request.referrer or url_for("main.customer_catalog"))

    # Check if item is already in user's cart in database
    if var_id_int:
        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ? AND variation_id = ?",
            (user_id, product_id, var_id_int)
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ? AND variation_id IS NULL",
            (user_id, product_id)
        ).fetchone()

    if existing:
        new_qty = existing["quantity"] + qty
        if max_stock > 0 and new_qty > max_stock:
            new_qty = max_stock
            flash(f"Updated {display_name} quantity in your cart to available stock ({max_stock}).", "warning")
        else:
            flash(f"Added {qty} item(s) to your cart: {display_name}.", "success")
        conn.execute(
            "UPDATE cart_items SET quantity = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (new_qty, existing["id"])
        )
    else:
        if max_stock > 0 and qty > max_stock:
            qty = max_stock
            flash(f"Added {qty} item(s) to your cart: {display_name} (adjusted to available stock).", "warning")
        else:
            flash(f"Added {qty} item(s) to your cart: {display_name}.", "success")
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, variation_id, quantity) VALUES (?, ?, ?, ?)",
            (user_id, product_id, var_id_int, qty)
        )

    conn.commit()
    conn.close()

    # Clear legacy session cart so database cart is single source of truth
    session.pop("cart", None)

    return redirect(request.referrer or url_for("main.customer_catalog"))


@main_bp.route("/customer/cart/update", methods=["POST"])
@login_required("customer")
def cart_update():
    user_id = session.get("user_id")
    cart_item_id = request.form.get("cart_item_id")
    try:
        qty = int(request.form.get("quantity", 0))
    except (ValueError, TypeError):
        qty = 0

    conn = get_db()
    item = None
    if cart_item_id and str(cart_item_id).isdigit():
        item = conn.execute(
            """
            SELECT ci.id, ci.user_id, ci.product_id, ci.variation_id, ci.quantity,
                   p.name AS product_name, p.stock_quantity AS product_stock, p.is_active,
                   pv.variation_name, pv.stock_quantity AS variation_stock
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            LEFT JOIN product_variations pv ON ci.variation_id = pv.id
            WHERE ci.id = ? AND ci.user_id = ?
            """,
            (int(cart_item_id), user_id)
        ).fetchone()

    # Fallback to cart_key (pid or pid:vid)
    if not item and request.form.get("cart_key"):
        cart_key = str(request.form.get("cart_key"))
        parts = cart_key.split(":")
        pid = int(parts[0]) if parts[0].isdigit() else 0
        vid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        if vid:
            item = conn.execute(
                """
                SELECT ci.id, ci.user_id, ci.product_id, ci.variation_id, ci.quantity,
                       p.name AS product_name, p.stock_quantity AS product_stock, p.is_active,
                       pv.variation_name, pv.stock_quantity AS variation_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                LEFT JOIN product_variations pv ON ci.variation_id = pv.id
                WHERE ci.user_id = ? AND ci.product_id = ? AND ci.variation_id = ?
                """,
                (user_id, pid, vid)
            ).fetchone()
        elif pid:
            item = conn.execute(
                """
                SELECT ci.id, ci.user_id, ci.product_id, ci.variation_id, ci.quantity,
                       p.name AS product_name, p.stock_quantity AS product_stock, p.is_active,
                       pv.variation_name, pv.stock_quantity AS variation_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                LEFT JOIN product_variations pv ON ci.variation_id = pv.id
                WHERE ci.user_id = ? AND ci.product_id = ? AND ci.variation_id IS NULL
                """,
                (user_id, pid)
            ).fetchone()

    if not item:
        conn.close()
        flash("Cart item not found.", "warning")
        return redirect(url_for("main.customer_cart"))

    item_name = f"{item['product_name']} ({item['variation_name']})" if item['variation_name'] else item['product_name']
    available_stock = item['variation_stock'] if item['variation_id'] else item['product_stock']
    available_stock = int(available_stock or 0)

    if qty <= 0:
        conn.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item["id"], user_id))
        conn.commit()
        conn.close()
        session.pop("cart", None)
        flash(f"Removed {item_name} from your cart.", "info")
        return redirect(url_for("main.customer_cart"))

    if available_stock > 0 and qty > available_stock:
        qty = available_stock
        flash(f"Quantity for {item_name} adjusted to maximum available stock ({available_stock}).", "warning")
    else:
        flash("Cart updated.", "success")

    conn.execute(
        "UPDATE cart_items SET quantity = ?, updated_at = datetime('now', 'localtime') WHERE id = ? AND user_id = ?",
        (qty, item["id"], user_id)
    )
    conn.commit()
    conn.close()
    session.pop("cart", None)
    return redirect(url_for("main.customer_cart"))


@main_bp.route("/customer/cart/remove/<int:item_id>", methods=["POST"])
@login_required("customer")
def cart_remove(item_id):
    user_id = session.get("user_id")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id))
    if cur.rowcount > 0:
        flash("Item removed from your shopping cart.", "info")
    else:
        flash("Cart item not found.", "warning")
    conn.commit()
    conn.close()
    session.pop("cart", None)
    return redirect(url_for("main.customer_cart"))


@main_bp.route("/customer/cart/clear", methods=["POST"])
@login_required("customer")
def cart_clear():
    user_id = session.get("user_id")
    conn = get_db()
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    session.pop("cart", None)
    flash("Your shopping cart has been cleared.", "info")
    return redirect(url_for("main.customer_cart"))


@main_bp.route("/customer/checkout", methods=["GET", "POST"])
@login_required("customer")
def customer_checkout():
    user_id = session.get("user_id")
    conn = get_db()

    cart_data = get_customer_cart_details(conn, user_id)
    cart_items = cart_data["items"]
    subtotal = cart_data["subtotal"]
    delivery_fee = cart_data["delivery_fee"]
    vat_amount = cart_data["vat_amount"]
    total_amount = cart_data["total_amount"]

    if not cart_items:
        conn.close()
        flash("Your shopping cart is empty. Browse our catalog and add construction materials to get started.", "warning")
        return redirect(url_for("main.customer_cart"))

    if request.method == "POST":
        recipient_name = request.form.get("recipient_name", "").strip()
        phone = request.form.get("phone", "").strip() or request.form.get("recipient_phone", "").strip()
        delivery_address = request.form.get("delivery_address", "").strip()
        special_instructions = request.form.get("special_instructions", "").strip()

        if not recipient_name or not delivery_address:
            flash("Please provide recipient name and delivery address.", "warning")
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
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

        # Automatic Delivery Availability Check & Proposal
        proposed_slot = find_and_reserve_delivery_slot(conn)

        if proposed_slot:
            order_status = "awaiting_confirmation"
            schedule_status = "proposed"
            assigned_date = proposed_slot["assigned_date"]
            assigned_time_slot = proposed_slot["assigned_time_slot"]
            reservation_expires_at = proposed_slot["expires_at"]
            flash(
                f"Your order has been submitted! We automatically proposed the next available delivery schedule: "
                f"{assigned_date} ({assigned_time_slot}). Please review and accept this schedule within "
                f"{proposed_slot['timeout_hours']} hours to proceed to payment.",
                "success",
            )
        else:
            order_status = "pending_scheduling"
            schedule_status = "unassigned"
            assigned_date = None
            assigned_time_slot = None
            reservation_expires_at = None
            flash(
                "Your order has been submitted! All immediate delivery schedules are currently fully booked. "
                "Our administrator will review your order and assign a delivery schedule as soon as capacity opens.",
                "info",
            )

        order_code = f"#{random.randint(1053, 9999)}"
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (
                order_code, customer_id, recipient_name, phone, delivery_address,
                special_instructions, subtotal, delivery_fee, vat_amount, total_amount,
                order_status, schedule_status, assigned_date, assigned_time_slot,
                reservation_expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_code,
                user_id,
                recipient_name,
                phone,
                delivery_address,
                special_instructions,
                subtotal,
                delivery_fee,
                vat_amount,
                total_amount,
                order_status,
                schedule_status,
                assigned_date,
                assigned_time_slot,
                reservation_expires_at,
            ),
        )
        order_id = cur.lastrowid

        for item in cart_items:
            var_id = item["variation_id"]
            var_name = item["variation_name"]
            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, variation_id, variation_name, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (order_id, item["product_id"], var_id, var_name, item["quantity"], item["price"], item["line_total"]),
            )
            # Deduct stock
            if var_id:
                cur.execute(
                    "UPDATE product_variations SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                    (item["quantity"], var_id),
                )
            cur.execute(
                "UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

        if proposed_slot:
            while True:
                d_code = f"DLV-{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"
                if not conn.execute("SELECT id FROM deliveries WHERE delivery_code = ?", (d_code,)).fetchone():
                    break
            cur.execute(
                """
                INSERT INTO deliveries (
                    delivery_code, order_id, driver_id, truck_id, delivery_window,
                    delivery_status, current_lat, current_lng
                ) VALUES (?, ?, ?, ?, ?, 'proposed', 13.9411, 121.1631)
                """,
                (d_code, order_id, proposed_slot["driver_id"], proposed_slot["truck_id"], assigned_time_slot),
            )

        create_notification(
            conn,
            user_id,
            "Order Submitted Successfully",
            f"Order {order_code} for ₱{total_amount:,.2f} has been submitted and is queued for scheduling.",
            "order",
            order_id,
        )
        if proposed_slot:
            create_notification(
                conn,
                user_id,
                "Delivery Schedule Proposed",
                f"Delivery schedule for order {order_code} has been proposed: {assigned_date} ({assigned_time_slot}). Please review and accept.",
                "schedule",
                order_id,
            )

        # Clear customer's shopping cart in database and session only after order is placed
        cur.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        session.pop("cart", None)

        conn.commit()
        conn.close()
        return redirect(url_for("main.customer_order_confirmation", order_id=order_id))

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
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


@main_bp.route("/customer/orders/<int:order_id>/confirmation")
@login_required("customer")
def customer_order_confirmation(order_id):
    """Post-checkout confirmation view displaying submitted order details and waiting notice."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    if session.get("role") != "admin" and order["customer_id"] != session["user_id"]:
        conn.close()
        flash("Unauthorized access to this order.", "danger")
        return redirect(url_for("main.customer_orders"))

    items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()

    delivery = conn.execute(
        """
        SELECT d.*, u.name AS driver_name, t.truck_code, t.plate_number
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        WHERE d.order_id = ?
        """,
        (order_id,),
    ).fetchone()
    conn.close()

    return render_template(
        "customer/order_confirmation.html",
        order=order,
        items=items,
        delivery=delivery,
    )


@main_bp.route("/customer/payment/<int:order_id>", methods=["GET", "POST"])
@login_required("customer")
def customer_payment(order_id):
    """Multi-step payment flow matching high-fidelity mockups.
    Enforces that payment cannot be accessed until schedule is approved by customer."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    # Security check: only order owner or admin
    if session.get("role") != "admin" and order["customer_id"] != session["user_id"]:
        conn.close()
        flash("Unauthorized access to this order.", "danger")
        return redirect(url_for("main.customer_orders"))

    # Strict workflow check: payment is NOT available until admin assigned and customer accepted schedule
    if order["order_status"] in ("pending", "pending_scheduling", "for_scheduling", "awaiting_confirmation", "cancelled", "rejected"):
        conn.close()
        if order["order_status"] == "awaiting_confirmation":
            flash("Please review and accept your admin-assigned delivery schedule before proceeding to payment.", "warning")
            return redirect(url_for("main.customer_orders"))
        elif order["order_status"] in ("cancelled", "rejected"):
            flash("Payment cannot be processed for cancelled orders.", "danger")
            return redirect(url_for("main.customer_orders"))
        else:
            flash("Payment is not available yet. Please wait for an administrator to review your order and assign an available delivery schedule.", "warning")
            return redirect(url_for("main.customer_orders"))

    items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()

    existing_payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchone()

    # Step navigation: 1 (method select), 2 (details), 3 (confirmation), 4 (approved)
    step = request.args.get("step", type=int) or 1
    method = request.args.get("method", "") or (existing_payment["method"] if existing_payment else "cash")

    if request.method == "POST":
        action = request.form.get("action", "")
        method = request.form.get("method", method or "cash")

        if action == "to_details":
            conn.close()
            return redirect(url_for("main.customer_payment", order_id=order_id, step=2, method=method))

        elif action == "review_receipt":
            # Pass details in session temporarily for preview
            session["payment_draft"] = {
                "order_id": order_id,
                "method": method,
                "payer_name": request.form.get("payer_name", "").strip() or order["recipient_name"],
                "mobile_number": request.form.get("mobile_number", "").strip() or order["phone"],
                "bank_used": request.form.get("bank_used", "").strip(),
                "reference_number": request.form.get("reference_number", "").strip() or request.form.get("reference_no", "").strip(),
                "receipt_note": request.form.get("receipt_note", "").strip(),
                "payment_datetime": request.form.get("payment_datetime", "").strip() or datetime.now().strftime("%d %b %Y · %I:%M %p"),
                "amount": float(request.form.get("amount", order["total_amount"]) or order["total_amount"]),
            }
            conn.close()
            return redirect(url_for("main.customer_payment", order_id=order_id, step=3, method=method))

        elif action == "confirm_payment":
            draft = session.pop("payment_draft", {})
            payer_name = draft.get("payer_name") or request.form.get("payer_name") or order["recipient_name"]
            bank_used = draft.get("bank_used") or request.form.get("bank_used", "")
            ref = draft.get("reference_number") or request.form.get("reference_number") or request.form.get("reference_no", "")
            note = draft.get("receipt_note") or request.form.get("receipt_note", "")

            if method == "cash":
                ref = ref or f"COD-{clean_order_code(order['order_code']).replace('#', '')}"
                new_payment_status = "payment_due"
                flash_msg = "Cash on Delivery arrangement confirmed! Awaiting administrator approval before release for delivery."
            else:
                new_payment_status = "pending_verification"
                flash_msg = "QR payment information submitted! Awaiting administrator verification before release for delivery."

            if existing_payment:
                conn.execute(
                    """
                    UPDATE payments
                    SET method=?, reference_number=?, receipt_note=?, payer_name=?, bank_used=?,
                        payment_status=?, paid_at=datetime('now','localtime'), rejection_reason=NULL
                    WHERE order_id=?
                    """,
                    (method, ref, note, payer_name, bank_used, new_payment_status, order_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO payments (order_id, method, reference_number, receipt_note, payer_name, bank_used, amount, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, method, ref, note, payer_name, bank_used, order["total_amount"], new_payment_status),
                )

            # Move order status to pending_payment_verification
            conn.execute(
                """
                UPDATE orders
                SET order_status = 'pending_payment_verification',
                    rejection_reason = NULL
                WHERE id = ?
                """,
                (order_id,),
            )
            create_notification(
                conn,
                session["user_id"],
                "Payment Submitted",
                f"Payment for order {clean_order_code(order['order_code'])} ({method.upper()}) was submitted and is pending administrator verification.",
                "payment",
                order_id,
            )
            conn.commit()
            conn.close()
            flash(flash_msg, "success")
            return redirect(url_for("main.customer_payment", order_id=order_id, step=4, method=method))

    draft = session.get("payment_draft", {})
    conn.close()
    return render_template(
        "customer/payment.html",
        order=order,
        items=items,
        payment=existing_payment,
        draft=draft,
        step=step,
        method=method,
    )


@main_bp.route("/customer/orders")
@login_required("customer")
def customer_orders():
    conn = get_db()
    expire_stale_reservations(conn)
    orders = conn.execute(
        """
        SELECT o.*, p.method AS payment_method, p.payment_status, p.reference_number,
               p.rejection_reason AS payment_rejection_reason,
               d.delivery_status, d.delivery_code,
               t.truck_code, t.plate_number, t.capacity AS truck_capacity,
               u_drv.name AS driver_name, u_drv.phone AS driver_phone
        FROM orders o
        LEFT JOIN payments p ON o.id = p.order_id
        LEFT JOIN deliveries d ON o.id = d.order_id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u_drv ON d.driver_id = u_drv.id
        WHERE o.customer_id = ?
        ORDER BY o.id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("customer/orders.html", orders=orders)


@main_bp.route("/customer/order/<int:order_id>/accept-schedule", methods=["POST"])
@login_required("customer")
def customer_accept_schedule(order_id):
    conn = get_db()
    expire_stale_reservations(conn)

    order = conn.execute(
        "SELECT * FROM orders WHERE id = ? AND customer_id = ?",
        (order_id, session["user_id"]),
    ).fetchone()

    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    # Backend validation: check if reservation has expired or order is not awaiting confirmation
    if order["order_status"] != "awaiting_confirmation":
        conn.close()
        if order["schedule_status"] == "expired":
            flash("Your proposed delivery schedule reservation has expired. Please check with administrator for an updated schedule.", "warning")
        else:
            flash(f"Order {clean_order_code(order['order_code'])} is not currently awaiting schedule confirmation.", "warning")
        return redirect(url_for("main.customer_orders"))

    if order["reservation_expires_at"]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if order["reservation_expires_at"] <= now_str:
            expire_stale_reservations(conn)
            conn.close()
            flash("Your schedule reservation has expired. The reserved delivery slot has been released.", "warning")
            return redirect(url_for("main.customer_orders"))

    conn.execute(
        """
        UPDATE orders
        SET order_status = 'schedule_confirmed',
            schedule_status = 'accepted',
            schedule_confirmed_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (order_id,),
    )
    conn.execute(
        "UPDATE deliveries SET delivery_status = 'confirmed' WHERE order_id = ?",
        (order_id,),
    )
    create_notification(
        conn,
        session["user_id"],
        "Schedule Confirmed",
        f"You confirmed the delivery schedule for order {clean_order_code(order['order_code'])}. You may now proceed to payment.",
        "schedule",
        order_id,
    )
    conn.commit()
    conn.close()
    flash(
        f"Delivery schedule for {clean_order_code(order['order_code'])} confirmed ({order['assigned_date']}, {order['assigned_time_slot']})! Please choose your preferred payment method below.",
        "success",
    )
    return redirect(url_for("main.customer_payment", order_id=order_id, step=1))


@main_bp.route("/customer/order/<int:order_id>/cancel", methods=["POST"])
@login_required()
def customer_cancel_order(order_id):
    conn = get_db()
    is_admin = session.get("role") == "admin"
    if is_admin:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    else:
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ? AND customer_id = ?",
            (order_id, session["user_id"]),
        ).fetchone()

    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders" if not is_admin else "main.admin_orders"))

    # Backend validation: cannot cancel if out for delivery, in transit, delivered, or already cancelled
    if order["order_status"] in ("out_for_delivery", "in_transit", "delivered", "cancelled"):
        conn.close()
        flash("This order has already progressed beyond the stage where cancellation is allowed.", "danger")
        return redirect(url_for("main.customer_orders" if not is_admin else "main.admin_orders"))

    cancellation_reason = request.form.get("cancellation_reason", "").strip() or "Cancelled by customer (schedule inconvenient or requested cancellation)"

    # 1. Update order status to 'cancelled'
    conn.execute(
        """
        UPDATE orders
        SET order_status = 'cancelled',
            schedule_status = 'cancelled',
            rejection_reason = ?
        WHERE id = ?
        """,
        (cancellation_reason, order_id),
    )

    # 2. Release assigned delivery resources (truck & driver)
    delivery = conn.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()
    if delivery:
        if delivery["truck_id"]:
            other_active = conn.execute(
                "SELECT COUNT(*) FROM deliveries WHERE truck_id = ? AND id != ? AND delivery_status IN ('assigned', 'loading', 'en_route')",
                (delivery["truck_id"], delivery["id"]),
            ).fetchone()[0]
            if other_active == 0:
                conn.execute("UPDATE trucks SET status = 'available' WHERE id = ?", (delivery["truck_id"],))
        conn.execute("DELETE FROM deliveries WHERE id = ?", (delivery["id"],))

    # 3. Restore inventory if stock was previously deducted
    logs = conn.execute(
        "SELECT * FROM inventory_logs WHERE remarks LIKE ?",
        (f"%Order {clean_order_code(order['order_code'])}%",),
    ).fetchall()
    if logs:
        order_items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        for item in order_items:
            conn.execute(
                "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, 'stock_in', ?, ?, ?)",
                (item["product_id"], item["quantity"], f"Cancelled Order {clean_order_code(order['order_code'])} stock restored", session.get("user_id")),
            )

    create_notification(
        conn,
        order["customer_id"],
        "Order Cancelled",
        f"Order {clean_order_code(order['order_code'])} has been cancelled.",
        "order",
        order_id,
    )

    conn.commit()
    conn.close()
    flash(
        f"Order {clean_order_code(order['order_code'])} has been cancelled. Reserved truck, driver, and delivery resources have been released.",
        "info",
    )
    return redirect(url_for("main.customer_orders" if not is_admin else "main.admin_orders"))


@main_bp.route("/customer/orders/<int:order_id>/tracking")
@login_required("customer")
def customer_order_tracking(order_id):
    conn = get_db()
    expire_stale_reservations(conn)
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.customer_orders"))

    if session.get("role") != "admin" and order["customer_id"] != session["user_id"]:
        conn.close()
        flash("Unauthorized access to this order tracking.", "danger")
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
        SELECT p.*, o.order_code, o.created_at AS order_date, o.id AS order_id
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


@main_bp.route("/order/<int:order_id>/invoice")
@login_required()
def order_invoice(order_id):
    """Generate and display clean printable tax invoice for an order."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.home"))

    user_role = session.get("role")
    if user_role not in ("admin", "staff") and order["customer_id"] != session.get("user_id"):
        conn.close()
        flash("Unauthorized access to this invoice.", "danger")
        return redirect(url_for("main.customer_orders"))

    customer = conn.execute("SELECT * FROM users WHERE id = ?", (order["customer_id"],)).fetchone()
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
        SELECT d.*, u.name AS driver_name, t.truck_code, t.plate_number
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        WHERE d.order_id = ?
        """,
        (order_id,),
    ).fetchone()
    conn.close()

    return render_template(
        "order_invoice.html",
        order=order,
        customer=customer,
        items=items,
        payment=payment,
        delivery=delivery,
    )


# -------------------------------------------------------------------------
# GPS APIS (FOR DRIVER & CUSTOMER LIVE TRACKING)
# -------------------------------------------------------------------------

@main_bp.route("/api/gps/update", methods=["POST"])
@main_bp.route("/api/gps/update/<int:delivery_id>", methods=["POST"])
@login_required()
def api_gps_update(delivery_id=None):
    """Receive driver GPS coordinates and update active delivery location."""
    data = request.get_json(silent=True) or request.form or {}
    del_id = delivery_id or data.get("delivery_id")
    lat = data.get("lat")
    lng = data.get("lng")

    if not del_id or lat is None or lng is None:
        return jsonify({"ok": False, "error": "Missing coordinates or delivery ID"}), 400

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid coordinates"}), 400

    conn = get_db()
    conn.execute(
        """
        UPDATE deliveries
        SET current_lat = ?, current_lng = ?, last_gps_update = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (lat_f, lng_f, int(del_id)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "delivery_id": int(del_id), "lat": lat_f, "lng": lng_f})


@main_bp.route("/api/gps/location/<int:order_id>")
@login_required()
def api_gps_order_location(order_id):
    """Customer endpoint to poll current delivery location for an order."""
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, delivery_code, delivery_status, current_lat, current_lng, last_gps_update
        FROM deliveries
        WHERE order_id = ?
        """,
        (order_id,),
    ).fetchone()
    conn.close()

    if not row or not row["current_lat"] or not row["current_lng"]:
        return jsonify({"ok": False, "error": "No GPS data for this order"}), 404

    return jsonify({
        "ok": True,
        "delivery_id": row["id"],
        "delivery_code": row["delivery_code"],
        "delivery_status": row["delivery_status"],
        "lat": row["current_lat"],
        "lng": row["current_lng"],
        "last_gps_update": row["last_gps_update"],
    })


@main_bp.route("/api/gps/delivery/<int:delivery_id>")
@login_required()
def api_gps_get(delivery_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT d.id, d.delivery_code, d.delivery_status, d.current_lat, d.current_lng, d.last_gps_update,
               u.name AS driver_name, t.truck_code, t.plate_number, o.order_code
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN orders o ON d.order_id = o.id
        WHERE d.id = ?
        """,
        (delivery_id,),
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False}), 404
    return jsonify(dict(row))


@main_bp.route("/api/gps/fleet")
@login_required("admin")
def api_gps_fleet():
    """Admin endpoint to get live locations of all active deliveries."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT d.id, d.delivery_code, d.delivery_status, d.current_lat, d.current_lng, d.last_gps_update,
               u.name AS driver_name, t.truck_code, t.plate_number, o.order_code, o.recipient_name, o.delivery_address
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN orders o ON d.order_id = o.id
        WHERE d.delivery_status IN ('assigned', 'loading', 'en_route')
        ORDER BY d.id DESC
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@main_bp.route("/api/gps/simulate/<int:delivery_id>", methods=["POST"])
@login_required()
def api_gps_simulate(delivery_id):
    """Simulate GPS advancement for testing and demonstration."""
    conn = get_db()
    row = conn.execute("SELECT current_lat, current_lng FROM deliveries WHERE id = ?", (delivery_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Not found"}), 404

    # Jitter or step location slightly within Lipa City
    cur_lat = row["current_lat"] or 13.9411
    cur_lng = row["current_lng"] or 121.1631
    next_lat = round(cur_lat + random.uniform(0.0010, 0.0030), 5)
    next_lng = round(cur_lng + random.uniform(-0.0015, 0.0020), 5)

    conn.execute(
        "UPDATE deliveries SET current_lat = ?, current_lng = ?, last_gps_update = datetime('now', 'localtime') WHERE id = ?",
        (next_lat, next_lng, delivery_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "lat": next_lat, "lng": next_lng})


# -------------------------------------------------------------------------
# ADMIN PORTAL
# -------------------------------------------------------------------------

@main_bp.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    conn = get_db()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer' AND is_active = 1").fetchone()[0]
    total_revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE order_status IN ('payment_verified', 'ready_for_dispatch', 'out_for_delivery', 'in_transit', 'delivered')").fetchone()[0]
    pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('pending', 'pending_scheduling')").fetchone()[0]
    low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity <= low_stock_threshold").fetchone()[0]
    in_progress_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status IN ('assigned', 'loading', 'en_route')").fetchone()[0]
    stock_in = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory_logs WHERE movement_type = 'stock_in'").fetchone()[0]
    stock_out = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory_logs WHERE movement_type = 'stock_out'").fetchone()[0]
    payments_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    ready_dispatch = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE order_status IN ('for_scheduling', 'approved', 'awaiting_confirmation', 'schedule_confirmed', 'scheduled')"
    ).fetchone()[0]
    pending_receipts = conn.execute("SELECT COUNT(*) FROM payments WHERE payment_status = 'pending'").fetchone()[0]

    recent_orders = conn.execute(
        """
        SELECT o.*, u.name AS customer_name, p.method AS payment_method, p.payment_status
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN payments p ON o.id = p.order_id
        ORDER BY o.id DESC LIMIT 6
        """
    ).fetchall()

    recent_deliveries = conn.execute(
        """
        SELECT d.*, o.order_code, o.delivery_address, t.truck_code, u.name AS driver_name
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        ORDER BY d.id DESC LIMIT 4
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_orders=total_orders,
        total_products=total_products,
        total_customers=total_customers,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        low_stock=low_stock,
        in_progress_deliveries=in_progress_deliveries,
        stock_in=stock_in,
        stock_out=stock_out,
        payments_count=payments_count,
        ready_dispatch=ready_dispatch,
        pending_receipts=pending_receipts,
        recent_orders=recent_orders,
        recent_deliveries=recent_deliveries,
    )


@main_bp.route("/admin/orders")
@login_required("admin")
def admin_orders():
    tab = request.args.get("tab", "pending")
    conn = get_db()
    expire_stale_reservations(conn)

    base_sql = """
        SELECT o.*, u.name AS customer_name, u.phone AS customer_phone,
               p.method AS payment_method, p.payment_status, p.reference_number AS payment_ref,
               p.rejection_reason AS payment_rejection_reason,
               u_auth.name AS authorized_by_name,
               MIN(CASE WHEN pr.stock_quantity >= oi.quantity THEN 1 ELSE 0 END) AS all_in_stock
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN payments p ON o.id = p.order_id
        LEFT JOIN users u_auth ON o.authorized_by = u_auth.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products pr ON oi.product_id = pr.id
    """
    if tab in ("pending", "pending_scheduling"):
        where = " WHERE o.order_status IN ('pending', 'pending_scheduling')"
    elif tab == "for_scheduling":
        where = " WHERE o.order_status IN ('for_scheduling', 'approved')"
    elif tab == "awaiting_confirmation":
        where = " WHERE o.order_status = 'awaiting_confirmation'"
    elif tab == "payment_verification":
        where = " WHERE o.order_status IN ('schedule_confirmed', 'pending_payment', 'pending_payment_verification')"
    elif tab == "ready_authorization":
        where = " WHERE o.order_status = 'payment_verified'"
    elif tab in ("scheduled", "ready", "ready_for_dispatch"):
        where = " WHERE o.order_status IN ('ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit', 'preparing')"
    else:
        where = ""

    orders = conn.execute(
        base_sql + where + " GROUP BY o.id ORDER BY o.id DESC"
    ).fetchall()

    counts = {
        "pending": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('pending', 'pending_scheduling')").fetchone()[0],
        "for_scheduling": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('for_scheduling', 'approved')").fetchone()[0],
        "awaiting_confirmation": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status='awaiting_confirmation'").fetchone()[0],
        "payment_verification": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('schedule_confirmed', 'pending_payment', 'pending_payment_verification')").fetchone()[0],
        "ready_authorization": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'payment_verified'").fetchone()[0],
        "scheduled": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit', 'preparing')").fetchone()[0],
        "all": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }

    items_by_order = {}
    all_items = conn.execute(
        """
        SELECT oi.*, p.name, p.unit, p.stock_quantity,
               (p.stock_quantity >= oi.quantity) AS is_available,
               MAX(0, p.stock_quantity - oi.quantity) AS remaining_after
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        """
    ).fetchall()
    for item in all_items:
        items_by_order.setdefault(item["order_id"], []).append(item)

    trucks = conn.execute("SELECT * FROM trucks ORDER BY truck_code").fetchall()
    drivers = conn.execute("SELECT * FROM users WHERE role = 'driver' AND is_active = 1 ORDER BY name").fetchall()

    deliv_rows = conn.execute(
        """
        SELECT d.*, t.truck_code, t.plate_number, t.capacity AS truck_capacity, u.name AS driver_name, u.phone AS driver_phone
        FROM deliveries d
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        """
    ).fetchall()
    deliveries_by_order = {d["order_id"]: d for d in deliv_rows}

    existing_schedules = conn.execute(
        """
        SELECT o.id, o.order_code, o.assigned_date, o.assigned_time_slot, o.order_status,
               t.truck_code, t.plate_number, u.name AS driver_name
        FROM orders o
        JOIN deliveries d ON o.id = d.order_id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        WHERE o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
          AND o.assigned_date IS NOT NULL
        ORDER BY o.assigned_date ASC, o.assigned_time_slot ASC
        """
    ).fetchall()

    conn.close()
    return render_template(
        "admin/orders.html",
        orders=orders,
        tab=tab,
        counts=counts,
        pending_count=counts["pending"],
        for_scheduling_count=counts["for_scheduling"],
        awaiting_count=counts["awaiting_confirmation"],
        scheduled_count=counts["scheduled"],
        all_count=counts["all"],
        items_by_order=items_by_order,
        trucks=trucks,
        drivers=drivers,
        deliveries_by_order=deliveries_by_order,
        existing_schedules=existing_schedules,
    )


@main_bp.route("/admin/orders/<int:order_id>/assign-schedule", methods=["POST"])
@login_required("admin")
def admin_order_assign_schedule(order_id):
    assigned_date = request.form.get("assigned_date", "").strip()
    assigned_time_slot = request.form.get("assigned_time_slot", "").strip()
    try:
        truck_id = int(request.form.get("truck_id", 0))
        driver_id = int(request.form.get("driver_id", 0))
    except (ValueError, TypeError):
        truck_id = 0
        driver_id = 0

    approval_notes = request.form.get("approval_notes", "").strip()

    if not assigned_date or not assigned_time_slot or not truck_id or not driver_id:
        flash("Please provide delivery date, time slot, truck, and driver.", "warning")
        return redirect(url_for("main.admin_orders", tab="for_scheduling"))

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.admin_orders"))

    # CONFLICT CHECK: Is this truck or driver already assigned to another order on the same date and time slot?
    conflict = conn.execute(
        """
        SELECT o.order_code, o.assigned_date, o.assigned_time_slot,
               t.truck_code, t.plate_number, u.name AS driver_name,
               (d.truck_id = ?) AS truck_conflict,
               (d.driver_id = ?) AS driver_conflict
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        WHERE o.id != ?
          AND o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
          AND o.assigned_date = ?
          AND o.assigned_time_slot = ?
          AND (d.truck_id = ? OR d.driver_id = ?)
        """,
        (truck_id, driver_id, order_id, assigned_date, assigned_time_slot, truck_id, driver_id),
    ).fetchone()

    if conflict:
        conn.close()
        conflict_msg = []
        if conflict["truck_conflict"]:
            conflict_msg.append(f"Truck {conflict['truck_code']} ({conflict['plate_number']})")
        if conflict["driver_conflict"]:
            conflict_msg.append(f"Driver {conflict['driver_name']}")
        reason = " and ".join(conflict_msg)
        flash(
            f"Scheduling Conflict: {reason} is already booked for Order {clean_order_code(conflict['order_code'])} on {assigned_date} ({assigned_time_slot}). Please select a different truck, driver, or time slot.",
            "danger",
        )
        return redirect(url_for("main.admin_orders", tab="for_scheduling"))

    # If pending or pending_scheduling, deduct stock if not yet deducted
    if order["order_status"] in ("pending", "pending_scheduling"):
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        for item in items:
            conn.execute(
                "UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, 'stock_out', ?, ?, ?)",
                (item["product_id"], item["quantity"], f"Approved & Scheduled Order {clean_order_code(order['order_code'])}", session["user_id"]),
            )

    conn.execute(
        """
        UPDATE orders
        SET assigned_date = ?,
            assigned_time_slot = ?,
            preferred_date = ?,
            delivery_slot = ?,
            order_status = 'awaiting_confirmation',
            schedule_status = 'proposed',
            approval_notes = COALESCE(NULLIF(?, ''), approval_notes)
        WHERE id = ?
        """,
        (assigned_date, assigned_time_slot, assigned_date, assigned_time_slot, approval_notes, order_id),
    )

    existing_deliv = conn.execute("SELECT id FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()
    if existing_deliv:
        conn.execute(
            """
            UPDATE deliveries
            SET driver_id = ?, truck_id = ?, delivery_window = ?, delivery_status = 'assigned'
            WHERE order_id = ?
            """,
            (driver_id, truck_id, assigned_time_slot, order_id),
        )
    else:
        while True:
            d_code = f"DLV-{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"
            if not conn.execute("SELECT id FROM deliveries WHERE delivery_code = ?", (d_code,)).fetchone():
                break
        conn.execute(
            """
            INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
            VALUES (?, ?, ?, ?, ?, 'assigned', 13.9411, 121.1631)
            """,
            (d_code, order_id, driver_id, truck_id, assigned_time_slot),
        )

    create_notification(
        conn,
        order["customer_id"],
        "Delivery Schedule Proposed",
        f"Admin assigned a delivery schedule for order {clean_order_code(order['order_code'])}: {assigned_date} ({assigned_time_slot}). Please review and accept.",
        "schedule",
        order_id,
    )

    conn.commit()
    conn.close()
    flash(
        f"Delivery schedule for {clean_order_code(order['order_code'])} assigned ({assigned_date}, {assigned_time_slot}). Customer notified to accept.",
        "success",
    )
    return redirect(url_for("main.admin_orders", tab="awaiting_confirmation"))


@main_bp.route("/admin/orders/<int:order_id>/decision", methods=["POST"])
@login_required("admin")
def admin_order_decision(order_id):
    decision = request.form.get("decision")
    reason = request.form.get("rejection_reason", "").strip()
    approval_notes = request.form.get("approval_notes", "").strip()
    conn = get_db()

    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.admin_orders"))

    if decision == "approve":
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        for item in items:
            conn.execute(
                "UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, 'stock_out', ?, ?, ?)",
                (item["product_id"], item["quantity"], f"Approved Order {clean_order_code(order['order_code'])}", session["user_id"]),
            )
        conn.execute(
            "UPDATE orders SET order_status = 'for_scheduling', approval_notes = ? WHERE id = ?",
            (approval_notes, order_id),
        )
        flash(f"Order {clean_order_code(order['order_code'])} approved and stock reserved. Ready for delivery scheduling.", "success")
        conn.commit()
        conn.close()
        return redirect(url_for("main.admin_orders", tab="for_scheduling"))

    elif decision == "reject":
        conn.execute(
            "UPDATE orders SET order_status = 'cancelled', schedule_status = 'cancelled', rejection_reason = ? WHERE id = ?",
            (reason or "Rejected upon admin review", order_id),
        )
        flash(f"Order {clean_order_code(order['order_code'])} rejected.", "warning")
        conn.commit()
        conn.close()
        return redirect(url_for("main.admin_orders", tab="pending"))

    conn.commit()
    conn.close()
    return redirect(url_for("main.admin_orders"))


@main_bp.route("/admin/orders/<int:order_id>/authorize-delivery", methods=["POST"])
@login_required("admin")
def admin_order_authorize_delivery(order_id):
    """Admin delivery authorization gate: Ensures payment verified & schedule accepted before driver release."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("main.admin_orders"))

    payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchone()
    delivery = conn.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()

    # Rule 1: Delivery schedule must have been confirmed / accepted
    if not order["assigned_date"] or order["schedule_status"] != "accepted":
        conn.close()
        flash(f"Cannot authorize delivery: Delivery schedule for {clean_order_code(order['order_code'])} has not been confirmed by customer.", "warning")
        return redirect(url_for("main.admin_orders", tab="ready_authorization"))

    # Rule 2: Delivery assignment (truck and driver) must exist
    if not delivery or not delivery["driver_id"] or not delivery["truck_id"]:
        conn.close()
        flash(f"Cannot authorize delivery: No truck and driver assigned to {clean_order_code(order['order_code'])}. Please assign logistics first.", "warning")
        return redirect(url_for("main.admin_orders", tab="ready_authorization"))

    # Rule 3: Payment must be verified (or COD arrangement approved)
    if not payment:
        conn.close()
        flash(f"Cannot authorize delivery: No payment record found for {clean_order_code(order['order_code'])}.", "danger")
        return redirect(url_for("main.admin_orders", tab="ready_authorization"))

    if payment["method"] == "qr" and payment["payment_status"] not in ("verified", "paid"):
        conn.close()
        flash(f"Cannot authorize delivery: QR Payment for {clean_order_code(order['order_code'])} has not been verified yet. Admin must confirm payment receipt first.", "danger")
        return redirect(url_for("main.admin_payments"))

    if payment["method"] == "cash" and order["order_status"] not in ("payment_verified", "ready_for_dispatch") and payment["payment_status"] not in ("payment_due", "verified", "paid"):
        conn.close()
        flash(f"Cannot authorize delivery: Cash on Delivery arrangement for {clean_order_code(order['order_code'])} has not been approved yet.", "warning")
        return redirect(url_for("main.admin_payments"))

    # Prevent duplicate authorization
    if order["order_status"] == "ready_for_dispatch" and delivery["delivery_status"] == "authorized":
        conn.close()
        flash(f"Order {clean_order_code(order['order_code'])} is already authorized for dispatch.", "info")
        return redirect(url_for("main.admin_orders", tab="scheduled"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        UPDATE orders
        SET order_status = 'ready_for_dispatch',
            authorized_by = ?,
            authorized_at = ?
        WHERE id = ?
        """,
        (session["user_id"], now_str, order_id),
    )
    conn.execute(
        """
        UPDATE deliveries
        SET delivery_status = 'authorized',
            authorized_by = ?,
            authorized_at = ?
        WHERE id = ?
        """,
        (session["user_id"], now_str, delivery["id"]),
    )
    create_notification(
        conn,
        order["customer_id"],
        "Ready for Dispatch",
        f"Order {clean_order_code(order['order_code'])} has been authorized for delivery. Assigned truck is preparing for dispatch.",
        "delivery",
        order_id,
    )
    conn.commit()
    conn.close()
    flash(f"Order {clean_order_code(order['order_code'])} authorized for delivery! The assigned driver has been released to begin dispatch.", "success")
    return redirect(url_for("main.admin_orders", tab="scheduled"))


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
                "INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url),
            )
            conn.commit()
            flash(f"Product '{name}' added successfully.", "success")

        elif action == "update_product":
            product_id = int(request.form.get("product_id"))
            name = request.form.get("name", "").strip()
            category_id = request.form.get("category_id")
            description = request.form.get("description", "").strip()
            unit = request.form.get("unit", "pc").strip()
            price = float(request.form.get("price", 0))
            stock_quantity = int(request.form.get("stock_quantity", 0))
            low_stock_threshold = int(request.form.get("low_stock_threshold", 20))
            image_url = request.form.get("image_url", "").strip()

            if image_url:
                conn.execute(
                    """
                    UPDATE products
                    SET category_id=?, name=?, description=?, unit=?, price=?, stock_quantity=?, low_stock_threshold=?, image_url=?
                    WHERE id=?
                    """,
                    (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url, product_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE products
                    SET category_id=?, name=?, description=?, unit=?, price=?, stock_quantity=?, low_stock_threshold=?
                    WHERE id=?
                    """,
                    (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, product_id),
                )
            conn.commit()
            flash(f"Product '{name}' updated successfully.", "success")

        elif action == "add_variation":
            product_id = int(request.form.get("product_id"))
            variation_name = request.form.get("variation_name", "").strip()
            price = float(request.form.get("price", 0))
            unit = request.form.get("unit", "").strip()
            stock_quantity = int(request.form.get("stock_quantity", 50))

            conn.execute(
                """
                INSERT INTO product_variations (product_id, variation_name, price, unit, stock_quantity, is_available)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (product_id, variation_name, price, unit, stock_quantity),
            )
            conn.commit()
            flash(f"Variation '{variation_name}' added successfully.", "success")

        elif action == "update_variation":
            variation_id = int(request.form.get("variation_id"))
            variation_name = request.form.get("variation_name", "").strip()
            price = float(request.form.get("price", 0))
            unit = request.form.get("unit", "").strip()
            stock_quantity = int(request.form.get("stock_quantity", 0))
            is_available = int(request.form.get("is_available", 1))

            conn.execute(
                """
                UPDATE product_variations
                SET variation_name = ?, price = ?, unit = ?, stock_quantity = ?, is_available = ?
                WHERE id = ?
                """,
                (variation_name, price, unit, stock_quantity, is_available, variation_id),
            )
            conn.commit()
            flash(f"Variation '{variation_name}' updated successfully.", "success")

        elif action == "delete_variation":
            variation_id = int(request.form.get("variation_id"))
            conn.execute("UPDATE product_variations SET is_available = 0 WHERE id = ?", (variation_id,))
            conn.commit()
            flash("Variation deactivated successfully.", "info")

        elif action == "stock_movement":
            product_id = int(request.form.get("product_id"))
            movement_type = request.form.get("movement_type", "stock_in")
            quantity = int(request.form.get("quantity", 0))
            supplier_ref = request.form.get("reference", "").strip()
            remarks_text = request.form.get("remarks", "").strip()
            full_remarks = f"{supplier_ref} · {remarks_text}" if supplier_ref else remarks_text

            if movement_type == "stock_in":
                conn.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (quantity, product_id))
            else:
                conn.execute("UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?", (quantity, product_id))

            conn.execute(
                "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, ?, ?, ?, ?)",
                (product_id, movement_type, quantity, full_remarks, session["user_id"]),
            )
            conn.commit()
            flash("Stock movement successfully recorded.", "success")

        conn.close()
        return redirect(url_for("main.admin_inventory"))

    products = [dict(p) for p in conn.execute(
        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE p.is_active = 1 ORDER BY p.id"
    ).fetchall()]

    all_variations = [dict(v) for v in conn.execute(
        "SELECT * FROM product_variations WHERE is_available = 1 ORDER BY price ASC"
    ).fetchall()]
    vars_by_product = {}
    for v in all_variations:
        vars_by_product.setdefault(v["product_id"], []).append(v)
    for p in products:
        p["variations"] = vars_by_product.get(p["id"], [])

    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    low_stock_count = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity <= low_stock_threshold AND is_active = 1").fetchone()[0]
    logs = conn.execute(
        """
        SELECT l.*, p.name AS product_name, u.name AS staff_name
        FROM inventory_logs l
        JOIN products p ON l.product_id = p.id
        LEFT JOIN users u ON l.created_by = u.id
        ORDER BY l.id DESC LIMIT 15
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
    expire_stale_reservations(conn)

    if request.method == "POST":
        try:
            order_id = int(request.form.get("order_id", 0))
            driver_id = int(request.form.get("driver_id", 0))
            truck_id = int(request.form.get("truck_id", 0))
        except (ValueError, TypeError):
            order_id = driver_id = truck_id = 0

        assigned_date = request.form.get("assigned_date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        assigned_time_slot = request.form.get("assigned_time_slot", "").strip() or request.form.get("delivery_window", "Morning (08:00 - 12:00)").strip()

        if not order_id or not driver_id or not truck_id:
            flash("Please select an order, driver, and truck.", "warning")
            return redirect(url_for("main.admin_deliveries"))

        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            conn.close()
            flash("Order not found.", "danger")
            return redirect(url_for("main.admin_deliveries"))

        # CONFLICT CHECK: Does truck or driver have overlapping delivery on assigned_date & time slot?
        conflict = conn.execute(
            """
            SELECT o.order_code, o.assigned_date, o.assigned_time_slot,
                   t.truck_code, t.plate_number, u.name AS driver_name,
                   (d.truck_id = ?) AS truck_conflict,
                   (d.driver_id = ?) AS driver_conflict
            FROM deliveries d
            JOIN orders o ON d.order_id = o.id
            LEFT JOIN trucks t ON d.truck_id = t.id
            LEFT JOIN users u ON d.driver_id = u.id
            WHERE o.id != ?
              AND o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'scheduled', 'out_for_delivery', 'in_transit')
              AND o.assigned_date = ?
              AND o.assigned_time_slot = ?
              AND (d.truck_id = ? OR d.driver_id = ?)
            """,
            (truck_id, driver_id, order_id, assigned_date, assigned_time_slot, truck_id, driver_id),
        ).fetchone()

        if conflict:
            conn.close()
            conflict_msg = []
            if conflict["truck_conflict"]:
                conflict_msg.append(f"Truck {conflict['truck_code']} ({conflict['plate_number']})")
            if conflict["driver_conflict"]:
                conflict_msg.append(f"Driver {conflict['driver_name']}")
            reason = " and ".join(conflict_msg)
            flash(
                f"Scheduling Conflict: {reason} is already booked for Order {clean_order_code(conflict['order_code'])} on {assigned_date} ({assigned_time_slot}). Please select an alternate vehicle, driver, or time slot.",
                "danger",
            )
            return redirect(url_for("main.admin_deliveries"))

        existing = conn.execute("SELECT id FROM deliveries WHERE order_id = ?", (order_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE deliveries SET driver_id=?, truck_id=?, delivery_window=?, delivery_status='assigned' WHERE order_id=?",
                (driver_id, truck_id, assigned_time_slot, order_id),
            )
        else:
            while True:
                d_code = f"DLV-{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"
                if not conn.execute("SELECT id FROM deliveries WHERE delivery_code = ?", (d_code,)).fetchone():
                    break
            conn.execute(
                """
                INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
                VALUES (?, ?, ?, ?, ?, 'assigned', 13.9411, 121.1631)
                """,
                (d_code, order_id, driver_id, truck_id, assigned_time_slot),
            )

        new_status = "scheduled" if order["schedule_status"] == "accepted" else "awaiting_confirmation"
        new_sched_status = "accepted" if order["schedule_status"] == "accepted" else "proposed"
        conn.execute(
            """
            UPDATE orders
            SET assigned_date = ?,
                assigned_time_slot = ?,
                preferred_date = ?,
                delivery_slot = ?,
                order_status = ?,
                schedule_status = ?
            WHERE id = ?
            """,
            (assigned_date, assigned_time_slot, assigned_date, assigned_time_slot, new_status, new_sched_status, order_id),
        )
        conn.commit()
        flash(f"Delivery scheduled for {assigned_date} ({assigned_time_slot})! Order status: {new_status.replace('_', ' ').title()}.", "success")
        conn.close()
        return redirect(url_for("main.admin_deliveries"))

    counts = {
        "for_scheduling": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('for_scheduling', 'approved')").fetchone()[0],
        "awaiting_confirmation": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'awaiting_confirmation'").fetchone()[0],
        "scheduled": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('scheduled', 'schedule_confirmed')").fetchone()[0],
        "en_route": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status = 'en_route'").fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status = 'delivered'").fetchone()[0],
        "assigned": conn.execute("SELECT COUNT(*) FROM deliveries WHERE delivery_status IN ('assigned', 'loading')").fetchone()[0],
        "queued": conn.execute("SELECT COUNT(*) FROM orders WHERE order_status IN ('for_scheduling', 'approved')").fetchone()[0],
    }

    ready_orders = conn.execute(
        """
        SELECT o.*, u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        WHERE o.order_status IN ('pending', 'pending_scheduling', 'for_scheduling', 'approved', 'awaiting_confirmation', 'schedule_confirmed', 'scheduled')
        ORDER BY o.id DESC
        """
    ).fetchall()

    drivers = conn.execute("SELECT * FROM users WHERE role='driver' AND is_active=1 ORDER BY name").fetchall()
    trucks = conn.execute("SELECT * FROM trucks ORDER BY truck_code").fetchall()
    deliveries = conn.execute(
        """
        SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.assigned_date, o.assigned_time_slot, o.order_status,
               u.name AS driver_name, t.truck_code, t.plate_number,
               p.payment_status, p.method AS payment_method
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN payments p ON o.id = p.order_id
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


@main_bp.route("/admin/delivery-availability", methods=["GET", "POST"])
@login_required("admin")
def admin_delivery_availability():
    """Admin delivery schedule availability and capacity management."""
    conn = get_db()
    expire_stale_reservations(conn)

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "update_settings":
            try:
                timeout_h = max(1, int(request.form.get("reservation_timeout_hours", 24)))
                cap = max(1, int(request.form.get("default_slot_capacity", 3)))
                lead = max(0, int(request.form.get("lead_time_days", 1)))
                horizon = max(1, int(request.form.get("horizon_days", 14)))
            except (ValueError, TypeError):
                timeout_h, cap, lead, horizon = 24, 3, 1, 14

            settings_to_save = [
                ("reservation_timeout_hours", str(timeout_h)),
                ("default_slot_capacity", str(cap)),
                ("lead_time_days", str(lead)),
                ("horizon_days", str(horizon)),
            ]
            for k, v in settings_to_save:
                conn.execute(
                    """
                    INSERT INTO delivery_settings (setting_key, setting_value)
                    VALUES (?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                    """,
                    (k, v),
                )
            conn.commit()
            flash("Delivery availability settings updated successfully.", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

        elif action == "toggle_slot":
            delivery_date = request.form.get("delivery_date", "").strip()
            time_slot = request.form.get("time_slot", "").strip()
            if delivery_date and time_slot:
                row = conn.execute(
                    "SELECT is_available, max_capacity FROM delivery_availability WHERE delivery_date = ? AND time_slot = ?",
                    (delivery_date, time_slot),
                ).fetchone()
                default_cap = int(get_delivery_setting(conn, "default_slot_capacity", 3))
                if row:
                    new_avail = 0 if row["is_available"] == 1 else 1
                    conn.execute(
                        "UPDATE delivery_availability SET is_available = ? WHERE delivery_date = ? AND time_slot = ?",
                        (new_avail, delivery_date, time_slot),
                    )
                else:
                    new_avail = 0
                    conn.execute(
                        """
                        INSERT INTO delivery_availability (delivery_date, time_slot, max_capacity, is_available, notes)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (delivery_date, time_slot, default_cap, new_avail, "Manually blocked"),
                    )
                conn.commit()
                status_str = "Enabled" if new_avail == 1 else "Blocked / Blackout"
                flash(f"Slot {delivery_date} {time_slot} is now {status_str}.", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

        elif action == "update_slot":
            delivery_date = request.form.get("delivery_date", "").strip()
            time_slot = request.form.get("time_slot", "").strip()
            try:
                max_capacity = max(1, int(request.form.get("max_capacity", 3)))
            except (ValueError, TypeError):
                max_capacity = 3
            is_available = 1 if request.form.get("is_available") in ("1", "on", "true") else 0
            notes = request.form.get("notes", "").strip()

            if delivery_date and time_slot:
                conn.execute(
                    """
                    INSERT INTO delivery_availability (delivery_date, time_slot, max_capacity, is_available, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(delivery_date, time_slot) DO UPDATE SET
                        max_capacity = excluded.max_capacity,
                        is_available = excluded.is_available,
                        notes = excluded.notes
                    """,
                    (delivery_date, time_slot, max_capacity, is_available, notes),
                )
                conn.commit()
                flash(f"Updated capacity & availability for {delivery_date} ({time_slot}).", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

        elif action == "bulk_generate":
            try:
                days_ahead = max(1, int(request.form.get("days_ahead", 14)))
                default_cap = max(1, int(request.form.get("default_capacity", 3)))
            except (ValueError, TypeError):
                days_ahead, default_cap = 14, 3

            today_d = datetime.now().date()
            std_slots = ["Morning (08:00 - 12:00)", "Afternoon (13:00 - 17:00)"]
            for i in range(1, days_ahead + 1):
                day_target = today_d + timedelta(days=i)
                day_str = day_target.strftime("%Y-%m-%d")
                is_avail = 0 if day_target.weekday() == 6 else 1
                day_note = "Sunday - Closed" if day_target.weekday() == 6 else None
                for s_name in std_slots:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO delivery_availability (delivery_date, time_slot, max_capacity, is_available, notes)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (day_str, s_name, default_cap, is_avail, day_note),
                    )
            conn.commit()
            flash(f"Populated delivery schedule availability for the next {days_ahead} days.", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

        elif action == "toggle_truck":
            try:
                truck_id = int(request.form.get("truck_id", 0))
            except (ValueError, TypeError):
                truck_id = 0
            new_status = request.form.get("status", "available").strip()
            if truck_id and new_status in ("available", "maintenance"):
                conn.execute("UPDATE trucks SET status = ? WHERE id = ?", (new_status, truck_id))
                conn.commit()
                flash(f"Truck status updated to {new_status.title()}.", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

        elif action == "toggle_driver":
            try:
                driver_id = int(request.form.get("driver_id", 0))
                is_active = int(request.form.get("is_active", 1))
            except (ValueError, TypeError):
                driver_id = 0
                is_active = 1
            if driver_id:
                conn.execute("UPDATE users SET is_active = ? WHERE id = ? AND role = 'driver'", (is_active, driver_id))
                conn.commit()
                flash("Driver availability updated.", "success")
            conn.close()
            return redirect(url_for("main.admin_delivery_availability"))

    # GET: Prepare settings, metrics, and schedule matrix
    settings = {
        "reservation_timeout_hours": int(get_delivery_setting(conn, "reservation_timeout_hours", 24)),
        "default_slot_capacity": int(get_delivery_setting(conn, "default_slot_capacity", 3)),
        "lead_time_days": int(get_delivery_setting(conn, "lead_time_days", 1)),
        "horizon_days": int(get_delivery_setting(conn, "horizon_days", 14)),
    }

    horizon = settings["horizon_days"]
    lead_time = settings["lead_time_days"]
    default_capacity = settings["default_slot_capacity"]
    today = datetime.now().date()
    std_slots = ["Morning (08:00 - 12:00)", "Afternoon (13:00 - 17:00)"]

    avail_rows = conn.execute("SELECT * FROM delivery_availability").fetchall()
    avail_map = {(r["delivery_date"], r["time_slot"]): r for r in avail_rows}

    active_orders = conn.execute(
        """
        SELECT o.id, o.order_code, o.assigned_date, o.assigned_time_slot, o.order_status, o.total_amount,
               u.name AS customer_name,
               d.truck_id, d.driver_id, t.truck_code, t.plate_number, u_drv.name AS driver_name
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        LEFT JOIN deliveries d ON o.id = d.order_id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u_drv ON d.driver_id = u_drv.id
        WHERE o.order_status IN ('awaiting_confirmation', 'schedule_confirmed', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'out_for_delivery', 'in_transit')
          AND o.assigned_date IS NOT NULL
        ORDER BY o.assigned_date, o.assigned_time_slot
        """
    ).fetchall()

    bookings_map = {}
    for ord_row in active_orders:
        key = (ord_row["assigned_date"], ord_row["assigned_time_slot"])
        bookings_map.setdefault(key, []).append(ord_row)

    schedule_calendar = []
    total_slots = 0
    available_slots_count = 0
    booked_slots_count = 0
    blackout_slots_count = 0

    for i in range(0, horizon + lead_time):
        day_d = today + timedelta(days=i)
        day_str = day_d.strftime("%Y-%m-%d")
        day_name = day_d.strftime("%A")
        is_lead_day = (i < lead_time)

        for slot_name in std_slots:
            total_slots += 1
            cfg = avail_map.get((day_str, slot_name))
            if cfg:
                is_available = bool(cfg["is_available"])
                max_capacity = cfg["max_capacity"]
                notes = cfg["notes"] or ""
            else:
                is_available = False if day_d.weekday() == 6 else True
                max_capacity = default_capacity
                notes = "Sunday - Closed" if day_d.weekday() == 6 else ""

            bookings = bookings_map.get((day_str, slot_name), [])
            booked_count = len(bookings)
            remaining = max(0, max_capacity - booked_count)

            if not is_available:
                status = "unavailable"
                blackout_slots_count += 1
            elif booked_count >= max_capacity:
                status = "full"
                booked_slots_count += 1
            else:
                status = "available"
                available_slots_count += 1

            schedule_calendar.append({
                "date": day_str,
                "day_name": day_name,
                "time_slot": slot_name,
                "is_available": is_available,
                "max_capacity": max_capacity,
                "booked_count": booked_count,
                "remaining": remaining,
                "notes": notes,
                "status": status,
                "is_lead_day": is_lead_day,
                "bookings": bookings,
            })

    trucks = conn.execute("SELECT * FROM trucks ORDER BY truck_code").fetchall()
    drivers = conn.execute("SELECT * FROM users WHERE role = 'driver' ORDER BY name").fetchall()
    conn.close()

    metrics = {
        "horizon_days": horizon,
        "total_slots": total_slots,
        "available_slots": available_slots_count,
        "full_slots": booked_slots_count,
        "blackout_slots": blackout_slots_count,
        "active_trucks": sum(1 for t in trucks if t["status"] != "maintenance"),
        "total_trucks": len(trucks),
        "active_drivers": sum(1 for d in drivers if d["is_active"] == 1),
        "total_drivers": len(drivers),
    }

    return render_template(
        "admin/delivery_availability.html",
        settings=settings,
        metrics=metrics,
        calendar=schedule_calendar,
        trucks=trucks,
        drivers=drivers,
    )


@main_bp.route("/admin/customers")
@login_required("admin")
def admin_customers():
    conn = get_db()
    customers = conn.execute(
        """
        SELECT u.*, COUNT(o.id) AS total_orders, COUNT(o.id) AS order_count,
               COALESCE(SUM(o.total_amount), 0) AS total_spent
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
        action = request.form.get("action", "")

        if action in ("confirm_payment", "verify_status"):
            payment_id = int(request.form.get("payment_id"))
            p_row = conn.execute("SELECT p.*, o.order_code FROM payments p JOIN orders o ON p.order_id = o.id WHERE p.id = ?", (payment_id,)).fetchone()
            if not p_row:
                conn.close()
                flash("Payment record not found.", "danger")
                return redirect(url_for("main.admin_payments"))

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if p_row["method"] == "cash":
                # Special COD Handling: approve arrangement without marking Paid before collection
                conn.execute(
                    """
                    UPDATE payments
                    SET payment_status = 'payment_due',
                        verified_by = ?,
                        verified_at = ?,
                        rejection_reason = NULL
                    WHERE id = ?
                    """,
                    (session["user_id"], now_str, payment_id),
                )
                conn.execute(
                    """
                    UPDATE orders
                    SET order_status = 'payment_verified',
                        rejection_reason = NULL
                    WHERE id = ?
                    """,
                    (p_row["order_id"],),
                )
                flash(f"Cash on Delivery arrangement for Order {clean_order_code(p_row['order_code'])} approved! Order is now eligible for delivery authorization.", "success")
            else:
                # Online QR: verify actual receipt of payment
                conn.execute(
                    """
                    UPDATE payments
                    SET payment_status = 'verified',
                        verified_by = ?,
                        verified_at = ?,
                        paid_at = ?,
                        rejection_reason = NULL
                    WHERE id = ?
                    """,
                    (session["user_id"], now_str, now_str, payment_id),
                )
                conn.execute(
                    """
                    UPDATE orders
                    SET order_status = 'payment_verified',
                        rejection_reason = NULL
                    WHERE id = ?
                    """,
                    (p_row["order_id"],),
                )
                flash(f"QR Payment for Order {clean_order_code(p_row['order_code'])} successfully verified and confirmed! Order is now eligible for delivery authorization.", "success")

            conn.commit()

        elif action == "reject_payment":
            payment_id = int(request.form.get("payment_id"))
            rejection_reason = request.form.get("rejection_reason", "").strip()
            if not rejection_reason:
                conn.close()
                flash("Please provide a rejection reason so the customer can correct the payment.", "warning")
                return redirect(url_for("main.admin_payments"))

            p_row = conn.execute("SELECT p.*, o.order_code FROM payments p JOIN orders o ON p.order_id = o.id WHERE p.id = ?", (payment_id,)).fetchone()
            if not p_row:
                conn.close()
                flash("Payment record not found.", "danger")
                return redirect(url_for("main.admin_payments"))

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                UPDATE payments
                SET payment_status = 'rejected',
                    rejection_reason = ?,
                    verified_by = ?,
                    verified_at = ?
                WHERE id = ?
                """,
                (rejection_reason, session["user_id"], now_str, payment_id),
            )
            conn.execute(
                """
                UPDATE orders
                SET order_status = 'payment_rejected',
                    rejection_reason = ?
                WHERE id = ?
                """,
                (rejection_reason, p_row["order_id"]),
            )
            conn.commit()
            flash(f"Payment for Order {clean_order_code(p_row['order_code'])} rejected with reason: '{rejection_reason}'. Customer notified to resubmit.", "info")

        elif action == "record_cod_collected":
            payment_id = int(request.form.get("payment_id"))
            p_row = conn.execute("SELECT p.*, o.order_code FROM payments p JOIN orders o ON p.order_id = o.id WHERE p.id = ?", (payment_id,)).fetchone()
            if p_row:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    """
                    UPDATE payments
                    SET payment_status = 'paid',
                        paid_at = ?,
                        verified_by = ?,
                        verified_at = ?
                    WHERE id = ?
                    """,
                    (now_str, session["user_id"], now_str, payment_id),
                )
                conn.commit()
                flash(f"Cash on Delivery collection for Order {clean_order_code(p_row['order_code'])} officially confirmed as Paid.", "success")

        elif action == "record_payment":
            order_id = int(request.form.get("order_id"))
            method = request.form.get("method", "cash")
            ref = request.form.get("reference_number", "").strip() or request.form.get("reference_no", "").strip()
            status = request.form.get("status", "verified")
            notes = request.form.get("notes", "").strip()
            amount = float(request.form.get("amount", 0))

            existing = conn.execute("SELECT id FROM payments WHERE order_id = ?", (order_id,)).fetchone()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if existing:
                conn.execute(
                    """
                    UPDATE payments
                    SET method=?, reference_number=?, payment_status=?, receipt_note=?, amount=?, verified_by=?, verified_at=?
                    WHERE order_id=?
                    """,
                    (method, ref, status, notes, amount, session["user_id"], now_str, order_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO payments (order_id, method, reference_number, payment_status, receipt_note, amount, verified_by, verified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, method, ref, status, notes, amount, session["user_id"], now_str),
                )

            if status in ("verified", "paid") or (method == "cash" and status == "payment_due"):
                conn.execute(
                    "UPDATE orders SET order_status = 'payment_verified', rejection_reason = NULL WHERE id = ?",
                    (order_id,),
                )
                ord_row = conn.execute("SELECT customer_id, order_code FROM orders WHERE id = ?", (order_id,)).fetchone()
                if ord_row:
                    create_notification(
                        conn,
                        ord_row["customer_id"],
                        "Payment Verified",
                        f"Payment for order {clean_order_code(ord_row['order_code'])} has been verified and confirmed. Ready for warehouse dispatch.",
                        "payment",
                        order_id,
                    )
            conn.commit()
            flash("Payment and receipt successfully recorded.", "success")

        conn.close()
        return redirect(url_for("main.admin_payments"))

    tab = request.args.get("tab", "awaiting")
    base_sql = """
        SELECT p.*, p.reference_number, o.order_code, o.recipient_name, o.phone AS customer_phone, o.delivery_address,
               o.total_amount AS order_total, o.order_status, o.assigned_date, o.assigned_time_slot,
               u_ver.name AS verified_by_name
        FROM payments p
        JOIN orders o ON p.order_id = o.id
        LEFT JOIN users u_ver ON p.verified_by = u_ver.id
    """
    if tab == "awaiting":
        where = " WHERE p.payment_status IN ('pending', 'pending_verification') OR (p.method = 'cash' AND o.order_status = 'pending_payment_verification')"
    elif tab == "verified":
        where = " WHERE p.payment_status IN ('verified', 'paid') OR (p.method = 'cash' AND o.order_status IN ('payment_verified', 'ready_for_dispatch', 'out_for_delivery', 'delivered'))"
    elif tab == "rejected":
        where = " WHERE p.payment_status = 'rejected' OR o.order_status = 'payment_rejected'"
    else:
        where = ""

    payments = conn.execute(base_sql + where + " ORDER BY p.id DESC").fetchall()

    counts = {
        "awaiting": conn.execute(
            """
            SELECT COUNT(*) FROM payments p
            JOIN orders o ON p.order_id = o.id
            WHERE p.payment_status IN ('pending', 'pending_verification')
               OR (p.method = 'cash' AND o.order_status = 'pending_payment_verification')
            """
        ).fetchone()[0],
        "verified": conn.execute(
            """
            SELECT COUNT(*) FROM payments p
            JOIN orders o ON p.order_id = o.id
            WHERE p.payment_status IN ('verified', 'paid')
               OR (p.method = 'cash' AND o.order_status IN ('payment_verified', 'ready_for_dispatch', 'out_for_delivery', 'delivered'))
            """
        ).fetchone()[0],
        "rejected": conn.execute(
            """
            SELECT COUNT(*) FROM payments p
            JOIN orders o ON p.order_id = o.id
            WHERE p.payment_status = 'rejected' OR o.order_status = 'payment_rejected'
            """
        ).fetchone()[0],
        "all": conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
    }

    all_orders = conn.execute(
        """
        SELECT o.id, o.order_code, o.recipient_name, o.total_amount, p.payment_status
        FROM orders o
        LEFT JOIN payments p ON o.id = p.order_id
        ORDER BY o.id DESC
        """
    ).fetchall()

    conn.close()
    return render_template(
        "admin/payments.html",
        payments=payments,
        all_orders=all_orders,
        tab=tab,
        counts=counts,
    )


@main_bp.route("/admin/reports")
@login_required("admin")
def admin_reports():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()
    query = """
        SELECT o.*, u.name AS customer_name, p.method AS payment_method, p.payment_status
        FROM orders o
        JOIN users u ON o.customer_id = u.id
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

    # Sales by category for chart (filtered by date if provided)
    cat_query = """
        SELECT c.name, COALESCE(SUM(oi.subtotal), 0) AS revenue
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        LEFT JOIN (
            SELECT oi.product_id, oi.subtotal
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.order_status != 'rejected'
    """
    cat_params = []
    if start_date:
        cat_query += " AND date(o.created_at) >= date(?)"
        cat_params.append(start_date)
    if end_date:
        cat_query += " AND date(o.created_at) <= date(?)"
        cat_params.append(end_date)
    cat_query += """
        ) oi ON p.id = oi.product_id
        GROUP BY c.id
        ORDER BY revenue DESC
    """
    cat_sales = conn.execute(cat_query, cat_params).fetchall()

    # Daily orders for trend (filtered by date if provided, latest 7 days)
    daily_query = """
        SELECT date(created_at) AS order_date, COUNT(*) AS count,
               SUM(CASE WHEN order_status IN ('approved', 'in_transit', 'delivered') THEN 1 ELSE 0 END) AS approved_count
        FROM orders
        WHERE 1=1
    """
    daily_params = []
    if start_date:
        daily_query += " AND date(created_at) >= date(?)"
        daily_params.append(start_date)
    if end_date:
        daily_query += " AND date(created_at) <= date(?)"
        daily_params.append(end_date)
    daily_query += """
        GROUP BY date(created_at)
        ORDER BY order_date DESC
        LIMIT 7
    """
    daily_orders_raw = conn.execute(daily_query, daily_params).fetchall()
    daily_orders = list(reversed(daily_orders_raw))

    conn.close()

    max_cat_rev = max([float(c["revenue"] or 0) for c in cat_sales] or [1.0])
    if max_cat_rev <= 0:
        max_cat_rev = 1.0

    max_daily_count = max([int(d["count"] or 0) for d in daily_orders] or [1])
    if max_daily_count <= 0:
        max_daily_count = 1

    return render_template(
        "admin/reports.html",
        orders=orders,
        total_sales=total_sales,
        low_stock_items=low_stock_items,
        cat_sales=cat_sales,
        daily_orders=daily_orders,
        max_cat_rev=max_cat_rev,
        max_daily_count=max_daily_count,
        start_date=start_date,
        end_date=end_date,
    )


def log_access_event(conn, action, affected_user, performed_by_id, performed_by_name, details=""):
    """Helper to safely record an access or permission management event."""
    try:
        aff_id = None
        aff_name = ""
        aff_email = ""
        aff_role = ""
        if affected_user is not None:
            try:
                aff_id = affected_user["id"]
            except Exception:
                pass
            try:
                aff_name = affected_user["name"] or ""
            except Exception:
                pass
            try:
                aff_email = affected_user["email"] or ""
            except Exception:
                pass
            try:
                aff_role = affected_user["role"] or ""
            except Exception:
                pass

        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        conn.execute(
            """
            INSERT INTO access_logs (action, affected_user_id, affected_user_name, affected_user_email, affected_user_role, performed_by, performed_by_name, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (action, aff_id, aff_name, aff_email, aff_role, performed_by_id, performed_by_name, details, ip),
        )
    except Exception:
        pass


@main_bp.route("/admin/access", methods=["GET", "POST"])
@login_required("admin")
def admin_access():
    conn = get_db()
    current_admin_id = session.get("user_id")
    current_admin_name = session.get("user_name", "Admin")

    if request.method == "POST":
        action = request.form.get("action")
        target_tab = request.form.get("target_tab", "accounts")

        if action == "add_staff":
            name = request.form.get("name", "").strip()
            role = request.form.get("role", "driver")
            staff_id = request.form.get("staff_id", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "rml12345")

            if role not in ("admin", "driver", "staff"):
                role = "driver"

            if not staff_id:
                prefix = "RML-ADM" if role == "admin" else "RML-DRV"
                staff_id = f"{prefix}-{random.randint(100, 999)}"

            # Ensure unique staff_id and email
            existing = conn.execute("SELECT id FROM users WHERE staff_id = ? OR LOWER(email) = ?", (staff_id, email)).fetchone()
            if existing:
                flash(f"Staff ID '{staff_id}' or Email '{email}' is already in use.", "danger")
            else:
                conn.execute(
                    "INSERT INTO users (staff_id, name, email, phone, password_hash, role, is_active, is_verified) VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
                    (staff_id, name, email, phone, generate_password_hash(password), role),
                )
                conn.commit()
                new_u = conn.execute("SELECT * FROM users WHERE staff_id = ?", (staff_id,)).fetchone()
                log_access_event(
                    conn,
                    "Staff Account Created",
                    new_u,
                    current_admin_id,
                    current_admin_name,
                    f"Created {role.title()} account '{name}' ({staff_id}) with temporary password.",
                )
                conn.commit()
                flash(f"Created {role.title()} account for {name} ({staff_id}) successfully.", "success")
                target_tab = "accounts"

        elif action == "update_role":
            uid = int(request.form.get("user_id", 0))
            new_role = request.form.get("role", "driver")

            # Self-demotion protection: prevent admins from locking themselves out
            if uid == current_admin_id and new_role != "admin":
                flash("Protection active: Administrators cannot remove their own administrative privileges.", "danger")
                target_tab = "roles"
            elif new_role not in ("admin", "driver", "staff"):
                flash("Invalid role selection.", "danger")
                target_tab = "roles"
            else:
                u = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
                if u:
                    old_role = u["role"]
                    if old_role != new_role:
                        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, uid))
                        conn.commit()
                        log_access_event(
                            conn,
                            "Role Updated",
                            u,
                            current_admin_id,
                            current_admin_name,
                            f"Role changed from {old_role.title()} to {new_role.title()}.",
                        )
                        conn.commit()
                        flash(f"Role for {u['name']} successfully changed to {new_role.title()}.", "success")
                    else:
                        flash(f"{u['name']} is already assigned the {new_role.title()} role.", "info")
                else:
                    flash("User account not found.", "danger")
                target_tab = "roles"

        elif action == "toggle_active":
            uid = int(request.form.get("user_id", 0))
            explicit_status = request.form.get("status")  # Optional: 'active' or 'suspended'

            # Self-lockout protection: prevent administrator from suspending their own active session
            if uid == current_admin_id:
                flash("Protection active: You cannot suspend your own active administrator account.", "danger")
                target_tab = "accounts"
            else:
                u = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
                if u:
                    if explicit_status == "suspended":
                        new_status = 0
                    elif explicit_status == "active":
                        new_status = 1
                    else:
                        new_status = 0 if u["is_active"] == 1 else 1

                    conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, uid))
                    conn.commit()

                    status_label = "Active" if new_status == 1 else "Suspended"
                    action_name = "Account Activated" if new_status == 1 else "Account Suspended"
                    log_access_event(
                        conn,
                        action_name,
                        u,
                        current_admin_id,
                        current_admin_name,
                        f"Account status set to {status_label} by administrator.",
                    )
                    conn.commit()
                    flash(f"Account for {u['name']} is now {status_label}.", "success" if new_status == 1 else "warning")
                else:
                    flash("User account not found.", "danger")
                target_tab = "accounts"

        conn.close()
        return redirect(url_for("main.admin_access", tab=target_tab))

    # GET Request: Fetch users and compute stats
    active_tab = request.args.get("tab", "accounts")
    search_q = request.args.get("search", "").strip()
    role_f = request.args.get("role_filter", "all").strip().lower()
    status_f = request.args.get("status_filter", "all").strip().lower()

    # Query enriched users with order and delivery metrics
    users_query = """
        SELECT u.*,
               (SELECT COUNT(*) FROM orders WHERE customer_id = u.id) AS order_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE customer_id = u.id AND order_status != 'rejected') AS total_spent,
               (SELECT COUNT(*) FROM deliveries WHERE driver_id = u.id) AS delivery_count,
               (SELECT COUNT(*) FROM deliveries WHERE driver_id = u.id AND delivery_status = 'delivered') AS completed_deliveries
        FROM users u
        ORDER BY 
            CASE WHEN u.role = 'admin' THEN 1 WHEN u.role = 'driver' THEN 2 ELSE 3 END,
            u.id ASC
    """
    all_users = conn.execute(users_query).fetchall()

    # Apply backend filters if requested
    filtered_users = []
    for u in all_users:
        # Search match
        if search_q:
            q_lower = search_q.lower()
            u_id_str = str(u["id"])
            staff_id_str = (u["staff_id"] or "").lower()
            name_str = (u["name"] or "").lower()
            email_str = (u["email"] or "").lower()
            phone_str = (u["phone"] or "").lower()
            if not (q_lower in name_str or q_lower in email_str or q_lower in phone_str or q_lower in staff_id_str or q_lower in u_id_str):
                continue

        # Role match
        if role_f and role_f != "all":
            if u["role"].lower() != role_f:
                continue

        # Status match
        if status_f and status_f != "all":
            if status_f == "active" and u["is_active"] != 1:
                continue
            if status_f == "suspended" and u["is_active"] != 0:
                continue

        filtered_users.append(u)

    # Calculate statistics across all accounts
    stats = {
        "total": len(all_users),
        "admin": sum(1 for u in all_users if u["role"] == "admin"),
        "driver": sum(1 for u in all_users if u["role"] == "driver"),
        "customer": sum(1 for u in all_users if u["role"] == "customer"),
        "active": sum(1 for u in all_users if u["is_active"] == 1),
        "suspended": sum(1 for u in all_users if u["is_active"] == 0),
    }

    staff_users = [u for u in all_users if u["role"] in ("admin", "driver", "staff")]

    # Fetch real access logs
    access_logs = conn.execute(
        """
        SELECT * FROM access_logs ORDER BY id DESC LIMIT 100
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin/access.html",
        users=filtered_users,
        all_users=all_users,
        staff_users=staff_users,
        access_logs=access_logs,
        stats=stats,
        active_tab=active_tab,
        search_query=search_q,
        role_filter=role_f,
        status_filter=status_f,
    )


# -------------------------------------------------------------------------
# DRIVER PORTAL
# -------------------------------------------------------------------------

@main_bp.route("/driver/schedule", endpoint="driver_schedule")
@main_bp.route("/driver/dashboard", endpoint="driver_dashboard")
@login_required("driver")
def driver_schedule():
    conn = get_db()
    uid = session["user_id"]

    query = """
        SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.phone, o.order_status,
               t.truck_code, t.plate_number
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN trucks t ON d.truck_id = t.id
    """
    if session.get("role") == "admin":
        deliveries = conn.execute(query + " ORDER BY d.id DESC").fetchall()
    else:
        deliveries = conn.execute(query + " WHERE d.driver_id = ? ORDER BY d.id DESC", (uid,)).fetchall()

    delivered_count = sum(1 for d in deliveries if d["delivery_status"] == "delivered")
    total_count = len(deliveries)

    # Find the current / next active delivery
    active_delivery = next(
        (d for d in deliveries if d["delivery_status"] in ("en_route", "assigned", "authorized", "loading")),
        deliveries[0] if deliveries else None,
    )
    conn.close()

    return render_template(
        "driver/schedule.html",
        deliveries=deliveries,
        delivered_count=delivered_count,
        total_count=total_count,
        active_delivery=active_delivery,
    )


@main_bp.route("/driver/delivery/<int:delivery_id>", methods=["GET", "POST"])
@login_required("driver")
def driver_delivery_task(delivery_id):
    conn = get_db()

    delivery_check = conn.execute(
        """
        SELECT d.*, o.order_code, o.order_status, o.customer_id
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        WHERE d.id = ?
        """,
        (delivery_id,),
    ).fetchone()

    if not delivery_check:
        conn.close()
        flash("Delivery task not found.", "danger")
        return redirect(url_for("main.driver_schedule"))

    # Security check: driver can only access their assigned deliveries (unless admin)
    if session.get("role") != "admin" and delivery_check["driver_id"] != session["user_id"]:
        conn.close()
        flash("Unauthorized access to this delivery task.", "danger")
        return redirect(url_for("main.driver_schedule"))

    is_authorized = (
        delivery_check["order_status"] in ("ready_for_dispatch", "out_for_delivery", "delivered") or
        delivery_check["delivery_status"] in ("authorized", "loading", "en_route", "delivered")
    )

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_status":
            new_status = request.form.get("delivery_status", "en_route")

            # STRICT RESTRICTION: Driver CANNOT start delivery or load unless authorized by admin!
            if not is_authorized and new_status in ("loading", "en_route"):
                conn.close()
                flash("Dispatch Restricted: This delivery has NOT been authorized by the administrator. Driver cannot start delivery.", "danger")
                return redirect(url_for("main.driver_delivery_task", delivery_id=delivery_id))

            conn.execute("UPDATE deliveries SET delivery_status = ? WHERE id = ?", (new_status, delivery_id))
            if new_status == "en_route":
                conn.execute(
                    "UPDATE orders SET order_status = 'out_for_delivery' WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)",
                    (delivery_id,),
                )
                ord_cust = conn.execute("SELECT customer_id, order_code, id FROM orders WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)", (delivery_id,)).fetchone()
                if ord_cust:
                    create_notification(
                        conn,
                        ord_cust["customer_id"],
                        "Out for Delivery",
                        f"Delivery truck is now en route with your materials for order {clean_order_code(ord_cust['order_code'])}. Live GPS tracking is active.",
                        "delivery",
                        ord_cust["id"],
                    )
            conn.commit()
            flash(f"Delivery status updated to '{new_status.replace('_', ' ').title()}'.", "success")

        elif action == "confirm_delivered":
            if not is_authorized:
                conn.close()
                flash("Dispatch Restricted: Unauthorized delivery cannot be completed.", "danger")
                return redirect(url_for("main.driver_delivery_task", delivery_id=delivery_id))

            recipient = request.form.get("recipient_received_by", "").strip()
            role = request.form.get("recipient_role", "").strip()
            notes = request.form.get("delivery_notes", "").strip()
            qty_recv = request.form.get("quantity_received", "").strip()
            completion_time = request.form.get("completion_time", "").strip() or datetime.now().strftime("%I:%M %p")
            ack = 1 if request.form.get("recipient_acknowledged") else 1

            conn.execute(
                """
                UPDATE deliveries
                SET delivery_status='delivered',
                    recipient_received_by=?,
                    recipient_role=?,
                    delivery_notes=?,
                    quantity_received=?,
                    completion_time=?,
                    recipient_acknowledged=?,
                    delivered_at=datetime('now', 'localtime')
                WHERE id=?
                """,
                (recipient, role, notes, qty_recv, completion_time, ack, delivery_id),
            )
            conn.execute(
                "UPDATE orders SET order_status = 'delivered' WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)",
                (delivery_id,),
            )
            ord_cust = conn.execute("SELECT customer_id, order_code, id FROM orders WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)", (delivery_id,)).fetchone()
            if ord_cust:
                create_notification(
                    conn,
                    ord_cust["customer_id"],
                    "Materials Delivered",
                    f"Order {clean_order_code(ord_cust['order_code'])} has been successfully delivered and acknowledged on-site.",
                    "delivery",
                    ord_cust["id"],
                )

            # Special Handling for Cash on Delivery:
            # When driver completes COD delivery, record that COD payment was collected
            payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (delivery_check["order_id"],)).fetchone()
            if payment and payment["method"] == "cash":
                conn.execute(
                    """
                    UPDATE payments
                    SET payment_status = 'paid',
                        paid_at = datetime('now', 'localtime'),
                        receipt_note = COALESCE(receipt_note, '') || ' [Collected on site by driver upon delivery]'
                    WHERE id = ?
                    """,
                    (payment["id"],),
                )

            conn.commit()
            flash("Delivery confirmed and marked as Delivered!", "success")

        conn.close()
        return redirect(url_for("main.driver_delivery_task", delivery_id=delivery_id))

    delivery = conn.execute(
        """
        SELECT d.*, o.order_code, o.recipient_name, o.delivery_address, o.phone, o.phone AS recipient_phone,
               o.special_instructions, o.order_status, o.total_amount AS order_total,
               t.truck_code, t.plate_number, u.name AS driver_name,
               u_auth.name AS authorized_by_name
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN users u_auth ON d.authorized_by = u_auth.id
        WHERE d.id = ?
        """,
        (delivery_id,),
    ).fetchone()

    if not delivery:
        conn.close()
        flash("Delivery task not found.", "danger")
        return redirect(url_for("main.driver_schedule"))

    # Security check: if driver, must be assigned to this delivery
    if session.get("role") != "admin" and delivery["driver_id"] != session["user_id"]:
        conn.close()
        flash("Unauthorized access to this delivery task.", "danger")
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
