import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app

def run_tests():
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"
        sess["user_name"] = "Admin"
        sess["_fresh"] = True

    print("--- Test 1: Default /admin/reports ---")
    res = client.get("/admin/reports")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")

    # Check for presence of required sections
    assert "Operational Reports" in html
    assert "Sales by Category" in html
    assert "Daily Orders &amp; Approvals" in html or "Daily Orders & Approvals" in html
    assert "Total Sales (Filtered)" in html
    assert "Low-Stock Products" in html
    assert "Total Orders Analyzed" in html
    assert "Order Transactions Ledger" in html
    assert "dateRangeModal" in html
    assert "exportModal" in html

    # Inspect all rendered bar heights
    bar_heights = [int(h) for h in re.findall(r'height:\s*([0-9]+)px', html)]
    print(f"All height values found: {bar_heights}")

    # Track heights are 160px; bar heights inside are <= 120px
    # Exclude track heights (160px) and modal/avatar sizes (36px, etc.)
    bars = [h for h in bar_heights if h not in (160, 36, 10, 8)]
    print(f"Chart bar heights: {bars}")

    for h in bars:
        assert h <= 120, f"Bar height {h}px exceeds maximum allowed container height of 120px!"
        assert h >= 0, f"Negative bar height {h}px!"

    print("PASS: All bar heights are strictly bounded between 0px and 120px.")

    print("\n--- Test 2: Filtered by Date Range (November 2026) ---")
    res_nov = client.get("/admin/reports?start_date=2026-11-01&end_date=2026-11-30")
    assert res_nov.status_code == 200
    html_nov = res_nov.data.decode("utf-8")
    assert "Filter Active" in html_nov
    nov_bars = [int(h) for h in re.findall(r'height:\s*([0-9]+)px', html_nov) if int(h) not in (160, 36, 10, 8)]
    for h in nov_bars:
        assert h <= 120, f"Bar height {h}px exceeds 120px!"
    print("PASS: Date range filtering renders with valid bounded bar heights.")

    print("\n--- Test 3: Empty Date Range (No Data in Range) ---")
    res_empty = client.get("/admin/reports?start_date=2025-01-01&end_date=2025-01-02")
    assert res_empty.status_code == 200
    html_empty = res_empty.data.decode("utf-8")
    assert "No orders found in the selected date range" in html_empty
    empty_bars = [int(h) for h in re.findall(r'height:\s*([0-9]+)px', html_empty) if int(h) not in (160, 36, 10, 8)]
    for h in empty_bars:
        assert h <= 120, f"Bar height {h}px exceeds 120px!"
    print("PASS: Empty date range renders cleanly without crashing or overflowing.")

    print("\nALL ADMIN REPORTS TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
