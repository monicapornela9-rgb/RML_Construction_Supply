import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db

def run_tests():
    client = app.test_client()

    conn = get_db()
    # Find an active or test delivery assigned to driver id=2 (Juan Dela Cruz)
    # Check deliveries for driver 2
    deliv = conn.execute("""
        SELECT d.*, o.order_code
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        WHERE d.driver_id = 2
        LIMIT 1
    """).fetchone()
    assert deliv is not None, "No delivery found for driver 2"
    deliv_id = deliv["id"]
    orig_deliv_status = deliv["delivery_status"]
    orig_rec_by = deliv["recipient_received_by"]
    orig_notes = deliv["delivery_notes"]
    orig_comp_time = deliv["completion_time"]
    conn.close()

    print(f"Testing with Delivery ID: {deliv_id} (Initial status: {orig_deliv_status})")

    # Sign in as Driver (id=2)
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "driver"
        sess["user_name"] = "Juan Dela Cruz"
        sess["_fresh"] = True

    # Temporarily ensure delivery is authorized & en_route so form displays
    conn = get_db()
    conn.execute("UPDATE deliveries SET delivery_status = 'en_route' WHERE id = ?", (deliv_id,))
    conn.execute("UPDATE orders SET order_status = 'out_for_delivery' WHERE id = (SELECT order_id FROM deliveries WHERE id = ?)", (deliv_id,))
    conn.commit()
    conn.close()

    print("\n--- Test 1: GET /driver/delivery/<id> and verify form fields ---")
    res = client.get(f"/driver/delivery/{deliv_id}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")

    assert "Confirm delivery at site" in html

    # Verify Role / Relationship is REMOVED
    assert "Role / relationship" not in html, "Role / relationship label still found in HTML!"
    assert 'name="recipient_role"' not in html, "recipient_role input still found in HTML!"
    print("PASS: 'Role / Relationship' field is completely removed.")

    # Verify all required fields are present
    assert 'name="recipient_received_by"' in html, "Recipient full name field missing!"
    assert 'name="delivered_date"' in html, "Delivery date field missing!"
    assert 'name="completion_time"' in html, "Completion time field missing!"
    assert 'name="quantity_received"' in html, "Quantity received field missing!"
    assert 'name="delivery_notes"' in html, "Condition / Delivery notes field missing!"
    assert 'name="recipient_acknowledged"' in html, "Recipient acknowledgement checkbox missing!"
    assert 'id="confirmCheck"' in html, "Driver confirmation checkbox missing!"
    print("PASS: All required fields and checkboxes are present and aligned.")

    print("\n--- Test 2: POST confirm_delivered submission without role ---")
    res_post = client.post(f"/driver/delivery/{deliv_id}", data={
        "action": "confirm_delivered",
        "recipient_received_by": "Engr. Roberto Silva",
        "delivered_date": "2026-11-23",
        "completion_time": "10:15 AM",
        "quantity_received": "50 bags Republic Portland Cement",
        "delivery_notes": "Unloaded completely under covered warehouse shelter.",
        "recipient_acknowledged": "1"
    }, follow_redirects=True)
    assert res_post.status_code == 200
    html_after = res_post.data.decode("utf-8")
    assert "Delivered &amp; Confirmed!" in html_after or "Delivered & Confirmed!" in html_after
    assert "Engr. Roberto Silva" in html_after
    assert "10:15 AM" in html_after

    # Verify DB update
    conn = get_db()
    saved = conn.execute("SELECT * FROM deliveries WHERE id = ?", (deliv_id,)).fetchone()
    assert saved["delivery_status"] == "delivered"
    assert saved["recipient_received_by"] == "Engr. Roberto Silva"
    assert saved["completion_time"] == "10:15 AM"
    assert saved["quantity_received"] == "50 bags Republic Portland Cement"
    assert saved["delivery_notes"] == "Unloaded completely under covered warehouse shelter."
    assert saved["recipient_acknowledged"] == 1

    # Verify order status
    ord_row = conn.execute("SELECT order_status FROM orders WHERE id = ?", (saved["order_id"],)).fetchone()
    assert ord_row["order_status"] == "delivered"

    # Restore original delivery state to preserve historical DB testing integrity
    conn.execute("""
        UPDATE deliveries
        SET delivery_status = ?,
            recipient_received_by = ?,
            completion_time = ?,
            delivery_notes = ?
        WHERE id = ?
    """, (orig_deliv_status, orig_rec_by, orig_comp_time, orig_notes, deliv_id))
    conn.execute("UPDATE orders SET order_status = 'delivered' WHERE id = ?", (saved["order_id"],))
    conn.commit()
    conn.close()

    print("PASS: Delivery confirmation submitted, validated, and saved to database successfully.")
    print("\nALL DRIVER DELIVERY CONFIRMATION TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
