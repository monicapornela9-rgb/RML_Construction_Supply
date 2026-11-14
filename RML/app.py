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
    """Make current user and cart count available to all HTML templates."""
    cart = session.get("cart", {})
    cart_count = sum(cart.values())
    user = None
    if "user_id" in session:
        conn = get_db()
        user = conn.execute(
            "SELECT id, staff_id, name, email, phone, address, role FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        conn.close()
    return dict(current_user=user, cart_count=cart_count)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
