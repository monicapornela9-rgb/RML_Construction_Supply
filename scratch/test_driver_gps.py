import os
import sys

rml_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "RML")
sys.path.insert(0, os.path.abspath(rml_dir))

from app import app
from db import get_db

def test_driver_and_gps():
    print("=== TESTING DRIVER DISPATCH, GPS SIMULATION & DELIVERY COMPLETION ===")
    app.config["TESTING"] = True
    client = app.test_client()

    # Login driver (Juan Dela Cruz, email: driver@rml.com, password: driver123)
    res_login = client.post("/login", data={"identifier": "driver@rml.com", "password": "driver123", "portal_role": "driver"}, follow_redirects=True)
    assert res_login.status_code == 200, "Driver login failed"

    # Find the active delivery created in previous test (or any assigned delivery)
    conn = get_db()
    deliv = conn.execute("SELECT d.*, o.id AS order_id FROM deliveries d JOIN orders o ON d.order_id = o.id WHERE d.driver_id = 2 ORDER BY d.id DESC LIMIT 1").fetchone()
    conn.close()
    assert deliv is not None, "No active delivery found for driver"
    deliv_id = deliv["id"]
    order_id = deliv["order_id"]
    print(f"Testing Delivery ID: {deliv_id}, Order ID: {order_id}")

    # 1. Driver sets status to 'en_route' (Out for delivery)
    res_enroute = client.post(
        f"/driver/delivery/{deliv_id}",
        data={"action": "update_status", "delivery_status": "en_route"},
        follow_redirects=True,
    )
    assert res_enroute.status_code == 200

    conn = get_db()
    order = conn.execute("SELECT order_status FROM orders WHERE id = ?", (order_id,)).fetchone()
    deliv_row = conn.execute("SELECT delivery_status FROM deliveries WHERE id = ?", (deliv_id,)).fetchone()
    conn.close()
    assert deliv_row["delivery_status"] == "en_route"
    assert order["order_status"] == "out_for_delivery", f"Expected 'out_for_delivery', got {order['order_status']}"
    print("✓ Driver set delivery to en_route -> Order status is 'out_for_delivery'.")

    # 2. GPS simulation
    res_gps = client.post(f"/api/gps/simulate/{deliv_id}")
    assert res_gps.status_code == 200
    gps_data = res_gps.get_json()
    assert gps_data["ok"] is True
    print(f"✓ GPS coordinate simulated: lat={gps_data['lat']}, lng={gps_data['lng']}.")

    # 3. Customer checks live tracking map endpoint
    res_loc = client.get(f"/api/gps/location/{order_id}")
    assert res_loc.status_code == 200
    loc_data = res_loc.get_json()
    assert loc_data["ok"] is True
    assert loc_data["lat"] == gps_data["lat"]
    print("✓ Customer GPS location endpoint returns updated live coordinates.")

    # 4. Customer checks tracking page -> Stage 6 ('Out for Delivery') is active
    client.post("/login", data={"identifier": "customer@rml.com", "password": "customer123", "portal_role": "customer"}, follow_redirects=True)
    res_track = client.get(f"/customer/orders/{order_id}/tracking")
    track_html = res_track.data.decode("utf-8")
    assert "Out for Delivery" in track_html
    assert "En Route (GPS)" in track_html
    print("✓ Customer tracking page displays Stage 6 active ('Out for Delivery - En Route (GPS)').")

    # 5. Driver confirms delivery complete
    client.post("/login", data={"identifier": "driver@rml.com", "password": "driver123", "portal_role": "driver"}, follow_redirects=True)
    res_deliv = client.post(
        f"/driver/delivery/{deliv_id}",
        data={
            "action": "confirm_delivered",
            "recipient_received_by": "Engr. Marco",
            "recipient_role": "Site Engineer",
            "quantity_received": "All items complete and intact",
            "delivery_notes": "Unloaded inside warehouse bay 3",
            "recipient_acknowledged": "1",
        },
        follow_redirects=True,
    )
    assert res_deliv.status_code == 200

    conn = get_db()
    order = conn.execute("SELECT order_status FROM orders WHERE id = ?", (order_id,)).fetchone()
    deliv_row = conn.execute("SELECT delivery_status, recipient_received_by FROM deliveries WHERE id = ?", (deliv_id,)).fetchone()
    conn.close()
    assert deliv_row["delivery_status"] == "delivered"
    assert order["order_status"] == "delivered", f"Expected 'delivered', got {order['order_status']}"
    print(f"✓ Delivery confirmed by {deliv_row['recipient_received_by']} -> Order status is 'delivered'.")

    # 6. Customer tracking page shows Stage 7 ('Delivered') completed
    client.post("/login", data={"identifier": "customer@rml.com", "password": "customer123", "portal_role": "customer"}, follow_redirects=True)
    res_track_done = client.get(f"/customer/orders/{order_id}/tracking")
    done_html = res_track_done.data.decode("utf-8")
    assert "Order Delivered Successfully" in done_html
    assert "7. Delivered" in done_html
    print("✓ Customer tracking page displays Stage 7 completed ('Delivered').")

    print("\n=== DRIVER & DISPATCH LIFECYCLE TESTS PASSED 100%! ===")

if __name__ == "__main__":
    test_driver_and_gps()
