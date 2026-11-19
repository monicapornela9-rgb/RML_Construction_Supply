import os
import sys

# Ensure RML is in path
rml_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "RML")
sys.path.insert(0, os.path.abspath(rml_dir))

from app import app
from db import get_db, init_db

def run_tests():
    print("=== STARTING FULL ORDER, SCHEDULING, CONFIRMATION & PAYMENT WORKFLOW TESTS ===")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    client = app.test_client()

    # Step 0: Ensure DB initialized
    init_db()

    # Helper: Login customer
    def login_customer(email="customer@rml.com", password="customer123"):
        return client.post("/login", data={"identifier": email, "password": password, "portal_role": "customer"}, follow_redirects=True)

    # Helper: Login admin
    def login_admin(email="admin@rml.com", password="admin123"):
        return client.post("/login", data={"identifier": email, "password": password, "portal_role": "admin"}, follow_redirects=True)

    # 1. Customer places an order
    print("\n--- Test 1: Customer Places Order ---")
    login_customer()
    # Add a product to cart (Product 1: Portland Cement)
    res = client.post("/customer/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
    assert res.status_code == 200, f"Failed to add product to cart: {res.status_code}"

    # Checkout submission (NO delivery date or slot)
    checkout_data = {
        "recipient_name": "Juan Test Customer",
        "phone": "09170001122",
        "delivery_address": "Test Site Block 12, Brgy. Dagatan, Lipa City",
        "special_instructions": "Gate 2 near basketball court",
    }
    res = client.post("/customer/checkout", data=checkout_data, follow_redirects=False)
    assert res.status_code == 302, f"Expected redirect after checkout, got {res.status_code}"
    redirect_url = res.headers["Location"]
    print(f"Checkout redirected to: {redirect_url}")
    assert "/customer/orders/" in redirect_url and "/confirmation" in redirect_url, \
        f"Checkout should redirect to confirmation page, but got {redirect_url}"
    assert "/customer/payment" not in redirect_url, "Checkout MUST NOT redirect to payment!"

    # Follow redirect to confirmation page
    res_conf = client.get(redirect_url)
    assert res_conf.status_code == 200, "Confirmation page failed to load"
    conf_html = res_conf.data.decode("utf-8")
    assert "Your order has been submitted successfully!" in conf_html, "Confirmation banner text missing"
    assert "Please wait while our administrator reviews your order and assigns an available delivery schedule." in conf_html, \
        "Admin review message missing from confirmation page"
    print("✓ Order placed and redirected to Confirmation page (NOT payment).")

    # Get Order ID from DB
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE recipient_name = 'Juan Test Customer' ORDER BY id DESC LIMIT 1").fetchone()
    order_id = order["id"]
    order_code = order["order_code"]
    conn.close()
    print(f"Created Order ID: {order_id}, Code: {order_code}, Status: {order['order_status']}")
    assert order["order_status"] == "pending_scheduling", f"Expected order_status 'pending_scheduling', got {order['order_status']}"

    # 2. Strict Backend Payment Guard: Customer CANNOT access payment while pending_scheduling
    print("\n--- Test 2: Payment Access Blocked Before Schedule Approval ---")
    res_pay = client.get(f"/customer/payment/{order_id}?step=1", follow_redirects=False)
    assert res_pay.status_code == 302, "Payment page should redirect when status is pending_scheduling"
    pay_redirect = res_pay.headers["Location"]
    assert "/customer/orders" in pay_redirect, f"Expected redirect to /customer/orders, got {pay_redirect}"
    
    # Follow redirect to see flash message
    res_orders = client.get(pay_redirect)
    orders_html = res_orders.data.decode("utf-8")
    assert "Payment is not available yet" in orders_html, "Expected flash warning about payment unavailability"
    print("✓ Backend successfully blocked direct payment access before schedule approval.")

    # 3. Dynamic Tracking Page: Check 7 Stages Stepper while Pending
    print("\n--- Test 3: Tracking Page Stepper (Pending Scheduling) ---")
    res_track = client.get(f"/customer/orders/{order_id}/tracking")
    assert res_track.status_code == 200
    track_html = res_track.data.decode("utf-8")
    assert "1. Order Submitted" in track_html
    assert "2. Admin Scheduling" in track_html
    assert "3. Customer Review" in track_html
    assert "4. Schedule Confirmed" in track_html
    assert "5. Payment" in track_html
    assert "6. Out for Delivery" in track_html
    assert "7. Delivered" in track_html
    assert "Payment selection unlocks after delivery schedule confirmation" in track_html
    assert "Payment Method: QR Pending" not in track_html
    print("✓ Tracking page properly displays 7-stage workflow and suppresses premature payment info.")

    # 4. Admin Reviews and Assigns Delivery Schedule
    print("\n--- Test 4: Admin Reviews & Assigns Schedule ---")
    login_admin()
    res_admin_orders = client.get("/admin/orders?tab=pending")
    assert res_admin_orders.status_code == 200
    admin_html = res_admin_orders.data.decode("utf-8")
    assert "Pending Scheduling" in admin_html

    # Assign truck 1 and driver (Juan Dela Cruz, ID 2) on a test date
    import random
    test_date = f"2026-12-{random.randint(10, 28)}"
    sched_data = {
        "assigned_date": test_date,
        "assigned_time_slot": "Morning (08:00 - 12:00)",
        "truck_id": 1,
        "driver_id": 2,
        "approval_notes": "Site foreman available from 8 AM",
    }
    res_assign = client.post(f"/admin/orders/{order_id}/assign-schedule", data=sched_data, follow_redirects=True)
    assert res_assign.status_code == 200
    
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    assert order["order_status"] == "awaiting_confirmation", f"Expected 'awaiting_confirmation', got {order['order_status']}"
    assert order["schedule_status"] == "proposed", f"Expected schedule_status 'proposed', got {order['schedule_status']}"
    print("✓ Admin assigned schedule and order moved to 'awaiting_confirmation'.")

    # Conflict check: Try to assign ANOTHER order to the same truck/driver on the same date & time slot
    print("\n--- Test 4b: Conflict Check on Truck/Driver Overlap ---")
    # Customer creates second order
    login_customer()
    client.post("/customer/cart/add", data={"product_id": 2, "quantity": 1}, follow_redirects=True)
    client.post("/customer/checkout", data=checkout_data, follow_redirects=True)
    conn = get_db()
    order2 = conn.execute("SELECT id FROM orders WHERE recipient_name = 'Juan Test Customer' ORDER BY id DESC LIMIT 1").fetchone()
    order2_id = order2["id"]
    conn.close()

    login_admin()
    # Try overlapping assignment
    res_conflict = client.post(f"/admin/orders/{order2_id}/assign-schedule", data=sched_data, follow_redirects=True)
    conflict_html = res_conflict.data.decode("utf-8")
    assert "Scheduling Conflict" in conflict_html, "Expected scheduling conflict warning"
    print("✓ Conflict prevention successfully blocked overlapping truck and driver booking.")

    # 5. Customer Still CANNOT access payment while awaiting_confirmation
    print("\n--- Test 5: Payment Blocked During awaiting_confirmation ---")
    login_customer()
    res_pay2 = client.get(f"/customer/payment/{order_id}?step=1", follow_redirects=False)
    assert res_pay2.status_code == 302
    assert "/customer/orders" in res_pay2.headers["Location"]
    print("✓ Payment route blocked when order is awaiting_confirmation.")

    # Customer checks My Orders & Tracking page
    res_orders = client.get("/customer/orders")
    orders_html = res_orders.data.decode("utf-8")
    assert "ACCEPT SCHEDULE" in orders_html
    assert "CANCEL ORDER" in orders_html
    assert "Our administrator has proposed a delivery schedule for your order" in orders_html

    res_track = client.get(f"/customer/orders/{order_id}/tracking")
    track_html = res_track.data.decode("utf-8")
    assert "ACCEPT SCHEDULE" in track_html
    assert "CANCEL ORDER" in track_html
    print("✓ Customer sees proposed schedule notice with Accept and Cancel actions.")

    # 6. Customer Accepts Proposed Delivery Schedule
    print("\n--- Test 6: Customer Accepts Schedule ---")
    res_accept = client.post(f"/customer/order/{order_id}/accept-schedule", follow_redirects=False)
    assert res_accept.status_code == 302, "Accept schedule should redirect"
    accept_redirect = res_accept.headers["Location"]
    print(f"Accept schedule redirected to: {accept_redirect}")
    assert f"/customer/payment/{order_id}?step=1" in accept_redirect, \
        f"Accept schedule MUST redirect directly to payment, got {accept_redirect}"

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    assert order["order_status"] == "schedule_confirmed", f"Expected 'schedule_confirmed', got {order['order_status']}"
    assert order["schedule_status"] == "accepted", f"Expected 'accepted', got {order['schedule_status']}"
    print("✓ Customer approved schedule. Order status is 'schedule_confirmed' and redirected to Payment.")

    # 7. Payment is NOW UNLOCKED and Processable
    print("\n--- Test 7: Payment Processing (After Schedule Approval) ---")
    res_pay_unlocked = client.get(f"/customer/payment/{order_id}?step=1")
    assert res_pay_unlocked.status_code == 200, "Payment page should be accessible now"
    pay_html = res_pay_unlocked.data.decode("utf-8")
    assert "Cash Payment" in pay_html
    assert "Online Payment via QR Code" in pay_html

    # Complete Cash on Delivery confirmation
    res_pay_confirm = client.post(
        f"/customer/payment/{order_id}",
        data={
            "action": "confirm_payment",
            "method": "cash",
            "payer_name": "Juan Test Customer",
        },
        follow_redirects=True,
    )
    assert res_pay_confirm.status_code == 200

    conn = get_db()
    payment = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchone()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    assert payment is not None, "Payment was not recorded"
    assert payment["method"] == "cash"
    assert order["order_status"] in ("schedule_confirmed", "scheduled")
    print(f"✓ Payment successfully recorded (Method: {payment['method']}, Status: {payment['payment_status']}).")

    # 8. Tracking Page Reflects Payment Complete
    print("\n--- Test 8: Tracking Page After Payment ---")
    res_track = client.get(f"/customer/orders/{order_id}/tracking")
    track_html = res_track.data.decode("utf-8")
    assert "1. Order Submitted" in track_html
    assert "5. Payment" in track_html
    assert "Cash on Delivery" in track_html or "CASH" in track_html
    print("✓ Tracking page reflects payment completed.")

    # 9. Cancel Order & Resource Release
    print("\n--- Test 9: Customer Cancellation Releases Resources ---")
    # Cancel order 2
    res_cancel = client.post(
        f"/customer/order/{order2_id}/cancel",
        data={"cancellation_reason": "Proposed schedule not convenient"},
        follow_redirects=True,
    )
    assert res_cancel.status_code == 200
    conn = get_db()
    order2_db = conn.execute("SELECT * FROM orders WHERE id = ?", (order2_id,)).fetchone()
    deliv2_db = conn.execute("SELECT * FROM deliveries WHERE order_id = ?", (order2_id,)).fetchone()
    conn.close()
    assert order2_db["order_status"] == "cancelled"
    assert deliv2_db is None, "Delivery record should be deleted on cancellation"
    print("✓ Order cancellation successfully updated status to cancelled and released resources.")

    print("\n=== ALL 10 TEST PHASES PASSED WITH 100% SUCCESS! ===")

if __name__ == "__main__":
    run_tests()
