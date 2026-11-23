import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app

client = app.test_client()

with client.session_transaction() as sess:
    sess["user_id"] = 38
    sess["role"] = "customer"
    sess["user_name"] = "Redena"
    sess["_fresh"] = True

filters = ["", "unread", "order", "schedule", "payment", "delivery"]

for f in filters:
    url = f"/customer/notifications?type={f}" if f else "/customer/notifications"
    resp = client.get(url)
    assert resp.status_code == 200, f"Filter {f} failed with status {resp.status_code}"
    html = resp.data.decode("utf-8")
    assert "Stay updated on your orders and deliveries." in html
    assert "Need help with your delivery?" in html
    assert "Contact RML Support" in html
    print(f"PASS Filter '{f or 'all'}': HTTP 200 OK")

print("ALL FILTERS TESTED SUCCESSFULLY!")
