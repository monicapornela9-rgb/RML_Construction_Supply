import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db

class TestAdminDashboardRedesign(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def set_admin_session(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["user_name"] = "Admin"
            sess["_fresh"] = True

    def set_customer_session(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7
            sess["role"] = "customer"
            sess["user_name"] = "Monica"
            sess["_fresh"] = True

    def test_admin_dashboard_structure_and_kpis(self):
        """Verify the 4 primary KPIs, table, and simplified fleet overview on Admin Dashboard."""
        self.set_admin_session()
        resp = self.client.get("/admin/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # 1. Header
        self.assertIn("Executive Operations Dashboard", html)
        self.assertIn("Operations Console", html)

        # 2. Four Main KPI Cards
        self.assertIn("Total Orders", html)
        self.assertIn("Pending Orders", html)
        self.assertIn("Active Deliveries", html)
        self.assertIn("Total Revenue", html)

        # 3. Recent Customer Orders table
        self.assertIn("Recent Customer Orders", html)
        self.assertIn("View All Orders", html)
        self.assertIn("/admin/orders", html)
        self.assertIn("Review &rarr;", html)

        # 4. Simplified Fleet Overview
        self.assertIn("Fleet Overview", html)
        self.assertIn("Live Map", html)
        self.assertIn("Open Fleet &amp; GPS Tracking", html)
        self.assertIn("/admin/deliveries", html)

        # 5. Secondary Operational Snapshot
        self.assertIn("Operational Snapshot:", html)
        self.assertIn("Verified Customers", html)
        self.assertIn("Low-Stock Items", html)
        self.assertIn("Units Restocked", html)
        self.assertIn("Pending QR Verifications", html)

        # 6. Verify redundant clutter from previous design is removed
        self.assertNotIn("Manage Delivery Availability Rules", html)
        self.assertNotIn("Payment Verification Queue (", html)
        self.assertNotIn("View Reports &amp; Analytics", html)

    def test_customer_cannot_access_admin_dashboard(self):
        """Security: Customers must be blocked from accessing admin dashboard."""
        self.set_customer_session()
        resp = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertIn(resp.status_code, [302, 303, 403])

    def test_all_sidebar_admin_routes_accessible(self):
        """Verify all 9 admin management sections remain fully accessible."""
        self.set_admin_session()
        routes = [
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
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Route {r} failed with {resp.status_code}")

if __name__ == "__main__":
    unittest.main()
