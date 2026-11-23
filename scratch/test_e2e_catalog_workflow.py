import os
import sys
import sqlite3

# Add RML directory to sys.path
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RML")
sys.path.insert(0, PROJECT_DIR)

from app import app
from db import get_db

def run_tests():
    print("=== STARTING FULL END-TO-END CATALOG & VARIATION WORKFLOW TEST ===")
    client = app.test_client()

    # 1. Login as Customer
    print("\n--- 1. Testing Customer Login ---")
    res = client.post("/login", data={
        "identifier": "customer@rml.com",
        "password": "customer123"
    }, follow_redirects=True)
    assert res.status_code == 200, f"Customer login failed: {res.status_code}"
    html = res.get_data(as_text=True)
    assert "Construction Materials" in html or "Product Catalog" in html, "Customer login redirect failed"
    print(" Customer login successful!")

    # 2. Inspect Catalog Page
    print("\n--- 2. Inspecting Catalog & Product Variations ---")
    res = client.get("/customer/catalog")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "variation-select" in html, "No variation dropdowns found in catalog HTML!"
    print(" Verified variation selector dropdowns on catalog page.")

    # 3. Find Bakal (Deformed Steel Rebar) and Opple LED Bulb variations in DB
    db_path = os.path.join(PROJECT_DIR, "rml_database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    bakal = cur.execute("SELECT * FROM products WHERE name LIKE '%Bakal%' AND is_active = 1").fetchone()
    assert bakal is not None, "Bakal product not found in DB!"
    bakal_12mm = cur.execute("SELECT * FROM product_variations WHERE product_id = ? AND variation_name = '12mm'", (bakal["id"],)).fetchone()
    assert bakal_12mm is not None, "Bakal 12mm variation not found in DB!"
    assert float(bakal_12mm["price"]) == 245.0, f"Expected 245.00 for Bakal 12mm, got {bakal_12mm['price']}"

    opple = cur.execute("SELECT * FROM products WHERE name LIKE '%Opple LED%' AND is_active = 1").fetchone()
    assert opple is not None, "Opple LED product not found in DB!"
    opple_15w = cur.execute("SELECT * FROM product_variations WHERE product_id = ? AND variation_name = '15w'", (opple["id"],)).fetchone()
    assert opple_15w is not None, "Opple 15w variation not found in DB!"
    assert float(opple_15w["price"]) == 170.0, f"Expected 170.00 for Opple 15w, got {opple_15w['price']}"

    initial_bakal_var_stock = bakal_12mm["stock_quantity"]
    initial_bakal_prod_stock = bakal["stock_quantity"]

    print(f"Bakal 12mm (ID: {bakal_12mm['id']}, Price: {bakal_12mm['price']}, Stock: {initial_bakal_var_stock})")
    print(f"Opple 15w (ID: {opple_15w['id']}, Price: {opple_15w['price']}, Stock: {opple_15w['stock_quantity']})")

    # 4. Add items with variations to Cart
    print("\n--- 3. Testing Adding Variations to Cart ---")
    # Add 2 pcs of Bakal 12mm
    res = client.post("/customer/cart/add", data={
        "product_id": bakal["id"],
        "variation_id": bakal_12mm["id"],
        "quantity": 2
    }, follow_redirects=True)
    assert res.status_code == 200
    print(" Added 2 pcs Bakal 12mm to cart.")

    # Add 3 pcs of Opple 15w
    res = client.post("/customer/cart/add", data={
        "product_id": opple["id"],
        "variation_id": opple_15w["id"],
        "quantity": 3
    }, follow_redirects=True)
    assert res.status_code == 200
    print(" Added 3 pcs Opple 15w to cart.")

    # 5. Check Checkout Page & Calculations
    print("\n--- 4. Checking Checkout Calculation & Variation Display ---")
    res = client.get("/customer/checkout")
    assert res.status_code == 200
    page_text = res.get_data(as_text=True)

    # Verify both variations are shown
    assert "12mm" in page_text, "Variation '12mm' not displayed in checkout summary!"
    assert "15w" in page_text, "Variation '15w' not displayed in checkout summary!"

    # Expected subtotal: 2 * 245 + 3 * 170 = 490 + 510 = 1000.00
    # Delivery fee: 1500.00
    # VAT (12%): 120.00
    # Total: 2620.00
    assert "1,000.00" in page_text, "Subtotal 1,000.00 not found in checkout summary!"
    assert "2,620.00" in page_text, "Total 2,620.00 not found in checkout summary!"
    print(" Checkout calculations verified: Subtotal = P1,000.00, Total = P2,620.00!")

    # 6. Submit Checkout Order
    print("\n--- 5. Submitting Order ---")
    res = client.post("/customer/checkout", data={
        "recipient_name": "Engr. Marco Builders",
        "phone": "09175559876",
        "delivery_address": "Lot 8 Block 2, Mount Malarayat, Lipa City",
        "special_instructions": "Gate code #4490, deliver near foundation pit"
    }, follow_redirects=True)
    assert res.status_code == 200
    conf_text = res.get_data(as_text=True)
    assert "Order Reference:" in conf_text or "Proposed Delivery Schedule Available" in conf_text or "order has been submitted" in conf_text
    print(" Order submitted successfully!")

    # Find newly created order in DB
    new_order = cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
    order_id = new_order["id"]
    print(f"Created Order #{new_order['order_code']} (ID: {order_id})")

    # Check order_items table for variation preservation
    order_items = cur.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    assert len(order_items) == 2, f"Expected 2 order items, got {len(order_items)}"

    item_map = {item["product_id"]: item for item in order_items}
    bakal_item = item_map[bakal["id"]]
    assert bakal_item["variation_id"] == bakal_12mm["id"], "Variation ID not recorded on order item!"
    assert bakal_item["variation_name"] == "12mm", "Variation name not recorded on order item!"
    assert float(bakal_item["unit_price"]) == 245.0, f"Expected 245.00 unit price, got {bakal_item['unit_price']}"
    assert float(bakal_item["subtotal"]) == 490.0, f"Expected 490.00 subtotal, got {bakal_item['subtotal']}"

    opple_item = item_map[opple["id"]]
    assert opple_item["variation_id"] == opple_15w["id"], "Variation ID not recorded on order item!"
    assert opple_item["variation_name"] == "15w", "Variation name not recorded on order item!"
    assert float(opple_item["unit_price"]) == 170.0, f"Expected 170.00 unit price, got {opple_item['unit_price']}"
    assert float(opple_item["subtotal"]) == 510.0, f"Expected 510.00 subtotal, got {opple_item['subtotal']}"
    print(" Database order items verified: exact variation_id, variation_name, and unit prices preserved!")

    # Check inventory deduction
    updated_bakal_var = cur.execute("SELECT * FROM product_variations WHERE id = ?", (bakal_12mm["id"],)).fetchone()
    assert updated_bakal_var["stock_quantity"] == initial_bakal_var_stock - 2, "Variation stock not deducted properly!"
    print(f" Stock deduction verified: Variation stock {initial_bakal_var_stock} -> {updated_bakal_var['stock_quantity']}")

    # 7. Check Confirmation, Tracking, and Invoice Views
    print("\n--- 6. Verifying Variation Visibility Across Customer Views ---")
    # Confirmation view
    res = client.get(f"/customer/orders/{order_id}/confirmation")
    assert res.status_code == 200
    t = res.get_data(as_text=True)
    assert "12mm" in t and "15w" in t, "Variations not shown on order confirmation page!"
    print(" Order Confirmation page displays variation badges!")

    # Tracking view
    res = client.get(f"/customer/orders/{order_id}/tracking")
    assert res.status_code == 200
    t = res.get_data(as_text=True)
    assert "12mm" in t and "15w" in t, "Variations not shown on tracking page!"
    print(" Order Tracking page displays variations in summary!")

    # Invoice view
    res = client.get(f"/order/{order_id}/invoice")
    assert res.status_code == 200
    t = res.get_data(as_text=True)
    assert "12mm" in t and "15w" in t, "Variations not shown on invoice!"
    print(" Official Invoice displays variation names!")

    # 8. Test Admin Inventory Management
    print("\n--- 7. Testing Admin Inventory & Variation Management ---")
    admin_client = app.test_client()
    res = admin_client.post("/admin/login", data={
        "identifier": "admin@rml.com",
        "password": "admin123"
    }, follow_redirects=True)
    assert res.status_code == 200
    print(" Admin logged in successfully!")

    # View Admin Inventory
    res = admin_client.get("/admin/inventory")
    assert res.status_code == 200
    admin_html = res.get_data(as_text=True)
    assert "Manage Variations" in admin_html or "variations" in admin_html
    print(" Admin inventory displays 'Manage Variations' action!")

    # Add a variation through admin form
    test_prod = cur.execute("SELECT * FROM products WHERE name LIKE '%Denatured Alcohol%'").fetchone()
    assert test_prod is not None
    print(f"Adding test variation to {test_prod['name']} (ID: {test_prod['id']})...")

    res = admin_client.post("/admin/inventory", data={
        "action": "add_variation",
        "product_id": test_prod["id"],
        "variation_name": "Test Size 500ml",
        "price": 85.50,
        "unit": "bottle",
        "stock_quantity": 40
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "added successfully" in res.get_data(as_text=True)

    # Verify added variation in DB
    added_var = cur.execute("SELECT * FROM product_variations WHERE product_id = ? AND variation_name = 'Test Size 500ml'", (test_prod["id"],)).fetchone()
    assert added_var is not None, "Newly added variation not found in DB!"
    assert float(added_var["price"]) == 85.50
    print(f" Admin add_variation verified: ID {added_var['id']}, Price: {added_var['price']}")

    # Update the variation price
    print("Updating test variation price...")
    res = admin_client.post("/admin/inventory", data={
        "action": "update_variation",
        "variation_id": added_var["id"],
        "variation_name": "Test Size 500ml Updated",
        "price": 89.00,
        "unit": "bottle",
        "stock_quantity": 45,
        "is_available": 1
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "updated successfully" in res.get_data(as_text=True)

    updated_var = cur.execute("SELECT * FROM product_variations WHERE id = ?", (added_var["id"],)).fetchone()
    assert float(updated_var["price"]) == 89.00
    assert updated_var["variation_name"] == "Test Size 500ml Updated"
    print(f" Admin update_variation verified: New Price: {updated_var['price']}, New Name: {updated_var['variation_name']}")

    # Deactivate the variation
    print("Deactivating test variation...")
    res = admin_client.post("/admin/inventory", data={
        "action": "delete_variation",
        "variation_id": added_var["id"]
    }, follow_redirects=True)
    assert res.status_code == 200

    deactivated_var = cur.execute("SELECT * FROM product_variations WHERE id = ?", (added_var["id"],)).fetchone()
    assert deactivated_var["is_available"] == 0, "Variation was not deactivated!"
    print(" Admin delete_variation (deactivation) verified!")

    conn.close()
    print("\n========================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! 100% VERIFIED!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
