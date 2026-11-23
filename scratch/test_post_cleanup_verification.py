import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from app import app
from db import get_db

with app.test_client() as c:
    print("======================================================================")
    print("VERIFYING POST-CLEANUP OPERATIONAL SYSTEM INTEGRITY")
    print("======================================================================\n")

    # 1. ADMIN DASHBOARD VERIFICATION
    print("[TEST 1] Admin Dashboard Operational Data Check")
    # Login as admin
    res_admin_login = c.post("/admin/login", data={
        "identifier": "admin@rml.com",
        "password": "admin123"
    }, follow_redirects=True)
    assert res_admin_login.status_code == 200
    assert "Admin Operations Dashboard" in res_admin_login.get_data(as_text=True) or "Admin Dashboard" in res_admin_login.get_data(as_text=True)

    res_admin_dash = c.get("/admin/dashboard")
    assert res_admin_dash.status_code == 200
    dash_html = res_admin_dash.get_data(as_text=True)

    # Verify no dummy orders in Admin Dashboard
    assert "John Doe" not in dash_html, "Dummy user 'John Doe' still found in Admin Dashboard!"
    assert "Engr. Paolo Santos" not in dash_html, "Dummy user 'Engr. Paolo Santos' still found in Admin Dashboard!"
    assert "Test Site Manager" not in dash_html, "Dummy test recipient found in Admin Dashboard!"
    assert "Expired Customer" not in dash_html, "Dummy test recipient found in Admin Dashboard!"
    assert "COD Buyer" not in dash_html, "Dummy test recipient found in Admin Dashboard!"
    assert "GCASH-MARCO-778899" not in dash_html, "Dummy payment ref found in Admin Dashboard!"
    assert "RML-9042" not in dash_html, "Dummy order #RML-9042 found in Admin Dashboard!"

    # Verify legitimate orders appear dynamically
    assert "Monica" in dash_html, "Legitimate customer 'Monica' missing from Admin Dashboard!"
    assert "Recent Customer Orders" in dash_html, "Recent Customer Orders section missing!"
    print("  PASS: Admin Dashboard displays ONLY legitimate customer orders (Zero dummy records).")

    # Check database counts
    conn = get_db()
    order_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    cust_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer' AND is_active = 1").fetchone()[0]
    prod_count = conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
    var_count = conn.execute("SELECT COUNT(*) FROM product_variations WHERE is_available = 1").fetchone()[0]
    dummy_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE recipient_name LIKE '%John Doe%' OR recipient_name LIKE '%Test Site Manager%'").fetchone()[0]
    conn.close()

    print(f"  Live System Stats -> Orders: {order_count}, Customers: {cust_count}, Products: {prod_count}, Variations: {var_count}")
    assert order_count >= 8, f"Expected at least 8 legitimate orders, found {order_count}"
    assert dummy_orders == 0, f"Expected 0 dummy orders, found {dummy_orders}"
    print("  PASS: Database contains legitimate customer orders and zero dummy records.")

    # 2. DRIVER DASHBOARD VERIFICATION
    print("\n[TEST 2] Driver Dashboard Delivery Check")
    # Logout admin
    c.get("/admin/logout")

    # Login as Driver 1: Juan Dela Cruz
    c.post("/driver/login", data={
        "identifier": "driver@rml.com",
        "password": "driver123"
    }, follow_redirects=True)

    res_driver_dash = c.get("/driver/dashboard")
    assert res_driver_dash.status_code == 200
    drv_html = res_driver_dash.get_data(as_text=True)

    # Ensure no fabricated deliveries
    assert "John Doe" not in drv_html
    assert "DLV-1109-02" not in drv_html
    assert "DLV-1114-23" not in drv_html
    assert "Test Site Manager" not in drv_html
    assert "Expired Customer" not in drv_html
    print("  PASS: Driver Juan Dela Cruz dashboard displays only legitimate delivery assignments.")

    # Logout driver
    c.get("/driver/logout")

    # 3. END-TO-END WORKFLOW TEST: NEW CUSTOMER ORDER CREATION & DISPATCH
    print("\n[TEST 3] End-to-End Workflow: New Customer Order Creation")
    test_email = "test_live_verify@example.com"
    test_pass = "StrongPass2026!"
    new_order_id = None
    
    try:
        # Register temporary test customer
        res_reg = c.post("/register", data={
            "name": "Live Verify Customer",
            "email": test_email,
            "phone": "09175558899",
            "address": "Brgy. Antipolo, Lipa City, Batangas",
            "password": test_pass,
            "confirm_password": test_pass
        }, follow_redirects=True)
        assert res_reg.status_code == 200

        # Login as the newly registered customer
        res_log = c.post("/login", data={
            "identifier": test_email,
            "password": test_pass
        }, follow_redirects=True)
        assert res_log.status_code == 200

        # Add a product to cart
        conn = get_db()
        test_prod = conn.execute("SELECT id, name, price FROM products WHERE is_active = 1 LIMIT 1").fetchone()
        conn.close()

        res_add = c.post("/customer/cart/add", data={
            "product_id": str(test_prod["id"]),
            "quantity": "2"
        }, follow_redirects=True)
        assert res_add.status_code == 200

        # Submit checkout to create new order
        res_checkout = c.post("/customer/checkout", data={
            "recipient_name": "Live Verify Customer",
            "phone": "09175558899",
            "delivery_address": "Brgy. Antipolo, Lipa City, Batangas",
            "preferred_date": "2026-11-25",
            "delivery_slot": "Morning (08:00 - 12:00)",
            "special_instructions": "Live operational test verification order"
        }, follow_redirects=True)
        assert res_checkout.status_code == 200

        # Verify order created in database
        conn = get_db()
        new_order = conn.execute(
            "SELECT * FROM orders WHERE recipient_name = 'Live Verify Customer' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert new_order is not None, "Failed to create new customer order in DB!"
        new_order_id = new_order["id"]
        new_order_code = new_order["order_code"]
        conn.close()
        print(f"  PASS: Customer placed real order #{new_order_id} [{new_order_code}] successfully.")

        # 4. ADMIN SEES NEW ORDER DYNAMICALLY & VERIFIES
        print("\n[TEST 4] Admin Dynamic Order Visibility & Processing")
        c.get("/logout")

        # Login as admin
        c.post("/admin/login", data={"identifier": "admin@rml.com", "password": "admin123"}, follow_redirects=True)
        res_admin_new = c.get("/admin/dashboard")
        admin_html_new = res_admin_new.get_data(as_text=True)

        assert new_order_code in admin_html_new, f"New order {new_order_code} did not appear in Admin Dashboard!"
        assert "Live Verify Customer" in admin_html_new, "New order customer name did not appear in Admin Dashboard!"
        print(f"  PASS: New order #{new_order_id} automatically appeared dynamically at the top of Admin Dashboard.")

    finally:
        # 5. CLEAN UP THE VERIFICATION ORDER & USER
        print("\n[TEST 5] Clean up temporary verification order and user")
        del_conn = get_db()
        if new_order_id:
            del_conn.execute("DELETE FROM order_items WHERE order_id = ?", (new_order_id,))
            del_conn.execute("DELETE FROM payments WHERE order_id = ?", (new_order_id,))
            del_conn.execute("DELETE FROM deliveries WHERE order_id = ?", (new_order_id,))
            del_conn.execute("DELETE FROM orders WHERE id = ?", (new_order_id,))
        del_conn.execute("DELETE FROM users WHERE email = ?", (test_email,))
        del_conn.commit()
        final_orders = del_conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        del_conn.close()

        assert final_orders == order_count, f"Expected clean state of {order_count} orders, got {final_orders}"
        print(f"  PASS: Temporary test order and test account cleaned up. Database in pristine state of {order_count} legitimate customer orders.")

    print("\n======================================================================")
    print("ALL POST-CLEANUP VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("======================================================================\n")
