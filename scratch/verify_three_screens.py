import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from app import app
from db import get_db

with app.test_client() as c:
    print("--- 1. SCREEN 1: /admin/orders?tab=ready ---")
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['user_name'] = 'Admin User'
    res = c.get('/admin/orders?tab=ready')
    print("Status:", res.status_code)
    html = res.get_data(as_text=True)
    print("Contains 'Dispatched / In Transit':", 'Dispatched / In Transit' in html)
    print("Contains 'Modals Placed Safely OUTSIDE':", 'Modals Placed Safely OUTSIDE' in html)
    print("Contains 'Santos Residence':", 'Santos Residence' in html)

    print("\n--- 2. SCREEN 2: /customer/checkout ---")
    with c.session_transaction() as sess:
        sess['user_id'] = 4
        sess['role'] = 'customer'
        sess['user_name'] = 'Monica Pornela'
    res = c.get('/customer/checkout')
    print("Status:", res.status_code)
    chtml = res.get_data(as_text=True)
    print("Contains 'Preferred Delivery Date' (Should be False):", 'Preferred Delivery Date' in chtml)
    print("Contains 'Delivery Slot' (Should be False):", 'Delivery Slot' in chtml)
    print("Contains 'Recipient / Company Name' (Should be True):", 'Recipient / Company Name' in chtml)
    print("Contains 'Automatic Delivery Schedule Proposal' (Should be True):", 'Automatic Delivery Schedule Proposal' in chtml)

    print("\n--- 3. SCREEN 3: /customer/orders/<id>/tracking ---")
    conn = get_db()
    o = conn.execute("SELECT id FROM orders WHERE customer_id = 4 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if o:
        order_id = o['id']
        res = c.get(f'/customer/orders/{order_id}/tracking')
        print(f"Tracking order #{order_id} Status:", res.status_code)
        thtml = res.get_data(as_text=True)
        print("Contains Admin Links (Drivers & Deliveries, Inventory) (Should be False):",
              ('Drivers &amp; Deliveries' in thtml or 'Inventory' in thtml))
        print("Contains Customer Links (My Orders, Product Catalog) (Should be True):",
              ('My Orders' in thtml and 'Product Catalog' in thtml))
        print("Does tracking require schedule acceptance before payment:",
              'Accept Schedule & Proceed to Payment' in thtml or 'Payment Verification' in thtml or 'Pending Admin' in thtml)
    else:
        print("No order found for user 4")
