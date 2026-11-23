import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app

client = app.test_client()

# Admin check
with client.session_transaction() as sess:
    sess["user_id"] = 1
    sess["role"] = "admin"
    sess["user_name"] = "Admin"
    sess["_fresh"] = True

admin_routes = [
    "/admin/dashboard",
    "/admin/orders",
    "/admin/inventory",
    "/admin/deliveries",
    "/admin/delivery-availability",
    "/admin/customers",
    "/admin/payments",
    "/admin/reports",
    "/admin/access",
]
for r in admin_routes:
    resp = client.get(r)
    assert resp.status_code == 200, f"Failed: {r} -> {resp.status_code}"
    print(f"PASS ADMIN: {r} -> 200 OK")

# Driver check
with client.session_transaction() as sess:
    sess["user_id"] = 2
    sess["role"] = "driver"
    sess["user_name"] = "Driver"
    sess["_fresh"] = True

driver_routes = [
    "/driver/dashboard",
]
for r in driver_routes:
    resp = client.get(r)
    assert resp.status_code == 200, f"Failed: {r} -> {resp.status_code}"
    print(f"PASS DRIVER: {r} -> 200 OK")

print("ALL ADMIN AND DRIVER ROUTES OK!")
