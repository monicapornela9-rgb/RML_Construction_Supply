import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "RML"))
from app import app
from db import get_db

with app.test_client() as client:
    conn = get_db()
    customer = conn.execute("SELECT id FROM users WHERE role='customer' LIMIT 1").fetchone()
    admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    driver = conn.execute("SELECT id FROM users WHERE role='driver' LIMIT 1").fetchone()
    truck = conn.execute("SELECT id FROM trucks LIMIT 1").fetchone()

    with client.session_transaction() as sess:
        sess["user_id"] = customer["id"]
        sess["role"] = "customer"
        sess["cart"] = {"1": 1}

    # Checkout
    res = client.post("/customer/checkout", data={"recipient_name": "COD Buyer", "phone": "09171112222", "delivery_address": "Lipa"}, follow_redirects=True)
    o = conn.execute("SELECT * FROM orders WHERE recipient_name='COD Buyer' ORDER BY id DESC LIMIT 1").fetchone()
    print("Order created:", o["id"], o["order_status"])

    # Accept schedule
    client.post(f"/customer/order/{o['id']}/accept-schedule")
    o = conn.execute("SELECT * FROM orders WHERE id=?", (o["id"],)).fetchone()
    print("Order accepted:", o["order_status"])

    # Select COD
    client.post(f"/customer/payment/{o['id']}", data={"action": "confirm_payment", "method": "cash"})
    p = conn.execute("SELECT * FROM payments WHERE order_id=?", (o["id"],)).fetchone()
    print("Payment created:", p["payment_status"], p["method"])

    # Admin approves COD
    with client.session_transaction() as sess:
        sess["user_id"] = admin["id"]
        sess["role"] = "admin"
    client.post("/admin/payments", data={"action": "confirm_payment", "payment_id": p["id"]})
    o = conn.execute("SELECT * FROM orders WHERE id=?", (o["id"],)).fetchone()
    p = conn.execute("SELECT * FROM payments WHERE id=?", (p["id"],)).fetchone()
    print("Admin approved COD:", o["order_status"], p["payment_status"])
    assert o["order_status"] == "payment_verified"
    assert p["payment_status"] == "payment_due"

    # Admin authorizes delivery
    client.post(f"/admin/orders/{o['id']}/authorize-delivery")
    o = conn.execute("SELECT * FROM orders WHERE id=?", (o["id"],)).fetchone()
    d = conn.execute("SELECT * FROM deliveries WHERE order_id=?", (o["id"],)).fetchone()
    print("Admin authorized delivery:", o["order_status"], d["delivery_status"])
    assert o["order_status"] == "ready_for_dispatch"
    assert d["delivery_status"] == "authorized"

    # Driver completes delivery
    with client.session_transaction() as sess:
        sess["user_id"] = d["driver_id"]
        sess["role"] = "driver"
    client.post(f"/driver/delivery/{d['id']}", data={"action": "confirm_delivered", "recipient_received_by": "Buyer", "recipient_role": "Owner"})
    o = conn.execute("SELECT * FROM orders WHERE id=?", (o["id"],)).fetchone()
    p = conn.execute("SELECT * FROM payments WHERE id=?", (p["id"],)).fetchone()
    print("Delivery completed and COD collected:", o["order_status"], p["payment_status"])
    assert o["order_status"] == "delivered"
    assert p["payment_status"] == "paid"
    print("COD TEST PASSED 100%!")
