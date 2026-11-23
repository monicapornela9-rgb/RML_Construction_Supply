from flask import Flask, session
from db import init_db, get_db
from routes import main_bp

app = Flask(__name__)
app.secret_key = "rml-construction-supply-secret-key"

# Initialize SQLite3 DB and register routes
init_db()
app.register_blueprint(main_bp)


@app.context_processor
def inject_globals():
    """Make current user, cart count, and unread notifications count available to all HTML templates."""
    cart_count = 0
    unread_notifications_count = 0
    user = None
    if "user_id" in session:
        conn = get_db()
        user = conn.execute(
            "SELECT id, staff_id, name, email, phone, address, role, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if user and user["role"] == "customer":
            try:
                c_row = conn.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE user_id = ?",
                    (session["user_id"],),
                ).fetchone()
                cart_count = int(c_row[0]) if c_row and c_row[0] else 0
            except Exception:
                cart_count = 0
            try:
                unread_row = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                    (session["user_id"],),
                ).fetchone()
                unread_notifications_count = unread_row[0] if unread_row else 0
            except Exception:
                unread_notifications_count = 0
        conn.close()
    return dict(
        current_user=user,
        cart_count=cart_count,
        unread_notifications_count=unread_notifications_count,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
