import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db

def run_tests():
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"
        sess["user_name"] = "RML Admin"
        sess["_fresh"] = True

    print("--- Test 1: GET /admin/orders UI Inspection ---")
    res = client.get("/admin/orders")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")

    # Verify Cancelled tab is present
    assert "Cancelled (" in html, "Cancelled tab not present in workflow navigation!"

    # Verify Admin Cancel Order Confirmation Modal structure
    assert "adminCancelModal" in html
    assert "cancelReasonCategorySelect" in html
    assert "Customer request" in html
    assert "Product unavailable" in html
    assert "Incorrect order details" in html
    assert "Delivery scheduling issue" in html
    assert "Duplicate order" in html
    assert "Business decision" in html
    assert "Other" in html
    assert "adminCancelConfirmCheck" in html
    assert "submitAdminCancelBtn" in html
    print("PASS: Admin Cancel Order modal and UI controls verified.")

    print("\n--- Test 2: Ineligibility Safeguards (Dispatched & Delivered) ---")
    conn = get_db()
    # Find a delivered order
    deliv_order = conn.execute("SELECT id, order_code, order_status FROM orders WHERE order_status = 'delivered' LIMIT 1").fetchone()
    if deliv_order:
        res_deliv_cancel = client.post(f"/admin/orders/{deliv_order['id']}/cancel", data={
            "reason_category": "Customer request"
        }, follow_redirects=True)
        html_deliv = res_deliv_cancel.data.decode("utf-8")
        assert "cannot be cancelled because" in html_deliv
        
        # Verify status did not change
        check_deliv = conn.execute("SELECT order_status FROM orders WHERE id = ?", (deliv_order["id"],)).fetchone()
        assert check_deliv["order_status"] == "delivered", "Delivered order was illegally cancelled!"
        print(f"PASS: Delivered order {deliv_order['order_code']} was blocked from cancellation.")
    conn.close()

    print("\n--- Test 3: Cancellation of Eligible Order with Inventory Restoration ---")
    # Create a fresh temporary order for testing
    conn = get_db()
    cur = conn.cursor()
    # Pick a product to test inventory restoration
    prod = conn.execute("SELECT id, name, stock_quantity FROM products WHERE is_active = 1 LIMIT 1").fetchone()
    pid = prod["id"]
    p_initial_stock = prod["stock_quantity"]

    test_order_code = "#TEST-9901"
    cur.execute("""
        INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, total_amount, order_status)
        VALUES (?, 7, 'Test Customer Monica', '09170001111', 'Lipa City Test Site', 1250.00, 'awaiting_confirmation')
    """, (test_order_code,))
    oid = cur.lastrowid

    # Insert order item with 5 units (stock is considered reserved/deducted)
    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
        VALUES (?, ?, 5, 250.00, 1250.00)
    """, (oid, pid))
    conn.commit()
    conn.close()

    # Cancel the order via admin route
    cancel_reason = "Delivery scheduling issue"
    cancel_notes = "Customer requested rescheduling but date is beyond operational window"
    res_cancel = client.post(f"/admin/orders/{oid}/cancel", data={
        "reason_category": cancel_reason,
        "cancellation_notes": cancel_notes
    }, follow_redirects=True)
    assert res_cancel.status_code == 200
    html_cancel = res_cancel.data.decode("utf-8")
    assert "has been successfully cancelled" in html_cancel

    # Verify Order in DB: Not deleted, status is 'cancelled', reason stored
    conn = get_db()
    cancelled_order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    assert cancelled_order is not None, "Order was deleted from database!"
    assert cancelled_order["order_status"] == "cancelled"
    assert cancel_reason in cancelled_order["rejection_reason"]
    assert cancel_notes in cancelled_order["rejection_reason"]
    assert cancelled_order["authorized_by"] == 1
    assert cancelled_order["authorized_at"] is not None

    # Verify Stock Restoration
    updated_prod = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()
    assert updated_prod["stock_quantity"] == p_initial_stock + 5, f"Stock was not restored! Expected {p_initial_stock + 5}, got {updated_prod['stock_quantity']}"

    # Verify inventory_logs entry
    inv_log = conn.execute("SELECT * FROM inventory_logs WHERE product_id = ? AND remarks LIKE ? ORDER BY id DESC LIMIT 1", (pid, f"%{test_order_code}%")).fetchone()
    assert inv_log is not None, "Inventory log entry not created!"
    assert inv_log["movement_type"] == "stock_in"
    assert inv_log["quantity"] == 5

    # Verify Customer Notification
    notif = conn.execute("SELECT * FROM notifications WHERE user_id = 7 AND order_id = ? ORDER BY id DESC LIMIT 1", (oid,)).fetchone()
    assert notif is not None, "Customer notification not sent!"
    assert "Order Cancelled" in notif["title"]
    assert test_order_code in notif["message"]
    assert cancel_reason in notif["message"]

    # Verify Access Log audit entry
    acc_log = conn.execute("SELECT * FROM access_logs WHERE action = 'Order Cancelled by Admin' ORDER BY id DESC LIMIT 1").fetchone()
    assert acc_log is not None, "Access log entry not recorded!"
    assert test_order_code in acc_log["details"]

    print("PASS: Order cancelled, inventory restored, notifications sent, and audit logged.")

    print("\n--- Test 4: Prevent Duplicate Stock Restoration ---")
    stock_before_repeat = updated_prod["stock_quantity"]
    # Attempt second cancellation on already cancelled order
    res_repeat = client.post(f"/admin/orders/{oid}/cancel", data={
        "reason_category": "Duplicate order"
    }, follow_redirects=True)
    html_repeat = res_repeat.data.decode("utf-8")
    assert "cannot be cancelled because" in html_repeat

    stock_after_repeat = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()["stock_quantity"]
    assert stock_after_repeat == stock_before_repeat, "Duplicate stock restoration occurred!"
    print("PASS: Duplicate cancellation blocked and stock restoration prevented.")

    print("\n--- Test 5: Payment Status Handling on Cancellation ---")
    # Test 5A: Verified Payment Flagging
    cur = conn.cursor()
    test_order_code_paid = "#TEST-9902"
    cur.execute("""
        INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, total_amount, order_status)
        VALUES (?, 7, 'Test Customer Monica', '09170001111', 'Lipa City Test Site', 3500.00, 'payment_verified')
    """, (test_order_code_paid,))
    oid_paid = cur.lastrowid
    cur.execute("""
        INSERT INTO payments (order_id, method, amount, payment_status, reference_number)
        VALUES (?, 'qr', 3500.00, 'verified', 'REF-TEST-9902')
    """, (oid_paid,))
    conn.commit()

    res_cancel_paid = client.post(f"/admin/orders/{oid_paid}/cancel", data={
        "reason_category": "Product unavailable",
        "cancellation_notes": "Out of stock item"
    }, follow_redirects=True)
    assert res_cancel_paid.status_code == 200
    assert "flagged for financial refund review" in res_cancel_paid.data.decode("utf-8")

    payment_record = conn.execute("SELECT * FROM payments WHERE order_id = ?", (oid_paid,)).fetchone()
    # Ensure payment status is NOT marked refunded automatically, but flagged in receipt_note
    assert payment_record["payment_status"] == "verified", "Payment status was illegally modified to refunded!"
    assert "FLAGGED FOR REFUND REVIEW" in payment_record["receipt_note"]
    print("PASS: Verified payment flagged for review without being marked as refunded.")

    # Cleanup temporary test orders
    conn.execute("DELETE FROM notifications WHERE order_id IN (?, ?)", (oid, oid_paid))
    conn.execute("DELETE FROM inventory_logs WHERE remarks LIKE ? OR remarks LIKE ?", (f"%{test_order_code}%", f"%{test_order_code_paid}%"))
    conn.execute("DELETE FROM order_items WHERE order_id IN (?, ?)", (oid, oid_paid))
    conn.execute("DELETE FROM payments WHERE order_id IN (?, ?)", (oid, oid_paid))
    conn.execute("DELETE FROM orders WHERE id IN (?, ?)", (oid, oid_paid))
    # Reset product stock to initial
    conn.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (p_initial_stock, pid))
    conn.commit()
    conn.close()

    print("\nALL ADMIN CANCEL ORDER TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
